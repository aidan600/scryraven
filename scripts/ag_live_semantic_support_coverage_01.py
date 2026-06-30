from __future__ import annotations

import argparse
import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.component_coverage_record import (  # noqa: E402
    ComponentCoverageRecord,
    ContentAvailabilityStatus,
    ContentReferenceCoverageBinding,
    CoverageLineage,
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
from core.evidence_ledger import EVIDENCE_LEDGER_SCHEMA_VERSION  # noqa: E402
from core.evidence_relative_analysis_packet import (  # noqa: E402
    EvidenceRelativeAnalysisPacketError,
    build_evidence_relative_analysis_packet,
    evidence_relative_analysis_packet_ref_from_packet,
)
from core.fetch_read_content_reference import (  # noqa: E402
    FetchReadContentReferenceError,
    validate_fetch_read_content_packet,
)
from core.run_kernel import (  # noqa: E402
    Observation,
    ObservationType,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.semantic_observation_admission_bridge import (  # noqa: E402
    SemanticObservationAdmissionBridgeError,
    SemanticObservationAdmissionBridgeResult,
    admit_semantic_observations_from_analysis_support_findings,
)

PHASE = "AG-LIVE-SEMANTIC-SUPPORT-COVERAGE-01"
MODE = "PROOF"
USABLE_ANSWER_VERDICT_TARGET = "NO-BUT-JUSTIFIED"
PROOF_CLASS = "live_component_proof"
PRODUCT_FACING_PROGRESS_TYPE = (
    "live component proof over already-custodied bounded content; standalone "
    "review harness only"
)
PRIOR_358_REF = "PR #358"
DEFAULT_INPUT_DIR = ROOT / "output" / "ag_live_source_survival_fetch_read_custody_01"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "ag_live_semantic_support_coverage_01"
DEFAULT_SOURCE_SURVIVAL_PACKET = DEFAULT_INPUT_DIR / "source_survival_packet.json"
DEFAULT_FETCH_READ_CONTENT_PACKET = DEFAULT_INPUT_DIR / "fetch_read_content_packet.json"
DEFAULT_SANITIZED_CONTENT_REFERENCE = DEFAULT_INPUT_DIR / "sanitized_content_reference.json"
DEFAULT_EVIDENCE_LEDGER_PROJECTION = DEFAULT_INPUT_DIR / "evidence_ledger_projection.json"

REQUEST_PACKET_NAME = "request_packet.json"
REQUEST_MARKDOWN_NAME = "request_packet.md"
RESULT_PACKET_NAME = "semantic_support_coverage_packet.json"
RESULT_MARKDOWN_NAME = "semantic_support_coverage_packet.md"
ANALYSIS_PACKET_NAME = "evidence_relative_analysis_packet.json"
SEMANTIC_PROJECTION_NAME = "semantic_observation_projection.json"
COVERAGE_PROJECTION_NAME = "component_coverage_projection.json"

TARGET_COMPONENT_ID = "component:adult-us-passport-book-renewal-fee"
TARGET_COMPONENT_TEXT = "adult U.S. passport book renewal fee"
TARGET_COMPONENT_CLAIM_UNDER_TEST = "adult U.S. passport book renewal fee is $130"
REQUIRED_DOMAIN = "travel.state.gov"
MANDATORY_NEXT_BUILD_PRODUCT_CHECKPOINT = (
    "If this phase passes, next phase should be Build-mode live-supported "
    "SufficiencyReadiness -> hardened FinalAnswerPacket -> AuthorProse "
    "reviewable answer packet, still with citation/source-obligation posture "
    "explicitly licensed or still closed as appropriate. If this phase fails, "
    "next phase should be a targeted REPAIR of the first broken semantic-support "
    "or ComponentCoverage seam."
)

SEMANTIC_SUPPORT_RESULTS = frozenset(
    {
        "semantic_support_coverage_pass",
        "semantic_support_partial",
        "semantic_support_fail_source_content_insufficient",
        "semantic_support_fail_analysis_packet",
        "semantic_support_fail_semantic_observation_admission",
        "semantic_support_fail_component_coverage",
        "validation_not_run_operator_blocked",
        "validation_inconclusive",
    }
)

OPENED_SURFACES = [
    "loading #358 source-survival output",
    "validating prior source survival/custody state",
    "evidence-relative analysis/proposal over bounded sanitized content only",
    "RunKernel SemanticObservation admission",
    "ComponentCoverage reduction",
    "reviewable semantic-support packet",
]

CLOSED_SURFACES = [
    "live provider/search/broker",
    "live fetch/read",
    "model calls",
    "broad retrieval",
    "raw HTML/raw headers/raw cookies/raw page text",
    "new source acquisition",
    "source-obligation satisfaction",
    "citation eligibility/rendering",
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "Author/AuthorProse",
    "answer text",
    "product correctness",
    "product-quality prose",
]

EXPLICIT_NON_PROOFS = [
    "source-obligation satisfaction",
    "citation eligibility",
    "citation rendering",
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "Author or AuthorProse behavior",
    "answer text",
    "answer correctness or product correctness",
    "product-quality prose",
]

ZERO_CALL_COUNTS = {
    "provider_search_calls": 0,
    "broker_calls": 0,
    "fetch_read_calls": 0,
    "model_calls": 0,
    "retrieval_calls": 0,
}

RAW_RETENTION_FLAGS = {
    "raw_html_retained": False,
    "raw_response_headers_retained": False,
    "raw_cookies_retained": False,
    "raw_page_text_retained": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
}

_SAFE_FALSE_KEYS = frozenset(
    {
        *RAW_RETENTION_FLAGS,
        "citation_eligible",
        "citation_created",
        "source_obligation_satisfied",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "product_correctness_claimed",
    }
)

_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "answer",
        "answer_text",
        "author",
        "author_input",
        "author_material",
        "authorization",
        "body",
        "cache",
        "citations",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "fap",
        "final_answer",
        "final_answer_packet",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_headers",
        "raw_html",
        "raw_model_response",
        "raw_page_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "source_obligation_satisfaction",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "author_input_created",
        "citation_created",
        "citation_eligible",
        "final_answer_packet_created",
        "product_correctness_claimed",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
)


class SemanticSupportCoverageError(ValueError):
    def __init__(self, code: str, message: str | None = None, *, gate: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.gate = gate


def prepare_request(
    *,
    source_survival_packet_path: str | Path = DEFAULT_SOURCE_SURVIVAL_PACKET,
    fetch_read_content_packet_path: str | Path = DEFAULT_FETCH_READ_CONTENT_PACKET,
    sanitized_content_reference_path: str | Path = DEFAULT_SANITIZED_CONTENT_REFERENCE,
    evidence_ledger_projection_path: str | Path = DEFAULT_EVIDENCE_LEDGER_PROJECTION,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    context = _load_and_validate_inputs(
        source_survival_packet_path=source_survival_packet_path,
        fetch_read_content_packet_path=fetch_read_content_packet_path,
        sanitized_content_reference_path=sanitized_content_reference_path,
        evidence_ledger_projection_path=evidence_ledger_projection_path,
    )
    target = _phase_output_dir(output_dir)
    packet = _base_packet(
        context=context,
        output_dir=target,
        semantic_support_result="validation_not_run_operator_blocked",
        first_failed_gate="operator_pending_confirm_semantic_coverage",
        semantic_observation_attempted_count=0,
        semantic_observation_admitted_count=0,
        component_coverage_attempted_count=0,
        component_coverage_reduced_count=0,
    )
    packet.update(
        {
            "packet_kind": "semantic_support_coverage_request_packet",
            "request_generation_does_not_reduce_semantic_coverage": True,
            "reduce_semantic_coverage_requires_confirm_semantic_coverage": True,
            "operator_command": _operator_command(
                source_survival_packet_path=source_survival_packet_path,
                fetch_read_content_packet_path=fetch_read_content_packet_path,
                sanitized_content_reference_path=sanitized_content_reference_path,
                evidence_ledger_projection_path=evidence_ledger_projection_path,
                output_dir=target,
            ),
        }
    )
    validate_review_packet(packet)
    _write_json(target / REQUEST_PACKET_NAME, packet)
    (target / REQUEST_MARKDOWN_NAME).write_text(_request_markdown(packet), encoding="utf-8")
    return packet


def reduce_semantic_coverage(
    *,
    source_survival_packet_path: str | Path = DEFAULT_SOURCE_SURVIVAL_PACKET,
    fetch_read_content_packet_path: str | Path = DEFAULT_FETCH_READ_CONTENT_PACKET,
    sanitized_content_reference_path: str | Path = DEFAULT_SANITIZED_CONTENT_REFERENCE,
    evidence_ledger_projection_path: str | Path = DEFAULT_EVIDENCE_LEDGER_PROJECTION,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    confirm_semantic_coverage: bool = False,
    run_kernel: Any | None = None,
) -> dict[str, Any]:
    if not confirm_semantic_coverage:
        raise SemanticSupportCoverageError(
            "confirm_semantic_coverage_required",
            "reduce-semantic-coverage requires --confirm-semantic-coverage",
            gate="operator_confirmation",
        )
    context = _load_and_validate_inputs(
        source_survival_packet_path=source_survival_packet_path,
        fetch_read_content_packet_path=fetch_read_content_packet_path,
        sanitized_content_reference_path=sanitized_content_reference_path,
        evidence_ledger_projection_path=evidence_ledger_projection_path,
    )
    target = _phase_output_dir(output_dir)
    result = "validation_inconclusive"
    first_failed_gate: str | None = None
    failure_reason: str | None = None
    analysis_packet: dict[str, Any] | None = None
    bridge_result: SemanticObservationAdmissionBridgeResult | None = None
    coverage_projection: dict[str, Any] | None = None
    semantic_attempted = 0
    semantic_admitted = 0
    coverage_attempted = 0
    coverage_reduced = 0

    try:
        proposal = _source_bound_support_proposal(context)
        if proposal is None:
            result = "semantic_support_fail_source_content_insufficient"
            first_failed_gate = "gate_5_evidence_relative_analysis_proposal"
            failure_reason = "bounded sanitized content did not contain target component support"
        else:
            try:
                analysis_packet = build_evidence_relative_analysis_packet(
                    evidence_ledger_projection=context["evidence_ledger_projection"],
                    analyst_proposal_records=[proposal],
                    current_answer_contract_ref=context["current_answer_contract_ref"],
                    current_answer_contract_digest=context["current_answer_contract_digest"],
                )
            except EvidenceRelativeAnalysisPacketError as exc:
                result = "semantic_support_fail_analysis_packet"
                first_failed_gate = "gate_5_evidence_relative_analysis_proposal"
                failure_reason = str(exc)
            if analysis_packet is not None:
                _write_json(target / ANALYSIS_PACKET_NAME, analysis_packet)
                semantic_attempted = 1
                if run_kernel is None:
                    result = "semantic_support_fail_semantic_observation_admission"
                    first_failed_gate = "gate_6_semantic_observation_admission"
                    failure_reason = (
                        "CLI path has #358 packets/projections only; existing "
                        "SemanticObservation bridge requires RunKernel state with "
                        "accepted contract and EvidenceLedger custody. The phase "
                        "does not re-admit EvidenceLedger custody or directly "
                        "mutate RunKernel state."
                    )
                else:
                    try:
                        admitted = admit_semantic_observations_from_analysis_support_findings(
                            run_kernel=run_kernel,
                            evidence_relative_analysis_packet=analysis_packet,
                            fetch_read_content_packet=context["fetch_read_content_packet"],
                            finding_ids=(
                                analysis_packet["analyst_report"]["findings"][0][
                                    "finding_id"
                                ],
                            ),
                        )
                        if len(admitted) != 1:
                            raise SemanticObservationAdmissionBridgeError(
                                "expected exactly one SemanticObservation admission"
                            )
                        bridge_result = admitted[0]
                        semantic_admitted = 1
                        _write_json(
                            target / SEMANTIC_PROJECTION_NAME,
                            _semantic_observation_projection(bridge_result, run_kernel),
                        )
                    except (SemanticObservationAdmissionBridgeError, RunKernelTransitionError) as exc:
                        result = "semantic_support_fail_semantic_observation_admission"
                        first_failed_gate = "gate_6_semantic_observation_admission"
                        failure_reason = str(exc)
                    if bridge_result is not None:
                        coverage_attempted = 1
                        try:
                            coverage_projection = _reduce_component_coverage(
                                run_kernel=run_kernel,
                                admission_result=bridge_result,
                            )
                            coverage_reduced = 1
                            result = "semantic_support_coverage_pass"
                            first_failed_gate = None
                            failure_reason = None
                            _write_json(target / COVERAGE_PROJECTION_NAME, coverage_projection)
                        except (RunKernelTransitionError, ValueError) as exc:
                            result = "semantic_support_fail_component_coverage"
                            first_failed_gate = "gate_7_component_coverage_reduction"
                            failure_reason = str(exc)
    finally:
        packet = _base_packet(
            context=context,
            output_dir=target,
            semantic_support_result=result,
            first_failed_gate=first_failed_gate,
            semantic_observation_attempted_count=semantic_attempted,
            semantic_observation_admitted_count=semantic_admitted,
            component_coverage_attempted_count=coverage_attempted,
            component_coverage_reduced_count=coverage_reduced,
            analysis_packet=analysis_packet,
            bridge_result=bridge_result,
            coverage_projection=coverage_projection,
            failure_reason=failure_reason,
        )
        packet["packet_kind"] = "semantic_support_coverage_packet"
        validate_review_packet(packet)
        _write_json(target / RESULT_PACKET_NAME, packet)
        (target / RESULT_MARKDOWN_NAME).write_text(
            _result_markdown(packet),
            encoding="utf-8",
        )
    return packet


def validate_review_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(packet)
    result = safe.get("semantic_support_result")
    if result not in SEMANTIC_SUPPORT_RESULTS:
        raise SemanticSupportCoverageError("invalid_semantic_support_result")
    if safe.get("mode") != MODE or safe.get("phase") != PHASE:
        raise SemanticSupportCoverageError("semantic_support_packet_phase_mismatch")
    if safe.get("provider_search_calls") != 0 or safe.get("broker_calls") != 0:
        raise SemanticSupportCoverageError("semantic_support_packet_opens_live_calls")
    if safe.get("fetch_read_calls") != 0 or safe.get("model_calls") != 0:
        raise SemanticSupportCoverageError("semantic_support_packet_opens_live_calls")
    for key, expected in RAW_RETENTION_FLAGS.items():
        if safe.get(key) is not expected:
            raise SemanticSupportCoverageError("semantic_support_packet_retains_raw_material")
    if safe.get("citation_eligibility_decisions") != 0:
        raise SemanticSupportCoverageError("semantic_support_packet_opens_citation_surface")
    if safe.get("source_obligation_satisfaction_decisions") != 0:
        raise SemanticSupportCoverageError("semantic_support_packet_opens_source_obligation_surface")
    if safe.get("sufficiency_fap_author_authorprose_count") != 0:
        raise SemanticSupportCoverageError("semantic_support_packet_opens_closed_authority")
    _reject_forbidden_packet_material(safe)
    return safe


def _load_and_validate_inputs(
    *,
    source_survival_packet_path: str | Path,
    fetch_read_content_packet_path: str | Path,
    sanitized_content_reference_path: str | Path,
    evidence_ledger_projection_path: str | Path,
) -> dict[str, Any]:
    paths = {
        "source_survival_packet": _input_path(source_survival_packet_path),
        "fetch_read_content_packet": _input_path(fetch_read_content_packet_path),
        "sanitized_content_reference": _input_path(sanitized_content_reference_path),
        "evidence_ledger_projection": _input_path(evidence_ledger_projection_path),
    }
    source = _read_json(paths["source_survival_packet"])
    fetch_packet = _read_json(paths["fetch_read_content_packet"])
    reference = _read_json(paths["sanitized_content_reference"])
    ledger = _read_json(paths["evidence_ledger_projection"])

    _validate_source_survival(source)
    try:
        fetch_packet = validate_fetch_read_content_packet(fetch_packet)
    except FetchReadContentReferenceError as exc:
        raise SemanticSupportCoverageError(
            "fetch_read_content_packet_invalid",
            str(exc),
            gate="gate_4_fetch_read_content_packet",
        ) from exc
    _validate_reference(reference, fetch_packet)
    custody_record = _validate_ledger_projection(ledger, reference)
    bounded_text = _bounded_text_from_reference(reference, fetch_packet)
    selected = _selected_source(source, fetch_packet, reference)
    current_ref = _safe_mapping(
        custody_record.get("current_answer_contract_ref")
        or reference.get("current_answer_contract_ref")
        or fetch_packet.get("current_answer_contract_ref")
    )
    return {
        "paths": {key: _rel(value) for key, value in paths.items()},
        "path_digests": {key: _file_digest(value) for key, value in paths.items()},
        "source_survival_packet": source,
        "fetch_read_content_packet": fetch_packet,
        "sanitized_content_reference": reference,
        "evidence_ledger_projection": ledger,
        "custody_record": custody_record,
        "bounded_text": bounded_text,
        "bounded_content_reference_id": reference.get("reference_id"),
        "bounded_content_digest": reference.get("excerpt_digest"),
        "bounded_content_char_count": len(bounded_text),
        "selected_source": selected,
        "current_answer_contract_ref": current_ref,
        "current_answer_contract_digest": (
            current_ref.get("contract_digest")
            or custody_record.get("current_answer_contract_digest")
            or reference.get("current_answer_contract_digest")
            or fetch_packet.get("current_answer_contract_digest")
        ),
    }


def _validate_source_survival(packet: Mapping[str, Any]) -> None:
    if packet.get("selected_source_survived") != "source_survival_pass":
        raise SemanticSupportCoverageError(
            "source_survival_must_pass",
            "selected_source_survived must be source_survival_pass",
            gate="gate_2_source_survival_pass",
        )
    if packet.get("fetch_read_calls_attempted") != 1 or packet.get("fetch_read_calls_completed") != 1:
        raise SemanticSupportCoverageError("fetch_read_attempts_mismatch", gate="gate_3_fetch_read_custody")
    if packet.get("final_domain") != REQUIRED_DOMAIN:
        raise SemanticSupportCoverageError("final_domain_mismatch", gate="gate_3_fetch_read_custody")
    if packet.get("http_status_class") != "2xx":
        raise SemanticSupportCoverageError("http_status_class_mismatch", gate="gate_3_fetch_read_custody")
    content_type = str(packet.get("content_type") or "").split(";", 1)[0].strip().casefold()
    if content_type != "text/html":
        raise SemanticSupportCoverageError("content_type_mismatch", gate="gate_3_fetch_read_custody")
    if packet.get("evidence_ledger_candidate_content_custody_count") != 1:
        raise SemanticSupportCoverageError("evidence_ledger_custody_count_mismatch", gate="gate_3_fetch_read_custody")
    for key in RAW_RETENTION_FLAGS:
        if packet.get(key) not in (None, False):
            raise SemanticSupportCoverageError("raw_retention_flag_must_be_false", gate="gate_3_fetch_read_custody")


def _validate_reference(reference: Mapping[str, Any], fetch_packet: Mapping[str, Any]) -> None:
    references = [
        item
        for item in fetch_packet.get("reference_records") or ()
        if isinstance(item, Mapping)
    ]
    if len(references) != 1:
        raise SemanticSupportCoverageError("fetch_read_reference_count_mismatch", gate="gate_4_fetch_read_content_packet")
    fetch_ref = references[0]
    for key in ("reference_id", "reference_digest", "candidate_id", "candidate_digest"):
        if reference.get(key) != fetch_ref.get(key):
            raise SemanticSupportCoverageError(
                "sanitized_content_reference_mismatch",
                f"{key} mismatch",
                gate="gate_4_fetch_read_content_packet",
            )
    if fetch_ref.get("fetch_read_status") != "readable":
        raise SemanticSupportCoverageError("fetch_read_reference_not_readable", gate="gate_4_fetch_read_content_packet")
    if fetch_ref.get("bounded_text_sanitized") is not True or fetch_ref.get("bounded_text_bounded") is not True:
        raise SemanticSupportCoverageError("bounded_content_flags_mismatch", gate="gate_4_fetch_read_content_packet")


def _validate_ledger_projection(
    ledger: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    custody = _safe_mapping(ledger.get("fetch_read_candidate_custody"))
    records = [
        dict(item)
        for item in custody.get("fetch_read_candidate_custody_records") or ()
        if isinstance(item, Mapping)
    ]
    if custody.get("custody_record_count") != 1 or custody.get("readable_record_count") != 1:
        raise SemanticSupportCoverageError("evidence_ledger_custody_count_mismatch", gate="gate_3_fetch_read_custody")
    if len(records) != 1:
        raise SemanticSupportCoverageError("evidence_ledger_record_count_mismatch", gate="gate_3_fetch_read_custody")
    record = records[0]
    for key in ("reference_id", "reference_digest", "candidate_id", "candidate_digest"):
        if record.get(key) != reference.get(key):
            raise SemanticSupportCoverageError("evidence_ledger_reference_mismatch", gate="gate_3_fetch_read_custody")
    if record.get("fetch_read_status") != "readable":
        raise SemanticSupportCoverageError("evidence_ledger_record_not_readable", gate="gate_3_fetch_read_custody")
    return record


def _source_bound_support_proposal(context: Mapping[str, Any]) -> dict[str, Any] | None:
    text = _collapse_text(context["bounded_text"])
    folded = text.casefold()
    required = (
        ("adult" in folded or "age 16" in folded or "16 and older" in folded),
        "passport" in folded,
        "book" in folded,
        "renew" in folded,
        "$130" in folded or re.search(r"\b130\b", folded) is not None,
    )
    if not all(required):
        return None
    record = _safe_mapping(context["custody_record"])
    return {
        "proposal_kind": "possible_support_proposal",
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_id": record.get("fetch_read_content_packet_id"),
        "fetch_read_content_packet_digest": record[
            "fetch_read_content_packet_digest"
        ],
        "search_result_candidate_packet_id": record.get(
            "search_result_candidate_packet_id"
        ),
        "search_result_candidate_packet_digest": record[
            "search_result_candidate_packet_digest"
        ],
        "search_result_candidate_record_digest": record.get(
            "search_result_candidate_record_digest"
        ),
        "component_id": record.get("component_id") or TARGET_COMPONENT_ID,
        "source_obligation_candidate_ids": record.get(
            "source_obligation_candidate_ids",
            [],
        ),
        "proposal_summary": TARGET_COMPONENT_CLAIM_UNDER_TEST,
        "reason": (
            "bounded sanitized travel.state.gov content contains the adult, "
            "passport book, renewal, and $130 anchors"
        ),
    }


def _reduce_component_coverage(
    *,
    run_kernel: Any,
    admission_result: SemanticObservationAdmissionBridgeResult,
) -> dict[str, Any]:
    observation = admission_result.semantic_observation
    content_ref = admission_result.sanitized_content_reference
    component_ref = _component_ref(run_kernel, observation.answer_component_id)
    record = ComponentCoverageRecord(
        record_id=f"coverage:ag-live-semantic-support:{observation.observation_digest[:16]}",
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        request_digest=run_kernel.state.initial_answer_contract[
            "parent_question_meaning_record_digest"
        ],
        accepted_contract_version=run_kernel.state.initial_answer_contract[
            "accepted_contract_version"
        ],
        accepted_contract_digest=run_kernel.state.initial_answer_contract[
            "accepted_contract_digest"
        ],
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        evidence_ledger_binding=_ledger_binding(run_kernel),
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=(SemanticObservationCoverageRef.from_observation(observation),),
        content_reference_bindings=(ContentReferenceCoverageBinding.from_content_reference(content_ref),),
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        currentness_posture=CurrentnessPosture.CURRENT,
        remaining_unknowns=("source-obligation candidate ids remain lineage only",),
        required_caveats=("Do not upgrade semantic support to source-obligation satisfaction.",),
        prohibited_upgrades=(
            "Do not create Sufficiency, FAP, Author, citation, or product-correctness claims.",
        ),
        followup_need=FollowupNeed.OPTIONAL,
        mode_budget_posture=ModeBudgetPosture.AVAILABLE,
        lineage=CoverageLineage(
            created_by=PHASE,
            created_from=(
                "bounded_358_content",
                "evidence_relative_analysis_packet",
                "admitted_semantic_observation",
            ),
        ),
        metadata={"phase": PHASE, "live_path_proof": True},
    ).require_valid()
    action = run_kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
        inputs={"phase": PHASE},
    )
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
            status=RunStageStatus.COMPLETED,
            payload={"component_coverage_record": payload},
        )
    )
    return dict(run_kernel.state.component_coverage_projection)


def _component_ref(run_kernel: Any, component_id: str) -> Mapping[str, Any]:
    for ref in run_kernel.state.initial_answer_contract.get("accepted_answer_component_refs", []):
        if isinstance(ref, Mapping) and ref.get("component_id") == component_id:
            return ref
    raise SemanticSupportCoverageError("target_component_missing_from_accepted_contract")


def _ledger_binding(run_kernel: Any) -> EvidenceLedgerSnapshotBinding:
    projection = run_kernel.state.evidence_ledger.to_projection().to_dict()
    digest = evidence_ledger_projection_digest(projection)
    observation_refs = tuple(
        ref["observation_id"]
        for ref in projection.get("observation_refs") or ()
        if isinstance(ref, Mapping) and ref.get("observation_id")
    )
    return EvidenceLedgerSnapshotBinding(
        ledger_snapshot_id=f"evidence-ledger:{run_kernel.state.run_id}:{digest[:32]}",
        ledger_schema_version=EVIDENCE_LEDGER_SCHEMA_VERSION,
        ledger_digest=digest,
        custody_status=EvidenceCustodyStatus.CUSTODIED,
        ledger_observation_refs=observation_refs,
        version_validity=VersionValidity.VALID,
    )


def _base_packet(
    *,
    context: Mapping[str, Any],
    output_dir: Path,
    semantic_support_result: str,
    first_failed_gate: str | None,
    semantic_observation_attempted_count: int,
    semantic_observation_admitted_count: int,
    component_coverage_attempted_count: int,
    component_coverage_reduced_count: int,
    analysis_packet: Mapping[str, Any] | None = None,
    bridge_result: SemanticObservationAdmissionBridgeResult | None = None,
    coverage_projection: Mapping[str, Any] | None = None,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    selected = _safe_mapping(context["selected_source"])
    analysis_ref = evidence_relative_analysis_packet_ref_from_packet(analysis_packet)
    semantic_ref = _semantic_ref(bridge_result)
    coverage_ref = _coverage_ref(coverage_projection)
    prior_357_refs = _safe_mapping(
        _safe_mapping(context["source_survival_packet"]).get(
            "prior_phase_refs_and_digests"
        )
    )
    return _without_empty(
        {
            "phase": PHASE,
            "mode": MODE,
            "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
            "proof_class": PROOF_CLASS,
            "product_facing_progress_type": PRODUCT_FACING_PROGRESS_TYPE,
            "prior_357_refs_and_digests": prior_357_refs,
            "prior_358_ref": PRIOR_358_REF,
            "prior_358_source_survival_packet_digest": context["path_digests"].get(
                "source_survival_packet"
            ),
            "prior_358_fetch_read_content_packet_digest": context["path_digests"].get(
                "fetch_read_content_packet"
            ),
            "prior_358_sanitized_content_reference_digest": context[
                "path_digests"
            ].get("sanitized_content_reference"),
            "prior_358_evidence_ledger_projection_digest": context[
                "path_digests"
            ].get("evidence_ledger_projection"),
            "input_358_paths": dict(context["paths"]),
            "selected_source_domain": selected.get("domain"),
            "selected_source_url": selected.get("url"),
            "selected_source_rank": selected.get("rank"),
            "selected_source_title": selected.get("title"),
            "target_component_id": TARGET_COMPONENT_ID,
            "target_component_text": TARGET_COMPONENT_TEXT,
            "target_component_claim_under_test": TARGET_COMPONENT_CLAIM_UNDER_TEST,
            "bounded_content_reference_id": context["bounded_content_reference_id"],
            "bounded_content_digest": context["bounded_content_digest"],
            "bounded_content_char_count": context["bounded_content_char_count"],
            "evidence_relative_analysis_proposal_id": analysis_ref.get("report_id"),
            "evidence_relative_analysis_proposal_digest": analysis_ref.get("report_digest"),
            "evidence_relative_analysis_proposal_ref": analysis_ref,
            "semantic_observation_attempted_count": semantic_observation_attempted_count,
            "semantic_observation_admitted_count": semantic_observation_admitted_count,
            "semantic_observation_id": semantic_ref.get("observation_id"),
            "semantic_observation_digest": semantic_ref.get("observation_digest"),
            "semantic_observation_ref": semantic_ref,
            "component_coverage_attempted_count": component_coverage_attempted_count,
            "component_coverage_reduced_count": component_coverage_reduced_count,
            "component_coverage_id": coverage_ref.get("coverage_record_id"),
            "component_coverage_digest": coverage_ref.get("coverage_record_digest"),
            "component_coverage_ref": coverage_ref,
            "semantic_support_result": semantic_support_result,
            "first_failed_gate": first_failed_gate,
            "failure_reason": failure_reason,
            **ZERO_CALL_COUNTS,
            **RAW_RETENTION_FLAGS,
            "citation_eligibility_decisions": 0,
            "source_obligation_satisfaction_decisions": 0,
            "sufficiency_fap_author_authorprose_count": 0,
            "opened_surfaces": list(OPENED_SURFACES),
            "closed_surfaces": list(CLOSED_SURFACES),
            "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
            "mandatory_next_build_product_checkpoint": (
                MANDATORY_NEXT_BUILD_PRODUCT_CHECKPOINT
            ),
            "existing_machinery_reused": [
                "FetchReadContentPacket validator",
                "EvidenceRelativeAnalysisPacket builder/validator",
                "SemanticObservation admission bridge",
                "RunKernel SemanticObservation admission reducer",
                "ComponentCoverageRecord and RunKernel coverage reducer",
            ],
            "new_machinery_introduced": [
                "scripts/ag_live_semantic_support_coverage_01.py",
                "tests/test_ag_live_semantic_support_coverage_01.py",
                "docs/architecture/AG_LIVE_SEMANTIC_SUPPORT_COVERAGE_01.md",
            ],
            "why_not_reinventing_existing_surface": (
                "The harness only maps bounded #358 content into an existing "
                "EvidenceRelativeAnalysisPacket proposal and then uses existing "
                "RunKernel admission/reduction paths when a RunKernel consumer is "
                "available."
            ),
            "old_path_treatment": (
                "Old Author/FAP/sufficiency/follow-up/pipeline paths remain closed "
                "and are not revived."
            ),
            "human_reviewable_product_output": (
                "structural proof packet only; no answer text or product prose"
            ),
            "live_validation_status": (
                "no new live calls; consumes existing #358 local bounded output only"
            ),
            "output_paths": {
                "request_packet": _rel(output_dir / REQUEST_PACKET_NAME),
                "request_markdown": _rel(output_dir / REQUEST_MARKDOWN_NAME),
                "semantic_support_coverage_packet": _rel(output_dir / RESULT_PACKET_NAME),
                "semantic_support_coverage_markdown": _rel(output_dir / RESULT_MARKDOWN_NAME),
                "analysis_packet": _rel(output_dir / ANALYSIS_PACKET_NAME),
                "semantic_observation_projection": _rel(output_dir / SEMANTIC_PROJECTION_NAME),
                "component_coverage_projection": _rel(output_dir / COVERAGE_PROJECTION_NAME),
            },
        }
    )


def _semantic_ref(result: SemanticObservationAdmissionBridgeResult | None) -> dict[str, Any]:
    if result is None:
        return {}
    return {
        "observation_id": result.semantic_observation.observation_id,
        "observation_digest": result.semantic_observation.observation_digest,
        "content_ref_id": result.sanitized_content_reference.content_ref_id,
        "content_digest": result.sanitized_content_reference.content_digest,
    }


def _coverage_ref(projection: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _safe_mapping(projection)
    return _without_empty(
        {
            "coverage_record_id": safe.get("coverage_record_id"),
            "coverage_record_digest": safe.get("coverage_record_digest"),
            "coverage_reduction_digest": safe.get("coverage_reduction_digest"),
            "coverage_state": safe.get("coverage_state"),
            "semantic_support_status": safe.get("semantic_support_status"),
        }
    )


def _semantic_observation_projection(
    result: SemanticObservationAdmissionBridgeResult,
    run_kernel: Any,
) -> dict[str, Any]:
    projection = _safe_mapping(run_kernel.state.semantic_observation_admission_projection)
    return _without_empty(
        {
            "phase": PHASE,
            "projection_kind": "semantic_observation_admission_projection_ref",
            "observation_id": result.semantic_observation.observation_id,
            "observation_digest": result.semantic_observation.observation_digest,
            "content_ref_id": result.sanitized_content_reference.content_ref_id,
            "content_digest": result.sanitized_content_reference.content_digest,
            "authorized_action_id": projection.get("authorized_action_id"),
            "admission_status": "admitted",
            "citation_eligible": False,
            "source_obligation_satisfied": False,
            "sufficiency_decided": False,
            "final_answer_packet_created": False,
            "author_input_created": False,
        }
    )


def _selected_source(
    source_packet: Mapping[str, Any],
    fetch_packet: Mapping[str, Any],
    reference: Mapping[str, Any],
) -> dict[str, Any]:
    selected = _safe_mapping(source_packet.get("selected_candidate"))
    record = _safe_mapping((fetch_packet.get("reference_records") or [{}])[0])
    return _without_empty(
        {
            "domain": selected.get("domain") or record.get("candidate_domain"),
            "url": selected.get("url") or record.get("candidate_url"),
            "rank": selected.get("rank") or selected.get("result_rank") or 1,
            "title": selected.get("title") or record.get("candidate_title") or reference.get("content_title"),
        }
    )


def _bounded_text_from_reference(
    reference: Mapping[str, Any],
    fetch_packet: Mapping[str, Any],
) -> str:
    text = _clean_text(reference.get("bounded_text"), limit=20_000)
    if not text:
        for item in fetch_packet.get("reference_records") or ():
            if isinstance(item, Mapping) and item.get("reference_id") == reference.get("reference_id"):
                text = _clean_text(item.get("bounded_text"), limit=20_000)
                break
    if not text:
        raise SemanticSupportCoverageError("bounded_content_missing", gate="gate_4_fetch_read_content_packet")
    return text


def _operator_command(
    *,
    source_survival_packet_path: str | Path,
    fetch_read_content_packet_path: str | Path,
    sanitized_content_reference_path: str | Path,
    evidence_ledger_projection_path: str | Path,
    output_dir: Path,
) -> str:
    return "\n".join(
        [
            "py scripts\\ag_live_semantic_support_coverage_01.py reduce-semantic-coverage `",
            f"  --source-survival-packet {_rel(source_survival_packet_path)} `",
            f"  --fetch-read-content-packet {_rel(fetch_read_content_packet_path)} `",
            f"  --sanitized-content-reference {_rel(sanitized_content_reference_path)} `",
            f"  --evidence-ledger-projection {_rel(evidence_ledger_projection_path)} `",
            f"  --output-dir {_rel(output_dir)} `",
            "  --confirm-semantic-coverage",
        ]
    )


def _request_markdown(packet: Mapping[str, Any]) -> str:
    return (
        f"# {PHASE} Request Packet\n\n"
        f"Mode: `{MODE}`\n\n"
        f"Usable-answer verdict target: `{USABLE_ANSWER_VERDICT_TARGET}`\n\n"
        f"Target component: `{TARGET_COMPONENT_TEXT}`\n\n"
        "This request packet performs no semantic admission and no ComponentCoverage reduction.\n\n"
        "## Operator Command\n\n"
        "```powershell\n"
        f"{packet['operator_command']}\n"
        "```\n"
    )


def _result_markdown(packet: Mapping[str, Any]) -> str:
    return (
        f"# {PHASE} Semantic Support Coverage Packet\n\n"
        f"Mode: `{MODE}`\n\n"
        f"Semantic support result: `{packet['semantic_support_result']}`\n\n"
        f"First failed gate: `{packet.get('first_failed_gate')}`\n\n"
        "SemanticObservation attempted/admitted: "
        f"`{packet['semantic_observation_attempted_count']}` / "
        f"`{packet['semantic_observation_admitted_count']}`\n\n"
        "ComponentCoverage attempted/reduced: "
        f"`{packet['component_coverage_attempted_count']}` / "
        f"`{packet['component_coverage_reduced_count']}`\n\n"
        "Provider/broker/fetch/model calls: `0 / 0 / 0 / 0`\n\n"
        "Mandatory next Build/product checkpoint: "
        f"`{MANDATORY_NEXT_BUILD_PRODUCT_CHECKPOINT}`\n"
    )


def _phase_output_dir(path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    raw.mkdir(parents=True, exist_ok=True)
    return raw.resolve()


def _input_path(path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    resolved = raw.resolve()
    if not resolved.exists():
        raise SemanticSupportCoverageError(
            "input_packet_missing",
            f"missing input packet: {_rel(resolved)}",
            gate="gate_1_load_358_source_survival_output",
        )
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, Mapping):
        raise SemanticSupportCoverageError("json_packet_must_be_object")
    return dict(decoded)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reject_forbidden_packet_material(value: Any) -> None:
    keys = _collect_keys(value)
    raw_or_closed = sorted(
        key
        for key in keys
        if key not in _SAFE_FALSE_KEYS
        and (key.startswith("raw_") or key in _FORBIDDEN_KEYS)
    )
    if raw_or_closed:
        raise SemanticSupportCoverageError(
            "semantic_support_packet_contains_raw_or_closed_fields",
            ", ".join(raw_or_closed),
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SemanticSupportCoverageError(
            "semantic_support_packet_opens_closed_surfaces",
            ", ".join(dangerous),
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != {} and value != []
    }


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = _collapse_text(value)
    return text[:limit] if text else None


def _collapse_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _rel(path: str | Path) -> str:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    try:
        return str(raw.resolve().relative_to(ROOT))
    except ValueError:
        return str(raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare and run AG-LIVE semantic support / ComponentCoverage proof "
            "packets from existing #358 bounded output. No live calls are made."
        )
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for sub in (
        subparsers.add_parser("prepare-request"),
        subparsers.add_parser("reduce-semantic-coverage"),
    ):
        sub.add_argument("--source-survival-packet", default=str(DEFAULT_SOURCE_SURVIVAL_PACKET))
        sub.add_argument("--fetch-read-content-packet", default=str(DEFAULT_FETCH_READ_CONTENT_PACKET))
        sub.add_argument("--sanitized-content-reference", default=str(DEFAULT_SANITIZED_CONTENT_REFERENCE))
        sub.add_argument("--evidence-ledger-projection", default=str(DEFAULT_EVIDENCE_LEDGER_PROJECTION))
        sub.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    subparsers.choices["reduce-semantic-coverage"].add_argument(
        "--confirm-semantic-coverage",
        action="store_true",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.operation == "prepare-request":
            packet = prepare_request(
                source_survival_packet_path=args.source_survival_packet,
                fetch_read_content_packet_path=args.fetch_read_content_packet,
                sanitized_content_reference_path=args.sanitized_content_reference,
                evidence_ledger_projection_path=args.evidence_ledger_projection,
                output_dir=args.output_dir,
            )
        else:
            packet = reduce_semantic_coverage(
                source_survival_packet_path=args.source_survival_packet,
                fetch_read_content_packet_path=args.fetch_read_content_packet,
                sanitized_content_reference_path=args.sanitized_content_reference,
                evidence_ledger_projection_path=args.evidence_ledger_projection,
                output_dir=args.output_dir,
                confirm_semantic_coverage=args.confirm_semantic_coverage,
            )
    except SemanticSupportCoverageError as exc:
        print(exc.code, file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"refusing AG-LIVE semantic support operation: {exc}", file=sys.stderr)
        return 2
    summary = {
        "phase": PHASE,
        "operation": args.operation,
        "output_dir": str(Path(args.output_dir)),
        "semantic_support_result": packet.get("semantic_support_result"),
        "first_failed_gate": packet.get("first_failed_gate"),
        "semantic_observation_admitted_count": packet.get(
            "semantic_observation_admitted_count"
        ),
        "component_coverage_reduced_count": packet.get(
            "component_coverage_reduced_count"
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
