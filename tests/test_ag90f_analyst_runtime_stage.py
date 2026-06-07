from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from core.analyst_runtime_stage import (
    AnalystRuntimeDeps,
    AnalystRuntimeRequest,
    build_analyst_model_call_recorder,
    execute_analyst_runtime_stage,
)
from core.corpus_state import CorpusState
from core.runtime_prompt_assembly import (
    build_analyst_prompt,
    build_unsupported_retrieval_prompt_fragments,
)

ROOT = Path(__file__).resolve().parents[1]
FAKE_API_KEY = object()
HELPER = ROOT / "core" / "analyst_runtime_stage.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"


class Status:
    def __init__(self) -> None:
        self.steps: list[str] = []

    def step(self, text: str) -> None:
        self.steps.append(text)


class Calls:
    def __init__(self, monotonic_values: list[float] | None = None) -> None:
        self.ask_model: list[dict[str, Any]] = []
        self.measure: list[dict[str, Any]] = []
        self.recorded: list[str] = []
        self._times = list(monotonic_values or [100.0, 101.25])

    def ask(self, prompt: str, system: str, **kwargs: Any) -> str:
        self.ask_model.append({"prompt": prompt, "system": system, "kwargs": kwargs})
        return "ANALYST_OUTPUT"

    def measure_stage(self, stage: str, **kwargs: Any) -> None:
        self.measure.append({"stage": stage, **kwargs})

    def record(self, prompt: str) -> None:
        self.recorded.append(prompt)

    def monotonic(self) -> float:
        return self._times.pop(0)


def _pre_gate(*, analyst_skipped: bool = False, reason: str | None = None):
    def _gate(**_: Any) -> dict[str, Any]:
        signals = ["low_utilization"] if analyst_skipped else []
        return {
            "analyst_skipped": analyst_skipped,
            "analyst_skip_reason": reason if analyst_skipped else None,
            "post_retrieval_fast_path_used": analyst_skipped,
            "pre_analyst_gate_signals": signals,
        }

    return _gate


def _post_gate(**_: Any) -> dict[str, Any]:
    return {
        "analyst_skipped_after_economist": False,
        "analyst_after_economist_skip_reason": "economist_shadow_mode_no_framework",
        "economist_output_used_as_analysis": False,
    }


def _request(**overrides: Any) -> AnalystRuntimeRequest:
    status = overrides.pop("status", Status())
    values = {
        "run_id": "run-1",
        "query": "Tesla margin comparison",
        "report_type": "quantitative_comparison",
        "query_type": "research",
        "complexity": "medium",
        "corpus_state": CorpusState.HEALTHY.value,
        "corpus_weak": False,
        "retrieval_retry_used": False,
        "empty_entity_flag": False,
        "utilization_rate_val": 1.0,
        "utilization_threshold": 0.2,
        "all_passages": [
            {
                "url": "https://ir.example/q1",
                "title": "Quarter source",
                "text": "Tesla automotive gross margin was 18.5%.",
                "source_tier": "official",
            }
        ],
        "total_chunks_embedded": 1,
        "primary_entity": "Tesla",
        "core_topic": "Tesla",
        "need_economist": True,
        "economist_ran": True,
        "economist_preflight_allowed": True,
        "economist_preflight_block_reason": None,
        "economist_preflight_missing_entities": [],
        "economist_safety_telemetry": {"economist_schema_valid": True},
        "economist_pre_analyst_skip_candidate_telemetry": {"candidate": False},
        "analyst_quant_packet_handoff_telemetry": {"analyst_model_called": False},
        "author_quant_source_telemetry": {"author_received_raw_quant_packet": False},
        "estimate_from_priors_requested": False,
        "estimate_from_priors_blocked_by_pre_analyst_gate": False,
        "status": status,
        "author_notes": "BASE_NOTE\n",
        "analyst_cached_prefix": "PREFIX\n",
        "intent": "financial analysis",
        "analyst_effort": "medium",
        "default_system": {
            "analyst": "ANALYST_SYSTEM",
            "analyst_estimate_from_priors": "PRIORS_SYSTEM",
        },
        "smart_provider": "openrouter",
        "smart_model": "smart-model",
        "local_url": "http://localhost:11434/v1",
        "or_api_key": FAKE_API_KEY,
        "use_reasoning": True,
        "analyst_seconds": 3.0,
    }
    values.update(overrides)
    return AnalystRuntimeRequest(values)


def _deps(calls: Calls, *, pre_gate: Any | None = None) -> AnalystRuntimeDeps:
    return AnalystRuntimeDeps(
        ask_model=calls.ask,
        measure_context_stage=calls.measure_stage,
        record_analyst_model_call=calls.record,
        evidence_slice_for_analyst=lambda: ["evidence-slice"],
        pre_analyst_retrieval_gate=pre_gate or _pre_gate(),
        post_economist_analyst_gate=_post_gate,
        monotonic=calls.monotonic,
    )


def test_unsupported_retrieval_skips_analyst_with_exact_directive_and_author_note() -> None:
    status = Status()
    calls = Calls()
    request = _request(status=status, corpus_weak=True)

    outcome = execute_analyst_runtime_stage(
        request,
        _deps(calls, pre_gate=_pre_gate(analyst_skipped=True, reason="corpus_weak")),
    )

    expected = build_unsupported_retrieval_prompt_fragments(
        analyst_skip_reason="corpus_weak",
        pre_analyst_gate_signals=["low_utilization"],
        pre_gate_failure_card_reason=outcome.pre_gate_failure_card_reason,
    )
    assert outcome.analysis == expected.analysis
    assert outcome.author_notes == "BASE_NOTE\n" + expected.author_note_append
    assert outcome.analyst_skipped is True
    assert outcome.analyst_skip_reason == "corpus_weak"
    assert outcome.post_retrieval_fast_path_used is True
    assert calls.ask_model == []
    assert calls.measure == []
    assert status.steps == [
        "Retrieval quality gate skipped Analyst; sending unsupported-evidence directive to Author."
    ]


