"""Bridge Analyst support findings into RunKernel SemanticObservation admission.

AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01 is intentionally not a new durable
packet.  It consumes an already validated EvidenceRelativeAnalysisPacket plus
bounded fetch/read content references, constructs the existing AG-SEM-02
SemanticObservation/SanitizedContentReference records, and admits them only
through the existing RunKernel authorization and reduction path.

The bridge does not create ComponentCoverage, source-obligation satisfaction,
citation eligibility, Sufficiency, FinalAnswerPacket material, Author input,
query plans, search dispatch, provider calls, broker calls, retrieval, models,
or product correctness. ComponentCoverage remains a separate reducer consumer
of the admitted observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.evidence_relative_analysis_packet import (
    EvidenceRelativeAnalysisPacketError,
    evidence_relative_analysis_packet_ref_from_packet,
    validate_evidence_relative_analysis_packet,
)
from core.fetch_read_content_reference import (
    FetchReadContentReferenceError,
    validate_fetch_read_content_packet,
)
from core.run_kernel import Observation, ObservationType, RunKernelTransitionError, RunStageStatus
from core.semantic_observation_foundation import (
    ContentKind,
    ObservationKind,
    SanitizedContentReference,
    SemanticObservation,
    SupportDirectness,
    SupportStatus,
)

SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER = (
    "semantic_observation_admission_bridge_ag_semantic_observation_admission_bridge_01"
)
SUPPORT_PROPOSAL_KIND = "possible_support_proposal"

_BLOCKER_FINDING_KINDS = frozenset(
    {
        "analysis_gap",
        "missing_fact",
        "possible_contradiction",
        "currentness_concern",
        "scope_mismatch",
    }
)

_CLOSED_DOWNSTREAM_FLAGS = {
    "component_coverage_created_by_bridge": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "author_called": False,
    "search_dispatched": False,
    "query_plan_created": False,
    "provider_called": False,
    "broker_called": False,
    "retrieval_executed": False,
    "model_called": False,
    "product_correctness_claimed": False,
}


class SemanticObservationAdmissionBridgeError(ValueError):
    """Raised when an Analyst support finding cannot be admitted safely."""


@dataclass(frozen=True, slots=True)
class SemanticObservationAdmissionBridgeResult:
    """Compact, non-durable result for one admitted support finding."""

    semantic_observation: SemanticObservation
    sanitized_content_reference: SanitizedContentReference
    admission_projection: Mapping[str, Any]
    analyst_finding: Mapping[str, Any]
    evidence_relative_analysis_packet_ref: Mapping[str, Any]
    accepted_contract_ref: Mapping[str, Any]
    current_answer_contract_ref: Mapping[str, Any]
    evidence_ledger_ref: Mapping[str, Any]
    fetch_read_candidate_custody_ref: Mapping[str, Any]
    fetch_read_content_packet_ref: Mapping[str, Any]
    source_obligation_candidate_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return compact lineage only; not a durable product packet."""

        return _compact(
            {
                "result_kind": "semantic_observation_admission_bridge_result",
                "durable_packet": False,
                "helper": SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER,
                "admitted_semantic_observation_id": (
                    self.semantic_observation.observation_id
                ),
                "admitted_semantic_observation_digest": (
                    self.semantic_observation.observation_digest
                ),
                "source_analyst_finding_id": self.analyst_finding.get("finding_id"),
                "source_analyst_finding_digest": self.analyst_finding.get(
                    "finding_digest"
                ),
                "component_id": self.semantic_observation.answer_component_id,
                "component_revision": self.semantic_observation.component_revision,
                "component_digest": (
                    self.semantic_observation.component_contract_digest
                ),
                "content_ref_id": self.sanitized_content_reference.content_ref_id,
                "content_digest": self.sanitized_content_reference.content_digest,
                "evidence_ref_id": self.sanitized_content_reference.evidence_ref_id,
                "candidate_id": self.analyst_finding.get("candidate_id"),
                "candidate_digest": self.analyst_finding.get("candidate_digest"),
                "reference_id": self.analyst_finding.get("reference_id"),
                "reference_digest": self.analyst_finding.get("reference_digest"),
                "evidence_relative_analysis_packet_ref": dict(
                    self.evidence_relative_analysis_packet_ref
                ),
                "accepted_contract_ref": dict(self.accepted_contract_ref),
                "current_answer_contract_ref": dict(self.current_answer_contract_ref),
                "evidence_ledger_ref": dict(self.evidence_ledger_ref),
                "fetch_read_candidate_custody_ref": dict(
                    self.fetch_read_candidate_custody_ref
                ),
                "fetch_read_content_packet_ref": dict(self.fetch_read_content_packet_ref),
                "source_obligation_candidate_ids": list(
                    self.source_obligation_candidate_ids
                ),
                "source_obligation_candidate_ids_are_lineage_only": True,
                "admission_action_id": self.admission_projection.get(
                    "authorized_action_id"
                ),
                "admission_status": "admitted",
                "component_coverage_consumer_expected": True,
                "component_coverage_created_by_bridge": False,
                "closed_downstream_flags": dict(_CLOSED_DOWNSTREAM_FLAGS),
            }
        )


