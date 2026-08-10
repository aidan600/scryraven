"""Focused offline parity proof for the PlannerRevision model-visible contract.

Mode: REPAIR.
Test class: phase_focus / offline_model_contract.
No test in this file invokes a provider, model service, search, fetch, or READ.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

import core.search_planner_revision_model_adapter as revision_adapter
from core.search_planner_revision_model_adapter import (
    SearchPlannerRevisionModelAdapter,
    SearchPlannerRevisionModelAdapterError,
    validate_and_sanitize_model_output,
)
from core.search_planner_revision_model_output_contract import (
    SEARCH_PLANNER_REVISION_ALLOWED_AMENDMENT_OPERATION_KINDS,
    SEARCH_PLANNER_REVISION_DANGEROUS_TRUE_MEMBER_NAMES,
    SEARCH_PLANNER_REVISION_FORBIDDEN_AMENDMENT_OPERATION_KINDS,
    SEARCH_PLANNER_REVISION_FORBIDDEN_AUTHORITY_MEMBER_NAMES,
    SEARCH_PLANNER_REVISION_MODEL_STRICT_JSON_OUTPUT_CONTRACT,
    SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS,
    SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS,
    SEARCH_PLANNER_REVISION_SENSITIVE_RAW_PRIVATE_MEMBER_NAMES,
)
from core.search_planner_revision_model_prompt import (
    build_search_planner_revision_model_prompt,
)
from core.search_planner_revision_runtime import (
    SearchPlannerRevisionRuntimeSafeFailureCode,
)


def _revision_input() -> dict[str, Any]:
    return {
        "run_id": "run:contract-alignment",
        "request_id": "request:contract-alignment",
        "component_id": "component:1",
        "consumed_ambiguity_dimension_ids": ["dimension:1"],
        "consumed_scout_hint_ids": ["hint:1"],
        "scout_directional_context": {},
        "safe_revision_context": {},
        "closed_surface_flags": {},
    }


def _minimal_model_output() -> dict[str, Any]:
    return {
        "revised_question_meaning_summary": "Refine only non-evidence search direction.",
        "semantic_slot_updates": [],
        "answer_component_updates": [],
        "component_search_requirement_updates": [],
        "mandatory_caveats": [],
        "prohibited_upgrades": [],
        "normalization_obligations": [],
        "assumptions": [],
        "unresolved_ambiguities": [],
        "consumed_ambiguity_dimension_ids": ["dimension:1"],
        "consumed_scout_hint_ids": ["hint:1"],
        "amendment_candidates": [],
        "closed_surface_flags": {},
    }


def _adapter(response: Any) -> SearchPlannerRevisionModelAdapter:
    def model_callable(*_args: Any, **_kwargs: Any) -> Any:
        return response

    return SearchPlannerRevisionModelAdapter(
        revision_model_callable=model_callable,
        enabled=True,
        licensed=True,
    )


def _output_contract_from_prompt() -> dict[str, Any]:
    prompt = build_search_planner_revision_model_prompt(_revision_input())
    payload = json.loads(prompt.rsplit("Sanitized revision input JSON:\n", maxsplit=1)[-1])
    return dict(payload["output_schema"])


def _assert_failure_code(
    model_output: dict[str, Any],
    expected: SearchPlannerRevisionRuntimeSafeFailureCode,
) -> None:
    with pytest.raises(SearchPlannerRevisionModelAdapterError) as captured:
        validate_and_sanitize_model_output(model_output)
    assert captured.value.failure_code is expected


def test_strict_json_contract_is_static_and_visible_in_the_prompt() -> None:
    schema = _output_contract_from_prompt()
    prompt = build_search_planner_revision_model_prompt(_revision_input())

    assert schema["strict_json_output_contract"] == list(SEARCH_PLANNER_REVISION_MODEL_STRICT_JSON_OUTPUT_CONTRACT)
    for requirement in SEARCH_PLANNER_REVISION_MODEL_STRICT_JSON_OUTPUT_CONTRACT:
        assert requirement in prompt


def test_required_and_optional_top_level_fields_match_the_adapter_contract() -> None:
    schema = _output_contract_from_prompt()
    top_level = schema["top_level"]
    fields = top_level["fields"]

    assert tuple(top_level["required_fields"]) == SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS
    assert tuple(top_level["optional_fields"]) == SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS
    assert tuple(schema["required_top_level_fields"]) == SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS
    assert tuple(schema["optional_top_level_fields"]) == SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS
    assert set(schema["allowed_amendment_operation_kinds"]) == (
        SEARCH_PLANNER_REVISION_ALLOWED_AMENDMENT_OPERATION_KINDS
    )
    assert set(schema["forbidden_operation_kinds"]) == (
        SEARCH_PLANNER_REVISION_FORBIDDEN_AMENDMENT_OPERATION_KINDS
    )
    assert revision_adapter._TOP_LEVEL_REQUIRED is SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS
    for field in SEARCH_PLANNER_REVISION_REQUIRED_TOP_LEVEL_FIELDS:
        assert fields[field]["required"] is True
    for field in SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS:
        assert fields[field]["required"] is False


def test_visible_field_types_and_consumed_id_rules_match_the_accepted_shape() -> None:
    fields = _output_contract_from_prompt()["top_level"]["fields"]

    assert fields["revised_question_meaning_summary"] == {
        "json_type": "string",
        "required": True,
        "max_length": 500,
        "nonempty_after_normalization": True,
        "adapter_normalization": (
            "leading and trailing whitespace is removed and internal whitespace runs are collapsed"
        ),
    }
    for field in (
        "semantic_slot_updates",
        "answer_component_updates",
        "component_search_requirement_updates",
        "unresolved_ambiguities",
    ):
        assert fields[field]["json_type"] == "array"
        assert fields[field]["items"] == "safe JSON objects"
        assert fields[field]["minimum_items"] == 0
    for field in (
        "mandatory_caveats",
        "prohibited_upgrades",
        "normalization_obligations",
        "assumptions",
    ):
        assert fields[field]["json_type"] == "array"
        assert fields[field]["items"]["json_type"] == "string"
        assert fields[field]["minimum_items"] == 0
    assert fields["consumed_ambiguity_dimension_ids"]["minimum_nonempty_items"] == 1
    assert fields["consumed_ambiguity_dimension_ids"]["copy_exact_input_ids"] is True
    assert fields["consumed_ambiguity_dimension_ids"]["preserve_input_order"] is True
    assert fields["consumed_scout_hint_ids"]["copy_exact_input_ids"] is True
    assert fields["consumed_scout_hint_ids"]["preserve_input_order"] is True
    assert fields["closed_surface_flags"] == {
        "json_type": "object",
        "required": True,
        "preferred_output": {},
        "rule": "Prefer {}. If a permitted flag is emitted, its JSON value must be false; no flag may be true.",
    }


def test_visible_authority_sensitive_and_false_only_policies_equal_validator_policy() -> None:
    rules = _output_contract_from_prompt()["global_member_name_rules"]

    assert set(rules["forbidden_authority_member_names"]) == (revision_adapter._FORBIDDEN_AUTHORITY_KEYS)
    assert set(rules["forbidden_authority_member_names"]) == (SEARCH_PLANNER_REVISION_FORBIDDEN_AUTHORITY_MEMBER_NAMES)
    assert set(rules["sensitive_raw_private_member_names"]) == revision_adapter._SENSITIVE_KEYS
    assert set(rules["sensitive_raw_private_member_names"]) == (
        SEARCH_PLANNER_REVISION_SENSITIVE_RAW_PRIVATE_MEMBER_NAMES
    )
    assert rules["sensitive_raw_private_member_name_patterns"] == ["raw_*"]
    assert rules["sensitive_content_rule"] == (
        "Do not include raw or private provider, cache, database, prompt, trace, payload, credential, or secret content anywhere in values or member names."
    )
    assert set(rules["dangerous_true_member_names"]) == revision_adapter._DANGEROUS_TRUE_KEYS
    assert set(rules["dangerous_true_member_names"]) == (SEARCH_PLANNER_REVISION_DANGEROUS_TRUE_MEMBER_NAMES)


def test_visible_amendment_operation_policy_equals_validator_policy() -> None:
    amendment = _output_contract_from_prompt()["amendment_candidate"]
    operation = amendment["fields"]["operation_kind"]

    assert set(operation["allowed_values"]) == revision_adapter._ALLOWED_OPERATION_KINDS
    assert set(operation["allowed_values"]) == (SEARCH_PLANNER_REVISION_ALLOWED_AMENDMENT_OPERATION_KINDS)
    assert set(operation["forbidden_values"]) == revision_adapter._FORBIDDEN_OPERATION_KINDS
    assert set(operation["forbidden_values"]) == (SEARCH_PLANNER_REVISION_FORBIDDEN_AMENDMENT_OPERATION_KINDS)
    assert amendment["allowed_model_authored_fields"] == [
        "candidate_id",
        "operation_kind",
        "caveat",
        "required_caveats",
        "summary",
        "component_id",
        "metadata",
    ]


def test_strengthened_contract_forbids_the_pre_repair_nested_authority_shape() -> None:
    payload = _minimal_model_output()
    payload["semantic_slot_updates"] = [{"evidence": False}]

    rules = _output_contract_from_prompt()["global_member_name_rules"]
    assert "evidence" in rules["forbidden_authority_member_names"]
    _assert_failure_code(
        payload,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_UNSAFE_OR_CLOSED_AUTHORITY,
    )


def test_minimal_contract_compliant_output_still_validates_without_repair() -> None:
    expected = _minimal_model_output()
    result = _adapter(json.dumps(expected)).produce(_revision_input())

    for key, value in expected.items():
        assert result[key] == value
    assert result["planner_revision_model_metadata"]["raw_prompt_retained"] is False
    assert result["planner_revision_model_metadata"]["raw_model_response_retained"] is False
    assert result["planner_revision_model_metadata"]["provider_payload_retained"] is False


def test_empty_closed_surface_flags_remain_valid_and_true_flags_fail_closed() -> None:
    valid = validate_and_sanitize_model_output(_minimal_model_output())
    assert valid["closed_surface_flags"] == {}

    unsafe = _minimal_model_output()
    unsafe["closed_surface_flags"] = {"citation_eligible": True}
    _assert_failure_code(
        unsafe,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_UNSAFE_OR_CLOSED_AUTHORITY,
    )


def test_invalid_amendment_operation_remains_invalid() -> None:
    payload = _minimal_model_output()
    payload["amendment_candidates"] = [{"operation_kind": "resolve_slot"}]

    _assert_failure_code(
        payload,
        SearchPlannerRevisionRuntimeSafeFailureCode.MODEL_OUTPUT_INVALID_AMENDMENT,
    )


def test_prompt_keeps_only_whitelisted_sanitized_revision_input() -> None:
    private_marker = "untrusted-private-input-value-must-not-appear"
    revision_input = {
        **_revision_input(),
        "unrecognized_private_input": private_marker,
    }

    prompt = build_search_planner_revision_model_prompt(revision_input)
    schema = _output_contract_from_prompt()

    assert private_marker not in prompt
    assert "revision_input" in prompt
    assert "global_member_name_rules" in prompt
    assert schema["top_level"]["additional_top_level_fields"].startswith("Do not invent")


def test_optional_fields_remain_accepted_by_the_existing_adapter() -> None:
    payload = deepcopy(_minimal_model_output())
    payload.update(
        {
            "revised_source_obligation_candidates": [],
            "source_obligation_focus_updates": [],
            "planner_revision_notes": ["Keep scope bounded."],
            "confidence_posture": "directional",
            "revision_posture": "proposal_only",
        }
    )

    sanitized = validate_and_sanitize_model_output(payload)
    assert (
        tuple(key for key in SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS if key in sanitized)
        == SEARCH_PLANNER_REVISION_OPTIONAL_TOP_LEVEL_FIELDS
    )
