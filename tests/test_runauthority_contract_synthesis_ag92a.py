from __future__ import annotations

import json
import sys
import types
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.evidence_ledger import build_evidence_ledger_observation_from_run_contract
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.query_plan import QUERY_PLAN_TRACE_KEY
from core.query_plan_runtime_adapter import build_query_plan_runtime_adapter

_search_providers_stub = types.ModuleType("core.search_providers")
_search_providers_stub.brave_reconnaissance = lambda *_args, **_kwargs: []
sys.modules.setdefault("core.search_providers", _search_providers_stub)

from core.query_production_runtime import (
    execute_query_plan_admission_action,
    execute_query_production_action,
    query_plan_admission_inputs_from_query_production_projection,
)
from core.router_query_preparation_contract import build_router_query_preparation_state
from core.run_authority_contract import (
    ContractSynthesisMode,
    ContractSynthesisStatus,
    RunContractRequirementKind,
)
from core.run_authority_contract_prompt import RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT
from core.run_authority_contract_runtime import execute_run_contract_synthesis_action
from core.run_authority_contract_templates import (
    ACADEMIC_LITERATURE,
    CANONICAL_TECHNICAL_DOCS,
    CONFLICT_SENSITIVE,
    CURRENT_OFFICIAL_NUMERIC_OR_RULE,
    INDIRECT_INFERENCE,
    LEGAL_OR_REGULATORY_CURRENT_PRIMARY,
    ORDINARY_EXPLAINER,
    USER_DOCUMENT_OR_PERSONAL_CORPUS,
    build_deterministic_contract,
)
from core.run_kernel import (
    EVIDENCE_LEDGER_STAGE,
    QUERY_PLAN_ADMISSION_STAGE,
    QUERY_PRODUCTION_STAGE,
    RUN_CONTRACT_STAGE,
    ActionType,
    ObservationType,
    RunKernel,
)

ROOT = Path(__file__).resolve().parents[1]


def _clean_query(value: str) -> str:
    return " ".join(str(value or "").split())[:300]


class _Status:
    def __init__(self) -> None:
        self.steps: list[str] = []

    def step(self, message: str) -> None:
        self.steps.append(message)


class _Logger:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, Exception]] = []

    def warning(self, message: str, error: Exception) -> None:
        self.warnings.append((message, error))


def _router_state(query: str, *, intent: str = "general", query_type: str = "rule") -> Any:
    return build_router_query_preparation_state(
        query=query,
        router_text=json.dumps(
            {
                "intent": intent,
                "report_type": "general_research",
                "query_type": query_type,
                "core_topic": query,
                "primary_entity": "Acme",
                "entities": ["Acme"],
                "is_academic": False,
            }
        ),
    )


def _query_runtime_kwargs(query: str, *, run_contract_projection: dict[str, Any]) -> dict[str, Any]:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return '{"queries":["current official rule","effective date"]}'

    return {
        "router_query_preparation_contract": _router_state(query),
        "query": query,
        "strategy": "Balanced",
        "current_date": "June 9, 2026",
        "focus_academic": False,
        "force_intent_news": False,
        "include_domains": [],
        "news_preferred_domains": ["reuters.com"],
        "ask_model": ask_model,
        "clean_json_response": lambda text: text,
        "default_system": {
            "researcher": "researcher-system",
            "recon_query_rewriter": "recon-system",
        },
        "fast_provider": "fast-provider",
        "fast_model": "fast-model",
        "local_url": "http://local",
        "api_key": None,
        "use_reasoning": True,
        "measure_context_stage": lambda *_args, **_kwargs: None,
        "clean_query": _clean_query,
        "cost_accumulator": object(),
        "status": _Status(),
        "provider_diagnostics": [],
        "run_log": _Logger(),
        "waste_flags": [],
        "brave_api_key_available": False,
        "brave_reconnaissance_func": lambda *_args, **_kwargs: [],
        "run_contract_projection": run_contract_projection,
    }


def _contract_projection(
    query: str = "What is the current official filing fee for Form I-130?",
    *,
    mode: str = "Balanced",
) -> dict[str, Any]:
    return build_deterministic_contract(query=query, mode=mode).to_projection()


