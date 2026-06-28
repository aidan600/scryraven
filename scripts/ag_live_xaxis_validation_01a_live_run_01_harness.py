from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.contract_amendment_record import (  # noqa: E402
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    WeakeningPosture,
)
from core.live_search_validation_invocation_runtime import (  # noqa: E402
    AG_LIVE_XAXIS_DEFAULT_JOB_ID,
    LiveSearchValidationCaps,
    LiveSearchValidationInvocationError,
    build_broker_request_envelope,
    build_live_search_validation_request_packet,
    dumps_packet,
    execution_facts_for_mode,
    reduce_provider_results_through_run_kernel,
    validate_request_packet,
    validate_safe_output_packet_path,
)
from core.live_search_validation_runtime import (  # noqa: E402
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
)
from core.run_kernel import (  # noqa: E402
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_executor_handoff_runtime import (  # noqa: E402
    SearchExecutorHandoffInput,
    execute_search_executor_handoff_action,
    planner_ref_from_search_planner_state,
)
from core.search_executor_handoff_runtime import (
    contract_ref_from_contract as handoff_contract_ref_from_contract,
)
from core.search_planner_runtime import (  # noqa: E402
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as planner_contract_ref_from_contract,
)

PHASE = "AG-LIVE-XAXIS-VALIDATION-01A-LIVE-RUN-01"
PROOF_CLASS = "offline_live_run_request_packet_generator"
DEFAULT_QUERY = "current passport renewal fees official government site"
DEFAULT_PROVIDER = "serper"
DEFAULT_RUN_ID = "run:ag-live-xaxis-validation-01a-live-run-01-harness"
DEFAULT_REQUEST_ID = "request:ag-live-xaxis-validation-01a-live-run-01-harness"
DEFAULT_REQUEST_OUTPUT = (
    "output/ag_live_xaxis_validation_01a_live_run_01_request.json"
)
DEFAULT_BROKER_OUTPUT = (
    "output/ag_live_xaxis_validation_01a_live_run_01_broker_envelope.json"
)
DEFAULT_OUTPUT_PACKET = (
    "output/ag_live_xaxis_validation_01a_live_run_01_output_packet.json"
)

COMPONENT_ID = "component:official-current-public-fact"
SOURCE_OBLIGATION_ID = "obligation:official-current-public-source"
SEARCH_REQUIREMENT_ID = "searchreq:official-current-public-fact"


class HarnessError(ValueError):
    """Raised when the LIVE-RUN-01 harness must fail closed."""


class DeterministicHarnessPlannerAdapter:
    """Local deterministic planner adapter; never calls a model or provider."""

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return _planner_adapter_result(planner_input)


def build_front_half_kernel(*, provider_hint: str = DEFAULT_PROVIDER) -> RunKernel:
    """Build repo-visible current_answer_contract + SearchExecutorHandoff state."""

    kernel = RunKernel.start(
        run_id=DEFAULT_RUN_ID,
        request_id=DEFAULT_REQUEST_ID,
        request={
            "phase": PHASE,
            "proof_class": PROOF_CLASS,
            "query_class": "single-component official-current public-information lookup",
            "query_text_retained": False,
        },
    )
    _reduce_deterministic_planner(kernel)
    _accept_initial_contract(kernel)
    _apply_current_contract_caveat(kernel)
    _reduce_search_executor_handoff(kernel, provider_hint=provider_hint)
    return kernel


def prepare_request_packet(
    *,
    output_path: str | Path,
    provider_authorized: str = DEFAULT_PROVIDER,
) -> dict[str, Any]:
    kernel = build_front_half_kernel(provider_hint=DEFAULT_PROVIDER)
    selected_task_id = _single_selected_task_id(kernel)
    packet = build_live_search_validation_request_packet(
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=kernel.state.search_executor_handoff_state,
        selected_search_task_ids=[selected_task_id],
        provider_authorized=provider_authorized,
        output_packet_path=output_path,
        root=ROOT,
        job_id=AG_LIVE_XAXIS_DEFAULT_JOB_ID,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        caps=LiveSearchValidationCaps(),
    )
    _write_packet(output_path, packet)
    return packet


def emit_broker_envelope(
    *,
    request_path: str | Path,
    output_path: str | Path,
    confirm_live_provider_call: bool,
) -> dict[str, Any]:
    if not confirm_live_provider_call:
        raise HarnessError(
            "broker envelope emission requires --confirm-live-provider-call"
        )
    request_packet = _load_request_packet(request_path)
    envelope = build_broker_request_envelope(
        request_packet,
        root=ROOT,
        confirm_live_provider_call=True,
    )
    _write_packet(output_path, envelope)
    return envelope


def reduce_sanitized_results(
    *,
    request_path: str | Path,
    provider_results_path: str | Path,
    output_path: str | Path,
    execution_mode: str = LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
) -> dict[str, Any]:
    request_packet = _load_request_packet(request_path)
    provider_results = _load_provider_results(provider_results_path)
    kernel = build_front_half_kernel(provider_hint=DEFAULT_PROVIDER)
    packet = reduce_provider_results_through_run_kernel(
        kernel=kernel,
        request_packet=request_packet,
        provider_results_by_task=provider_results,
        root=ROOT,
        **execution_facts_for_mode(execution_mode),
    )
    _write_packet(output_path, packet)
    return packet


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        mode_count = sum(
            bool(value)
            for value in (
                args.prepare_request,
                args.emit_broker_envelope,
                args.reduce_sanitized_results,
            )
        )
        if mode_count != 1:
            raise HarnessError("select exactly one harness operation")

        if args.prepare_request:
            output = args.output or DEFAULT_REQUEST_OUTPUT
            packet = prepare_request_packet(
                output_path=output,
                provider_authorized=args.provider_authorized,
            )
        elif args.emit_broker_envelope:
            if not args.request:
                raise HarnessError("--emit-broker-envelope requires --request")
            output = args.output or DEFAULT_BROKER_OUTPUT
            packet = emit_broker_envelope(
                request_path=args.request,
                output_path=output,
                confirm_live_provider_call=args.confirm_live_provider_call,
            )
        else:
            if not args.request or not args.provider_results:
                raise HarnessError(
                    "--reduce-sanitized-results requires --request and "
                    "--provider-results"
                )
            output = args.output or DEFAULT_OUTPUT_PACKET
            packet = reduce_sanitized_results(
                request_path=args.request,
                provider_results_path=args.provider_results,
                output_path=output,
                execution_mode=args.execution_mode,
            )
    except (
        HarnessError,
        LiveSearchValidationInvocationError,
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"refusing AG-LIVE-XAXIS LIVE-RUN-01 harness operation: {exc}", file=sys.stderr)
        return 2

    print(dumps_packet(packet), end="")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare inert AG-LIVE-XAXIS-VALIDATION-01A-LIVE-RUN-01 packets "
            "without provider, broker, network, fetch/read, evidence, "
            "citation, Sufficiency, FAP, or Author execution."
        )
    )
    operations = parser.add_argument_group("operation")
    operations.add_argument("--prepare-request", action="store_true")
    operations.add_argument("--emit-broker-envelope", action="store_true")
    operations.add_argument("--reduce-sanitized-results", action="store_true")
    parser.add_argument("--request", help="Sanitized request packet under output/.")
    parser.add_argument(
        "--provider-results",
        help="Sanitized provider result map under output/.",
    )
    parser.add_argument(
        "--output",
        help="Output packet path under output/.",
    )
    parser.add_argument(
        "--provider-authorized",
        default=DEFAULT_PROVIDER,
        help="Explicit allowlisted provider for request preparation.",
    )
    parser.add_argument(
        "--execution-mode",
        default=LIVE_SEARCH_VALIDATION_EXECUTION_MODE_DIRECT_LIVE,
        choices=("direct_live", "broker_live"),
        help="Execution facts to record when reducing supplied sanitized results.",
    )
    parser.add_argument(
        "--confirm-live-provider-call",
        action="store_true",
        help=(
            "Required only to emit the broker envelope; this harness still does "
            "not call the broker or provider."
        ),
    )
    return parser


