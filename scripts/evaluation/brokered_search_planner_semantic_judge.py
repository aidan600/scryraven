"""Broker-capable two-pass adapter behind the provider-neutral semantic owner."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Mapping, Protocol

from scripts.evaluation.run_analystos_model_origination_evaluation import (
    EvaluationTransportResponse,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    SEMANTIC_EXECUTION_OBSERVATION_VERSION,
    SemanticJudgeRouteAuthorization,
    canonical_json_bytes,
    canonical_sha256,
)
from scripts.evaluation.search_planner_semantic_judgment import (
    SEMANTIC_JUDGMENT_CONTRACT_VERSION,
    RequirementMapping,
    SemanticAmbiguity,
    SemanticIssue,
    SemanticJudgmentContractError,
    SemanticJudgmentRequest,
    SemanticJudgmentResult,
    SemanticPassJudgment,
    reconcile_semantic_judgments,
    validate_semantic_pass_judgment,
)

SEMANTIC_JUDGE_PRIMARY_SYSTEM_PROMPT = (
    "You are the primary SearchPlanner semantic-judgment pass. Evaluate only "
    "the supplied provider-neutral request contract. Return one strict JSON "
    "SemanticPassJudgment and no prose."
)
SEMANTIC_JUDGE_ADVERSARIAL_SYSTEM_PROMPT = (
    "You are the independent adversarial SearchPlanner semantic-judgment "
    "pass. Look for missing, incorrect, unsupported, misinterpreted, or "
    "authority-upgrading plan content. Evaluate only the supplied "
    "provider-neutral request contract. Return one strict JSON "
    "SemanticPassJudgment and no prose."
)

_PASS_FIELDS = frozenset(
    {"status", "requirement_mappings", "issues", "ambiguities"}
)
_MAPPING_FIELDS = frozenset(
    {"requirement_id", "proposal_paths", "bounded_explanation"}
)
_ISSUE_FIELDS = frozenset(
    {
        "requirement_id",
        "issue_kind",
        "proposal_paths",
        "answer_blocking",
        "bounded_explanation",
    }
)
_AMBIGUITY_FIELDS = frozenset(
    {
        "requirement_id",
        "precise_ambiguity",
        "competing_interpretations",
        "proposal_paths",
        "smallest_review_action",
    }
)
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")


class BrokeredSemanticJudgeError(ValueError):
    """Raised when execution facts cannot be represented truthfully."""


class SemanticJudgeTransport(Protocol):
    def __call__(
        self,
        *,
        role: str,
        prompt: str,
        system_prompt: str,
        provider: str,
        model: str,
        maximum_input_tokens: int,
        maximum_output_tokens: int,
        correlation_id: str,
    ) -> EvaluationTransportResponse: ...


@dataclass(frozen=True, slots=True)
class SemanticJudgePassExecutionFact:
    pass_kind: str
    call_id: str
    execution_identity_digest: str
    request_packet_digest: str
    response_digest: str | None
    response_length: int
    response_presence_posture: str
    parse_posture: str
    contract_validation_posture: str
    validated_pass_status: str | None
    route_attestation: Mapping[str, Any]
    usage_attestation: Mapping[str, Any]
    token_accounting: Mapping[str, Any]
    cost_accounting_usd: str | None
    bounded_failure_fact: str | None

    def __post_init__(self) -> None:
        if self.pass_kind not in {"primary", "adversarial"}:
            raise BrokeredSemanticJudgeError(
                "semantic execution pass kind is unsupported"
            )
        if not str(self.call_id or "").strip():
            raise BrokeredSemanticJudgeError(
                "semantic execution call ID must be explicit"
            )
        for label in (
            "execution_identity_digest",
            "request_packet_digest",
        ):
            if not _DIGEST_PATTERN.fullmatch(getattr(self, label)):
                raise BrokeredSemanticJudgeError(
                    f"{label} must be one SHA-256 digest"
                )
        if self.response_digest is not None and not _DIGEST_PATTERN.fullmatch(
            self.response_digest
        ):
            raise BrokeredSemanticJudgeError(
                "semantic response digest must be one SHA-256 digest"
            )
        if self.response_length < 0:
            raise BrokeredSemanticJudgeError(
                "semantic response length cannot be negative"
            )
        if self.response_presence_posture not in {
            "PRESENT",
            "MISSING",
            "NOT_RUN",
        }:
            raise BrokeredSemanticJudgeError(
                "semantic response-presence posture is unsupported"
            )
        if self.parse_posture not in {"PASS", "FAIL", "NOT_RUN"}:
            raise BrokeredSemanticJudgeError(
                "semantic parse posture is unsupported"
            )
        if self.contract_validation_posture not in {
            "PASS",
            "FAIL",
            "NOT_RUN",
        }:
            raise BrokeredSemanticJudgeError(
                "semantic contract-validation posture is unsupported"
            )
        if self.validated_pass_status not in {
            "MET",
            "NOT_MET",
            "REVIEW_REQUIRED",
            None,
        }:
            raise BrokeredSemanticJudgeError(
                "validated semantic pass status is unsupported"
            )
        if self.contract_validation_posture == "PASS":
            if self.validated_pass_status is None:
                raise BrokeredSemanticJudgeError(
                    "validated pass status is required after contract PASS"
                )
        elif self.validated_pass_status is not None:
            raise BrokeredSemanticJudgeError(
                "nonvalidated semantic pass cannot carry a status"
            )
        if self.response_presence_posture == "NOT_RUN":
            if (
                self.response_digest is not None
                or self.response_length
                or self.parse_posture != "NOT_RUN"
                or self.contract_validation_posture != "NOT_RUN"
            ):
                raise BrokeredSemanticJudgeError(
                    "NOT_RUN semantic pass contains execution facts"
                )
        if self.bounded_failure_fact is not None and (
            not self.bounded_failure_fact.strip()
            or len(self.bounded_failure_fact) > 240
        ):
            raise BrokeredSemanticJudgeError(
                "semantic failure fact must be bounded"
            )
        _reject_raw_material(asdict(self))


@dataclass(frozen=True, slots=True)
class SearchPlannerSemanticJudgeExecutionObservation:
    schema_version: str
    owner: str
    semantic_request_id: str
    semantic_request_packet_digest: str
    semantic_contract_version: str
    proposal_digest: str
    mechanical_result_ref: str
    semantic_judge_route_identity_digest: str
    primary_pass: SemanticJudgePassExecutionFact
    adversarial_pass: SemanticJudgePassExecutionFact
    cumulative_semantic_judge_cost_usd: str
    semantic_judge_call_cap_consumption: Mapping[str, int]
    reconciliation_posture: str
    retention_posture: Mapping[str, bool]
    bounded_failure_facts: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != SEMANTIC_EXECUTION_OBSERVATION_VERSION:
            raise BrokeredSemanticJudgeError(
                "semantic execution observation version is unsupported"
            )
        if (
            self.owner
            != "SearchPlannerSemanticJudgeExecutionObservation"
        ):
            raise BrokeredSemanticJudgeError(
                "semantic execution observation owner is invalid"
            )
        if self.semantic_contract_version != SEMANTIC_JUDGMENT_CONTRACT_VERSION:
            raise BrokeredSemanticJudgeError(
                "semantic execution contract version is invalid"
            )
        for label in (
            "semantic_request_packet_digest",
            "proposal_digest",
            "semantic_judge_route_identity_digest",
        ):
            if not _DIGEST_PATTERN.fullmatch(getattr(self, label)):
                raise BrokeredSemanticJudgeError(
                    f"{label} must be one SHA-256 digest"
                )
        if self.semantic_request_id != (
            f"semantic-judgment:{self.semantic_request_packet_digest}"
        ):
            raise BrokeredSemanticJudgeError(
                "semantic execution request identity is invalid"
            )
        if not re.fullmatch(
            r"mechanical-result:[0-9a-f]{64}",
            self.mechanical_result_ref,
        ):
            raise BrokeredSemanticJudgeError(
                "semantic execution mechanical reference is invalid"
            )
        if (
            self.primary_pass.call_id == self.adversarial_pass.call_id
            or self.primary_pass.execution_identity_digest
            == self.adversarial_pass.execution_identity_digest
        ):
            raise BrokeredSemanticJudgeError(
                "semantic judge passes require distinct call and execution identities"
            )
        if self.reconciliation_posture not in {"PASS", "NOT_RUN"}:
            raise BrokeredSemanticJudgeError(
                "semantic reconciliation posture is unsupported"
            )
        consumed = dict(self.semantic_judge_call_cap_consumption)
        if set(consumed) != {
            "primary_calls",
            "adversarial_calls",
            "total_calls",
        }:
            raise BrokeredSemanticJudgeError(
                "semantic call-cap consumption is incomplete"
            )
        expected_primary = int(
            self.primary_pass.response_presence_posture != "NOT_RUN"
        )
        expected_adversarial = int(
            self.adversarial_pass.response_presence_posture != "NOT_RUN"
        )
        if consumed != {
            "primary_calls": expected_primary,
            "adversarial_calls": expected_adversarial,
            "total_calls": expected_primary + expected_adversarial,
        }:
            raise BrokeredSemanticJudgeError(
                "semantic call-cap consumption differs from pass facts"
            )
        cost = _decimal_or_error(
            self.cumulative_semantic_judge_cost_usd,
            "cumulative semantic-judge cost",
        )
        expected_cost = sum(
            (
                _decimal_or_error(
                    item.cost_accounting_usd,
                    "semantic pass cost",
                )
                if item.cost_accounting_usd is not None
                else Decimal("0")
            )
            for item in (self.primary_pass, self.adversarial_pass)
        )
        if cost != expected_cost:
            raise BrokeredSemanticJudgeError(
                "cumulative semantic-judge cost differs from pass accounting"
            )
        if (
            set(self.retention_posture)
            != {
                "raw_judge_prompts_retained",
                "raw_judge_responses_retained",
                "provider_payloads_retained",
                "reasoning_traces_retained",
            }
            or any(self.retention_posture.values())
        ):
            raise BrokeredSemanticJudgeError(
                "semantic execution retention posture is invalid"
            )
        if any(
            not item.strip() or len(item) > 240
            for item in self.bounded_failure_facts
        ):
            raise BrokeredSemanticJudgeError(
                "semantic execution failure facts must be bounded"
            )
        if self.reconciliation_posture == "PASS":
            if (
                self.primary_pass.contract_validation_posture != "PASS"
                or self.adversarial_pass.contract_validation_posture
                != "PASS"
                or self.bounded_failure_facts
            ):
                raise BrokeredSemanticJudgeError(
                    "semantic reconciliation PASS lacks two validated passes"
                )
        _reject_raw_material(self.to_packet(validate=False))

    def to_packet(self, *, validate: bool = True) -> dict[str, Any]:
        if validate:
            self.__post_init__()
        return asdict(self)

    @property
    def observation_digest(self) -> str:
        return canonical_sha256(self.to_packet())


@dataclass(frozen=True, slots=True)
class BrokeredSemanticJudgmentOutcome:
    semantic_result: SemanticJudgmentResult | None
    execution_observation: (
        SearchPlannerSemanticJudgeExecutionObservation
    )


class BrokeredSearchPlannerSemanticJudge:
    """Execute two blinded broker calls, then delegate meaning to the owner."""

    def __init__(
        self,
        *,
        transport: SemanticJudgeTransport,
        route: SemanticJudgeRouteAuthorization,
    ) -> None:
        if not callable(transport):
            raise TypeError("semantic judge transport must be callable")
        route.__post_init__()
        self._transport = transport
        self._route = route

    def judge(
        self,
        request: SemanticJudgmentRequest,
        *,
        primary_call_id: str,
        adversarial_call_id: str,
    ) -> BrokeredSemanticJudgmentOutcome:
        request.__post_init__()
        if (
            not primary_call_id
            or not adversarial_call_id
            or primary_call_id == adversarial_call_id
        ):
            raise BrokeredSemanticJudgeError(
                "semantic judge calls require distinct pre-reserved identities"
            )
        route_digest = canonical_sha256(self._route.to_packet())
        primary_prompt, primary_request_digest = _build_pass_prompt(
            request,
            pass_kind="primary",
        )
        adversarial_prompt, adversarial_request_digest = _build_pass_prompt(
            request,
            pass_kind="adversarial",
        )
        primary_execution_digest = _execution_identity_digest(
            call_id=primary_call_id,
            pass_kind="primary",
            semantic_request=request,
            route_digest=route_digest,
            request_packet_digest=primary_request_digest,
        )
        adversarial_execution_digest = _execution_identity_digest(
            call_id=adversarial_call_id,
            pass_kind="adversarial",
            semantic_request=request,
            route_digest=route_digest,
            request_packet_digest=adversarial_request_digest,
        )

        primary_response = self._call(
            prompt=primary_prompt,
            system_prompt=SEMANTIC_JUDGE_PRIMARY_SYSTEM_PROMPT,
            call_id=primary_call_id,
        )
        primary_prompt = ""
        primary_judgment, primary_fact = self._parse_pass_response(
            request=request,
            response=primary_response,
            pass_kind="primary",
            call_id=primary_call_id,
            execution_identity_digest=primary_execution_digest,
            request_packet_digest=primary_request_digest,
        )
        primary_response = None
        if primary_judgment is None:
            adversarial_fact = _not_run_fact(
                pass_kind="adversarial",
                call_id=adversarial_call_id,
                execution_identity_digest=adversarial_execution_digest,
                request_packet_digest=adversarial_request_digest,
            )
            adversarial_prompt = ""
            return BrokeredSemanticJudgmentOutcome(
                semantic_result=None,
                execution_observation=_build_observation(
                    request=request,
                    route_digest=route_digest,
                    primary=primary_fact,
                    adversarial=adversarial_fact,
                    reconciliation_posture="NOT_RUN",
                ),
            )

        adversarial_response = self._call(
            prompt=adversarial_prompt,
            system_prompt=SEMANTIC_JUDGE_ADVERSARIAL_SYSTEM_PROMPT,
            call_id=adversarial_call_id,
        )
        adversarial_prompt = ""
        adversarial_judgment, adversarial_fact = self._parse_pass_response(
            request=request,
            response=adversarial_response,
            pass_kind="adversarial",
            call_id=adversarial_call_id,
            execution_identity_digest=adversarial_execution_digest,
            request_packet_digest=adversarial_request_digest,
        )
        adversarial_response = None
        if adversarial_judgment is None:
            return BrokeredSemanticJudgmentOutcome(
                semantic_result=None,
                execution_observation=_build_observation(
                    request=request,
                    route_digest=route_digest,
                    primary=primary_fact,
                    adversarial=adversarial_fact,
                    reconciliation_posture="NOT_RUN",
                ),
            )
        semantic_result = reconcile_semantic_judgments(
            request,
            primary=primary_judgment,
            adversarial=adversarial_judgment,
        )
        observation = _build_observation(
            request=request,
            route_digest=route_digest,
            primary=primary_fact,
            adversarial=adversarial_fact,
            reconciliation_posture="PASS",
        )
        validate_semantic_result_execution_pair(
            semantic_result,
            observation,
        )
        return BrokeredSemanticJudgmentOutcome(
            semantic_result=semantic_result,
            execution_observation=observation,
        )

    def _call(
        self,
        *,
        prompt: str,
        system_prompt: str,
        call_id: str,
    ) -> EvaluationTransportResponse:
        return self._transport(
            role=self._route.role,
            prompt=prompt,
            system_prompt=system_prompt,
            provider=self._route.provider,
            model=self._route.model,
            maximum_input_tokens=self._route.maximum_input_tokens,
            maximum_output_tokens=self._route.maximum_output_tokens,
            correlation_id=call_id,
        )

    def _parse_pass_response(
        self,
        *,
        request: SemanticJudgmentRequest,
        response: EvaluationTransportResponse,
        pass_kind: str,
        call_id: str,
        execution_identity_digest: str,
        request_packet_digest: str,
    ) -> tuple[
        SemanticPassJudgment | None,
        SemanticJudgePassExecutionFact,
    ]:
        route_attestation, usage_attestation, token_accounting, cost = (
            _validate_safe_response(response, self._route)
        )
        response_text = (
            str(response.output)
            if response.output is not None
            else ""
        )
        response_digest = sha256(
            response_text.encode("utf-8")
        ).hexdigest()
        response_length = len(response_text)
        failure: str | None = None
        parsed: SemanticPassJudgment | None = None
        parse_posture = "NOT_RUN"
        contract_posture = "NOT_RUN"
        if (
            response.generation_status != "completed"
            or not response.output_text_present
            or not response_text
        ):
            failure = _bounded_failure(
                "IncompleteSemanticJudgeResponse",
                response.generation_incomplete_reason
                or "output_not_present",
            )
            parse_posture = "FAIL"
            contract_posture = "NOT_RUN"
        else:
            try:
                parsed = parse_semantic_pass_judgment(response_text)
                parse_posture = "PASS"
                parsed = validate_semantic_pass_judgment(
                    request,
                    parsed,
                    pass_label=pass_kind,
                )
                contract_posture = "PASS"
            except (
                BrokeredSemanticJudgeError,
                SemanticJudgmentContractError,
                json.JSONDecodeError,
                KeyError,
                TypeError,
                ValueError,
            ) as exc:
                failure = _bounded_failure(
                    type(exc).__name__,
                    str(exc),
                )
                if parse_posture != "PASS":
                    parse_posture = "FAIL"
                contract_posture = "FAIL"
                parsed = None
        response_text = ""
        fact = SemanticJudgePassExecutionFact(
            pass_kind=pass_kind,
            call_id=call_id,
            execution_identity_digest=execution_identity_digest,
            request_packet_digest=request_packet_digest,
            response_digest=response_digest,
            response_length=response_length,
            response_presence_posture=(
                "PRESENT"
                if response.output_text_present and response_length
                else "MISSING"
            ),
            parse_posture=parse_posture,
            contract_validation_posture=contract_posture,
            validated_pass_status=(
                parsed.status if parsed is not None else None
            ),
            route_attestation=route_attestation,
            usage_attestation=usage_attestation,
            token_accounting=token_accounting,
            cost_accounting_usd=cost,
            bounded_failure_fact=failure,
        )
        return parsed, fact


def validate_semantic_result_execution_pair(
    semantic_result: SemanticJudgmentResult,
    observation: SearchPlannerSemanticJudgeExecutionObservation,
) -> None:
    """Require exactly one matching execution observation for a live result."""

    semantic_result.__post_init__()
    observation.__post_init__()
    if (
        semantic_result.request_id != observation.semantic_request_id
        or semantic_result.input_packet_digest
        != observation.semantic_request_packet_digest
        or semantic_result.judge_contract_version
        != observation.semantic_contract_version
        or semantic_result.proposal_digest != observation.proposal_digest
        or semantic_result.deterministic_result_ref
        != observation.mechanical_result_ref
        or semantic_result.primary_judgment.status
        != observation.primary_pass.validated_pass_status
        or semantic_result.adversarial_challenge.status
        != observation.adversarial_pass.validated_pass_status
        or observation.reconciliation_posture != "PASS"
    ):
        raise BrokeredSemanticJudgeError(
            "semantic result and execution observation do not bind exactly"
        )
    if (
        semantic_result.provider_selected
        or semantic_result.model_selected
        or semantic_result.live_call_count
    ):
        raise BrokeredSemanticJudgeError(
            "semantic result execution telemetry must remain provider-neutral"
        )


def parse_semantic_pass_judgment(
    value: str,
) -> SemanticPassJudgment:
    """Parse one strict pass object; semantic meaning is validated separately."""

    try:
        raw = json.loads(
            value,
            parse_constant=lambda item: (_raise_nonfinite(item)),
        )
    except json.JSONDecodeError:
        raise
    if not isinstance(raw, Mapping):
        raise BrokeredSemanticJudgeError(
            "semantic pass response must be one object"
        )
    _require_exact_fields(raw, _PASS_FIELDS, "semantic pass")
    mappings = tuple(
        _parse_mapping(item)
        for item in _require_array(
            raw["requirement_mappings"],
            "requirement_mappings",
        )
    )
    issues = tuple(
        _parse_issue(item)
        for item in _require_array(raw["issues"], "issues")
    )
    ambiguities = tuple(
        _parse_ambiguity(item)
        for item in _require_array(raw["ambiguities"], "ambiguities")
    )
    return SemanticPassJudgment(
        status=_require_text(raw["status"], "status"),
        requirement_mappings=mappings,
        issues=issues,
        ambiguities=ambiguities,
    )


def _build_pass_prompt(
    request: SemanticJudgmentRequest,
    *,
    pass_kind: str,
) -> tuple[str, str]:
    if pass_kind not in {"primary", "adversarial"}:
        raise BrokeredSemanticJudgeError(
            "semantic pass kind is unsupported"
        )
    packet = {
        "semantic_pass_contract": {
            "status_values": [
                "MET",
                "NOT_MET",
                "REVIEW_REQUIRED",
            ],
            "required_fields": [
                "status",
                "requirement_mappings",
                "issues",
                "ambiguities",
            ],
            "pass_kind": pass_kind,
        },
        "semantic_judgment_request": request.to_packet(),
    }
    prompt = canonical_json_bytes(packet).decode("utf-8")
    system_prompt = (
        SEMANTIC_JUDGE_PRIMARY_SYSTEM_PROMPT
        if pass_kind == "primary"
        else SEMANTIC_JUDGE_ADVERSARIAL_SYSTEM_PROMPT
    )
    request_digest = canonical_sha256(
        {
            "semantic_request_id": request.request_id,
            "pass_kind": pass_kind,
            "system_prompt_sha256": sha256(
                system_prompt.encode("utf-8")
            ).hexdigest(),
            "input_prompt_sha256": sha256(
                prompt.encode("utf-8")
            ).hexdigest(),
        }
    )
    return prompt, request_digest


def _execution_identity_digest(
    *,
    call_id: str,
    pass_kind: str,
    semantic_request: SemanticJudgmentRequest,
    route_digest: str,
    request_packet_digest: str,
) -> str:
    return canonical_sha256(
        {
            "call_id": call_id,
            "pass_kind": pass_kind,
            "semantic_request_id": semantic_request.request_id,
            "semantic_request_packet_digest": (
                semantic_request.input_packet_digest
            ),
            "proposal_digest": semantic_request.proposal_digest,
            "mechanical_result_ref": (
                semantic_request.deterministic_result_ref
            ),
            "semantic_contract_version": (
                semantic_request.judge_contract_version
            ),
            "semantic_judge_route_identity_digest": route_digest,
            "request_packet_digest": request_packet_digest,
        }
    )


def _validate_safe_response(
    response: EvaluationTransportResponse,
    route: SemanticJudgeRouteAuthorization,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    if (
        response.canonical_provider_used != route.provider
        or response.canonical_model_used != route.model
        or response.reasoning_effort != route.reasoning_effort
        or response.provider_request_attempt_count != 1
        or response.raw_material_retained
    ):
        raise BrokeredSemanticJudgeError(
            "semantic judge route or retention attestation is invalid"
        )
    if not response.usage_observed:
        raise BrokeredSemanticJudgeError(
            "semantic judge usage must be observed"
        )
    for label, value, maximum in (
        (
            "input_tokens",
            response.input_tokens,
            route.maximum_input_tokens,
        ),
        (
            "output_tokens",
            response.output_tokens,
            route.maximum_output_tokens,
        ),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > maximum
        ):
            raise BrokeredSemanticJudgeError(
                f"semantic judge {label} attestation is invalid"
            )
    if response.cost_posture != "exact":
        raise BrokeredSemanticJudgeError(
            "semantic judge cost posture must be exact"
        )
    cost = response.caller_calculated_route_priced_cost_usd
    parsed_cost = _decimal_or_error(cost, "semantic judge call cost")
    if parsed_cost > Decimal(route.per_call_cost_ceiling_usd):
        raise BrokeredSemanticJudgeError(
            "semantic judge call exceeded its cost ceiling"
        )
    if (
        response.output_text_character_count
        != len(str(response.output or ""))
        or response.output_text_digest
        != sha256(str(response.output or "").encode("utf-8")).hexdigest()
    ):
        raise BrokeredSemanticJudgeError(
            "semantic judge safe response identity is invalid"
        )
    route_attestation = {
        "provider_matches_authorization": True,
        "model_matches_authorization": True,
        "reasoning_effort_matches_authorization": True,
        "physical_attempt_count": 1,
        "raw_material_retained": False,
    }
    usage_attestation = {
        "posture": "OBSERVED_AND_WITHIN_CAP",
        "input_within_cap": True,
        "output_within_cap": True,
        "cost_within_cap": True,
    }
    token_accounting = {
        "input_tokens": response.input_tokens,
        "cached_input_tokens": response.cached_input_tokens,
        "uncached_input_tokens": response.uncached_input_tokens,
        "output_tokens": response.output_tokens,
        "reasoning_tokens": response.reasoning_tokens,
        "non_reasoning_output_tokens": (
            response.non_reasoning_output_tokens
        ),
        "total_tokens": response.total_tokens,
    }
    return route_attestation, usage_attestation, token_accounting, str(cost)


def _build_observation(
    *,
    request: SemanticJudgmentRequest,
    route_digest: str,
    primary: SemanticJudgePassExecutionFact,
    adversarial: SemanticJudgePassExecutionFact,
    reconciliation_posture: str,
) -> SearchPlannerSemanticJudgeExecutionObservation:
    failures = tuple(
        item.bounded_failure_fact
        for item in (primary, adversarial)
        if item.bounded_failure_fact is not None
    )
    cost = sum(
        (
            _decimal_or_error(
                item.cost_accounting_usd,
                "semantic pass cost",
            )
            if item.cost_accounting_usd is not None
            else Decimal("0")
        )
        for item in (primary, adversarial)
    )
    return SearchPlannerSemanticJudgeExecutionObservation(
        schema_version=SEMANTIC_EXECUTION_OBSERVATION_VERSION,
        owner="SearchPlannerSemanticJudgeExecutionObservation",
        semantic_request_id=request.request_id,
        semantic_request_packet_digest=request.input_packet_digest,
        semantic_contract_version=request.judge_contract_version,
        proposal_digest=request.proposal_digest,
        mechanical_result_ref=request.deterministic_result_ref,
        semantic_judge_route_identity_digest=route_digest,
        primary_pass=primary,
        adversarial_pass=adversarial,
        cumulative_semantic_judge_cost_usd=format(cost, "f"),
        semantic_judge_call_cap_consumption={
            "primary_calls": int(
                primary.response_presence_posture != "NOT_RUN"
            ),
            "adversarial_calls": int(
                adversarial.response_presence_posture != "NOT_RUN"
            ),
            "total_calls": sum(
                (
                    int(
                        primary.response_presence_posture != "NOT_RUN"
                    ),
                    int(
                        adversarial.response_presence_posture
                        != "NOT_RUN"
                    ),
                )
            ),
        },
        reconciliation_posture=reconciliation_posture,
        retention_posture={
            "raw_judge_prompts_retained": False,
            "raw_judge_responses_retained": False,
            "provider_payloads_retained": False,
            "reasoning_traces_retained": False,
        },
        bounded_failure_facts=failures,
    )


def _not_run_fact(
    *,
    pass_kind: str,
    call_id: str,
    execution_identity_digest: str,
    request_packet_digest: str,
) -> SemanticJudgePassExecutionFact:
    return SemanticJudgePassExecutionFact(
        pass_kind=pass_kind,
        call_id=call_id,
        execution_identity_digest=execution_identity_digest,
        request_packet_digest=request_packet_digest,
        response_digest=None,
        response_length=0,
        response_presence_posture="NOT_RUN",
        parse_posture="NOT_RUN",
        contract_validation_posture="NOT_RUN",
        validated_pass_status=None,
        route_attestation={"posture": "NOT_RUN"},
        usage_attestation={"posture": "NOT_RUN"},
        token_accounting={
            "input_tokens": None,
            "cached_input_tokens": None,
            "uncached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "non_reasoning_output_tokens": None,
            "total_tokens": None,
        },
        cost_accounting_usd=None,
        bounded_failure_fact=None,
    )


def _parse_mapping(value: Any) -> RequirementMapping:
    raw = _object(value, "requirement mapping")
    _require_exact_fields(raw, _MAPPING_FIELDS, "requirement mapping")
    return RequirementMapping(
        requirement_id=_require_text(
            raw["requirement_id"],
            "mapping requirement_id",
        ),
        proposal_paths=_text_tuple(
            raw["proposal_paths"],
            "mapping proposal_paths",
        ),
        bounded_explanation=_require_text(
            raw["bounded_explanation"],
            "mapping bounded_explanation",
            maximum=1000,
        ),
    )


def _parse_issue(value: Any) -> SemanticIssue:
    raw = _object(value, "semantic issue")
    _require_exact_fields(raw, _ISSUE_FIELDS, "semantic issue")
    if not isinstance(raw["answer_blocking"], bool):
        raise BrokeredSemanticJudgeError(
            "semantic issue answer_blocking must be boolean"
        )
    return SemanticIssue(
        requirement_id=_require_text(
            raw["requirement_id"],
            "issue requirement_id",
        ),
        issue_kind=_require_text(
            raw["issue_kind"],
            "issue_kind",
        ),
        proposal_paths=_text_tuple(
            raw["proposal_paths"],
            "issue proposal_paths",
        ),
        answer_blocking=raw["answer_blocking"],
        bounded_explanation=_require_text(
            raw["bounded_explanation"],
            "issue bounded_explanation",
            maximum=1000,
        ),
    )


def _parse_ambiguity(value: Any) -> SemanticAmbiguity:
    raw = _object(value, "semantic ambiguity")
    _require_exact_fields(
        raw,
        _AMBIGUITY_FIELDS,
        "semantic ambiguity",
    )
    return SemanticAmbiguity(
        requirement_id=_require_text(
            raw["requirement_id"],
            "ambiguity requirement_id",
        ),
        precise_ambiguity=_require_text(
            raw["precise_ambiguity"],
            "precise_ambiguity",
            maximum=1000,
        ),
        competing_interpretations=_text_tuple(
            raw["competing_interpretations"],
            "competing_interpretations",
        ),
        proposal_paths=_text_tuple(
            raw["proposal_paths"],
            "ambiguity proposal_paths",
        ),
        smallest_review_action=_require_text(
            raw["smallest_review_action"],
            "smallest_review_action",
            maximum=1000,
        ),
    )


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BrokeredSemanticJudgeError(
            f"{label} must be one object"
        )
    return value


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    if set(value) != expected:
        raise BrokeredSemanticJudgeError(
            f"{label} fields differ from the strict contract"
        )


def _require_array(value: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(value, list):
        raise BrokeredSemanticJudgeError(
            f"{label} must be one JSON array"
        )
    return tuple(value)


def _require_text(
    value: Any,
    label: str,
    *,
    maximum: int = 160,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
    ):
        raise BrokeredSemanticJudgeError(
            f"{label} must be an explicit bounded string"
        )
    return value


def _text_tuple(value: Any, label: str) -> tuple[str, ...]:
    items = _require_array(value, label)
    if not items:
        raise BrokeredSemanticJudgeError(
            f"{label} must be nonempty"
        )
    return tuple(
        _require_text(item, f"{label} item", maximum=1000)
        for item in items
    )


def _raise_nonfinite(value: str) -> None:
    raise BrokeredSemanticJudgeError(
        f"semantic pass contains non-finite JSON: {value}"
    )


def _decimal_or_error(
    value: str | None,
    label: str,
) -> Decimal:
    if value is None:
        raise BrokeredSemanticJudgeError(
            f"{label} must be observed"
        )
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BrokeredSemanticJudgeError(
            f"{label} must be an exact decimal"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise BrokeredSemanticJudgeError(
            f"{label} must be finite and nonnegative"
        )
    return parsed


def _bounded_failure(kind: str, message: str) -> str:
    digest = sha256(str(message).encode("utf-8")).hexdigest()
    return f"{kind}:message_sha256={digest}"[:240]


def _reject_raw_material(value: Any) -> None:
    forbidden = {
        "arm_id",
        "chain_of_thought",
        "control",
        "experiment_arm_id",
        "full_prompt",
        "instruction_digest",
        "model_response",
        "planner_prompt",
        "prompt_text",
        "provider_payload",
        "raw_judge_response",
        "raw_planner_response",
        "reasoning_trace",
        "semantic_judge_prompt",
        "trial_order",
        "variant",
    }
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = (
                str(key).strip().casefold().replace("-", "_")
            )
            if normalized in forbidden:
                raise BrokeredSemanticJudgeError(
                    "semantic execution observation contains forbidden material"
                )
            _reject_raw_material(nested)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_raw_material(item)


__all__ = [
    "BrokeredSearchPlannerSemanticJudge",
    "BrokeredSemanticJudgeError",
    "BrokeredSemanticJudgmentOutcome",
    "SEMANTIC_JUDGE_ADVERSARIAL_SYSTEM_PROMPT",
    "SEMANTIC_JUDGE_PRIMARY_SYSTEM_PROMPT",
    "SearchPlannerSemanticJudgeExecutionObservation",
    "SemanticJudgePassExecutionFact",
    "parse_semantic_pass_judgment",
    "validate_semantic_result_execution_pair",
]
