"""Offline proof for Planner semantic compiler + SearchJudgment FAST profile."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from core.run_config import RunConfig
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
    SearchPlannerStrictParseSubtype,
    accept_planner_model_output,
    validate_and_sanitize_model_output,
)
from core.search_planner_model_prompt import (
    SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION,
    SEARCH_PLANNER_RICH_INTERNAL_OUTPUT_SCHEMA,
    build_search_planner_model_prompt,
)
from core.search_planner_semantic_compiler import (
    SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA,
    SearchPlannerSemanticProposalError,
    compile_semantic_planner_proposal,
    count_model_authored_mechanical_identity_keys,
    validate_semantic_planner_proposal,
)
from core.searchos_slice_a_product_runtime import _invoke_judgment_model

REPO_ROOT = Path(__file__).resolve().parents[1]

# Audit baseline from PLANNER-SEMANTIC-COMPILER phase brief.
_BEFORE_STATIC_CONTRACT_CHARS = 17775
_BEFORE_ASSEMBLED_REQUEST_CHARS = 22618


def _estimate_tokens(char_count: int) -> int:
    return max(1, (char_count + 3) // 4)


def _direct_semantic_proposal() -> dict[str, Any]:
    return {
        "interpretation": (
            "Determine the official current threshold and preserve source-bound caveats."
        ),
        "components": [
            {
                "purpose": "user_facing_answer_target",
                "label": "Official threshold",
                "question": (
                    "What is the official current filing threshold for the requested program?"
                ),
                "requirement_posture": "required",
                "acceptance_criteria": [
                    "state the threshold",
                    "bind the answer to an official current source",
                ],
                "support_kinds": ["direct"],
                "materiality": "material",
                "slots": [
                    {
                        "kind": "entity",
                        "status": "explicit",
                        "selected_value": "Example Permit",
                        "materiality": "material",
                    },
                    {
                        "kind": "time_period",
                        "status": "explicit",
                        "selected_value": "2026",
                        "materiality": "material",
                    },
                ],
                "source": {"kind": "official_current", "strictness": "required"},
                "search": {
                    "summary": "Find the official current source for the threshold.",
                    "preferred_source_kinds": ["official"],
                    "recency_requirement": "current for 2026",
                    "primary_query": {
                        "text": "Example Permit official filing threshold 2026",
                        "role": "official_bias",
                    },
                    "recon": {"posture": "not_needed", "dimensions": []},
                },
                "caveats": ["Keep the answer source-bound."],
                "prohibited_upgrades": ["Do not substitute a non-official estimate."],
            }
        ],
        "material_ambiguity": "clear",
        "caveats": ["Report only the source-bound value."],
        "prohibited_upgrades": ["Do not infer a threshold from older years."],
        "assumptions": ["The user asks for the program named in the query."],
    }


def _multicomponent_semantic_proposal() -> dict[str, Any]:
    return {
        "interpretation": (
            "Answer the official threshold using a supporting premise about the program year."
        ),
        "components": [
            {
                "local_id": "premise_year",
                "purpose": "supporting_premise",
                "label": "Program year",
                "question": "Which program year governs the threshold?",
                "requirement_posture": "required",
                "acceptance_criteria": ["identify the governing year"],
                "support_kinds": ["direct"],
                "materiality": "material",
                "slots": [
                    {
                        "kind": "time_period",
                        "status": "explicit",
                        "selected_value": "2026",
                        "materiality": "material",
                    }
                ],
                "source": {"kind": "official_current", "strictness": "required"},
                "search": {
                    "summary": "Confirm the governing program year.",
                    "primary_query": {
                        "text": "Example Permit program year 2026",
                        "role": "recency",
                    },
                    "recon": {"posture": "not_needed", "dimensions": []},
                },
            },
            {
                "local_id": "threshold",
                "purpose": "user_facing_answer_target",
                "label": "Official threshold",
                "question": "What is the official threshold for that year?",
                "requirement_posture": "required",
                "acceptance_criteria": ["state the threshold"],
                "support_kinds": ["inferred"],
                "max_inference_depth": 1,
                "depends_on": ["premise_year"],
                "materiality": "material",
                "slots": [
                    {
                        "kind": "metric",
                        "status": "explicit",
                        "selected_value": "filing threshold",
                        "materiality": "material",
                    }
                ],
            },
        ],
        "material_ambiguity": "clear",
    }


def _ambiguity_currentness_proposal() -> dict[str, Any]:
    return {
        "interpretation": (
            "Resolve which Example Permit variant is intended before answering the current fee."
        ),
        "components": [
            {
                "purpose": "user_facing_answer_target",
                "label": "Current fee",
                "question": "What is the current official fee for the intended Example Permit?",
                "requirement_posture": "required",
                "acceptance_criteria": ["state the current fee"],
                "support_kinds": ["direct"],
                "materiality": "material",
                "slots": [
                    {
                        "kind": "variant",
                        "status": "ambiguous",
                        "materiality": "material",
                        "candidate_values": ["standard", "expedited"],
                    }
                ],
                "source": {"kind": "date_bound_currentness", "strictness": "required"},
                "search": {
                    "summary": "Find the current official fee schedule.",
                    "preferred_source_kinds": ["official"],
                    "recency_requirement": "current as of today",
                    "primary_query": {
                        "text": "Example Permit current official fee schedule",
                        "role": "recency",
                    },
                    "recon": {"posture": "not_needed", "dimensions": []},
                },
            }
        ],
        "material_ambiguity": "material_variant_ambiguity",
        "caveats": ["Do not silently pick a variant."],
    }


def _planner_input_mapping() -> dict[str, Any]:
    return {
        "run_id": "run-planner-semantic-01",
        "request_id": "req-planner-semantic-01",
        "requested_mode": "balanced",
        "user_query_text_for_planning": (
            "What is the Example Permit filing threshold for 2026?"
        ),
        "user_query_ref": {"ref": "query"},
        "safe_context": {"source_policy": "official-current"},
        "route_context_ref": {"route_ref": "safe-route-ref"},
        "run_context_ref": {"run_ref": "safe-run-ref"},
        "parent_contract_refs": [],
        "closed_surface_flags": {},
    }


def test_direct_factual_semantic_proposal_compiles_to_rich_authority() -> None:
    semantic = _direct_semantic_proposal()
    assert count_model_authored_mechanical_identity_keys(semantic) == 0
    rich = accept_planner_model_output(semantic)
    component = rich["answer_components"][0]
    assert component["requirement_posture"] == "required"
    assert component["allowed_support_kinds"] == ["direct"]
    assert component["max_inference_depth"] == 0
    assert len(component["source_obligation_candidate_ids"]) == 1
    obligation = rich["source_obligation_candidates"][0]
    assert obligation["obligation_kind"] == "official_current"
    assert obligation["strictness"] == "required"
    requirement = rich["component_search_requirements"][0]
    strategies = requirement["metadata"]["query_strategy_candidates"]
    assert len(strategies) == 1
    assert strategies[0]["candidate_kind"] == "primary"
    assert strategies[0]["candidate_query_text"] == (
        "Example Permit official filing threshold 2026"
    )
    assert strategies[0]["strategy_id"].startswith("strategy:")
    assert strategies[0]["recon_requirement"] == {
        "posture": "not_needed",
        "unresolved_dimension_ids": [],
        "candidate_queries": [],
        "required_for_truthful_targeting": False,
    }
    assert component["component_id"].startswith("component:")
    assert component["component_revision"] == "1"


def test_multicomponent_inferred_dependency_compile() -> None:
    rich = accept_planner_model_output(_multicomponent_semantic_proposal())
    by_label = {
        item["user_facing_label"]: item for item in rich["answer_components"]
    }
    premise = by_label["Program year"]
    target = by_label["Official threshold"]
    assert premise["allowed_support_kinds"] == ["direct"]
    assert target["allowed_support_kinds"] == ["inferred"]
    assert target["max_inference_depth"] == 1
    assert target["dependency_component_ids"] == [premise["component_id"]]
    assert target.get("source_obligation_candidate_ids") in ([], None)
    owned_requirements = [
        item
        for item in rich["component_search_requirements"]
        if item["component_id"] == target["component_id"]
    ]
    assert owned_requirements == []


def test_ambiguity_and_currentness_preserved_after_compile() -> None:
    rich = accept_planner_model_output(_ambiguity_currentness_proposal())
    assert rich["material_ambiguity_posture"] == "material_variant_ambiguity"
    slot = rich["semantic_slots"][0]
    assert slot["status"] == "ambiguous"
    assert slot["user_confirmation_required"] is True
    obligation = rich["source_obligation_candidates"][0]
    assert obligation["obligation_kind"] == "date_bound_currentness"
    requirement = rich["component_search_requirements"][0]
    assert requirement["recency_requirement"] == "current as of today"
    assert "official" in requirement["preferred_source_kinds"]


def test_compiler_determinism() -> None:
    semantic = validate_semantic_planner_proposal(_direct_semantic_proposal())
    first = compile_semantic_planner_proposal(semantic)
    second = compile_semantic_planner_proposal(semantic)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_rich_validator_still_receives_compiled_output() -> None:
    compiled = compile_semantic_planner_proposal(_direct_semantic_proposal())
    sanitized = validate_and_sanitize_model_output(compiled)
    assert sanitized["answer_components"]
    assert sanitized["source_obligation_candidates"]
    assert sanitized["component_search_requirements"]


def test_no_model_authored_mechanical_identities() -> None:
    for payload in (
        _direct_semantic_proposal(),
        _multicomponent_semantic_proposal(),
        _ambiguity_currentness_proposal(),
    ):
        assert count_model_authored_mechanical_identity_keys(payload) == 0


def test_pr551_parse_diagnostics_remain_intact() -> None:
    calls: list[dict[str, Any]] = []

    def fake_ask(
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        calls.append(kwargs)
        sink = kwargs.get("safe_response_envelope_sink")
        if callable(sink):
            sink({"provider_completion_posture": "completed"})
        return '{"interpretation":'

    adapter = SearchPlannerModelAdapter(
        ask_model=fake_ask,
        provider="OpenAI",
        model="gpt-5.4-mini",
        effort="medium",
        enabled=True,
        licensed=True,
    )
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        adapter.produce(_planner_input_mapping())
    error = caught.value
    assert error.failure_code.value == "INVALID_JSON"
    assert error.strict_parse_subtype == SearchPlannerStrictParseSubtype.JSON_DECODE_ERROR
    assert error.provider_completion_posture.value == "completed"
    assert error.cleaner_modified is False
    assert calls and calls[0]["require_json"] is True


def test_semantically_invalid_proposal_uses_canonical_adapter_failure() -> None:
    proposal = _direct_semantic_proposal()
    proposal["components"][0]["support_kinds"] = ["not_a_kind"]
    marker = "LEAKED_MODEL_VALUE_not_a_kind"
    proposal["interpretation"] = marker

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(proposal)
    error = caught.value
    assert not isinstance(error.__cause__, ValueError)
    assert error.__cause__ is None
    assert error.failure_code.value == "INVALID_SEMANTIC_PROPOSAL"
    assert error.predicate_id is not None
    assert error.predicate_id.name == "SEMANTIC_PROPOSAL_VALIDATION_FAILED"
    assert error.mechanical_rule_id == "M02"
    assert error.failure_stage.name == "MODEL_OUTPUT_VALIDATION"
    message = str(error)
    assert message == "search planner semantic proposal failed closed"
    assert marker not in message
    assert "not_a_kind" not in message
    assert "raw_" not in message.lower()
    assert "secret" not in message.lower()


def test_inferred_support_requires_explicit_max_inference_depth() -> None:
    proposal = _multicomponent_semantic_proposal()
    del proposal["components"][1]["max_inference_depth"]

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(proposal)
    error = caught.value
    assert error.failure_code.value == "INVALID_SEMANTIC_PROPOSAL"
    assert error.predicate_id is not None
    assert error.predicate_id.name == "SEMANTIC_PROPOSAL_VALIDATION_FAILED"
    assert error.mechanical_rule_id == "M02"


def test_slotless_component_is_rejected_not_bound_to_all_slots() -> None:
    proposal = _direct_semantic_proposal()
    proposal["components"][0]["slots"] = []

    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        accept_planner_model_output(proposal)
    error = caught.value
    assert error.failure_code.value == "INVALID_SEMANTIC_PROPOSAL"
    assert error.predicate_id is not None
    assert error.predicate_id.name == "SEMANTIC_PROPOSAL_VALIDATION_FAILED"
    assert error.mechanical_rule_id == "M02"


def _with_recon(proposal: dict[str, Any], recon: dict[str, Any]) -> dict[str, Any]:
    mutated = json.loads(json.dumps(proposal))
    mutated["components"][0]["search"]["recon"] = recon
    return mutated


def test_scout_case_a_clear_query_not_needed_is_model_authored() -> None:
    rich = accept_planner_model_output(_direct_semantic_proposal())
    recon = rich["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ][0]["recon_requirement"]
    assert recon["posture"] == "not_needed"
    assert recon["unresolved_dimension_ids"] == []
    assert recon["candidate_queries"] == []
    assert recon["required_for_truthful_targeting"] is False


def test_scout_case_b_optional_ambiguity_compiles_to_rich_downstream_shape() -> None:
    proposal = _with_recon(
        _direct_semantic_proposal(),
        {
            "posture": "optional",
            "dimensions": [
                {
                    "kind": "entity_identity",
                    "query": "Example Permit former current official name",
                }
            ],
        },
    )
    rich = accept_planner_model_output(proposal)
    recon = rich["component_search_requirements"][0]["metadata"][
        "query_strategy_candidates"
    ][0]["recon_requirement"]
    assert recon["posture"] == "optional"
    assert recon["required_for_truthful_targeting"] is False
    assert recon["unresolved_dimension_ids"] == [
        "dimension:01:01:entity_identity"
    ]
    assert recon["candidate_queries"] == [
        {
            "dimension_id": "dimension:01:01:entity_identity",
            "candidate_query_text": "Example Permit former current official name",
            "query_kind": "all_time",
        }
    ]


def test_scout_case_d_omitted_recon_fails_closed() -> None:
    proposal = _direct_semantic_proposal()
    del proposal["components"][0]["search"]["recon"]
    with pytest.raises(SearchPlannerSemanticProposalError) as caught:
        validate_semantic_planner_proposal(proposal)
    assert "recon is required" in str(caught.value)
    assert "not_needed" in str(caught.value)


def test_scout_case_e_malformed_recon_contradictions_fail_closed() -> None:
    contradictions = (
        {
            "posture": "not_needed",
            "dimensions": [
                {"kind": "entity_identity", "query": "should not appear"}
            ],
        },
        {"posture": "required", "dimensions": []},
        {"posture": "optional", "dimensions": []},
    )
    for recon in contradictions:
        proposal = _with_recon(_direct_semantic_proposal(), recon)
        with pytest.raises(SearchPlannerSemanticProposalError):
            validate_semantic_planner_proposal(proposal)


def test_scout_case_f_no_mechanical_authorship_in_recon() -> None:
    proposal = _with_recon(
        _direct_semantic_proposal(),
        {
            "posture": "optional",
            "dimensions": [
                {
                    "kind": "entity_identity",
                    "query": "Example identity probe",
                    "dimension_id": "dimension:hacked",
                }
            ],
        },
    )
    with pytest.raises(SearchPlannerSemanticProposalError) as caught:
        validate_semantic_planner_proposal(proposal)
    message = str(caught.value)
    assert "mechanical identity" in message or "unknown fields" in message


def test_planner_burden_reduction_floors() -> None:
    schema = SEARCH_PLANNER_SEMANTIC_PROPOSAL_SCHEMA
    static_chars = len(json.dumps(schema, sort_keys=True, separators=(",", ":")))
    prompt = build_search_planner_model_prompt(_planner_input_mapping())
    assembled_chars = len(prompt)
    static_reduction = (
        (_BEFORE_STATIC_CONTRACT_CHARS - static_chars) / _BEFORE_STATIC_CONTRACT_CHARS
    )
    assembled_reduction = (
        (_BEFORE_ASSEMBLED_REQUEST_CHARS - assembled_chars)
        / _BEFORE_ASSEMBLED_REQUEST_CHARS
    )
    assert SEARCH_PLANNER_MODEL_PROMPT_SCHEMA_VERSION.endswith("_v5")
    assert static_chars < _BEFORE_STATIC_CONTRACT_CHARS
    assert assembled_chars < _BEFORE_ASSEMBLED_REQUEST_CHARS
    # Compact recon restoration adds required search.recon authorship fields while
    # remaining far below the pre-compiler rich static contract.
    assert static_reduction >= 0.45
    assert assembled_reduction >= 0.30
    # Rich internal authority schema remains available post-compile.
    rich_chars = len(
        json.dumps(
            SEARCH_PLANNER_RICH_INTERNAL_OUTPUT_SCHEMA,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    assert rich_chars > static_chars


def test_runconfig_profile_effort_defaults() -> None:
    config = RunConfig(query="example")
    assert config.fast_reasoning_effort == "medium"
    assert config.smart_reasoning_effort == "medium"
    assert config.fast_provider == "OpenAI"
    assert config.smart_provider == "OpenAI"


def test_searchjudgment_uses_fast_profile_effort() -> None:
    captured: dict[str, Any] = {}

    def fake_ask(prompt: str, system_prompt: str, **kwargs: Any) -> str:
        captured.update(kwargs)
        return "{}"

    raw = _invoke_judgment_model(
        model_input={"authorized_request": {"schema_version": "x"}},
        ask_model=fake_ask,
        provider="FastProvider",
        model="fast-model",
        base_url=None,
        api_key=None,
        effort="medium",
        use_reasoning=True,
        measure_context_stage=None,
    )
    assert raw == "{}"
    assert captured["provider"] == "FastProvider"
    assert captured["model"] == "fast-model"
    assert captured["effort"] == "medium"
    assert captured["require_json"] is True
    assert captured["use_reasoning"] is True


def test_searchjudgment_orchestrator_wires_fast_profile() -> None:
    source = (REPO_ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    judgment_calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name in {
            "execute_searchos_slice_a_iterative_judgment",
            "execute_searchos_recovery_cycle",
        }:
            judgment_calls.append(node)
    assert judgment_calls
    for call in judgment_calls:
        keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        assert "provider" in keywords and "model" in keywords and "effort" in keywords
        provider = keywords["provider"]
        model = keywords["model"]
        effort = keywords["effort"]
        assert isinstance(provider, ast.Name) and provider.id == "fast_provider"
        assert isinstance(model, ast.Name) and model.id == "fast_model"
        assert isinstance(effort, ast.Name) and effort.id == "fast_reasoning_effort"


def test_searchjudgment_request_parity_surface() -> None:
    source = inspect.getsource(_invoke_judgment_model)
    assert "require_json=True" in source
    assert "use_reasoning=use_reasoning" in source
    assert 'effort="high"' not in source
    assert "effort=effort" in source


def test_ordinary_role_local_effort_overrides_removed_from_multicomponent() -> None:
    path = REPO_ROOT / "core" / "multicomponent_role_runtime.py"
    text = path.read_text(encoding="utf-8")
    assert 'effort="high"' not in text
    assert "effort=prepared.effort" in text
    assert "effort=effort" in text


def test_cli_reasoning_effort_flags_exist() -> None:
    text = (REPO_ROOT / "proplex" / "__main__.py").read_text(encoding="utf-8")
    assert "--fast-reasoning-effort" in text
    assert "--smart-reasoning-effort" in text
    assert "SCRYRAVEN_FAST_REASONING_EFFORT" in text
    assert "SCRYRAVEN_SMART_REASONING_EFFORT" in text
    assert "fast_reasoning_effort=args.fast_reasoning_effort" in text
    assert "smart_reasoning_effort=args.smart_reasoning_effort" in text
