"""Investigator's private structured contract, independent of Research and Analyst."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SupportedNote(Contract):
    id: str
    text: str
    support_material_refs: list[str] = Field(min_length=1)


class Obligation(Contract):
    id: str
    trigger: str
    answer_impact: str
    next_action: str


class InvestigationState(Contract):
    """Compact, non-evidentiary continuity; counters and active refs are engine-owned."""

    interpreted_target: str
    intellectual_operation: str
    supported_understanding: list[SupportedNote]
    qualifications_and_conflicts: list[SupportedNote]
    unresolved_obligations: list[Obligation]


class UnresolvedPortion(Contract):
    portion: str
    limitation: str


class InvestigatorTerminal(Contract):
    """One integrated analysis and its exact support set, not a per-sentence proof map.

    Synthesis may compare, explain, evaluate, or establish qualified relationships.
    All qualifications/conflicts are part of that same supported analysis.
    """

    interpreted_target: str
    intellectual_operation: str
    synthesis: str
    qualifications: list[str]
    conflicts: list[str]
    unresolved: list[UnresolvedPortion]
    posture: Literal["supported", "partial", "unable"]
    stop_reason: str
    support_material_refs: list[str]


class Discover(Contract):
    kind: Literal["discover"]
    query: str
    evidence_need: str


class Read(Contract):
    kind: Literal["read"]
    source_ref: str
    missing_context: str


class ExactRange(Contract):
    parent_ref: str
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)


class Locate(Contract):
    material_ref: str
    query: str
    start_char: int = Field(ge=0)


class CatalogWindow(Contract):
    offset: int = Field(ge=0)
    query: str


class Inspect(Contract):
    kind: Literal["inspect"]
    purpose: str
    activate_material_refs: list[str]
    exact_ranges: list[ExactRange]
    locate: Locate | None
    catalog_window: CatalogWindow | None


class Finish(Contract):
    kind: Literal["finish"]
    terminal: InvestigatorTerminal


class Clarify(Contract):
    kind: Literal["clarify"]
    question: str
    target_difference: str


class InvestigatorDecision(Contract):
    state: InvestigationState
    shelve_material_refs: list[str]
    action: Discover | Read | Inspect | Finish | Clarify


@dataclass(frozen=True)
class ExperimentalLimits:
    """Harness knobs, not durable product promises or renewable obligation budgets."""

    max_nonterminal_cycles: int = 16
    max_external_acquisitions: int = 16
    active_evidence_target_chars: int = 128_000
    catalog_page_size: int = 24
    region_page_size: int = 12
    max_state_chars: int = 24_000
    max_model_input_chars: int = 512_000

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if type(value) is not int or value < (0 if name.startswith("max_nonterminal")
                                                or name == "max_external_acquisitions" else 1):
                raise ValueError("invalid_experimental_limits")
