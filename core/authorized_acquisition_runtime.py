"""RunKernel-guarded post-discovery acquisition executors.

This module is the PRODUCT boundary between RunKernel-owned acquisition control
and the provider-neutral mechanical adapter.  Capability interpretation and
work-order construction are delegated to ``core.acquisition_control``;
provider selection is delegated exclusively to ``core.routing``; and exactly
one already-authorized request may reach ``dispatch_acquisition``.

Execution results remain acquisition material only.  Nothing in this module
admits evidence, satisfies a source obligation, authorizes a citation, decides
sufficiency, or grants FinalAnswerPacket/Author authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from core.acquisition_adapters import AcquisitionTransports, dispatch_acquisition
from core.acquisition_contracts import (
    CRAWL_AGGREGATE_RETAINED_CHARACTER_CEILING,
    READ_RETAINED_CHARACTER_CEILING,
    AcquisitionArtifact,
    AcquisitionExecutionResult,
    AcquisitionExecutionStatus,
    AcquisitionRequest,
)
from core.acquisition_control import (
    AcquisitionCapabilityDecisionObservationV1,
    AcquisitionControlError,
    AcquisitionCustodyAuthorizationV1,
    AcquisitionExecutionObservationV1,
    AcquisitionExecutionObservationV2,
    AcquisitionNeedProposalV1,
    AcquisitionNeedProposalV2,
    AcquisitionRouteObservationV1,
    AcquisitionTerminalReceiptV1,
    AcquisitionWorkOrderV1,
    AcquisitionWorkOrderV2,
    build_acquisition_work_order,
    build_terminal_receipt_from_decision,
    build_terminal_receipt_from_execution,
    build_terminal_receipt_from_route,
    build_terminal_receipt_from_work_order_invalidation,
    derive_acquisition_capability_decision,
    ensure_acquisition_control_state,
    stable_json_digest,
)
from core.cap_enforcement import RunCapExceeded
from core.routing import (
    PROVIDER_NAMES,
    AcquisitionCapability,
    ProviderAvailability,
    ProviderCapabilityRequest,
    ProviderRouteDecision,
    acquisition_routing_policy_ref,
    route_provider_capability,
)
from core.run_kernel import (
    AuthorizedAction,
    Observation,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
    validate_authorized_action,
)
from core.searchos_navigation_runtime import (
    SearchOSNavigationError,
    SearchOSNavigationExecutionOverlayV1,
    validate_navigation_execution_artifact,
)

ACQUISITION_CAPABILITY_DECISION_STAGE = "acquisition_capability_decision"
ACQUISITION_WORK_ORDER_STAGE = "acquisition_work_order_admission"
ACQUISITION_ROUTE_STAGE = "acquisition_route"
ACQUISITION_EXECUTION_STAGE = "acquisition_execution"
ACQUISITION_TERMINAL_REDUCTION_STAGE = "acquisition_terminal_reduction"
ACQUISITION_CUSTODY_STAGE = "acquisition_custody_consumption"

ACQUISITION_CAPABILITY_DECIDE_ACTION = "acquisition_capability_decide"
ACQUISITION_WORK_ORDER_ADMIT_ACTION = "acquisition_work_order_admit"
ACQUISITION_ROUTE_ACTION = "acquisition_route"
ACQUISITION_EXECUTE_ACTION = "acquisition_execute"
ACQUISITION_TERMINAL_REDUCE_ACTION = "acquisition_terminal_reduce"
ACQUISITION_CUSTODY_CONSUME_ACTION = "acquisition_custody_consume"

ACQUISITION_CAPABILITY_DECIDED_OBSERVATION = "acquisition_capability_decided"
ACQUISITION_WORK_ORDER_ADMITTED_OBSERVATION = "acquisition_work_order_admitted"
ACQUISITION_ROUTE_OBSERVED_OBSERVATION = "acquisition_route_completed"
ACQUISITION_EXECUTION_OBSERVED_OBSERVATION = "acquisition_execution_observed"
ACQUISITION_TERMINAL_REDUCED_OBSERVATION = "acquisition_terminal_reduced"
ACQUISITION_CUSTODY_AUTHORIZED_OBSERVATION = "acquisition_custody_authorized"

PROVIDER_AVAILABILITY_SNAPSHOT_SCHEMA_VERSION = "provider_availability_snapshot_v1"


@dataclass(frozen=True, slots=True)
class AcquisitionCapabilityDecisionRuntimeResult:
    """Deterministic capability decision plus its reducible observation."""

    decision: AcquisitionCapabilityDecisionObservationV1
    observation: Observation


@dataclass(frozen=True, slots=True)
class AcquisitionWorkOrderAdmissionRuntimeResult:
    """Provider-neutral admitted work order plus its observation."""

    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2
    observation: Observation


@dataclass(frozen=True, slots=True)
class AcquisitionRouteRuntimeResult:
    """Completed core.routing decision and compact reducible route fact."""

    route_decision: ProviderRouteDecision
    route_observation: AcquisitionRouteObservationV1
    availability_snapshot_ref: Mapping[str, Any]
    observation: Observation


@dataclass(frozen=True, slots=True)
class AuthorizedAcquisitionExecutionRuntimeResult:
    """Ephemeral material, compact execution fact, and deferred cap error."""

    execution_result: AcquisitionExecutionResult
    execution_observation: (
        AcquisitionExecutionObservationV1 | AcquisitionExecutionObservationV2
    )
    observation: Observation
    deferred_error: RunCapExceeded | None = None
    navigation_response_validation: Mapping[str, Any] | None = None

    def raise_deferred_error(self) -> None:
        """Re-raise a run-cap terminal after RunKernel releases active custody."""

        if self.deferred_error is not None:
            raise self.deferred_error


@dataclass(frozen=True, slots=True)
class AcquisitionTerminalReductionRuntimeResult:
    """One terminal receipt ready for canonical RunKernel reduction."""

    terminal_receipt: AcquisitionTerminalReceiptV1
    observation: Observation


@dataclass(frozen=True, slots=True)
class AcquisitionCustodyAuthorizationRuntimeResult:
    """Successful-material custody authorization and its observation."""

    custody_authorization: AcquisitionCustodyAuthorizationV1
    observation: Observation


def build_provider_availability_snapshot_ref(
    available_providers: Mapping[str, object] | None,
    *,
    work_order_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind route authorization to boolean-only provider availability facts."""

    availability = ProviderAvailability.from_boolean_mapping(
        available_providers
    )
    core = {
        "schema_version": PROVIDER_AVAILABILITY_SNAPSHOT_SCHEMA_VERSION,
        "provider_availability": availability.to_mapping(),
        "provider_names": list(PROVIDER_NAMES),
        "boolean_only": True,
    }
    digest = stable_json_digest(core)
    work_order_id = str((work_order_ref or {}).get("work_order_id") or "")
    identity = f"{work_order_id}:" if work_order_id else ""
    return {
        "availability_snapshot_id": f"provider-availability:{identity}{digest[:20]}",
        "availability_snapshot_digest": digest,
    }


