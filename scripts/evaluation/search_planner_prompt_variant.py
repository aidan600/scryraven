"""Evaluation-only dispatch of SearchPlanner instruction variants.

The product remains the sole prompt builder.  This module can only preserve the
product prompt or replace the bytes preceding its existing sanitized-input
marker.  It retains identities and lengths, never prompt text.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any

from scripts.evaluation.search_planner_product_boundary_observer import (
    SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER,
)

PROMPT_VARIANT_CONTRACT_VERSION = (
    "search_planner_instruction_prefix_variant_v1"
)
PROMPT_DISPATCH_OBSERVATION_SCHEMA_VERSION = (
    "search_planner_prompt_variant_dispatch_observation_v1"
)


class PromptVariantContractError(ValueError):
    """Raised when a dispatch could alter a protected prompt surface."""


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


@dataclass(frozen=True, slots=True)
class PromptVariantSpecification:
    """One authorization-supplied control/variant definition."""

    contract_version: str
    control_arm_id: str
    variant_arm_id: str
    variant_instruction_text: str = field(repr=False, compare=False)
    variant_instruction_sha256: str
    maximum_instruction_characters: int

    def __post_init__(self) -> None:
        if self.contract_version != PROMPT_VARIANT_CONTRACT_VERSION:
            raise PromptVariantContractError(
                "prompt-variant contract version is unsupported"
            )
        for label, value in (
            ("control_arm_id", self.control_arm_id),
            ("variant_arm_id", self.variant_arm_id),
        ):
            if not str(value or "").strip() or len(value) > 120:
                raise PromptVariantContractError(
                    f"{label} must be explicit and bounded"
                )
        if self.control_arm_id == self.variant_arm_id:
            raise PromptVariantContractError(
                "control and variant arm identities must differ"
            )
        if (
            isinstance(self.maximum_instruction_characters, bool)
            or not isinstance(self.maximum_instruction_characters, int)
            or self.maximum_instruction_characters <= 0
            or self.maximum_instruction_characters > 20000
        ):
            raise PromptVariantContractError(
                "maximum instruction characters must be a bounded integer"
            )
        if (
            not self.variant_instruction_text.strip()
            or len(self.variant_instruction_text)
            > self.maximum_instruction_characters
        ):
            raise PromptVariantContractError(
                "variant instruction text is empty or exceeds its exact bound"
            )
        if SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER in self.variant_instruction_text:
            raise PromptVariantContractError(
                "variant instruction text cannot contain the product marker"
            )
        if not re.fullmatch(
            r"[0-9a-f]{64}",
            self.variant_instruction_sha256,
        ):
            raise PromptVariantContractError(
                "variant instruction digest must be one SHA-256 digest"
            )
        if self.variant_instruction_sha256 != _digest_text(
            self.variant_instruction_text
        ):
            raise PromptVariantContractError(
                "variant instruction digest does not cover the supplied text"
            )


@dataclass(frozen=True, slots=True)
class PromptVariantDispatchObservation:
    """Safe identities proving what changed at the injected dependency."""

    schema_version: str
    owner: str
    contract_version: str
    variant_identity: str
    transformation_posture: str
    product_semantic_input_digest: str
    product_semantic_input_length: int
    dispatched_semantic_input_digest: str
    dispatched_semantic_input_length: int
    product_system_prompt_digest: str
    product_system_prompt_length: int
    dispatched_system_prompt_digest: str
    dispatched_system_prompt_length: int
    product_instruction_digest: str
    product_instruction_length: int
    dispatched_instruction_digest: str
    dispatched_instruction_length: int
    product_full_prompt_digest: str
    product_full_prompt_length: int
    dispatched_full_prompt_digest: str
    dispatched_full_prompt_length: int
    marker_digest: str
    marker_length: int
    serialized_input_packet_digest: str
    serialized_input_packet_length: int
    control_bytes_unchanged: bool
    protected_bytes_unchanged: bool
    raw_prompt_retained: bool = False
    variant_instruction_retained: bool = False
    serialized_input_packet_retained: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != PROMPT_DISPATCH_OBSERVATION_SCHEMA_VERSION:
            raise PromptVariantContractError(
                "prompt dispatch observation schema is unsupported"
            )
        if self.owner != "SearchPlannerPromptVariantDispatch":
            raise PromptVariantContractError(
                "prompt dispatch observation owner is invalid"
            )
        if self.contract_version != PROMPT_VARIANT_CONTRACT_VERSION:
            raise PromptVariantContractError(
                "prompt dispatch contract identity is invalid"
            )
        if self.transformation_posture not in {
            "CONTROL_UNCHANGED",
            "INSTRUCTION_PREFIX_REPLACED",
        }:
            raise PromptVariantContractError(
                "prompt dispatch transformation posture is unsupported"
            )
        if not str(self.variant_identity or "").strip():
            raise PromptVariantContractError(
                "prompt dispatch variant identity must be explicit"
            )
        for label, value in asdict(self).items():
            if label.endswith("_digest") and not re.fullmatch(
                r"[0-9a-f]{64}",
                str(value),
            ):
                raise PromptVariantContractError(
                    f"{label} must be one SHA-256 digest"
                )
            if label.endswith("_length") and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise PromptVariantContractError(
                    f"{label} must be a nonnegative integer"
                )
        if (
            self.product_semantic_input_digest
            != self.dispatched_semantic_input_digest
            or self.product_semantic_input_length
            != self.dispatched_semantic_input_length
            or self.product_system_prompt_digest
            != self.dispatched_system_prompt_digest
            or self.product_system_prompt_length
            != self.dispatched_system_prompt_length
        ):
            raise PromptVariantContractError(
                "prompt dispatch changed a protected semantic or system surface"
            )
        if not self.protected_bytes_unchanged:
            raise PromptVariantContractError(
                "prompt dispatch must preserve marker and serialized input bytes"
            )
        if self.transformation_posture == "CONTROL_UNCHANGED":
            if not self.control_bytes_unchanged:
                raise PromptVariantContractError(
                    "control dispatch must preserve every prompt byte"
                )
            if (
                self.product_instruction_digest
                != self.dispatched_instruction_digest
                or self.product_full_prompt_digest
                != self.dispatched_full_prompt_digest
            ):
                raise PromptVariantContractError(
                    "control dispatch identities must be byte-identical"
                )
        else:
            if self.control_bytes_unchanged:
                raise PromptVariantContractError(
                    "variant dispatch cannot claim unchanged control bytes"
                )
            if (
                self.product_instruction_digest
                == self.dispatched_instruction_digest
                or self.product_full_prompt_digest
                == self.dispatched_full_prompt_digest
            ):
                raise PromptVariantContractError(
                    "variant dispatch must change instruction and full-prompt identities"
                )
        if any(
            (
                self.raw_prompt_retained,
                self.variant_instruction_retained,
                self.serialized_input_packet_retained,
            )
        ):
            raise PromptVariantContractError(
                "prompt dispatch observation cannot retain raw material"
            )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PromptDispatchResult:
    """Transient prompt plus its safe dispatch observation."""

    dispatched_prompt: str = field(repr=False, compare=False)
    observation: PromptVariantDispatchObservation


def dispatch_search_planner_prompt(
    *,
    product_built_prompt: str,
    system_prompt: str,
    arm_id: str,
    specification: PromptVariantSpecification,
) -> PromptDispatchResult:
    """Dispatch control unchanged or replace only the instruction prefix."""

    specification.__post_init__()
    if arm_id not in {
        specification.control_arm_id,
        specification.variant_arm_id,
    }:
        raise PromptVariantContractError(
            "scheduled arm is outside the prompt-variant authorization"
        )
    if product_built_prompt.count(SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER) != 1:
        raise PromptVariantContractError(
            "product prompt must contain the exact payload marker once"
        )
    product_prefix, marker, serialized_packet = product_built_prompt.partition(
        SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER
    )
    try:
        packet = json.loads(serialized_packet)
        planner_input = dict(packet["planner_input"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PromptVariantContractError(
            "product prompt contains no valid sanitized planner input"
        ) from exc
    canonical_semantic_input = _canonical_json(planner_input)
    product_instruction = product_prefix + marker
    if arm_id == specification.control_arm_id:
        dispatched_prefix = product_prefix
        dispatched_prompt = product_built_prompt
        posture = "CONTROL_UNCHANGED"
    else:
        dispatched_prefix = specification.variant_instruction_text
        if dispatched_prefix == product_prefix:
            raise PromptVariantContractError(
                "variant instruction must differ from installed instructions"
            )
        dispatched_prompt = dispatched_prefix + marker + serialized_packet
        posture = "INSTRUCTION_PREFIX_REPLACED"
    dispatched_instruction = dispatched_prefix + marker
    protected_bytes_unchanged = (
        marker == SEARCH_PLANNER_PROMPT_PAYLOAD_MARKER
        and dispatched_prompt.endswith(marker + serialized_packet)
    )
    observation = PromptVariantDispatchObservation(
        schema_version=PROMPT_DISPATCH_OBSERVATION_SCHEMA_VERSION,
        owner="SearchPlannerPromptVariantDispatch",
        contract_version=PROMPT_VARIANT_CONTRACT_VERSION,
        variant_identity=arm_id,
        transformation_posture=posture,
        product_semantic_input_digest=_digest_text(
            canonical_semantic_input
        ),
        product_semantic_input_length=len(canonical_semantic_input),
        dispatched_semantic_input_digest=_digest_text(
            canonical_semantic_input
        ),
        dispatched_semantic_input_length=len(canonical_semantic_input),
        product_system_prompt_digest=_digest_text(system_prompt),
        product_system_prompt_length=len(system_prompt),
        dispatched_system_prompt_digest=_digest_text(system_prompt),
        dispatched_system_prompt_length=len(system_prompt),
        product_instruction_digest=_digest_text(product_instruction),
        product_instruction_length=len(product_instruction),
        dispatched_instruction_digest=_digest_text(dispatched_instruction),
        dispatched_instruction_length=len(dispatched_instruction),
        product_full_prompt_digest=_digest_text(product_built_prompt),
        product_full_prompt_length=len(product_built_prompt),
        dispatched_full_prompt_digest=_digest_text(dispatched_prompt),
        dispatched_full_prompt_length=len(dispatched_prompt),
        marker_digest=_digest_text(marker),
        marker_length=len(marker),
        serialized_input_packet_digest=_digest_text(serialized_packet),
        serialized_input_packet_length=len(serialized_packet),
        control_bytes_unchanged=dispatched_prompt == product_built_prompt,
        protected_bytes_unchanged=protected_bytes_unchanged,
    )
    return PromptDispatchResult(
        dispatched_prompt=dispatched_prompt,
        observation=observation,
    )


__all__ = [
    "PROMPT_DISPATCH_OBSERVATION_SCHEMA_VERSION",
    "PROMPT_VARIANT_CONTRACT_VERSION",
    "PromptDispatchResult",
    "PromptVariantContractError",
    "PromptVariantDispatchObservation",
    "PromptVariantSpecification",
    "dispatch_search_planner_prompt",
]
