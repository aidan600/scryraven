from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.author_prose_finalization_runtime import (  # noqa: E402
    reduce_author_prose_finalization,
)
from core.component_coverage_record import (  # noqa: E402
    ComponentCoverageRecord,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageState,
    CurrentnessPosture,
    DerivedSupportStatus,
    EvidenceBasis,
    EvidenceCustodyStatus,
    EvidenceLedgerSnapshotBinding,
    ExplicitnessPosture,
    FollowupNeed,
    ModeBudgetPosture,
    SemanticObservationCoverageRef,
    SemanticSupportStatus,
    SourceObligationStatus,
    SupportPosture,
    VersionValidity,
)
from core.component_coverage_reduction_runtime import (  # noqa: E402
    evidence_ledger_projection_digest,
)
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
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION  # noqa: E402
from core.evidence_ledger_lifecycle import (  # noqa: E402
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.evidence_relative_analysis_packet import (  # noqa: E402
    build_evidence_relative_analysis_packet,
    validate_evidence_relative_analysis_packet,
)
from core.fetch_read_content_reference import (  # noqa: E402
    build_fetch_read_content_packet_from_candidate_packet,
    validate_fetch_read_content_packet,
)
from core.final_answer_packet_hardening_runtime import (  # noqa: E402
    reduce_hardened_final_answer_packet,
)
from core.live_search_validation_runtime import (  # noqa: E402
    build_live_search_validation_observation_payload,
)
from core.run_kernel import (  # noqa: E402
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.scrutineer_review_runtime import (  # noqa: E402
    build_scrutineer_review_record,
    reduce_scrutineer_review,
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
from core.search_result_candidate_packet import (  # noqa: E402
    build_search_result_candidate_packet_from_live_validation_state,
    validate_search_result_candidate_packet,
)
from core.semantic_observation_admission_bridge import (  # noqa: E402
    admit_semantic_observations_from_analysis_support_findings,
)
from core.specialist_source_bound_calculation_runtime import (  # noqa: E402
    build_specialist_source_bound_calculation_record,
    reduce_specialist_source_bound_calculation,
)
from core.sufficiency_readiness_runtime import (  # noqa: E402
    reduce_sufficiency_readiness,
)

PHASE = "AG-FIXTURE-DOGFOOD-INTEGRATION-01"
PROOF_CLASS = "product-facing dry-run proof plus phase-focused integration tests"
PRODUCT_PROGRESS_TYPE = "product-facing dry-run dogfood output / product-path integration"
PRODUCT_PATH_AFFECTED = "offline fixture dogfood path only"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "ag_fixture_dogfood_integration_01"
MANDATORY_NEXT_CHECKPOINT = "AG-LOCAL-DRYRUN-QUERY-TO-AUTHORPROSE-01"
OLD_PATH_TREATMENT = (
    "Old FAP/Author/follow-up/sufficiency/AG-89D/AG-91K/AG-92C/AG-96/"
    "pipeline/offline bridge surfaces remain legacy/passive/historical or closed."
)
DEFAULT_QUERY = "fixture dogfood official permit threshold"
DEFAULT_RUN_ID = "run:ag-fixture-dogfood-integration-01"
DEFAULT_REQUEST_ID = "request:ag-fixture-dogfood-integration-01"
COMPONENT_ID = "component:official-current-public-fact"
SOURCE_OBLIGATION_ID = "obligation:official-current-public-source"
SEARCH_REQUIREMENT_ID = "searchreq:official-current-public-fact"

EXPLICIT_NON_PROOFS = [
    "ordinary live user-query execution",
    "live source acquisition quality",
    "real-source fetch/read survival",
    "messy-live-evidence semantic support",
    "citation rendering",
    "citation eligibility in user-visible output",
    "source-obligation satisfaction",
    "product correctness",
    "product-quality Author prose",
    "live validation",
]

CURRENT_PATH_SURFACE_ORDER = [
    "SearchResultCandidatePacket",
    "FetchReadContentPacket / SanitizedContentReference",
    "EvidenceLedger candidate/content custody",
    "EvidenceRelativeAnalysisPacket / AnalystReport",
    "FollowupSearchIntent / follow-up authorization",
    "SemanticObservation admission",
    "ComponentCoverage",
    "ScrutineerReview",
    "Specialist source-bound calculation",
    "SufficiencyReadiness",
    "hardened FinalAnswerPacket",
    "AuthorProseFinalization",
]


class FixtureDogfoodError(ValueError):
    """Raised when the dogfood runner cannot produce a review packet safely."""


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    scenario_id: str
    title: str
    scenario_kind: str
    description: str


@dataclass(frozen=True, slots=True)
class GeneratedReviewPacket:
    scenario_id: str
    json_path: Path
    markdown_path: Path
    packet: dict[str, Any]


class DeterministicDogfoodPlannerAdapter:
    """Repo-visible planner fixture; never calls a model or provider."""

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return _planner_adapter_result(planner_input)


def generate_review_packets(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> list[GeneratedReviewPacket]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    packets = [
        _build_full_supported_packet(),
        _build_partial_packet(),
        _build_contested_packet(),
    ]
    generated: list[GeneratedReviewPacket] = []
    for packet in packets:
        scenario_id = packet["scenario"]["scenario_id"]
        json_path = target / f"{scenario_id}.json"
        markdown_path = target / f"{scenario_id}.md"
        _write_json(json_path, packet)
        markdown_path.write_text(_packet_markdown(packet), encoding="utf-8")
        generated.append(
            GeneratedReviewPacket(
                scenario_id=scenario_id,
                json_path=json_path,
                markdown_path=markdown_path,
                packet=packet,
            )
        )

    index = {
        "phase": PHASE,
        "proof_class": PROOF_CLASS,
        "product_facing_progress_type": PRODUCT_PROGRESS_TYPE,
        "packet_count": len(generated),
        "packets": [
            {
                "scenario_id": item.scenario_id,
                "json_path": str(item.json_path),
                "markdown_path": str(item.markdown_path),
                "author_prose_status": item.packet["author_prose_output"][
                    "author_prose_status"
                ],
                "sufficiency_readiness_status": item.packet[
                    "sufficiency_readiness_status"
                ]["final_readiness_status"],
                "fap_status": item.packet["hardened_final_answer_packet_status"][
                    "fap_status"
                ],
            }
            for item in generated
        ],
        "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
        "mandatory_next_checkpoint": MANDATORY_NEXT_CHECKPOINT,
    }
    _write_json(target / "index.json", index)
    (target / "index.md").write_text(_index_markdown(index), encoding="utf-8")
    return generated


def _build_full_supported_packet() -> dict[str, Any]:
    spec = ScenarioSpec(
        scenario_id="01_full_supported",
        title="Fully Supported Answer",
        scenario_kind="full_supported",
        description=(
            "A readable fixture candidate moves through custody, Analyst support, "
            "SemanticObservation admission, ComponentCoverage, Specialist, "
            "Scrutineer, SufficiencyReadiness, hardened FAP, and AuthorProse."
        ),
    )
    chain = _supported_chain_with_candidate_packet()
    kernel = chain["kernel"]

    _reduce_specialist_success(chain)
    _reduce_scrutineer(
        chain,
        red_flag_context=True,
        specialist_source_bound_calculation_projection=(
            kernel.state.specialist_source_bound_calculation_projection
        ),
        specialist_source_bound_calculation_history=(
            kernel.state.specialist_source_bound_calculation_history
        ),
    )
    _reduce_readiness_fap_author(kernel)
    return _review_packet(spec, chain)


def _build_partial_packet() -> dict[str, Any]:
    spec = ScenarioSpec(
        scenario_id="02_partial_unresolved",
        title="Partial Answer With Unresolved Optional Component",
        scenario_kind="partial_or_blocked",
        description=(
            "One component is supported by the current path while a second "
            "optional component remains unresolved. AuthorProse must preserve "
            "the partial posture instead of hiding the unresolved component."
        ),
    )
    chain = _supported_chain_with_candidate_packet()
    _add_component(
        chain["kernel"],
        component_id="component:optional-context",
        required=False,
    )
    _reduce_readiness_fap_author(chain["kernel"])
    return _review_packet(spec, chain)


def _build_contested_packet() -> dict[str, Any]:
    spec = ScenarioSpec(
        scenario_id="03_contested_weak_evidence",
        title="Contested Weak Evidence",
        scenario_kind="contested_weak_or_conflicting",
        description=(
            "The candidate/content/custody path supports the component, but "
            "Specialist receives mixed currentness and weak-source numeric "
            "inputs. Sufficiency, FAP, and AuthorProse must preserve contested "
            "posture and avoid overclaiming."
        ),
    )
    chain = _supported_chain_with_candidate_packet()
    kernel = chain["kernel"]
    contested = _specialist_record(
        chain,
        calculation_kind="sum",
        inputs=[
            _specialist_input(chain, label="current", value=10),
            _specialist_input(
                chain,
                label="stale",
                value=15,
                currentness="unknown",
                source_class="weak_secondary",
            ),
        ],
    )
    reduce_specialist_source_bound_calculation(
        run_kernel=kernel,
        specialist_source_bound_calculation_record=contested,
    )
    _reduce_readiness_fap_author(
        kernel,
        author_policy={"uncertainty_profile": "contested_first"},
    )
    return _review_packet(spec, chain)


def _packet_from_state(*, candidate_count: int = 1) -> tuple[Any, dict[str, Any]]:
    kernel = _build_front_half_kernel()
    _reduce_validation(kernel, results=_fake_results(kernel, count=candidate_count))
    packet = build_search_result_candidate_packet_from_live_validation_state(
        kernel.state.live_search_validation_state
    )
    return kernel, packet


def _build_front_half_kernel() -> RunKernel:
    kernel = RunKernel.start(
        run_id=DEFAULT_RUN_ID,
        request_id=DEFAULT_REQUEST_ID,
        request={
            "phase": PHASE,
            "proof_class": PROOF_CLASS,
            "query_class": "deterministic fixture dogfood",
            "query_text_retained": False,
        },
    )
    _reduce_deterministic_planner(kernel)
    _accept_initial_contract(kernel)
    _apply_current_contract_caveat(kernel)
    _reduce_search_executor_handoff(kernel)
    return kernel


def _reduce_deterministic_planner(kernel: RunKernel) -> None:
    planner_input = SearchPlannerInput(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        user_query_text=DEFAULT_QUERY,
        requested_mode="balanced",
        safe_context={
            "phase": PHASE,
            "front_half_source": "deterministic_fixture_dogfood",
            "source_policy": "official-current",
            "not_product_path": True,
        },
        route_context_ref={"route_ref": "ag-fixture-dogfood-integration-01"},
        run_context_ref={"run_ref": "ag-fixture-dogfood-integration-01"},
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
        adapter=DeterministicDogfoodPlannerAdapter(),
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )


def _accept_initial_contract(kernel: RunKernel) -> None:
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=str(qmr["record_id"]),
        parent_proposal_digest=str(qmr["record_digest"]),
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": dict(qmr)},
        )
    )


def _apply_current_contract_caveat(kernel: RunKernel) -> None:
    accepted = kernel.state.initial_answer_contract
    record = _current_contract_caveat_record(kernel, accepted)
    action = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={"contract_amendment_record": record.to_dict()},
        )
    )

    admission = kernel.state.contract_amendment_admission_projection
    apply_action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=str(admission["admission_digest"]),
    )
    kernel.reduce(
        Observation.from_action(
            apply_action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )


def _reduce_search_executor_handoff(kernel: RunKernel) -> None:
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
        provider_preference_hint="serper",
    )
    action = kernel.authorize_search_executor_handoff()
    result = execute_search_executor_handoff_action(
        action=action,
        handoff_input=handoff_input,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )


