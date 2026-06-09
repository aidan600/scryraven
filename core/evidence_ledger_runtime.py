"""RunKernel evidence-ledger reduction adapter.

This module validates the RunKernel action and wraps sanitized ledger
observations. The actual custody semantics live in ``core.evidence_ledger`` and
are reduced by ``RunKernel`` into canonical ``RunState``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.run_kernel import (
    EVIDENCE_LEDGER_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)


@dataclass(frozen=True, slots=True)
class EvidenceLedgerReductionResult:
    """Validated observation ready for RunKernel reduction."""

    observation: Observation


def execute_evidence_ledger_reduction_action(
    action: AuthorizedAction,
    *,
    payload: Mapping[str, Any],
) -> EvidenceLedgerReductionResult:
    """Return a RunKernel observation for canonical evidence-ledger reduction."""

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.EVIDENCE_LEDGER_REDUCE,
        stage=EVIDENCE_LEDGER_STAGE,
        expected_observation_type=ObservationType.EVIDENCE_CUSTODY_OBSERVED,
    )
    return EvidenceLedgerReductionResult(
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.EVIDENCE_CUSTODY_OBSERVED,
            status=RunStageStatus.COMPLETED,
            payload=payload,
        )
    )


__all__ = [
    "EvidenceLedgerReductionResult",
    "execute_evidence_ledger_reduction_action",
]