def _requirement_by_kind(
    projection: dict[str, Any],
    kind: RunContractRequirementKind | str,
) -> dict[str, Any]:
    raw_kind = kind.value if isinstance(kind, RunContractRequirementKind) else str(kind)
    for requirement in projection["source_requirements"]:
        if requirement["requirement_kind"] == raw_kind:
            return requirement
    raise AssertionError(f"missing requirement kind {raw_kind}")


def _final_passage() -> dict[str, Any]:
    return {
        "source_id": "S1",
        "url": "https://official.example/rule",
        "title": "Official rule",
        "text": "The current rule is listed here.",
        "source_tier": "official",
        "source_class": "official_current_rules",
    }


def test_run_kernel_authorizes_reduces_contract_and_sanitizes_projection() -> None:
    kernel = RunKernel.start(run_id="ag92a-run", request_id="request")

    action = kernel.authorize_run_contract_synthesis(inputs={"query_length": 56})
    result = execute_run_contract_synthesis_action(
        action,
        query="What is the current official filing fee for Form I-130?",
        mode="Balanced",
        current_date="June 9, 2026",
        route_projection={"intent": "general", "query_type": "rule"},
    )
    kernel.reduce(result.observation)

    assert action.action_type is ActionType.RUN_CONTRACT_SYNTHESIZE
    assert action.stage == RUN_CONTRACT_STAGE
    assert action.expected_observation_type is ObservationType.RUN_CONTRACT_SYNTHESIZED
    projection = kernel.state.run_contract_projection
    assert projection["owner"] == "RunKernel.RunAuthorityContract"
    assert projection["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["storage_only"] is False
    assert CURRENT_OFFICIAL_NUMERIC_OR_RULE in projection["selected_template_ids"]
    assert projection["query_ref"]["query_length"] > 0
    assert "What is the current" not in json.dumps(projection)
    assert projection["prompt_hash"] is None
    assert projection["prompt_text_retained"] is False
    assert projection["model_response_text_retained"] is False
    assert kernel.state.to_trace_projection().to_dict()["run_contract_projection"][
        "contract_id"
    ] == projection["contract_id"]


@pytest.mark.parametrize(
    ("query", "expected_template", "expected_kind", "strictness"),
    [
        (
            "What is the current official filing fee?",
            CURRENT_OFFICIAL_NUMERIC_OR_RULE,
            RunContractRequirementKind.OFFICIAL_CURRENT,
            "required",
        ),
        (
            "What is the current California legal deadline to appeal?",
            LEGAL_OR_REGULATORY_CURRENT_PRIMARY,
            RunContractRequirementKind.LEGAL_PRIMARY,
            "required",
        ),
        (
            "What is the current OpenAI Responses API parameter?",
            CANONICAL_TECHNICAL_DOCS,
            RunContractRequirementKind.CANONICAL_DOCS,
            "required",
        ),
        (
            "Summarize the benchmark paper evidence for this method",
            ACADEMIC_LITERATURE,
            RunContractRequirementKind.ACADEMIC,
            "required",
        ),
        (
            "Explain why plants need sunlight",
            ORDINARY_EXPLAINER,
            RunContractRequirementKind.REPUTABLE_SECONDARY,
            "preferred",
        ),
        (
            "Based on my uploaded document, summarize the warranty",
            USER_DOCUMENT_OR_PERSONAL_CORPUS,
            RunContractRequirementKind.USER_DOCUMENT,
            "required",
        ),
    ],
)
def test_deterministic_templates_select_expected_obligations(
    query: str,
    expected_template: str,
    expected_kind: RunContractRequirementKind,
    strictness: str,
) -> None:
    projection = build_deterministic_contract(query=query, mode="Balanced").to_projection()

    assert expected_template in projection["selected_template_ids"]
    requirement = _requirement_by_kind(projection, expected_kind)
    assert requirement["strictness"] == strictness
    if expected_template == ORDINARY_EXPLAINER:
        assert not any(
            item["requirement_kind"] == RunContractRequirementKind.OFFICIAL_CURRENT.value
            and item["strictness"] == "required"
            for item in projection["source_requirements"]
        )


def test_indirect_and_conflict_templates_preserve_special_postures() -> None:
    indirect = build_deterministic_contract(
        query="Can we infer market share from the sourced revenue numbers?",
        mode="Balanced",
    ).to_projection()
    conflict = build_deterministic_contract(
        query="Compare conflicting reports about the official launch status",
        mode="Balanced",
    ).to_projection()

    assert INDIRECT_INFERENCE in indirect["selected_template_ids"]
    assert indirect["inference_policy"]["policy"] == "inferred_from_sourced_premises_allowed"
    assert "do_not_launder_inference_as_direct_source_claim" in indirect["final_posture_policy"][
        "prohibited_upgrades"
    ]
    assert CONFLICT_SENSITIVE in conflict["selected_template_ids"]
    assert conflict["conflict_policy"]["preserve"] is True
    assert conflict["conflict_policy"]["block_overconfident_claim"] is True


def test_smart_model_contract_is_parsed_validated_and_committed() -> None:
    query = "What is the current official filing fee for Form I-130?"
    deterministic = build_deterministic_contract(query=query, mode="Deep").to_projection()
    model_contract = deepcopy(deterministic)
    model_contract["contract_id"] = "model-ag92a-contract"
    model_contract["synthesis_mode"] = ContractSynthesisMode.SMART_MODEL_ADAPTED.value
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_ask_model(*args: Any, **kwargs: Any) -> str:
        calls.append((args, kwargs))
        return json.dumps(model_contract)

    kernel = RunKernel.start(run_id="ag92a-smart", request_id="request")
    action = kernel.authorize_run_contract_synthesis(inputs={})
    result = execute_run_contract_synthesis_action(
        action,
        query=query,
        mode="Deep",
        current_date="June 9, 2026",
        route_projection={"query_type": "rule"},
        ask_model=fake_ask_model,
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
        provider="smart-provider",
        model="smart-model",
        effort="medium",
        use_reasoning=True,
    )
    kernel.reduce(result.observation)

    assert calls
    prompt, system_prompt = calls[0][0][:2]
    assert "RUNAUTHORITY CONTRACT SYNTHESIS" in prompt
    assert "strict JSON" in prompt
    assert system_prompt == RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT
    assert calls[0][1]["provider"] == "smart-provider"
    assert calls[0][1]["require_json"] is True
    assert result.validation.status is ContractSynthesisStatus.VALID
    assert (
        kernel.state.run_contract_projection["synthesis_mode"]
        == ContractSynthesisMode.SMART_MODEL_ADAPTED.value
    )
    assert kernel.state.run_contract_projection["contract_id"].startswith("run-contract-")
    assert kernel.state.run_contract_projection["model_identity"]["model"] == "smart-model"
    assert kernel.state.run_contract_projection["prompt_hash"]
    assert "RUNAUTHORITY CONTRACT SYNTHESIS" not in json.dumps(
        kernel.state.to_trace_projection().to_dict()
    )


def test_invalid_model_json_falls_back_without_storing_raw_response() -> None:
    raw_response = "SECRET_RAW_RESPONSE_92A not json"

    def fake_ask_model(*_args: Any, **_kwargs: Any) -> str:
        return raw_response

    kernel = RunKernel.start(run_id="ag92a-fallback", request_id="request")
    action = kernel.authorize_run_contract_synthesis(inputs={})
    result = execute_run_contract_synthesis_action(
        action,
        query="What is the current official filing fee?",
        mode="Balanced",
        current_date="June 9, 2026",
        ask_model=fake_ask_model,
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
        provider="smart-provider",
        model="smart-model",
    )
    kernel.reduce(result.observation)

    assert result.validation.status is ContractSynthesisStatus.FALLBACK
    assert kernel.state.run_contract_projection["synthesis_mode"] == "fallback"
    trace_text = json.dumps(kernel.state.to_trace_projection().to_dict())
    assert raw_response not in trace_text
    assert kernel.state.run_contract_projection["model_response_text_retained"] is False


def test_model_cannot_weaken_strong_source_obligations() -> None:
    query = "What is the current official filing fee for Form I-130?"
    deterministic = build_deterministic_contract(query=query, mode="Balanced").to_projection()
    weakened = deepcopy(deterministic)
    weakened["contract_id"] = "weakened-contract"
    for requirement in weakened["source_requirements"]:
        if requirement["requirement_kind"] in {
            RunContractRequirementKind.OFFICIAL_CURRENT.value,
            RunContractRequirementKind.SOURCE_BOUND_NUMERIC.value,
        }:
            requirement["strictness"] = "contextual"
            requirement["required_source_class"] = "blog_summary"
            requirement["required_source_tier"] = "secondary"
            requirement["required_currentness"] = "not_required"
            requirement["cannot_satisfy_with"] = []

    def fake_ask_model(*_args: Any, **_kwargs: Any) -> str:
        return json.dumps(weakened)

    result = execute_run_contract_synthesis_action(
        RunKernel.start(run_id="ag92a-weaken", request_id="request").authorize_run_contract_synthesis(
            inputs={}
        ),
        query=query,
        mode="Balanced",
        current_date="June 9, 2026",
        ask_model=fake_ask_model,
        clean_json_response=lambda text: text,
        smart_model_enabled=True,
    )
    projection = result.contract.to_projection()
    official = _requirement_by_kind(projection, RunContractRequirementKind.OFFICIAL_CURRENT)
    numeric = _requirement_by_kind(projection, RunContractRequirementKind.SOURCE_BOUND_NUMERIC)

    assert result.validation.status is ContractSynthesisStatus.REPAIRED
    assert official["strictness"] == "required"
    assert official["required_source_class"] == "official_current_rules"
    assert official["required_source_tier"] == "official"
    assert official["required_currentness"] == "current"
    assert numeric["required_source_class"] == "official_current_rules"
    assert "social_signal" in official["cannot_satisfy_with"]
    assert "trusted_community" in official["cannot_satisfy_with"]


def test_lower_tier_evidence_is_context_only_for_stronger_requirements() -> None:
    projection = _contract_projection()
    official = _requirement_by_kind(projection, RunContractRequirementKind.OFFICIAL_CURRENT)

    assert official["allowed_lower_tier_use"] == "leads_or_context_only"
    assert "reputable_secondary" in official["cannot_satisfy_with"]
    assert "social_or_forum" in official["cannot_satisfy_with"]
    assert "community" in official["cannot_satisfy_with"]
    assert "aggregate_count_only" in official["cannot_satisfy_with"]


def test_evidence_ledger_consumes_contract_requirements() -> None:
    projection = _contract_projection()
    kernel = RunKernel.start(run_id="ag92a-ledger", request_id="request")
    action = kernel.authorize_evidence_ledger_reduction(inputs={"source": "contract"})
    observation = build_evidence_ledger_observation_from_run_contract(
        observation_id="ag92a-contract-ledger",
        contract_projection=projection,
    )
    result = execute_evidence_ledger_reduction_action(action, payload=observation.to_dict())
    kernel.reduce(result.observation)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE]["owner"] == "RunKernel.EvidenceLedger"
    assert ledger["requirement_count"] >= 2
    assert any(
        item["origin_ref"].startswith("RunKernel.RunAuthorityContract:")
        for item in ledger["source_requirements"]
    )
    assert "official_current_rules" in {
        item["required_source_class"] for item in ledger["source_requirements"]
    }
    assert any(
        gap["gap_type"] == "missing_official_current_candidate"
        and gap["requirement_id"] == "run_contract:official_current_rules"
        for gap in ledger["custody_gaps"]
    )


