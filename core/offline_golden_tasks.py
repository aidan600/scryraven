"""Fixture-backed golden task schema for AG-93B offline evaluation.

The schema is intentionally normalized around RunAuthority concepts but remains
offline-only. It stores synthetic source refs, expected ingredients, custody and
posture expectations, and citation-alignment rules for deterministic harness
tests. It does not call providers, search, models, prompts, persistence, or
runtime orchestration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any, Mapping

OFFLINE_GOLDEN_TASK_SCHEMA_VERSION = "offline_golden_task_ag93b_v1"


def _tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def _strings(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    for item in _tuple(value):
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return tuple(out)


def _bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


@dataclass(frozen=True, slots=True)
class GoldenSourceRef:
    source_id: str
    url: str
    title: str
    source_class: str
    source_tier: str
    currentness: str = "not_applicable"
    citation_eligible: bool = True
    supports_ingredient_ids: tuple[str, ...] = ()
    notes: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "GoldenSourceRef":
        return cls(
            source_id=str(payload.get("source_id") or ""),
            url=str(payload.get("url") or ""),
            title=str(payload.get("title") or ""),
            source_class=str(payload.get("source_class") or ""),
            source_tier=str(payload.get("source_tier") or ""),
            currentness=str(payload.get("currentness") or "not_applicable"),
            citation_eligible=_bool(payload.get("citation_eligible"), default=True),
            supports_ingredient_ids=_strings(
                payload.get("supports_ingredient_ids") or payload.get("supports")
            ),
            notes=payload.get("notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "source_class": self.source_class,
            "source_tier": self.source_tier,
            "currentness": self.currentness,
            "citation_eligible": self.citation_eligible,
            "supports_ingredient_ids": list(self.supports_ingredient_ids),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ExpectedAnswerIngredient:
    ingredient_id: str
    description: str
    source_ids: tuple[str, ...] = ()
    requirement_id: str | None = None
    required_phrases: tuple[str, ...] = ()
    required_in_final_answer: bool = True
    source_bound_numeric: bool = False
    numeric_value: str | None = None
    may_be_unknown: bool = False

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ExpectedAnswerIngredient":
        return cls(
            ingredient_id=str(payload.get("ingredient_id") or ""),
            description=str(payload.get("description") or ""),
            source_ids=_strings(payload.get("source_ids")),
            requirement_id=payload.get("requirement_id"),
            required_phrases=_strings(payload.get("required_phrases")),
            required_in_final_answer=_bool(
                payload.get("required_in_final_answer"),
                default=True,
            ),
            source_bound_numeric=_bool(payload.get("source_bound_numeric")),
            numeric_value=payload.get("numeric_value"),
            may_be_unknown=_bool(payload.get("may_be_unknown")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingredient_id": self.ingredient_id,
            "description": self.description,
            "source_ids": list(self.source_ids),
            "requirement_id": self.requirement_id,
            "required_phrases": list(self.required_phrases),
            "required_in_final_answer": self.required_in_final_answer,
            "source_bound_numeric": self.source_bound_numeric,
            "numeric_value": self.numeric_value,
            "may_be_unknown": self.may_be_unknown,
        }


@dataclass(frozen=True, slots=True)
class ExpectedSourceObligation:
    requirement_id: str
    required_source_class: str | None = None
    required_source_tier: str | None = None
    required_currentness: str | None = None
    satisfying_source_ids: tuple[str, ...] = ()
    forbidden_source_ids: tuple[str, ...] = ()
    lower_tier_allowed: bool = False
    must_be_satisfied: bool = True

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ExpectedSourceObligation":
        return cls(
            requirement_id=str(payload.get("requirement_id") or ""),
            required_source_class=payload.get("required_source_class"),
            required_source_tier=payload.get("required_source_tier"),
            required_currentness=payload.get("required_currentness"),
            satisfying_source_ids=_strings(payload.get("satisfying_source_ids")),
            forbidden_source_ids=_strings(payload.get("forbidden_source_ids")),
            lower_tier_allowed=_bool(payload.get("lower_tier_allowed")),
            must_be_satisfied=_bool(payload.get("must_be_satisfied"), default=True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "required_source_class": self.required_source_class,
            "required_source_tier": self.required_source_tier,
            "required_currentness": self.required_currentness,
            "satisfying_source_ids": list(self.satisfying_source_ids),
            "forbidden_source_ids": list(self.forbidden_source_ids),
            "lower_tier_allowed": self.lower_tier_allowed,
            "must_be_satisfied": self.must_be_satisfied,
        }


@dataclass(frozen=True, slots=True)
class ExpectedLedgerState:
    admitted_source_ids: tuple[str, ...] = ()
    satisfied_requirement_ids: tuple[str, ...] = ()
    expected_gap_types: tuple[str, ...] = ()
    rejected_source_ids: tuple[str, ...] = ()
    non_satisfying_source_ids: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ExpectedLedgerState":
        return cls(
            admitted_source_ids=_strings(payload.get("admitted_source_ids")),
            satisfied_requirement_ids=_strings(payload.get("satisfied_requirement_ids")),
            expected_gap_types=_strings(payload.get("expected_gap_types")),
            rejected_source_ids=_strings(payload.get("rejected_source_ids")),
            non_satisfying_source_ids=_strings(payload.get("non_satisfying_source_ids")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "admitted_source_ids": list(self.admitted_source_ids),
            "satisfied_requirement_ids": list(self.satisfied_requirement_ids),
            "expected_gap_types": list(self.expected_gap_types),
            "rejected_source_ids": list(self.rejected_source_ids),
            "non_satisfying_source_ids": list(self.non_satisfying_source_ids),
        }


@dataclass(frozen=True, slots=True)
class ExpectedSearchState:
    allowed_decisions: tuple[str, ...] = ()
    min_attempts: int = 0
    max_attempts: int | None = None
    min_recovery_attempts: int = 0
    max_recovery_attempts: int | None = None
    required_target_source_classes: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ExpectedSearchState":
        max_attempts = payload.get("max_attempts")
        max_recovery_attempts = payload.get("max_recovery_attempts")
        return cls(
            allowed_decisions=_strings(payload.get("allowed_decisions")),
            min_attempts=int(payload.get("min_attempts") or 0),
            max_attempts=int(max_attempts) if max_attempts is not None else None,
            min_recovery_attempts=int(payload.get("min_recovery_attempts") or 0),
            max_recovery_attempts=(
                int(max_recovery_attempts) if max_recovery_attempts is not None else None
            ),
            required_target_source_classes=_strings(
                payload.get("required_target_source_classes")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_decisions": list(self.allowed_decisions),
            "min_attempts": self.min_attempts,
            "max_attempts": self.max_attempts,
            "min_recovery_attempts": self.min_recovery_attempts,
            "max_recovery_attempts": self.max_recovery_attempts,
            "required_target_source_classes": list(self.required_target_source_classes),
        }


@dataclass(frozen=True, slots=True)
class ExpectedSufficiencyState:
    allowed_decisions: tuple[str, ...] = ()
    allowed_postures: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ExpectedSufficiencyState":
        return cls(
            allowed_decisions=_strings(payload.get("allowed_decisions")),
            allowed_postures=_strings(payload.get("allowed_postures")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_decisions": list(self.allowed_decisions),
            "allowed_postures": list(self.allowed_postures),
        }


@dataclass(frozen=True, slots=True)
class ExpectedFinalPacketState:
    required_caveats: tuple[str, ...] = ()
    prohibited_upgrades: tuple[str, ...] = ()
    allowed_evidence_source_ids: tuple[str, ...] = ()
    citation_eligible_source_ids: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ExpectedFinalPacketState":
        return cls(
            required_caveats=_strings(payload.get("required_caveats")),
            prohibited_upgrades=_strings(payload.get("prohibited_upgrades")),
            allowed_evidence_source_ids=_strings(payload.get("allowed_evidence_source_ids")),
            citation_eligible_source_ids=_strings(
                payload.get("citation_eligible_source_ids")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_caveats": list(self.required_caveats),
            "prohibited_upgrades": list(self.prohibited_upgrades),
            "allowed_evidence_source_ids": list(self.allowed_evidence_source_ids),
            "citation_eligible_source_ids": list(self.citation_eligible_source_ids),
        }


@dataclass(frozen=True, slots=True)
class CitationAlignmentExpectation:
    ingredient_id: str
    source_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CitationAlignmentExpectation":
        return cls(
            ingredient_id=str(payload.get("ingredient_id") or ""),
            source_ids=_strings(payload.get("source_ids")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingredient_id": self.ingredient_id,
            "source_ids": list(self.source_ids),
        }


@dataclass(frozen=True, slots=True)
class ForbiddenUnsupportedClaim:
    claim_id: str
    phrases: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ForbiddenUnsupportedClaim":
        return cls(
            claim_id=str(payload.get("claim_id") or ""),
            phrases=_strings(payload.get("phrases")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"claim_id": self.claim_id, "phrases": list(self.phrases)}


@dataclass(frozen=True, slots=True)
class GoldenTask:
    task_id: str
    family: str
    query: str
    source_refs: tuple[GoldenSourceRef, ...]
    expected_answer_ingredients: tuple[ExpectedAnswerIngredient, ...]
    source_obligations: tuple[ExpectedSourceObligation, ...]
    expected_contract_requirements: tuple[ExpectedSourceObligation, ...] = ()
    expected_ledger: ExpectedLedgerState = field(default_factory=ExpectedLedgerState)
    expected_search: ExpectedSearchState = field(default_factory=ExpectedSearchState)
    expected_sufficiency: ExpectedSufficiencyState = field(default_factory=ExpectedSufficiencyState)
    expected_final_packet: ExpectedFinalPacketState = field(default_factory=ExpectedFinalPacketState)
    citation_alignment: tuple[CitationAlignmentExpectation, ...] = ()
    forbidden_unsupported_claims: tuple[ForbiddenUnsupportedClaim, ...] = ()
    prose_style_notes: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "GoldenTask":
        expected_contract_requirements = payload.get("expected_contract_requirements")
        if expected_contract_requirements is None:
            expected_contract_requirements = payload.get("source_obligations")
        return cls(
            task_id=str(payload.get("task_id") or ""),
            family=str(payload.get("family") or ""),
            query=str(payload.get("query") or ""),
            source_refs=tuple(
                GoldenSourceRef.from_mapping(item)
                for item in _tuple(payload.get("source_refs"))
                if isinstance(item, Mapping)
            ),
            expected_answer_ingredients=tuple(
                ExpectedAnswerIngredient.from_mapping(item)
                for item in _tuple(payload.get("expected_answer_ingredients"))
                if isinstance(item, Mapping)
            ),
            source_obligations=tuple(
                ExpectedSourceObligation.from_mapping(item)
                for item in _tuple(payload.get("source_obligations"))
                if isinstance(item, Mapping)
            ),
            expected_contract_requirements=tuple(
                ExpectedSourceObligation.from_mapping(item)
                for item in _tuple(expected_contract_requirements)
                if isinstance(item, Mapping)
            ),
            expected_ledger=ExpectedLedgerState.from_mapping(
                _mapping(payload.get("expected_ledger"))
            ),
            expected_search=ExpectedSearchState.from_mapping(
                _mapping(payload.get("expected_search"))
            ),
            expected_sufficiency=ExpectedSufficiencyState.from_mapping(
                _mapping(payload.get("expected_sufficiency"))
            ),
            expected_final_packet=ExpectedFinalPacketState.from_mapping(
                _mapping(payload.get("expected_final_packet"))
            ),
            citation_alignment=tuple(
                CitationAlignmentExpectation.from_mapping(item)
                for item in _tuple(payload.get("citation_alignment"))
                if isinstance(item, Mapping)
            ),
            forbidden_unsupported_claims=tuple(
                ForbiddenUnsupportedClaim.from_mapping(item)
                for item in _tuple(payload.get("forbidden_unsupported_claims"))
                if isinstance(item, Mapping)
            ),
            prose_style_notes=_strings(payload.get("prose_style_notes")),
        )

    @property
    def source_ref_by_id(self) -> dict[str, GoldenSourceRef]:
        return {item.source_id: item for item in self.source_refs}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": OFFLINE_GOLDEN_TASK_SCHEMA_VERSION,
            "task_id": self.task_id,
            "family": self.family,
            "query": self.query,
            "source_refs": [item.to_dict() for item in self.source_refs],
            "expected_answer_ingredients": [
                item.to_dict() for item in self.expected_answer_ingredients
            ],
            "source_obligations": [item.to_dict() for item in self.source_obligations],
            "expected_contract_requirements": [
                item.to_dict() for item in self.expected_contract_requirements
            ],
            "expected_ledger": self.expected_ledger.to_dict(),
            "expected_search": self.expected_search.to_dict(),
            "expected_sufficiency": self.expected_sufficiency.to_dict(),
            "expected_final_packet": self.expected_final_packet.to_dict(),
            "citation_alignment": [item.to_dict() for item in self.citation_alignment],
            "forbidden_unsupported_claims": [
                item.to_dict() for item in self.forbidden_unsupported_claims
            ],
            "prose_style_notes": list(self.prose_style_notes),
        }


def golden_task_from_mapping(payload: Mapping[str, Any]) -> GoldenTask:
    return GoldenTask.from_mapping(payload)


def load_golden_tasks(path: str | PathLike[str]) -> tuple[GoldenTask, ...]:
    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{fixture_path}: expected JSON object")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError(f"{fixture_path}: expected tasks list")
    return tuple(
        GoldenTask.from_mapping(item)
        for item in tasks
        if isinstance(item, Mapping)
    )


__all__ = [
    "OFFLINE_GOLDEN_TASK_SCHEMA_VERSION",
    "CitationAlignmentExpectation",
    "ExpectedAnswerIngredient",
    "ExpectedFinalPacketState",
    "ExpectedLedgerState",
    "ExpectedSearchState",
    "ExpectedSourceObligation",
    "ExpectedSufficiencyState",
    "ForbiddenUnsupportedClaim",
    "GoldenSourceRef",
    "GoldenTask",
    "golden_task_from_mapping",
    "load_golden_tasks",
]