def execute_acquisition_capability_decision_action(
    action: AuthorizedAction,
    *,
    proposal: AcquisitionNeedProposalV1 | AcquisitionNeedProposalV2,
    authority_snapshot: Mapping[str, Any],
    acquisition_control_state: Mapping[str, Any],
) -> AcquisitionCapabilityDecisionRuntimeResult:
    """Derive capability after exact RunKernel proposal authorization."""

    authorized = validate_authorized_action(
        action,
        action_type=ACQUISITION_CAPABILITY_DECIDE_ACTION,
        stage=ACQUISITION_CAPABILITY_DECISION_STAGE,
        expected_observation_type=ACQUISITION_CAPABILITY_DECIDED_OBSERVATION,
    )
    state = _validated_control_state(acquisition_control_state, action=authorized)
    _require_action_binding(authorized, "proposal", proposal.to_dict())
    _validate_authority_snapshot(
        authority_snapshot,
        run_id=authorized.run_id,
        request_id=proposal.request_id,
    )
    _require_action_binding(authorized, "authority_snapshot", dict(authority_snapshot))
    _require_action_binding(
        authorized,
        "acquisition_control_state_digest",
        stable_json_digest(state),
    )
    proposal_type = (
        AcquisitionNeedProposalV2
        if isinstance(proposal, AcquisitionNeedProposalV2)
        else AcquisitionNeedProposalV1
    )
    canonical_proposal = proposal_type.from_dict(
        _mapping_bucket(state, "proposals_by_id").get(proposal.proposal_id, {})
    )
    _require_canonical_record(
        state,
        bucket="proposals_by_id",
        record_id=proposal.proposal_id,
        expected=canonical_proposal.to_dict(),
        code="capability_decision_proposal_not_canonical",
    )
    if canonical_proposal.to_dict() != proposal.to_dict():
        raise AcquisitionControlError("capability_decision_proposal_mismatch")
    decision = derive_acquisition_capability_decision(
        proposal=proposal,
        authority_snapshot=authority_snapshot,
        acquisition_control_state=state,
    )
    return AcquisitionCapabilityDecisionRuntimeResult(
        decision=decision,
        observation=_observation(authorized, {"capability_decision": decision.to_dict()}),
    )


def execute_acquisition_work_order_admission_action(
    action: AuthorizedAction,
    *,
    proposal: AcquisitionNeedProposalV1 | AcquisitionNeedProposalV2,
    decision: AcquisitionCapabilityDecisionObservationV1,
    acquisition_control_state: Mapping[str, Any],
) -> AcquisitionWorkOrderAdmissionRuntimeResult:
    """Construct one provider-neutral order from an accepted decision."""

    authorized = validate_authorized_action(
        action,
        action_type=ACQUISITION_WORK_ORDER_ADMIT_ACTION,
        stage=ACQUISITION_WORK_ORDER_STAGE,
        expected_observation_type=ACQUISITION_WORK_ORDER_ADMITTED_OBSERVATION,
    )
    state = _validated_control_state(acquisition_control_state, action=authorized)
    _require_action_binding(authorized, "proposal_ref", proposal.ref())
    _require_action_binding(authorized, "capability_decision_ref", decision.ref())
    _require_canonical_record(
        state,
        bucket="proposals_by_id",
        record_id=proposal.proposal_id,
        expected=proposal.to_dict(),
        code="work_order_proposal_not_canonical",
    )
    _require_canonical_record(
        state,
        bucket="capability_decisions_by_id",
        record_id=decision.decision_id,
        expected=decision.to_dict(),
        code="work_order_decision_not_canonical",
    )
    work_order = build_acquisition_work_order(
        proposal=proposal,
        decision=decision,
        runkernel_authorization_ref=_action_ref(authorized),
    )
    return AcquisitionWorkOrderAdmissionRuntimeResult(
        work_order=work_order,
        observation=_observation(authorized, {"work_order": work_order.to_dict()}),
    )


def execute_acquisition_route_action(
    action: AuthorizedAction,
    *,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2,
    available_providers: Mapping[str, object] | None,
    acquisition_control_state: Mapping[str, Any],
) -> AcquisitionRouteRuntimeResult:
    """Complete provider selection solely through ``core.routing``."""

    authorized = validate_authorized_action(
        action,
        action_type=ACQUISITION_ROUTE_ACTION,
        stage=ACQUISITION_ROUTE_STAGE,
        expected_observation_type=ACQUISITION_ROUTE_OBSERVED_OBSERVATION,
    )
    state = _validated_control_state(acquisition_control_state, action=authorized)
    _require_action_binding(authorized, "work_order_ref", work_order.ref())
    current_policy_ref = acquisition_routing_policy_ref()
    if dict(work_order.routing_policy_ref) != current_policy_ref:
        raise AcquisitionControlError("stale_acquisition_routing_policy")
    _require_action_binding(authorized, "routing_policy_ref", current_policy_ref)
    availability_snapshot = ProviderAvailability.from_boolean_mapping(
        available_providers
    ).to_mapping()
    _require_action_binding(authorized, "availability_snapshot", availability_snapshot)
    availability_ref = build_provider_availability_snapshot_ref(
        availability_snapshot,
        work_order_ref=work_order.ref(),
    )
    _require_action_binding(authorized, "availability_snapshot_ref", availability_ref)
    _require_canonical_record(
        state,
        bucket="work_orders_by_id",
        record_id=work_order.work_order_id,
        expected=work_order.to_dict(),
        code="route_work_order_not_canonical",
    )
    _require_active_work_order(state, work_order)
    navigation_origin = isinstance(work_order, AcquisitionWorkOrderV2)
    include_domains = (
        (
            str(
                work_order.navigation_destination_binding_ref.get(
                    "normalized_hostname"
                )
                or ""
            ),
        )
        if navigation_origin
        else tuple(work_order.include_domains)
    )
    request = ProviderCapabilityRequest(
        capability=_authorized_capability(work_order.authorized_capability),
        domain_constraints=include_domains,
        include_domains=include_domains,
        exclude_domains=(
            () if navigation_origin else tuple(work_order.exclude_domains)
        ),
        derivation_reason=(
            "runkernel_authorized_navigation_candidate_work_order"
            if navigation_origin
            else "runkernel_authorized_post_discovery_work_order"
        ),
    )
    route_decision = route_provider_capability(
        request,
        availability_snapshot,
    )
    route_observation = AcquisitionRouteObservationV1.create(
        work_order_ref=work_order.ref(),
        route_decision_trace=route_decision.to_trace(),
        routing_policy_ref=current_policy_ref,
        availability_snapshot_ref=availability_ref,
    )
    return AcquisitionRouteRuntimeResult(
        route_decision=route_decision,
        route_observation=route_observation,
        availability_snapshot_ref=availability_ref,
        observation=_observation(authorized, {"route_observation": route_observation.to_dict()}),
    )


