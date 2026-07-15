"""Product-facing ordinary-live CLI dry-run support.

The dry-run enters the real CLI -> run_pipeline path with deterministic offline
dependencies. It is default-off, performs no live provider/search/fetch/model
calls, and emits only a review status for the ordinary-live main RunKernel
coverage trace.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from core.ordinary_live_main_runkernel_coverage_runtime import (
    ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY,
)
from core.prompts import DEFAULT_SYSTEM
from core.run_config import RunConfig, RunDeps

ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG = (
    "--ordinary-live-main-runkernel-coverage-dry-run"
)
ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_INPUT = (
    "What is the official current permit threshold for the example program?"
)
ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_NEXT_CHECKPOINT = (
    "limited-live-validation-current-path-checkpoint"
)

_CANDIDATE_URL = "https://official.example.gov/program/threshold"
_CANDIDATE_DOMAIN = "official.example.gov"
_PRIMARY_ENTITY = "Example Program"
_CORE_TOPIC = "Example Program current permit threshold"
_RESEARCH_QUERY = "Example Program official current permit threshold"
_DRY_RUN_REPORT = (
    "ordinary-live dry-run report suppressed; review the CLI dry-run status."
)
_ANCHORS = (
    ("official",),
    ("current",),
    ("permit",),
    ("threshold",),
    ("500",),
)


@dataclass(slots=True)
class OrdinaryLiveEntrypointDryRunDeps:
    """Deterministic fake dependency boundary for the product CLI dry-run."""

    output_dir: Path
    logger: logging.Logger
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    search_calls: list[dict[str, Any]] = field(default_factory=list)
    closed_dependency_calls: list[str] = field(default_factory=list)

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self.model_calls.append(
            {
                "system_prompt": str(system_prompt)[:120],
                "stream": bool(kwargs.get("stream")),
                "provider": kwargs.get("provider"),
                "model": kwargs.get("model"),
            }
        )
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": "general_research",
                    "image_mode": "none",
                    "core_topic": _CORE_TOPIC,
                    "is_academic": False,
                    "query_type": "other",
                    "entities": [_PRIMARY_ENTITY],
                    "primary_entity": _PRIMARY_ENTITY,
                }
            )
        if system_prompt == "You are a concise title generator.":
            return "Example Program Threshold"
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            return json.dumps({"queries": [_RESEARCH_QUERY]})
        if _is_expander_prompt(system_prompt):
            return json.dumps(
                {"component_queries": [], "reasoning": "dry-run fixture sufficient"}
            )
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            return (
                "Dry-run analysis is limited to deterministic offline source "
                "material and is not product correctness."
            )
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            return _DRY_RUN_REPORT
        raise RuntimeError(
            "ordinary-live dry-run fake model received an unexpected prompt"
        )

    def embed_texts(self, texts: list[str], **_kwargs: Any) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def process_search_queries(
        self,
        queries: list[str],
        intent: str,
        complexity: str,
        search_depth: str,
        results_per_query: int,
        *_args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {
                "queries": list(queries),
                "intent": intent,
                "complexity": complexity,
                "search_depth": search_depth,
                "results_per_query": results_per_query,
                "provider_role": kwargs.get("provider_role"),
            }
        )
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 4:
            seen_urls = _args[3]
        passages = [_retrieval_passage()]
        if seen_urls is not None:
            for passage in passages:
                seen_urls.add(passage["url"])
        return passages

    def fake_source_fetch_read(
        self,
        *,
        candidate: Mapping[str, Any],
        source_url: str,
        source_candidate_ref: Mapping[str, Any],
    ) -> dict[str, Any]:
        del source_candidate_ref
        text = (
            "The official current Example Program permit threshold is 500 "
            "units for the active program year."
        )
        return {
            "fetch_read_status": "readable",
            "attempted_url": source_url,
            "resolved_url": source_url,
            "final_url": source_url,
            "canonical_url": source_url,
            "resolved_domain": candidate["domain"],
            "http_status": 200,
            "content_type": "text/html; charset=utf-8",
            "retrieved_or_observed_at": "2026-06-30T12:00:00Z",
            "content_title": candidate["title"],
            "content_length": len(text),
            "sanitized_text": text,
        }

    def closed_dependency(self, name: str) -> Any:
        def _called(*_args: Any, **_kwargs: Any) -> Any:
            self.closed_dependency_calls.append(name)
            if name == "run_scout":
                return {}
            return ""

        return _called

    def to_run_deps(self) -> RunDeps:
        return RunDeps(
            ask_model=self.ask_model,
            embed_texts=self.embed_texts,
            compute_similarities=lambda texts, *_args, **_kwargs: [
                1.0 for _ in texts
            ],
            process_search_queries=self.process_search_queries,
            filter_top_evidence=lambda passages, *_args, **_kwargs: list(passages),
            is_plausible_domain=lambda _url: True,
            anchor_query_to_topic=lambda query, _topic: query,
            fetch_linkup_precision_block=self.closed_dependency(
                "fetch_linkup_precision_block"
            ),
            run_scout=self.closed_dependency("run_scout"),
            should_skip_quant_scout=lambda *_args, **_kwargs: True,
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES=set(),
            logger=self.logger,
            execution_log_path=(
                self.output_dir
                / "ordinary_live_main_runkernel_coverage_dry_run_execution.jsonl"
            ),
            feedback_log_path=(
                self.output_dir
                / "ordinary_live_main_runkernel_coverage_dry_run_feedback.jsonl"
            ),
            kb_triggers_path=(
                self.output_dir
                / "ordinary_live_main_runkernel_coverage_dry_run_kb.jsonl"
            ),
            policy_state_path=(
                self.output_dir
                / "ordinary_live_main_runkernel_coverage_dry_run_policy.json"
            ),
            policy_journal_path=(
                self.output_dir
                / "ordinary_live_main_runkernel_coverage_dry_run_policy_journal.jsonl"
            ),
            ordinary_live_source_fetch_read=self.fake_source_fetch_read,
        )


def build_ordinary_live_entrypoint_dry_run_config(
    *,
    query: str,
    mode: str,
    current_date: str,
    include_domains: list[str],
    exclude_domains: list[str],
) -> RunConfig:
    """Build the default-off dry-run RunConfig consumed by the ordinary CLI."""

    return RunConfig(
        query=query,
        mode=mode,
        current_date=current_date,
        include_domains=list(include_domains),
        exclude_domains=list(exclude_domains),
        fast_provider="offline-fake-provider",
        fast_model="ordinary-live-dry-run-fast",
        smart_provider="offline-fake-provider",
        smart_model="ordinary-live-dry-run-smart",
        embed_provider="offline-fake-provider",
        embed_model="ordinary-live-dry-run-embed",
        local_url="http://offline.invalid/v1",
        or_api_key="",
        use_reasoning=False,
        run_authority_contract_smart_model=False,
        run_authority_search_judgment_smart_model=False,
        run_authority_sufficiency_smart_model=False,
        ordinary_live_candidate_handoff_results=_candidate_results(),
        ordinary_live_candidate_handoff_provider="offline-fake-search",
        ordinary_live_source_custody_anchor_groups=_ANCHORS,
        enable_ordinary_live_main_runkernel_coverage=True,
    )


def format_ordinary_live_entrypoint_dry_run_status(
    *,
    execution_trace: Mapping[str, Any],
) -> str:
    """Return the CLI-visible dry-run status, never the generated report text."""

    projection = _safe_mapping(
        execution_trace.get(ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY)
    )
    if not projection:
        return "\n".join(
            (
                "ordinary-live dry-run blocked",
                "blocker: ordinary_entrypoint_visibility_not_supported",
                f"next checkpoint: {ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_NEXT_CHECKPOINT}",
                "output type: dry-run blocker, not live product behavior",
            )
        )

    live_calls = sum(
        _bounded_int(projection.get(key))
        for key in (
            "provider_search_calls",
            "search_calls",
            "broker_calls",
            "fetch_read_calls",
            "model_calls",
            "retrieval_calls",
        )
    )
    component_reduced = _bounded_int(
        projection.get("main_component_coverage_reduced_count")
    ) > 0
    semantic_admitted = _bounded_int(
        projection.get("main_semantic_observation_admitted_count")
    ) > 0
    closed_flags = _safe_mapping(projection.get("closed_surface_flags"))
    sufficiency_fap_author_closed = all(
        closed_flags.get(key) is False
        for key in (
            "sufficiency_readiness_reduced",
            "fap_created",
            "author_invoked",
            "answer_text_created",
            "product_correctness_claimed",
        )
    )
    if projection.get("failed_closed") is True:
        blocker = str(
            projection.get("first_failed_seam")
            or "ordinary_live_main_runkernel_coverage_failed_closed"
        )
        return "\n".join(
            (
                "ordinary-live dry-run blocked",
                f"blocker: {blocker}",
                f"main SemanticObservation admitted: {_bool_text(semantic_admitted)}",
                f"main ComponentCoverage reduced: {_bool_text(component_reduced)}",
                f"live calls: {live_calls}",
                f"next checkpoint: {ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_NEXT_CHECKPOINT}",
                "output type: dry-run blocker, not live product behavior",
            )
        )

    return "\n".join(
        (
            "ordinary-live dry-run reached main RunKernel coverage",
            "ordinary entrypoint: python -m proplex",
            "runtime consumer: core.pipeline_orchestrator.run_pipeline",
            f"main SemanticObservation admitted: {_bool_text(semantic_admitted)}",
            f"main ComponentCoverage reduced: {_bool_text(component_reduced)}",
            (
                "Sufficiency/FAP/Author closed for ordinary-live coverage: "
                f"{_bool_text(sufficiency_fap_author_closed)}"
            ),
            f"live calls: {live_calls}",
            "output type: dry-run status, not live product behavior",
        )
    )


def _candidate_results() -> list[dict[str, Any]]:
    return [
        {
            "title": "Example Program Permit Threshold",
            "url": _CANDIDATE_URL,
            "domain": _CANDIDATE_DOMAIN,
            "snippet": "Official current permit threshold for the Example Program.",
            "published_or_observed_date": "2026-06-30",
        }
    ]


def _retrieval_passage() -> dict[str, Any]:
    return {
        "source_id": 1,
        "title": "Example Program Permit Threshold",
        "url": _CANDIDATE_URL,
        "text": (
            "Official Example Program material says the current permit "
            "threshold is 500 units."
        ),
        "score": 0.99,
        "credibility": 4,
        "source_tier": "official",
        "source_class": "primary_source_documents",
        "currentness_signal": "current",
        "readable_status": "readable",
        "disposition": "accepted",
        "eligible_for_stronger_obligation": False,
        "query_ref": _RESEARCH_QUERY,
        "_provider": "offline_fake_search",
    }


def _is_expander_prompt(system_prompt: str) -> bool:
    text = str(system_prompt)
    return (
        text == DEFAULT_SYSTEM["expander"]
        or "component_queries" in text
        or "research gap detector" in text.casefold()
    )


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


__all__ = [
    "ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG",
    "ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_INPUT",
    "OrdinaryLiveEntrypointDryRunDeps",
    "build_ordinary_live_entrypoint_dry_run_config",
    "format_ordinary_live_entrypoint_dry_run_status",
]
