"""Sanitized observation of the canonical ordinary SearchPlanner boundary.

The observer wraps only the injected model-call dependency. Product code still
constructs the Planner input and prompt, cleans and parses the response,
validates the proposal, projects runtime state, and performs initial acceptance.
No raw prompt or response is retained.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_SYSTEM_PROMPT

PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION = "search_planner_product_boundary_observer_v1"
CANONICAL_PRODUCT_BOUNDARY_REF = (
    "core.pipeline_orchestrator.run_pipeline -> "
    "core.query_production_runtime.execute_initial_query_strategy_convergence -> "
    "core.search_planner_model_adapter.SearchPlannerModelAdapter"
)
CANONICAL_PRODUCT_BOUNDARY_VERSION = "canonical_product_search_planner_boundary_cd7a337_v1"
_PROMPT_PAYLOAD_MARKER = "Sanitized planner input JSON:\n"
_STAGE_POSTURES = frozenset({"PASS", "FAIL", "NOT_REACHED", "REVIEW_REQUIRED"})
_INCOMPLETE_POSTURES = frozenset({"COMPLETE", "INCOMPLETE", "NOT_REACHED", "REVIEW_REQUIRED"})
_FORBIDDEN_SAFE_REF_KEYS = frozenset(
    {
        "api_key",
        "authorization_header",
        "body",
        "content",
        "credential",
        "full_prompt",
        "model_response",
        "prompt",
        "prompt_text",
        "provider_request",
        "provider_response",
        "provider_payload",
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "response",
        "secret",
    }
)
_MECHANICAL_RULE_IDS = frozenset(f"M{index:02d}" for index in range(1, 18))


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True, slots=True)
class PromptDigestObservation:
    semantic_input_digest: str
    semantic_input_length: int
    system_prompt_digest: str
    system_prompt_length: int
    instruction_digest: str
    instruction_length: int
    full_prompt_digest: str
    full_prompt_length: int
    extraction_posture: str

    def __post_init__(self) -> None:
        for label in (
            "semantic_input_digest",
            "system_prompt_digest",
            "instruction_digest",
            "full_prompt_digest",
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", getattr(self, label)):
                raise ValueError(f"{label} must be one SHA-256 digest")
        for label in (
            "semantic_input_length",
            "system_prompt_length",
            "instruction_length",
            "full_prompt_length",
        ):
            if getattr(self, label) < 0:
                raise ValueError(f"{label} cannot be negative")
        if self.extraction_posture not in {"PASS", "REVIEW_REQUIRED"}:
            raise ValueError("prompt extraction posture is unsupported")


@dataclass(frozen=True, slots=True)
class AskModelArgumentShape:
    positional_shape: tuple[str, ...]
    keyword_names: tuple[str, ...]
    keyword_types: Mapping[str, str]
    require_json: bool
    provider_present: bool
    model_present: bool
    reasoning_effort_present: bool
    cost_accumulator_present: bool
    cost_phase: str | None
    credential_argument_present: bool

    def __post_init__(self) -> None:
        if self.positional_shape != ("prompt:str", "system_prompt:str"):
            raise ValueError("ask_model positional shape is unsupported")
        if self.keyword_names != tuple(sorted(set(self.keyword_names))):
            raise ValueError("ask_model keyword names must be sorted and unique")
        if set(self.keyword_types) != set(self.keyword_names):
            raise ValueError("ask_model keyword type identities are incomplete")


@dataclass(frozen=True, slots=True)
class ProductBoundaryObservation:
    schema_version: str
    owner: str
    boundary_ref: str
    boundary_version: str
    boundary_status: str
    product_boundary_reached: bool
    model_call_count: int
    prompt_identity: PromptDigestObservation | None
    ask_model_argument_shape: AskModelArgumentShape | None
    output_digest: str | None
    output_length: int
    response_received: bool
    response_cleaning_posture: str
    parser_posture: str
    validator_posture: str
    runtime_projection_posture: str
    initial_acceptance_posture: str
    search_work_plan_posture: str
    incomplete_generation_posture: str
    canonical_failure_rule_ids: tuple[str, ...]
    bounded_failure_reason: str | None
    safe_usage_refs: tuple[Mapping[str, Any], ...]
    safe_execution_refs: tuple[Mapping[str, Any], ...]
    proposal_digest: str | None = None
    raw_prompt_retained: bool = False
    raw_response_retained: bool = False
    raw_provider_payload_retained: bool = False
    observer_parsed_model_output: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION:
            raise ValueError("product-boundary observation schema is unsupported")
        if self.owner != "CanonicalProductSearchPlannerBoundary":
            raise ValueError("product-boundary observation owner is invalid")
        if self.boundary_version != CANONICAL_PRODUCT_BOUNDARY_VERSION:
            raise ValueError("product-boundary observation version is invalid")
        if self.boundary_status not in _STAGE_POSTURES:
            raise ValueError("product-boundary status is unsupported")
        for value in (
            self.parser_posture,
            self.validator_posture,
            self.runtime_projection_posture,
            self.initial_acceptance_posture,
            self.search_work_plan_posture,
        ):
            if value not in _STAGE_POSTURES:
                raise ValueError(f"unsupported stage posture: {value}")
        if self.incomplete_generation_posture not in _INCOMPLETE_POSTURES:
            raise ValueError("incomplete-generation posture is unsupported")
        if self.model_call_count < 0 or self.output_length < 0:
            raise ValueError("observation counts and lengths cannot be negative")
        if self.product_boundary_reached != (self.model_call_count > 0):
            raise ValueError("product-boundary reachability must match the observed call count")
        if self.product_boundary_reached != (
            self.prompt_identity is not None and self.ask_model_argument_shape is not None
        ):
            raise ValueError("reached boundary observations require prompt and argument identities")
        if self.output_digest is not None and not re.fullmatch(r"[0-9a-f]{64}", self.output_digest):
            raise ValueError("output digest must be one SHA-256 digest")
        if self.proposal_digest is not None and not re.fullmatch(r"[0-9a-f]{64}", self.proposal_digest):
            raise ValueError("proposal digest must be one SHA-256 digest")
        if self.validator_posture == "PASS" and self.proposal_digest is None:
            raise ValueError("validated proposal observations require a proposal digest")
        if self.response_received != (self.output_digest is not None):
            raise ValueError("response posture must match the output digest")
        if not self.response_received and self.output_length:
            raise ValueError("missing responses cannot have a positive output length")
        if (
            len(set(self.canonical_failure_rule_ids)) != len(self.canonical_failure_rule_ids)
            or not set(self.canonical_failure_rule_ids) <= _MECHANICAL_RULE_IDS
        ):
            raise ValueError("canonical failure rule identities are invalid")
        if any(
            (
                self.raw_prompt_retained,
                self.raw_response_retained,
                self.raw_provider_payload_retained,
                self.observer_parsed_model_output,
            )
        ):
            raise ValueError("product-boundary observations cannot retain raw material")
        _reject_unsafe_refs(self.safe_usage_refs)
        _reject_unsafe_refs(self.safe_execution_refs)

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


class CanonicalProductSearchPlannerBoundaryObserver:
    """Observe one ordinary SearchPlanner call without becoming its authority."""

    def __init__(self, model_call: Callable[..., Any]) -> None:
        if not callable(model_call):
            raise TypeError("model_call must be callable")
        self._model_call = model_call
        self._call_count = 0
        self._prompt_identity: PromptDigestObservation | None = None
        self._argument_shape: AskModelArgumentShape | None = None
        self._output_digest: str | None = None
        self._output_length = 0
        self._response_received = False

    def __call__(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> Any:
        if system_prompt != SEARCH_PLANNER_MODEL_SYSTEM_PROMPT:
            return self._model_call(prompt, system_prompt, **kwargs)

        self._call_count += 1
        self._prompt_identity = _observe_prompt_identity(prompt, system_prompt)
        self._argument_shape = _observe_argument_shape(kwargs)
        try:
            response = self._model_call(prompt, system_prompt, **kwargs)
        except Exception:
            self._response_received = False
            raise
        transient_text = str(response or "")
        self._response_received = True
        self._output_digest = _digest_text(transient_text)
        self._output_length = len(transient_text)
        return response

    def finalize(
        self,
        *,
        run_kernel: Any | None,
        failure: Exception | None = None,
        response_cleaner_ref: str = "core.text_utils.clean_json_response",
        failure_rule_ids: Sequence[str] = (),
        safe_usage_refs: Sequence[Mapping[str, Any]] = (),
        safe_execution_refs: Sequence[Mapping[str, Any]] = (),
    ) -> ProductBoundaryObservation:
        """Create one typed observation from the product-owned state."""

        state = getattr(run_kernel, "state", None)
        proposal_value = getattr(state, "search_planner_proposal_state", None)
        proposal_state = bool(proposal_value)
        acceptance_state = bool(getattr(state, "initial_answer_contract_projection", None))
        search_work_plan = bool(getattr(state, "search_work_plan", None))
        parser, validator = _parser_validator_postures(
            called=self._call_count > 0,
            proposal_state=proposal_state,
            failure=failure,
        )
        runtime = _downstream_posture(
            reached=proposal_state,
            upstream=validator,
            failed=bool(failure and not proposal_state),
        )
        acceptance = _downstream_posture(
            reached=acceptance_state,
            upstream=runtime,
            failed=bool(failure and proposal_state and not acceptance_state),
        )
        work_plan = _downstream_posture(
            reached=search_work_plan,
            upstream=acceptance,
            failed=bool(failure and acceptance_state and not search_work_plan),
        )
        bounded_reason = (
            (
                f"{type(failure).__name__}:"
                f"message_sha256={_digest_text(str(failure))}"
            )
            if failure is not None
            else None
        )
        incomplete = (
            "NOT_REACHED"
            if self._call_count == 0
            else "INCOMPLETE"
            if not self._response_received or self._output_length == 0
            else "COMPLETE"
        )
        status = "NOT_REACHED" if self._call_count == 0 else "PASS" if failure is None and acceptance_state else "FAIL"
        return ProductBoundaryObservation(
            schema_version=PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION,
            owner="CanonicalProductSearchPlannerBoundary",
            boundary_ref=CANONICAL_PRODUCT_BOUNDARY_REF,
            boundary_version=CANONICAL_PRODUCT_BOUNDARY_VERSION,
            boundary_status=status,
            product_boundary_reached=self._call_count > 0,
            model_call_count=self._call_count,
            prompt_identity=self._prompt_identity,
            ask_model_argument_shape=self._argument_shape,
            output_digest=self._output_digest,
            output_length=self._output_length,
            response_received=self._response_received,
            response_cleaning_posture=(f"PRODUCT_OWNED:{response_cleaner_ref}" if self._call_count else "NOT_REACHED"),
            parser_posture=parser,
            validator_posture=validator,
            runtime_projection_posture=runtime,
            initial_acceptance_posture=acceptance,
            search_work_plan_posture=work_plan,
            incomplete_generation_posture=incomplete,
            canonical_failure_rule_ids=tuple(failure_rule_ids),
            bounded_failure_reason=bounded_reason,
            safe_usage_refs=tuple(dict(item) for item in safe_usage_refs),
            safe_execution_refs=tuple(dict(item) for item in safe_execution_refs),
            proposal_digest=(
                _digest_text(_canonical_json(proposal_value))
                if proposal_state
                else None
            ),
        )


def _observe_prompt_identity(
    prompt: str,
    system_prompt: str,
) -> PromptDigestObservation:
    prefix, marker, serialized_packet = prompt.partition(_PROMPT_PAYLOAD_MARKER)
    if not marker:
        return PromptDigestObservation(
            semantic_input_digest=_digest_text(""),
            semantic_input_length=0,
            system_prompt_digest=_digest_text(system_prompt),
            system_prompt_length=len(system_prompt),
            instruction_digest=_digest_text(prompt),
            instruction_length=len(prompt),
            full_prompt_digest=_digest_text(prompt),
            full_prompt_length=len(prompt),
            extraction_posture="REVIEW_REQUIRED",
        )
    try:
        packet = json.loads(serialized_packet)
        planner_input = _canonical_json(dict(packet["planner_input"]))
        extraction = "PASS"
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        planner_input = ""
        extraction = "REVIEW_REQUIRED"
    instruction = prefix + marker
    return PromptDigestObservation(
        semantic_input_digest=_digest_text(planner_input),
        semantic_input_length=len(planner_input),
        system_prompt_digest=_digest_text(system_prompt),
        system_prompt_length=len(system_prompt),
        instruction_digest=_digest_text(instruction),
        instruction_length=len(instruction),
        full_prompt_digest=_digest_text(prompt),
        full_prompt_length=len(prompt),
        extraction_posture=extraction,
    )


def _observe_argument_shape(kwargs: Mapping[str, Any]) -> AskModelArgumentShape:
    return AskModelArgumentShape(
        positional_shape=("prompt:str", "system_prompt:str"),
        keyword_names=tuple(sorted(kwargs)),
        keyword_types={key: type(value).__name__ for key, value in sorted(kwargs.items())},
        require_json=kwargs.get("require_json") is True,
        provider_present=bool(str(kwargs.get("provider") or "").strip()),
        model_present=bool(str(kwargs.get("model") or "").strip()),
        reasoning_effort_present=bool(str(kwargs.get("effort") or kwargs.get("reasoning_effort") or "").strip()),
        cost_accumulator_present=kwargs.get("cost_accumulator") is not None,
        cost_phase=(str(kwargs.get("cost_phase")) if kwargs.get("cost_phase") is not None else None),
        credential_argument_present="api_key" in kwargs,
    )


def _parser_validator_postures(
    *,
    called: bool,
    proposal_state: bool,
    failure: Exception | None,
) -> tuple[str, str]:
    if not called:
        return "NOT_REACHED", "NOT_REACHED"
    if proposal_state:
        return "PASS", "PASS"
    if failure is None:
        return "REVIEW_REQUIRED", "REVIEW_REQUIRED"
    reason = str(failure).casefold()
    if "valid json" in reason or "json object" in reason:
        return "FAIL", "NOT_REACHED"
    if "search planner model output" in reason:
        return "PASS", "FAIL"
    return "REVIEW_REQUIRED", "REVIEW_REQUIRED"


def _downstream_posture(
    *,
    reached: bool,
    upstream: str,
    failed: bool,
) -> str:
    if reached:
        return "PASS"
    if upstream in {"FAIL", "NOT_REACHED"}:
        return "NOT_REACHED"
    if failed:
        return "FAIL"
    return "REVIEW_REQUIRED"


def _reject_unsafe_refs(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().casefold().replace("-", "_")
            if normalized in _FORBIDDEN_SAFE_REF_KEYS:
                raise ValueError(f"safe observation ref contains forbidden key: {normalized}")
            _reject_unsafe_refs(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_unsafe_refs(item)


__all__ = [
    "AskModelArgumentShape",
    "CANONICAL_PRODUCT_BOUNDARY_REF",
    "CANONICAL_PRODUCT_BOUNDARY_VERSION",
    "CanonicalProductSearchPlannerBoundaryObserver",
    "PRODUCT_BOUNDARY_OBSERVER_SCHEMA_VERSION",
    "ProductBoundaryObservation",
    "PromptDigestObservation",
]