def admit_semantic_observations_from_analysis_support_findings(
    *,
    run_kernel: Any,
    evidence_relative_analysis_packet: Mapping[str, Any],
    fetch_read_content_packet: Mapping[str, Any],
    finding_ids: Sequence[str] = (),
) -> tuple[SemanticObservationAdmissionBridgeResult, ...]:
    """Admit eligible Analyst support findings through RunKernel.

    Non-support findings are not silently promoted when explicitly requested by
    ``finding_ids``. Without an explicit selection they are ignored, and the
    helper admits only eligible source-bound support findings.
    """

    analysis_packet = _validate_analysis_packet(evidence_relative_analysis_packet)
    fetch_packet = _validate_fetch_packet(fetch_read_content_packet)
    evidence_ledger_projection = _evidence_ledger_projection(run_kernel)
    accepted_contract = _accepted_contract(run_kernel)
    current_contract = _current_contract(run_kernel)
    current_contract_ref = _required_current_contract_ref(
        analysis_packet,
        current_contract=current_contract,
    )
    accepted_contract_ref = _accepted_contract_ref(accepted_contract)
    _require_run_request_match(
        analysis_packet=analysis_packet,
        fetch_read_packet=fetch_packet,
        run_kernel=run_kernel,
    )

    finding_index = {
        str(finding.get("finding_id") or ""): dict(finding)
        for finding in _report_findings(analysis_packet)
        if finding.get("finding_id")
    }
    selected_ids = tuple(_clean_token(item, limit=320) for item in finding_ids)
    selected_ids = tuple(item for item in selected_ids if item)
    if selected_ids:
        unknown = [item for item in selected_ids if item not in finding_index]
        if unknown:
            raise SemanticObservationAdmissionBridgeError(
                "unknown Analyst finding id(s): " + ", ".join(unknown)
            )
        findings = [finding_index[item] for item in selected_ids]
    else:
        findings = [dict(item) for item in _report_findings(analysis_packet)]

    references = _fetch_read_references_by_id(fetch_packet)
    custody_records = _custody_records_by_reference(evidence_ledger_projection)
    results: list[SemanticObservationAdmissionBridgeResult] = []
    rejected: list[str] = []
    for finding in findings:
        try:
            result = _admit_one(
                run_kernel=run_kernel,
                finding=finding,
                analysis_packet=analysis_packet,
                fetch_read_packet=fetch_packet,
                references=references,
                custody_records=custody_records,
                accepted_contract=accepted_contract,
                accepted_contract_ref=accepted_contract_ref,
                current_contract=current_contract,
                current_contract_ref=current_contract_ref,
                evidence_ledger_projection=evidence_ledger_projection,
            )
        except SemanticObservationAdmissionBridgeError as exc:
            if selected_ids:
                raise
            rejected.append(str(exc))
            continue
        results.append(result)
    if not results:
        detail = "; ".join(rejected) if rejected else "no findings supplied"
        raise SemanticObservationAdmissionBridgeError(
            "no eligible Analyst support findings for SemanticObservation "
            f"admission: {detail}"
        )
    return tuple(results)