def _selected_task_ids(kernel: RunKernel, *, count: int = 1) -> list[str]:
    tasks = kernel.state.search_executor_handoff_state["search_task_records"]
    return [task["search_task_id"] for task in tasks[:count]]


def _fake_results(
    kernel: RunKernel,
    *,
    count: int = 1,
) -> dict[str, list[dict[str, Any]]]:
    task_id = _selected_task_ids(kernel)[0]
    results = []
    for index in range(1, count + 1):
        results.append(
            {
                "title": f"Official Example Permit Threshold {index}",
                "url": f"https://official.example.gov/permit/threshold-{index}",
                "domain": "official.example.gov",
                "snippet": "Official current threshold information.",
                "published_or_observed_date": "2026-01-01",
            }
        )
    return {task_id: results}


def _reduce_validation(
    kernel: RunKernel,
    *,
    results: Mapping[str, list[dict[str, Any]]],
) -> None:
    action = kernel.authorize_live_search_validation(
        selected_search_task_ids=_selected_task_ids(kernel),
        provider_authorized="serper",
        provider_call_cap=2,
        results_per_task_cap=2,
    )
    payload = build_live_search_validation_observation_payload(
        action=action,
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=kernel.state.search_executor_handoff_state,
        provider_used="serper",
        provider_results_by_task=results,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
            status=RunStageStatus.COMPLETED,
            payload=payload,
        )
    )


