"""Closed safe terminal attribution for the ordinary initial-planning corridor.

This module owns one finite terminal projection only. It is not a repository-wide
exception framework and never derives a cause from an exception message, stage
name, or arbitrary metadata.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, TypeVar

INITIAL_QUERY_STRATEGY_FAILURE_SCHEMA_VERSION: Final = "initial_query_strategy_failure_v1"
INITIAL_QUERY_STRATEGY_FAILURE_BOUNDARY: Final = "initial_query_strategy"
INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY: Final = "initial_query_strategy_failure"

_T = TypeVar("_T")


class InitialQueryStrategyFailureOrigin(str, Enum):
    """Closed failure origins for the ordinary initial-planning corridor."""

    PLANNER_RUNTIME = "planner_runtime"
    QUERY_STRATEGY_CONVERGENCE = "query_strategy_convergence"
    SCOUT_DISAMBIGUATION_RUNTIME = "scout_disambiguation_runtime"
    SEARCH_PLANNER_REVISION_RUNTIME = "search_planner_revision_runtime"
    RUN_KERNEL = "run_kernel"


class InitialQueryStrategyFailureCode(str, Enum):
    """Closed failure codes for the ordinary initial-planning corridor."""

    SEARCH_PLANNER_RUNTIME_ERROR = "search_planner_runtime_error"
    QUERY_STRATEGY_CONVERGENCE_ERROR = "query_strategy_convergence_error"
    SCOUT_DISAMBIGUATION_RUNTIME_ERROR = "scout_disambiguation_runtime_error"
    SEARCH_PLANNER_REVISION_RUNTIME_ERROR = "search_planner_revision_runtime_error"
    SEARCH_PLANNER_PRODUCTION_TRANSITION = "search_planner_production_transition"
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRANSITION = (
        "initial_answer_contract_acceptance_transition"
    )
    SCOUT_DISAMBIGUATION_TRANSITION = "scout_disambiguation_transition"
    SEARCH_PLANNER_REVISION_TRANSITION = "search_planner_revision_transition"
    CONTRACT_AMENDMENT_ADMISSION_TRANSITION = "contract_amendment_admission_transition"
    CONTRACT_AMENDMENT_APPLICATION_TRANSITION = (
        "contract_amendment_application_transition"
    )
    SEARCH_WORK_PLAN_CONSTRUCTION_TRANSITION = (
        "search_work_plan_construction_transition"
    )
    QUERY_PRODUCTION_TRANSITION = "query_production_transition"
    QUERY_PLAN_ADMISSION_TRANSITION = "query_plan_admission_transition"


_RUN_KERNEL_CODE_BY_OPERATION: Final[dict[str, InitialQueryStrategyFailureCode]] = {
    "search_planner_production": (
        InitialQueryStrategyFailureCode.SEARCH_PLANNER_PRODUCTION_TRANSITION
    ),
    "initial_answer_contract_acceptance": (
        InitialQueryStrategyFailureCode.INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRANSITION
    ),
    "scout_disambiguation": (
        InitialQueryStrategyFailureCode.SCOUT_DISAMBIGUATION_TRANSITION
    ),
    "search_planner_revision": (
        InitialQueryStrategyFailureCode.SEARCH_PLANNER_REVISION_TRANSITION
    ),
    "contract_amendment_admission": (
        InitialQueryStrategyFailureCode.CONTRACT_AMENDMENT_ADMISSION_TRANSITION
    ),
    "contract_amendment_application": (
        InitialQueryStrategyFailureCode.CONTRACT_AMENDMENT_APPLICATION_TRANSITION
    ),
    "search_work_plan_construction": (
        InitialQueryStrategyFailureCode.SEARCH_WORK_PLAN_CONSTRUCTION_TRANSITION
    ),
    "query_production": InitialQueryStrategyFailureCode.QUERY_PRODUCTION_TRANSITION,
    "query_plan_admission": (
        InitialQueryStrategyFailureCode.QUERY_PLAN_ADMISSION_TRANSITION
    ),
}


@dataclass(frozen=True, slots=True)
class InitialQueryStrategyFailure:
    """An allowlisted, message-free terminal attribution."""

    failure_origin: InitialQueryStrategyFailureOrigin
    failure_code: InitialQueryStrategyFailureCode

    def to_terminal_projection(self) -> dict[str, str]:
        return {
            "schema_version": INITIAL_QUERY_STRATEGY_FAILURE_SCHEMA_VERSION,
            "boundary": INITIAL_QUERY_STRATEGY_FAILURE_BOUNDARY,
            "failure_origin": self.failure_origin.value,
            "failure_code": self.failure_code.value,
        }


class InitialQueryStrategyFailureError(RuntimeError):
    """Corridor-local carrier for translated, closed initial-planning causes.

    The public message is fixed and intentionally generic. Bounded terminals
    project only ``failure.to_terminal_projection()``.
    """

    __slots__ = ("_failure",)

    def __init__(self, failure: InitialQueryStrategyFailure) -> None:
        if not isinstance(failure, InitialQueryStrategyFailure):
            raise TypeError("failure must be an InitialQueryStrategyFailure")
        super().__init__("initial query strategy planning failed")
        self._failure = failure

    @property
    def failure(self) -> InitialQueryStrategyFailure:
        return self._failure

    def to_terminal_projection(self) -> dict[str, str]:
        return self._failure.to_terminal_projection()


def search_planner_runtime_failure() -> InitialQueryStrategyFailure:
    return InitialQueryStrategyFailure(
        failure_origin=InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME,
        failure_code=InitialQueryStrategyFailureCode.SEARCH_PLANNER_RUNTIME_ERROR,
    )


def query_strategy_convergence_failure() -> InitialQueryStrategyFailure:
    return InitialQueryStrategyFailure(
        failure_origin=InitialQueryStrategyFailureOrigin.QUERY_STRATEGY_CONVERGENCE,
        failure_code=InitialQueryStrategyFailureCode.QUERY_STRATEGY_CONVERGENCE_ERROR,
    )


def scout_disambiguation_runtime_failure() -> InitialQueryStrategyFailure:
    return InitialQueryStrategyFailure(
        failure_origin=InitialQueryStrategyFailureOrigin.SCOUT_DISAMBIGUATION_RUNTIME,
        failure_code=InitialQueryStrategyFailureCode.SCOUT_DISAMBIGUATION_RUNTIME_ERROR,
    )


def search_planner_revision_runtime_failure() -> InitialQueryStrategyFailure:
    return InitialQueryStrategyFailure(
        failure_origin=InitialQueryStrategyFailureOrigin.SEARCH_PLANNER_REVISION_RUNTIME,
        failure_code=(
            InitialQueryStrategyFailureCode.SEARCH_PLANNER_REVISION_RUNTIME_ERROR
        ),
    )


def run_kernel_initial_planning_failure(
    *, operation: str
) -> InitialQueryStrategyFailure:
    code = _RUN_KERNEL_CODE_BY_OPERATION.get(operation)
    if code is None:
        raise ValueError("initial planning RunKernel operation is not allowlisted")
    return InitialQueryStrategyFailure(
        failure_origin=InitialQueryStrategyFailureOrigin.RUN_KERNEL,
        failure_code=code,
    )


def invoke_run_kernel_initial_planning(
    operation: str, call: Callable[[], _T]
) -> _T:
    """Translate audited RunKernel transition failures at one exact call site."""

    from core.run_kernel import RunKernelTransitionError

    try:
        return call()
    except RunKernelTransitionError as exc:
        raise InitialQueryStrategyFailureError(
            run_kernel_initial_planning_failure(operation=operation)
        ) from exc


def classify_initial_query_strategy_failure(
    exc: BaseException | None,
) -> InitialQueryStrategyFailure | None:
    """Return the closed corridor cause, or None for unknown/untyped failures.

    ``SearchPlannerModelAdapterError`` remains on the existing rich terminal path
    and is intentionally excluded here.
    """

    if exc is None:
        return None

    from core.query_production_runtime import QueryStrategyConvergenceError
    from core.search_planner_model_adapter import SearchPlannerModelAdapterError
    from core.search_planner_runtime import SearchPlannerRuntimeError

    if isinstance(exc, SearchPlannerModelAdapterError):
        return None
    if isinstance(exc, InitialQueryStrategyFailureError):
        return exc.failure
    if isinstance(exc, QueryStrategyConvergenceError):
        return query_strategy_convergence_failure()
    if isinstance(exc, SearchPlannerRuntimeError):
        return search_planner_runtime_failure()
    return None


def project_initial_query_strategy_failure_for_terminal(
    exc: BaseException | None,
) -> dict[str, str] | None:
    failure = classify_initial_query_strategy_failure(exc)
    return None if failure is None else failure.to_terminal_projection()


def initial_query_strategy_failure_from_safe_metadata(
    safe_metadata: Mapping[str, Any] | None,
) -> InitialQueryStrategyFailure | None:
    """Extract only a typed closed carrier from existing PipelineError metadata."""

    if not isinstance(safe_metadata, Mapping):
        return None
    candidate = safe_metadata.get(INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY)
    return candidate if isinstance(candidate, InitialQueryStrategyFailure) else None


__all__ = [
    "INITIAL_QUERY_STRATEGY_FAILURE_BOUNDARY",
    "INITIAL_QUERY_STRATEGY_FAILURE_SCHEMA_VERSION",
    "INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY",
    "InitialQueryStrategyFailure",
    "InitialQueryStrategyFailureCode",
    "InitialQueryStrategyFailureError",
    "InitialQueryStrategyFailureOrigin",
    "classify_initial_query_strategy_failure",
    "initial_query_strategy_failure_from_safe_metadata",
    "invoke_run_kernel_initial_planning",
    "project_initial_query_strategy_failure_for_terminal",
    "query_strategy_convergence_failure",
    "run_kernel_initial_planning_failure",
    "scout_disambiguation_runtime_failure",
    "search_planner_revision_runtime_failure",
    "search_planner_runtime_failure",
]