def _admit_one(
    *,
    run_kernel: Any,
    finding: Mapping[str, Any],
    analysis_packet: Mapping[str, Any],
    fetch_read_packet: Mapping[str, Any],
    references: Mapping[str, Mapping[str, Any]],
    custody_records: Mapping[str, Mapping[str, Any]],
    accepted_contract: Mapping[str, Any],
    accepted_contract_ref: Mapping[str, Any],
    current_contract: Mapping[str, Any],
    current_contract_ref: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
) -> SemanticObservationAdmissionBridgeResult:
    _require_support_finding_eligible(finding)
    reference_id = _required_token(
        finding.get("reference_id"),
        "support finding requires reference_id",
        limit=320,
    )
    reference = _required_bound_reference(
        finding=finding,
        fetch_read_packet=fetch_read_packet,
        references=references,
    )
    custody_record = _required_readable_custody_record(
        finding=finding,
        custody_records=custody_records,
    )
    component_ref = _component_ref_for_finding(
        finding=finding,
        accepted_contract=accepted_contract,
        current_contract=current_contract,
    )
    content_ref = _content_reference_from_finding(
        finding=finding,
        reference=reference,
        accepted_contract=accepted_contract,
        component_ref=component_ref,
        analysis_packet=analysis_packet,
        current_contract_ref=current_contract_ref,
        custody_record=custody_record,
    )
    observation = _semantic_observation_from_finding(
        finding=finding,
        content_ref=content_ref,
        accepted_contract=accepted_contract,
        component_ref=component_ref,
        analysis_packet=analysis_packet,
        current_contract_ref=current_contract_ref,
    )
    action = run_kernel.authorize_semantic_observation_admission(
        semantic_observation_id=observation.observation_id,
        semantic_observation_digest=observation.observation_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        inputs={
            "semantic_observation_admission_bridge": (
                SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER
            ),
            "evidence_relative_analysis_packet_id": analysis_packet.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_packet.get(
                "packet_digest"
            ),
            "analyst_report_id": _safe_mapping(
                analysis_packet.get("analyst_report")
            ).get("report_id"),
            "analyst_report_digest": _safe_mapping(
                analysis_packet.get("analyst_report")
            ).get("report_digest"),
            "analyst_finding_id": finding.get("finding_id"),
            "analyst_finding_digest": finding.get("finding_digest"),
            "current_answer_contract_ref": dict(current_contract_ref),
            "current_answer_contract_digest": current_contract_ref.get(
                "contract_digest"
            ),
            "fetch_read_content_packet_id": fetch_read_packet.get("packet_id"),
            "fetch_read_content_packet_digest": fetch_read_packet.get(
                "packet_digest"
            ),
            "content_ref_id": content_ref.content_ref_id,
            "content_digest": content_ref.content_digest,
            "reference_id": reference_id,
            "reference_digest": finding.get("reference_digest"),
            "candidate_id": finding.get("candidate_id"),
            "candidate_digest": finding.get("candidate_digest"),
            "source_obligation_candidate_ids": list(
                _text_tuple(finding.get("source_obligation_candidate_ids"), limit=260)
            ),
            "source_obligation_candidate_ids_are_lineage_only": True,
        },
    )
    try:
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
                status=RunStageStatus.COMPLETED,
                payload={
                    "semantic_observation": observation.to_dict(),
                    "sanitized_content_references": [content_ref.to_dict()],
                },
            )
        )
    except RunKernelTransitionError as exc:
        raise SemanticObservationAdmissionBridgeError(str(exc)) from exc

    admission_projection = dict(run_kernel.state.semantic_observation_admission_projection)
    return SemanticObservationAdmissionBridgeResult(
        semantic_observation=observation,
        sanitized_content_reference=content_ref,
        admission_projection=admission_projection,
        analyst_finding=dict(finding),
        evidence_relative_analysis_packet_ref=(
            evidence_relative_analysis_packet_ref_from_packet(analysis_packet)
        ),
        accepted_contract_ref=dict(accepted_contract_ref),
        current_answer_contract_ref=dict(current_contract_ref),
        evidence_ledger_ref=dict(analysis_packet.get("evidence_ledger_ref") or {}),
        fetch_read_candidate_custody_ref=dict(
            analysis_packet.get("fetch_read_candidate_custody_ref") or {}
        ),
        fetch_read_content_packet_ref={
            "packet_id": fetch_read_packet.get("packet_id"),
            "packet_digest": fetch_read_packet.get("packet_digest"),
            "reference_id": reference_id,
            "reference_digest": finding.get("reference_digest"),
        },
        source_obligation_candidate_ids=_text_tuple(
            finding.get("source_obligation_candidate_ids"),
            limit=260,
        ),
    )