def _readable_material(
    packet: Mapping[str, Any],
    *,
    index: int = 0,
) -> dict[str, Any]:
    candidate = packet["candidate_records"][index]
    bounded_text = "Bounded sanitized excerpt about the permit threshold."
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "run_id": packet["run_id"],
        "request_id": packet["request_id"],
        "current_answer_contract_digest": packet["current_answer_contract_digest"],
        "search_executor_handoff_digest": packet["search_executor_handoff_digest"],
        "search_result_candidate_packet_id": packet["packet_id"],
        "search_result_candidate_packet_digest": packet["packet_digest"],
        "fetch_read_status": "readable",
        "attempted_url": candidate["url"],
        "resolved_url": candidate["url"],
        "resolved_domain": candidate["domain"],
        "content_type": "text/html",
        "http_status": 200,
        "retrieved_or_observed_at": "2026-06-28T00:00:00Z",
        "published_or_observed_date": "2026-01-01",
        "content_title": "Official Example Permit Threshold",
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(bounded_text),
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }


def _failed_material(packet: Mapping[str, Any], *, index: int = 0) -> dict[str, Any]:
    candidate = packet["candidate_records"][index]
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "fetch_read_status": "failed",
        "attempted_url": candidate["url"],
        "resolved_domain": candidate["domain"],
        "read_error_code": "timeout",
        "failure_reason": "timeout",
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }


def _custody_records(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = projection["fetch_read_candidate_custody"][
        "fetch_read_candidate_custody_records"
    ]
    return [dict(record) for record in records]


def _records_by_status(
    projection: Mapping[str, Any],
    status: str,
) -> list[dict[str, Any]]:
    return [
        record
        for record in _custody_records(projection)
        if record["fetch_read_status"] == status
    ]


def _support_proposal(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal_kind": "possible_support_proposal",
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_digest": record[
            "fetch_read_content_packet_digest"
        ],
        "search_result_candidate_packet_digest": record[
            "search_result_candidate_packet_digest"
        ],
        "component_id": record["component_id"],
        "proposal_summary": "Appears relevant to the requested component.",
        "reason": "offline analyst proposal over custody identity only",
    }


def _contract_ref_from_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    record = _records_by_status(projection, "readable")[0]
    ref = dict(record.get("current_answer_contract_ref") or {})
    return {
        "source": ref.get("source") or "current_answer_contract",
        "contract_version": (
            ref.get("contract_version")
            or ref.get("current_contract_version")
            or ref.get("accepted_contract_version")
        ),
        "contract_digest": (
            ref.get("contract_digest")
            or ref.get("current_contract_digest")
            or ref.get("accepted_contract_digest")
            or record["current_answer_contract_digest"]
        ),
    }


def _bridge(chain: Mapping[str, Any]):
    return admit_semantic_observations_from_analysis_support_findings(
        run_kernel=chain["kernel"],
        evidence_relative_analysis_packet=chain["analysis_packet"],
        fetch_read_content_packet=chain["fetch_read_packet"],
    )[0]


def _bridge_coverage_record(
    chain: Mapping[str, Any],
    result: Any,
) -> ComponentCoverageRecord:
    return _coverage_record(
        kernel=chain["kernel"],
        record_id="coverage:ag-fixture-dogfood-integration:supportable",
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        observation=result.semantic_observation,
        content_ref=result.sanitized_content_reference,
        remaining_unknowns=(
            "source-obligation candidate ids remain lineage only",
            "this fixture does not prove citation rendering",
        ),
        followup_need=FollowupNeed.OPTIONAL,
        currentness_posture=CurrentnessPosture.CURRENT,
        metadata={"phase": PHASE, "analyst_finding_id": result.analyst_finding["finding_id"]},
    ).require_valid()


def _initial_component_ref(kernel: Any) -> Mapping[str, Any]:
    return kernel.state.initial_answer_contract["accepted_answer_component_refs"][0]


def _ledger_binding(kernel: Any) -> EvidenceLedgerSnapshotBinding:
    projection = kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        ref["observation_id"]
        for ref in projection.get("observation_refs") or ()
        if isinstance(ref, Mapping) and ref.get("observation_id")
    )
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{kernel.state.run_id}:{digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _coverage_record(
    *,
    kernel: Any,
    record_id: str,
    coverage_state: CoverageState,
    semantic_support_status: SemanticSupportStatus,
    source_obligation_status: SourceObligationStatus,
    content_availability_status: ContentAvailabilityStatus,
    evidence_custody_status: EvidenceCustodyStatus,
    evidence_basis: tuple[EvidenceBasis, ...],
    observation: Any,
    content_ref: Any,
    remaining_unknowns: tuple[str, ...],
    followup_need: FollowupNeed,
    currentness_posture: CurrentnessPosture,
    metadata: Mapping[str, Any] | None = None,
) -> ComponentCoverageRecord:
    accepted = kernel.state.initial_answer_contract
    component_ref = _initial_component_ref(kernel)
    return ComponentCoverageRecord(
        record_id=record_id,
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        request_digest=accepted["parent_question_meaning_record_digest"],
        accepted_contract_version=accepted["accepted_contract_version"],
        accepted_contract_digest=accepted["accepted_contract_digest"],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=_ledger_binding(kernel),
        coverage_state=coverage_state,
        semantic_support_status=semantic_support_status,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=source_obligation_status,
        content_availability_status=content_availability_status,
        evidence_custody_status=evidence_custody_status,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=(
            SemanticObservationCoverageRef.from_observation(observation),
        ),
        content_reference_bindings=(
            ContentReferenceCoverageBinding.from_content_reference(content_ref),
        ),
        evidence_basis=evidence_basis,
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        currentness_posture=currentness_posture,
        remaining_unknowns=remaining_unknowns,
        required_caveats=("Do not upgrade observed custody to final evidence.",),
        prohibited_upgrades=(
            "Do not treat Analyst possible_support_proposal as canonical coverage.",
        ),
        followup_need=followup_need,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        metadata=dict(metadata or {}),
    )


def _reseal_coverage(record: ComponentCoverageRecord) -> dict[str, Any]:
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    return payload


def _reduce_coverage(kernel: Any, record: ComponentCoverageRecord) -> dict[str, Any]:
    component_ref = _initial_component_ref(kernel)
    action = kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
            status=RunStageStatus.COMPLETED,
            payload={"component_coverage_record": _reseal_coverage(record)},
        )
    )
    return dict(kernel.state.component_coverage_projection)