def execute_authorized_acquisition_work_order(
    action: AuthorizedAction,
    *,
    run_kernel: RunKernel,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2,
    route_observation: AcquisitionRouteObservationV1,
    route_decision: ProviderRouteDecision,
    transports: AcquisitionTransports | None = None,
    before_transport: Callable[[], None] | None = None,
    navigation_execution_overlay: SearchOSNavigationExecutionOverlayV1
    | None = None,
) -> AuthorizedAcquisitionExecutionRuntimeResult:
    """Guard and dispatch exactly one current, selected acquisition order."""

    authorized = validate_authorized_action(
        action,
        action_type=ACQUISITION_EXECUTE_ACTION,
        stage=ACQUISITION_EXECUTION_STAGE,
        expected_observation_type=ACQUISITION_EXECUTION_OBSERVED_OBSERVATION,
    )
    state = _validated_execution_kernel_state(
        run_kernel=run_kernel,
        action=authorized,
    )
    authority_snapshot = run_kernel.acquisition_authority_snapshot()
    _require_action_binding(authorized, "work_order_ref", work_order.ref())
    _require_action_binding(authorized, "route_observation_ref", route_observation.ref())
    _require_action_binding(authorized, "execution_authorization_ref", _action_ref(authorized))
    snapshot_digest = _validate_authority_snapshot(
        authority_snapshot,
        run_id=authorized.run_id,
        request_id=str(state.get("request_id") or ""),
    )
    _require_action_binding(
        authorized, "authority_snapshot_digest", snapshot_digest
    )
    _require_action_binding(
        authorized, "answer_contract_ref", dict(work_order.answer_contract_ref)
    )
    _require_action_binding(
        authorized, "component_ref", dict(work_order.component_ref)
    )
    _require_action_binding(
        authorized,
        "source_obligation_ref",
        dict(work_order.source_obligation_ref),
    )
    _require_current_work_order_lineage(
        work_order=work_order,
        authority_snapshot=authority_snapshot,
    )
    _guard_execution_state(
        state=state,
        action=authorized,
        work_order=work_order,
        route_observation=route_observation,
        route_decision=route_decision,
    )
    navigation_overlay_ref: Mapping[str, Any] = {}
    if isinstance(work_order, AcquisitionWorkOrderV2):
        if not isinstance(
            navigation_execution_overlay,
            SearchOSNavigationExecutionOverlayV1,
        ):
            raise AcquisitionControlError(
                "navigation_execution_overlay_unavailable"
            )
        navigation_overlay_ref = navigation_execution_overlay.ref()
        _require_action_binding(
            authorized,
            "navigation_execution_overlay_ref",
            navigation_overlay_ref,
        )
        if (
            navigation_execution_overlay.run_id != authorized.run_id
            or navigation_execution_overlay.request_id != work_order.request_id
        ):
            raise AcquisitionControlError(
                "navigation_execution_overlay_scope_mismatch"
            )
        try:
            navigation_execution_overlay.validate_lineage(
                work_order_ref=work_order.ref(),
                route_observation_ref=route_observation.ref(),
                navigation_edge_ref=work_order.navigation_edge_ref,
                navigation_selection_ref=work_order.navigation_selection_ref,
                destination_binding_ref=(
                    work_order.navigation_destination_binding_ref
                ),
            )
        except SearchOSNavigationError as exc:
            raise AcquisitionControlError(exc.code) from exc
        request = _materialize_navigation_acquisition_request(
            work_order,
            route_decision,
            navigation_execution_overlay,
        )
    else:
        if navigation_execution_overlay is not None:
            raise AcquisitionControlError(
                "discovery_execution_overlay_not_allowed"
            )
        request = _materialize_acquisition_request(work_order, route_decision)
    deferred_error: RunCapExceeded | None = None
    execution_result: AcquisitionExecutionResult | None = None
    transport_claimed = False
    navigation_response_validation: Mapping[str, Any] | None = None

    def claim_execution_authorization() -> None:
        nonlocal transport_claimed
        try:
            run_kernel.claim_acquisition_execution(
                action=authorized,
                work_order_ref=work_order.ref(),
                route_observation_ref=route_observation.ref(),
            )
        except RunKernelTransitionError as exc:
            raise AcquisitionControlError(str(exc)) from exc
        transport_claimed = True

    def claim_immediately_before_transport() -> None:
        if before_transport is not None:
            try:
                before_transport()
            except Exception:
                claim_execution_authorization()
                raise
        claim_execution_authorization()
        if navigation_execution_overlay is not None:
            try:
                navigation_execution_overlay.consume(
                    execution_action_ref=_action_ref(authorized)
                )
            except SearchOSNavigationError as exc:
                raise AcquisitionControlError(exc.code) from exc

    try:
        try:
            execution_result = dispatch_acquisition(
                request,
                transports=transports,
                before_transport=claim_immediately_before_transport,
            )
        except RunCapExceeded as exc:
            deferred_error = exc
            execution_result = AcquisitionExecutionResult(
                request=request,
                status=AcquisitionExecutionStatus.BLOCKED,
                provider_calls_attempted=0,
                provider_calls_completed=0,
                block_code="run_cap_exceeded",
                detail=None,
                transport_posture="blocked_before_transport_by_run_cap",
            )
        if not transport_claimed:
            claim_execution_authorization()
        if (
            isinstance(work_order, AcquisitionWorkOrderV2)
            and execution_result.succeeded
        ):
            if len(execution_result.artifacts) != 1:
                raise AcquisitionControlError(
                    "navigation_read_artifact_cardinality_invalid"
                )
            artifact = execution_result.artifacts[0]
            try:
                navigation_response_validation = (
                    validate_navigation_execution_artifact(
                        overlay=navigation_execution_overlay,
                        attempted_url=artifact.attempted_url,
                        requested_url=artifact.requested_url,
                        final_url=artifact.final_url,
                        resolved_url=artifact.resolved_url,
                        canonical_url=artifact.canonical_url,
                        provider_reported_url=artifact.provider_reported_url,
                        retained_digest=artifact.retained_digest,
                        retained_character_count=(
                            artifact.retained_character_count
                        ),
                    )
                )
            except SearchOSNavigationError as exc:
                execution_result = AcquisitionExecutionResult(
                    request=request,
                    status=AcquisitionExecutionStatus.FAILED,
                    artifacts=(),
                    provider_calls_attempted=(
                        execution_result.provider_calls_attempted
                    ),
                    provider_calls_completed=(
                        execution_result.provider_calls_completed
                    ),
                    failure_code=exc.code,
                    detail=None,
                    transport_posture="navigation_response_policy_blocked",
                )
        artifact_refs = tuple(
            (
                _navigation_artifact_ref(
                    artifact,
                    work_order=work_order,
                    response_validation=navigation_response_validation,
                )
                if isinstance(work_order, AcquisitionWorkOrderV2)
                else _artifact_ref(artifact)
            )
            for artifact in execution_result.artifacts
        )
        execution_projection = _execution_result_projection(
            execution_result,
            artifact_refs=artifact_refs,
        )
        if isinstance(work_order, AcquisitionWorkOrderV2):
            execution_observation = AcquisitionExecutionObservationV2.create(
                work_order=work_order,
                completed_route_ref=route_observation.ref(),
                execution_action_ref=_action_ref(authorized),
                navigation_execution_overlay_ref=navigation_overlay_ref,
                execution_result_trace=execution_projection,
                artifact_refs=artifact_refs,
                provider_calls_attempted=(
                    execution_result.provider_calls_attempted
                ),
                provider_calls_completed=(
                    execution_result.provider_calls_completed
                ),
                terminal_status=_terminal_status(execution_result),
                failure_or_block_code=(
                    execution_result.failure_code
                    or execution_result.block_code
                ),
            )
        else:
            execution_observation = AcquisitionExecutionObservationV1.create(
                work_order_ref=work_order.ref(),
                completed_route_ref=route_observation.ref(),
                execution_result_trace=execution_projection,
                artifact_refs=artifact_refs,
                provider_calls_attempted=(
                    execution_result.provider_calls_attempted
                ),
                provider_calls_completed=(
                    execution_result.provider_calls_completed
                ),
                terminal_status=_terminal_status(execution_result),
                failure_or_block_code=(
                    execution_result.failure_code
                    or execution_result.block_code
                ),
            )
    except Exception:
        if not transport_claimed:
            raise
        attempted = (
            execution_result.provider_calls_attempted
            if execution_result is not None
            else 0
        )
        completed = (
            execution_result.provider_calls_completed
            if execution_result is not None
            else 0
        )
        execution_result = AcquisitionExecutionResult(
            request=request,
            status=AcquisitionExecutionStatus.FAILED,
            provider_calls_attempted=attempted,
            provider_calls_completed=completed,
            failure_code="guarded_execution_failed_closed",
            detail=None,
            transport_posture=(
                "claimed_execution_failed_closed_no_replay"
            ),
        )
        execution_projection = _execution_result_projection(
            execution_result,
            artifact_refs=(),
        )
        if isinstance(work_order, AcquisitionWorkOrderV2):
            execution_observation = AcquisitionExecutionObservationV2.create(
                work_order=work_order,
                completed_route_ref=route_observation.ref(),
                execution_action_ref=_action_ref(authorized),
                navigation_execution_overlay_ref=navigation_overlay_ref,
                execution_result_trace=execution_projection,
                artifact_refs=(),
                provider_calls_attempted=attempted,
                provider_calls_completed=completed,
                terminal_status="failed",
                failure_or_block_code="guarded_execution_failed_closed",
            )
        else:
            execution_observation = AcquisitionExecutionObservationV1.create(
                work_order_ref=work_order.ref(),
                completed_route_ref=route_observation.ref(),
                execution_result_trace=execution_projection,
                artifact_refs=(),
                provider_calls_attempted=attempted,
                provider_calls_completed=completed,
                terminal_status="failed",
                failure_or_block_code="guarded_execution_failed_closed",
            )
    if navigation_execution_overlay is not None:
        navigation_execution_overlay.expire()
    return AuthorizedAcquisitionExecutionRuntimeResult(
        execution_result=execution_result,
        execution_observation=execution_observation,
        observation=_observation(
            authorized,
            {"execution_observation": execution_observation.to_dict()},
        ),
        deferred_error=deferred_error,
        navigation_response_validation=navigation_response_validation,
    )


