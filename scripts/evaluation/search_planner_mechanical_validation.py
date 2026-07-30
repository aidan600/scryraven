"""Deterministic mechanical evaluation of product-boundary observations."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping

from scripts.evaluation.search_planner_product_boundary_observer import (
    CANONICAL_PRODUCT_BOUNDARY_REF,
    PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION,
    ProductBoundaryObservation,
)

MECHANICAL_VALIDATOR_SCHEMA_VERSION = "canonical_search_planner_mechanical_authority_v1"
MECHANICAL_RULES: tuple[tuple[str, str], ...] = (
    ("M01", "one JSON object and required fields"),
    ("M02", "types, enums, bounds, and one-to-five components"),
    ("M03", "unique IDs and valid cross-references"),
    ("M04", "lawful dependencies, acyclic graph, and depth"),
    ("M05", "component support matrix"),
    ("M06", "component purpose and source/target separation"),
    ("M07", "query-strategy and distinct-primary rules"),
    ("M08", "neutrality and closed authority"),
    ("M09", "privacy and raw-material exclusion"),
    ("M10", "lineage and binding integrity"),
    ("M11", "runtime projection and authorization"),
    ("M12", "initial acceptance and query-production handoff"),
    ("M13", "call manifest, incompleteness, and stop posture"),
    ("M14", "route, cap, and retry posture"),
    ("M15", "usage, cost, and safe telemetry posture"),
    ("M16", "result classification and precedence"),
    ("M17", "ordinary product ownership and no shadow path"),
)
_RULE_TEXT = dict(MECHANICAL_RULES)
_POSTURES = frozenset({"PASS", "FAIL", "NOT_REACHED", "REVIEW_REQUIRED"})


@dataclass(frozen=True, slots=True)
class MechanicalRuleResult:
    rule_id: str
    rule: str
    posture: str
    bounded_reason: str
    observation_refs: tuple[str, ...]
    blocks_semantic_judgment: bool

    def __post_init__(self) -> None:
        if self.rule_id not in _RULE_TEXT:
            raise ValueError(f"unknown mechanical rule: {self.rule_id}")
        if self.rule != _RULE_TEXT[self.rule_id]:
            raise ValueError("mechanical rule text differs from the registry")
        if self.posture not in _POSTURES:
            raise ValueError(f"unsupported mechanical posture: {self.posture}")
        if len(self.bounded_reason) > 240:
            raise ValueError("mechanical reason exceeds the bounded contract")
        if not self.bounded_reason.strip():
            raise ValueError("mechanical reason must be explicit")
        if not self.observation_refs or any(
            not str(item or "").strip() for item in self.observation_refs
        ):
            raise ValueError("mechanical observation references must be explicit")
        if not isinstance(self.blocks_semantic_judgment, bool):
            raise ValueError("mechanical blocking posture must be boolean")


@dataclass(frozen=True, slots=True)
class MechanicalValidationResult:
    schema_version: str
    owner: str
    result_id: str
    product_observation_schema_version: str
    product_observation_digest: str
    product_proposal_digest: str | None
    overall_posture: str
    rule_results: tuple[MechanicalRuleResult, ...]
    blocking_failure_rule_ids: tuple[str, ...]
    review_required_rule_ids: tuple[str, ...]
    semantic_judgment_allowed: bool
    diagnostic_semantic_judgment_allowed: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != MECHANICAL_VALIDATOR_SCHEMA_VERSION:
            raise ValueError("mechanical result schema is unsupported")
        if self.owner != "CanonicalSearchPlannerMechanicalAuthority":
            raise ValueError("mechanical result owner is invalid")
        if not re.fullmatch(r"mechanical-result:[0-9a-f]{64}", self.result_id):
            raise ValueError("mechanical result identity is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.product_observation_digest):
            raise ValueError("product observation identity must be one SHA-256 digest")
        if self.product_observation_schema_version != PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION:
            raise ValueError("product observation schema identity is unsupported")
        if self.product_proposal_digest is not None and not re.fullmatch(
            r"[0-9a-f]{64}",
            self.product_proposal_digest,
        ):
            raise ValueError("product proposal identity must be one SHA-256 digest")
        if self.overall_posture not in _POSTURES:
            raise ValueError("unsupported overall mechanical posture")
        ids = tuple(item.rule_id for item in self.rule_results)
        if ids != tuple(rule_id for rule_id, _ in MECHANICAL_RULES):
            raise ValueError("mechanical result must cover M01 through M17 exactly")
        blocking = tuple(
            item.rule_id
            for item in self.rule_results
            if item.posture == "FAIL" and item.blocks_semantic_judgment
        )
        review = tuple(
            item.rule_id
            for item in self.rule_results
            if item.posture in {"NOT_REACHED", "REVIEW_REQUIRED"}
            and item.blocks_semantic_judgment
        )
        if self.blocking_failure_rule_ids != blocking:
            raise ValueError("blocking rule identities do not match the rule results")
        if self.review_required_rule_ids != review:
            raise ValueError("review-required rule identities do not match the rule results")
        boundary_not_reached = self.rule_results[-1].posture == "NOT_REACHED"
        expected_overall = (
            "NOT_REACHED"
            if boundary_not_reached
            else "FAIL"
            if blocking
            else "REVIEW_REQUIRED"
            if review
            else "PASS"
        )
        if self.overall_posture != expected_overall:
            raise ValueError("overall mechanical posture does not match the rule results")
        if self.semantic_judgment_allowed != (self.overall_posture == "PASS"):
            raise ValueError("semantic authority must follow the mechanical result")
        if self.overall_posture == "PASS" and self.product_proposal_digest is None:
            raise ValueError("mechanical PASS requires the canonical proposal identity")
        if self.result_id != f"mechanical-result:{_digest(_result_material(self))}":
            raise ValueError("mechanical result identity does not cover the owner result")

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


def validate_product_observation(
    observation: ProductBoundaryObservation,
) -> MechanicalValidationResult:
    """Decide only deterministic rules from one typed product observation."""

    if (
        observation.schema_version != PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION
        or observation.owner != "CanonicalProductSearchPlannerBoundary"
    ):
        raise ValueError("mechanical validation requires the canonical typed product observation")
    observation_digest = _digest(observation.to_packet())
    results = tuple(_evaluate_rule(rule_id, observation) for rule_id, _ in MECHANICAL_RULES)
    blocking = tuple(item.rule_id for item in results if item.posture == "FAIL" and item.blocks_semantic_judgment)
    review = tuple(
        item.rule_id
        for item in results
        if item.posture in {"NOT_REACHED", "REVIEW_REQUIRED"} and item.blocks_semantic_judgment
    )
    if not observation.product_boundary_reached:
        overall = "NOT_REACHED"
    elif blocking:
        overall = "FAIL"
    elif review:
        overall = "REVIEW_REQUIRED"
    else:
        overall = "PASS"
    result_material = {
        "schema_version": MECHANICAL_VALIDATOR_SCHEMA_VERSION,
        "owner": "CanonicalSearchPlannerMechanicalAuthority",
        "product_observation_schema_version": observation.schema_version,
        "product_observation_digest": observation_digest,
        "product_proposal_digest": observation.proposal_digest,
        "overall_posture": overall,
        "rule_results": [asdict(item) for item in results],
        "blocking_failure_rule_ids": blocking,
        "review_required_rule_ids": review,
        "semantic_judgment_allowed": overall == "PASS",
        "diagnostic_semantic_judgment_allowed": True,
    }
    return MechanicalValidationResult(
        schema_version=MECHANICAL_VALIDATOR_SCHEMA_VERSION,
        owner="CanonicalSearchPlannerMechanicalAuthority",
        result_id=f"mechanical-result:{_digest(result_material)}",
        product_observation_schema_version=observation.schema_version,
        product_observation_digest=observation_digest,
        product_proposal_digest=observation.proposal_digest,
        overall_posture=overall,
        rule_results=results,
        blocking_failure_rule_ids=blocking,
        review_required_rule_ids=review,
        semantic_judgment_allowed=overall == "PASS",
    )


def _result_material(
    result: MechanicalValidationResult,
) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "owner": result.owner,
        "product_observation_schema_version": (
            result.product_observation_schema_version
        ),
        "product_observation_digest": result.product_observation_digest,
        "product_proposal_digest": result.product_proposal_digest,
        "overall_posture": result.overall_posture,
        "rule_results": [asdict(item) for item in result.rule_results],
        "blocking_failure_rule_ids": result.blocking_failure_rule_ids,
        "review_required_rule_ids": result.review_required_rule_ids,
        "semantic_judgment_allowed": result.semantic_judgment_allowed,
        "diagnostic_semantic_judgment_allowed": (
            result.diagnostic_semantic_judgment_allowed
        ),
    }


def _evaluate_rule(
    rule_id: str,
    observation: ProductBoundaryObservation,
) -> MechanicalRuleResult:
    evaluators: Mapping[
        str,
        Callable[[ProductBoundaryObservation], tuple[str, str, tuple[str, ...]]],
    ] = {
        "M01": _parser_rule,
        "M02": lambda item: _validator_rule("M02", item),
        "M03": lambda item: _validator_rule("M03", item),
        "M04": lambda item: _validator_rule("M04", item),
        "M05": lambda item: _validator_rule("M05", item),
        "M06": lambda item: _validator_rule("M06", item),
        "M07": lambda item: _validator_rule("M07", item),
        "M08": lambda item: _validator_rule("M08", item),
        "M09": lambda item: _privacy_rule(item),
        "M10": lambda item: _validator_rule("M10", item),
        "M11": lambda item: _stage_rule(
            item.runtime_projection_posture,
            "canonical runtime projection",
            "runtime_projection_posture",
        ),
        "M12": lambda item: _stage_rule(
            item.initial_acceptance_posture,
            "canonical initial acceptance",
            "initial_acceptance_posture",
        ),
        "M13": _incomplete_rule,
        "M14": _route_rule,
        "M15": _telemetry_rule,
        "M16": _precedence_rule,
        "M17": _product_owner_rule,
    }
    posture, reason, refs = evaluators[rule_id](observation)
    return MechanicalRuleResult(
        rule_id=rule_id,
        rule=_RULE_TEXT[rule_id],
        posture=posture,
        bounded_reason=reason,
        observation_refs=refs,
        blocks_semantic_judgment=True,
    )


def _parser_rule(
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    posture = observation.parser_posture
    return (
        posture,
        (
            "Canonical product parser accepted one JSON object."
            if posture == "PASS"
            else "Canonical product parser did not establish one valid object."
        ),
        ("parser_posture",),
    )


def _validator_rule(
    rule_id: str,
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    if observation.validator_posture == "PASS":
        return (
            "PASS",
            f"Canonical product validator accepted {_RULE_TEXT[rule_id]}.",
            ("validator_posture", f"canonical_rule:{rule_id}"),
        )
    if rule_id in observation.canonical_failure_rule_ids:
        return (
            "FAIL",
            f"Canonical product validator rejected {_RULE_TEXT[rule_id]}.",
            ("validator_posture", f"canonical_failure_rule:{rule_id}"),
        )
    if observation.validator_posture == "FAIL":
        return (
            "NOT_REACHED",
            "Another canonical validator rule failed before this rule was established.",
            ("validator_posture",),
        )
    return (
        observation.validator_posture,
        "Canonical product validation did not establish this rule.",
        ("validator_posture",),
    )


def _privacy_rule(
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    if any(
        (
            observation.raw_prompt_retained,
            observation.raw_response_retained,
            observation.raw_provider_payload_retained,
            observation.observer_parsed_model_output,
        )
    ):
        return (
            "FAIL",
            "The observation violated raw-material or no-shadow constraints.",
            ("retention_posture", "observer_parsed_model_output"),
        )
    return _validator_rule("M09", observation)


def _stage_rule(
    posture: str,
    label: str,
    ref: str,
) -> tuple[str, str, tuple[str, ...]]:
    return (
        posture,
        f"{label} {'succeeded' if posture == 'PASS' else 'was not established'}.",
        (ref,),
    )


def _incomplete_rule(
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    posture = observation.incomplete_generation_posture
    if posture == "COMPLETE":
        return (
            "PASS",
            "A bounded response was received before parsing.",
            ("incomplete_generation_posture", "response_received"),
        )
    if posture == "INCOMPLETE":
        return (
            "FAIL",
            "Generation was incomplete; parser and semantic success are blocked.",
            ("incomplete_generation_posture", "response_received"),
        )
    return (
        "NOT_REACHED",
        "No product model boundary was reached.",
        ("incomplete_generation_posture",),
    )


def _route_rule(
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    shape = observation.ask_model_argument_shape
    if shape is None:
        return "NOT_REACHED", "No model-call argument shape was observed.", ("ask_model_argument_shape",)
    passed = all(
        (
            observation.model_call_count == 1,
            shape.require_json,
            shape.provider_present,
            shape.model_present,
            shape.reasoning_effort_present,
        )
    )
    return (
        "PASS" if passed else "FAIL",
        (
            "One exact JSON-required product route was observed."
            if passed
            else "The observed product route shape was incomplete or repeated."
        ),
        ("model_call_count", "ask_model_argument_shape"),
    )


def _telemetry_rule(
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    shape = observation.ask_model_argument_shape
    if shape is None:
        return "NOT_REACHED", "No accounting seam was observed.", ("ask_model_argument_shape",)
    passed = (
        shape.cost_accumulator_present
        and shape.cost_phase == "search_planner"
        and not observation.raw_provider_payload_retained
    )
    return (
        "PASS" if passed else "FAIL",
        (
            "The canonical cost seam and sanitized telemetry posture were present."
            if passed
            else "The canonical cost seam or sanitized telemetry posture was absent."
        ),
        ("ask_model_argument_shape", "safe_usage_refs"),
    )


def _precedence_rule(
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    if not observation.product_boundary_reached:
        return (
            "NOT_REACHED",
            "No product stages were reached, so precedence was not exercised.",
            ("product_boundary_reached",),
        )
    order = (
        observation.parser_posture,
        observation.validator_posture,
        observation.runtime_projection_posture,
        observation.initial_acceptance_posture,
        observation.search_work_plan_posture,
    )
    incoherent = any(later == "PASS" and earlier != "PASS" for earlier, later in zip(order, order[1:]))
    if observation.boundary_status == "FAIL":
        return (
            "FAIL",
            "The canonical product boundary rejected the proposal.",
            (
                "boundary_status",
                "parser_posture",
                "validator_posture",
                "runtime_projection_posture",
                "initial_acceptance_posture",
            ),
        )
    return (
        "FAIL" if incoherent else "PASS",
        (
            "A downstream pass appeared after an upstream non-pass."
            if incoherent
            else "Product stage results preserve fail-closed precedence."
        ),
        (
            "parser_posture",
            "validator_posture",
            "runtime_projection_posture",
            "initial_acceptance_posture",
        ),
    )


def _product_owner_rule(
    observation: ProductBoundaryObservation,
) -> tuple[str, str, tuple[str, ...]]:
    if not observation.product_boundary_reached:
        return "NOT_REACHED", "The ordinary product boundary was not reached.", ("boundary_ref",)
    passed = observation.boundary_ref == CANONICAL_PRODUCT_BOUNDARY_REF and not observation.observer_parsed_model_output
    return (
        "PASS" if passed else "FAIL",
        (
            "The canonical ordinary product boundary remained the sole owner."
            if passed
            else "A noncanonical or shadow boundary was observed."
        ),
        ("boundary_ref", "observer_parsed_model_output"),
    )


def _digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(rendered.encode("utf-8")).hexdigest()


__all__ = [
    "MECHANICAL_RULES",
    "MECHANICAL_VALIDATOR_SCHEMA_VERSION",
    "MechanicalRuleResult",
    "MechanicalValidationResult",
    "validate_product_observation",
]