def _review_record(chain: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    kernel = chain["kernel"]
    return build_scrutineer_review_record(
        evidence_relative_analysis_packet=chain["analysis_packet"],
        semantic_observation_admission_projection=(
            kernel.state.semantic_observation_admission_projection
        ),
        semantic_observation_admission_history=(
            kernel.state.semantic_observation_admission_history
        ),
        component_coverage_projection=kernel.state.component_coverage_projection,
        component_coverage_history=kernel.state.component_coverage_history,
        **kwargs,
    )


def _reduce_review(chain: Mapping[str, Any], record: Mapping[str, Any]) -> Any:
    return reduce_scrutineer_review(
        run_kernel=chain["kernel"],
        scrutineer_review_record=record,
    )


def _component_ref(chain: Mapping[str, Any]) -> dict[str, Any]:
    return dict(
        chain["kernel"].state.initial_answer_contract[
            "accepted_answer_component_refs"
        ][0]
    )


def _source_ref(chain: Mapping[str, Any]) -> dict[str, Any]:
    admission = chain["kernel"].state.semantic_observation_admission_projection
    coverage = chain["kernel"].state.component_coverage_projection
    analysis_packet = chain["analysis_packet"]
    content_ref = (admission.get("content_ref_records") or [{}])[0]
    return {
        "evidence_ledger_ref": analysis_packet["evidence_ledger_ref"],
        "content_ref": {
            "content_ref_id": content_ref.get("content_ref_id"),
            "content_digest": content_ref.get("content_digest"),
        },
        "semantic_observation_ref": {
            "observation_id": admission["observation_id"],
            "observation_digest": admission["observation_digest"],
        },
        "analysis_packet_ref": {
            "packet_id": analysis_packet["packet_id"],
            "packet_digest": analysis_packet["packet_digest"],
        },
        "component_ref": {
            "component_id": coverage["answer_component_id"],
            "component_digest": coverage["component_digest"],
        },
    }


def _specialist_input(
    chain: Mapping[str, Any],
    *,
    label: str,
    value: Any,
    unit: str | None = "USD",
    source_bound: bool = True,
    currentness: str = "current",
    source_class: str = "current_primary_or_official",
    conflict: str = "none",
) -> dict[str, Any]:
    component = _component_ref(chain)
    return {
        "label": label,
        "numeric_value": value,
        "unit": unit,
        "scale": "ones",
        "source_bound": source_bound,
        "fixture_bound": False,
        "source_bound_ref": _source_ref(chain),
        "fixture_ref": {},
        "component_id": component["component_id"],
        "currentness_posture": currentness,
        "source_class_posture": source_class,
        "conflict_posture": conflict,
        "caveats": ["fixture numeric input; no answer authority"],
    }


def _specialist_record(
    chain: Mapping[str, Any],
    *,
    calculation_kind: str = "difference",
    inputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    kernel = chain["kernel"]
    return build_specialist_source_bound_calculation_record(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        calculation_kind=calculation_kind,
        formula_label=f"fixture {calculation_kind}",
        input_records=inputs
        or [
            _specialist_input(chain, label="gross", value=42),
            _specialist_input(chain, label="offset", value=12),
        ],
        reviewed_artifact_refs={
            "analysis_packet_ref": {
                "packet_id": chain["analysis_packet"]["packet_id"],
                "packet_digest": chain["analysis_packet"]["packet_digest"],
            }
        },
    )


def _add_component(
    kernel: Any,
    *,
    component_id: str,
    required: bool,
) -> dict[str, Any]:
    component = deepcopy(
        kernel.state.current_answer_contract["accepted_answer_component_refs"][0]
    )
    component["component_id"] = component_id
    component["component_revision"] = "1"
    component["component_digest"] = f"digest:{component_id}"
    component["requirement_posture"] = "required" if required else "optional"
    component["materiality"] = "material" if required else "non_material"
    component["mandatory_caveats"] = [
        f"Component {component_id} is unresolved in the readiness preview."
    ]
    component["prohibited_upgrades"] = [
        f"Do not upgrade component {component_id} beyond supported readiness."
    ]
    refs = kernel.state.current_answer_contract["accepted_answer_component_refs"]
    refs.append(component)
    kernel.state.current_answer_contract["accepted_answer_component_count"] = len(refs)
    return component


def _planner_adapter_result(planner_input: Mapping[str, Any]) -> dict[str, Any]:
    query_ref = _mapping(planner_input.get("user_query_ref"))
    return {
        "question_meaning_summary": (
            "Prepare an official-current fixture chain for AuthorProse dogfood."
        ),
        "requested_output": "Reviewable AuthorProse dry-run packet.",
        "semantic_slots": [
            {
                "slot_id": "slot:query-class",
                "slot_kind": "source_basis",
                "status": "explicit",
                "selected_value": "official-current fixture dogfood",
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
                    "preserve fixture source/content/custody lineage",
                    "produce AuthorProse without live validation claims",
                ],
                "semantic_slot_ids": ["slot:query-class"],
                "source_obligation_candidate_ids": [SOURCE_OBLIGATION_ID],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": [
                    "Fixture current-path output does not prove live validation."
                ],
                "prohibited_upgrades": [
                    "Do not claim citation rendering or source-obligation satisfaction."
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
            "AG-FIXTURE dogfood uses deterministic offline fixtures only."
        ],
        "prohibited_upgrades": [
            "No live provider/model/search/fetch/read/retrieval, citation rendering, old Author, or product-correctness claim."
        ],
        "normalization_obligations": [
            "Preserve review-output boundaries and explicit non-proofs."
        ],
        "assumptions": [
            "Fixture candidate/read material is deterministic and sanitized."
        ],
        "unsupported_outputs": [
            "Live product correctness is outside AG-FIXTURE-DOGFOOD-INTEGRATION-01."
        ],
        "planner_model_metadata": {
            "provider": "deterministic_fixture_adapter",
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
        operation_id="operation:add-ag-fixture-dogfood-caveat",
        operation_kind=AmendmentOperationKind.ADD_CAVEAT,
        operation_payload={
            "caveat": (
                "AG-FIXTURE dogfood state is deterministic fixture state for "
                "review packet generation, not live product validation."
            ),
            "component_id": COMPONENT_ID,
        },
    )
    return ContractAmendmentRecord(
        amendment_record_id="amendment:ag-fixture-dogfood-current-contract",
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
            gap_refs=("fixture:review-output-boundary",),
            currentness_refs=("fixture:official-current-dogfood",),
        ),
        operations=(operation,),
        materiality=MaterialityPosture.NON_MATERIAL,
        user_confirmation_posture="not_required",
        monotonicity=MonotonicityPosture.STRENGTHENS,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        required_caveats=(
            "Review packets do not prove live source acquisition or product correctness.",
        ),
        prohibited_upgrades=(
            "Do not treat fixture output as citation rendering or source-obligation satisfaction.",
        ),
        metadata={"phase": PHASE},
    )


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


def _supported_chain_with_candidate_packet() -> dict[str, Any]:
    kernel, candidate_packet = _packet_from_state(candidate_count=1)
    candidate_packet = validate_search_result_candidate_packet(
        deepcopy(candidate_packet)
    )
    materials = [_readable_material(candidate_packet, index=0)]
    fetch_read_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        materials,
    )
    fetch_read_packet = validate_fetch_read_content_packet(deepcopy(fetch_read_packet))
    ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_read_packet,
    )
    readable = _records_by_status(ledger_projection, "readable")[0]
    contract_ref = _contract_ref_from_projection(ledger_projection)
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=ledger_projection,
        analyst_proposal_records=[_support_proposal(readable)],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    analysis_packet = validate_evidence_relative_analysis_packet(
        deepcopy(analysis_packet)
    )
    chain = {
        "kernel": kernel,
        "candidate_packet": candidate_packet,
        "fetch_read_packet": fetch_read_packet,
        "ledger_projection": ledger_projection,
        "analysis_packet": analysis_packet,
        "followup_packet": None,
    }
    admission = _bridge(chain)
    coverage_record = _bridge_coverage_record(chain, admission)
    coverage_projection = _reduce_coverage(kernel, coverage_record)
    chain.update(
        {
            "semantic_admission": admission,
            "coverage_record": coverage_record.to_dict(include_validation=False),
            "coverage_projection": coverage_projection,
        }
    )
    return chain


