"""Runtime input adapter for RunAuthority sufficiency judgment.

This module assembles compact, already-computed finalization facts into the
``RunSufficiencyJudgmentInput`` consumed by the bounded sufficiency executor. It
does not authorize actions, call models, reduce state, or decide sufficiency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.run_authority_sufficiency import (
    RunSufficiencyJudgmentInput,
    clean_text,
    clean_token,
    safe_json,
)
from core.sufficiency_semantic_state_consumption_runtime import (
    build_semantic_state_facts_for_sufficiency,
)

_COMPONENT_READINESS_INPUT_SCHEMA_VERSION = (
    "sufficiency_component_readiness_input_ag_readiness_01_v1"
)
_BINDING_BOOL_FIELDS = (
    "evidence_bound",
    "citation_bound",
    "source_obligation_bound",
    "answer_value_bound",
    "full_component_success",
    "partial_user_answer_candidate",
    "source_obligation_satisfied_from_ledger",
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    return [_mapping(item) for item in _list(value) if isinstance(item, Mapping)]


def _safe_bool(value: Any) -> bool:
    return True if value is True else False


def _safe_binding_status(value: Any) -> dict[str, Any]:
    binding = _mapping(value)
    out: dict[str, Any] = {}
    for field_name in _BINDING_BOOL_FIELDS:
        out[field_name] = _safe_bool(binding.get(field_name))
    for field_name in (
        "evidence_binding_status",
        "citation_binding_status",
        "source_obligation_binding_status",
        "answer_value_binding_status",
    ):
        token = clean_token(binding.get(field_name))
        if token:
            out[field_name] = token
    blockers = []
    for item in _list(binding.get("blocker_reasons")):
        token = clean_token(item)
        if token and token not in blockers:
            blockers.append(token)
    out["blocker_reasons"] = blockers
    out["component_candidate_link_ref_count"] = len(
        _mapping_list(binding.get("component_candidate_link_refs"))
    )
    out["component_custody_gap_ref_count"] = len(
        _mapping_list(binding.get("component_custody_gap_refs"))
    )
    return out


def _safe_ref_sequence(value: Any) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in _mapping_list(value):
        safe = safe_json(
            {
                key: item.get(key)
                for key in (
                    "component_id",
                    "candidate_id",
                    "source_obligation_id",
                    "custody_gap_id",
                    "gap_id",
                    "gap_type",
                    "required_source_class",
                    "source_class_hint",
                    "source_obligation_status",
                    "reason",
                    "domain",
                    "title",
                    "url",
                    "fetched",
                    "read",
                    "evidence_ledger_admitted",
                    "citation_eligible",
                    "source_obligation_satisfied",
                    "semantic_coverage",
                    "final_evidence",
                )
                if key in item
            }
        )
        if isinstance(safe, Mapping):
            refs.append(dict(safe))
    return refs


def _custody_by_component(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    custody_projection = _mapping(
        evidence_ledger_projection.get("component_scoped_source_custody")
    )
    return {
        str(item.get("component_id")): item
        for item in _mapping_list(custody_projection.get("per_component_custody"))
        if clean_token(item.get("component_id"))
    }


def _canonical_support_from_custody(custody: Mapping[str, Any]) -> dict[str, Any]:
    source_obligations = _mapping_list(custody.get("source_obligation_refs"))
    candidate_links = _mapping_list(custody.get("candidate_links"))
    custody_gaps = _mapping_list(custody.get("custody_gaps"))
    satisfied_obligations = [
        item
        for item in source_obligations
        if clean_token(item.get("source_obligation_status")) == "satisfied"
    ]
    admitted_candidates = [
        item
        for item in candidate_links
        if clean_token(item.get("admission_status")) in {"admitted", "accepted"}
    ]
    citation_eligible = [
        item
        for item in candidate_links
        if clean_token(item.get("citation_status")) == "citation_eligible"
    ]
    return {
        "source_obligation_satisfied": bool(
            source_obligations and len(satisfied_obligations) == len(source_obligations)
        ),
        "evidence_admitted": bool(admitted_candidates),
        "citation_eligible": bool(citation_eligible),
        "custody_gap_count": len(custody_gaps),
        "candidate_link_count": len(candidate_links),
        "source_obligation_count": len(source_obligations),
    }


def build_component_readiness_input_projection(
    *,
    answer_contract_authority_map_projection: Mapping[str, Any] | None,
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Build subordinate, non-authoritative component readiness input."""

    answer_map = _mapping(answer_contract_authority_map_projection)
    ledger = _mapping(evidence_ledger_projection)
    custody_projection = _mapping(ledger.get("component_scoped_source_custody"))
    ledger_custody_by_component = _custody_by_component(ledger)
    components: list[dict[str, Any]] = []
    for component in _mapping_list(answer_map.get("components")):
        component_id = clean_token(component.get("component_id"))
        if not component_id:
            continue
        binding = _mapping(component.get("binding_status"))
        evidence_custody = _mapping(component.get("evidence_custody"))
        ledger_custody = ledger_custody_by_component.get(component_id, {})
        component_candidate_refs = _safe_ref_sequence(
            binding.get("component_candidate_link_refs")
            or evidence_custody.get("component_candidate_link_refs")
            or ledger_custody.get("candidate_links")
        )
        component_gap_refs = _safe_ref_sequence(
            binding.get("component_custody_gap_refs")
            or evidence_custody.get("component_custody_gap_refs")
            or ledger_custody.get("custody_gaps")
        )
        component_source_obligation_refs = _safe_ref_sequence(
            evidence_custody.get("component_source_obligation_refs")
            or ledger_custody.get("source_obligation_refs")
        )
        blocker_reasons = []
        for item in (
            _list(binding.get("blocker_reasons"))
            + [gap.get("gap_type") for gap in component_gap_refs]
        ):
            token = clean_token(item)
            if token and token not in blocker_reasons:
                blocker_reasons.append(token)
        components.append(
            {
                "component_id": component_id,
                "label": clean_text(component.get("label"), limit=160),
                "answer_target": clean_text(component.get("answer_target"), limit=160),
                "expected_answerable": component.get("expected_answerable"),
                "binding_status": _safe_binding_status(binding),
                "canonical_support": _canonical_support_from_custody(ledger_custody),
                "component_candidate_link_refs": component_candidate_refs,
                "component_custody_gap_refs": component_gap_refs,
                "component_source_obligation_refs": component_source_obligation_refs,
                "blocker_reasons": blocker_reasons,
            }
        )
    return {
        "schema_version": _COMPONENT_READINESS_INPUT_SCHEMA_VERSION,
        "source": (
            "AnswerContractAuthorityMap.binding_status+"
            "EvidenceLedger.component_scoped_source_custody"
        ),
        "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "readiness_owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "final_packet_owner": "RunKernel.FinalAnswerPacket",
        "binding_input_owner": clean_token(answer_map.get("owner")),
        "binding_input_passive": True,
        "custody_owner": clean_token(custody_projection.get("owner")),
        "custody_canonical_state": custody_projection.get("canonical_state") is True,
        "component_count": len(components),
        "components": components,
        "partial_user_answer_candidate": False,
        "final_answer_allowed": False if components else None,
        "author_payload_ready": False if components else None,
    }


