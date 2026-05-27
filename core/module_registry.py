"""Static passive module registry metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ModuleKind(str, Enum):
    CONTROLLER = "controller"
    MODEL_STAGE = "model_stage"
    RETRIEVAL_STAGE = "retrieval_stage"
    RECOVERY_STAGE = "recovery_stage"
    SAFETY_GATE = "safety_gate"
    PERSISTENCE = "persistence"
    PRESENTATION = "presentation"


@dataclass(frozen=True)
class ModuleRegistryEntry:
    """Static metadata for a module or agent-facing stage."""

    module_id: str
    module_kind: ModuleKind
    owner_surface: str
    input_contract_summary: str
    output_contract_summary: str
    allowed_side_effects: tuple[str, ...]
    safety_constraints: tuple[str, ...]
    future_delegation_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "module_kind": self.module_kind.value,
            "owner_surface": self.owner_surface,
            "input_contract_summary": self.input_contract_summary,
            "output_contract_summary": self.output_contract_summary,
            "allowed_side_effects": list(self.allowed_side_effects),
            "safety_constraints": list(self.safety_constraints),
            "future_delegation_allowed": self.future_delegation_allowed,
        }


MODULE_REGISTRY: tuple[ModuleRegistryEntry, ...] = (
    ModuleRegistryEntry(
        module_id="router",
        module_kind=ModuleKind.MODEL_STAGE,
        owner_surface="core.pipeline_orchestrator router phase",
        input_contract_summary="User query, current date, and prior routing context.",
        output_contract_summary="Intent, report type, image mode, core topic, query type, and entity hints.",
        allowed_side_effects=("model_call_already_owned_by_orchestrator",),
        safety_constraints=("No prompt changes or provider routing changes in Phase 19A.",),
    ),
    ModuleRegistryEntry(
        module_id="answer_contract_controller",
        module_kind=ModuleKind.CONTROLLER,
        owner_surface="AG-1 answer-contract controller spine",
        input_contract_summary=(
            "Router metadata, compact evidence state, existing recovery/stop decisions, "
            "and answer-contract obligations."
        ),
        output_contract_summary=(
            "AnswerContract, controller action results, stop decision, and compact safe "
            "AnswerContractFulfillment handoff."
        ),
        allowed_side_effects=(),
        safety_constraints=(
            "Pure dataclass/helper scaffold only.",
            "Must not call providers, models, prompts, retrieval, storage, or orchestration.",
            "Must not expose raw quantitative packets, Economist framework, provider internals, or evidence dumps.",
        ),
        future_delegation_allowed=True,
    ),
    ModuleRegistryEntry(
        module_id="researcher",
        module_kind=ModuleKind.MODEL_STAGE,
        owner_surface="core.pipeline_orchestrator researcher phase",
        input_contract_summary="Routed topic metadata and mode-derived query budget.",
        output_contract_summary="First-pass retrieval query list.",
        allowed_side_effects=("model_call_already_owned_by_orchestrator",),
        safety_constraints=("Does not own provider selection, search depth, or source ranking.",),
        future_delegation_allowed=True,
    ),
    ModuleRegistryEntry(
        module_id="retrieval",
        module_kind=ModuleKind.RETRIEVAL_STAGE,
        owner_surface="core.pipeline_orchestrator retrieval loop",
        input_contract_summary="Queries, providers selected elsewhere, depth selected elsewhere, and result limits.",
        output_contract_summary="Retrieved passages, images, provider diagnostics, and retrieval pass records.",
        allowed_side_effects=("search_calls_already_owned_by_orchestrator",),
        safety_constraints=("Registry metadata must not call providers or alter provider/depth policy.",),
    ),
    ModuleRegistryEntry(
        module_id="weak_corpus_recovery",
        module_kind=ModuleKind.RECOVERY_STAGE,
        owner_surface="weak-corpus recovery path",
        input_contract_summary="Already-computed corpus state, utilization, iteration budget, and prior queries.",
        output_contract_summary="Observed weak-corpus recovery status, skip reason, and recovery queries.",
        allowed_side_effects=("search_calls_only_when_existing_orchestrator_path_runs",),
        safety_constraints=("Must remain separate from source-class recovery.",),
    ),
    ModuleRegistryEntry(
        module_id="source_class_recovery",
        module_kind=ModuleKind.RECOVERY_STAGE,
        owner_surface="source-class recovery lifecycle and existing runtime path",
        input_contract_summary="Source-class recommendation, evidence signals, provider reuse facts, and depth reuse facts.",
        output_contract_summary="Observed source-class lifecycle, attempt count, provider role, result counts, and additive passages.",
        allowed_side_effects=("search_calls_only_when_existing_source_class_path_runs",),
        safety_constraints=(
            "Must not change eligibility, provider reuse, depth reuse, or additive merge behavior.",
            "Must remain separate from weak-corpus recovery.",
        ),
    ),
    ModuleRegistryEntry(
        module_id="analyst",
        module_kind=ModuleKind.MODEL_STAGE,
        owner_surface="Analyst stage",
        input_contract_summary="Final evidence, retrieval telemetry, and bounded Analyst-safe quantitative notes.",
        output_contract_summary="Analyst synthesis or existing gate-owned skip telemetry.",
        allowed_side_effects=("model_call_already_owned_by_orchestrator",),
        safety_constraints=("Economist output cannot bypass Analyst.",),
        future_delegation_allowed=True,
    ),
    ModuleRegistryEntry(
        module_id="economist",
        module_kind=ModuleKind.SAFETY_GATE,
        owner_surface="shadow quantitative pre-Analyst path",
        input_contract_summary="Quantitative route metadata and evidence-bound metric signals.",
        output_contract_summary="Shadow quantitative packet telemetry and safety gate diagnostics.",
        allowed_side_effects=("model_call_already_owned_by_orchestrator",),
        safety_constraints=(
            "Cannot execute code.",
            "Cannot bypass Analyst.",
            "Raw quantitative_packet, raw framework, and economist_v1 JSON must not go to Author.",
        ),
    ),
    ModuleRegistryEntry(
        module_id="scrutineer",
        module_kind=ModuleKind.MODEL_STAGE,
        owner_surface="Deep-mode Scrutineer path",
        input_contract_summary="Deep Analyst synthesis and cited evidence.",
        output_contract_summary="Scrutineer flags and optional remediation facts.",
        allowed_side_effects=("model_call_already_owned_by_orchestrator",),
        safety_constraints=("Deep-only; must not alter Balanced or Fast routing.",),
    ),
    ModuleRegistryEntry(
        module_id="author",
        module_kind=ModuleKind.PRESENTATION,
        owner_surface="Author stage",
        input_contract_summary="User query, mode instructions, citations, safe Analyst synthesis, and safe notes.",
        output_contract_summary="Final user-visible report.",
        allowed_side_effects=("model_call_already_owned_by_orchestrator",),
        safety_constraints=(
            "Must not receive raw quantitative_packet.",
            "Must not receive raw Economist framework or economist_v1 JSON.",
            "Must not receive source-class diagnostics as user-visible content.",
        ),
    ),
    ModuleRegistryEntry(
        module_id="persistence",
        module_kind=ModuleKind.PERSISTENCE,
        owner_surface="execution JSONL and optional SQLite telemetry",
        input_contract_summary="Final execution log entry and compact row mapping.",
        output_contract_summary="JSONL event and optional RUN_COLUMNS-compatible SQLite row.",
        allowed_side_effects=("jsonl_write", "sqlite_write_when_existing_db_path_enabled"),
        safety_constraints=("Phase 19A must not change SQLite RUN_COLUMNS.",),
    ),
)


def get_module_registry() -> tuple[ModuleRegistryEntry, ...]:
    """Return static registry metadata."""
    return MODULE_REGISTRY


def get_module_entry(module_id: str) -> ModuleRegistryEntry:
    """Return one static module entry by id."""
    for entry in MODULE_REGISTRY:
        if entry.module_id == module_id:
            return entry
    raise KeyError(module_id)


__all__ = [
    "MODULE_REGISTRY",
    "ModuleKind",
    "ModuleRegistryEntry",
    "get_module_entry",
    "get_module_registry",
]
