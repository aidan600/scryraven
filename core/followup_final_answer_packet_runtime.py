"""Fixture-only follow-up FinalAnswerPacket preparation seam for AG-96I2E.

This module derives a packet-level authority record from canonical follow-up
sufficiency recheck state, the current EvidenceLedger projection, and the
current SufficiencyJudgment projection. It never calls Author, providers, search,
retrieval, fetch/read, prompts, models, citation formatters, provider-job
executors, shell processes, or arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from core.final_answer_packet import FinalAnswerPacket, SourceObligationStatus
from core.final_answer_runtime_adapter import build_final_answer_packet
from core.followup_deliberation import clean_text, clean_token, safe_json, stable_hash
from core.followup_fixture_boundaries import (
    FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS,
    FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS,
    FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
    followup_closed_flags,
    followup_common_redaction_posture,
    followup_fixture_provenance,
    followup_live_surface_flags,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    evidence_ledger_projection_digest,
)

FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION = (
    "followup_final_answer_packet_ag96i2e_v1"
)
FOLLOWUP_FINAL_ANSWER_PACKET_TRACE_KEY = "followup_final_answer_packet_runtime"
FOLLOWUP_FINAL_ANSWER_PACKET_STAGE = "followup_final_answer_packet"
FOLLOWUP_FINAL_ANSWER_PACKET_MODE = (
    "fixture_only_followup_final_answer_packet_prepare"
)
FOLLOWUP_FINAL_ANSWER_PACKET_GATE_REASON = (
    "ag96i2e_fixture_only_final_answer_packet_prepare"
)


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketRequest:
    request_id: str
    run_id: str
    checkpoint_id: str
    followup_authorization_consumption_id: str
    sealed_candidate_id: str
    followup_execution_id: str
    execution_id: str
    followup_execution_observation_id: str
    followup_evidence_intake_id: str
    intake_id: str
    followup_evidence_intake_observation_id: str
    followup_sufficiency_recheck_id: str
    recheck_id: str
    followup_sufficiency_recheck_observation_id: str
    provider_job_kind: str
    component_id: str
    source_obligation_id: str
    requirement_ids: tuple[str, ...]
    expected_source_classes: tuple[str, ...]
    fixture_execution_mode: str
    evidence_ledger_intake_mode: str
    sufficiency_recheck_mode: str
    evidence_ledger_projection_digest: str
    sufficiency_judgment_digest: str
    followup_sufficiency_recheck_digest: str
    provider_execution_licensed: bool
    final_answer_packet_mode: str
    author_activation_allowed: bool
    citation_rendering_changed: bool
    product_answer_behavior_changed: bool
    live_validation_not_run: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION,
            "record_type": "followup_final_answer_packet_request",
            "request_id": clean_text(self.request_id, limit=220),
            "run_id": clean_token(self.run_id),
            "checkpoint_id": clean_token(self.checkpoint_id),
            "followup_authorization_consumption_id": clean_text(
                self.followup_authorization_consumption_id,
                limit=220,
            ),
            "sealed_candidate_id": clean_token(self.sealed_candidate_id),
            "followup_execution_id": clean_text(
                self.followup_execution_id,
                limit=220,
            ),
            "execution_id": clean_text(self.execution_id, limit=220),
            "followup_execution_observation_id": clean_text(
                self.followup_execution_observation_id,
                limit=220,
            ),
            "followup_evidence_intake_id": clean_text(
                self.followup_evidence_intake_id,
                limit=220,
            ),
            "intake_id": clean_text(self.intake_id, limit=220),
            "followup_evidence_intake_observation_id": clean_text(
                self.followup_evidence_intake_observation_id,
                limit=220,
            ),
            "followup_sufficiency_recheck_id": clean_text(
                self.followup_sufficiency_recheck_id,
                limit=220,
            ),
            "recheck_id": clean_text(self.recheck_id, limit=220),
            "followup_sufficiency_recheck_observation_id": clean_text(
                self.followup_sufficiency_recheck_observation_id,
                limit=220,
            ),
            "provider_job_kind": clean_token(self.provider_job_kind),
            "component_id": clean_token(self.component_id),
            "source_obligation_id": clean_token(self.source_obligation_id),
            "requirement_ids": [clean_token(item) for item in self.requirement_ids],
            "expected_source_classes": [
                clean_token(item) for item in self.expected_source_classes
            ],
            "fixture_execution_mode": clean_token(self.fixture_execution_mode),
            "evidence_ledger_intake_mode": clean_token(
                self.evidence_ledger_intake_mode
            ),
            "sufficiency_recheck_mode": clean_token(self.sufficiency_recheck_mode),
            "evidence_ledger_projection_digest": clean_text(
                self.evidence_ledger_projection_digest,
                limit=120,
            ),
            "sufficiency_judgment_digest": clean_text(
                self.sufficiency_judgment_digest,
                limit=120,
            ),
            "followup_sufficiency_recheck_digest": clean_text(
                self.followup_sufficiency_recheck_digest,
                limit=120,
            ),
            "fixture_only_provenance": _fixture_only_provenance(),
            "provider_execution_licensed": bool(self.provider_execution_licensed),
            "final_answer_packet_mode": clean_token(self.final_answer_packet_mode),
            "author_activation_allowed": bool(self.author_activation_allowed),
            "citation_rendering_changed": bool(self.citation_rendering_changed),
            "product_answer_behavior_changed": bool(
                self.product_answer_behavior_changed
            ),
            "live_validation_not_run": bool(self.live_validation_not_run),
            "behavior_boundary_flags": _behavior_boundary_flags(),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketResult:
    result_id: str
    status: str
    packet_projection: Mapping[str, Any]
    final_evidence_refs: tuple[Mapping[str, Any], ...]
    citation_eligibility_refs: tuple[Mapping[str, Any], ...]
    packet_authority_payload: Mapping[str, Any]
    answer_readiness_posture: Mapping[str, Any]
    mandatory_caveats: tuple[str, ...]
    prohibited_upgrades: tuple[str, ...]
    missing_required_obligations: tuple[Mapping[str, Any], ...]
    partial_obligations: tuple[Mapping[str, Any], ...]
    satisfied_obligations: tuple[Mapping[str, Any], ...]
    source_bound_unknowns: tuple[Mapping[str, Any], ...]
    unresolved_conflicts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION,
            "record_type": "followup_final_answer_packet_result",
            "result_id": clean_text(self.result_id, limit=220),
            "status": clean_token(self.status),
            "packet_projection": safe_json(self.packet_projection),
            "final_evidence_refs": [safe_json(item) for item in self.final_evidence_refs],
            "citation_eligibility_refs": [
                safe_json(item) for item in self.citation_eligibility_refs
            ],
            "packet_authority_payload": safe_json(self.packet_authority_payload),
            "answer_readiness_posture": safe_json(self.answer_readiness_posture),
            "mandatory_caveats": [clean_text(item, limit=300) for item in self.mandatory_caveats],
            "prohibited_upgrades": [
                clean_text(item, limit=300) for item in self.prohibited_upgrades
            ],
            "missing_required_obligations": [
                safe_json(item) for item in self.missing_required_obligations
            ],
            "partial_obligations": [safe_json(item) for item in self.partial_obligations],
            "satisfied_obligations": [
                safe_json(item) for item in self.satisfied_obligations
            ],
            "source_bound_unknowns": [safe_json(item) for item in self.source_bound_unknowns],
            "unresolved_conflicts": [clean_text(item, limit=220) for item in self.unresolved_conflicts],
            "final_answer_packet_prepared": True,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "provider_execution_licensed": False,
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketObservation:
    observation_id: str
    request: FollowupFinalAnswerPacketRequest
    result: FollowupFinalAnswerPacketResult

    def to_dict(self) -> dict[str, Any]:
        request = self.request.to_dict()
        result = self.result.to_dict()
        packet = _mapping(result.get("packet_projection"))
        return {
            "schema_version": FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION,
            "trace_key": FOLLOWUP_FINAL_ANSWER_PACKET_TRACE_KEY,
            "record_type": "followup_final_answer_packet_observation",
            "owner": "FollowupFinalAnswerPacketRuntime",
            "canonical_state": False,
            "trace_only": False,
            "storage_only": False,
            "observation_id": clean_text(self.observation_id, limit=220),
            "run_id": request.get("run_id"),
            "checkpoint_id": request.get("checkpoint_id"),
            "followup_authorization_consumption_id": request.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": request.get("sealed_candidate_id"),
            "followup_execution_id": request.get("followup_execution_id"),
            "execution_id": request.get("execution_id"),
            "followup_execution_observation_id": request.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": request.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": request.get("intake_id"),
            "followup_evidence_intake_observation_id": request.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": request.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": request.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": request.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "provider_job_kind": request.get("provider_job_kind"),
            "component_id": request.get("component_id"),
            "source_obligation_id": request.get("source_obligation_id"),
            "requirement_ids": request.get("requirement_ids", []),
            "expected_source_classes": request.get("expected_source_classes", []),
            "fixture_execution_mode": request.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": request.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": request.get("sufficiency_recheck_mode"),
            "evidence_ledger_projection_digest": request.get(
                "evidence_ledger_projection_digest"
            ),
            "sufficiency_judgment_digest": request.get(
                "sufficiency_judgment_digest"
            ),
            "followup_sufficiency_recheck_digest": request.get(
                "followup_sufficiency_recheck_digest"
            ),
            "provider_execution_licensed": request.get(
                "provider_execution_licensed"
            ),
            "final_answer_packet_mode": request.get("final_answer_packet_mode"),
            "request": request,
            "result": result,
            "packet_projection": packet,
            "packet_id": packet.get("packet_id"),
            "readiness_status": packet.get("readiness_status"),
            "readiness_reasons": packet.get("readiness_reasons", []),
            "final_evidence_refs": result.get("final_evidence_refs", []),
            "citation_eligibility_refs": result.get("citation_eligibility_refs", []),
            "packet_authority_payload": result.get("packet_authority_payload", {}),
            "answer_readiness_posture": result.get("answer_readiness_posture", {}),
            "mandatory_caveats": result.get("mandatory_caveats", []),
            "prohibited_upgrades": result.get("prohibited_upgrades", []),
            "missing_required_obligations": result.get(
                "missing_required_obligations",
                [],
            ),
            "partial_obligations": result.get("partial_obligations", []),
            "satisfied_obligations": result.get("satisfied_obligations", []),
            "source_bound_unknowns": result.get("source_bound_unknowns", []),
            "unresolved_conflicts": result.get("unresolved_conflicts", []),
            "final_answer_packet_prepared": True,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "behavior_boundary_flags": _behavior_boundary_flags(),
            "redaction_posture": _redaction_posture(),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketConsumptionRecord:
    packet_preparation_id: str
    observation: FollowupFinalAnswerPacketObservation

    def to_dict(self) -> dict[str, Any]:
        observed = self.observation.to_dict()
        return {
            **observed,
            "record_type": "followup_final_answer_packet_consumption_record",
            "owner": "FollowupFinalAnswerPacketRuntime",
            "canonical_state": False,
            "packet_preparation_id": clean_text(
                self.packet_preparation_id,
                limit=220,
            ),
        }


@dataclass(frozen=True, slots=True)
class FollowupFinalAnswerPacketActionResult:
    record: FollowupFinalAnswerPacketConsumptionRecord
    observation: Any


def execute_followup_final_answer_packet_prepare_action(
    action: Any,
    *,
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupFinalAnswerPacketActionResult:
    """Execute the fixture-only packet adapter for one authorized action."""

    from core.run_kernel import (  # Local import avoids a module import cycle.
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
        validate_authorized_action,
    )

    authorized = validate_authorized_action(
        action,
        action_type=ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
        stage=FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
        expected_observation_type=(
            ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED
        ),
    )
    record = build_followup_final_answer_packet_record(
        action_inputs=authorized.inputs,
        followup_sufficiency_recheck_state=followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=sufficiency_judgment_projection,
        evidence_ledger_projection=evidence_ledger_projection,
        followup_evidence_intake_state=followup_evidence_intake_state,
    )
    return FollowupFinalAnswerPacketActionResult(
        record=record,
        observation=Observation.from_action(
            authorized,
            observation_type=ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED,
            status=RunStageStatus.COMPLETED,
            payload={"followup_final_answer_packet_state": record.to_dict()},
        ),
    )


def build_followup_final_answer_packet_record(
    *,
    action_inputs: Mapping[str, Any],
    followup_sufficiency_recheck_state: Mapping[str, Any],
    sufficiency_judgment_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    followup_evidence_intake_state: Mapping[str, Any],
) -> FollowupFinalAnswerPacketConsumptionRecord:
    action = _mapping(safe_json(action_inputs))
    recheck = _mapping(safe_json(followup_sufficiency_recheck_state))
    sufficiency = _mapping(safe_json(sufficiency_judgment_projection))
    ledger = _mapping(safe_json(evidence_ledger_projection))
    intake = _mapping(safe_json(followup_evidence_intake_state))
    _validate_recheck_state(recheck)
    _validate_sufficiency_projection(sufficiency)
    _validate_ledger_projection(ledger)
    _validate_intake_state(intake, action)
    _validate_action_inputs(action, recheck, sufficiency, ledger, intake)

    final_evidence = _eligible_final_evidence_refs(
        ledger,
        action_inputs=action,
        recheck_state=recheck,
    )
    packet_sufficiency = _packet_sufficiency_projection(sufficiency, recheck)
    packet = build_final_answer_packet(
        run_id=str(action.get("run_id") or recheck.get("run_id") or ""),
        final_evidence=final_evidence,
        author_evidence=final_evidence,
        ordered_sources=(),
        unique_source_urls=_unique_source_urls(final_evidence),
        final_answer_source_telemetry={},
        source_obligation_projection=ledger,
        answer_contract_projection=None,
        run_contract_projection=None,
        sufficiency_judgment_projection=packet_sufficiency,
        query_lineage_refs={
            "followup_final_answer_packet": {
                "authority": "RunKernel.FollowupFinalAnswerPacket",
                "recheck_id": action.get("recheck_id"),
                "evidence_ledger_projection_digest": action.get(
                    "evidence_ledger_projection_digest"
                ),
            }
        },
        evidence_sufficient=False,
        corpus_weak=True,
        failure_card_payload={"show": False, "reason": None},
        conflicts_present=bool(sufficiency.get("unresolved_conflicts")),
        synth_was_insufficient=True,
        author_notes=None,
    )
    packet = _with_fixture_packet_boundaries(packet)
    packet_projection = packet.to_dict()
    authority_payload = _packet_authority_payload(packet)
    request = FollowupFinalAnswerPacketRequest(
        request_id=f"followup-final-answer-packet-request:{action.get('recheck_id')}",
        run_id=str(action.get("run_id") or ""),
        checkpoint_id=str(action.get("checkpoint_id") or ""),
        followup_authorization_consumption_id=str(
            action.get("followup_authorization_consumption_id") or ""
        ),
        sealed_candidate_id=str(action.get("sealed_candidate_id") or ""),
        followup_execution_id=str(action.get("followup_execution_id") or ""),
        execution_id=str(action.get("execution_id") or ""),
        followup_execution_observation_id=str(
            action.get("followup_execution_observation_id") or ""
        ),
        followup_evidence_intake_id=str(
            action.get("followup_evidence_intake_id") or ""
        ),
        intake_id=str(action.get("intake_id") or ""),
        followup_evidence_intake_observation_id=str(
            action.get("followup_evidence_intake_observation_id") or ""
        ),
        followup_sufficiency_recheck_id=str(
            action.get("followup_sufficiency_recheck_id") or ""
        ),
        recheck_id=str(action.get("recheck_id") or ""),
        followup_sufficiency_recheck_observation_id=str(
            action.get("followup_sufficiency_recheck_observation_id") or ""
        ),
        provider_job_kind=str(action.get("provider_job_kind") or ""),
        component_id=str(action.get("component_id") or ""),
        source_obligation_id=str(action.get("source_obligation_id") or ""),
        requirement_ids=tuple(_strings(action.get("requirement_ids"))),
        expected_source_classes=tuple(_strings(action.get("expected_source_classes"))),
        fixture_execution_mode=str(action.get("fixture_execution_mode") or ""),
        evidence_ledger_intake_mode=str(action.get("evidence_ledger_intake_mode") or ""),
        sufficiency_recheck_mode=str(action.get("sufficiency_recheck_mode") or ""),
        evidence_ledger_projection_digest=str(
            action.get("evidence_ledger_projection_digest") or ""
        ),
        sufficiency_judgment_digest=str(action.get("sufficiency_judgment_digest") or ""),
        followup_sufficiency_recheck_digest=str(
            action.get("followup_sufficiency_recheck_digest") or ""
        ),
        provider_execution_licensed=False,
        final_answer_packet_mode=FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
        author_activation_allowed=False,
        citation_rendering_changed=False,
        product_answer_behavior_changed=False,
        live_validation_not_run=True,
    )
    result = FollowupFinalAnswerPacketResult(
        result_id=f"followup-final-answer-packet-result:{action.get('recheck_id')}",
        status="fixture_final_answer_packet_prepared",
        packet_projection=packet_projection,
        final_evidence_refs=tuple(packet_projection.get("evidence_allowed") or ()),
        citation_eligibility_refs=tuple(
            tuple(packet_projection.get("citation_eligible") or ())
            + tuple(packet_projection.get("citation_ineligible") or ())
        ),
        packet_authority_payload=authority_payload,
        answer_readiness_posture={
            "readiness_status": packet_projection.get("readiness_status"),
            "readiness_reasons": packet_projection.get("readiness_reasons", []),
            "final_answer_allowed": packet_projection.get("final_answer_allowed"),
            "final_answer_posture": packet_projection.get("final_answer_posture"),
            "sufficiency_decision": packet_projection.get("sufficiency_decision"),
        },
        mandatory_caveats=tuple(
            _strings(packet_projection.get("mandatory_caveats"))
        ),
        prohibited_upgrades=tuple(
            _strings(packet_projection.get("prohibited_upgrades"))
        ),
        missing_required_obligations=tuple(
            _mappings(packet_projection.get("missing_required_obligations"))
            or _missing_source_obligations(packet)
        ),
        partial_obligations=tuple(_mappings(packet_projection.get("partial_obligations"))),
        satisfied_obligations=tuple(
            _mappings(packet_projection.get("satisfied_obligations"))
        ),
        source_bound_unknowns=tuple(
            _mappings(packet_projection.get("source_bound_numeric_unknowns"))
        ),
        unresolved_conflicts=tuple(_strings(sufficiency.get("unresolved_conflicts"))),
    )
    observation = FollowupFinalAnswerPacketObservation(
        observation_id=f"followup-final-answer-packet-observation:{action.get('recheck_id')}",
        request=request,
        result=result,
    )
    return FollowupFinalAnswerPacketConsumptionRecord(
        packet_preparation_id=(
            f"followup-final-answer-packet:{action.get('recheck_id')}"
        ),
        observation=observation,
    )


def followup_projection_digest(projection: Mapping[str, Any]) -> str:
    return stable_hash(safe_json(projection))


def _packet_sufficiency_projection(
    sufficiency: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
) -> dict[str, Any]:
    projection = dict(sufficiency)
    packet_inputs = _mapping(projection.get("final_packet_inputs"))
    mandatory = tuple(
        dict.fromkeys(
            _strings(packet_inputs.get("mandatory_caveats"))
            + _strings(projection.get("mandatory_caveats"))
            + _strings(recheck_state.get("mandatory_caveats"))
            + ("fixture_only_final_answer_packet_author_deferred",)
        )
    )
    prohibited = tuple(
        dict.fromkeys(
            _strings(packet_inputs.get("prohibited_upgrades"))
            + _strings(projection.get("prohibited_upgrades"))
            + _strings(recheck_state.get("prohibited_upgrades"))
            + (
                "do_not_activate_author_from_fixture_only_final_answer_packet",
                "do_not_convert_fixture_packet_to_product_answer_readiness",
            )
        )
    )
    packet_inputs.update(
        {
            "final_answer_allowed": False,
            "readiness_status": "blocked",
            "readiness_reasons": list(
                dict.fromkeys(
                    _strings(packet_inputs.get("readiness_reasons"))
                    + _strings(projection.get("readiness_reasons"))
                    + (
                        "fixture_only_final_answer_packet_author_deferred",
                        "product_answer_behavior_closed",
                    )
                )
            ),
            "mandatory_caveats": list(mandatory),
            "prohibited_upgrades": list(prohibited),
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "behavior_boundary_flags": {
                **_mapping(packet_inputs.get("behavior_boundary_flags")),
                **_behavior_boundary_flags(),
            },
        }
    )
    projection["final_answer_allowed"] = False
    projection["final_packet_inputs"] = packet_inputs
    projection["mandatory_caveats"] = list(mandatory)
    projection["prohibited_upgrades"] = list(prohibited)
    projection["author_activation_allowed"] = False
    projection["citation_behavior_changed"] = False
    projection["live_validation_not_run"] = True
    return projection


def _eligible_final_evidence_refs(
    ledger: Mapping[str, Any],
    *,
    action_inputs: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    expected_classes = set(_expected_source_classes(action_inputs))
    allowed_candidate_ids = _satisfied_candidate_ids(recheck_state, action_inputs)
    custody = {
        _mapping(record).get("candidate_id"): _mapping(record)
        for record in _list(ledger.get("custody_records"))
        if isinstance(record, Mapping)
    }
    refs: list[dict[str, Any]] = []
    for candidate in _mappings(ledger.get("candidate_records")):
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id or candidate_id not in allowed_candidate_ids:
            continue
        custody_record = custody.get(candidate_id, {})
        if custody_record.get("disposition") != "accepted":
            continue
        if candidate.get("fact_disposition") != "accepted":
            continue
        if expected_classes and candidate.get("source_class") not in expected_classes:
            continue
        if candidate.get("contextual_only") is True:
            continue
        if candidate.get("readable_status") in {"not_readable", "unreadable"}:
            continue
        refs.append(
            {
                "candidate_id": candidate_id,
                "source_id": candidate_id,
                "url": candidate.get("url"),
                "title": candidate.get("title") or candidate.get("source_label"),
                "domain": candidate.get("domain"),
                "source_tier": candidate.get("source_tier"),
                "source_class": candidate.get("source_class"),
                "text": "",
                "query_refs": [
                    item
                    for item in (
                        candidate.get("query_ref"),
                        candidate.get("retrieval_pass_id"),
                    )
                    if item
                ],
                "custody_ref": {
                    "authority": "RunKernel.EvidenceLedger",
                    "candidate_id": candidate_id,
                    "custody_observation_id": custody_record.get("observation_id"),
                    "requirement_id": custody_record.get("requirement_id"),
                    "disposition": custody_record.get("disposition"),
                    "reason": custody_record.get("reason"),
                },
            }
        )
    return tuple(refs)


def _satisfied_candidate_ids(
    recheck_state: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> set[str]:
    wanted_requirements = {
        _requirement_token(item)
        for item in _strings(action_inputs.get("requirement_ids"))
    }
    out: set[str] = set()
    for status in _mappings(recheck_state.get("source_requirement_statuses")):
        if status.get("status") != "satisfied":
            continue
        requirement_id = status.get("requirement_id")
        if wanted_requirements and _requirement_token(requirement_id) not in (
            wanted_requirements
        ):
            continue
        out.update(_strings(status.get("linked_candidate_ids")))
    return out


def _packet_authority_payload(packet: FinalAnswerPacket) -> dict[str, Any]:
    citation_source_ids = [
        item.get("source_id")
        for item in packet.to_dict().get("citation_eligible", [])
        if item.get("source_id") is not None
    ]
    citation_ineligible = packet.to_dict().get("citation_ineligible", [])
    missing = tuple(packet.missing_required_obligations) or _missing_source_obligations(
        packet
    )
    payload = packet.to_authority_payload(
        citation_source_ids=citation_source_ids,
        citation_ineligible_refs=citation_ineligible,
        missing_source_obligations=missing,
        partial_source_obligations=tuple(packet.partial_obligations),
        satisfied_source_obligations=tuple(packet.satisfied_obligations)
        or _satisfied_source_obligations(packet),
    )
    return {
        **payload,
        "fixture_only": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "not_for_product_answer_activation": True,
    }


def _with_fixture_packet_boundaries(packet: FinalAnswerPacket) -> FinalAnswerPacket:
    flags = {
        **_mapping(packet.behavior_boundary_flags),
        **_behavior_boundary_flags(),
    }
    refs = {
        **_mapping(packet.author_input_refs),
        "status": "author_execution_deferred",
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        "fixture_only": True,
        "not_for_product_answer_activation": True,
        "citation_formatter_invoked": False,
    }
    return replace(packet, behavior_boundary_flags=flags, author_input_refs=refs)


def _missing_source_obligations(packet: FinalAnswerPacket) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        obligation.to_dict()
        for obligation in packet.source_obligations
        if obligation.status is not SourceObligationStatus.SATISFIED
    )


def _satisfied_source_obligations(
    packet: FinalAnswerPacket,
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        obligation.to_dict()
        for obligation in packet.source_obligations
        if obligation.status is SourceObligationStatus.SATISFIED
    )


def _unique_source_urls(
    final_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        str(item.get("url")): item.get("source_id")
        for item in final_evidence
        if item.get("url") and item.get("source_id")
    }


def _expected_source_classes(action_inputs: Mapping[str, Any]) -> tuple[str, ...]:
    expected = tuple(
        item
        for item in _strings(action_inputs.get("expected_source_classes"))
        if item and item != "[redacted]"
    )
    if expected:
        return expected
    job_kind = clean_token(action_inputs.get("provider_job_kind"))
    by_job = {
        "official_current_candidate_acquisition": (
            "official_government",
            "official_current_rules",
        ),
        "legal_current_primary_acquisition": (
            "primary_legal",
            "legal_or_regulatory_text",
        ),
        "canonical_doc_acquisition": ("canonical", "primary_source_documents"),
        "source_bound_numeric_extraction_calculation_support": (
            "sourced_numeric_values",
        ),
        "conflict_currentness_check": ("current_primary_or_official",),
        "reconciliation_support": ("source_family_map",),
        "fetch_read_extract": ("answer_bearing_extract",),
    }
    return by_job.get(job_kind, ("answer_bearing_candidate",))


def _validate_recheck_state(state: Mapping[str, Any]) -> None:
    if state.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical recheck state")
    if state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
        raise PermissionError("follow-up packet requires RunKernel recheck state")
    if state.get("sufficiency_recheck_mode") != FOLLOWUP_SUFFICIENCY_RECHECK_MODE:
        raise PermissionError("follow-up packet requires fixture-only recheck mode")
    if state.get("provider_execution_licensed") is not False:
        raise PermissionError("provider execution is not licensed for packet prep")
    if state.get("final_answer_packet_deferred") is not True:
        raise PermissionError("follow-up packet requires previously deferred packet")
    if state.get("author_activation_allowed") is not False:
        raise PermissionError("follow-up packet requires Author activation closed")
    if state.get("citation_behavior_changed") is not False:
        raise PermissionError("follow-up packet requires unchanged citation behavior")
    flags = _mapping(state.get("behavior_boundary_flags"))
    for flag in _closed_surface_false_flags():
        if flags.get(flag) is not False:
            raise PermissionError(f"follow-up packet requires {flag}=False")
    if flags.get("sufficiency_judgment_rechecked") is not True:
        raise PermissionError("follow-up packet requires completed sufficiency recheck")


def _validate_sufficiency_projection(projection: Mapping[str, Any]) -> None:
    if projection.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
        raise PermissionError("follow-up packet requires canonical sufficiency owner")
    if projection.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical sufficiency")
    if projection.get("trace_only") is not False:
        raise PermissionError("SufficiencyJudgment projection must not be trace-only")
    packet_inputs = _mapping(projection.get("final_packet_inputs"))
    if (
        projection.get("author_activation_allowed") is True
        or packet_inputs.get("author_activation_allowed") is True
    ):
        raise PermissionError("SufficiencyJudgment must keep Author closed")
    if (
        projection.get("citation_behavior_changed") is True
        or packet_inputs.get("citation_behavior_changed") is True
    ):
        raise PermissionError("SufficiencyJudgment must keep citation behavior closed")
    if (
        projection.get("live_validation_not_run") is False
        or packet_inputs.get("live_validation_not_run") is False
    ):
        raise PermissionError("SufficiencyJudgment must record no live validation")


def _validate_ledger_projection(projection: Mapping[str, Any]) -> None:
    if projection.get("owner") != "RunKernel.EvidenceLedger":
        raise PermissionError("follow-up packet requires EvidenceLedger owner")
    if projection.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical EvidenceLedger")
    if projection.get("trace_only") is not False:
        raise PermissionError("EvidenceLedger projection must not be trace-only")


def _validate_intake_state(
    intake_state: Mapping[str, Any],
    action_inputs: Mapping[str, Any],
) -> None:
    if intake_state.get("canonical_state") is not True:
        raise PermissionError("follow-up packet requires canonical intake state")
    if intake_state.get("owner") != "RunKernel.FollowupEvidenceIntake":
        raise PermissionError("follow-up packet requires RunKernel intake state")
    if intake_state.get("intake_id") != action_inputs.get("intake_id"):
        raise PermissionError("follow-up packet intake_id mismatch")
    if intake_state.get("provider_execution_licensed") is not False:
        raise PermissionError("follow-up packet intake must keep provider unlicensed")


def _validate_action_inputs(
    action_inputs: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
    sufficiency_projection: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    intake_state: Mapping[str, Any],
) -> None:
    for field in (
        "run_id",
        "checkpoint_id",
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "followup_evidence_intake_id",
        "intake_id",
        "followup_evidence_intake_observation_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
        "sufficiency_recheck_mode",
    ):
        if action_inputs.get(field) != recheck_state.get(field):
            raise PermissionError(f"authorized follow-up packet {field} mismatch")
    for field in (
        "followup_authorization_consumption_id",
        "sealed_candidate_id",
        "followup_execution_id",
        "execution_id",
        "followup_execution_observation_id",
        "intake_id",
        "provider_job_kind",
        "component_id",
        "source_obligation_id",
        "fixture_execution_mode",
        "evidence_ledger_intake_mode",
    ):
        if action_inputs.get(field) != intake_state.get(field):
            raise PermissionError(
                f"authorized follow-up packet intake {field} mismatch"
            )
    for action_field, state_field in (
        ("followup_evidence_intake_id", "intake_id"),
        ("followup_evidence_intake_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != intake_state.get(state_field):
            raise PermissionError(
                f"authorized follow-up packet intake {action_field} mismatch"
            )
    for action_field, state_field in (
        ("followup_sufficiency_recheck_id", "recheck_id"),
        ("recheck_id", "recheck_id"),
        ("followup_sufficiency_recheck_observation_id", "observation_id"),
    ):
        if action_inputs.get(action_field) != recheck_state.get(state_field):
            raise PermissionError(
                f"authorized follow-up packet {action_field} mismatch"
            )
    if _strings(action_inputs.get("requirement_ids")) != _strings(
        recheck_state.get("requirement_ids")
    ):
        raise PermissionError("authorized follow-up packet requirement_ids mismatch")
    if _strings(action_inputs.get("expected_source_classes")) != (
        _expected_source_classes(recheck_state)
    ):
        raise PermissionError(
            "authorized follow-up packet expected_source_classes mismatch"
        )
    if action_inputs.get("provider_execution_licensed") is not False:
        raise PermissionError("follow-up packet must keep provider unlicensed")
    if action_inputs.get("final_answer_packet_mode") != (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    ):
        raise PermissionError("follow-up packet action must be fixture-only")
    if action_inputs.get("author_activation_allowed") is not False:
        raise PermissionError("follow-up packet action must keep Author closed")
    if action_inputs.get("citation_rendering_changed") is not False:
        raise PermissionError("follow-up packet action must not render citations")
    if action_inputs.get("product_answer_behavior_changed") is not False:
        raise PermissionError("follow-up packet action must not change product answers")
    if action_inputs.get("live_validation_not_run") is not True:
        raise PermissionError("follow-up packet action must not run live validation")
    if action_inputs.get("evidence_ledger_projection_digest") != (
        evidence_ledger_projection_digest(evidence_ledger_projection)
    ):
        raise PermissionError("follow-up packet EvidenceLedger digest mismatch")
    if action_inputs.get("sufficiency_judgment_digest") != (
        followup_projection_digest(sufficiency_projection)
    ):
        raise PermissionError("follow-up packet SufficiencyJudgment digest mismatch")
    if action_inputs.get("followup_sufficiency_recheck_digest") != (
        followup_projection_digest(recheck_state)
    ):
        raise PermissionError("follow-up packet recheck digest mismatch")


def _behavior_boundary_flags() -> dict[str, bool]:
    return {
        **followup_live_surface_flags(),
        **{flag: False for flag in FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS},
        "sufficiency_judgment_rechecked": True,
        "final_answer_packet_prepared": True,
        "final_answer_packet_updated": True,
        "author_activation_allowed": False,
        "author_execution_deferred": True,
        **followup_closed_flags(
            *FOLLOWUP_AUTHOR_CITATION_PRODUCT_RUNTIME_FALSE_FLAGS
        ),
        "live_validation_not_run": True,
    }


def _closed_surface_false_flags() -> tuple[str, ...]:
    return (
        *FOLLOWUP_LIVE_SURFACE_FALSE_FLAGS[1:],
        *FOLLOWUP_SEARCH_RECHECK_FALSE_FLAGS,
        "final_answer_packet_updated",
        "final_answer_behavior_changed",
        "author_prose_behavior_changed",
        "citation_behavior_changed",
    )


def _fixture_only_provenance() -> dict[str, Any]:
    return followup_fixture_provenance(
        intake_bridge="ag96i2c_followup_evidence_ledger_intake",
        recheck_bridge="ag96i2d_followup_sufficiency_recheck",
        packet_bridge="ag96i2e_followup_final_answer_packet_prepare",
        author_executor_connected=False,
    )


def _redaction_posture() -> dict[str, bool]:
    return followup_common_redaction_posture()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mappings(value: Any) -> tuple[dict[str, Any], ...]:
    return tuple(dict(item) for item in _list(value) if isinstance(item, Mapping))


def _list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return []


def _strings(value: Any) -> tuple[str, ...]:
    if value is None or isinstance(value, str):
        values = (value,) if value else ()
    elif isinstance(value, Sequence):
        values = tuple(value)
    else:
        values = (value,)
    out: list[str] = []
    for item in values:
        token = clean_token(item)
        if token and token not in out:
            out.append(token)
    return tuple(out)


def _requirement_token(value: Any) -> str:
    token = clean_token(value) or ""
    if token.startswith("source_requirement:"):
        token = token.split(":", 1)[1]
    if token.startswith("source_requirement_"):
        token = token.removeprefix("source_requirement_")
    return token


__all__ = [
    "FOLLOWUP_FINAL_ANSWER_PACKET_GATE_REASON",
    "FOLLOWUP_FINAL_ANSWER_PACKET_MODE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_SCHEMA_VERSION",
    "FOLLOWUP_FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_TRACE_KEY",
    "FollowupFinalAnswerPacketActionResult",
    "FollowupFinalAnswerPacketConsumptionRecord",
    "FollowupFinalAnswerPacketObservation",
    "FollowupFinalAnswerPacketRequest",
    "FollowupFinalAnswerPacketResult",
    "build_followup_final_answer_packet_record",
    "execute_followup_final_answer_packet_prepare_action",
    "followup_projection_digest",
]