def _reduce_specialist_success(chain: Mapping[str, Any]) -> None:
    reduce_specialist_source_bound_calculation(
        run_kernel=chain["kernel"],
        specialist_source_bound_calculation_record=_specialist_record(chain),
    )


def _reduce_scrutineer(chain: Mapping[str, Any], **kwargs: Any) -> None:
    review = _review_record(chain, mode="Balanced", **kwargs)
    _reduce_review(chain, review)


def _reduce_readiness_fap_author(
    kernel: Any,
    *,
    author_policy: Mapping[str, Any] | None = None,
) -> None:
    reduce_sufficiency_readiness(run_kernel=kernel, mode="Balanced")
    reduce_hardened_final_answer_packet(run_kernel=kernel)
    reduce_author_prose_finalization(run_kernel=kernel, policy=author_policy)


def _review_packet(spec: ScenarioSpec, chain: Mapping[str, Any]) -> dict[str, Any]:
    kernel = chain["kernel"]
    readiness = dict(kernel.state.sufficiency_readiness_projection)
    fap = dict(kernel.state.final_answer_authority_projection)
    author = dict(kernel.state.author_prose_projection)
    packet = {
        "phase": PHASE,
        "scenario": {
            "scenario_id": spec.scenario_id,
            "title": spec.title,
            "scenario_kind": spec.scenario_kind,
            "description": spec.description,
            "mode": "Balanced",
            "run_id": kernel.state.run_id,
            "request_id": kernel.state.request_id,
            "current_answer_contract_ref": _contract_summary(
                kernel.state.current_answer_contract
            ),
        },
        "proof_class": PROOF_CLASS,
        "product_facing_progress_type": PRODUCT_PROGRESS_TYPE,
        "product_path_affected": PRODUCT_PATH_AFFECTED,
        "runtime_consumer": (
            "existing current-path reducers/builders/runtimes through "
            "AuthorProseFinalization"
        ),
        "actual_app_delta": (
            "deterministic local generation of reviewable product-shaped "
            "AuthorProse packets from fixture scenarios"
        ),
        "user_facing_reviewable_output_delta": (
            "JSON and Markdown packets showing candidate/content/custody "
            "through SufficiencyReadiness, hardened FAP, and AuthorProse"
        ),
        "generated_by_invoking_current_path_surfaces": True,
        "current_path_surfaces_consumed": _surface_consumption(chain, kernel),
        "input_candidate_content_custody_refs": _input_refs(chain),
        "component_coverage_summary": _coverage_summary(chain, readiness),
        "followup_scrutineer_specialist_posture": _review_specialist_posture(
            chain,
            kernel,
        ),
        "sufficiency_readiness_status": {
            "owner": readiness.get("owner"),
            "final_readiness_status": readiness.get("final_readiness_status"),
            "readiness_digest": readiness.get("readiness_digest"),
            "component_statuses": _component_statuses(readiness),
            "followup_budget_posture": readiness.get("followup_budget_posture"),
            "mandatory_caveats": readiness.get("mandatory_caveats") or [],
            "prohibited_upgrades": readiness.get("prohibited_upgrades") or [],
        },
        "hardened_final_answer_packet_status": {
            "owner": fap.get("owner"),
            "fap_status": fap.get("fap_status"),
            "packet_created": fap.get("packet_created"),
            "packet_id": fap.get("packet_id"),
            "packet_digest": fap.get("packet_digest"),
            "component_packet_entries": fap.get("component_packet_entries") or [],
            "mandatory_caveats": fap.get("mandatory_caveats") or [],
            "prohibited_upgrades": fap.get("prohibited_upgrades") or [],
        },
        "author_prose_output": {
            "owner": author.get("owner"),
            "author_prose_status": author.get("author_prose_status"),
            "fap_status": author.get("fap_status"),
            "answer_text": author.get("answer_text"),
            "answer_blocks": author.get("answer_blocks") or [],
            "supported_component_ids": author.get("supported_component_ids") or [],
            "unresolved_component_ids": author.get("unresolved_component_ids") or [],
            "must_not_answer_component_ids": (
                author.get("must_not_answer_component_ids") or []
            ),
            "source_ref_presentation": author.get("source_ref_presentation") or {},
            "mandatory_caveats": author.get("mandatory_caveats") or [],
            "prohibited_upgrades": author.get("prohibited_upgrades") or [],
            "prohibited_claims": author.get("prohibited_claims") or [],
        },
        "caveats_blockers_contested_posture": _caveat_blocker_posture(
            readiness,
            fap,
            author,
        ),
        "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
        "old_path_treatment": OLD_PATH_TREATMENT,
        "live_validation_status": (
            "not run; fixture fake search-result state only; no broker, "
            "provider, fetch/read execution, retrieval, model, citation "
            "rendering, or old Author execution"
        ),
        "mandatory_next_checkpoint": MANDATORY_NEXT_CHECKPOINT,
        "review_packet_theater_guard": {
            "review_packet_is_output_only": True,
            "manual_final_summary_assembly": False,
            "actual_current_path_outputs_recorded": True,
            "core_surfaces_invoked": _invoked_surface_names(kernel),
        },
        "current_path_outputs": _current_path_outputs(chain, kernel),
    }
    return _json_safe(packet)