def _reduce_deterministic_planner(kernel: RunKernel) -> None:
    planner_input = SearchPlannerInput(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        user_query_text=DEFAULT_QUERY,
        requested_mode="balanced",
        safe_context={
            "phase": PHASE,
            "front_half_source": "deterministic_repo_visible_harness_fixture",
            "source_policy": "official-current",
            "not_product_path": True,
        },
        route_context_ref={"route_ref": "ag-live-xaxis-live-run-01-harness"},
        run_context_ref={"run_ref": "ag-live-xaxis-live-run-01-harness"},
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )
    action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=DeterministicHarnessPlannerAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)


def _accept_initial_contract(kernel: RunKernel) -> None:
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=str(qmr["record_id"]),
        parent_proposal_digest=str(qmr["record_digest"]),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
        status=RunStageStatus.COMPLETED,
        payload={"question_meaning_record": dict(qmr)},
    )
    kernel.reduce(observation)


def _apply_current_contract_caveat(kernel: RunKernel) -> None:
    accepted = kernel.state.initial_answer_contract
    record = _current_contract_caveat_record(kernel, accepted)
    action = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload={"contract_amendment_record": record.to_dict()},
    )
    kernel.reduce(observation)

    admission = kernel.state.contract_amendment_admission_projection
    apply_action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=str(admission["admission_digest"]),
    )
    apply_observation = Observation.from_action(
        apply_action,
        observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
        status=RunStageStatus.COMPLETED,
        payload={},
    )
    kernel.reduce(apply_observation)