def test_answer_contract_handoff_consumes_run_contract_over_aggregate_counts() -> None:
    projection = _contract_projection()
    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query="What is the current official filing fee?",
            evidence_available=True,
            evidence_sufficient=True,
            source_tier_counts={"official": 99, "secondary": 99},
            run_contract_projection=projection,
        )
    )

    assert (
        "official_current_rules"
        in result.state.evidence_state_summary.source_classes_missing
    )
    assert (
        "official_current_rules"
        in result.fulfillment_handoff.unfulfilled_source_classes
    )


def test_final_answer_packet_consumes_contract_into_author_payload() -> None:
    projection = _contract_projection()
    packet = build_final_answer_packet(
        run_id="ag92a-packet",
        final_evidence=[_final_passage()],
        evidence_sufficient=True,
        run_contract_projection=projection,
    )
    payload = packet.to_author_input_payload(
        prompt="Draft the final answer.",
        author_system_prompt_key="author",
        author_effort="medium",
    )

    assert any(
        item["source_class"] == "official_current_rules"
        for item in payload.missing_source_obligations
    )
    assert "Missing or unsatisfied source obligations" in payload.prompt
    assert "official_current_rules" in payload.prompt
    assert "do_not_treat_secondary_or_aggregate_counts" in payload.prompt
    assert payload.prohibited_upgrades
    assert payload.mandatory_caveats