def execute_acquisition_terminal_reduction_action(
    action: AuthorizedAction,
    *,
    acquisition_control_state: Mapping[str, Any],
    proposal: AcquisitionNeedProposalV1 | AcquisitionNeedProposalV2 | None = None,
    decision: AcquisitionCapabilityDecisionObservationV1 | None = None,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2 | None = None,
    route_observation: AcquisitionRouteObservationV1 | None = None,
    execution_observation: (
        AcquisitionExecutionObservationV1
        | AcquisitionExecutionObservationV2
        | None
    ) = None,
    invalidation_code: str | None = None,
) -> AcquisitionTerminalReductionRuntimeResult:
    """Create one receipt for a blocked decision/route or terminal execution."""

    authorized = validate_authorized_action(
        action,
        action_type=ACQUISITION_TERMINAL_REDUCE_ACTION,
        stage=ACQUISITION_TERMINAL_REDUCTION_STAGE,
        expected_observation_type=ACQUISITION_TERMINAL_REDUCED_OBSERVATION,
    )
    state = _validated_control_state(acquisition_control_state, action=authorized)
    terminal_receipt: AcquisitionTerminalReceiptV1 | None
    if execution_observation is not None:
        if work_order is None or route_observation is None:
            raise AcquisitionControlError("execution_terminal_lineage_missing")
        _require_action_binding(authorized, "terminal_source_ref", execution_observation.ref())
        _require_action_binding(authorized, "terminal_source_kind", "execution")
        _require_terminal_execution_lineage(
            state,
            work_order=work_order,
            route_observation=route_observation,
            execution_observation=execution_observation,
        )
        terminal_receipt = build_terminal_receipt_from_execution(
            work_order=work_order,
            route=route_observation,
            execution=execution_observation,
        )
    elif route_observation is not None:
        if work_order is None:
            raise AcquisitionControlError("route_terminal_work_order_missing")
        _require_action_binding(authorized, "terminal_source_ref", route_observation.ref())
        _require_action_binding(authorized, "terminal_source_kind", "route")
        _require_terminal_route_lineage(
            state,
            work_order=work_order,
            route_observation=route_observation,
        )
        terminal_receipt = build_terminal_receipt_from_route(
            work_order=work_order,
            route=route_observation,
        )
    elif work_order is not None:
        _require_action_binding(
            authorized, "terminal_source_ref", work_order.ref()
        )
        _require_action_binding(
            authorized,
            "terminal_source_kind",
            "work_order_invalidation",
        )
        _require_action_binding(
            authorized,
            "work_order_invalidation_code",
            invalidation_code,
        )
        _require_canonical_record(
            state,
            bucket="work_orders_by_id",
            record_id=work_order.work_order_id,
            expected=work_order.to_dict(),
            code="terminal_work_order_not_canonical",
        )
        _require_active_work_order(state, work_order)
        terminal_receipt = (
            build_terminal_receipt_from_work_order_invalidation(
                work_order=work_order,
                block_code=str(invalidation_code or ""),
            )
        )
    elif decision is not None and proposal is not None:
        _require_action_binding(authorized, "terminal_source_ref", decision.ref())
        _require_action_binding(authorized, "terminal_source_kind", "decision")
        _require_canonical_record(
            state,
            bucket="proposals_by_id",
            record_id=proposal.proposal_id,
            expected=proposal.to_dict(),
            code="terminal_proposal_not_canonical",
        )
        _require_canonical_record(
            state,
            bucket="capability_decisions_by_id",
            record_id=decision.decision_id,
            expected=decision.to_dict(),
            code="terminal_decision_not_canonical",
        )
        if decision.proposal_ref != proposal.ref():
            raise AcquisitionControlError("terminal_decision_proposal_mismatch")
        terminal_receipt = build_terminal_receipt_from_decision(
            proposal=proposal,
            decision=decision,
        )
        if terminal_receipt is None:
            raise AcquisitionControlError("decision_is_not_terminal")
    else:
        raise AcquisitionControlError("terminal_subject_missing")
    existing_receipts = _mapping_bucket(state, "terminal_receipts_by_operation_key")
    if terminal_receipt.operation_identity_key in existing_receipts:
        raise AcquisitionControlError("operation_already_terminal")
    return AcquisitionTerminalReductionRuntimeResult(
        terminal_receipt=terminal_receipt,
        observation=_observation(authorized, {"terminal_receipt": terminal_receipt.to_dict()}),
    )


