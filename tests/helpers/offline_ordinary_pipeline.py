from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps

OFFLINE_PROVIDER_ENV_KEYS = (
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
    "LINKUP_API_KEY",
    "EXA_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)

HANDOFF_SEMANTIC = "semantic"
HANDOFF_SUFFICIENCY = "sufficiency"
HANDOFF_PACKET = "packet"
HANDOFF_AUTHOR = "author"


def scrub_offline_runtime(monkeypatch: Any) -> None:
    for key in OFFLINE_PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(orchestrator, "DB_ENABLED", False)
    monkeypatch.setattr(orchestrator, "kb_review_agent", lambda *_args, **_kwargs: {})


def assert_no_semantic_state(kernel: Any) -> None:
    assert not kernel.state.initial_answer_contract
    assert not kernel.state.semantic_observation_admission_history
    assert not kernel.state.component_coverage_history


def offline_balanced_run_config(
    *,
    query: str,
    current_date: str,
    session_id: str,
    run_id: str,
    cap_policy: Any | None = None,
    smart_search_judgment_model: bool = False,
    enable_ordinary_live_candidate_handoff: bool = False,
    ordinary_live_candidate_handoff_results: (
        Sequence[dict[str, Any]] | Mapping[str, Any] | None
    ) = None,
    ordinary_live_candidate_handoff_provider: str = "offline-fake-search",
    enable_ordinary_live_source_custody: bool = False,
    ordinary_live_source_custody_anchor_groups: Sequence[Any] = (),
    enable_ordinary_live_semantic_coverage: bool = False,
    enable_ordinary_live_authority_consolidation: bool = False,
    enable_ordinary_live_main_runkernel_coverage: bool = False,
) -> RunConfig:
    return RunConfig(
        query=query,
        mode="Balanced",
        current_date=current_date,
        session_id=session_id,
        run_id=run_id,
        fast_provider="offline-fake-provider",
        fast_model="offline-fake-fast-model",
        smart_provider="offline-fake-provider",
        smart_model="offline-fake-smart-model",
        local_url="http://offline.invalid/v1",
        or_api_key="",
        use_reasoning=False,
        run_authority_contract_smart_model=False,
        run_authority_search_judgment_smart_model=smart_search_judgment_model,
        run_authority_sufficiency_smart_model=False,
        cap_policy=cap_policy,
        enable_ordinary_live_candidate_handoff=(
            enable_ordinary_live_candidate_handoff
        ),
        ordinary_live_candidate_handoff_results=(
            dict(ordinary_live_candidate_handoff_results)
            if isinstance(ordinary_live_candidate_handoff_results, Mapping)
            else list(ordinary_live_candidate_handoff_results or ())
        ),
        ordinary_live_candidate_handoff_provider=(
            ordinary_live_candidate_handoff_provider
        ),
        enable_ordinary_live_source_custody=enable_ordinary_live_source_custody,
        ordinary_live_source_custody_anchor_groups=tuple(
            ordinary_live_source_custody_anchor_groups
        ),
        enable_ordinary_live_semantic_coverage=(
            enable_ordinary_live_semantic_coverage
        ),
        enable_ordinary_live_authority_consolidation=(
            enable_ordinary_live_authority_consolidation
        ),
        enable_ordinary_live_main_runkernel_coverage=(
            enable_ordinary_live_main_runkernel_coverage
        ),
    )


@dataclass
class OfflineOrdinaryPipelineHarness:
    tmp_path: Path
    query: str
    core_topic: str
    primary_entity: str
    raw_author_response: str
    researcher_queries: Sequence[str] | None = None
    expander_reasoning: str = "offline fixture sufficient"
    analyst_response: str | None = None
    logger_name: str = "tests.helpers.offline_ordinary_pipeline"
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    search_calls: list[dict[str, Any]] = field(default_factory=list)
    author_prompts: list[str] = field(default_factory=list)
    author_kwargs: list[dict[str, Any]] = field(default_factory=list)
    forbidden_live_calls: list[str] = field(default_factory=list)

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self.model_calls.append(
            {
                "system_prompt": system_prompt,
                "stream": bool(kwargs.get("stream")),
                "provider": kwargs.get("provider"),
                "model": kwargs.get("model"),
                "use_reasoning": kwargs.get("use_reasoning"),
            }
        )
        if system_prompt == DEFAULT_SYSTEM["router"]:
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": "general_research",
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": False,
                    "query_type": "other",
                    "entities": [self.primary_entity],
                    "primary_entity": self.primary_entity,
                }
            )
        if system_prompt == "You are a concise title generator.":
            return f"{self.primary_entity} Rule"
        if system_prompt == DEFAULT_SYSTEM["researcher"]:
            queries = self.researcher_queries or (
                f"{self.primary_entity} official current rule",
            )
            return json.dumps({"queries": list(queries)})
        if system_prompt == DEFAULT_SYSTEM["expander"] or (
            "research gap detector" in system_prompt
        ):
            return json.dumps(
                {"component_queries": [], "reasoning": self.expander_reasoning}
            )
        if system_prompt == DEFAULT_SYSTEM["evaluator"]:
            return json.dumps({"is_sufficient": True, "new_queries": []})
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            return self.analyst_response or (
                f"Analysis is limited to the retrieved official {self.primary_entity} "
                "rule."
            )
        if system_prompt == DEFAULT_SYSTEM["synth_evaluator"]:
            return json.dumps({"is_sufficient": True, "supplemental_queries": []})
        if kwargs.get("stream"):
            self.author_prompts.append(prompt)
            self.author_kwargs.append(dict(kwargs))
            return self.raw_author_response
        raise AssertionError(f"unexpected model call in offline fixture: {system_prompt!r}")

    def embed_texts(self, texts: list[str], **_kwargs: Any) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    def build_search_passages(self) -> list[dict[str, Any]]:
        raise NotImplementedError

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
                "search_providers": list(kwargs.get("search_providers") or []),
            }
        )
        seen_urls = kwargs.get("seen_urls")
        if seen_urls is None and len(_args) >= 4:
            seen_urls = _args[3]
        passages = self.build_search_passages()
        if seen_urls is not None:
            for passage in passages:
                seen_urls.add(passage["url"])
        return passages

    def forbidden_live_dependency(self, name: str):
        def _called(*_args: Any, **_kwargs: Any) -> Any:
            self.forbidden_live_calls.append(name)
            if name == "run_scout":
                return {}
            return ""

        return _called

    def strict_one_shot_smart_model_transport(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> Any:
        from core.strict_one_shot_model_transport import (
            BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED,
            StrictOneShotModelTransportResult,
            normalize_canonical_model_provider,
        )

        provider = str(kwargs.get("provider") or "OpenAI")
        model = str(kwargs.get("model") or "gpt-5.4")
        canonical_provider = normalize_canonical_model_provider(provider)
        try:
            output_text = self.ask_model(prompt, system_prompt, **kwargs)
        except Exception as exc:  # noqa: BLE001 - test fake preserves safe failure facts.
            return StrictOneShotModelTransportResult(
                return_code=2,
                failure_kind=BLOCKED_STRICT_ONE_SHOT_PROVIDER_CALL_FAILED,
                detail=f"Offline strict one-shot fake failed closed: {type(exc).__name__}.",
                canonical_provider=canonical_provider,
                configured_model=model,
                provider_request_attempt_count=1,
                provider_request_succeeded=False,
                provider_request_failed=True,
            )
        return StrictOneShotModelTransportResult(
            return_code=0,
            output_text=str(output_text or ""),
            canonical_provider=canonical_provider,
            configured_model=model,
            provider_request_attempt_count=1,
            provider_request_succeeded=True,
            provider_request_failed=False,
        )

    def deps(self) -> RunDeps:
        return RunDeps(
            ask_model=self.ask_model,
            embed_texts=self.embed_texts,
            compute_similarities=lambda texts, *_args, **_kwargs: [1.0 for _ in texts],
            process_search_queries=self.process_search_queries,
            filter_top_evidence=lambda passages, *_args, **_kwargs: list(passages),
            is_plausible_domain=lambda _url: True,
            anchor_query_to_topic=lambda query, _topic: query,
            fetch_linkup_precision_block=self.forbidden_live_dependency(
                "fetch_linkup_precision_block"
            ),
            run_economist_step=self.forbidden_live_dependency("run_economist_step"),
            run_scout=self.forbidden_live_dependency("run_scout"),
            should_skip_quant_scout=lambda *_args, **_kwargs: True,
            clean_json_response=lambda value: value,
            DEFAULT_SYSTEM=DEFAULT_SYSTEM,
            NEWS_PREFERRED_DOMAINS=[],
            ACADEMIC_DOMAINS=[],
            QUANT_REPORT_TYPES=set(),
            logger=logging.getLogger(self.logger_name),
            execution_log_path=self.tmp_path / "execution.jsonl",
            feedback_log_path=self.tmp_path / "feedback.jsonl",
            kb_triggers_path=self.tmp_path / "kb.jsonl",
            policy_state_path=self.tmp_path / "policy.json",
            policy_journal_path=self.tmp_path / "policy_journal.jsonl",
            strict_one_shot_smart_model_transport=self.strict_one_shot_smart_model_transport,
        )


def install_handoff_capture(
    monkeypatch: Any,
    *,
    capture_stages: Sequence[str],
) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    stages = set(capture_stages)

    if HANDOFF_SEMANTIC in stages:
        captured["semantic_handoff_called"] = False
        original_semantic = (
            orchestrator.execute_ordinary_semantic_or_multicomponent_handoff_from_scope
        )

        def semantic_wrapper(
            run_kernel: Any,
            runtime_scope: dict[str, Any],
            **kwargs: Any,
        ) -> Any:
            captured["semantic_handoff_called"] = True
            captured["semantic_run_kernel"] = run_kernel
            captured["semantic_runtime_scope"] = dict(runtime_scope)
            result = original_semantic(run_kernel, runtime_scope, **kwargs)
            captured["multicomponent_or_semantic_handoff_result"] = result
            compatibility_result = getattr(result, "direct_handoff", None) or result
            prior = captured.get("semantic_handoff_result")
            prior_status = getattr(getattr(prior, "status", None), "value", None)
            if prior is None or prior_status != "committed":
                captured["semantic_handoff_result"] = compatibility_result
            return result

        monkeypatch.setattr(
            orchestrator,
            "execute_ordinary_semantic_or_multicomponent_handoff_from_scope",
            semantic_wrapper,
        )

    if HANDOFF_SUFFICIENCY in stages:
        captured["sufficiency_handoff_called"] = False
        captured["sufficiency_handoffs"] = []
        captured["sufficiency_projections"] = []
        original_sufficiency = orchestrator.execute_sufficiency_judgment_handoff_from_scope

        def sufficiency_wrapper(
            run_kernel: Any,
            runtime_scope: dict[str, Any],
            **kwargs: Any,
        ) -> Any:
            captured["sufficiency_handoff_called"] = True
            captured["sufficiency_runtime_scope"] = dict(runtime_scope)
            handoff = original_sufficiency(run_kernel, runtime_scope, **kwargs)
            captured["sufficiency_handoff"] = handoff
            captured["sufficiency_handoffs"].append(handoff)
            captured["sufficiency_projection"] = dict(
                run_kernel.state.sufficiency_judgment_projection
            )
            captured["sufficiency_projections"].append(
                dict(run_kernel.state.sufficiency_judgment_projection)
            )
            return handoff

        monkeypatch.setattr(
            orchestrator,
            "execute_sufficiency_judgment_handoff_from_scope",
            sufficiency_wrapper,
        )

    if HANDOFF_PACKET in stages:
        captured["packet_handoff_called"] = False
        original_packet = orchestrator.prepare_final_answer_packet_author_handoff_from_scope

        def packet_wrapper(
            run_kernel: Any,
            runtime_scope: dict[str, Any],
            **kwargs: Any,
        ) -> Any:
            captured["packet_handoff_called"] = True
            captured["run_kernel"] = run_kernel
            captured["packet_runtime_scope"] = dict(runtime_scope)
            handoff = original_packet(run_kernel, runtime_scope, **kwargs)
            captured["packet_handoff"] = handoff
            return handoff

        monkeypatch.setattr(
            orchestrator,
            "prepare_final_answer_packet_author_handoff_from_scope",
            packet_wrapper,
        )

    if HANDOFF_AUTHOR in stages:
        captured["author_handoff_called"] = False
        original_author = orchestrator.execute_author_handoff_from_scope

        def author_wrapper(
            run_kernel: Any,
            runtime_scope: dict[str, Any],
            **kwargs: Any,
        ) -> Any:
            captured["author_handoff_called"] = True
            captured["author_runtime_scope"] = dict(runtime_scope)
            handoff = original_author(run_kernel, runtime_scope, **kwargs)
            captured["author_handoff"] = handoff
            return handoff

        monkeypatch.setattr(orchestrator, "execute_author_handoff_from_scope", author_wrapper)

    return captured


def run_offline_ordinary_pipeline(
    harness: OfflineOrdinaryPipelineHarness,
    monkeypatch: Any,
    *,
    current_date: str,
    session_id: str,
    run_id: str,
    capture_stages: Sequence[str],
    cap_policy: Any | None = None,
    smart_search_judgment_model: bool = False,
    enable_ordinary_live_candidate_handoff: bool = False,
    ordinary_live_candidate_handoff_results: (
        Sequence[dict[str, Any]] | Mapping[str, Any] | None
    ) = None,
    ordinary_live_candidate_handoff_provider: str = "offline-fake-search",
    enable_ordinary_live_source_custody: bool = False,
    ordinary_live_source_fetch_read: Any | None = None,
    ordinary_live_source_custody_anchor_groups: Sequence[Any] = (),
    enable_ordinary_live_semantic_coverage: bool = False,
    enable_ordinary_live_authority_consolidation: bool = False,
    enable_ordinary_live_main_runkernel_coverage: bool = False,
) -> tuple[dict[str, Any], Any]:
    captured = install_handoff_capture(monkeypatch, capture_stages=capture_stages)
    deps = harness.deps()
    if ordinary_live_source_fetch_read is not None:
        deps = replace(
            deps,
            ordinary_live_source_fetch_read=ordinary_live_source_fetch_read,
        )
    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date=current_date,
            session_id=session_id,
            run_id=run_id,
            cap_policy=cap_policy,
            smart_search_judgment_model=smart_search_judgment_model,
            enable_ordinary_live_candidate_handoff=(
                enable_ordinary_live_candidate_handoff
            ),
            ordinary_live_candidate_handoff_results=(
                ordinary_live_candidate_handoff_results
            ),
            ordinary_live_candidate_handoff_provider=(
                ordinary_live_candidate_handoff_provider
            ),
            enable_ordinary_live_source_custody=enable_ordinary_live_source_custody,
            ordinary_live_source_custody_anchor_groups=(
                ordinary_live_source_custody_anchor_groups
            ),
            enable_ordinary_live_semantic_coverage=(
                enable_ordinary_live_semantic_coverage
            ),
            enable_ordinary_live_authority_consolidation=(
                enable_ordinary_live_authority_consolidation
            ),
            enable_ordinary_live_main_runkernel_coverage=(
                enable_ordinary_live_main_runkernel_coverage
            ),
        ),
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )
    return captured, outcome
