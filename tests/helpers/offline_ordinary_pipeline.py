from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import core.pipeline_orchestrator as orchestrator
from core.acquisition_adapters import AcquisitionTransports
from core.cost_accounting import CostAccumulator
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
)
from core.prompts import DEFAULT_SYSTEM
from core.protocols import NullStatusWriter
from core.run_config import RunConfig, RunDeps
from core.search_judgment_read_assessment_runtime import (
    SEARCH_JUDGMENT_READ_SYSTEM_PROMPT,
)
from core.search_planner_runtime import DeterministicSearchPlannerAdapter
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_JUDGMENT_SYSTEM_PROMPT,
)

OFFLINE_PROVIDER_ENV_KEYS = (
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
    "LINKUP_API_KEY",
    "EXA_API_KEY",
    "SERPER_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)

OFFLINE_SEARCH_PROVIDER_ENV_KEYS = {
    "tavily": "TAVILY_API_KEY",
    "linkup": "LINKUP_API_KEY",
    "exa": "EXA_API_KEY",
    "serper": "SERPER_API_KEY",
    "brave": "BRAVE_API_KEY",
}
OFFLINE_PROVIDER_AVAILABILITY_PLACEHOLDER = "offline-provider-availability"

HANDOFF_SEMANTIC = "semantic"
HANDOFF_SUFFICIENCY = "sufficiency"
HANDOFF_PACKET = "packet"
HANDOFF_AUTHOR = "author"


def scrub_offline_runtime(
    monkeypatch: Any,
    *,
    available_search_providers: Sequence[str] = (),
) -> None:
    requested_providers = tuple(
        str(provider).strip().casefold() for provider in available_search_providers
    )
    unknown_providers = tuple(
        provider
        for provider in requested_providers
        if provider not in OFFLINE_SEARCH_PROVIDER_ENV_KEYS
    )
    if unknown_providers:
        raise ValueError(
            "unknown offline search provider(s): " + ", ".join(unknown_providers)
        )
    for key in OFFLINE_PROVIDER_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    for provider in requested_providers:
        monkeypatch.setenv(
            OFFLINE_SEARCH_PROVIDER_ENV_KEYS[provider],
            OFFLINE_PROVIDER_AVAILABILITY_PLACEHOLDER,
        )
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
    search_planner_supplied_context: Mapping[str, Any] | None = None,
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
        search_planner_supplied_context=dict(
            search_planner_supplied_context or {}
        ),
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
    read_assessment_decision: str | None = None
    read_assessment_calls: list[dict[str, Any]] = field(default_factory=list)
    read_transport_calls: list[str] = field(default_factory=list)
    run_kernel: Any | None = field(default=None, init=False, repr=False)
    read_candidate_packet: dict[str, Any] | None = field(
        default=None, init=False, repr=False
    )
    read_query_plan: Any | None = field(default=None, init=False, repr=False)
    read_discovery_result_store: Any | None = field(
        default=None, init=False, repr=False
    )
    full_search_judgment_inputs: list[dict[str, Any]] = field(
        default_factory=list, init=False, repr=False
    )

    def _record_model_call(self, system_prompt: str, kwargs: Mapping[str, Any]) -> None:
        self.model_calls.append(
            {
                "system_prompt": system_prompt,
                "stream": bool(kwargs.get("stream")),
                "provider": kwargs.get("provider"),
                "model": kwargs.get("model"),
                "use_reasoning": kwargs.get("use_reasoning"),
            }
        )

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        self._record_model_call(system_prompt, kwargs)
        if system_prompt == SEARCHOS_JUDGMENT_SYSTEM_PROMPT:
            payload = json.loads(prompt)
            options = list(payload.get("candidate_use_options") or [])
            custody_refs = list(payload.get("read_custody_refs") or [])
            self.read_assessment_calls.append(
                {
                    "slot_id": dict(payload.get("slot_ref") or {}).get("slot_id"),
                    "binding_ids": [
                        dict(item.get("candidate_use_option_ref") or {}).get("candidate_use_option_id")
                        for item in options
                    ],
                    "cost_phase": kwargs.get("cost_phase"),
                }
            )
            common = {
                "schema_version": "searchos_judgment_decision_v1",
                "judgment_request_id": payload["judgment_request_id"],
                "judgment_request_digest": payload["judgment_request_digest"],
                "slot_id": dict(payload["slot_ref"])["slot_id"],
            }
            if self.read_assessment_decision == "MALFORMED":
                return "not-json"
            if self.read_assessment_decision == "WRAPPED_JSON":
                return "Decision follows: " + json.dumps(
                    {
                        **common,
                        "action": "HANDOFF_UNRESOLVED",
                        "reason": "must_not_be_repaired",
                    }
                )
            if self.read_assessment_decision == "NO_READ":
                return json.dumps(
                    {
                        **common,
                        "action": "HANDOFF_UNRESOLVED",
                        "reason": "offline_no_read",
                    }
                )
            if (
                self.read_assessment_decision == "FOLLOWUP_THEN_READ"
                and len(self.read_assessment_calls) == 1
                and not custody_refs
            ):
                return json.dumps(
                    {
                        **common,
                        "action": "PROPOSE_FOLLOWUP_QUERY",
                        "followup_query": ("Alpha exact model-authored follow-up query"),
                        "reason": "offline_followup_needed",
                    }
                )
            if self.read_assessment_decision == "REQUEST_FIRST_THEN_NO_READ" and len(self.read_assessment_calls) > 1:
                return json.dumps(
                    {
                        **common,
                        "action": "HANDOFF_UNRESOLVED",
                        "reason": "offline_no_later_read",
                    }
                )
            if self.read_assessment_decision == "INVALID_NOMINATION":
                invalid_ref = dict(dict(options[0])["candidate_use_option_ref"])
                invalid_ref["candidate_use_option_id"] = "not-an-eligible-option"
                return json.dumps(
                    {
                        **common,
                        "action": "REQUEST_READ_PAGE",
                        "candidate_use_option_ref": invalid_ref,
                        "reason": "offline_invalid_nomination",
                    }
                )
            if custody_refs:
                return json.dumps(
                    {
                        **common,
                        "action": ("HANDOFF_CURRENT_MATERIAL_FOR_SEMANTIC_EVALUATION"),
                        "read_custody_refs": custody_refs,
                        "reason": "offline_read_material_ready",
                    }
                )
            if options:
                return json.dumps(
                    {
                        **common,
                        "action": "REQUEST_READ_PAGE",
                        "candidate_use_option_ref": dict(dict(options[0])["candidate_use_option_ref"]),
                        "reason": "offline_request_page",
                    }
                )
            return json.dumps(
                {
                    **common,
                    "action": "HANDOFF_UNRESOLVED",
                    "reason": "offline_no_candidates",
                }
            )
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_ANALYST]:
            payload = json.loads(prompt)
            question = str(dict(payload.get("component_ref") or {}).get("user_facing_question") or self.core_topic)
            return json.dumps(
                {
                    "claim_text": "Offline supported finding for " + question,
                    "support_status": "supported",
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            )
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME]:
            return json.dumps(
                {
                    "validation_status": "supported",
                    "reasons": ["Offline exact READ material supports the finding."],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            )
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            payload = json.loads(prompt)
            component_ids = [
                str(item.get("component_id") or "")
                for item in payload.get("component_nodes") or ()
                if isinstance(item, Mapping) and item.get("component_id")
            ]
            return json.dumps(
                {
                    "synthesis_proposals": [
                        {
                            "synthesis_key": "S",
                            "claim_text": "Offline admitted component findings form the requested synthesis.",
                            "relationship_type": "requested_synthesis",
                            "component_inputs": component_ids,
                            "synthesis_inputs": [],
                            "caveats": [],
                            "nonclaims": [],
                            "blockers": [],
                        }
                    ]
                }
            )
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME]:
            return json.dumps(
                {
                    "validation_status": "supported",
                    "reasons": ["Offline admitted inputs support the synthesis."],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                }
            )
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SCRUTINEER]:
            return json.dumps(
                {
                    "challenge_status": "passed",
                    "reasons": ["Offline full case is coherent."],
                    "challenged_synthesis_keys": [],
                    "caveats": [],
                    "nonclaims": [],
                }
            )
        if system_prompt == SEARCH_JUDGMENT_READ_SYSTEM_PROMPT:
            payload = json.loads(prompt)
            bindings = list(payload.get("eligible_bindings") or [])
            self.read_assessment_calls.append(
                {
                    "slot_id": payload.get("assessment_unit", {}).get("slot_id"),
                    "binding_ids": [item.get("binding_id") for item in bindings],
                    "cost_phase": kwargs.get("cost_phase"),
                }
            )
            if self.read_assessment_decision == "NO_READ":
                return json.dumps(
                    {
                        "schema_version": (
                            "search_judgment_read_assessment_decision_v1"
                        ),
                        "decision": "NO_READ",
                        "reason_code": "offline_no_read",
                    }
                )
            if self.read_assessment_decision == "REQUEST_READ_PAGE" and bindings:
                return json.dumps(
                    {
                        "schema_version": (
                            "search_judgment_read_assessment_decision_v1"
                        ),
                        "decision": "REQUEST_READ_PAGE",
                        "nominated_binding_id": bindings[0]["binding_id"],
                        "reason_code": "offline_request_page",
                    }
                )
            if (
                self.read_assessment_decision == "REQUEST_FIRST_THEN_NO_READ"
                and bindings
            ):
                if len(self.read_assessment_calls) == 1:
                    return json.dumps(
                        {
                            "schema_version": (
                                "search_judgment_read_assessment_decision_v1"
                            ),
                            "decision": "REQUEST_READ_PAGE",
                            "nominated_binding_id": bindings[0]["binding_id"],
                            "reason_code": "offline_request_first_page",
                        }
                    )
                return json.dumps(
                    {
                        "schema_version": (
                            "search_judgment_read_assessment_decision_v1"
                        ),
                        "decision": "NO_READ",
                        "reason_code": "offline_no_later_read",
                    }
                )
            if self.read_assessment_decision == "INVALID_NOMINATION":
                return json.dumps(
                    {
                        "schema_version": (
                            "search_judgment_read_assessment_decision_v1"
                        ),
                        "decision": "REQUEST_READ_PAGE",
                        "nominated_binding_id": "not-an-eligible-binding",
                        "reason_code": "offline_invalid_nomination",
                    }
                )
            if self.read_assessment_decision == "MALFORMED":
                return "not-json"
            if self.read_assessment_decision == "WRAPPED_JSON":
                return (
                    "Decision follows: "
                    + json.dumps(
                        {
                            "schema_version": (
                                "search_judgment_read_assessment_decision_v1"
                            ),
                            "decision": "NO_READ",
                            "reason_code": "must_not_be_repaired",
                        }
                    )
                )
            raise AssertionError("offline READ assessment response unavailable")
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
        discovery_context = kwargs.get("discovery_result_context")
        discovery_store = kwargs.get("discovery_result_store")
        if discovery_context is not None and discovery_store is not None:
            context = dict(discovery_context)
            item_refs = [dict(item) for item in context.get("query_plan_item_refs") or () if isinstance(item, Mapping)]
            if not item_refs:
                raise AssertionError("offline discovery fixture lacks QueryPlan item lineage")
            provider = str(context.get("provider") or "")
            call_ordinal = discovery_store.reserve_provider_call_ordinal()
            discovery_store.note_call(
                returned_count=len(passages),
                admitted_limit=results_per_query,
            )
            lineaged: list[dict[str, Any]] = []
            for rank, raw_passage in enumerate(passages[:results_per_query], start=1):
                item_ref = item_refs[(rank - 1) % len(item_refs)]
                result_context = {
                    **context,
                    "query_plan_item_ref": item_ref,
                    "query_role": item_ref.get("query_plan_role"),
                }
                passage = dict(raw_passage)
                identity = discovery_store.admit_result(
                    context=result_context,
                    provider=provider,
                    call_ordinal=call_ordinal,
                    result_rank=rank,
                    result=passage,
                    material_text=str(passage.get("text") or ""),
                    material_class="provider_returned_discovery_material",
                )
                if identity is None:
                    continue
                passage["source_result_ref"] = identity.ref()
                passage["source_material_ref"] = dict(identity.material_ref)
                passage["source_result_material_class"] = identity.material_class
                passage["source_result_material_digest"] = identity.material_digest
                passage["provider_call_ordinal"] = identity.provider_call_ordinal
                passage["provider_rank_or_position"] = identity.result_rank
                passage["query_digest"] = identity.query_digest
                passage["normalized_url"] = identity.normalized_url
                passage["url"] = identity.normalized_url
                lineaged.append(passage)
            passages = lineaged
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
        from core.cost_accounting import estimate_tokens
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
        text = str(output_text or "")
        return StrictOneShotModelTransportResult(
            return_code=0,
            output_text=text,
            canonical_provider=canonical_provider,
            configured_model=model,
            provider_request_attempt_count=1,
            provider_request_succeeded=True,
            provider_request_failed=False,
            provider_response_received=True,
            input_tokens=estimate_tokens(prompt) + estimate_tokens(system_prompt),
            output_tokens=estimate_tokens(text),
            usage_observed=False,
            usage_estimated=True,
        )

    def deps(self) -> RunDeps:
        def offline_tavily_extract(payload: dict[str, Any]) -> dict[str, Any]:
            requested = payload.get("urls")
            requested_url = str(requested[0]) if isinstance(requested, list) else str(requested or "")
            self.read_transport_calls.append(requested_url)
            return {
                "results": [
                    {
                        "url": requested_url,
                        "attempted_url": requested_url,
                        "title": "Offline exact READ source",
                        "raw_content": ("Offline exact-URL readable source material for " + requested_url),
                    }
                ],
                "failed_results": [],
            }

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
            provider_availability={"tavily": True},
            search_planner_adapter=DeterministicSearchPlannerAdapter(),
            searchos_read_acquisition_transports=AcquisitionTransports(tavily_extract=offline_tavily_extract),
        )