def test_query_production_and_query_plan_receive_contract_hints() -> None:
    query = "What is the current official filing fee?"
    projection = _contract_projection(query)
    kernel = RunKernel.start(run_id="ag92a-query", request_id="request")
    production_action = kernel.authorize_query_production(inputs={})
    production = execute_query_production_action(
        production_action,
        **_query_runtime_kwargs(query, run_contract_projection=projection),
    )
    kernel.reduce(production.observation)

    reduced = kernel.state.projections[QUERY_PRODUCTION_STAGE]
    posture = reduced["effective_route_posture"]
    assert posture["contract_consumed_by_query_production"] is True
    assert posture["run_contract_ref"]["contract_id"] == projection["contract_id"]
    assert production.contract_source_requirement_hints

    query_plan_inputs = query_plan_admission_inputs_from_query_production_projection(
        reduced
    )
    query_authority = build_query_plan_runtime_adapter(
        run_id="ag92a-query",
        primary_entity="Acme",
        entities_list=["Acme"],
        core_topic=query,
        user_query=query,
        intent="general",
        clean=_clean_query,
    )
    admission_action = kernel.authorize_query_plan_admission(inputs={})
    admission = execute_query_plan_admission_action(
        admission_action,
        query_authority=query_authority,
        router_query_preparation_contract=_router_state(query),
        candidate_queries=query_plan_inputs.candidate_queries,
        candidate_source=query_plan_inputs.candidate_source,
        query_type=query_plan_inputs.query_type,
        current_date="June 9, 2026",
        max_queries=3,
        route_runtime_posture=query_plan_inputs.effective_route_posture,
    )
    kernel.reduce(admission.observation)

    assert admission.router_query_preparation_contract.router_source_obligation_hints[
        "source_obligation_seeded_by_run_contract"
    ] is True
    assert admission.router_query_preparation_contract.query_preparation_provenance[
        "run_contract_source_hints_consumed"
    ] is True
    plan = query_authority.to_trace_fragment()[QUERY_PLAN_TRACE_KEY]
    assert any(
        item["origin"] == "run_authority_contract"
        and item["metadata"]["contract_changed_query_order"] is False
        for item in plan["items"]
    )
    assert kernel.state.projections[QUERY_PLAN_ADMISSION_STAGE][
        "contract_source_requirement_hints"
    ]