def execute_acquisition_custody_authorization_action(
    action: AuthorizedAction,
    *,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2,
    route_observation: AcquisitionRouteObservationV1,
    terminal_receipt: AcquisitionTerminalReceiptV1,
    custody_consumer: str,
    acquisition_control_state: Mapping[str, Any],
) -> AcquisitionCustodyAuthorizationRuntimeResult:
    """Authorize custody consumption only for successful current READ material."""

    authorized = validate_authorized_action(
        action,
        action_type=ACQUISITION_CUSTODY_CONSUME_ACTION,
        stage=ACQUISITION_CUSTODY_STAGE,
        expected_observation_type=ACQUISITION_CUSTODY_AUTHORIZED_OBSERVATION,
    )
    state = _validated_control_state(acquisition_control_state, action=authorized)
    _require_action_binding(authorized, "work_order_ref", work_order.ref())
    _require_action_binding(authorized, "route_observation_ref", route_observation.ref())
    _require_action_binding(authorized, "terminal_receipt_ref", terminal_receipt.ref())
    _require_action_binding(authorized, "custody_consumer", custody_consumer)
    _require_canonical_record(
        state,
        bucket="work_orders_by_id",
        record_id=work_order.work_order_id,
        expected=work_order.to_dict(),
        code="custody_work_order_not_canonical",
    )
    _require_canonical_record(
        state,
        bucket="routes_by_id",
        record_id=route_observation.route_observation_id,
        expected=route_observation.to_dict(),
        code="custody_route_not_canonical",
    )
    receipts = _mapping_bucket(state, "terminal_receipts_by_operation_key")
    if receipts.get(work_order.operation_identity_key) != terminal_receipt.to_dict():
        raise AcquisitionControlError("custody_terminal_receipt_not_canonical")
    if terminal_receipt.work_order_ref != work_order.ref():
        raise AcquisitionControlError("custody_receipt_work_order_mismatch")
    if terminal_receipt.route_observation_ref != route_observation.ref():
        raise AcquisitionControlError("custody_receipt_route_mismatch")
    if terminal_receipt.terminal_status != "completed":
        raise AcquisitionControlError("custody_requires_successful_execution")
    if work_order.authorized_capability != AcquisitionCapability.READ.value:
        raise AcquisitionControlError("custody_capability_not_installed")
    prior = _mapping_bucket(state, "custody_authorizations_by_receipt")
    if terminal_receipt.receipt_id in prior:
        raise AcquisitionControlError("custody_already_authorized")
    custody_authorization = AcquisitionCustodyAuthorizationV1.create(
        work_order_ref=work_order.ref(),
        route_observation_ref=route_observation.ref(),
        terminal_receipt_ref=terminal_receipt.ref(),
        answer_contract_ref=work_order.answer_contract_ref,
        source_obligation_ref=work_order.source_obligation_ref,
        capability=work_order.authorized_capability,
        custody_consumer=custody_consumer,
    )
    return AcquisitionCustodyAuthorizationRuntimeResult(
        custody_authorization=custody_authorization,
        observation=_observation(
            authorized,
            {"custody_authorization": custody_authorization.to_dict()},
        ),
    )