@dataclass
class PostRetirementOrdinaryPipelineHarness(OfflineOrdinaryPipelineHarness):
    """Current ordinary pipeline fixture with a fail-closed Economist sentinel."""

    router_report_type: str = "general_research"
    router_query_type: str = "other"
    router_entities: Sequence[str] | None = None
    healthy: bool = True
    evidence_rows: Sequence[Mapping[str, Any]] | None = None
    install_economist_sentinel: bool = True
    analyst_prompts: list[str] = field(default_factory=list)
    analyst_calls: int = 0
    economist_calls: list[str] = field(default_factory=list)

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt == DEFAULT_SYSTEM["router"]:
            self._record_model_call(system_prompt, kwargs)
            entities = list(self.router_entities or (self.primary_entity,))
            return json.dumps(
                {
                    "intent": "general",
                    "report_type": self.router_report_type,
                    "image_mode": "none",
                    "core_topic": self.core_topic,
                    "is_academic": False,
                    "query_type": self.router_query_type,
                    "entities": entities,
                    "primary_entity": self.primary_entity,
                }
            )
        if system_prompt == DEFAULT_SYSTEM["analyst"]:
            self.analyst_calls += 1
            self.analyst_prompts.append(prompt)
        if system_prompt.startswith("You are a ruthless fact-checker"):
            self._record_model_call(system_prompt, kwargs)
            return json.dumps({"flags": []})
        return super().ask_model(prompt, system_prompt, **kwargs)

    def build_search_passages(self) -> list[dict[str, Any]]:
        if self.evidence_rows is not None:
            rows = self.evidence_rows
        elif self.healthy:
            entities = list(self.router_entities or (self.primary_entity,))
            names = [entities[(index - 1) % len(entities)] for index in range(1, 5)]
            rows = [
                {
                    "title": f"{name} official operating report",
                    "url": f"https://{name.casefold()}.example/report-{index}",
                    "text": (
                        f"The current official {name} operating rate is "
                        f"{index + 10} units per hour."
                    ),
                    "credibility": 4,
                    "source_tier": "official",
                    "source_class": "primary_source_documents",
                    "currentness_signal": "current",
                    "readable_status": "readable",
                    "disposition": "accepted",
                }
                for index, name in enumerate(names, 1)
            ]
        else:
            rows = [
                {
                    "title": f"Unrelated general news {index}",
                    "url": f"https://apnews.com/article/unrelated-{index}",
                    "text": f"Unrelated Gadget general news excerpt {index}.",
                    "credibility": 1,
                    "source_tier": "unknown",
                }
                for index in range(1, 5)
            ]

        passages: list[dict[str, Any]] = []
        for index, raw_row in enumerate(rows, 1):
            row = dict(raw_row)
            row.setdefault("source_id", index)
            row.setdefault("score", 1.0 - ((index - 1) * 0.01))
            row.setdefault("credibility", 3 if self.healthy else 1)
            row.setdefault("source_tier", "official" if self.healthy else "unknown")
            row.setdefault("_provider", "offline_fake_search")
            passages.append(row)
        return passages

    def forbidden_legacy_economist(self, *_args: Any, **_kwargs: Any) -> str:
        self.economist_calls.append("called")
        raise AssertionError("retired legacy Economist was invoked")

    def deps(self) -> RunDeps:
        deps = super().deps()
        return replace(
            deps,
            QUANT_REPORT_TYPES={"quantitative_comparison", "benchmark"},
            run_economist_step=(
                self.forbidden_legacy_economist
                if self.install_economist_sentinel
                else None
            ),
        )

    @property
    def model_system_prompts(self) -> list[str]:
        return [str(call["system_prompt"]) for call in self.model_calls]


