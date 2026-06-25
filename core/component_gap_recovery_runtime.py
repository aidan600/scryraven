"""Mode-neutral authorized component-gap recovery runtime.

The runtime executes exactly one already-authorized component-gap recovery
cycle. Mode-specific policy decides whether the primitive is allowed and how
many cycles may run; the primitive itself only enforces the shared custody and
semantic-state mechanics.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.ordinary_semantic_producer_runtime import (
    BindableFinalPassage,
    build_component_coverage_proposal,
    build_semantic_observation_and_content_refs,
)
from core.provider_job_evidence_ledger_bridge import (
    build_provider_job_evidence_ledger_observation,
)
from core.sufficiency_semantic_state_consumption_runtime import (
    build_semantic_state_facts_for_sufficiency,
    evaluate_semantic_sufficiency_overlay,
)

COMPONENT_GAP_RECOVERY_TRACE_KEY = "component_gap_recovery_runtime"
COMPONENT_GAP_RECOVERY_OWNER = "ComponentGapRecoveryRuntime"
COMPONENT_GAP_RECOVERY_SCHEMA_VERSION = "component_gap_recovery_runtime_v1"


class ComponentGapRecoveryStatus(str, Enum):
    """Outcome vocabulary for one authorized component-gap recovery attempt."""

    NOT_APPLICABLE = "not_applicable"
    BLOCKED = "blocked"
    ATTEMPTED_NO_COVERAGE = "attempted_no_coverage"
    RECOVERED = "recovered"


@dataclass(frozen=True, slots=True)
class ComponentGapRecoveryPolicy:
    """Permission and budget envelope supplied by a mode policy."""

    policy_label: str
    requested_mode: str
    allowed_requested_modes: tuple[str, ...] = field(default_factory=tuple)
    max_cycles: int = 1
    offline_only: bool = True
    existing_candidate_query_only: bool = True
    model_generated_query_text_allowed: bool = False
    provider_live_calls_allowed: bool = False
    accepted_amendments_allowed: bool = False
    deep_reconciliation_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_label": self.policy_label,
            "requested_mode": self.requested_mode,
            "allowed_requested_modes": list(self.allowed_requested_modes),
            "max_cycles": int(self.max_cycles),
            "offline_only": bool(self.offline_only),
            "existing_candidate_query_only": bool(
                self.existing_candidate_query_only
            ),
            "model_generated_query_text_allowed": bool(
                self.model_generated_query_text_allowed
            ),
            "provider_live_calls_allowed": bool(self.provider_live_calls_allowed),
            "accepted_amendments_allowed": bool(
                self.accepted_amendments_allowed
            ),
            "deep_reconciliation_allowed": bool(self.deep_reconciliation_allowed),
        }


@dataclass(frozen=True, slots=True)
class ComponentGapRecoveryResult:
    """Compact result returned to the ordinary product path."""

    status: ComponentGapRecoveryStatus
    stop_reason: str
    budget_record: Mapping[str, Any]
    recovered_passages: tuple[dict[str, Any], ...] = ()
    evidence_ledger_projection: Mapping[str, Any] | None = None
    semantic_state_facts: Mapping[str, Any] | None = None

    @property
    def recovered(self) -> bool:
        return self.status is ComponentGapRecoveryStatus.RECOVERED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "stop_reason": self.stop_reason,
            "budget_record": dict(self.budget_record),
            "recovered_passage_count": len(self.recovered_passages),
            "evidence_ledger_digest": (
                self.evidence_ledger_projection or {}
            ).get("ledger_digest"),
            "semantic_state_facts_digest": (
                self.semantic_state_facts or {}
            ).get("semantic_state_facts_digest"),
        }


@dataclass(frozen=True, slots=True)
class ComponentGapRecoveryHandoff:
    """Canonical product handoff after recovered semantic coverage succeeds."""

    all_passages: tuple[dict[str, Any], ...]
    evidence_ledger_projection: Mapping[str, Any] | None
    final_evidence_rebuild_required: bool = True
    semantic_binding_committed: bool = True


def build_component_gap_recovery_handoff(
    *,
    result: ComponentGapRecoveryResult,
    all_passages: Sequence[Mapping[str, Any]],
) -> ComponentGapRecoveryHandoff:
    """Return recovered passages for ordinary final-evidence rebuilding."""

    recovered_passages = [dict(item) for item in result.recovered_passages]
    merged_all_passages = [*(dict(item) for item in all_passages), *recovered_passages]
    return ComponentGapRecoveryHandoff(
        all_passages=tuple(merged_all_passages),
        evidence_ledger_projection=result.evidence_ledger_projection,
    )


def execute_authorized_component_gap_recovery(
    *,
    run_kernel: Any,
    policy: ComponentGapRecoveryPolicy,
    query_plan_trace: Mapping[str, Any] | None,
    search_judgment_projection: Mapping[str, Any] | None,
    evidence_ledger_projection: Mapping[str, Any] | None,
    search_work_projection: Mapping[str, Any] | None,
    offline_recovery_adapter: Callable[..., Any] | None,
    runtime_context: Mapping[str, Any] | None = None,
    seen_urls: set[str] | None = None,
) -> ComponentGapRecoveryResult:
    """Execute one shared, authorized, offline component-gap recovery cycle."""

    context = dict(runtime_context or {})
    query_plan = _extract_query_plan(query_plan_trace)
    accepted_contract = _accepted_contract(run_kernel)
    history = _history(run_kernel)
    attempted_cycles = _attempted_cycle_count(history)

    policy_blocker = _policy_blocker(policy)
    if policy_blocker:
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason=policy_blocker,
            attempted_cycles=attempted_cycles,
        )

    if not accepted_contract:
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.NOT_APPLICABLE,
            stop_reason="accepted_contract_absent",
            attempted_cycles=attempted_cycles,
        )

    if policy.max_cycles <= attempted_cycles:
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason="cycle_budget_exhausted",
            attempted_cycles=attempted_cycles,
        )

    if _has_pre_recovery_final_answer_packet(run_kernel):
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason="pre_recovery_final_answer_packet_already_present",
            attempted_cycles=attempted_cycles,
        )

    if (
        getattr(run_kernel.state, "contract_amendment_admission_history", None)
        and not policy.accepted_amendments_allowed
    ):
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason="accepted_amendments_closed_by_policy",
            attempted_cycles=attempted_cycles,
        )

    gap_result = _single_component_gap(
        run_kernel=run_kernel,
        accepted_contract=accepted_contract,
        evidence_ledger_projection=evidence_ledger_projection,
    )
    if gap_result.get("stop_reason"):
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.NOT_APPLICABLE,
            stop_reason=str(gap_result["stop_reason"]),
            attempted_cycles=attempted_cycles,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
        )
    component_gap = dict(gap_result["component_gap"])
    component_ref = dict(gap_result["component_ref"])

    judgment_blocker = _search_judgment_gap_blocker(
        search_judgment_projection=search_judgment_projection,
        component_gap=component_gap,
    )
    if judgment_blocker:
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason=judgment_blocker,
            attempted_cycles=attempted_cycles,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
        )

    query_result = _authorized_existing_query(
        query_plan=query_plan,
        component_gap=component_gap,
    )
    if query_result.get("stop_reason"):
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason=str(query_result["stop_reason"]),
            attempted_cycles=attempted_cycles,
            component_gap=component_gap,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
        )
    authorized_query = str(query_result["authorized_query"])
    query_metadata = dict(query_result.get("query_metadata") or {})
    idempotency_key = _idempotency_key(
        accepted_contract=accepted_contract,
        component_gap=component_gap,
        authorized_query=authorized_query,
    )
    if any(item.get("idempotency_key") == idempotency_key for item in history):
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason="duplicate_recovery_cycle",
            attempted_cycles=attempted_cycles,
            component_gap=component_gap,
            authorized_query=authorized_query,
            idempotency_key=idempotency_key,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
        )

    if offline_recovery_adapter is None:
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.BLOCKED,
            stop_reason="offline_recovery_adapter_absent",
            attempted_cycles=attempted_cycles,
            component_gap=component_gap,
            authorized_query=authorized_query,
            idempotency_key=idempotency_key,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
        )

    raw_passages = _call_offline_adapter(
        adapter=offline_recovery_adapter,
        authorized_query=authorized_query,
        component_gap=component_gap,
        policy=policy,
        context=context,
        seen_urls=seen_urls,
    )
    annotated_passages = _annotated_recovery_passages(
        passages=raw_passages,
        accepted_contract=accepted_contract,
        component_gap=component_gap,
        component_ref=component_ref,
        query_metadata=query_metadata,
        authorized_query=authorized_query,
        idempotency_key=idempotency_key,
    )
    if not annotated_passages:
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.ATTEMPTED_NO_COVERAGE,
            stop_reason="offline_recovery_returned_no_evidence",
            attempted_cycles=attempted_cycles + 1,
            component_gap=component_gap,
            authorized_query=authorized_query,
            idempotency_key=idempotency_key,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
            adapter_invoked=True,
        )

    ledger_result = _admit_recovery_evidence(
        run_kernel=run_kernel,
        run_id=str(getattr(run_kernel.state, "run_id", "")),
        query_plan=query_plan,
        search_work_projection=search_work_projection,
        authorized_query=authorized_query,
        component_gap=component_gap,
        component_ref=component_ref,
        query_metadata=query_metadata,
        annotated_passages=annotated_passages,
        idempotency_key=idempotency_key,
    )
    evidence_projection = dict(ledger_result.get("evidence_ledger_projection") or {})
    if not evidence_projection:
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.ATTEMPTED_NO_COVERAGE,
            stop_reason=str(ledger_result.get("stop_reason") or "ledger_admission_failed"),
            attempted_cycles=attempted_cycles + 1,
            component_gap=component_gap,
            authorized_query=authorized_query,
            idempotency_key=idempotency_key,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
            adapter_invoked=True,
        )

    coverage_result = _admit_semantic_component_coverage(
        run_kernel=run_kernel,
        accepted_contract=accepted_contract,
        component_ref=component_ref,
        evidence_ledger_projection=evidence_projection,
        annotated_passages=annotated_passages,
        authorized_query=authorized_query,
        idempotency_key=idempotency_key,
        original_query=str(context.get("query") or ""),
    )
    if coverage_result.get("stop_reason"):
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.ATTEMPTED_NO_COVERAGE,
            stop_reason=str(coverage_result["stop_reason"]),
            attempted_cycles=attempted_cycles + 1,
            component_gap=component_gap,
            authorized_query=authorized_query,
            idempotency_key=idempotency_key,
            evidence_ledger_projection=evidence_projection,
            semantic_state_facts=gap_result.get("semantic_state_facts"),
            adapter_invoked=True,
        )

    post_facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=run_kernel.state.initial_answer_contract,
        component_coverage_history=run_kernel.state.component_coverage_history,
        contract_amendment_admission_history=(
            run_kernel.state.contract_amendment_admission_history
        ),
        evidence_ledger_projection=run_kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    if _component_still_missing(post_facts, component_ref):
        return _record_and_result(
            run_kernel=run_kernel,
            policy=policy,
            status=ComponentGapRecoveryStatus.ATTEMPTED_NO_COVERAGE,
            stop_reason="semantic_coverage_recheck_failed",
            attempted_cycles=attempted_cycles + 1,
            component_gap=component_gap,
            authorized_query=authorized_query,
            idempotency_key=idempotency_key,
            evidence_ledger_projection=run_kernel.state.evidence_ledger.to_projection().to_dict(),
            semantic_state_facts=post_facts,
            adapter_invoked=True,
        )

    return _record_and_result(
        run_kernel=run_kernel,
        policy=policy,
        status=ComponentGapRecoveryStatus.RECOVERED,
        stop_reason="recovered",
        attempted_cycles=attempted_cycles + 1,
        component_gap=component_gap,
        authorized_query=authorized_query,
        idempotency_key=idempotency_key,
        evidence_ledger_projection=run_kernel.state.evidence_ledger.to_projection().to_dict(),
        semantic_state_facts=post_facts,
        recovered_passages=annotated_passages,
        adapter_invoked=True,
    )


def _policy_blocker(policy: ComponentGapRecoveryPolicy) -> str | None:
    mode = str(policy.requested_mode or "")
    allowed = {str(item) for item in policy.allowed_requested_modes or ()}
    if allowed and mode not in allowed:
        return "requested_mode_not_allowed"
    if int(policy.max_cycles or 0) <= 0:
        return "cycle_budget_absent"
    if not policy.offline_only:
        return "non_offline_recovery_not_implemented"
    if not policy.existing_candidate_query_only:
        return "generated_or_new_query_recovery_closed"
    if policy.model_generated_query_text_allowed:
        return "model_generated_query_text_closed"
    if policy.provider_live_calls_allowed:
        return "provider_live_calls_closed"
    if policy.deep_reconciliation_allowed:
        return "deep_reconciliation_closed"
    return None


def _accepted_contract(run_kernel: Any) -> dict[str, Any]:
    contract = getattr(run_kernel.state, "initial_answer_contract", None)
    if isinstance(contract, Mapping):
        accepted_contract_digest = _clean_token(
            contract.get("accepted_contract_digest")
        )
        accepted_contract_version = _clean_token(
            contract.get("accepted_contract_version")
        )
        if accepted_contract_digest and accepted_contract_version:
            return dict(contract)
    return {}


def _single_component_gap(
    *,
    run_kernel: Any,
    accepted_contract: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any] | None,
) -> dict[str, Any]:
    facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=accepted_contract,
        component_coverage_history=run_kernel.state.component_coverage_history,
        contract_amendment_admission_history=(
            run_kernel.state.contract_amendment_admission_history
        ),
        evidence_ledger_projection=evidence_ledger_projection
        or run_kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    overlay = evaluate_semantic_sufficiency_overlay(facts)
    blockers = [
        dict(item)
        for item in facts.get("blockers") or ()
        if isinstance(item, Mapping)
    ]
    non_missing_blockers = [
        blocker
        for blocker in blockers
        if _clean_token(blocker.get("code")) != "missing_required_component_coverage"
    ]
    if non_missing_blockers:
        return {
            "stop_reason": "semantic_state_has_non_recoverable_blockers",
            "semantic_state_facts": facts,
        }
    gaps = [
        dict(item)
        for item in overlay.missing_assessments
        if isinstance(item, Mapping)
        and _clean_token(item.get("semantic_gap_code"))
        == "missing_required_component_coverage"
        and _clean_token(item.get("requirement_kind"))
        == "semantic_component_coverage"
    ]
    if len(gaps) == 0:
        return {
            "stop_reason": "no_single_component_gap",
            "semantic_state_facts": facts,
        }
    if len(gaps) > 1:
        return {
            "stop_reason": "multiple_component_gaps",
            "semantic_state_facts": facts,
        }
    gap = gaps[0]
    component_ref = _component_ref(
        accepted_contract,
        _clean_token(gap.get("answer_component_id") or gap.get("component_id")),
    )
    if not component_ref:
        return {
            "stop_reason": "component_gap_ref_absent",
            "semantic_state_facts": facts,
        }
    if _clean_token(component_ref.get("component_digest")) != _clean_token(
        gap.get("component_digest")
    ):
        return {
            "stop_reason": "component_gap_digest_mismatch",
            "semantic_state_facts": facts,
        }
    return {
        "component_gap": gap,
        "component_ref": component_ref,
        "semantic_state_facts": facts,
    }


def _search_judgment_gap_blocker(
    *,
    search_judgment_projection: Mapping[str, Any] | None,
    component_gap: Mapping[str, Any],
) -> str | None:
    projection = dict(search_judgment_projection or {})
    if not projection:
        return "search_judgment_projection_absent"
    if projection.get("owner") not in {
        "RunAuthoritySearchJudgment",
        "RunKernel.RunAuthoritySearchJudgment",
    }:
        return "search_judgment_owner_not_canonical"
    if projection.get("trace_only"):
        return "search_judgment_trace_only"
    gaps = [
        dict(item)
        for item in (
            projection.get("semantic_gaps")
            or projection.get("gaps")
            or ()
        )
        if isinstance(item, Mapping)
    ]
    if len(gaps) != 1:
        return "search_judgment_component_gap_count_not_one"
    gap = gaps[0]
    for key in (
        "accepted_contract_version",
        "accepted_contract_digest",
        "answer_component_id",
        "component_digest",
        "semantic_gap_code",
    ):
        if _clean_token(gap.get(key), limit=256) != _clean_token(
            component_gap.get(key), limit=256
        ):
            return f"search_judgment_gap_{key}_mismatch"
    return None


def _authorized_existing_query(
    *,
    query_plan: Mapping[str, Any],
    component_gap: Mapping[str, Any],
) -> dict[str, Any]:
    consumption = dict(query_plan.get("search_work_consumption") or {})
    metadata_map = consumption.get("query_metadata") or {}
    if not isinstance(metadata_map, Mapping):
        return {"stop_reason": "query_plan_metadata_absent"}
    matches: list[tuple[str, dict[str, Any]]] = []
    for raw_query, raw_metadata in metadata_map.items():
        if not isinstance(raw_metadata, Mapping):
            continue
        metadata = dict(raw_metadata)
        authority = metadata.get("version_bound_component_gap_authority") or {}
        if not isinstance(authority, Mapping):
            continue
        if not metadata.get("version_bound_component_gap_authorized"):
            continue
        if _authority_matches_gap(authority, component_gap):
            matches.append((str(raw_query), metadata))
    if len(matches) == 0:
        return {"stop_reason": "authorized_component_gap_query_absent"}
    if len(matches) > 1:
        return {"stop_reason": "multiple_authorized_component_gap_queries"}
    query, metadata = matches[0]
    if metadata.get("query_text_generated") or metadata.get(
        "new_executable_query_text_generated"
    ):
        return {"stop_reason": "authorized_query_was_generated"}
    if not _query_was_existing_candidate(query, query_plan):
        return {"stop_reason": "authorized_query_not_existing_candidate"}
    return {"authorized_query": query, "query_metadata": metadata}


def _authority_matches_gap(
    authority: Mapping[str, Any],
    component_gap: Mapping[str, Any],
) -> bool:
    for key in (
        "accepted_contract_version",
        "accepted_contract_digest",
        "answer_component_id",
        "component_digest",
        "semantic_gap_code",
    ):
        if _clean_token(authority.get(key), limit=256) != _clean_token(
            component_gap.get(key), limit=256
        ):
            return False
    return not (
        authority.get("query_text_generated")
        or authority.get("new_executable_query_text_generated")
    )


def _query_was_existing_candidate(query: str, query_plan: Mapping[str, Any]) -> bool:
    normalized = _clean_query(query).casefold()
    if not normalized:
        return False
    for value in query_plan.get("admitted_query_order") or ():
        if _clean_query(value).casefold() == normalized:
            return True
    authorized_by_iteration = query_plan.get("authorized_queries_by_iteration") or {}
    if isinstance(authorized_by_iteration, Mapping):
        for values in authorized_by_iteration.values():
            for value in values or ():
                if _clean_query(value).casefold() == normalized:
                    return True
    for item in query_plan.get("items") or ():
        if not isinstance(item, Mapping):
            continue
        if _clean_query(item.get("authorized_query")).casefold() != normalized:
            continue
        stage = _clean_token(item.get("stage") or item.get("phase"))
        if stage != "search_judgment_component_gap_authority":
            return True
    return False


def _call_offline_adapter(
    *,
    adapter: Callable[..., Any],
    authorized_query: str,
    component_gap: Mapping[str, Any],
    policy: ComponentGapRecoveryPolicy,
    context: Mapping[str, Any],
    seen_urls: set[str] | None,
) -> list[dict[str, Any]]:
    raw = adapter(
        [authorized_query],
        str(context.get("intent") or "general"),
        str(context.get("complexity") or "medium"),
        str(context.get("search_depth") or "basic"),
        _positive_int(context.get("results_per_query")) or 1,
        provider_role="component_gap_recovery_offline",
        seen_urls=seen_urls,
        component_gap_recovery=True,
        component_gap=dict(component_gap),
        recovery_policy=policy.to_dict(),
    )
    return [
        dict(item)
        for item in (raw or ())
        if isinstance(item, Mapping)
    ]


def _annotated_recovery_passages(
    *,
    passages: Sequence[Mapping[str, Any]],
    accepted_contract: Mapping[str, Any],
    component_gap: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    query_metadata: Mapping[str, Any],
    authorized_query: str,
    idempotency_key: str,
) -> tuple[dict[str, Any], ...]:
    source_obligation_ids = _source_obligation_ids(
        component_ref=component_ref,
        query_metadata=query_metadata,
    )
    provider_job_id = _provider_job_id(
        component_ref=component_ref,
        query_metadata=query_metadata,
        idempotency_key=idempotency_key,
    )
    execution_id = f"component-gap-recovery:{idempotency_key[:24]}"
    provider_job_kind = _provider_job_kind(component_ref)
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(passages, start=1):
        item = dict(raw)
        item.setdefault(
            "candidate_id",
            f"component_gap_recovery_candidate:{idempotency_key[:20]}:{index}",
        )
        item["query_ref"] = authorized_query
        item["authorized_query"] = authorized_query
        item["component_gap_recovery"] = True
        item["component_gap_recovery_idempotency_key"] = idempotency_key
        item["component_gap_recovery_schema_version"] = (
            COMPONENT_GAP_RECOVERY_SCHEMA_VERSION
        )
        item["accepted_contract_version"] = accepted_contract.get(
            "accepted_contract_version"
        )
        item["accepted_contract_digest"] = accepted_contract.get(
            "accepted_contract_digest"
        )
        item["answer_component_id"] = component_gap.get("answer_component_id")
        item["component_digest"] = component_gap.get("component_digest")
        item["provider_job_id"] = provider_job_id
        item["provider_job_execution_id"] = execution_id
        item["provider_job_kind"] = provider_job_kind
        item["source_obligation_ids"] = list(source_obligation_ids)
        item.setdefault("dispatch_ref", execution_id)
        item.setdefault("final_evidence_eligible", "unknown")
        item.setdefault("readable_status", "readable")
        item.setdefault("fetchable_status", "available")
        out.append(item)
    return tuple(out)


def _admit_recovery_evidence(
    *,
    run_kernel: Any,
    run_id: str,
    query_plan: Mapping[str, Any],
    search_work_projection: Mapping[str, Any] | None,
    authorized_query: str,
    component_gap: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    query_metadata: Mapping[str, Any],
    annotated_passages: Sequence[Mapping[str, Any]],
    idempotency_key: str,
) -> dict[str, Any]:
    provider_job_id = _provider_job_id(
        component_ref=component_ref,
        query_metadata=query_metadata,
        idempotency_key=idempotency_key,
    )
    execution_id = f"component-gap-recovery:{idempotency_key[:24]}"
    source_obligation_ids = _source_obligation_ids(
        component_ref=component_ref,
        query_metadata=query_metadata,
    )
    handoff = {
        "provider_job_execution_records": [
            {
                "execution_id": execution_id,
                "provider_job_id": provider_job_id,
                "provider_job_kind": _provider_job_kind(component_ref),
                "component_id": _clean_token(
                    component_gap.get("answer_component_id")
                    or component_ref.get("component_id")
                ),
                "source_obligation_ids": list(source_obligation_ids),
                "authorized_queries": [authorized_query],
                "dispatch_refs": [execution_id],
                "query_plan_item_ids": list(
                    query_metadata.get("query_plan_item_ids") or ()
                ),
            }
        ],
        "component_gap_recovery": True,
        "offline_only": True,
        "idempotency_key": idempotency_key,
    }
    bridge_result = build_provider_job_evidence_ledger_observation(
        observation_id=(
            f"{run_id}:evidence-ledger:component-gap-recovery:"
            f"{idempotency_key[:24]}"
        ),
        provider_job_execution_handoff=handoff,
        query_plan_trace=query_plan,
        current_authorized_queries=[authorized_query],
        retrieval_records=list(annotated_passages),
        search_work_projection=search_work_projection,
    )
    if not bridge_result.observation_payload:
        return {
            "stop_reason": (
                bridge_result.projection.get("fallback_reason")
                or "provider_job_bridge_no_observation"
            )
        }
    action = run_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": "component_gap_recovery_provider_job_bridge",
            "candidate_count": bridge_result.projection.get("candidate_count"),
            "requirement_count": bridge_result.projection.get("requirement_count"),
            "component_gap_recovery_idempotency_key": idempotency_key,
            "component_gap_recovery_owner": COMPONENT_GAP_RECOVERY_OWNER,
        }
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload=dict(bridge_result.observation_payload),
    )
    run_kernel.reduce(result.observation)
    projection = run_kernel.state.evidence_ledger.to_projection().to_dict()
    record = {
        "bridge_projection": dict(bridge_result.projection),
        "evidence_ledger_projection": projection,
        "observation_payload": dict(bridge_result.observation_payload),
    }
    return record


def _admit_semantic_component_coverage(
    *,
    run_kernel: Any,
    accepted_contract: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    annotated_passages: Sequence[Mapping[str, Any]],
    authorized_query: str,
    idempotency_key: str,
    original_query: str,
) -> dict[str, Any]:
    candidates = _candidate_records_by_id(evidence_ledger_projection)
    for passage in annotated_passages:
        candidate_id = _clean_token(passage.get("candidate_id"), limit=200)
        candidate = candidates.get(candidate_id)
        if not candidate:
            continue
        bindable = BindableFinalPassage(
            passage=dict(passage),
            evidence_ref_id=candidate_id,
            candidate_record=dict(candidate),
        )
        try:
            observation, content_refs = build_semantic_observation_and_content_refs(
                accepted_contract=accepted_contract,
                bindable=bindable,
                component_ref=component_ref,
            )
        except Exception:
            continue
        if not content_refs:
            continue
        coverage = build_component_coverage_proposal(
            accepted_contract=accepted_contract,
            observation=observation,
            content_ref=content_refs[0],
            evidence_ledger_projection=evidence_ledger_projection,
            run_id=str(getattr(run_kernel.state, "run_id", "")),
            request_id=str(getattr(run_kernel.state, "request_id", "")),
            query=original_query or authorized_query,
        )
        if coverage is None:
            continue

        try:
            commit_projection = run_kernel.commit_recovered_semantic_delta(
                semantic_observation=observation.to_dict(),
                sanitized_content_references=[
                    ref.to_dict() for ref in content_refs
                ],
                component_coverage_record=coverage.to_dict(),
                answer_component_id=component_ref["component_id"],
                component_revision=component_ref["component_revision"],
                component_digest=component_ref["component_digest"],
                accepted_contract_digest=accepted_contract["accepted_contract_digest"],
                accepted_contract_version=accepted_contract[
                    "accepted_contract_version"
                ],
                request_id=str(getattr(run_kernel.state, "request_id", "")),
                inputs={
                    "component_gap_recovery_idempotency_key": idempotency_key,
                    "authorized_recovery_query": authorized_query,
                    "component_gap_recovery_owner": COMPONENT_GAP_RECOVERY_OWNER,
                },
            )
        except Exception:
            continue
        return {
            "coverage_record_id": coverage.record_id,
            "commit_projection": dict(commit_projection),
        }
    return {"stop_reason": "recovered_evidence_not_semantically_covering_gap"}


def _component_still_missing(
    semantic_state_facts: Mapping[str, Any],
    component_ref: Mapping[str, Any],
) -> bool:
    component_id = _clean_token(component_ref.get("component_id"))
    for summary in semantic_state_facts.get("component_summaries") or ():
        if not isinstance(summary, Mapping):
            continue
        if _clean_token(summary.get("component_id")) != component_id:
            continue
        return not bool(summary.get("coverage_present")) or bool(
            summary.get("coverage_suspect")
        )
    return True


def _record_and_result(
    *,
    run_kernel: Any,
    policy: ComponentGapRecoveryPolicy,
    status: ComponentGapRecoveryStatus,
    stop_reason: str,
    attempted_cycles: int,
    component_gap: Mapping[str, Any] | None = None,
    authorized_query: str | None = None,
    idempotency_key: str | None = None,
    evidence_ledger_projection: Mapping[str, Any] | None = None,
    semantic_state_facts: Mapping[str, Any] | None = None,
    recovered_passages: Sequence[Mapping[str, Any]] = (),
    adapter_invoked: bool = False,
) -> ComponentGapRecoveryResult:
    budget_record = {
        "schema_version": COMPONENT_GAP_RECOVERY_SCHEMA_VERSION,
        "owner": COMPONENT_GAP_RECOVERY_OWNER,
        "mode_neutral_primitive": True,
        **policy.to_dict(),
        "attempted_cycles": int(attempted_cycles),
        "adapter_invoked": bool(adapter_invoked),
        "authorized_query": authorized_query,
        "idempotency_key": idempotency_key,
        "stop_reason": stop_reason,
        "recovered_component_ids": [
            _clean_token((component_gap or {}).get("answer_component_id"))
        ]
        if status is ComponentGapRecoveryStatus.RECOVERED
        else [],
    }
    record = {
        "schema_version": COMPONENT_GAP_RECOVERY_SCHEMA_VERSION,
        "owner": COMPONENT_GAP_RECOVERY_OWNER,
        "mode_neutral_primitive": True,
        "canonical_budget_owner": "RunKernel.RunState.component_gap_recovery_history",
        "status": status.value,
        "stop_reason": stop_reason,
        "policy": policy.to_dict(),
        "budget_record": budget_record,
        "component_gap": dict(component_gap or {}),
        "authorized_query": authorized_query,
        "idempotency_key": idempotency_key,
        "adapter_invoked": bool(adapter_invoked),
        "evidence_ledger_digest": (evidence_ledger_projection or {}).get(
            "ledger_digest"
        ),
        "semantic_state_facts_digest": (semantic_state_facts or {}).get(
            "semantic_state_facts_digest"
        ),
        "recovered_passage_count": len(recovered_passages),
    }
    _append_canonical_recovery_record(run_kernel, record)
    return ComponentGapRecoveryResult(
        status=status,
        stop_reason=stop_reason,
        budget_record=budget_record,
        recovered_passages=tuple(dict(item) for item in recovered_passages),
        evidence_ledger_projection=evidence_ledger_projection,
        semantic_state_facts=semantic_state_facts,
    )


def _append_canonical_recovery_record(
    run_kernel: Any,
    record: Mapping[str, Any],
) -> None:
    history = _history(run_kernel)
    history.append(dict(record))
    run_kernel.state.component_gap_recovery_history = history
    _write_projection_from_canonical_history(run_kernel)


def _write_projection_from_canonical_history(run_kernel: Any) -> None:
    history = _history(run_kernel)
    latest = dict(history[-1]) if history else {}
    run_kernel.state.projections[COMPONENT_GAP_RECOVERY_TRACE_KEY] = {
        "schema_version": COMPONENT_GAP_RECOVERY_SCHEMA_VERSION,
        "owner": COMPONENT_GAP_RECOVERY_OWNER,
        "runtime_consumer": "core.pipeline_orchestrator.run_pipeline",
        "mode_neutral_primitive": True,
        "canonical_budget_owner": "RunKernel.RunState.component_gap_recovery_history",
        "projection_derived_from_canonical_state": True,
        "latest": latest,
        "history": history,
        "history_count": len(history),
    }


def _history(run_kernel: Any) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in getattr(
            run_kernel.state,
            "component_gap_recovery_history",
            (),
        )
        if isinstance(item, Mapping)
    ]


def _attempted_cycle_count(history: Sequence[Mapping[str, Any]]) -> int:
    return sum(1 for item in history if item.get("adapter_invoked"))


def _has_pre_recovery_final_answer_packet(run_kernel: Any) -> bool:
    packet = getattr(run_kernel.state, "final_answer_packet", None)
    if isinstance(packet, Mapping) and packet:
        return True
    return bool(getattr(run_kernel.state, "final_answer_packet_projection", None))


def _component_ref(
    accepted_contract: Mapping[str, Any],
    component_id: str,
) -> dict[str, Any]:
    for ref in accepted_contract.get("accepted_answer_component_refs") or ():
        if not isinstance(ref, Mapping):
            continue
        if _clean_token(ref.get("component_id")) == component_id:
            return dict(ref)
    return {}


def _candidate_records_by_id(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for candidate in evidence_ledger_projection.get("candidate_records") or ():
        if not isinstance(candidate, Mapping):
            continue
        candidate_id = _clean_token(candidate.get("candidate_id"), limit=200)
        if candidate_id:
            out[candidate_id] = dict(candidate)
    return out


def _source_obligation_ids(
    *,
    component_ref: Mapping[str, Any],
    query_metadata: Mapping[str, Any],
) -> tuple[str, ...]:
    values = (
        component_ref.get("source_obligation_candidate_ids")
        or component_ref.get("source_obligation_candidate_refs")
        or query_metadata.get("source_obligation_candidate_ids")
        or ()
    )
    cleaned = tuple(
        dict.fromkeys(item for item in (_clean_token(value) for value in values) if item)
    )
    primary = tuple(
        item
        for item in cleaned
        if "source_bound_numeric" not in item.casefold()
    )
    return primary or cleaned


def _provider_job_id(
    *,
    component_ref: Mapping[str, Any],
    query_metadata: Mapping[str, Any],
    idempotency_key: str,
) -> str:
    _ = query_metadata
    component_id = _clean_token(component_ref.get("component_id")) or "component"
    return f"component_gap_recovery_provider_job:{component_id}:{idempotency_key[:12]}"


def _provider_job_kind(component_ref: Mapping[str, Any]) -> str:
    obligation_ids = {
        _clean_token(item).casefold()
        for item in (
            component_ref.get("source_obligation_candidate_ids")
            or component_ref.get("source_obligation_candidate_refs")
            or ()
        )
        if _clean_token(item)
    }
    if any("legal_current_primary" in item for item in obligation_ids):
        return "conflict_currentness_check"
    if any("source_bound_numeric" in item for item in obligation_ids):
        return "fetch_read_extract"
    if any("official_current" in item for item in obligation_ids):
        return "official_candidate_acquisition"
    source_classes = {
        _clean_token(item)
        for item in (
            component_ref.get("source_obligation_classes")
            or component_ref.get("source_classes")
            or component_ref.get("required_source_classes")
            or ()
        )
    }
    source_class = _clean_token(component_ref.get("source_class"))
    if source_class:
        source_classes.add(source_class)
    if {
        "legal_or_regulatory_text",
        "current_primary_or_official",
    } & source_classes:
        return "conflict_currentness_check"
    if "primary_source_documents" in source_classes:
        return "canonical_extraction"
    if "sourced_numeric_values" in source_classes:
        return "fetch_read_extract"
    return "official_candidate_acquisition"


def _idempotency_key(
    *,
    accepted_contract: Mapping[str, Any],
    component_gap: Mapping[str, Any],
    authorized_query: str,
) -> str:
    payload = {
        "accepted_contract_version": accepted_contract.get(
            "accepted_contract_version"
        ),
        "accepted_contract_digest": accepted_contract.get("accepted_contract_digest"),
        "answer_component_id": component_gap.get("answer_component_id"),
        "component_digest": component_gap.get("component_digest"),
        "semantic_gap_code": component_gap.get("semantic_gap_code"),
        "authorized_query": _clean_query(authorized_query),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _extract_query_plan(query_plan_trace: Mapping[str, Any] | None) -> dict[str, Any]:
    trace = dict(query_plan_trace or {})
    nested = trace.get("query_plan")
    if isinstance(nested, Mapping):
        return dict(nested)
    return trace


def _clean_token(value: Any, limit: int = 120) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:limit]


def _clean_query(value: Any, limit: int = 1000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except Exception:
        return 0
    return parsed if parsed > 0 else 0


__all__ = [
    "COMPONENT_GAP_RECOVERY_OWNER",
    "COMPONENT_GAP_RECOVERY_SCHEMA_VERSION",
    "COMPONENT_GAP_RECOVERY_TRACE_KEY",
    "ComponentGapRecoveryHandoff",
    "ComponentGapRecoveryPolicy",
    "ComponentGapRecoveryResult",
    "ComponentGapRecoveryStatus",
    "build_component_gap_recovery_handoff",
    "execute_authorized_component_gap_recovery",
]