def _reduce_search_executor_handoff(
    kernel: RunKernel,
    *,
    provider_hint: str,
) -> None:
    contract = kernel.state.current_answer_contract
    handoff_input = SearchExecutorHandoffInput(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        parent_current_contract_ref=handoff_contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
        parent_initial_contract_ref=handoff_contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        contract_parent_kind="current_answer_contract",
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            kernel.state.search_planner_proposal_state
        ),
        answer_component_refs=contract.get("accepted_answer_component_refs", []),
        source_obligation_candidate_refs=_source_refs_from_contract(contract),
        component_search_requirements=(
            kernel.state.search_planner_proposal_state.get(
                "component_search_requirements",
                [],
            )
        ),
        required_caveats=contract.get("mandatory_caveats", []),
        prohibited_upgrades=contract.get("prohibited_upgrades", []),
        query_budget={"max_search_tasks": 1, "max_results_per_task": 2},
        allowed_verticals=["search"],
        provider_preference_hint=provider_hint,
    )
    action = kernel.authorize_search_executor_handoff()
    result = execute_search_executor_handoff_action(
        action=action,
        handoff_input=handoff_input,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)


def _planner_adapter_result(planner_input: Mapping[str, Any]) -> dict[str, Any]:
    query_ref = _mapping(planner_input.get("user_query_ref"))
    return {
        "question_meaning_summary": (
            "Prepare a single official-current public-information lookup for "
            "search-candidate validation."
        ),
        "requested_output": "Sanitized search candidates only; no answer.",
        "semantic_slots": [
            {
                "slot_id": "slot:query-class",
                "slot_kind": "source_basis",
                "status": "explicit",
                "selected_value": "official-current public-information lookup",
                "materiality": "material",
            }
        ],
        "answer_components": [
            {
                "component_id": COMPONENT_ID,
                "component_revision": "1",
                "user_facing_label": "Official current public fact",
                "user_facing_question": DEFAULT_QUERY,
                "requirement_posture": "required",
                "acceptance_criteria": [
                    "discover official-current public result candidates",
                    "do not answer or cite the query in this harness",
                ],
                "semantic_slot_ids": ["slot:query-class"],
                "source_obligation_candidate_ids": [SOURCE_OBLIGATION_ID],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": [
                    "SearchResultCandidate records are non-evidence."
                ],
                "prohibited_upgrades": [
                    "Do not claim source-obligation satisfaction."
                ],
                "materiality": "material",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": SOURCE_OBLIGATION_ID,
                "obligation_kind": "official_current_source",
                "component_candidate_ids": [COMPONENT_ID],
                "strictness": "required",
            }
        ],
        "component_search_requirements": [
            {
                "component_id": COMPONENT_ID,
                "requirement_id": SEARCH_REQUIREMENT_ID,
                "requirement_summary": DEFAULT_QUERY,
                "source_obligation_candidate_ids": [SOURCE_OBLIGATION_ID],
                "preferred_source_kinds": ["official"],
                "recency_requirement": "current",
            }
        ],
        "material_ambiguity_posture": "clear",
        "mandatory_caveats": [
            "LIVE-RUN-01 prepares request packets only and does not answer."
        ],
        "prohibited_upgrades": [
            "No fetch/read, EvidenceLedger, citations, Sufficiency, FAP, Author, or product-correctness claim."
        ],
        "normalization_obligations": [
            "Treat the query as search-candidate discovery only."
        ],
        "assumptions": [
            "The trusted-local operator will supply any sanitized provider results separately."
        ],
        "unsupported_outputs": [
            "Final answer creation is outside AG-LIVE-XAXIS-VALIDATION-01A-LIVE-RUN-01."
        ],
        "planner_model_metadata": {
            "provider": "deterministic_harness_adapter",
            "model_adapter_enabled": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "provider_payload_retained": False,
            "prompt_hash": query_ref.get("digest"),
        },
    }