def test_static_guards_keep_contract_brain_out_of_pipeline() -> None:
    pipeline = (ROOT / "core" / "pipeline_orchestrator.py").read_text()
    runtime = (ROOT / "core" / "run_authority_contract_runtime.py").read_text()
    templates = (ROOT / "core" / "run_authority_contract_templates.py").read_text()
    kernel = (ROOT / "core" / "run_kernel.py").read_text()
    query_runtime = (ROOT / "core" / "query_production_runtime.py").read_text()
    answer_contract = (ROOT / "core" / "answer_contract_runtime_handoff.py").read_text()
    final_adapter = (ROOT / "core" / "final_answer_runtime_adapter.py").read_text()

    assert "execute_run_contract_synthesis_action(" in pipeline
    assert "build_evidence_ledger_observation_from_run_contract(" in pipeline
    assert "run_contract_projection=run_contract_projection" in pipeline
    assert "current_official_numeric_or_rule" not in pipeline
    assert "RUN_AUTHORITY_CONTRACT_SYSTEM_PROMPT" not in pipeline
    assert "RunContractSourceRequirement(" not in pipeline

    assert "ActionType.RUN_CONTRACT_SYNTHESIZE" in runtime
    assert "validate_authorized_action(" in runtime
    assert "ask_model(" in runtime
    assert "RUN_CONTRACT_STAGE" in kernel
    assert "run_contract_projection" in kernel
    assert CURRENT_OFFICIAL_NUMERIC_OR_RULE in templates
    assert LEGAL_OR_REGULATORY_CURRENT_PRIMARY in templates
    assert "contract_source_requirement_hints" in query_runtime
    assert "source_class_facts_from_run_contract_projection" in answer_contract
    assert "run_contract_projection" in final_adapter
