"""Named RunKernel lifecycle helpers for EvidenceLedger reductions.

The helpers keep repeated authorize/execute/reduce callsite shapes out of the
orchestrator while preserving EvidenceLedger semantics. They do not construct
policy decisions or call providers, models, search, prompts, ranking, or
retrieval.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.evidence_ledger import (
    build_evidence_ledger_observation_from_run_contract,
    build_evidence_ledger_observation_from_runtime,
)
from core.evidence_ledger_runtime import execute_evidence_ledger_reduction_action
from core.run_kernel import RunKernel


def _ledger_projection(run_kernel: RunKernel) -> dict[str, Any]:
    return run_kernel.state.evidence_ledger.to_projection().to_dict()


def reduce_run_contract_requirements_into_evidence_ledger(
    *,
    run_kernel: RunKernel,
    run_id: str,
    run_contract_projection: Mapping[str, Any],
    observation_id_suffix: str,
    authorization_observation_source: str,
) -> dict[str, Any]:
    """Reduce RunAuthorityContract requirements into EvidenceLedger."""

    action = run_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": authorization_observation_source,
            "contract_id": run_contract_projection.get("contract_id"),
            "source_requirement_count": len(
                run_contract_projection.get("source_requirements", [])
            ),
        }
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload=build_evidence_ledger_observation_from_run_contract(
            observation_id=f"{run_id}:evidence-ledger:{observation_id_suffix}",
            contract_projection=run_contract_projection,
        ).to_dict(),
    )
    run_kernel.reduce(result.observation)
    return _ledger_projection(run_kernel)


def reduce_pre_recovery_source_obligations_into_evidence_ledger(
    *,
    run_kernel: RunKernel,
    run_id: str,
    source_class_recovery_telemetry: Mapping[str, Any],
    final_top_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reduce pre-recovery runtime source obligation facts into EvidenceLedger."""

    action = run_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": "pre_recovery_source_obligation",
            "candidate_count": len(final_top_evidence),
        }
    )
    observation = build_evidence_ledger_observation_from_runtime(
        observation_id=f"{run_id}:evidence-ledger:pre-recovery",
        observation_source="pre_recovery_source_obligation",
        source_class_recovery_telemetry=source_class_recovery_telemetry,
        final_top_evidence=final_top_evidence,
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload=observation.to_dict(),
    )
    run_kernel.reduce(result.observation)
    return _ledger_projection(run_kernel)


def reduce_final_evidence_bundle_into_evidence_ledger(
    *,
    run_kernel: RunKernel,
    run_id: str,
    final_top_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reduce the selected final evidence bundle into EvidenceLedger."""

    action = run_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": "final_evidence_bundle",
            "final_evidence_count": len(final_top_evidence),
        }
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload=build_evidence_ledger_observation_from_runtime(
            observation_id=f"{run_id}:evidence-ledger:final-evidence",
            observation_source="final_evidence_bundle",
            final_top_evidence=final_top_evidence,
            final_evidence_selected=True,
        ).to_dict(),
    )
    run_kernel.reduce(result.observation)
    return _ledger_projection(run_kernel)


def reduce_post_final_source_obligations_into_evidence_ledger(
    *,
    run_kernel: RunKernel,
    run_id: str,
    source_class_recovery_telemetry: Mapping[str, Any],
    final_top_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reduce post-final runtime source obligation facts into EvidenceLedger."""

    action = run_kernel.authorize_evidence_ledger_reduction(
        inputs={
            "observation_source": "post_final_source_obligation",
            "candidate_count": len(final_top_evidence),
        }
    )
    observation = build_evidence_ledger_observation_from_runtime(
        observation_id=f"{run_id}:evidence-ledger:post-final",
        observation_source="post_final_source_obligation",
        source_class_recovery_telemetry=source_class_recovery_telemetry,
        final_top_evidence=final_top_evidence,
        final_evidence_selected=True,
    )
    result = execute_evidence_ledger_reduction_action(
        action,
        payload=observation.to_dict(),
    )
    run_kernel.reduce(result.observation)
    return _ledger_projection(run_kernel)


__all__ = [
    "reduce_final_evidence_bundle_into_evidence_ledger",
    "reduce_post_final_source_obligations_into_evidence_ledger",
    "reduce_pre_recovery_source_obligations_into_evidence_ledger",
    "reduce_run_contract_requirements_into_evidence_ledger",
]
