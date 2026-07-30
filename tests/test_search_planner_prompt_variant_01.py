from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from core.search_planner_model_prompt import (
    SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
    build_search_planner_model_prompt,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER,
)
from scripts.evaluation.search_planner_prompt_variant import (
    PROMPT_VARIANT_CONTRACT_VERSION,
    PromptVariantContractError,
    PromptVariantSpecification,
    dispatch_search_planner_prompt,
)

VARIANT_TEXT = (
    "SYNTHETIC VARIANT INSTRUCTIONS\n"
    "Return one strict JSON planner proposal.\n\n"
)


def _specification() -> PromptVariantSpecification:
    return PromptVariantSpecification(
        contract_version=PROMPT_VARIANT_CONTRACT_VERSION,
        control_arm_id="installed-control",
        variant_arm_id="synthetic-variant",
        variant_instruction_text=VARIANT_TEXT,
        variant_instruction_sha256=sha256(
            VARIANT_TEXT.encode("utf-8")
        ).hexdigest(),
        maximum_instruction_characters=1000,
    )


def _product_prompt() -> str:
    return build_search_planner_model_prompt(
        {
            "run_id": "run:synthetic",
            "request_id": "request:synthetic",
            "requested_mode": "Balanced",
            "user_query_text_for_planning": (
                "What is the fictional Alder threshold?"
            ),
            "user_query_ref": {
                "sha256": "0" * 64,
                "character_count": 41,
            },
            "safe_context": {"fictional": True},
            "route_context_ref": {"route_id": "route:synthetic"},
            "run_context_ref": {
                "run_contract_id": "contract:synthetic"
            },
            "parent_contract_refs": [],
            "closed_surface_flags": {
                "evidence_admitted": False,
                "search_executed": False,
            },
        }
    )


def test_control_dispatch_is_byte_identical() -> None:
    product_prompt = _product_prompt()
    result = dispatch_search_planner_prompt(
        product_built_prompt=product_prompt,
        system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
        arm_id="installed-control",
        specification=_specification(),
    )

    assert result.dispatched_prompt == product_prompt
    observation = result.observation
    assert observation.transformation_posture == "CONTROL_UNCHANGED"
    assert observation.control_bytes_unchanged is True
    assert (
        observation.product_full_prompt_digest
        == observation.dispatched_full_prompt_digest
    )
    assert (
        observation.product_instruction_digest
        == observation.dispatched_instruction_digest
    )


def test_variant_replaces_instruction_prefix_only() -> None:
    product_prompt = _product_prompt()
    _, marker, serialized_packet = product_prompt.partition(
        SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER
    )
    result = dispatch_search_planner_prompt(
        product_built_prompt=product_prompt,
        system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
        arm_id="synthetic-variant",
        specification=_specification(),
    )

    assert result.dispatched_prompt == (
        VARIANT_TEXT + marker + serialized_packet
    )
    observation = result.observation
    assert observation.transformation_posture == (
        "INSTRUCTION_PREFIX_REPLACED"
    )
    assert observation.protected_bytes_unchanged is True
    assert (
        observation.product_semantic_input_digest
        == observation.dispatched_semantic_input_digest
    )
    assert (
        observation.product_semantic_input_length
        == observation.dispatched_semantic_input_length
    )
    assert (
        observation.product_system_prompt_digest
        == observation.dispatched_system_prompt_digest
    )
    assert (
        observation.product_instruction_digest
        != observation.dispatched_instruction_digest
    )
    assert (
        observation.product_full_prompt_digest
        != observation.dispatched_full_prompt_digest
    )
    assert (
        result.dispatched_prompt.partition(marker)[2]
        == serialized_packet
    )


def test_dispatch_observation_retains_only_digests_and_lengths() -> None:
    product_prompt = _product_prompt()
    result = dispatch_search_planner_prompt(
        product_built_prompt=product_prompt,
        system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
        arm_id="synthetic-variant",
        specification=_specification(),
    )
    packet = result.observation.to_packet()
    rendered = json.dumps(packet, sort_keys=True)

    assert product_prompt not in rendered
    assert VARIANT_TEXT not in rendered
    assert "fictional Alder threshold" not in rendered
    assert packet["raw_prompt_retained"] is False
    assert packet["variant_instruction_retained"] is False
    assert packet["serialized_input_packet_retained"] is False


@pytest.mark.parametrize(
    "prompt",
    (
        "no product payload marker",
        (
            "prefix"
            + SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER
            + "{}"
            + SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER
            + "{}"
        ),
    ),
)
def test_dispatch_rejects_missing_or_repeated_marker(
    prompt: str,
) -> None:
    with pytest.raises(
        PromptVariantContractError,
        match="exact payload marker once",
    ):
        dispatch_search_planner_prompt(
            product_built_prompt=prompt,
            system_prompt=SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
            arm_id="installed-control",
            specification=_specification(),
        )


def test_variant_specification_rejects_marker_or_digest_mismatch() -> None:
    specification = _specification()
    with pytest.raises(
        PromptVariantContractError,
        match="cannot contain the product marker",
    ):
        replace(
            specification,
            variant_instruction_text=(
                VARIANT_TEXT + SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER
            ),
            variant_instruction_sha256=sha256(
                (
                    VARIANT_TEXT
                    + SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER
                ).encode("utf-8")
            ).hexdigest(),
        )
    with pytest.raises(
        PromptVariantContractError,
        match="does not cover",
    ):
        replace(
            specification,
            variant_instruction_sha256="0" * 64,
        )