def execution_event_from_log(path: Path) -> dict[str, Any]:
    return next(
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("event") == "execution"
    )


def run_post_retirement_ordinary_pipeline(
    tmp_path: Path,
    monkeypatch: Any,
    *,
    mode: str = "Balanced",
    report_type: str = "general_research",
    query_type: str = "other",
    healthy: bool = True,
    forced_corpus_state: str | None = None,
    evidence_rows: Sequence[Mapping[str, Any]] | None = None,
    query: str = "Compare Alpha and Beta operating rates using current evidence.",
    core_topic: str = "Alpha and Beta operating rates",
    primary_entity: str = "Alpha",
    router_entities: Sequence[str] | None = None,
    researcher_queries: Sequence[str] | None = None,
    analyst_response: str = "The retrieved evidence supports a bounded comparison.",
    raw_author_response: str = (
        "The evidence supports a bounded qualitative comparison. "
        "[[1]](https://alpha.example/report-1)"
    ),
    install_economist_sentinel: bool = True,
    current_date: str = "2026-05-06",
    cap_policy: Any | None = None,
    deps_overrides: Mapping[str, Any] | None = None,
    environment_overrides: Mapping[str, str] | None = None,
    read_assessment_decision: str | None = None,
    harness_sink: list[PostRetirementOrdinaryPipelineHarness] | None = None,
) -> tuple[Any, PostRetirementOrdinaryPipelineHarness]:
    scrub_offline_runtime(monkeypatch)
    for key, value in (environment_overrides or {}).items():
        monkeypatch.setenv(key, value)
    if router_entities is None and query_type == "comparison":
        router_entities = ("Alpha", "Beta")
    harness = PostRetirementOrdinaryPipelineHarness(
        tmp_path=tmp_path,
        query=query,
        core_topic=core_topic,
        primary_entity=primary_entity,
        researcher_queries=researcher_queries,
        analyst_response=analyst_response,
        raw_author_response=raw_author_response,
        router_report_type=report_type,
        router_query_type=query_type,
        router_entities=router_entities,
        healthy=healthy,
        evidence_rows=evidence_rows,
        install_economist_sentinel=install_economist_sentinel,
        read_assessment_decision=read_assessment_decision,
    )
    if harness_sink is not None:
        harness_sink.append(harness)
    original_read_runtime = orchestrator.execute_searchos_slice_a_iterative_judgment

    def capture_read_runtime(**kwargs: Any) -> Any:
        harness.run_kernel = kwargs["run_kernel"]
        harness.read_candidate_packet = dict(kwargs["candidate_packet"])
        harness.read_query_plan = kwargs["query_authority"].plan
        harness.read_discovery_result_store = kwargs["discovery_result_store"]
        return original_read_runtime(**kwargs)

    monkeypatch.setattr(
        orchestrator,
        "execute_searchos_slice_a_iterative_judgment",
        capture_read_runtime,
    )
    original_full_judgment_input = (
        orchestrator.build_search_judgment_input_from_runtime
    )

    def capture_full_judgment_input(*args: Any, **kwargs: Any) -> Any:
        result = original_full_judgment_input(*args, **kwargs)
        harness.full_search_judgment_inputs.append(result.to_dict())
        return result

    monkeypatch.setattr(
        orchestrator,
        "build_search_judgment_input_from_runtime",
        capture_full_judgment_input,
    )
    config = replace(
        offline_balanced_run_config(
            query=query,
            current_date=current_date,
            session_id=f"session-{mode.casefold()}",
            run_id=f"run-{mode.casefold()}",
            cap_policy=cap_policy,
        ),
        mode=mode,
        forced_corpus_state=(
            forced_corpus_state
            if forced_corpus_state is not None
            else (None if healthy else "off_topic")
        ),
        include_domains=["alpha.example"],
        exclude_domains=["blocked.example"],
    )
    deps = harness.deps()
    if deps_overrides:
        deps = replace(deps, **dict(deps_overrides))
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET,),
    )
    outcome = orchestrator.run_pipeline(
        config,
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )
    harness.run_kernel = captured.get("run_kernel") or harness.run_kernel
    return outcome, harness


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
    ordinary_live_source_acquisition_transports: Any | None = None,
    provider_availability: Mapping[str, object] | None = None,
    ordinary_live_source_custody_anchor_groups: Sequence[Any] = (),
    enable_ordinary_live_semantic_coverage: bool = False,
    enable_ordinary_live_authority_consolidation: bool = False,
    enable_ordinary_live_main_runkernel_coverage: bool = False,
) -> tuple[dict[str, Any], Any]:
    captured = install_handoff_capture(monkeypatch, capture_stages=capture_stages)
    deps = harness.deps()
    if ordinary_live_source_fetch_read is not None:
        if ordinary_live_source_acquisition_transports is not None:
            raise ValueError(
                "test helper accepts either a typed transport or legacy fixture, not both"
            )

        def offline_linkup_fetch(payload: dict[str, Any]) -> dict[str, Any]:
            source_url = str(payload.get("url") or "")
            candidate = {
                "title": "Offline selected candidate",
                "url": source_url,
                "domain": source_url.split("/", 3)[2] if "://" in source_url else "",
            }
            raw = ordinary_live_source_fetch_read(
                candidate=candidate,
                source_url=source_url,
                source_candidate_ref={"url": source_url},
            )
            material = dict(raw) if isinstance(raw, Mapping) else {}
            material.setdefault(
                "markdown",
                material.get("sanitized_text") or material.get("readable_text"),
            )
            return material

        deps = replace(
            deps,
            ordinary_live_source_acquisition_transports=AcquisitionTransports(
                linkup_fetch=offline_linkup_fetch
            ),
        )
    if ordinary_live_source_acquisition_transports is not None:
        deps = replace(
            deps,
            ordinary_live_source_acquisition_transports=(
                ordinary_live_source_acquisition_transports
            ),
        )
    if provider_availability is None and (
        ordinary_live_source_fetch_read is not None
        or ordinary_live_source_acquisition_transports is not None
    ):
        provider_availability = {"linkup": True, "tavily": True}
    if provider_availability is not None:
        deps = replace(deps, provider_availability=dict(provider_availability))
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