def _validate_analysis_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_evidence_relative_analysis_packet(packet)
    except EvidenceRelativeAnalysisPacketError as exc:
        raise SemanticObservationAdmissionBridgeError(str(exc)) from exc


def _validate_fetch_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_fetch_read_content_packet(packet)
    except FetchReadContentReferenceError as exc:
        raise SemanticObservationAdmissionBridgeError(str(exc)) from exc


def _evidence_ledger_projection(run_kernel: Any) -> dict[str, Any]:
    ledger = getattr(getattr(run_kernel, "state", None), "evidence_ledger", None)
    if ledger is None or not hasattr(ledger, "to_projection"):
        raise SemanticObservationAdmissionBridgeError(
            "bridge requires RunKernel EvidenceLedger projection"
        )
    projection = ledger.to_projection().to_dict()
    if not isinstance(projection, Mapping):
        raise SemanticObservationAdmissionBridgeError(
            "bridge requires mapping EvidenceLedger projection"
        )
    return dict(projection)


def _accepted_contract(run_kernel: Any) -> dict[str, Any]:
    state = getattr(run_kernel, "state", None)
    accepted = _safe_mapping(getattr(state, "initial_answer_contract", None))
    projection = _safe_mapping(
        getattr(state, "initial_answer_contract_projection", None)
    )
    if not accepted or not projection:
        raise SemanticObservationAdmissionBridgeError(
            "bridge requires an accepted initial answer contract"
        )
    return accepted


def _current_contract(run_kernel: Any) -> dict[str, Any]:
    return _safe_mapping(getattr(getattr(run_kernel, "state", None), "current_answer_contract", None))


def _required_current_contract_ref(
    analysis_packet: Mapping[str, Any],
    *,
    current_contract: Mapping[str, Any],
) -> dict[str, Any]:
    ref = _safe_mapping(analysis_packet.get("current_answer_contract_ref"))
    digest = _clean_token(
        analysis_packet.get("current_answer_contract_digest"),
        limit=128,
    )
    if not ref or not digest:
        raise SemanticObservationAdmissionBridgeError(
            "bridge requires current_answer_contract ref and digest lineage"
        )
    if ref.get("contract_digest") != digest:
        raise SemanticObservationAdmissionBridgeError(
            "analysis packet current_answer_contract digest mismatch"
        )
    if current_contract:
        current_digest = _clean_token(
            current_contract.get("accepted_contract_digest"),
            limit=128,
        )
        current_version = _clean_token(
            current_contract.get("accepted_contract_version"),
            limit=160,
        )
        if digest != current_digest:
            raise SemanticObservationAdmissionBridgeError(
                "analysis packet current_answer_contract digest does not match "
                "RunKernel current_answer_contract"
            )
        if ref.get("contract_version") != current_version:
            raise SemanticObservationAdmissionBridgeError(
                "analysis packet current_answer_contract version does not match "
                "RunKernel current_answer_contract"
            )
    return ref