def test_low_complexity_direct_to_author_without_analyst_model_call() -> None:
    calls = Calls()
    outcome = execute_analyst_runtime_stage(
        _request(complexity="low"),
        _deps(calls),
    )

    assert outcome.analysis == "DIRECT_TO_AUTHOR"
    assert outcome.analyst_skipped is False
    assert calls.ask_model == []
    assert calls.recorded == []
    assert calls.measure == []


def test_estimate_from_priors_prompt_system_kwargs_and_timing_are_exact() -> None:
    calls = Calls(monotonic_values=[10.0, 12.5])
    request = _request(
        corpus_weak=True,
        corpus_state=CorpusState.ESTIMATE_FROM_PRIORS.value,
        estimate_from_priors_requested=True,
    )

    outcome = execute_analyst_runtime_stage(request, _deps(calls))

    expected_prompt = build_analyst_prompt(
        analyst_cached_prefix="PREFIX\n",
        intent="financial analysis",
        analyst_effort="medium",
        estimate_from_priors=True,
    )
    assert outcome.analysis == "ANALYST_OUTPUT"
    assert outcome.analyst_seconds == 5.5
    assert calls.recorded == [expected_prompt]
    assert calls.measure == [
        {
            "stage": "analyst_estimate_from_priors",
            "prompt": expected_prompt,
            "system_prompt": "PRIORS_SYSTEM",
            "stable_prefix": "PRIORS_SYSTEM",
            "evidence_passages": ["evidence-slice"],
        }
    ]
    assert calls.ask_model == [
        {
            "prompt": expected_prompt,
            "system": "PRIORS_SYSTEM",
            "kwargs": {
                "provider": "openrouter",
                "model": "smart-model",
                "effort": "medium",
                "base_url": "http://localhost:11434/v1",
                "api_key": FAKE_API_KEY,
                "use_reasoning": True,
            },
        }
    ]


def test_normal_analyst_prompt_system_kwargs_and_timing_are_exact() -> None:
    calls = Calls(monotonic_values=[20.0, 21.25])

    outcome = execute_analyst_runtime_stage(_request(), _deps(calls))

    expected_prompt = build_analyst_prompt(
        analyst_cached_prefix="PREFIX\n",
        intent="financial analysis",
        analyst_effort="medium",
    )
    assert outcome.analysis == "ANALYST_OUTPUT"
    assert outcome.analyst_seconds == 4.25
    assert calls.recorded == [expected_prompt]
    assert calls.measure == [
        {
            "stage": "analyst",
            "prompt": expected_prompt,
            "system_prompt": "ANALYST_SYSTEM",
            "stable_prefix": "ANALYST_SYSTEM",
            "evidence_passages": ["evidence-slice"],
        }
    ]
    assert calls.ask_model[0]["prompt"] == expected_prompt
    assert calls.ask_model[0]["system"] == "ANALYST_SYSTEM"
    assert calls.ask_model[0]["kwargs"] == {
        "provider": "openrouter",
        "model": "smart-model",
        "effort": "medium",
        "base_url": "http://localhost:11434/v1",
        "api_key": FAKE_API_KEY,
        "use_reasoning": True,
    }


def test_economist_handoff_fields_and_output_used_telemetry_remain_shadow_only() -> None:
    calls = Calls()
    outcome = execute_analyst_runtime_stage(
        _request(
            economist_ran=True,
            economist_preflight_allowed=False,
            economist_preflight_block_reason="missing_entities",
            economist_preflight_missing_entities=["Tesla", "BYD"],
        ),
        _deps(calls),
    )

    assert outcome.economist_ran is True
    assert outcome.economist_preflight_allowed is False
    assert outcome.economist_preflight_block_reason == "missing_entities"
    assert outcome.economist_preflight_missing_entities == ["Tesla", "BYD"]
    assert outcome.analyst_skipped_after_economist is False
    assert outcome.economist_output_used_as_analysis is False
    assert outcome.analyst_after_economist_skip_reason == "economist_shadow_mode_no_framework"


def test_analyst_model_call_recorder_preserves_quant_packet_review_telemetry() -> None:
    telemetry = {"analyst_quant_packet_injected": True}
    recorder = build_analyst_model_call_recorder(telemetry)

    recorder("prefix\nQUANTITATIVE PACKET FOR ANALYST REVIEW ONLY\nbody")

    assert telemetry["analyst_model_called"] is True
    assert telemetry["analyst_quant_packet_reviewed_by_model"] is True


def test_ag90f_static_seam_guards() -> None:
    helper_source = HELPER.read_text(encoding="utf-8")
    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    helper_tree = ast.parse(helper_source)

    forbidden_import_fragments = (
        "core.routing",
        "core.search_providers",
        "select_providers",
        "choose_supplemental_search_depth",
        "brave_reconnaissance",
    )
    for fragment in forbidden_import_fragments:
        assert fragment not in helper_source

    forbidden_helper_calls = {
        "select_providers",
        "choose_supplemental_search_depth",
        "process_search_queries",
        "format_citations",
    }
    for node in ast.walk(helper_tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_helper_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_helper_calls

    assert "{**globals(), **locals()}" not in pipeline_source
    assert "globals()" not in helper_source
    assert "globals()" not in pipeline_source
    assert "execute_analyst_runtime_stage_from_scope(\n            locals()," in pipeline_source
    assert len(pipeline_source.splitlines()) < 6580
