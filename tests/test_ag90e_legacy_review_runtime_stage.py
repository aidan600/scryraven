from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.legacy_review_runtime_stage import (
    LegacyReviewRuntimeDeps,
    LegacyReviewRuntimeRequest,
    execute_legacy_review_runtime_stage,
)
from core.runtime_prompt_assembly import (
    build_scrutineer_prompt,
    build_scrutineer_remediation_prompt,
    build_synthesis_evaluator_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
HELPER = ROOT / "core" / "legacy_review_runtime_stage.py"

FAKE_API_KEY = object()

DEFAULT_SYSTEM = {
    "synth_evaluator": "SYNTH_SYS",
    "scrutineer": "SCRUT_SYS",
    "researcher": "RESEARCH_SYS",
    "analyst": "ANALYST_SYS",
}


class Status:
    def __init__(self) -> None:
        self.steps: list[str] = []

    def step(self, message: str) -> None:
        self.steps.append(message)


class Collector:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def mark_eligible(self) -> None:
        self.events.append(("eligible", None))

    def mark_strong_retrieval_skipped(self) -> None:
        self.events.append(("strong_skip", None))

    def mark_parse_failed(self, error: Exception) -> None:
        self.events.append(("parse_failed", type(error).__name__))

    def mark_completeness(self, *, sufficient: bool, deficiency_text: str | None) -> None:
        self.events.append(("completeness", sufficient, deficiency_text))

    def record_supplemental_queries(self, queries: list[str]) -> None:
        self.events.append(("supp_queries", list(queries)))

    def record_author_hedge_note(self) -> None:
        self.events.append(("hedge", None))

    def record_dispatch(self, *, providers: list[str], search_depth: str) -> None:
        self.events.append(("dispatch", list(providers), search_depth))

    def record_evidence(self, passages: list[dict[str, Any]]) -> None:
        self.events.append(("evidence", list(passages)))

    def record_final_evidence_rebuild(self) -> None:
        self.events.append(("rebuild", None))

    def record_analyst_rerun(self) -> None:
        self.events.append(("analyst_rerun", None))


class QueryAuthority:
    def __init__(self, *, supplemental: list[str] | None = None, remediation: list[str] | None = None) -> None:
        self.supplemental = supplemental
        self.remediation = remediation
        self.calls: list[tuple[str, list[str], int]] = []

    def finalize_supplemental(self, queries: list[str], *, max_len: int) -> list[str]:
        self.calls.append(("supplemental", list(queries), max_len))
        return list(self.supplemental if self.supplemental is not None else queries[:max_len])

    def finalize_remediation(self, queries: list[str], *, max_len: int) -> list[str]:
        self.calls.append(("remediation", list(queries), max_len))
        return list(self.remediation if self.remediation is not None else queries[:max_len])


@dataclass
class Outcome:
    passages: list[dict[str, Any]]
    seen_url_delta: int = 0


@dataclass
class Bundle:
    final_top_evidence: list[dict[str, Any]]
    unique_source_urls: list[str]
    ordered_sources: list[str]
    evidence_block: str
    cached_prefix: str


class Harness:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.model_calls: list[tuple[str, str, dict[str, Any]]] = []
        self.measure_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.analyst_prompts: list[str] = []
        self.select_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.supplemental_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.remediation_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.now = 0.0

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self.model_calls.append((prompt, system_prompt, dict(kwargs)))
        return self.responses.pop(0)

    def clean_json_response(self, value: Any) -> str:
        return str(value)

    def measure(self, *args: Any, **kwargs: Any) -> None:
        self.measure_calls.append((args, kwargs))

    def record_analyst(self, prompt: str) -> None:
        self.analyst_prompts.append(prompt)

    def select_providers(self, *args: Any, **kwargs: Any) -> list[str]:
        self.select_calls.append((args, kwargs))
        return ["brave", "exa"]

    def choose_depth(self, complexity: str, search_depth: str) -> str:
        return f"{complexity}:{search_depth}"

    def supplemental(self, *args: Any, **kwargs: Any) -> Outcome:
        self.supplemental_calls.append((args, kwargs))
        return Outcome(passages=[{"url": "https://supp.example", "text": "supp"}], seen_url_delta=1)

    def remediation(self, *args: Any, **kwargs: Any) -> Outcome:
        self.remediation_calls.append((args, kwargs))
        return Outcome(passages=[{"url": "https://remed.example", "text": "remed"}], seen_url_delta=1)

    def monotonic(self) -> float:
        self.now += 1.0
        return self.now


def _request(**overrides: Any) -> LegacyReviewRuntimeRequest:
    values = dict(
        scope={"ordered_sources": ["old"], "evidence_block": "old evidence", "cached_prefix": "old prefix"},
        query="What happened?",
        analysis="Initial analysis",
        complexity="medium",
        corpus_weak=False,
        entity_hint_for_retrieval=None,
        utilization_rate_val=None,
        synth_skip_utilization_threshold=0.8,
        post_retrieval_fast_path_used=False,
        economist_output_used_as_analysis=False,
        status=Status(),
        collector=Collector(),
        default_system=DEFAULT_SYSTEM,
        query_authority=QueryAuthority(),
        search_depth="standard",
        query_type="news",
        intent="research",
        available_keys={"brave": True},
        report_type="brief",
        is_academic=False,
        suppress_tavily=True,
        local_url="http://local",
        or_api_key=FAKE_API_KEY,
        use_reasoning=True,
        fast_provider="fast-provider",
        fast_model="fast-model",
        smart_provider="smart-provider",
        smart_model="smart-model",
        analyst_effort="medium",
        all_passages=[],
        linkup_block="LINKUP",
        current_date="2026-06-06",
        core_topic="topic",
        past_searches=["old query"],
        final_top_evidence=[{"url": "https://old.example", "text": "old"}],
        unique_source_urls=["https://old.example"],
        run_log=logging.getLogger("ag90e-test"),
        author_notes="",
        first_synth_sufficient=True,
        synth_was_insufficient=False,
        synth_deficiency=None,
        supplemental_ran=False,
        delta_urls_supplemental=0,
        synth_evaluator_seconds=0.0,
        analyst_seconds=0.0,
        scrutineer_ran=False,
        scrutineer_seconds=0.0,
    )
    values.update(overrides)
    return LegacyReviewRuntimeRequest(**values)


def _deps(harness: Harness, *, supp=None, remed=None) -> LegacyReviewRuntimeDeps:
    return LegacyReviewRuntimeDeps(
        ask_model=harness.ask_model,
        clean_json_response=harness.clean_json_response,
        measure_context_stage=harness.measure,
        record_analyst_model_call=harness.record_analyst,
        build_final_evidence_bundle=lambda *_args, **_kwargs: Bundle(
            final_top_evidence=[{"url": "https://rebuilt.example", "text": "rebuilt"}],
            unique_source_urls=["https://rebuilt.example"],
            ordered_sources=["rebuilt"],
            evidence_block="rebuilt evidence",
            cached_prefix="rebuilt prefix",
        ),
        final_evidence_bundle_inputs=lambda: object(),
        build_analyst_cached_prefix=lambda: "ANALYST PREFIX",
        evidence_slice_for_analyst=lambda: ["slice"],
        select_providers=harness.select_providers,
        choose_supplemental_search_depth=harness.choose_depth,
        execute_supplemental_search=supp or harness.supplemental,
        execute_scrutineer_remediation=remed or harness.remediation,
        monotonic=harness.monotonic,
        environ_get=lambda key: "enabled" if key == "LINKUP_API_KEY" else None,
    )


def test_synthesis_evaluator_model_call_shape_and_prompt_when_sufficient() -> None:
    harness = Harness([json.dumps({"is_sufficient": True})])
    request = _request()

    outcome = execute_legacy_review_runtime_stage(request, _deps(harness))

    expected_prompt = build_synthesis_evaluator_prompt(query=request.query, analysis=request.analysis)
    assert harness.model_calls == [
        (
            expected_prompt,
            DEFAULT_SYSTEM["synth_evaluator"],
            {
                "provider": "fast-provider",
                "model": "fast-model",
                "effort": "low",
                "base_url": "http://local",
                "api_key": FAKE_API_KEY,
                "require_json": True,
                "use_reasoning": True,
            },
        )
    ]
    assert outcome.first_synth_sufficient is True
    assert outcome.supplemental_ran is False
    assert harness.supplemental_calls == []


def test_supplemental_search_dispatch_shape_and_analyst_rerun_shape() -> None:
    harness = Harness([
        json.dumps({"is_sufficient": False, "deficiency": "Missing dates", "supplemental_queries": ["date query"]}),
        "Updated analysis",
    ])
    request = _request(query_authority=QueryAuthority(supplemental=["date query"]))

    outcome = execute_legacy_review_runtime_stage(request, _deps(harness))

    assert harness.select_calls[0] == (
        ("news", "research", "medium", {"brave": True}),
        {"report_type": "brief", "is_academic": False, "suppress_tavily": True, "override": None},
    )
    assert harness.supplemental_calls[0][1] == {
        "queries": ["date query"],
        "search_depth": "medium:standard",
        "providers": ["brave", "exa"],
    }
    analyst_call = harness.model_calls[-1]
    assert analyst_call[1:] == (
        DEFAULT_SYSTEM["analyst"],
        {
            "provider": "smart-provider",
            "model": "smart-model",
            "effort": "medium",
            "base_url": "http://local",
            "api_key": FAKE_API_KEY,
            "use_reasoning": True,
        },
    )
    assert outcome.analysis == "Updated analysis"
    assert outcome.final_top_evidence == [{"url": "https://rebuilt.example", "text": "rebuilt"}]
    assert outcome.delta_urls_supplemental == 1


def test_scrutineer_high_flag_threshold_passes_flags_without_remediation() -> None:
    flags = [{"severity": "high", "category": "SINGLE-SOURCE", "challenge": str(i)} for i in range(5)]
    harness = Harness([
        json.dumps({"is_sufficient": True}),
        json.dumps({"verdict": "flagged", "flags": flags}),
    ])
    request = _request(complexity="high")

    outcome = execute_legacy_review_runtime_stage(request, _deps(harness))

    scrut_prompt = build_scrutineer_prompt(
        intent=request.intent,
        default_scrutineer_system=DEFAULT_SYSTEM["scrutineer"],
        final_top_evidence=request.final_top_evidence,
        unique_source_urls=request.unique_source_urls,
        analysis=request.analysis,
    )
    assert harness.model_calls[1] == (
        scrut_prompt.user_prompt,
        scrut_prompt.system_prompt,
        {
            "provider": "smart-provider",
            "model": "smart-model",
            "effort": "medium",
            "base_url": "http://local",
            "api_key": FAKE_API_KEY,
            "require_json": True,
            "use_reasoning": False,
        },
    )
    assert outcome.scrutineer_high_count == 5
    assert outcome.scrutineer_pass_flags_directly_to_author is True
    assert harness.remediation_calls == []


def test_scrutineer_duplicate_remediation_query_records_rejection_without_dispatch() -> None:
    flag = {"severity": "high", "category": "SINGLE-SOURCE", "challenge": "Needs source", "flag_id": "f1"}
    harness = Harness([
        json.dumps({"is_sufficient": True}),
        json.dumps({"verdict": "flagged", "flags": [flag]}),
        json.dumps({"queries": ["old query"]}),
    ])
    request = _request(complexity="high", query_authority=QueryAuthority(remediation=[]))

    outcome = execute_legacy_review_runtime_stage(request, _deps(harness))

    expected_remed_prompt = build_scrutineer_remediation_prompt(
        current_date="2026-06-06",
        core_topic="topic",
        past_searches=["old query"],
        search_flags=[flag],
    )
    assert harness.model_calls[2] == (
        expected_remed_prompt,
        DEFAULT_SYSTEM["researcher"],
        {
            "provider": "fast-provider",
            "model": "fast-model",
            "effort": "low",
            "base_url": "http://local",
            "api_key": FAKE_API_KEY,
            "require_json": True,
            "use_reasoning": True,
        },
    )
    assert outcome.scrutineer_remediation_dispatch_authorized is False
    assert outcome.scrutineer_remediation_queries[0].filter_posture == "rejected_duplicate"
    assert outcome.scrutineer_remediation_queries[0].rejection_reason == "overlap_gt_0_6"
    assert harness.remediation_calls == []


def test_scrutineer_remediation_dispatch_shape_and_resynthesis() -> None:
    flag = {"severity": "high", "category": "TEMPORAL DRIFT", "challenge": "Needs update", "flag_id": "f2"}
    harness = Harness([
        json.dumps({"is_sufficient": True}),
        json.dumps({"verdict": "flagged", "flags": [flag]}),
        json.dumps({"queries": ["fresh update"]}),
        "Remediated analysis",
    ])
    request = _request(complexity="high", query_authority=QueryAuthority(remediation=["fresh update"]))

    outcome = execute_legacy_review_runtime_stage(request, _deps(harness))

    assert harness.remediation_calls[0][1] == {
        "queries": ["fresh update"],
        "providers": ["brave", "exa"],
    }
    assert outcome.scrutineer_remediation_dispatch_authorized is True
    assert outcome.scrutineer_remediation_dispatch_posture == "completed"
    assert outcome.scrutineer_remediation_provider_role == "scrutineer_remediation"
    assert outcome.scrutineer_remediation_linkup_depth_override == "deep"
    assert outcome.scrutineer_remediation_resynthesis_triggered is True
    assert outcome.analysis == "Remediated analysis"
    assert harness.model_calls[-1][2] == {
        "provider": "smart-provider",
        "model": "smart-model",
        "effort": "medium",
        "base_url": "http://local",
        "api_key": FAKE_API_KEY,
        "use_reasoning": True,
    }


def test_ag90e_static_guards_for_bounded_extraction() -> None:
    pipeline_lines = len(PIPELINE.read_text(encoding="utf-8").splitlines())
    helper_source = HELPER.read_text(encoding="utf-8")
    assert pipeline_lines <= 6580
    assert "from core.routing import" not in helper_source
    assert "from core.search_providers" not in helper_source
    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    assert "process_search_queries(" not in helper_source
    assert "from core.prompts" not in helper_source
    assert "{**globals(), **locals()}" not in pipeline_source
    assert "globals()" not in pipeline_source.split("execute_legacy_review_runtime_stage_from_scope", 1)[1]
    assert "legacy_review_deps = legacy_review_runtime_stage.LegacyReviewRuntimeDeps(" in pipeline_source
    assert "locals(), deps=legacy_review_deps, default_system=DEFAULT_SYSTEM" in pipeline_source
    assert "stage_scope = {key: scope[key] for key in _SCOPE_KEYS if key in scope}" in helper_source
    assert "_RETRIEVAL_DISPATCH_SCOPE_FIELD_NAMES" in helper_source
    assert "json.dumps(scope" not in helper_source
    assert "json.dumps(stage_scope" not in helper_source