def _current_contract_caveat_record(
    kernel: RunKernel,
    accepted: Mapping[str, Any],
) -> ContractAmendmentRecord:
    operation = AmendmentOperation(
        operation_id="operation:add-live-run-01-harness-caveat",
        operation_kind=AmendmentOperationKind.ADD_CAVEAT,
        operation_payload={
            "caveat": (
                "LIVE-RUN-01 harness state is deterministic fixture state for "
                "request-packet preparation, not a product answer path."
            ),
            "component_id": COMPONENT_ID,
        },
    )
    return ContractAmendmentRecord(
        amendment_record_id="amendment:ag-live-xaxis-live-run-01-current-contract",
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        request_digest=_request_digest(),
        parent_contract_version=str(accepted["accepted_contract_version"]),
        parent_contract_digest=str(accepted["accepted_contract_digest"]),
        parent_question_meaning_record_id=accepted.get(
            "parent_question_meaning_record_id"
        ),
        parent_question_meaning_record_digest=accepted.get(
            "parent_question_meaning_record_digest"
        ),
        accepted_contract_ref=(
            f"contract:{accepted['accepted_contract_version']}:accepted"
        ),
        trigger_refs=AmendmentTriggerRefs(
            gap_refs=("harness:requires-current-answer-contract",),
            currentness_refs=("harness:official-current-query-class",),
        ),
        operations=(operation,),
        materiality=MaterialityPosture.NON_MATERIAL,
        user_confirmation_posture="not_required",
        monotonicity=MonotonicityPosture.STRENGTHENS,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        required_caveats=(
            "SearchResultCandidate records remain non-evidence.",
        ),
        prohibited_upgrades=(
            "Do not use provider_preference_hint as live provider authority.",
        ),
        metadata={
            "phase": PHASE,
            "front_half_source": "deterministic_repo_visible_harness_fixture",
        },
    )


def _single_selected_task_id(kernel: RunKernel) -> str:
    tasks = kernel.state.search_executor_handoff_state.get("search_task_records", [])
    if len(tasks) != 1:
        raise HarnessError(
            "LIVE-RUN-01 harness requires exactly one SearchExecutorHandoff task"
        )
    task = _mapping(tasks[0])
    task_id = str(task.get("search_task_id") or "")
    if not task_id:
        raise HarnessError("selected SearchExecutorHandoff task is missing id")
    return task_id


def _source_refs_from_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for component in contract.get("accepted_answer_component_refs", []) or []:
        mapping = _mapping(component)
        component_id = mapping.get("component_id")
        for candidate_id in mapping.get("source_obligation_candidate_ids", []) or []:
            refs.append(
                {
                    "candidate_id": candidate_id,
                    "component_candidate_ids": [component_id],
                    "obligation_kind": "source_support",
                    "strictness": "required",
                }
            )
    return refs


def _load_request_packet(path: str | Path) -> dict[str, Any]:
    resolved = validate_safe_output_packet_path(path, root=ROOT)
    decoded = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise HarnessError("request packet must be a JSON object")
    return validate_request_packet(decoded, root=ROOT)


def _load_provider_results(path: str | Path) -> dict[str, Sequence[Mapping[str, Any]]]:
    resolved = validate_safe_output_packet_path(path, root=ROOT)
    decoded = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise HarnessError("provider results must be a JSON object keyed by task id")
    result: dict[str, Sequence[Mapping[str, Any]]] = {}
    for task_id, value in decoded.items():
        if isinstance(value, str | bytes) or not isinstance(value, Sequence):
            raise HarnessError("provider results values must be lists")
        result[str(task_id)] = value
    return result


def _write_packet(path: str | Path, packet: Mapping[str, Any]) -> None:
    resolved = validate_safe_output_packet_path(path, root=ROOT)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(dumps_packet(packet), encoding="utf-8")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _request_digest() -> str:
    payload = {
        "phase": PHASE,
        "request_id": DEFAULT_REQUEST_ID,
        "query": DEFAULT_QUERY,
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