def _surface_consumption(
    chain: Mapping[str, Any],
    kernel: Any,
) -> list[dict[str, Any]]:
    consumed = {
        "SearchResultCandidatePacket": _packet_ref(chain["candidate_packet"]),
        "FetchReadContentPacket / SanitizedContentReference": _packet_ref(
            chain["fetch_read_packet"]
        ),
        "EvidenceLedger candidate/content custody": _ledger_ref(chain),
        "EvidenceRelativeAnalysisPacket / AnalystReport": _packet_ref(
            chain["analysis_packet"]
        ),
        "SemanticObservation admission": _semantic_admission_ref(kernel),
        "ComponentCoverage": _coverage_ref(kernel),
        "SufficiencyReadiness": _readiness_ref(kernel),
        "hardened FinalAnswerPacket": _packet_ref(
            kernel.state.final_answer_authority_projection
        ),
        "AuthorProseFinalization": _author_prose_ref(kernel),
    }
    if chain.get("followup_packet"):
        consumed["FollowupSearchIntent / follow-up authorization"] = _packet_ref(
            chain["followup_packet"]
        )
    if kernel.state.scrutineer_review_projection:
        consumed["ScrutineerReview"] = _scrutineer_ref(kernel)
    if kernel.state.specialist_source_bound_calculation_projection:
        consumed["Specialist source-bound calculation"] = _specialist_ref(kernel)

    surfaces: list[dict[str, Any]] = []
    for surface in CURRENT_PATH_SURFACE_ORDER:
        ref = consumed.get(surface)
        surfaces.append(
            {
                "surface": surface,
                "status": "consumed" if ref else "not_applicable",
                "ref": ref or {},
                "not_applicable_reason": (
                    "" if ref else _not_applicable_reason(surface)
                ),
            }
        )
    return surfaces


def _input_refs(chain: Mapping[str, Any]) -> dict[str, Any]:
    candidate_packet = chain["candidate_packet"]
    fetch_read_packet = chain["fetch_read_packet"]
    ledger_projection = chain["ledger_projection"]
    custody_records = ledger_projection["fetch_read_candidate_custody"][
        "fetch_read_candidate_custody_records"
    ]
    return {
        "candidate_packet_ref": _packet_ref(candidate_packet),
        "candidate_refs": [
            _pick(
                record,
                (
                    "candidate_id",
                    "candidate_digest",
                    "component_id",
                    "title",
                    "url",
                    "domain",
                    "snippet",
                    "published_or_observed_date",
                    "non_evidence",
                    "not_citation",
                ),
            )
            for record in candidate_packet.get("candidate_records", [])
        ],
        "fetch_read_packet_ref": _packet_ref(fetch_read_packet),
        "content_refs": [
            _pick(
                record,
                (
                    "reference_id",
                    "reference_digest",
                    "candidate_id",
                    "fetch_read_status",
                    "content_title",
                    "resolved_url",
                    "resolved_domain",
                    "bounded_text_digest",
                    "bounded_text_char_count",
                    "not_semantic_support",
                    "not_citation_eligible",
                ),
            )
            for record in fetch_read_packet.get("reference_records", [])
        ],
        "evidence_ledger_ref": _ledger_ref(chain),
        "custody_refs": [
            _pick(
                record,
                (
                    "custody_record_id",
                    "custody_record_digest",
                    "reference_id",
                    "reference_digest",
                    "candidate_id",
                    "candidate_digest",
                    "component_id",
                    "fetch_read_status",
                    "custody_status",
                    "content_digest",
                    "source_obligation_satisfied",
                    "semantic_support_created",
                    "citation_eligible",
                ),
            )
            for record in custody_records
        ],
    }