def _accepted_contract_ref(accepted_contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": "accepted_initial_answer_contract",
        "contract_version": accepted_contract.get("accepted_contract_version"),
        "contract_digest": accepted_contract.get("accepted_contract_digest"),
    }


def _require_run_request_match(
    *,
    analysis_packet: Mapping[str, Any],
    fetch_read_packet: Mapping[str, Any],
    run_kernel: Any,
) -> None:
    state = getattr(run_kernel, "state", None)
    run_id = _clean_token(getattr(state, "run_id", None), limit=160)
    request_id = _clean_token(getattr(state, "request_id", None), limit=160)
    for label, value in (
        ("analysis packet run_id", analysis_packet.get("run_id")),
        ("fetch/read packet run_id", fetch_read_packet.get("run_id")),
    ):
        if _clean_token(value, limit=160) != run_id:
            raise SemanticObservationAdmissionBridgeError(
                f"{label} does not match RunKernel run_id"
            )
    for label, value in (
        ("analysis packet request_id", analysis_packet.get("request_id")),
        ("fetch/read packet request_id", fetch_read_packet.get("request_id")),
    ):
        if _clean_token(value, limit=160) != request_id:
            raise SemanticObservationAdmissionBridgeError(
                f"{label} does not match RunKernel request_id"
            )