def _guard_execution_state(
    *,
    state: Mapping[str, Any],
    action: AuthorizedAction,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2,
    route_observation: AcquisitionRouteObservationV1,
    route_decision: ProviderRouteDecision,
) -> None:
    _require_canonical_record(
        state,
        bucket="work_orders_by_id",
        record_id=work_order.work_order_id,
        expected=work_order.to_dict(),
        code="execution_work_order_not_canonical",
    )
    _require_canonical_record(
        state,
        bucket="routes_by_id",
        record_id=route_observation.route_observation_id,
        expected=route_observation.to_dict(),
        code="execution_route_not_canonical",
    )
    if route_observation.terminal_status != "selected" or route_decision.blocked:
        raise AcquisitionControlError("execution_route_not_selected")
    current_policy_ref = acquisition_routing_policy_ref()
    if (
        dict(work_order.routing_policy_ref) != current_policy_ref
        or dict(route_observation.routing_policy_ref) != current_policy_ref
    ):
        raise AcquisitionControlError("stale_acquisition_routing_policy")
    availability_ref = build_provider_availability_snapshot_ref(
        route_decision.availability.to_mapping(),
        work_order_ref=work_order.ref(),
    )
    if dict(route_observation.availability_snapshot_ref) != availability_ref:
        raise AcquisitionControlError("route_availability_snapshot_mismatch")
    expected_route = AcquisitionRouteObservationV1.create(
        work_order_ref=work_order.ref(),
        route_decision_trace=route_decision.to_trace(),
        routing_policy_ref=current_policy_ref,
        availability_snapshot_ref=availability_ref,
    )
    if expected_route.to_dict() != route_observation.to_dict():
        raise AcquisitionControlError("route_decision_observation_mismatch")
    if route_decision.capability.value != work_order.authorized_capability:
        raise AcquisitionControlError("route_capability_mismatch")
    _require_active_work_order(state, work_order)
    receipts = _mapping_bucket(state, "terminal_receipts_by_operation_key")
    if work_order.operation_identity_key in receipts:
        raise AcquisitionControlError("operation_already_terminal")
    authorizations = _mapping_bucket(state, "execution_authorizations_by_id")
    authorization = authorizations.get(action.action_id)
    if not isinstance(authorization, Mapping):
        raise AcquisitionControlError("execution_authorization_not_canonical")
    for key, expected in _action_ref(action).items():
        if authorization.get(key) != expected:
            raise AcquisitionControlError("execution_authorization_action_mismatch")
    if authorization.get("work_order_ref") != work_order.ref():
        raise AcquisitionControlError("execution_authorization_work_order_mismatch")
    if authorization.get("route_observation_ref") != route_observation.ref():
        raise AcquisitionControlError("execution_authorization_route_mismatch")
    if (
        authorization.get("claim_status") != "authorized"
        or authorization.get("transport_claimed") is not False
    ):
        raise AcquisitionControlError("execution_authorization_already_claimed")


def _require_current_work_order_lineage(
    *,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2,
    authority_snapshot: Mapping[str, Any],
) -> None:
    contract_ref = authority_snapshot.get("answer_contract_ref")
    components = authority_snapshot.get("components_by_id")
    obligations = authority_snapshot.get("source_obligations_by_id")
    if not isinstance(contract_ref, Mapping):
        raise AcquisitionControlError("authority_snapshot_contract_ref_missing")
    if not isinstance(components, Mapping) or not isinstance(obligations, Mapping):
        raise AcquisitionControlError("authority_snapshot_lineage_missing")
    component_id = work_order.component_ref.get("component_id")
    obligation_id = work_order.source_obligation_ref.get("source_obligation_id")
    if dict(contract_ref) != dict(work_order.answer_contract_ref):
        raise AcquisitionControlError("stale_answer_contract")
    if components.get(component_id) != dict(work_order.component_ref):
        raise AcquisitionControlError("stale_component_revision")
    if obligations.get(obligation_id) != dict(work_order.source_obligation_ref):
        raise AcquisitionControlError("mismatched_source_obligation")


def _require_terminal_execution_lineage(
    state: Mapping[str, Any],
    *,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2,
    route_observation: AcquisitionRouteObservationV1,
    execution_observation: (
        AcquisitionExecutionObservationV1 | AcquisitionExecutionObservationV2
    ),
) -> None:
    _require_terminal_route_lineage(
        state,
        work_order=work_order,
        route_observation=route_observation,
        require_blocked=False,
    )
    _require_canonical_record(
        state,
        bucket="execution_observations_by_id",
        record_id=execution_observation.execution_observation_id,
        expected=execution_observation.to_dict(),
        code="terminal_execution_not_canonical",
    )
    if execution_observation.work_order_ref != work_order.ref():
        raise AcquisitionControlError("terminal_execution_work_order_mismatch")
    if execution_observation.completed_route_ref != route_observation.ref():
        raise AcquisitionControlError("terminal_execution_route_mismatch")


def _require_terminal_route_lineage(
    state: Mapping[str, Any],
    *,
    work_order: AcquisitionWorkOrderV1 | AcquisitionWorkOrderV2,
    route_observation: AcquisitionRouteObservationV1,
    require_blocked: bool = True,
) -> None:
    _require_canonical_record(
        state,
        bucket="work_orders_by_id",
        record_id=work_order.work_order_id,
        expected=work_order.to_dict(),
        code="terminal_work_order_not_canonical",
    )
    _require_canonical_record(
        state,
        bucket="routes_by_id",
        record_id=route_observation.route_observation_id,
        expected=route_observation.to_dict(),
        code="terminal_route_not_canonical",
    )
    if route_observation.work_order_ref != work_order.ref():
        raise AcquisitionControlError("terminal_route_work_order_mismatch")
    if require_blocked and route_observation.terminal_status != "blocked":
        raise AcquisitionControlError("selected_route_is_not_terminal")
    _require_active_work_order(state, work_order)


