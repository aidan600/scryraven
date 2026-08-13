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
    RUN_KERNEL = "run_kernel"


class InitialQueryStrategyFailureCode(str, Enum):
    """Closed codes for corridor translations that are not owner-exception fields.

    ``SearchPlannerRuntimeError`` and ``QueryStrategyConvergenceError`` author
    their own typed codes; those values are projected directly and are not
    duplicated here.
    """

    SEARCH_PLANNER_PRODUCTION_TRANSITION = "search_planner_production_transition"
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRANSITION = (
        "initial_answer_contract_acceptance_transition"
    )
    CONTRACT_AMENDMENT_ADMISSION_TRANSITION = "contract_amendment_admission_transition"
    CONTRACT_AMENDMENT_APPLICATION_TRANSITION = (
        "contract_amendment_application_transition"
    )
    QUERY_PLAN_ADMISSION_TRANSITION = "query_plan_admission_transition"


_RUN_KERNEL_CODE_BY_OPERATION: Final[dict[str, InitialQueryStrategyFailureCode]] = {
    "search_planner_production": (
        InitialQueryStrategyFailureCode.SEARCH_PLANNER_PRODUCTION_TRANSITION
    ),
    "initial_answer_contract_acceptance": (
        InitialQueryStrategyFailureCode.INITIAL_ANSWER_CONTRACT_ACCEPTANCE_TRANSITION
    ),
    "contract_amendment_admission": (
        InitialQueryStrategyFailureCode.CONTRACT_AMENDMENT_ADMISSION_TRANSITION
    ),
    "contract_amendment_application": (
        InitialQueryStrategyFailureCode.CONTRACT_AMENDMENT_APPLICATION_TRANSITION
    ),
    "query_plan_admission": (
        InitialQueryStrategyFailureCode.QUERY_PLAN_ADMISSION_TRANSITION
    ),
}

_RUN_KERNEL_TRANSITION_CODES: Final[frozenset[str]] = frozenset(
    code.value for code in _RUN_KERNEL_CODE_BY_OPERATION.values()
)

def _licensed_failure_codes_for_origin(
    origin: InitialQueryStrategyFailureOrigin,
) -> frozenset[str]:
    """Return the finite codes licensed for one closed corridor origin.

    Owner enums remain defined in their owner modules. This helper only
    licenses their values for terminal projection.
    """

    if origin is InitialQueryStrategyFailureOrigin.PLANNER_RUNTIME:
        from core.search_planner_runtime import SearchPlannerRuntimeSafeFailureCode

        return frozenset(member.value for member in SearchPlannerRuntimeSafeFailureCode)
    if origin is InitialQueryStrategyFailureOrigin.QUERY_STRATEGY_CONVERGENCE:
        from core.query_production_runtime import QueryStrategyConvergenceFailureCode

        return frozenset(
            member.value for member in QueryStrategyConvergenceFailureCode
        )
    if origin is InitialQueryStrategyFailureOrigin.RUN_KERNEL:
        return _RUN_KERNEL_TRANSITION_CODES
    raise ValueError("failure_origin is not a closed corridor origin")


@dataclass(frozen=True, slots=True)
class InitialQueryStrategyFailure:
    """An allowlisted, message-free terminal attribution."""

    failure_origin: InitialQueryStrategyFailureOrigin
    failure_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.failure_origin, InitialQueryStrategyFailureOrigin):
            raise TypeError("failure_origin must be a closed corridor origin")
        if not isinstance(self.failure_code, str) or not self.failure_code.strip():
            raise ValueError("failure_code must be a non-empty closed token")
        if self.failure_code != self.failure_code.strip():
            raise ValueError("failure_code must not carry surrounding whitespace")
        licensed = _licensed_failure_codes_for_origin(self.failure_origin)
        if self.failure_code not in licensed:
            raise ValueError(
                "failure_code is not licensed for the closed failure_origin"
            )

    def to_terminal_projection(self) -> dict[str, str]:
        return {
            "schema_version": INITIAL_QUERY_STRATEGY_FAILURE_SCHEMA_VERSION,
            "boundary": INITIAL_QUERY_STRATEGY_FAILURE_BOUNDARY,
            "failure_origin": self.failure_origin.value,
            "failure_code": self.failure_code,
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


def run_kernel_initial_planning_failure(
    *, operation: str
) -> InitialQueryStrategyFailure:
    code = _RUN_KERNEL_CODE_BY_OPERATION.get(operation)
    if code is None:
        raise ValueError("initial planning RunKernel operation is not allowlisted")
    return InitialQueryStrategyFailure(
        failure_origin=InitialQueryStrategyFailureOrigin.RUN_KERNEL,
        failure_code=code.value,
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
    and is intentionally excluded here. Runtime and convergence causes consume
    the exception's owner-authored identity; this classifier does not invent a
    second generic code for those families. Subclasses that lack a licensed
    owner-authored runtime safe code remain generic ``bounded_run_failed``.
    """

    if exc is None:
        return None

    from core.query_production_runtime import (
        QueryStrategyConvergenceError,
        QueryStrategyConvergenceFailureCode,
    )
    from core.search_planner_model_adapter import SearchPlannerModelAdapterError
    from core.search_planner_runtime import (
        SearchPlannerRuntimeError,
        SearchPlannerRuntimeSafeFailureCode,
    )

    if isinstance(exc, SearchPlannerModelAdapterError):
        return None
    if isinstance(exc, InitialQueryStrategyFailureError):
        return exc.failure
    if isinstance(exc, QueryStrategyConvergenceError):
        code = exc.failure_code
        if not isinstance(code, QueryStrategyConvergenceFailureCode):
            return None
        try:
            return InitialQueryStrategyFailure(
                failure_origin=InitialQueryStrategyFailureOrigin(
                    QueryStrategyConvergenceError.SAFE_FAILURE_ORIGIN
                ),
                failure_code=code.value,
            )
        except (TypeError, ValueError):
            return None
    if isinstance(exc, SearchPlannerRuntimeError):
        try:
            code = exc.failure_code
        except AttributeError:
            return None
        if not isinstance(code, SearchPlannerRuntimeSafeFailureCode):
            return None
        try:
            return InitialQueryStrategyFailure(
                failure_origin=InitialQueryStrategyFailureOrigin(
                    SearchPlannerRuntimeError.SAFE_FAILURE_ORIGIN
                ),
                failure_code=code.value,
            )
        except (TypeError, ValueError):
            return None
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
    "run_kernel_initial_planning_failure",
]