def _report_findings(packet: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    report = _safe_mapping(packet.get("analyst_report"))
    return tuple(
        dict(item)
        for item in report.get("findings") or ()
        if isinstance(item, Mapping)
    )


def _fetch_read_references_by_id(
    fetch_read_packet: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    references: dict[str, Mapping[str, Any]] = {}
    for reference in fetch_read_packet.get("reference_records") or ():
        if not isinstance(reference, Mapping):
            continue
        reference_id = _clean_token(reference.get("reference_id"), limit=320)
        if reference_id:
            references[reference_id] = dict(reference)
    return references


def _custody_records_by_reference(
    evidence_ledger_projection: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    custody = _safe_mapping(evidence_ledger_projection.get("fetch_read_candidate_custody"))
    records: dict[str, Mapping[str, Any]] = {}
    for record in custody.get("fetch_read_candidate_custody_records") or ():
        if not isinstance(record, Mapping):
            continue
        reference_id = _clean_token(record.get("reference_id"), limit=320)
        if reference_id:
            records[reference_id] = dict(record)
    return records


def _require_support_finding_eligible(finding: Mapping[str, Any]) -> None:
    kind = _clean_token(finding.get("proposal_kind"), limit=120)
    if kind != SUPPORT_PROPOSAL_KIND:
        if kind in _BLOCKER_FINDING_KINDS:
            raise SemanticObservationAdmissionBridgeError(
                f"{kind} is a blocker/proposal finding, not admission support"
            )
        raise SemanticObservationAdmissionBridgeError(
            f"{kind or 'missing proposal_kind'} is not eligible for admission"
        )
    for key in (
        "finding_id",
        "finding_digest",
        "candidate_id",
        "candidate_digest",
        "reference_id",
        "reference_digest",
        "fetch_read_content_packet_digest",
        "search_result_candidate_packet_digest",
        "component_id",
    ):
        if not _clean_token(finding.get(key), limit=320):
            raise SemanticObservationAdmissionBridgeError(
                f"support finding requires {key}"
            )
    if finding.get("contradicts_reference_id") or finding.get("contradicts_finding_id"):
        raise SemanticObservationAdmissionBridgeError(
            "support finding carries unresolved contradiction linkage"
        )
    flags = _safe_mapping(finding.get("closed_surface_flags"))
    for key in (
        "semantic_observation_admitted",
        "component_coverage_created",
        "source_obligation_satisfied",
        "citation_eligible",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "product_correctness_claimed",
    ):
        if finding.get(key) is not False or flags.get(key) is not False:
            raise SemanticObservationAdmissionBridgeError(
                f"support finding opens closed surface {key}"
            )


def _required_bound_reference(
    *,
    finding: Mapping[str, Any],
    fetch_read_packet: Mapping[str, Any],
    references: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    reference_id = _required_token(
        finding.get("reference_id"),
        "support finding requires reference_id",
        limit=320,
    )
    reference = references.get(reference_id)
    if reference is None:
        raise SemanticObservationAdmissionBridgeError(
            "support finding has no matching FetchReadContentPacket reference"
        )
    _require_equal(
        fetch_read_packet.get("packet_digest"),
        finding.get("fetch_read_content_packet_digest"),
        "fetch/read packet digest mismatch",
    )
    if finding.get("fetch_read_content_packet_id"):
        _require_equal(
            fetch_read_packet.get("packet_id"),
            finding.get("fetch_read_content_packet_id"),
            "fetch/read packet id mismatch",
        )
    for key in (
        "candidate_id",
        "candidate_digest",
        "reference_digest",
        "search_result_candidate_packet_digest",
        "search_result_candidate_record_digest",
    ):
        _require_equal(reference.get(key), finding.get(key), f"{key} mismatch")
    if reference.get("fetch_read_status") != "readable":
        raise SemanticObservationAdmissionBridgeError(
            "support finding requires readable FetchReadContentPacket reference"
        )
    if not reference.get("bounded_text") or reference.get("bounded_text_sanitized") is not True:
        raise SemanticObservationAdmissionBridgeError(
            "support finding requires matching bounded sanitized content"
        )
    if reference.get("bounded_text_bounded") is not True:
        raise SemanticObservationAdmissionBridgeError(
            "support finding requires explicitly bounded content"
        )
    if _clean_token(reference.get("excerpt_digest"), limit=128) != _clean_token(
        finding.get("excerpt_digest"),
        limit=128,
    ):
        raise SemanticObservationAdmissionBridgeError(
            "support finding excerpt digest does not match bounded content"
        )
    return reference


def _required_readable_custody_record(
    *,
    finding: Mapping[str, Any],
    custody_records: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    reference_id = _required_token(
        finding.get("reference_id"),
        "support finding requires reference_id",
        limit=320,
    )
    record = custody_records.get(reference_id)
    if record is None:
        raise SemanticObservationAdmissionBridgeError(
            "support finding has no readable EvidenceLedger custody record"
        )
    for key in (
        "candidate_id",
        "candidate_digest",
        "reference_id",
        "reference_digest",
        "fetch_read_content_packet_digest",
        "search_result_candidate_packet_digest",
    ):
        _require_equal(record.get(key), finding.get(key), f"custody {key} mismatch")
    if record.get("fetch_read_status") != "readable":
        raise SemanticObservationAdmissionBridgeError(
            "support finding EvidenceLedger custody is not readable"
        )
    if not record.get("bounded_content_present"):
        raise SemanticObservationAdmissionBridgeError(
            "support finding EvidenceLedger custody lacks bounded content"
        )
    return record


def _component_ref_for_finding(
    *,
    finding: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    current_contract: Mapping[str, Any],
) -> Mapping[str, Any]:
    component_id = _required_token(
        finding.get("component_id"),
        "support finding requires component_id",
        limit=260,
    )
    accepted_component = _component_by_id(accepted_contract, component_id)
    if accepted_component is None:
        raise SemanticObservationAdmissionBridgeError(
            "support finding component is not in the accepted answer contract"
        )
    if current_contract:
        current_component = _component_by_id(current_contract, component_id)
        if current_component is None:
            raise SemanticObservationAdmissionBridgeError(
                "support finding component is not in current_answer_contract"
            )
        for key in ("component_revision", "component_digest"):
            if _clean_token(accepted_component.get(key), limit=128) != _clean_token(
                current_component.get(key),
                limit=128,
            ):
                raise SemanticObservationAdmissionBridgeError(
                    "current and accepted answer contract component lineage mismatch"
                )
    for key in ("component_revision", "component_digest"):
        if not _clean_token(accepted_component.get(key), limit=128):
            raise SemanticObservationAdmissionBridgeError(
                f"accepted answer component requires {key}"
            )
    return dict(accepted_component)


def _content_reference_from_finding(
    *,
    finding: Mapping[str, Any],
    reference: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    analysis_packet: Mapping[str, Any],
    current_contract_ref: Mapping[str, Any],
    custody_record: Mapping[str, Any],
) -> SanitizedContentReference:
    metadata = _lineage_metadata(
        finding=finding,
        analysis_packet=analysis_packet,
        current_contract_ref=current_contract_ref,
        custody_record=custody_record,
    )
    return SanitizedContentReference(
        content_ref_id=str(reference["reference_id"]),
        evidence_ref_id=str(reference["candidate_id"]),
        admitted_evidence_ref=str(reference["candidate_id"]),
        source_id=f"source:{reference.get('candidate_domain')}",
        source_digest=str(reference["reference_digest"]),
        source_url=(
            reference.get("resolved_url")
            or reference.get("final_url")
            or reference.get("canonical_url")
            or reference.get("candidate_url")
        ),
        source_title=reference.get("content_title") or reference.get("candidate_title"),
        source_domain=reference.get("resolved_domain") or reference.get(
            "candidate_domain"
        ),
        answer_component_id=str(component_ref["component_id"]),
        component_revision=str(component_ref["component_revision"]),
        component_contract_digest=str(component_ref["component_digest"]),
        question_meaning_record_id=str(
            accepted_contract["parent_question_meaning_record_id"]
        ),
        question_meaning_record_digest=str(
            accepted_contract["parent_question_meaning_record_digest"]
        ),
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text=str(reference["bounded_text"]),
        extraction_method=SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER,
        worker_kind="analyst_support_finding_admission_bridge",
        currentness="bounded_fixture_currentness_unclaimed",
        observed_at=reference.get("retrieved_or_observed_at"),
        metadata=metadata,
    ).require_valid()


def _semantic_observation_from_finding(
    *,
    finding: Mapping[str, Any],
    content_ref: SanitizedContentReference,
    accepted_contract: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    analysis_packet: Mapping[str, Any],
    current_contract_ref: Mapping[str, Any],
) -> SemanticObservation:
    finding_digest = _required_token(
        finding.get("finding_digest"),
        "support finding requires finding_digest",
        limit=128,
    )
    observation_id = (
        "semantic-observation:analysis-bridge:"
        f"{finding_digest[:16]}:{content_ref.content_digest[:16]}"
    )
    claim = (
        _clean_text(finding.get("proposal_summary"), limit=240)
        or "Analyst support finding admitted from bounded sanitized content."
    )
    return SemanticObservation(
        observation_id=observation_id,
        observation_kind=ObservationKind.SUPPORT,
        question_meaning_record_id=str(
            accepted_contract["parent_question_meaning_record_id"]
        ),
        question_meaning_record_digest=str(
            accepted_contract["parent_question_meaning_record_digest"]
        ),
        contract_version=str(accepted_contract["accepted_contract_version"]),
        contract_digest=str(accepted_contract["accepted_contract_digest"]),
        answer_component_id=str(component_ref["component_id"]),
        component_revision=str(component_ref["component_revision"]),
        component_contract_digest=str(component_ref["component_digest"]),
        evidence_refs=(content_ref.evidence_ref_id,),
        content_refs=(content_ref.content_ref_id,),
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=SupportStatus.SUPPORTS,
        claim_or_value=claim,
        normalization_fit="direct bounded sanitized source reference",
        scope_fit="accepted answer contract component",
        assumption_fit="no computation; source-obligation ids remain lineage only",
        inference_depth=0,
        candidate_caveats=(
            "Source-obligation candidate IDs remain lineage only.",
            "SemanticObservation admission does not create citation eligibility.",
        ),
        candidate_followup_gaps=(
            "Blocked/follow-up gap to ComponentCoverage blocker lineage remains downstream.",
        ),
        candidate_contract_amendment_notes=(
            "No current_answer_contract mutation is created by this bridge.",
        ),
        metadata=_lineage_metadata(
            finding=finding,
            analysis_packet=analysis_packet,
            current_contract_ref=current_contract_ref,
            custody_record={},
        ),
    ).require_valid(content_references=(content_ref,))


def _lineage_metadata(
    *,
    finding: Mapping[str, Any],
    analysis_packet: Mapping[str, Any],
    current_contract_ref: Mapping[str, Any],
    custody_record: Mapping[str, Any],
) -> dict[str, Any]:
    report = _safe_mapping(analysis_packet.get("analyst_report"))
    metadata = {
        "phase": "AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01",
        "helper": SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER,
        "evidence_relative_analysis_packet_id": analysis_packet.get("packet_id"),
        "evidence_relative_analysis_packet_digest": analysis_packet.get(
            "packet_digest"
        ),
        "analyst_report_id": report.get("report_id"),
        "analyst_report_digest": report.get("report_digest"),
        "analyst_finding_id": finding.get("finding_id"),
        "analyst_finding_digest": finding.get("finding_digest"),
        "current_answer_contract_version": current_contract_ref.get(
            "contract_version"
        ),
        "current_answer_contract_digest": current_contract_ref.get("contract_digest"),
        "candidate_id": finding.get("candidate_id"),
        "candidate_digest": finding.get("candidate_digest"),
        "reference_id": finding.get("reference_id"),
        "reference_digest": finding.get("reference_digest"),
        "fetch_read_content_packet_id": finding.get("fetch_read_content_packet_id"),
        "fetch_read_content_packet_digest": finding.get(
            "fetch_read_content_packet_digest"
        ),
        "search_result_candidate_packet_id": finding.get(
            "search_result_candidate_packet_id"
        ),
        "search_result_candidate_packet_digest": finding.get(
            "search_result_candidate_packet_digest"
        ),
        "search_result_candidate_record_digest": finding.get(
            "search_result_candidate_record_digest"
        ),
        "evidence_ledger_projection_digest": analysis_packet.get(
            "evidence_ledger_projection_digest"
        ),
        "fetch_read_candidate_custody_projection_digest": _safe_mapping(
            finding.get("evidence_ledger_custody_projection_ref")
        ).get("projection_digest"),
        "source_obligation_candidate_ids": list(
            _text_tuple(finding.get("source_obligation_candidate_ids"), limit=260)
        ),
        "source_obligation_candidate_ids_are_lineage_only": True,
    }
    if custody_record:
        metadata["custody_reference_id"] = custody_record.get("reference_id")
        metadata["custody_reference_digest"] = custody_record.get("reference_digest")
    return _compact(metadata)


def _component_by_id(
    contract: Mapping[str, Any],
    component_id: str,
) -> Mapping[str, Any] | None:
    for component in contract.get("accepted_answer_component_refs") or ():
        if not isinstance(component, Mapping):
            continue
        if _clean_token(component.get("component_id"), limit=260) == component_id:
            return component
    return None


def _require_equal(left: Any, right: Any, message: str) -> None:
    if _clean_token(left, limit=320) != _clean_token(right, limit=320):
        raise SemanticObservationAdmissionBridgeError(message)


def _required_token(value: Any, message: str, *, limit: int = 160) -> str:
    token = _clean_token(value, limit=limit)
    if not token:
        raise SemanticObservationAdmissionBridgeError(message)
    return token


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    return _clean_text(value, limit=limit)


def _text_tuple(value: Any, *, limit: int = 160) -> tuple[str, ...]:
    if isinstance(value, str):
        token = _clean_token(value, limit=limit)
        return (token,) if token else ()
    if not isinstance(value, Sequence) or isinstance(value, bytes):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _clean_token(item, limit=limit)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return tuple(out)


def _compact(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }


__all__ = [
    "SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER",
    "SUPPORT_PROPOSAL_KIND",
    "SemanticObservationAdmissionBridgeError",
    "SemanticObservationAdmissionBridgeResult",
    "admit_semantic_observations_from_analysis_support_findings",
]