def _materialize_acquisition_request(
    work_order: AcquisitionWorkOrderV1,
    route_decision: ProviderRouteDecision,
) -> AcquisitionRequest:
    bounds = dict(work_order.hard_operation_bounds)
    parent_id = _first_parent_id(work_order.parent_acquisition_job_refs)
    candidate_id = work_order.candidate_ref.get("candidate_id")
    obligation_id = work_order.source_obligation_ref.get("source_obligation_id")
    return AcquisitionRequest(
        acquisition_job_id=work_order.work_order_id,
        route_decision=route_decision,
        parent_acquisition_job_id=parent_id,
        acquisition_lineage_id=str(work_order.source_obligation_ref.get("source_obligation_digest") or ""),
        selected_urls=tuple(work_order.selected_urls),
        root_url=work_order.root_url,
        render_javascript=False,
        focus_text=(
            str(work_order.bounded_focus.get("focus_text")) if work_order.bounded_focus.get("focus_text") else None
        ),
        include_domains=tuple(work_order.include_domains),
        exclude_domains=tuple(work_order.exclude_domains),
        include_path_prefix=work_order.include_path_prefix,
        exclude_path_prefixes=tuple(work_order.exclude_path_prefixes),
        max_results=int(bounds.get("max_results", 5)),
        max_pages=int(bounds.get("max_pages", 0)),
        max_depth=int(bounds.get("max_depth", 0)),
        max_retained_characters=int(
            bounds.get(
                "max_retained_characters",
                READ_RETAINED_CHARACTER_CEILING,
            )
        ),
        max_aggregate_retained_characters=int(
            bounds.get(
                "max_aggregate_retained_characters",
                CRAWL_AGGREGATE_RETAINED_CHARACTER_CEILING,
            )
        ),
        crawl_job_ordinal=1,
        candidate_reference=str(candidate_id) if candidate_id else None,
        obligation_reference=str(obligation_id) if obligation_id else None,
    )


def _materialize_navigation_acquisition_request(
    work_order: AcquisitionWorkOrderV2,
    route_decision: ProviderRouteDecision,
    overlay: SearchOSNavigationExecutionOverlayV1,
) -> AcquisitionRequest:
    """Materialize an exact URL only for the already-validated adapter call."""

    if route_decision.capability is not AcquisitionCapability.READ:
        raise AcquisitionControlError("navigation_route_capability_mismatch")
    bounds = dict(work_order.hard_operation_bounds)
    hostname = str(
        work_order.navigation_destination_binding_ref.get("normalized_hostname")
        or ""
    )
    if not hostname:
        raise AcquisitionControlError(
            "navigation_destination_binding_hostname_missing"
        )
    return AcquisitionRequest(
        acquisition_job_id=work_order.work_order_id,
        route_decision=route_decision,
        parent_acquisition_job_id=None,
        acquisition_lineage_id=work_order.source_obligation_ref.get(
            "source_obligation_digest"
        ),
        selected_urls=(overlay.exact_execution_url,),
        root_url=None,
        render_javascript=False,
        focus_text=None,
        include_domains=(hostname,),
        exclude_domains=(),
        include_path_prefix=None,
        exclude_path_prefixes=(),
        max_results=1,
        max_pages=0,
        max_depth=0,
        max_retained_characters=int(
            bounds.get(
                "max_retained_characters",
                READ_RETAINED_CHARACTER_CEILING,
            )
        ),
        max_aggregate_retained_characters=(
            CRAWL_AGGREGATE_RETAINED_CHARACTER_CEILING
        ),
        crawl_job_ordinal=1,
        candidate_reference=str(
            work_order.navigation_destination_binding_ref.get(
                "destination_binding_id"
            )
            or ""
        ),
        obligation_reference=str(
            work_order.source_obligation_ref.get("source_obligation_id") or ""
        ),
    )


def _artifact_ref(artifact: AcquisitionArtifact) -> dict[str, Any]:
    core = {
        "kind": artifact.kind.value,
        "acquisition_job_id": artifact.acquisition_job_id,
        "provider": artifact.provider,
        "operation": artifact.operation,
        "provider_variant": artifact.provider_variant,
        "output_type": artifact.output_type,
        "status": artifact.status,
        "requested_url": artifact.requested_url,
        "final_url": artifact.final_url,
        "canonical_url": artifact.canonical_url,
        "root_url": artifact.root_url,
        "retained_digest": artifact.retained_digest,
        "retained_character_count": artifact.retained_character_count,
        "url_count": len(artifact.urls),
        "page_count": len(artifact.pages),
        "failure_code": artifact.failure_code,
        "authority_posture": artifact.authority_posture,
    }
    compact_core = {
        key: value for key, value in core.items() if value not in (None, "")
    }
    digest = stable_json_digest(compact_core)
    return {
        "artifact_id": (f"acquisition-artifact:{artifact.acquisition_job_id}:{digest[:20]}"),
        "artifact_digest": digest,
        **compact_core,
        "retained_text_included": False,
        "raw_provider_payload_included": False,
    }