def build_sufficiency_judgment_input_from_runtime(
    *,
    contract_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    search_judgment_projection: Mapping[str, Any],
    search_judgment_history: Sequence[Mapping[str, Any]],
    answer_contract_projection: Mapping[str, Any],
    final_evidence_count: int,
    author_evidence_count: int,
    citation_eligible_candidate_count: int,
    conflicts_present: bool,
    scrutineer_flag_count: int,
    corpus_weak: bool,
    weak_corpus_reason: str | None,
    synth_was_insufficient: bool,
    failure_card_show: bool,
    failure_card_reason: str | None,
    iterations_run: int,
    max_iterations: int,
    recovery_attempt_count: int,
    initial_answer_contract: Mapping[str, Any] | None = None,
    current_answer_contract: Mapping[str, Any] | None = None,
    component_coverage_history: Sequence[Mapping[str, Any]] = (),
    contract_amendment_admission_history: Sequence[Mapping[str, Any]] = (),
    answer_contract_authority_map_projection: Mapping[str, Any] | None = None,
    multicomponent_graph_state: Mapping[str, Any] | None = None,
    multicomponent_recovery_state: Mapping[str, Any] | None = None,
    multicomponent_recovery_authorization_state: Mapping[str, Any] | None = None,
    multicomponent_scheduler_state: Mapping[str, Any] | None = None,
    searchos_existing_gap_recovery_terminal_state: (
        Mapping[str, Any] | None
    ) = None,
    run_id: str | None = None,
    request_id: str | None = None,
) -> RunSufficiencyJudgmentInput:
    """Build the AG-92C sufficiency input from runtime facts."""

    semantic_state_facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=initial_answer_contract or {},
        current_answer_contract=current_answer_contract or {},
        component_coverage_history=component_coverage_history,
        contract_amendment_admission_history=contract_amendment_admission_history,
        evidence_ledger_projection=evidence_ledger_projection,
        multicomponent_graph_state=multicomponent_graph_state,
    )

    return RunSufficiencyJudgmentInput(
        contract_projection=contract_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        search_judgment_projection=search_judgment_projection,
        search_judgment_history=search_judgment_history,
        answer_contract_projection=answer_contract_projection,
        source_obligation_projection=evidence_ledger_projection,
        final_evidence_facts={
            "final_evidence_count": final_evidence_count,
            "author_evidence_count": author_evidence_count,
            "citation_eligible_candidate_count": citation_eligible_candidate_count,
        },
        conflict_facts={
            "conflicts_present": bool(conflicts_present),
            "scrutineer_flag_count": scrutineer_flag_count,
            "conflict_posture": "unresolved" if conflicts_present else "none",
        },
        indirect_inference_facts={},
        weak_failure_facts={
            "corpus_weak": bool(corpus_weak),
            "weak_corpus_reason": weak_corpus_reason if corpus_weak else None,
            "synth_was_insufficient": bool(synth_was_insufficient),
            "failure_card": {
                "show": failure_card_show,
                "reason": failure_card_reason,
            },
        },
        budget={
            "iteration": iterations_run,
            "max_iterations": max_iterations,
            "remaining_budget": max(0, max_iterations - iterations_run),
            "recovery_attempts": recovery_attempt_count,
            "budget_exhausted": iterations_run >= max_iterations,
        },
        semantic_state_facts=semantic_state_facts,
        component_readiness_projection=build_component_readiness_input_projection(
            answer_contract_authority_map_projection=(
                answer_contract_authority_map_projection
            ),
            evidence_ledger_projection=evidence_ledger_projection,
        ),
        multicomponent_graph_state=_mapping(multicomponent_graph_state),
        multicomponent_recovery_state=_mapping(multicomponent_recovery_state),
        multicomponent_recovery_authorization_state=_mapping(
            multicomponent_recovery_authorization_state
        ),
        multicomponent_scheduler_state=_mapping(multicomponent_scheduler_state),
        searchos_existing_gap_recovery_terminal_state=_mapping(
            searchos_existing_gap_recovery_terminal_state
        ),
        run_identity={"run_id": run_id, "request_id": request_id},
    )


__all__ = [
    "build_component_readiness_input_projection",
    "build_sufficiency_judgment_input_from_runtime",
]