def _coverage_summary(
    chain: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    coverage = chain.get("coverage_projection") or {}
    return {
        "coverage_ref": _packet_like_ref(
            coverage,
            id_keys=("coverage_state_id", "record_id", "coverage_record_id"),
            digest_keys=("coverage_digest", "record_digest"),
        ),
        "coverage_state": coverage.get("coverage_state"),
        "semantic_support_status": coverage.get("semantic_support_status"),
        "source_obligation_status": coverage.get("source_obligation_status"),
        "content_availability_status": coverage.get("content_availability_status"),
        "evidence_custody_status": coverage.get("evidence_custody_status"),
        "component_readiness_map": readiness.get("component_readiness_map") or {},
        "supported_component_refs": readiness.get("supported_component_refs") or [],
        "missing_component_refs": readiness.get("missing_component_refs") or [],
        "followup_required_component_refs": (
            readiness.get("followup_required_component_refs") or []
        ),
    }


def _review_specialist_posture(
    chain: Mapping[str, Any],
    kernel: Any,
) -> dict[str, Any]:
    followup_packet = chain.get("followup_packet")
    review = kernel.state.scrutineer_review_projection
    specialist = kernel.state.specialist_source_bound_calculation_projection
    authorization_projection = kernel.state.projections.get(
        "followup_search_authorization"
    )
    return {
        "followup": {
            "status": "intent_packet_present" if followup_packet else "not_applicable",
            "intent_packet_ref": _packet_ref(followup_packet) if followup_packet else {},
            "authorization_status": (
                "authorized" if authorization_projection else "not_authorized"
            ),
            "authorization_ref": authorization_projection or {},
        },
        "scrutineer": {
            "status": "consumed" if review else "not_applicable",
            "review_outcome": review.get("review_outcome") if review else None,
            "issue_count": review.get("issue_count") if review else 0,
            "contested": review.get("contested") if review else False,
            "review_ref": _scrutineer_ref(kernel) if review else {},
        },
        "specialist": {
            "status": "consumed" if specialist else "not_applicable",
            "calculation_status": (
                specialist.get("calculation_status") if specialist else None
            ),
            "result": specialist.get("result") if specialist else {},
            "blockers": specialist.get("blockers") if specialist else [],
            "calculation_ref": _specialist_ref(kernel) if specialist else {},
        },
    }


def _caveat_blocker_posture(
    readiness: Mapping[str, Any],
    fap: Mapping[str, Any],
    author: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "readiness_status": readiness.get("final_readiness_status"),
        "fap_status": fap.get("fap_status"),
        "author_prose_status": author.get("author_prose_status"),
        "mandatory_caveats": _dedupe_text(
            [
                *(readiness.get("mandatory_caveats") or []),
                *(fap.get("mandatory_caveats") or []),
                *(author.get("mandatory_caveats") or []),
            ]
        ),
        "prohibited_upgrades": _dedupe_text(
            [
                *(readiness.get("prohibited_upgrades") or []),
                *(fap.get("prohibited_upgrades") or []),
                *(author.get("prohibited_upgrades") or []),
            ]
        ),
        "blockers": _dedupe_text(
            [
                *(readiness.get("blockers") or []),
                *(fap.get("blockers") or []),
                *(author.get("blockers") or []),
            ]
        ),
        "contested_posture_preserved": bool(
            readiness.get("final_readiness_status") == "contested"
            or fap.get("fap_status") == "contested_answer_packet"
            or author.get("contested_posture_preserved") is True
        ),
        "full_answer_implication_allowed": author.get(
            "full_answer_implication_allowed"
        ),
        "supported_claims_created": author.get("supported_claims_created"),
    }


def _current_path_outputs(chain: Mapping[str, Any], kernel: Any) -> dict[str, Any]:
    return {
        "search_result_candidate_packet": chain["candidate_packet"],
        "fetch_read_content_packet": chain["fetch_read_packet"],
        "evidence_ledger_projection": chain["ledger_projection"],
        "evidence_relative_analysis_packet": chain["analysis_packet"],
        "followup_search_intent_packet": chain.get("followup_packet") or {},
        "semantic_observation_admission_projection": (
            kernel.state.semantic_observation_admission_projection
        ),
        "component_coverage_projection": kernel.state.component_coverage_projection,
        "scrutineer_review_projection": kernel.state.scrutineer_review_projection,
        "specialist_source_bound_calculation_projection": (
            kernel.state.specialist_source_bound_calculation_projection
        ),
        "sufficiency_readiness_projection": (
            kernel.state.sufficiency_readiness_projection
        ),
        "final_answer_packet_projection": (
            kernel.state.final_answer_authority_projection
        ),
        "author_prose_projection": kernel.state.author_prose_projection,
    }


def _invoked_surface_names(kernel: Any) -> list[str]:
    names = [
        "build_search_result_candidate_packet_from_live_validation_state",
        "build_fetch_read_content_packet_from_candidate_packet",
        "reduce_fetch_read_content_packet_into_evidence_ledger",
        "build_evidence_relative_analysis_packet",
        "admit_semantic_observations_from_analysis_support_findings",
        "RunKernel.authorize_component_coverage_reduction",
        "RunKernel.reduce COMPONENT_COVERAGE_REDUCED",
        "reduce_sufficiency_readiness",
        "reduce_hardened_final_answer_packet",
        "reduce_author_prose_finalization",
    ]
    if kernel.state.scrutineer_review_projection:
        names.append("reduce_scrutineer_review")
    if kernel.state.specialist_source_bound_calculation_projection:
        names.append("reduce_specialist_source_bound_calculation")
    return names


def _component_statuses(readiness: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for component_id, entry in (readiness.get("component_readiness_map") or {}).items():
        if isinstance(entry, Mapping):
            result[str(component_id)] = str(entry.get("component_readiness_status"))
    return result


def _contract_summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": contract.get("accepted_contract_version"),
        "contract_digest": contract.get("accepted_contract_digest"),
        "component_ids": [
            component.get("component_id")
            for component in contract.get("accepted_answer_component_refs", [])
            if isinstance(component, Mapping)
        ],
        "component_count": contract.get("accepted_answer_component_count"),
    }


def _ledger_ref(chain: Mapping[str, Any]) -> dict[str, Any]:
    analysis_packet = chain.get("analysis_packet") or {}
    ref = dict(analysis_packet.get("evidence_ledger_ref") or {})
    if ref:
        return ref
    projection = chain.get("ledger_projection") or {}
    return _packet_like_ref(
        projection,
        id_keys=("ledger_id", "evidence_ledger_id"),
        digest_keys=("ledger_digest", "projection_digest"),
    )


def _semantic_admission_ref(kernel: Any) -> dict[str, Any]:
    projection = kernel.state.semantic_observation_admission_projection
    return _packet_like_ref(
        projection,
        id_keys=("admission_id", "observation_id"),
        digest_keys=("admission_digest", "observation_digest"),
    )


def _coverage_ref(kernel: Any) -> dict[str, Any]:
    projection = kernel.state.component_coverage_projection
    return _packet_like_ref(
        projection,
        id_keys=("coverage_state_id", "record_id", "coverage_record_id"),
        digest_keys=("coverage_digest", "record_digest"),
    )


def _readiness_ref(kernel: Any) -> dict[str, Any]:
    return _packet_like_ref(
        kernel.state.sufficiency_readiness_projection,
        id_keys=("readiness_id", "sufficiency_readiness_id"),
        digest_keys=("readiness_digest",),
    )


def _scrutineer_ref(kernel: Any) -> dict[str, Any]:
    return _packet_like_ref(
        kernel.state.scrutineer_review_projection,
        id_keys=("review_id",),
        digest_keys=("review_digest",),
    )


def _specialist_ref(kernel: Any) -> dict[str, Any]:
    return _packet_like_ref(
        kernel.state.specialist_source_bound_calculation_projection,
        id_keys=("calculation_id",),
        digest_keys=("calculation_digest",),
    )


def _author_prose_ref(kernel: Any) -> dict[str, Any]:
    return _packet_like_ref(
        kernel.state.author_prose_projection,
        id_keys=("author_prose_id",),
        digest_keys=("author_prose_digest",),
    )


def _packet_ref(packet: Mapping[str, Any] | None) -> dict[str, Any]:
    if not packet:
        return {}
    return _packet_like_ref(
        packet,
        id_keys=("packet_id",),
        digest_keys=("packet_digest",),
    )


def _packet_like_ref(
    value: Mapping[str, Any],
    *,
    id_keys: Sequence[str],
    digest_keys: Sequence[str],
) -> dict[str, Any]:
    if not value:
        return {}
    ref: dict[str, Any] = {}
    for key in id_keys:
        if value.get(key):
            ref["id"] = value[key]
            break
    for key in digest_keys:
        if value.get(key):
            ref["digest"] = value[key]
            break
    for key in ("owner", "schema_version", "status", "fap_status"):
        if value.get(key):
            ref[key] = value[key]
    return ref


def _not_applicable_reason(surface: str) -> str:
    reasons = {
        "FollowupSearchIntent / follow-up authorization": (
            "scenario does not require follow-up authorization"
        ),
        "ScrutineerReview": "scenario does not invoke Scrutineer posture",
        "Specialist source-bound calculation": (
            "scenario does not require source-bound calculation"
        ),
    }
    return reasons.get(surface, "surface not applicable for this scenario")


def _pick(value: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {key: value[key] for key in keys if key in value}


def _dedupe_text(values: Sequence[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _request_digest() -> str:
    payload = {
        "phase": PHASE,
        "request_id": DEFAULT_REQUEST_ID,
        "query": DEFAULT_QUERY,
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _write_json(path: Path, packet: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_safe(packet), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _packet_markdown(packet: Mapping[str, Any]) -> str:
    scenario = packet["scenario"]
    readiness = packet["sufficiency_readiness_status"]
    fap = packet["hardened_final_answer_packet_status"]
    author = packet["author_prose_output"]
    posture = packet["caveats_blockers_contested_posture"]
    surfaces = "\n".join(
        f"- {item['surface']}: {item['status']}"
        for item in packet["current_path_surfaces_consumed"]
    )
    non_proofs = "\n".join(f"- {item}" for item in packet["explicit_non_proofs"])
    caveats = "\n".join(
        f"- {item}" for item in posture.get("mandatory_caveats") or ["None recorded."]
    )
    return (
        f"# {scenario['title']}\n\n"
        f"Scenario id: `{scenario['scenario_id']}`\n\n"
        f"Proof class: {packet['proof_class']}\n\n"
        f"Product-facing progress type: {packet['product_facing_progress_type']}\n\n"
        "## Scenario\n\n"
        f"{scenario['description']}\n\n"
        "## Current Path Surfaces Consumed\n\n"
        f"{surfaces}\n\n"
        "## Readiness and FAP\n\n"
        f"- SufficiencyReadiness: `{readiness['final_readiness_status']}`\n"
        f"- Hardened FAP: `{fap['fap_status']}`\n\n"
        "## AuthorProse Output\n\n"
        f"Status: `{author['author_prose_status']}`\n\n"
        f"{author['answer_text']}\n\n"
        "## Caveats / Blockers / Contested Posture\n\n"
        f"{caveats}\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n"
    )


def _index_markdown(index: Mapping[str, Any]) -> str:
    rows = "\n".join(
        "- `{scenario_id}`: {author_prose_status} / {sufficiency_readiness_status} / {fap_status}".format(
            **packet
        )
        for packet in index["packets"]
    )
    non_proofs = "\n".join(f"- {item}" for item in index["explicit_non_proofs"])
    return (
        f"# {PHASE}\n\n"
        f"Proof class: {index['proof_class']}\n\n"
        f"Product-facing progress type: {index['product_facing_progress_type']}\n\n"
        "## Packets\n\n"
        f"{rows}\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n\n"
        f"Mandatory next checkpoint: `{index['mandatory_next_checkpoint']}`\n"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate AG-FIXTURE-DOGFOOD-INTEGRATION-01 reviewable "
            "AuthorProse dogfood packets from deterministic fixture scenarios."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Ignored/local output directory for JSON and Markdown packets.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        generated = generate_review_packets(output_dir=args.output_dir)
    except (FixtureDogfoodError, ValueError, KeyError) as exc:
        print(f"refusing AG-FIXTURE dogfood packet generation: {exc}", file=sys.stderr)
        return 2
    summary = {
        "phase": PHASE,
        "output_dir": str(Path(args.output_dir)),
        "packet_count": len(generated),
        "packets": [
            {
                "scenario_id": item.scenario_id,
                "json_path": str(item.json_path),
                "markdown_path": str(item.markdown_path),
            }
            for item in generated
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