def _navigation_artifact_ref(
    artifact: AcquisitionArtifact,
    *,
    work_order: AcquisitionWorkOrderV2,
    response_validation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Project navigation acquisition material without any exact locator."""

    validation = dict(response_validation or {})
    core = {
        "kind": artifact.kind.value,
        "acquisition_job_id": artifact.acquisition_job_id,
        "provider": artifact.provider,
        "operation": artifact.operation,
        "provider_variant": artifact.provider_variant,
        "output_type": artifact.output_type,
        "status": artifact.status,
        "physical_acquisition_origin": "navigation_candidate",
        "navigation_destination_binding_ref": (
            work_order.navigation_destination_binding_ref
        ),
        "navigation_edge_ref": work_order.navigation_edge_ref,
        "navigation_selection_ref": work_order.navigation_selection_ref,
        "physical_identity_digest": work_order.physical_identity_digest,
        "full_destination_digest": work_order.full_destination_digest,
        "retained_digest": artifact.retained_digest,
        "retained_character_count": artifact.retained_character_count,
        "response_validation_ref": (
            {
                "navigation_response_validation_id": validation.get(
                    "navigation_response_validation_id"
                ),
                "navigation_response_validation_digest": validation.get(
                    "navigation_response_validation_digest"
                ),
            }
            if validation
            else {}
        ),
        "secondary_url_postures": validation.get(
            "secondary_url_postures", {}
        ),
        "failure_code": artifact.failure_code,
        "authority_posture": artifact.authority_posture,
    }
    compact = {
        key: value for key, value in core.items() if value not in (None, "", {})
    }
    digest = stable_json_digest(compact)
    return {
        "artifact_id": (
            f"acquisition-artifact-navigation:"
            f"{artifact.acquisition_job_id}:{digest[:20]}"
        ),
        "artifact_digest": digest,
        **compact,
        "retained_text_included": False,
        "raw_provider_payload_included": False,
        "exact_locator_included": False,
    }


def _execution_result_projection(
    execution_result: AcquisitionExecutionResult,
    *,
    artifact_refs: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    return {
        "acquisition_job_id": execution_result.request.acquisition_job_id,
        "capability": execution_result.request.capability.value,
        "status": execution_result.status.value,
        "artifact_refs": [dict(item) for item in artifact_refs],
        "provider_calls_attempted": execution_result.provider_calls_attempted,
        "provider_calls_completed": execution_result.provider_calls_completed,
        "block_code": execution_result.block_code,
        "failure_code": execution_result.failure_code,
        "transport_posture": execution_result.transport_posture,
        "retained_text_included": False,
        "raw_provider_payload_included": False,
        "provider_failure_fallback_attempted": False,
        "capability_switch_attempted": False,
    }


def _terminal_status(execution_result: AcquisitionExecutionResult) -> str:
    if execution_result.status is AcquisitionExecutionStatus.SUCCEEDED:
        return "completed"
    return execution_result.status.value


def _validated_control_state(value: Mapping[str, Any], *, action: AuthorizedAction) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AcquisitionControlError("acquisition_control_state_missing")
    request_id = str(value.get("request_id") or "")
    if not request_id:
        raise AcquisitionControlError("acquisition_control_request_id_missing")
    return ensure_acquisition_control_state(
        value,
        run_id=action.run_id,
        request_id=request_id,
    )


def _validated_execution_kernel_state(
    *, run_kernel: RunKernel, action: AuthorizedAction
) -> dict[str, Any]:
    if not isinstance(run_kernel, RunKernel):
        raise AcquisitionControlError("execution_run_kernel_missing")
    if run_kernel.state.run_id != action.run_id:
        raise AcquisitionControlError("execution_run_kernel_identity_mismatch")
    issued = run_kernel.state.issued_actions.get(action.action_id)
    if issued != action:
        raise AcquisitionControlError("execution_action_not_canonical")
    if action.action_id in run_kernel.state.reduced_action_ids:
        raise AcquisitionControlError("execution_action_already_reduced")
    if (
        run_kernel.state.action_statuses.get(action.action_id)
        is not RunStageStatus.AUTHORIZED
    ):
        raise AcquisitionControlError("execution_action_not_authorized")
    return _validated_control_state(
        run_kernel.state.acquisition_control_state,
        action=action,
    )


def _validate_authority_snapshot(value: Mapping[str, Any], *, run_id: str, request_id: str) -> str:
    if not isinstance(value, Mapping):
        raise AcquisitionControlError("authority_snapshot_missing")
    snapshot = dict(value)
    digest = str(snapshot.pop("snapshot_digest", ""))
    if not digest or stable_json_digest(snapshot) != digest:
        raise AcquisitionControlError("authority_snapshot_digest_mismatch")
    if snapshot.get("run_id") != run_id or snapshot.get("request_id") != request_id:
        raise AcquisitionControlError("authority_snapshot_identity_mismatch")
    return digest


def _require_action_binding(action: AuthorizedAction, key: str, expected: Any) -> None:
    if action.inputs.get(key) != expected:
        raise AcquisitionControlError(f"authorized_action_{key}_mismatch")


def _require_canonical_record(
    state: Mapping[str, Any],
    *,
    bucket: str,
    record_id: str,
    expected: Mapping[str, Any],
    code: str,
) -> None:
    records = _mapping_bucket(state, bucket)
    if records.get(record_id) != dict(expected):
        raise AcquisitionControlError(code)


def _require_active_work_order(state: Mapping[str, Any], work_order: AcquisitionWorkOrderV1) -> None:
    obligation_id = str(work_order.source_obligation_ref.get("source_obligation_id") or "")
    active = _mapping_bucket(state, "active_by_source_obligation").get(obligation_id)
    if not isinstance(active, Mapping):
        raise AcquisitionControlError("active_acquisition_slot_missing")
    active_ref = active.get("work_order_ref")
    if active_ref is None:
        active_ref = {
            "work_order_id": active.get("work_order_id"),
            "work_order_digest": active.get("work_order_digest"),
        }
    if active_ref != work_order.ref():
        raise AcquisitionControlError("active_acquisition_slot_mismatch")
    if active.get("operation_identity_key") not in (
        None,
        work_order.operation_identity_key,
    ):
        raise AcquisitionControlError("active_operation_identity_mismatch")


def _mapping_bucket(state: Mapping[str, Any], bucket: str) -> Mapping[str, Any]:
    value = state.get(bucket)
    if not isinstance(value, Mapping):
        raise AcquisitionControlError(f"acquisition_control_{bucket}_invalid")
    return value


def _authorized_capability(value: str) -> AcquisitionCapability:
    try:
        capability = AcquisitionCapability(value)
    except ValueError as exc:
        raise AcquisitionControlError("work_order_capability_not_routable") from exc
    if capability in {
        AcquisitionCapability.DISCOVER,
        AcquisitionCapability.PROVIDER_SYNTHESIS,
    }:
        raise AcquisitionControlError("work_order_capability_not_routable")
    return capability


def _first_parent_id(refs: tuple[Mapping[str, Any], ...]) -> str | None:
    for ref in refs:
        for key in (
            "acquisition_job_id",
            "packet_id",
            "receipt_id",
            "work_order_id",
        ):
            value = ref.get(key)
            if value:
                return str(value)
    return None


def _action_ref(action: AuthorizedAction) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "action_type": action.action_type.value,
        "stage": action.stage,
        "sequence": action.sequence,
    }


def _observation(action: AuthorizedAction, payload: Mapping[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type=action.expected_observation_type,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )


__all__ = [
    "ACQUISITION_CAPABILITY_DECISION_STAGE",
    "ACQUISITION_CUSTODY_STAGE",
    "ACQUISITION_EXECUTION_STAGE",
    "ACQUISITION_ROUTE_STAGE",
    "ACQUISITION_TERMINAL_REDUCTION_STAGE",
    "ACQUISITION_WORK_ORDER_STAGE",
    "AcquisitionCapabilityDecisionRuntimeResult",
    "AcquisitionCustodyAuthorizationRuntimeResult",
    "AcquisitionRouteRuntimeResult",
    "AcquisitionTerminalReductionRuntimeResult",
    "AcquisitionWorkOrderAdmissionRuntimeResult",
    "AuthorizedAcquisitionExecutionRuntimeResult",
    "build_provider_availability_snapshot_ref",
    "execute_acquisition_capability_decision_action",
    "execute_acquisition_custody_authorization_action",
    "execute_acquisition_route_action",
    "execute_acquisition_terminal_reduction_action",
    "execute_acquisition_work_order_admission_action",
    "execute_authorized_acquisition_work_order",
]
