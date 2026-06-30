"""Default-off ordinary live authority consolidation precondition.

This helper consumes the in-memory ordinary semantic coverage result produced
by the bounded child RunKernel and inspects the main ordinary answer RunKernel
for a readiness-compatible component binding. It does not mutate RunKernel
state, rehydrate from trace projections, reduce SufficiencyReadiness, create a
FinalAnswerPacket, create Author input, render citations, satisfy source
obligations, or call providers/search/brokers/fetch/read/models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.run_kernel import RunKernel

ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY = (
    "ordinary_live_authority_consolidation"
)
ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_PHASE = (
    "AG-ORDINARY-LIVE-AUTHORITY-CONSOLIDATION-AND-READINESS-"
    "PRECONDITION-01"
)
ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_MODE = "REPAIR"

_READINESS_BLOCKER = "coverage_not_bound_to_main_answer_readiness_component"
_MISSING_MAIN_BINDING_BLOCKER = "main_answer_component_binding_missing"
_EQUIVALENCE_BLOCKER = "main_answer_component_equivalence_not_established"
_TRANSFER_REDUCER_BLOCKER = "child_to_parent_component_coverage_transfer_reducer_missing"

_CHILD_OWNER = "ordinary_live_candidate_handoff_run_kernel"
_CHILD_DEBT = (
    "Bounded child RunKernel owns candidate/source/semantic coverage for this "
    "ordinary-live chain only temporarily; main-answer readiness still requires "
    "a canonical main RunKernel component binding/reducer."
)
_CONSOLIDATION_PATH = (
    "Next checkpoint must decide or implement a canonical child-to-main "
    "component coverage authority reducer before SufficiencyReadiness/FAP/"
    "AuthorProse may consume this chain."
)

_DIAGNOSTIC_AUTHORITY_KEYS = frozenset(
    {
        "ordinary_retrieval_results",
        "provider_diagnostic",
        "provider_diagnostics",
        "retrieval_diagnostic",
        "retrieval_diagnostics",
        "retrieval_result",
        "retrieval_results",
        "search_diagnostic",
        "search_diagnostics",
        "top_passage",
        "top_passages",
    }
)
_FORBIDDEN_TRACE_KEYS = frozenset(
    {
        "answer",
        "answer_text",
        "author",
        "author_input",
        "author_material",
        "body",
        "bounded_text",
        "citation",
        "citation_record",
        "citation_records",
        "citations",
        "cookie",
        "cookies",
        "fap",
        "final_answer",
        "final_answer_packet",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_headers",
        "raw_html",
        "raw_model_response",
        "raw_page_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "source_obligation_satisfaction",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)
_CLOSED_FALSE_FLAGS = {
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "citation_created": False,
    "citation_rendered": False,
    "sufficiency_readiness_reduced": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "answer_text_created": False,
    "product_correctness_claimed": False,
}
_NON_PROOFS = (
    "no live provider/search/broker/fetch/model call",
    "no execution_trace projection consumed as authority",
    "no projection-to-RunKernel rehydration",
    "no direct RunKernel state mutation",
    "no child coverage promotion to main-answer readiness by assertion",
    "no source-obligation satisfaction",
    "no citation eligibility or citation rendering",
    "no SufficiencyReadiness reduction",
    "no FinalAnswerPacket",
    "no Author or AuthorProse behavior",
    "no answer text or product correctness claim",
)


class OrdinaryLiveAuthorityConsolidationError(ValueError):
    """Raised internally when consolidation must fail closed."""

    def __init__(self, first_failed_seam: str, message: str) -> None:
        super().__init__(message)
        self.first_failed_seam = first_failed_seam


@dataclass(frozen=True, slots=True)
class OrdinaryLiveAuthorityConsolidationResult:
    projection: dict[str, Any]


def ordinary_live_authority_consolidation_disabled_projection() -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY,
        "phase": ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_PHASE,
        "mode": ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_MODE,
        "enabled": False,
        "ran": False,
        "failed_closed": False,
        "status": "disabled",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
    }


def execute_ordinary_live_authority_consolidation(
    *,
    main_run_kernel: RunKernel | None,
    child_run_kernel: RunKernel | None,
    semantic_coverage_result: Any | None,
) -> OrdinaryLiveAuthorityConsolidationResult:
    """Assess whether child coverage can become a main readiness component."""

    base = _base_projection()
    child_coverage_ref: dict[str, Any] = {}
    child_component_ref: dict[str, Any] = {}
    main_component_ref: dict[str, Any] = {}
    try:
        if semantic_coverage_result is None:
            raise OrdinaryLiveAuthorityConsolidationError(
                "ordinary_live_semantic_coverage_result_missing",
                "ordinary authority consolidation requires the in-memory "
                "semantic coverage result",
            )
        if isinstance(semantic_coverage_result, Mapping):
            _reject_diagnostic_authority_keys(
                semantic_coverage_result,
                context="ordinary authority consolidation semantic result",
            )
            raise OrdinaryLiveAuthorityConsolidationError(
                "ordinary_live_semantic_coverage_result_object_missing",
                "ordinary authority consolidation requires the semantic coverage "
                "result object, not a trace/projection mapping",
            )
        if main_run_kernel is None:
            raise OrdinaryLiveAuthorityConsolidationError(
                "main_answer_run_kernel_missing",
                "ordinary authority consolidation requires the main answer RunKernel",
            )
        if child_run_kernel is None:
            raise OrdinaryLiveAuthorityConsolidationError(
                "ordinary_candidate_handoff_run_kernel_missing",
                "ordinary authority consolidation requires the in-memory child "
                "RunKernel that reduced semantic coverage",
            )

        semantic_projection = _safe_mapping(
            getattr(semantic_coverage_result, "projection", None)
        )
        _reject_diagnostic_authority_keys(
            semantic_projection,
            context="ordinary semantic coverage projection",
        )
        if semantic_projection.get("failed_closed") is True:
            raise OrdinaryLiveAuthorityConsolidationError(
                "ordinary_live_semantic_coverage_failed_closed",
                "ordinary authority consolidation requires successful semantic coverage",
            )
        object_coverage = _safe_mapping(
            getattr(semantic_coverage_result, "component_coverage_projection", None)
        )
        child_coverage = _safe_mapping(child_run_kernel.state.component_coverage_projection)
        if not object_coverage or not child_coverage:
            raise OrdinaryLiveAuthorityConsolidationError(
                "child_component_coverage_missing",
                "ordinary authority consolidation requires in-memory child "
                "ComponentCoverage",
            )
        _require_same_child_coverage(
            object_coverage=object_coverage,
            child_coverage=child_coverage,
        )
        child_coverage_ref = _coverage_ref(child_coverage)
        child_component_ref = _child_component_ref(child_run_kernel, child_coverage)
        main_components = _main_answer_components(main_run_kernel)
        equivalence = _component_equivalence(
            child_component_ref=child_component_ref,
            main_components=main_components,
        )
        main_component_ref = dict(equivalence["main_answer_component_ref"])
        blocker = _readiness_blocker(
            equivalence_posture=str(equivalence["component_equivalence_posture"]),
            main_components=main_components,
        )
        projection = _without_empty(
            {
                **base,
                "ran": True,
                "failed_closed": True,
                "status": "blocked",
                "first_failed_seam": blocker,
                "failure_reason": _blocker_reason(blocker),
                "source_semantic_coverage_result_object_consumed": True,
                "projection_consumed_as_authority": False,
                "child_kernel_consumed_in_memory": True,
                "semantic_coverage_result_object_type": (
                    type(semantic_coverage_result).__name__
                ),
                "child_coverage_ref": child_coverage_ref,
                "child_component_ref": child_component_ref,
                "main_answer_component_candidate_count": len(main_components),
                "main_answer_component_candidate_ref": main_component_ref,
                "component_equivalence_posture": equivalence[
                    "component_equivalence_posture"
                ],
                "binding_basis": equivalence["binding_basis"],
                "semantic_equivalence_posture": equivalence[
                    "component_equivalence_posture"
                ],
                "safe_binding_created": False,
                "authority_consolidation_status": _authority_status(blocker),
                "readiness_precondition_status": "not_met",
                "readiness_blocker_if_any": blocker,
                "legacy_readiness_blocker": _READINESS_BLOCKER,
                "future_sufficiency_readiness_may_consume": False,
                "future_final_answer_packet_may_consume": False,
                "future_author_may_consume": False,
                "future_readiness_fap_author_eligibility": False,
                "precondition_binding_record_ref": {},
                "precondition_binding_record_authoritative": False,
                "precondition_binding_record_changes_future_readiness_eligibility": (
                    False
                ),
                "named_future_consumer": "none_currently",
                "named_future_consumer_exists": False,
                "missing_architecture_decision": (
                    "canonical child-to-main answer component coverage transfer "
                    "and readiness consumer"
                ),
                "mandatory_next_checkpoint": (
                    "AG-ORDINARY-LIVE-MAIN-COMPONENT-BINDING-AUTHORITY-"
                    "DECISION-01"
                ),
                **_child_kernel_debt_projection(),
                **_closed_surface_counts(),
                "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
                **_CLOSED_FALSE_FLAGS,
                "explicit_non_proofs": list(_NON_PROOFS),
            }
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveAuthorityConsolidationResult(projection=projection)
    except OrdinaryLiveAuthorityConsolidationError as exc:
        projection = _fail_projection(
            base,
            exc.first_failed_seam,
            str(exc),
            child_coverage_ref=child_coverage_ref,
            child_component_ref=child_component_ref,
            main_component_ref=main_component_ref,
            child_kernel_consumed=child_run_kernel is not None,
        )
        _assert_safe_projection(projection)
        return OrdinaryLiveAuthorityConsolidationResult(projection=projection)


def _base_projection() -> dict[str, Any]:
    return {
        "trace_key": ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY,
        "phase": ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_PHASE,
        "mode": ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_MODE,
        "repair_verdict_target": "YES_OR_NO_BUT_JUSTIFIED",
        "enabled": True,
        "ran": False,
        "failed_closed": False,
        "first_failed_seam": None,
        "status": "not_run",
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
        "product_path_affected": "ordinary run_pipeline",
        "default_disabled": True,
        "source_semantic_coverage_result_object_consumed": False,
        "projection_consumed_as_authority": False,
        "child_kernel_consumed_in_memory": False,
        "projection_to_runkernel_rehydration": False,
        "direct_runkernel_mutation": False,
        "retrieval_diagnostics_used_as_authority": False,
        "diagnostic_provider_fields_used_as_authority": False,
        "product_code_imports_scripts_ag": False,
        **_zero_call_counts(),
    }


def _fail_projection(
    base: Mapping[str, Any],
    first_failed_seam: str,
    reason: str,
    *,
    child_coverage_ref: Mapping[str, Any],
    child_component_ref: Mapping[str, Any],
    main_component_ref: Mapping[str, Any],
    child_kernel_consumed: bool,
) -> dict[str, Any]:
    return _without_empty(
        {
            **dict(base),
            "ran": False,
            "failed_closed": True,
            "status": "failed_closed",
            "first_failed_seam": first_failed_seam,
            "failure_reason": _clean_text(reason, limit=420),
            "projection_consumed_as_authority": False,
            "child_kernel_consumed_in_memory": bool(child_kernel_consumed),
            "child_coverage_ref": dict(child_coverage_ref),
            "child_component_ref": dict(child_component_ref),
            "main_answer_component_candidate_ref": dict(main_component_ref),
            "component_equivalence_posture": (
                "unknown_requires_architecture_decision"
            ),
            "binding_basis": "none",
            "semantic_equivalence_posture": (
                "unknown_requires_architecture_decision"
            ),
            "safe_binding_created": False,
            "authority_consolidation_status": "failed_closed",
            "readiness_precondition_status": "not_met",
            "readiness_blocker_if_any": first_failed_seam,
            "legacy_readiness_blocker": _READINESS_BLOCKER,
            "future_sufficiency_readiness_may_consume": False,
            "future_final_answer_packet_may_consume": False,
            "future_author_may_consume": False,
            "future_readiness_fap_author_eligibility": False,
            "precondition_binding_record_ref": {},
            "precondition_binding_record_authoritative": False,
            "precondition_binding_record_changes_future_readiness_eligibility": (
                False
            ),
            "named_future_consumer": "none_currently",
            "named_future_consumer_exists": False,
            "mandatory_next_checkpoint": (
                "AG-ORDINARY-LIVE-MAIN-COMPONENT-BINDING-AUTHORITY-"
                "DECISION-01"
            ),
            **_child_kernel_debt_projection(),
            **_closed_surface_counts(),
            "closed_surface_flags": dict(_CLOSED_FALSE_FLAGS),
            **_CLOSED_FALSE_FLAGS,
            "explicit_non_proofs": list(_NON_PROOFS),
            **_zero_call_counts(),
        }
    )


def _require_same_child_coverage(
    *,
    object_coverage: Mapping[str, Any],
    child_coverage: Mapping[str, Any],
) -> None:
    for key in (
        "coverage_record_id",
        "coverage_record_digest",
        "coverage_reduction_digest",
        "answer_component_id",
        "component_revision",
        "component_digest",
    ):
        if _clean_text(object_coverage.get(key), limit=220) != _clean_text(
            child_coverage.get(key),
            limit=220,
        ):
            raise OrdinaryLiveAuthorityConsolidationError(
                "semantic_coverage_result_child_kernel_mismatch",
                "semantic coverage result does not match child RunKernel "
                f"coverage field {key}",
            )


def _coverage_ref(coverage: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "coverage_record_id": coverage.get("coverage_record_id"),
            "coverage_record_digest": coverage.get("coverage_record_digest"),
            "coverage_reduction_digest": coverage.get("coverage_reduction_digest"),
            "answer_component_id": coverage.get("answer_component_id"),
            "component_revision": coverage.get("component_revision"),
            "component_digest": coverage.get("component_digest"),
            "coverage_state": coverage.get("coverage_state"),
            "semantic_support_status": coverage.get("semantic_support_status"),
            "source_obligation_status": coverage.get("source_obligation_status"),
        }
    )


def _child_component_ref(
    child_run_kernel: RunKernel,
    child_coverage: Mapping[str, Any],
) -> dict[str, Any]:
    component_id = _clean_text(child_coverage.get("answer_component_id"), limit=220)
    component = _component_from_contracts(child_run_kernel, component_id)
    return _component_ref(
        component,
        fallback={
            "component_id": component_id,
            "component_revision": child_coverage.get("component_revision"),
            "component_digest": child_coverage.get("component_digest"),
            "contract_kind": "bounded_child_candidate_source_custody_component",
        },
    )


def _main_answer_components(main_run_kernel: RunKernel) -> list[dict[str, Any]]:
    contract = (
        _safe_mapping(main_run_kernel.state.current_answer_contract)
        or _safe_mapping(main_run_kernel.state.initial_answer_contract)
    )
    refs = _safe_list(contract.get("accepted_answer_component_refs"))
    return [
        _component_ref(
            item,
            fallback={"contract_kind": "main_ordinary_answer_component"},
        )
        for item in refs
        if isinstance(item, Mapping) and _clean_text(item.get("component_id"))
    ]


def _component_equivalence(
    *,
    child_component_ref: Mapping[str, Any],
    main_components: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    child_id = _clean_text(child_component_ref.get("component_id"), limit=220)
    child_digest = _clean_text(child_component_ref.get("component_digest"), limit=128)
    for component in main_components:
        main_id = _clean_text(component.get("component_id"), limit=220)
        main_digest = _clean_text(component.get("component_digest"), limit=128)
        if child_id and child_digest and child_id == main_id and child_digest == main_digest:
            return {
                "component_equivalence_posture": "equivalent_by_component_id_and_digest",
                "binding_basis": "component_id_and_digest_exact_match",
                "main_answer_component_ref": _component_ref(component),
            }
    if not main_components:
        return {
            "component_equivalence_posture": "unknown_requires_architecture_decision",
            "binding_basis": "main_answer_component_absent",
            "main_answer_component_ref": {},
        }
    for component in main_components:
        if child_id and child_id == _clean_text(component.get("component_id"), limit=220):
            return {
                "component_equivalence_posture": "unknown_requires_architecture_decision",
                "binding_basis": "component_id_match_without_digest_match",
                "main_answer_component_ref": _component_ref(component),
            }
    return {
        "component_equivalence_posture": "not_equivalent",
        "binding_basis": "no_canonical_component_id_digest_match",
        "main_answer_component_ref": _component_ref(main_components[0]),
    }


def _readiness_blocker(
    *,
    equivalence_posture: str,
    main_components: Sequence[Mapping[str, Any]],
) -> str:
    if not main_components:
        return _MISSING_MAIN_BINDING_BLOCKER
    if equivalence_posture == "equivalent_by_component_id_and_digest":
        return _TRANSFER_REDUCER_BLOCKER
    return _EQUIVALENCE_BLOCKER


def _authority_status(blocker: str) -> str:
    if blocker == _TRANSFER_REDUCER_BLOCKER:
        return "blocked_missing_child_to_parent_reducer"
    if blocker == _MISSING_MAIN_BINDING_BLOCKER:
        return "blocked_missing_main_answer_component_binding"
    return "blocked_component_equivalence_not_established"


def _blocker_reason(blocker: str) -> str:
    if blocker == _MISSING_MAIN_BINDING_BLOCKER:
        return (
            "main ordinary RunKernel has no readiness-compatible accepted answer "
            "component binding at the consolidation point"
        )
    if blocker == _TRANSFER_REDUCER_BLOCKER:
        return (
            "component identity matches, but no canonical reducer currently "
            "transfers child coverage into main RunKernel readiness state"
        )
    if blocker == _EQUIVALENCE_BLOCKER:
        return (
            "child coverage cannot be proven equivalent to a main answer "
            "component by canonical id/digest/contract refs"
        )
    return blocker


def _component_from_contracts(
    run_kernel: RunKernel,
    component_id: str | None,
) -> dict[str, Any]:
    if not component_id:
        return {}
    for contract in (
        _safe_mapping(run_kernel.state.current_answer_contract),
        _safe_mapping(run_kernel.state.initial_answer_contract),
    ):
        for item in _safe_list(contract.get("accepted_answer_component_refs")):
            if isinstance(item, Mapping) and item.get("component_id") == component_id:
                return dict(item)
    return {}


def _component_ref(
    component: Mapping[str, Any] | None,
    fallback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = {**dict(fallback or {}), **_safe_mapping(component)}
    return _without_empty(
        {
            "component_id": source.get("component_id")
            or source.get("answer_component_id"),
            "component_revision": source.get("component_revision"),
            "component_digest": source.get("component_digest")
            or source.get("component_contract_digest"),
            "component_label": source.get("user_facing_label")
            or source.get("label"),
            "component_question": source.get("user_facing_question")
            or source.get("question")
            or source.get("answer_target"),
            "contract_kind": source.get("contract_kind"),
            "requirement_posture": source.get("requirement_posture"),
            "materiality": source.get("materiality"),
            "prohibited_upgrades": _safe_list(source.get("prohibited_upgrades")),
            "mandatory_caveats": _safe_list(source.get("mandatory_caveats")),
        }
    )


def _child_kernel_debt_projection() -> dict[str, Any]:
    return {
        "child_kernel_owner": _CHILD_OWNER,
        "child_kernel_temporary_architecture_debt": True,
        "child_kernel_debt_summary": _CHILD_DEBT,
        "child_kernel_consolidation_path": _CONSOLIDATION_PATH,
    }


def _zero_call_counts() -> dict[str, int]:
    return {
        "provider_search_calls": 0,
        "search_calls": 0,
        "broker_calls": 0,
        "fetch_read_calls": 0,
        "model_calls": 0,
        "retrieval_calls": 0,
    }


def _closed_surface_counts() -> dict[str, int]:
    return {
        **_zero_call_counts(),
        "source_obligation_satisfaction_decisions": 0,
        "citation_eligibility_decisions": 0,
        "citation_rendering_decisions": 0,
        "sufficiency_readiness_reductions": 0,
        "final_answer_packet_creations": 0,
        "author_authorprose_invocations": 0,
        "answer_text_creations": 0,
        "product_correctness_claims": 0,
    }


def _reject_diagnostic_authority_keys(value: Any, *, context: str) -> None:
    diagnostic = sorted(_collect_keys(value) & _DIAGNOSTIC_AUTHORITY_KEYS)
    if diagnostic:
        raise OrdinaryLiveAuthorityConsolidationError(
            "diagnostic_consolidation_authority_rejected",
            f"{context} includes diagnostic-shaped authority fields: "
            + ", ".join(diagnostic),
        )


def _assert_safe_projection(projection: Mapping[str, Any]) -> None:
    forbidden = sorted(_collect_keys(projection) & _FORBIDDEN_TRACE_KEYS)
    if forbidden:
        raise OrdinaryLiveAuthorityConsolidationError(
            "ordinary_live_authority_consolidation_projection_unsafe",
            "ordinary authority consolidation projection includes forbidden fields: "
            + ", ".join(forbidden),
        )


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        return dict(mapped) if isinstance(mapped, Mapping) else {}
    return {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    return text[:limit]


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


__all__ = [
    "ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_MODE",
    "ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_PHASE",
    "ORDINARY_LIVE_AUTHORITY_CONSOLIDATION_TRACE_KEY",
    "OrdinaryLiveAuthorityConsolidationResult",
    "execute_ordinary_live_authority_consolidation",
    "ordinary_live_authority_consolidation_disabled_projection",
]
