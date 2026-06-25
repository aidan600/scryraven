"""Canonical RunKernel state, actions, observations, and trace projection.

AG-91H intentionally keeps this spine small. It authorizes bounded runtime
actions, reduces executor observations into RunState, and projects trace from
that state. It does not call models, search providers, persistence, prompts, or
ranking/citation/final-answer code.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence

from core.component_coverage_reduction_runtime import (
    COMPONENT_COVERAGE_REDUCTION_REASON,
    ComponentCoverageReductionError,
    build_component_coverage_reduction_projection,
    build_component_coverage_reduction_state,
)
from core.component_coverage_reduction_runtime import (
    COMPONENT_COVERAGE_REDUCTION_STAGE as COMPONENT_COVERAGE_REDUCTION_STAGE_NAME,
)
from core.contract_amendment_admission_runtime import (
    CONTRACT_AMENDMENT_ADMISSION_REASON,
    ContractAmendmentAdmissionError,
    build_contract_amendment_admission_projection,
    build_contract_amendment_admission_state,
)
from core.contract_amendment_admission_runtime import (
    CONTRACT_AMENDMENT_ADMISSION_STAGE as CONTRACT_AMENDMENT_ADMISSION_STAGE_NAME,
)
from core.evidence_ledger import EvidenceLedger
from core.final_answer_packet import _safe_json
from core.followup_author_evidence_content_bridge_runtime import (
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_REASON,
    af4b2_authority_projection_from_record,
    af4b2_packet_projection_from_record,
    build_followup_author_evidence_content_bridge_action_inputs,
    build_followup_author_evidence_content_bridge_projection,
    build_followup_author_evidence_content_bridge_record,
    build_run_kernel_followup_author_evidence_content_bridge_state,
    reject_followup_author_evidence_content_bridge_input_spoof,
    validate_followup_author_evidence_content_bridge_observation_binding,
)
from core.followup_author_evidence_content_bridge_runtime import (
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE as FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE_NAME,
)
from core.followup_author_execution_activation_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REASON,
    build_followup_author_execution_activation_action_inputs,
    build_followup_author_execution_activation_projection,
    build_followup_author_execution_activation_record,
    build_run_kernel_followup_author_execution_activation_state,
    reject_followup_author_execution_activation_input_spoof,
    validate_followup_author_execution_activation_observation_binding,
    y_authority_projection_from_record,
    y_packet_projection_from_record,
)
from core.followup_author_execution_activation_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE as FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE_NAME,
)
from core.followup_author_execution_from_ad_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_REASON,
    ae_authority_projection_from_record,
    ae_packet_projection_from_record,
    build_followup_author_execution_from_ad_action_inputs,
    build_followup_author_execution_from_ad_projection,
    build_followup_author_execution_from_ad_record,
    build_run_kernel_followup_author_execution_from_ad_state,
    reject_followup_author_execution_from_ad_input_spoof,
    validate_followup_author_execution_from_ad_observation_binding,
)
from core.followup_author_execution_from_ad_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE as FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE_NAME,
)
from core.followup_author_execution_from_af4d_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_REASON,
    build_followup_author_execution_from_af4d_action_inputs,
    build_followup_author_execution_from_af4d_projection,
    build_followup_author_execution_from_af4d_record,
    build_run_kernel_followup_author_execution_from_af4d_state,
    reject_followup_author_execution_from_af4d_input_spoof,
    validate_followup_author_execution_from_af4d_authorization,
    validate_followup_author_execution_from_af4d_observation_binding,
)
from core.followup_author_execution_from_af4d_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE as FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE_NAME,
)
from core.followup_author_execution_readiness_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_REASON,
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS,
    build_followup_author_execution_readiness_action_inputs,
    build_followup_author_execution_readiness_projection,
    build_followup_author_execution_readiness_record,
    validate_followup_author_execution_readiness_observation_binding,
)
from core.followup_author_execution_readiness_runtime import (
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE as FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE_NAME,
)
from core.followup_author_gate_runtime import (
    AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
    AG96I3V1_U1_BOUND_AUTHOR_GATE_REASON,
    FOLLOWUP_AUTHOR_GATE_MODE,
    build_followup_author_gate_record,
    build_followup_u1_bound_author_gate_record,
    validate_followup_u1_bound_author_gate_observation_binding,
)
from core.followup_author_gate_runtime import (
    FOLLOWUP_AUTHOR_GATE_STAGE as FOLLOWUP_AUTHOR_GATE_STAGE_NAME,
)
from core.followup_author_input_authority_runtime import (
    AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_INPUT_AUTHORITY_GATE_REASON,
    FOLLOWUP_AUTHOR_INPUT_REFS_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
    build_followup_author_input_authority_record,
    u1_packet_projection_from_record,
    validate_followup_author_input_authority_observation_binding,
)
from core.followup_author_input_authority_runtime import (
    FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE as FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE_NAME,
)
from core.followup_author_input_materialization_runtime import (
    AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE,
    FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_REASON,
    FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS,
    build_followup_author_input_materialization_action_inputs,
    build_followup_author_input_materialization_projection,
    build_followup_author_input_materialization_record,
    reject_followup_author_input_materialization_input_spoof,
    validate_followup_author_input_materialization_observation_binding,
)
from core.followup_author_input_materialization_runtime import (
    AUTHOR_INPUT_MATERIALIZATION_FALSE_FLAGS as _FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_FALSE_FLAGS,
)
from core.followup_author_input_materialization_runtime import (
    FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE as FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE_NAME,
)
from core.followup_author_invocation_construction_runtime import (
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_REASON,
    af4_authority_projection_from_record,
    af4_packet_projection_from_record,
    build_followup_author_invocation_construction_action_inputs,
    build_followup_author_invocation_construction_projection,
    build_followup_author_invocation_construction_record,
    build_run_kernel_followup_author_invocation_construction_state,
    reject_followup_author_invocation_construction_input_spoof,
    validate_followup_author_invocation_construction_observation_binding,
)
from core.followup_author_invocation_construction_runtime import (
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE as FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE_NAME,
)
from core.followup_author_model_request_assembly_runtime import (
    FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_REASON,
    build_followup_author_model_request_assembly_action_inputs,
    build_followup_author_model_request_assembly_projection,
    build_followup_author_model_request_assembly_record,
    build_run_kernel_followup_author_model_request_assembly_state,
    reject_followup_author_model_request_assembly_input_spoof,
    validate_followup_author_model_request_assembly_observation_binding,
)
from core.followup_author_model_request_assembly_runtime import (
    FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE as FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE_NAME,
)
from core.followup_author_observation_runtime import (
    FOLLOWUP_AUTHOR_OBSERVATION_MODE,
    build_followup_author_observation_record,
    derive_followup_author_observation_compliance,
    reject_followup_author_observation_boundary_spoof,
)
from core.followup_author_observation_runtime import (
    FOLLOWUP_AUTHOR_OBSERVATION_STAGE as FOLLOWUP_AUTHOR_OBSERVATION_STAGE_NAME,
)
from core.followup_author_payload_authority_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REASON,
    ac_authority_projection_from_record,
    ac_packet_projection_from_record,
    build_followup_author_payload_authority_action_inputs,
    build_followup_author_payload_authority_projection,
    build_followup_author_payload_authority_record,
    build_run_kernel_followup_author_payload_authority_state,
    reject_followup_author_payload_authority_input_spoof,
    validate_followup_author_payload_authority_observation_binding,
)
from core.followup_author_payload_authority_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE as FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE_NAME,
)
from core.followup_author_payload_construction_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_REASON,
    ad_authority_projection_from_record,
    ad_packet_projection_from_record,
    build_followup_author_payload_construction_action_inputs,
    build_followup_author_payload_construction_projection,
    build_followup_author_payload_construction_record,
    build_run_kernel_followup_author_payload_construction_state,
    reject_followup_author_payload_construction_input_spoof,
    validate_followup_author_payload_construction_observation_binding,
)
from core.followup_author_payload_construction_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE as FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE_NAME,
)
from core.followup_author_prompt_assembly_manifest_runtime import (
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REASON,
    build_followup_author_prompt_assembly_manifest_action_inputs,
    build_followup_author_prompt_assembly_manifest_projection,
    build_followup_author_prompt_assembly_manifest_record,
    build_run_kernel_followup_author_prompt_assembly_manifest_state,
    reject_followup_author_prompt_assembly_manifest_input_spoof,
    validate_followup_author_prompt_assembly_manifest_observation_binding,
    z_authority_projection_from_record,
    z_packet_projection_from_record,
)
from core.followup_author_prompt_assembly_manifest_runtime import (
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE as FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE_NAME,
)
from core.followup_author_response_finalization_runtime import (
    FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_REASON,
    build_followup_author_response_finalization_action_inputs,
    build_followup_author_response_finalization_projection,
    build_followup_author_response_finalization_record,
    build_run_kernel_followup_author_response_finalization_state,
    reject_followup_author_response_finalization_input_spoof,
    validate_followup_author_response_finalization_authorization,
    validate_followup_author_response_finalization_observation_binding,
)
from core.followup_author_response_finalization_runtime import (
    FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE as FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE_NAME,
)
from core.followup_citation_rendering_runtime import (
    AG96I3T1_CITATION_RENDERING_MODE,
    FOLLOWUP_CITATION_RENDERING_GATE_REASON,
    build_followup_citation_rendering_record,
)
from core.followup_citation_rendering_runtime import (
    FOLLOWUP_CITATION_RENDERING_STAGE as FOLLOWUP_CITATION_RENDERING_STAGE_NAME,
)
from core.followup_citation_source_handoff_runtime import (
    AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
    FOLLOWUP_CITATION_SOURCE_HANDOFF_GATE_REASON,
    build_followup_citation_source_handoff_record,
)
from core.followup_citation_source_handoff_runtime import (
    FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE as FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE_NAME,
)
from core.followup_final_answer_packet_runtime import (
    AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE,
    AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE,
    AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE,
    AG96I3Q1_CITATION_ELIGIBILITY_MODE,
    FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_GATE_REASON,
    FOLLOWUP_CITATION_ELIGIBILITY_GATE_REASON,
    FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
    FOLLOWUP_FINAL_EVIDENCE_SELECTION_GATE_REASON,
    build_followup_blocked_final_answer_packet_shell_record,
    build_followup_citation_eligibility_record,
    build_followup_final_answer_packet_readiness_record,
    build_followup_final_answer_packet_record,
    build_followup_final_evidence_selection_record,
    followup_projection_digest,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE as FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE_NAME,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_CITATION_ELIGIBILITY_STAGE as FOLLOWUP_CITATION_ELIGIBILITY_STAGE_NAME,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE as FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE_NAME,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_FINAL_ANSWER_PACKET_STAGE as FOLLOWUP_FINAL_ANSWER_PACKET_STAGE_NAME,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE as FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE_NAME,
)
from core.followup_provider_job_execution_runtime import (
    FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND,
    FOLLOWUP_PROVIDER_JOB_EXECUTION_GATE_REASON,
    FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
)
from core.followup_runkernel_reducers import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
    FollowupRunKernelReducerError,
    ag96i3m2_admission_review_authorization_projection,
    ag96i3m2_intake_binding_authorization_projection,
    build_final_answer_authority_projection,
    build_followup_author_gate_projection,
    build_followup_author_observation_projection,
    build_followup_authorization_projection,
    build_followup_blocked_final_answer_packet_shell_projection,
    build_followup_citation_eligibility_projection,
    build_followup_citation_rendering_projection,
    build_followup_citation_source_handoff_projection,
    build_followup_evidence_intake_ledger_observation,
    build_followup_evidence_intake_projection,
    build_followup_execution_projection,
    build_followup_final_answer_packet_projection,
    build_followup_final_answer_packet_readiness_projection,
    build_followup_final_evidence_selection_projection,
    build_followup_sufficiency_recheck_projection,
    followup_evidence_intake_outcome,
    followup_expected_source_classes,
    followup_sealed_candidate,
    require_followup_flags_false,
    validate_followup_author_gate_observation_binding,
    validate_followup_author_observation_binding,
    validate_followup_blocked_final_answer_packet_shell_observation_binding,
    validate_followup_citation_eligibility_observation_binding,
    validate_followup_citation_rendering_observation_binding,
    validate_followup_citation_source_handoff_observation_binding,
    validate_followup_evidence_intake_action_binding,
    validate_followup_execution_action_binding,
    validate_followup_final_answer_packet_observation_binding,
    validate_followup_final_answer_packet_readiness_observation_binding,
    validate_followup_final_evidence_selection_observation_binding,
    validate_followup_provider_job_execution_action_binding,
    validate_followup_sufficiency_recheck_observation_binding,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_FALSE_FLAGS as _FOLLOWUP_AUTHOR_EXECUTION_READINESS_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS as _FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS as _FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_BLOCKED_PACKET_SHELL_FALSE_FLAGS as _FOLLOWUP_BLOCKED_PACKET_SHELL_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_CITATION_ELIGIBILITY_FALSE_FLAGS as _FOLLOWUP_CITATION_ELIGIBILITY_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_CITATION_RENDERING_FALSE_FLAGS as _FOLLOWUP_CITATION_RENDERING_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_CITATION_SOURCE_HANDOFF_FALSE_FLAGS as _FOLLOWUP_CITATION_SOURCE_HANDOFF_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_EXECUTION_FALSE_FLAGS as _FOLLOWUP_EXECUTION_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_FINAL_EVIDENCE_SELECTION_FALSE_FLAGS as _FOLLOWUP_FINAL_EVIDENCE_SELECTION_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_INTAKE_FALSE_FLAGS as _FOLLOWUP_INTAKE_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_PACKET_FALSE_FLAGS as _FOLLOWUP_PACKET_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_PACKET_READINESS_FALSE_FLAGS as _FOLLOWUP_PACKET_READINESS_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS as _FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS,
)
from core.followup_runkernel_reducers import (
    FOLLOWUP_RECHECK_FALSE_FLAGS as _FOLLOWUP_RECHECK_FALSE_FLAGS,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    build_followup_sufficiency_recheck_record,
    evidence_ledger_custody_summary,
    evidence_ledger_projection_digest,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_STAGE as FOLLOWUP_SUFFICIENCY_RECHECK_STAGE_NAME,
)
from core.initial_answer_contract_acceptance_runtime import (
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_REASON,
    InitialAnswerContractAcceptanceError,
    build_initial_answer_contract_acceptance_projection,
    build_initial_answer_contract_acceptance_state,
)
from core.initial_answer_contract_acceptance_runtime import (
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE as INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE_NAME,
)
from core.semantic_observation_admission_runtime import (
    SEMANTIC_OBSERVATION_ADMISSION_REASON,
    SemanticObservationAdmissionError,
    build_semantic_observation_admission_projection,
    build_semantic_observation_admission_state,
)
from core.semantic_observation_admission_runtime import (
    SEMANTIC_OBSERVATION_ADMISSION_STAGE as SEMANTIC_OBSERVATION_ADMISSION_STAGE_NAME,
)
from core.semantic_producer_bundle_commit_runtime import (
    SemanticProducerBundleCommitStagingError,
    normalize_semantic_producer_bundle_payload,
    stage_semantic_producer_bundle_commit,
)

RUN_KERNEL_TRACE_KEY = "run_kernel"

ROUTE_REQUEST_STAGE = "route_request"
QUERY_PRODUCTION_STAGE = "query_production"
QUERY_PLAN_ADMISSION_STAGE = "query_plan_admission"
RUN_CONTRACT_STAGE = "run_contract"
INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE = (
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE_NAME
)
SEMANTIC_OBSERVATION_ADMISSION_STAGE = (
    SEMANTIC_OBSERVATION_ADMISSION_STAGE_NAME
)
COMPONENT_COVERAGE_REDUCTION_STAGE = COMPONENT_COVERAGE_REDUCTION_STAGE_NAME
RECOVERED_SEMANTIC_DELTA_COMMIT_STAGE = (
    "component_gap_recovery_semantic_delta_commit"
)
SEMANTIC_PRODUCER_BUNDLE_COMMIT_STAGE = "semantic_producer_bundle_commit"
SEMANTIC_PRODUCER_BUNDLE_COMMIT_REASON = (
    "ordinary_semantic_producer_atomic_bundle_commit"
)
RECOVERED_SEMANTIC_DELTA_COMMIT_REASON = (
    "component_gap_recovery_atomic_semantic_delta_commit"
)
CONTRACT_AMENDMENT_ADMISSION_STAGE = CONTRACT_AMENDMENT_ADMISSION_STAGE_NAME
SEARCH_WORK_PLAN_CONSTRUCTION_STAGE = "search_work_plan_construction"
MAIN_RETRIEVAL_STAGE = "main_retrieval"
RETRIEVAL_STOP_CHECKPOINT_STAGE = "retrieval_stop_checkpoint"
EVIDENCE_LEDGER_STAGE = "evidence_ledger"
SEARCH_JUDGMENT_STAGE = "search_judgment"
SUFFICIENCY_JUDGMENT_STAGE = "sufficiency_judgment"
FINAL_ANSWER_PACKET_STAGE = "final_answer_packet"
AUTHOR_EXECUTION_STAGE = "author_execution"
FOLLOWUP_AUTHORIZATION_STAGE = "followup_authorization_consumption"
FOLLOWUP_EXECUTION_STAGE = "followup_fixture_execution"
FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE = "followup_provider_job_execution"
FOLLOWUP_EVIDENCE_INTAKE_STAGE = "followup_evidence_intake"
FOLLOWUP_SUFFICIENCY_RECHECK_STAGE = FOLLOWUP_SUFFICIENCY_RECHECK_STAGE_NAME
FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE = (
    FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE_NAME
)
FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE = (
    FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE_NAME
)
FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE = (
    FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE_NAME
)
FOLLOWUP_CITATION_ELIGIBILITY_STAGE = FOLLOWUP_CITATION_ELIGIBILITY_STAGE_NAME
FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE = FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE_NAME
FOLLOWUP_CITATION_RENDERING_STAGE = FOLLOWUP_CITATION_RENDERING_STAGE_NAME
FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE = FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE_NAME
FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE = (
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE_NAME
)
FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE = (
    FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE_NAME
)
FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE = (
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE_NAME
)
FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE = (
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE_NAME
)
FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE = FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE_NAME
FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE = (
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE_NAME
)
FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE = (
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE_NAME
)
FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE = (
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE_NAME
)
FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE = (
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE_NAME
)
FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE = (
    FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE_NAME
)
FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE = (
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE_NAME
)
FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE = (
    FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE_NAME
)
FOLLOWUP_FINAL_ANSWER_PACKET_STAGE = FOLLOWUP_FINAL_ANSWER_PACKET_STAGE_NAME
FOLLOWUP_AUTHOR_GATE_STAGE = FOLLOWUP_AUTHOR_GATE_STAGE_NAME
FOLLOWUP_AUTHOR_OBSERVATION_STAGE = FOLLOWUP_AUTHOR_OBSERVATION_STAGE_NAME

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "db",
        "db_row",
        "full_trace",
        "log",
        "logs",
        "output",
        "output_artifact",
        "output_packet",
        "password",
        "prompt",
        "provider_payload",
        "raw_model_response",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_trace",
        "secret",
        "secrets",
        "token",
    }
)

class ActionType(str, Enum):
    """Bounded action vocabulary authorized by RunKernel."""

    ROUTE_REQUEST = "route_request"
    RUN_CONTRACT_SYNTHESIZE = "run_contract_synthesize"
    INITIAL_ANSWER_CONTRACT_ACCEPT = "initial_answer_contract_accept"
    SEMANTIC_OBSERVATION_ADMIT = "semantic_observation_admit"
    COMPONENT_COVERAGE_REDUCE = "component_coverage_reduce"
    RECOVERED_SEMANTIC_DELTA_COMMIT = (
        "component_gap_recovery_semantic_delta_commit"
    )
    SEMANTIC_PRODUCER_BUNDLE_COMMIT = "semantic_producer_bundle_commit"
    CONTRACT_AMENDMENT_ADMIT = "contract_amendment_admit"
    SEARCH_WORK_PLAN_CONSTRUCT = "search_work_plan_construct"
    QUERY_PRODUCTION = "query_production"
    QUERY_PLAN_ADMISSION = "query_plan_admission"
    MAIN_RETRIEVAL_PASS = "main_retrieval_pass"
    RETRIEVAL_STOP_CHECKPOINT = "retrieval_stop_checkpoint"
    EVIDENCE_LEDGER_REDUCE = "evidence_ledger_reduce"
    SEARCH_JUDGMENT_DECIDE = "search_judgment_decide"
    SUFFICIENCY_JUDGMENT_DECIDE = "sufficiency_judgment_decide"
    FINAL_ANSWER_PACKET_PREPARE = "final_answer_packet_prepare"
    AUTHOR_EXECUTE = "author_execute"
    FOLLOWUP_AUTHORIZATION_CONSUME = "followup_authorization_consume"
    FOLLOWUP_FIXTURE_EXECUTE = "followup_fixture_execute"
    FOLLOWUP_PROVIDER_JOB_EXECUTE = "followup_provider_job_execute"
    FOLLOWUP_EVIDENCE_INTAKE = "followup_evidence_intake"
    FOLLOWUP_SUFFICIENCY_RECHECK = "followup_sufficiency_recheck"
    FOLLOWUP_FINAL_ANSWER_PACKET_READINESS = (
        "followup_final_answer_packet_readiness"
    )
    FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL = (
        "followup_blocked_final_answer_packet_shell"
    )
    FOLLOWUP_FINAL_EVIDENCE_SELECTION = "followup_final_evidence_selection"
    FOLLOWUP_CITATION_ELIGIBILITY = "followup_citation_eligibility"
    FOLLOWUP_CITATION_SOURCE_HANDOFF = "followup_citation_source_handoff"
    FOLLOWUP_CITATION_RENDERING = "followup_citation_rendering"
    FOLLOWUP_AUTHOR_INPUT_AUTHORITY = "followup_author_input_authority"
    FOLLOWUP_AUTHOR_EXECUTION_READINESS = "followup_author_execution_readiness"
    FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION = (
        "followup_author_input_materialization"
    )
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION = (
        "followup_author_execution_activation"
    )
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST = (
        "followup_author_prompt_assembly_manifest"
    )
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY = "followup_author_payload_authority"
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION = "followup_author_payload_construction"
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE = (
        "followup_author_evidence_content_bridge"
    )
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AD = "followup_author_execution_from_ad"
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION = (
        "followup_author_invocation_construction"
    )
    FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY = (
        "followup_author_model_request_assembly"
    )
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D = "followup_author_execution_from_af4d"
    FOLLOWUP_AUTHOR_RESPONSE_FINALIZE = "followup_author_response_finalize"
    FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE = "followup_final_answer_packet_prepare"
    FOLLOWUP_AUTHOR_GATE = "followup_author_gate"
    FOLLOWUP_AUTHOR_OBSERVATION = "followup_author_observation"


class ObservationType(str, Enum):
    """Observation vocabulary returned by bounded executors/adapters."""

    ROUTE_RESULT = "route_result"
    RUN_CONTRACT_SYNTHESIZED = "run_contract_synthesized"
    INITIAL_ANSWER_CONTRACT_ACCEPTED = "initial_answer_contract_accepted"
    SEMANTIC_OBSERVATION_ADMITTED = "semantic_observation_admitted"
    COMPONENT_COVERAGE_REDUCED = "component_coverage_reduced"
    RECOVERED_SEMANTIC_DELTA_COMMITTED = (
        "component_gap_recovery_semantic_delta_committed"
    )
    SEMANTIC_PRODUCER_BUNDLE_COMMITTED = "semantic_producer_bundle_committed"
    CONTRACT_AMENDMENT_ADMITTED = "contract_amendment_admitted"
    SEARCH_WORK_PLAN_CONSTRUCTED = "search_work_plan_constructed"
    QUERY_CANDIDATES_PRODUCED = "query_candidates_produced"
    QUERY_PLAN_ADMITTED = "query_plan_admitted"
    RETRIEVAL_PASS_RESULT = "retrieval_pass_result"
    RETRIEVAL_STOP_DECISION = "retrieval_stop_decision"
    EVIDENCE_CUSTODY_OBSERVED = "evidence_custody_observed"
    SEARCH_JUDGMENT_DECIDED = "search_judgment_decided"
    SUFFICIENCY_JUDGMENT_DECIDED = "sufficiency_judgment_decided"
    FINAL_ANSWER_PACKET_PREPARED = "final_answer_packet_prepared"
    AUTHOR_OUTPUT_OBSERVED = "author_output_observed"
    FOLLOWUP_AUTHORIZATION_CONSUMED = "followup_authorization_consumed"
    FOLLOWUP_EXECUTION_OBSERVED = "followup_execution_observed"
    FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED = (
        "followup_provider_job_execution_observed"
    )
    FOLLOWUP_EVIDENCE_INTAKE_OBSERVED = "followup_evidence_intake_observed"
    FOLLOWUP_SUFFICIENCY_RECHECK_OBSERVED = (
        "followup_sufficiency_recheck_observed"
    )
    FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED = (
        "followup_final_answer_packet_prepared"
    )
    FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_PREPARED = (
        "followup_final_answer_packet_readiness_prepared"
    )
    FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_PREPARED = (
        "followup_blocked_final_answer_packet_shell_prepared"
    )
    FOLLOWUP_FINAL_EVIDENCE_SELECTION_PREPARED = (
        "followup_final_evidence_selection_prepared"
    )
    FOLLOWUP_CITATION_ELIGIBILITY_PREPARED = (
        "followup_citation_eligibility_prepared"
    )
    FOLLOWUP_CITATION_SOURCE_HANDOFF_PREPARED = (
        "followup_citation_source_handoff_prepared"
    )
    FOLLOWUP_CITATION_RENDERING_PREPARED = (
        "followup_citation_rendering_prepared"
    )
    FOLLOWUP_AUTHOR_INPUT_AUTHORITY_PREPARED = (
        "followup_author_input_authority_prepared"
    )
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_PREPARED = (
        "followup_author_execution_readiness_prepared"
    )
    FOLLOWUP_AUTHOR_INPUT_MATERIALIZED = (
        "followup_author_input_materialized"
    )
    FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_PREPARED = (
        "followup_author_execution_activation_prepared"
    )
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_PREPARED = (
        "followup_author_prompt_assembly_manifest_prepared"
    )
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_PREPARED = (
        "followup_author_payload_authority_prepared"
    )
    FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTED = (
        "followup_author_payload_constructed"
    )
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGED = (
        "followup_author_evidence_content_bridged"
    )
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_OBSERVED = (
        "followup_author_execution_from_ad_observed"
    )
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED = (
        "followup_author_invocation_constructed"
    )
    FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED = (
        "followup_author_model_request_assembled"
    )
    FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_OBSERVED = (
        "followup_author_execution_from_af4d_observed"
    )
    FOLLOWUP_AUTHOR_RESPONSE_FINALIZED = (
        "followup_author_response_finalized"
    )
    FOLLOWUP_AUTHOR_GATE_OBSERVED = "followup_author_gate_observed"
    FOLLOWUP_AUTHOR_OBSERVATION_OBSERVED = (
        "followup_author_observation_observed"
    )


class RunStageStatus(str, Enum):
    """Compact stage/action lifecycle status."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    COMPLETED = "completed"
    FAILED = "failed"


class RunKernelTransitionError(ValueError):
    """Raised when an observation does not match the authorized transition."""


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    return text[:limit]


def _json_safe(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _clean_text(value, limit=800)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _clean_text(key, limit=100)
            if not key_text:
                continue
            if key_text.casefold() in _SENSITIVE_KEYS:
                out[key_text] = "[redacted]"
            else:
                out[key_text] = _json_safe(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        ordered = list(value)
        if isinstance(value, (set, frozenset)):
            ordered = sorted(ordered, key=str)
        return [_json_safe(item, depth=depth + 1) for item in ordered[:80]]
    return _clean_text(value, limit=300)


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _json_safe(dict(value or {}))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _stable_packet_safe_json_digest(value: Any) -> str:
    canonical_json = json.dumps(
        _safe_json(value),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def _safe_semantic_consumption(value: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _safe_mapping(value)
    if not isinstance(value, Mapping):
        return safe
    raw_projection = value.get("semantic_ref_projection")
    if not isinstance(raw_projection, Mapping):
        return safe

    from core.sufficiency_semantic_state_consumption_runtime import (
        _safe_semantic_ref_projection,
    )

    semantic_ref_projection = _safe_semantic_ref_projection(raw_projection)
    if semantic_ref_projection:
        safe["semantic_ref_projection"] = semantic_ref_projection
    return safe


def _validation_status(validation: Mapping[str, Any]) -> str | None:
    status = validation.get("status")
    if status:
        return str(status)
    ok = validation.get("ok")
    if ok is True:
        return "ok"
    if ok is False:
        return "errors"
    plan_validation = validation.get("search_work_plan")
    if isinstance(plan_validation, Mapping):
        if plan_validation.get("ok") is True:
            return "ok"
        if plan_validation.get("ok") is False:
            return "errors"
    return None


@dataclass(frozen=True, slots=True)
class AuthorizedAction:
    """One bounded action RunKernel authorizes an executor/adapter to consume."""

    action_id: str
    run_id: str
    stage: str
    action_type: ActionType
    reason: str
    inputs: Mapping[str, Any]
    expected_observation_type: ObservationType
    sequence: int

    def __post_init__(self) -> None:
        if not _clean_text(self.action_id, limit=120):
            raise ValueError("authorized action requires action_id")
        if not _clean_text(self.run_id, limit=120):
            raise ValueError("authorized action requires run_id")
        if not _clean_text(self.stage, limit=120):
            raise ValueError("authorized action requires stage")
        if int(self.sequence or 0) <= 0:
            raise ValueError("authorized action sequence must be positive")
        object.__setattr__(self, "action_type", ActionType(self.action_type))
        object.__setattr__(
            self,
            "expected_observation_type",
            ObservationType(self.expected_observation_type),
        )
        object.__setattr__(self, "inputs", _safe_mapping(self.inputs))

    def validate(
        self,
        *,
        action_type: ActionType | str,
        stage: str,
        expected_observation_type: ObservationType | str | None = None,
    ) -> None:
        expected_action_type = ActionType(action_type)
        if self.action_type is not expected_action_type:
            raise ValueError(
                f"authorized action type {self.action_type.value!r} does not match "
                f"{expected_action_type.value!r}"
            )
        if self.stage != stage:
            raise ValueError(
                f"authorized action stage {self.stage!r} does not match {stage!r}"
            )
        if expected_observation_type is not None:
            expected = ObservationType(expected_observation_type)
            if self.expected_observation_type is not expected:
                raise ValueError(
                    "authorized action expected observation type "
                    f"{self.expected_observation_type.value!r} does not match "
                    f"{expected.value!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "run_id": self.run_id,
            "stage": self.stage,
            "action_type": self.action_type.value,
            "reason": self.reason,
            "inputs": _safe_mapping(self.inputs),
            "expected_observation_type": self.expected_observation_type.value,
            "sequence": self.sequence,
        }


@dataclass(frozen=True, slots=True)
class Observation:
    """Facts returned by a bounded executor for exactly one AuthorizedAction."""

    observation_id: str
    run_id: str
    action_id: str
    stage: str
    observation_type: ObservationType
    status: RunStageStatus
    payload: Mapping[str, Any]
    sequence: int

    def __post_init__(self) -> None:
        if not _clean_text(self.observation_id, limit=120):
            raise ValueError("observation requires observation_id")
        if not _clean_text(self.run_id, limit=120):
            raise ValueError("observation requires run_id")
        if not _clean_text(self.action_id, limit=120):
            raise ValueError("observation requires action_id")
        if not _clean_text(self.stage, limit=120):
            raise ValueError("observation requires stage")
        if int(self.sequence or 0) <= 0:
            raise ValueError("observation sequence must be positive")
        object.__setattr__(self, "observation_type", ObservationType(self.observation_type))
        object.__setattr__(self, "status", RunStageStatus(self.status))
        payload = _safe_mapping(self.payload)
        if (
            self.observation_type is ObservationType.SUFFICIENCY_JUDGMENT_DECIDED
            and isinstance(self.payload, Mapping)
        ):
            raw_judgment_projection = self.payload.get("judgment_projection")
            if isinstance(raw_judgment_projection, Mapping):
                judgment_projection = _safe_mapping(raw_judgment_projection)
                semantic_consumption = _safe_semantic_consumption(
                    raw_judgment_projection.get("semantic_consumption")
                )
                if semantic_consumption:
                    judgment_projection["semantic_consumption"] = semantic_consumption
                payload["judgment_projection"] = judgment_projection
        object.__setattr__(self, "payload", payload)

    @classmethod
    def from_action(
        cls,
        action: AuthorizedAction,
        *,
        observation_type: ObservationType | str,
        status: RunStageStatus | str,
        payload: Mapping[str, Any] | None = None,
    ) -> "Observation":
        return cls(
            observation_id=f"{action.action_id}:observation",
            run_id=action.run_id,
            action_id=action.action_id,
            stage=action.stage,
            observation_type=ObservationType(observation_type),
            status=RunStageStatus(status),
            payload=dict(payload or {}),
            sequence=action.sequence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "run_id": self.run_id,
            "action_id": self.action_id,
            "stage": self.stage,
            "observation_type": self.observation_type.value,
            "status": self.status.value,
            "payload": _safe_mapping(self.payload),
            "sequence": self.sequence,
        }


@dataclass(slots=True)
class RunState:
    """Canonical run state for stages migrated to RunKernel."""

    run_id: str
    request_id: str
    request: Mapping[str, Any] = field(default_factory=dict)
    stage_statuses: dict[str, RunStageStatus] = field(default_factory=dict)
    action_statuses: dict[str, RunStageStatus] = field(default_factory=dict)
    issued_actions: dict[str, AuthorizedAction] = field(default_factory=dict)
    reduced_action_ids: set[str] = field(default_factory=set)
    observations: list[Observation] = field(default_factory=list)
    projections: dict[str, dict[str, Any]] = field(default_factory=dict)
    run_contract: dict[str, Any] = field(default_factory=dict)
    run_contract_projection: dict[str, Any] = field(default_factory=dict)
    run_contract_validation: dict[str, Any] = field(default_factory=dict)
    initial_answer_contract: dict[str, Any] = field(default_factory=dict)
    initial_answer_contract_projection: dict[str, Any] = field(default_factory=dict)
    initial_answer_contract_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    semantic_observation_admission_state: dict[str, Any] = field(
        default_factory=dict
    )
    semantic_observation_admission_projection: dict[str, Any] = field(
        default_factory=dict
    )
    semantic_observation_admission_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    component_coverage_state: dict[str, Any] = field(default_factory=dict)
    component_coverage_projection: dict[str, Any] = field(default_factory=dict)
    component_coverage_history: list[dict[str, Any]] = field(default_factory=list)
    component_gap_recovery_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    contract_amendment_admission_state: dict[str, Any] = field(default_factory=dict)
    contract_amendment_admission_projection: dict[str, Any] = field(
        default_factory=dict
    )
    contract_amendment_admission_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    search_work_plan: dict[str, Any] = field(default_factory=dict)
    search_work_plan_projection: dict[str, Any] = field(default_factory=dict)
    search_work_plan_validation: dict[str, Any] = field(default_factory=dict)
    evidence_ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    search_judgment: dict[str, Any] = field(default_factory=dict)
    search_judgment_projection: dict[str, Any] = field(default_factory=dict)
    search_judgment_history: list[dict[str, Any]] = field(default_factory=list)
    sufficiency_judgment: dict[str, Any] = field(default_factory=dict)
    sufficiency_judgment_projection: dict[str, Any] = field(default_factory=dict)
    sufficiency_judgment_history: list[dict[str, Any]] = field(default_factory=list)
    final_answer_packet: dict[str, Any] = field(default_factory=dict)
    author_observation: dict[str, Any] = field(default_factory=dict)
    final_answer_outcome: dict[str, Any] = field(default_factory=dict)
    final_answer_authority_projection: dict[str, Any] = field(default_factory=dict)
    followup_authorization_state: dict[str, Any] = field(default_factory=dict)
    followup_authorization_projection: dict[str, Any] = field(default_factory=dict)
    followup_authorization_history: list[dict[str, Any]] = field(default_factory=list)
    followup_execution_state: dict[str, Any] = field(default_factory=dict)
    followup_execution_projection: dict[str, Any] = field(default_factory=dict)
    followup_execution_history: list[dict[str, Any]] = field(default_factory=list)
    followup_evidence_intake_state: dict[str, Any] = field(default_factory=dict)
    followup_evidence_intake_projection: dict[str, Any] = field(default_factory=dict)
    followup_evidence_intake_history: list[dict[str, Any]] = field(default_factory=list)
    followup_sufficiency_recheck_state: dict[str, Any] = field(default_factory=dict)
    followup_sufficiency_recheck_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_sufficiency_recheck_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_final_answer_packet_readiness_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_final_answer_packet_readiness_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_final_answer_packet_readiness_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_blocked_final_answer_packet_shell_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_blocked_final_answer_packet_shell_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_blocked_final_answer_packet_shell_history: list[
        dict[str, Any]
    ] = field(default_factory=list)
    followup_final_evidence_selection_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_final_evidence_selection_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_final_evidence_selection_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_citation_eligibility_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_citation_eligibility_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_citation_eligibility_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_citation_source_handoff_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_citation_source_handoff_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_citation_source_handoff_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_citation_rendering_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_citation_rendering_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_citation_rendering_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_input_authority_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_input_authority_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_input_authority_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_execution_readiness_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_readiness_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_readiness_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_input_materialization_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_input_materialization_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_input_materialization_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_execution_activation_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_activation_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_activation_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_prompt_assembly_manifest_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_prompt_assembly_manifest_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_prompt_assembly_manifest_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_payload_authority_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_payload_authority_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_payload_authority_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_payload_construction_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_payload_construction_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_payload_construction_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_evidence_content_bridge_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_evidence_content_bridge_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_evidence_content_bridge_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_execution_from_ad_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_from_ad_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_from_ad_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_invocation_construction_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_invocation_construction_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_invocation_construction_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_model_request_assembly_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_model_request_assembly_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_model_request_assembly_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_execution_from_af4d_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_from_af4d_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_execution_from_af4d_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_response_finalization_state: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_response_finalization_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_response_finalization_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_final_answer_packet_state: dict[str, Any] = field(default_factory=dict)
    followup_final_answer_packet_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_final_answer_packet_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    followup_author_gate_state: dict[str, Any] = field(default_factory=dict)
    followup_author_gate_projection: dict[str, Any] = field(default_factory=dict)
    followup_author_gate_history: list[dict[str, Any]] = field(default_factory=list)
    followup_author_observation_state: dict[str, Any] = field(default_factory=dict)
    followup_author_observation_projection: dict[str, Any] = field(
        default_factory=dict
    )
    followup_author_observation_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    next_action_sequence: int = 1
    next_observation_sequence: int = 1

    def __post_init__(self) -> None:
        if not _clean_text(self.run_id, limit=120):
            raise ValueError("run state requires run_id")
        if not _clean_text(self.request_id, limit=120):
            raise ValueError("run state requires request_id")
        self.request = _safe_mapping(self.request)

    def to_trace_projection(self) -> "KernelTraceProjection":
        return KernelTraceProjection(
            run_id=self.run_id,
            request_id=self.request_id,
            request=_safe_mapping(self.request),
            stage_statuses={
                stage: status.value for stage, status in self.stage_statuses.items()
            },
            action_statuses={
                action_id: status.value
                for action_id, status in self.action_statuses.items()
            },
            actions=[action.to_dict() for action in self.issued_actions.values()],
            observations=[observation.to_dict() for observation in self.observations],
            projections=deepcopy(self.projections),
            run_contract=deepcopy(self.run_contract),
            run_contract_projection=deepcopy(self.run_contract_projection),
            run_contract_validation=deepcopy(self.run_contract_validation),
            initial_answer_contract=deepcopy(self.initial_answer_contract),
            initial_answer_contract_projection=deepcopy(
                self.initial_answer_contract_projection
            ),
            initial_answer_contract_history=deepcopy(
                self.initial_answer_contract_history
            ),
            semantic_observation_admission_state=deepcopy(
                self.semantic_observation_admission_state
            ),
            semantic_observation_admission_projection=deepcopy(
                self.semantic_observation_admission_projection
            ),
            semantic_observation_admission_history=deepcopy(
                self.semantic_observation_admission_history
            ),
            component_coverage_state=deepcopy(self.component_coverage_state),
            component_coverage_projection=deepcopy(self.component_coverage_projection),
            component_coverage_history=deepcopy(self.component_coverage_history),
            component_gap_recovery_history=deepcopy(
                self.component_gap_recovery_history
            ),
            contract_amendment_admission_state=deepcopy(
                self.contract_amendment_admission_state
            ),
            contract_amendment_admission_projection=deepcopy(
                self.contract_amendment_admission_projection
            ),
            contract_amendment_admission_history=deepcopy(
                self.contract_amendment_admission_history
            ),
            search_work_plan=deepcopy(self.search_work_plan),
            search_work_plan_projection=deepcopy(self.search_work_plan_projection),
            search_work_plan_validation=deepcopy(self.search_work_plan_validation),
            evidence_ledger=self.evidence_ledger.to_projection().to_dict(),
            search_judgment=deepcopy(self.search_judgment),
            search_judgment_projection=deepcopy(self.search_judgment_projection),
            search_judgment_history=deepcopy(self.search_judgment_history),
            sufficiency_judgment=deepcopy(self.sufficiency_judgment),
            sufficiency_judgment_projection=deepcopy(
                self.sufficiency_judgment_projection
            ),
            sufficiency_judgment_history=deepcopy(
                self.sufficiency_judgment_history
            ),
            final_answer_packet=deepcopy(self.final_answer_packet),
            author_observation=deepcopy(self.author_observation),
            final_answer_outcome=deepcopy(self.final_answer_outcome),
            final_answer_authority_projection=deepcopy(
                self.final_answer_authority_projection
            ),
            followup_authorization_state=deepcopy(self.followup_authorization_state),
            followup_authorization_projection=deepcopy(
                self.followup_authorization_projection
            ),
            followup_authorization_history=deepcopy(
                self.followup_authorization_history
            ),
            followup_execution_state=deepcopy(self.followup_execution_state),
            followup_execution_projection=deepcopy(
                self.followup_execution_projection
            ),
            followup_execution_history=deepcopy(self.followup_execution_history),
            followup_evidence_intake_state=deepcopy(
                self.followup_evidence_intake_state
            ),
            followup_evidence_intake_projection=deepcopy(
                self.followup_evidence_intake_projection
            ),
            followup_evidence_intake_history=deepcopy(
                self.followup_evidence_intake_history
            ),
            followup_sufficiency_recheck_state=deepcopy(
                self.followup_sufficiency_recheck_state
            ),
            followup_sufficiency_recheck_projection=deepcopy(
                self.followup_sufficiency_recheck_projection
            ),
            followup_sufficiency_recheck_history=deepcopy(
                self.followup_sufficiency_recheck_history
            ),
            followup_final_answer_packet_readiness_state=deepcopy(
                self.followup_final_answer_packet_readiness_state
            ),
            followup_final_answer_packet_readiness_projection=deepcopy(
                self.followup_final_answer_packet_readiness_projection
            ),
            followup_final_answer_packet_readiness_history=deepcopy(
                self.followup_final_answer_packet_readiness_history
            ),
            followup_blocked_final_answer_packet_shell_state=deepcopy(
                self.followup_blocked_final_answer_packet_shell_state
            ),
            followup_blocked_final_answer_packet_shell_projection=deepcopy(
                self.followup_blocked_final_answer_packet_shell_projection
            ),
            followup_blocked_final_answer_packet_shell_history=deepcopy(
                self.followup_blocked_final_answer_packet_shell_history
            ),
            followup_final_evidence_selection_state=deepcopy(
                self.followup_final_evidence_selection_state
            ),
            followup_final_evidence_selection_projection=deepcopy(
                self.followup_final_evidence_selection_projection
            ),
            followup_final_evidence_selection_history=deepcopy(
                self.followup_final_evidence_selection_history
            ),
            followup_citation_eligibility_state=deepcopy(
                self.followup_citation_eligibility_state
            ),
            followup_citation_eligibility_projection=deepcopy(
                self.followup_citation_eligibility_projection
            ),
            followup_citation_eligibility_history=deepcopy(
                self.followup_citation_eligibility_history
            ),
            followup_citation_source_handoff_state=deepcopy(
                self.followup_citation_source_handoff_state
            ),
            followup_citation_source_handoff_projection=deepcopy(
                self.followup_citation_source_handoff_projection
            ),
            followup_citation_source_handoff_history=deepcopy(
                self.followup_citation_source_handoff_history
            ),
            followup_citation_rendering_state=deepcopy(
                self.followup_citation_rendering_state
            ),
            followup_citation_rendering_projection=deepcopy(
                self.followup_citation_rendering_projection
            ),
            followup_citation_rendering_history=deepcopy(
                self.followup_citation_rendering_history
            ),
            followup_author_input_authority_state=deepcopy(
                self.followup_author_input_authority_state
            ),
            followup_author_input_authority_projection=deepcopy(
                self.followup_author_input_authority_projection
            ),
            followup_author_input_authority_history=deepcopy(
                self.followup_author_input_authority_history
            ),
            followup_author_execution_readiness_state=deepcopy(
                self.followup_author_execution_readiness_state
            ),
            followup_author_execution_readiness_projection=deepcopy(
                self.followup_author_execution_readiness_projection
            ),
            followup_author_execution_readiness_history=deepcopy(
                self.followup_author_execution_readiness_history
            ),
            followup_author_input_materialization_state=deepcopy(
                self.followup_author_input_materialization_state
            ),
            followup_author_input_materialization_projection=deepcopy(
                self.followup_author_input_materialization_projection
            ),
            followup_author_input_materialization_history=deepcopy(
                self.followup_author_input_materialization_history
            ),
            followup_author_execution_activation_state=deepcopy(
                self.followup_author_execution_activation_state
            ),
            followup_author_execution_activation_projection=deepcopy(
                self.followup_author_execution_activation_projection
            ),
            followup_author_execution_activation_history=deepcopy(
                self.followup_author_execution_activation_history
            ),
            followup_author_prompt_assembly_manifest_state=deepcopy(
                self.followup_author_prompt_assembly_manifest_state
            ),
            followup_author_prompt_assembly_manifest_projection=deepcopy(
                self.followup_author_prompt_assembly_manifest_projection
            ),
            followup_author_prompt_assembly_manifest_history=deepcopy(
                self.followup_author_prompt_assembly_manifest_history
            ),
            followup_author_payload_authority_state=deepcopy(
                self.followup_author_payload_authority_state
            ),
            followup_author_payload_authority_projection=deepcopy(
                self.followup_author_payload_authority_projection
            ),
            followup_author_payload_authority_history=deepcopy(
                self.followup_author_payload_authority_history
            ),
            followup_author_payload_construction_state=deepcopy(
                self.followup_author_payload_construction_state
            ),
            followup_author_payload_construction_projection=deepcopy(
                self.followup_author_payload_construction_projection
            ),
            followup_author_payload_construction_history=deepcopy(
                self.followup_author_payload_construction_history
            ),
            followup_author_evidence_content_bridge_state=deepcopy(
                self.followup_author_evidence_content_bridge_state
            ),
            followup_author_evidence_content_bridge_projection=deepcopy(
                self.followup_author_evidence_content_bridge_projection
            ),
            followup_author_evidence_content_bridge_history=deepcopy(
                self.followup_author_evidence_content_bridge_history
            ),
            followup_author_execution_from_ad_state=deepcopy(
                self.followup_author_execution_from_ad_state
            ),
            followup_author_execution_from_ad_projection=deepcopy(
                self.followup_author_execution_from_ad_projection
            ),
            followup_author_execution_from_ad_history=deepcopy(
                self.followup_author_execution_from_ad_history
            ),
            followup_author_invocation_construction_state=deepcopy(
                self.followup_author_invocation_construction_state
            ),
            followup_author_invocation_construction_projection=deepcopy(
                self.followup_author_invocation_construction_projection
            ),
            followup_author_invocation_construction_history=deepcopy(
                self.followup_author_invocation_construction_history
            ),
            followup_author_model_request_assembly_state=deepcopy(
                self.followup_author_model_request_assembly_state
            ),
            followup_author_model_request_assembly_projection=deepcopy(
                self.followup_author_model_request_assembly_projection
            ),
            followup_author_model_request_assembly_history=deepcopy(
                self.followup_author_model_request_assembly_history
            ),
            followup_author_execution_from_af4d_state=deepcopy(
                self.followup_author_execution_from_af4d_state
            ),
            followup_author_execution_from_af4d_projection=deepcopy(
                self.followup_author_execution_from_af4d_projection
            ),
            followup_author_execution_from_af4d_history=deepcopy(
                self.followup_author_execution_from_af4d_history
            ),
            followup_author_response_finalization_state=deepcopy(
                self.followup_author_response_finalization_state
            ),
            followup_author_response_finalization_projection=deepcopy(
                self.followup_author_response_finalization_projection
            ),
            followup_author_response_finalization_history=deepcopy(
                self.followup_author_response_finalization_history
            ),
            followup_final_answer_packet_state=deepcopy(
                self.followup_final_answer_packet_state
            ),
            followup_final_answer_packet_projection=deepcopy(
                self.followup_final_answer_packet_projection
            ),
            followup_final_answer_packet_history=deepcopy(
                self.followup_final_answer_packet_history
            ),
            followup_author_gate_state=deepcopy(self.followup_author_gate_state),
            followup_author_gate_projection=deepcopy(
                self.followup_author_gate_projection
            ),
            followup_author_gate_history=deepcopy(
                self.followup_author_gate_history
            ),
            followup_author_observation_state=deepcopy(
                self.followup_author_observation_state
            ),
            followup_author_observation_projection=deepcopy(
                self.followup_author_observation_projection
            ),
            followup_author_observation_history=deepcopy(
                self.followup_author_observation_history
            ),
            next_action_sequence=self.next_action_sequence,
            next_observation_sequence=self.next_observation_sequence,
        )


@dataclass(frozen=True, slots=True)
class KernelTraceProjection:
    """Trace/export view derived only from RunState."""

    run_id: str
    request_id: str
    request: Mapping[str, Any]
    stage_statuses: Mapping[str, str]
    action_statuses: Mapping[str, str]
    actions: Sequence[Mapping[str, Any]]
    observations: Sequence[Mapping[str, Any]]
    projections: Mapping[str, Any]
    run_contract: Mapping[str, Any]
    run_contract_projection: Mapping[str, Any]
    run_contract_validation: Mapping[str, Any]
    initial_answer_contract: Mapping[str, Any]
    initial_answer_contract_projection: Mapping[str, Any]
    initial_answer_contract_history: Sequence[Mapping[str, Any]]
    semantic_observation_admission_state: Mapping[str, Any]
    semantic_observation_admission_projection: Mapping[str, Any]
    semantic_observation_admission_history: Sequence[Mapping[str, Any]]
    component_coverage_state: Mapping[str, Any]
    component_coverage_projection: Mapping[str, Any]
    component_coverage_history: Sequence[Mapping[str, Any]]
    component_gap_recovery_history: Sequence[Mapping[str, Any]]
    contract_amendment_admission_state: Mapping[str, Any]
    contract_amendment_admission_projection: Mapping[str, Any]
    contract_amendment_admission_history: Sequence[Mapping[str, Any]]
    search_work_plan: Mapping[str, Any]
    search_work_plan_projection: Mapping[str, Any]
    search_work_plan_validation: Mapping[str, Any]
    evidence_ledger: Mapping[str, Any]
    search_judgment: Mapping[str, Any]
    search_judgment_projection: Mapping[str, Any]
    search_judgment_history: Sequence[Mapping[str, Any]]
    sufficiency_judgment: Mapping[str, Any]
    sufficiency_judgment_projection: Mapping[str, Any]
    sufficiency_judgment_history: Sequence[Mapping[str, Any]]
    final_answer_packet: Mapping[str, Any]
    author_observation: Mapping[str, Any]
    final_answer_outcome: Mapping[str, Any]
    final_answer_authority_projection: Mapping[str, Any]
    followup_authorization_state: Mapping[str, Any]
    followup_authorization_projection: Mapping[str, Any]
    followup_authorization_history: Sequence[Mapping[str, Any]]
    followup_execution_state: Mapping[str, Any]
    followup_execution_projection: Mapping[str, Any]
    followup_execution_history: Sequence[Mapping[str, Any]]
    followup_evidence_intake_state: Mapping[str, Any]
    followup_evidence_intake_projection: Mapping[str, Any]
    followup_evidence_intake_history: Sequence[Mapping[str, Any]]
    followup_sufficiency_recheck_state: Mapping[str, Any]
    followup_sufficiency_recheck_projection: Mapping[str, Any]
    followup_sufficiency_recheck_history: Sequence[Mapping[str, Any]]
    followup_final_answer_packet_readiness_state: Mapping[str, Any]
    followup_final_answer_packet_readiness_projection: Mapping[str, Any]
    followup_final_answer_packet_readiness_history: Sequence[Mapping[str, Any]]
    followup_blocked_final_answer_packet_shell_state: Mapping[str, Any]
    followup_blocked_final_answer_packet_shell_projection: Mapping[str, Any]
    followup_blocked_final_answer_packet_shell_history: Sequence[Mapping[str, Any]]
    followup_final_evidence_selection_state: Mapping[str, Any]
    followup_final_evidence_selection_projection: Mapping[str, Any]
    followup_final_evidence_selection_history: Sequence[Mapping[str, Any]]
    followup_citation_eligibility_state: Mapping[str, Any]
    followup_citation_eligibility_projection: Mapping[str, Any]
    followup_citation_eligibility_history: Sequence[Mapping[str, Any]]
    followup_citation_source_handoff_state: Mapping[str, Any]
    followup_citation_source_handoff_projection: Mapping[str, Any]
    followup_citation_source_handoff_history: Sequence[Mapping[str, Any]]
    followup_citation_rendering_state: Mapping[str, Any]
    followup_citation_rendering_projection: Mapping[str, Any]
    followup_citation_rendering_history: Sequence[Mapping[str, Any]]
    followup_author_input_authority_state: Mapping[str, Any]
    followup_author_input_authority_projection: Mapping[str, Any]
    followup_author_input_authority_history: Sequence[Mapping[str, Any]]
    followup_author_execution_readiness_state: Mapping[str, Any]
    followup_author_execution_readiness_projection: Mapping[str, Any]
    followup_author_execution_readiness_history: Sequence[Mapping[str, Any]]
    followup_author_input_materialization_state: Mapping[str, Any]
    followup_author_input_materialization_projection: Mapping[str, Any]
    followup_author_input_materialization_history: Sequence[Mapping[str, Any]]
    followup_author_execution_activation_state: Mapping[str, Any]
    followup_author_execution_activation_projection: Mapping[str, Any]
    followup_author_execution_activation_history: Sequence[Mapping[str, Any]]
    followup_author_prompt_assembly_manifest_state: Mapping[str, Any]
    followup_author_prompt_assembly_manifest_projection: Mapping[str, Any]
    followup_author_prompt_assembly_manifest_history: Sequence[Mapping[str, Any]]
    followup_author_payload_authority_state: Mapping[str, Any]
    followup_author_payload_authority_projection: Mapping[str, Any]
    followup_author_payload_authority_history: Sequence[Mapping[str, Any]]
    followup_author_payload_construction_state: Mapping[str, Any]
    followup_author_payload_construction_projection: Mapping[str, Any]
    followup_author_payload_construction_history: Sequence[Mapping[str, Any]]
    followup_author_evidence_content_bridge_state: Mapping[str, Any]
    followup_author_evidence_content_bridge_projection: Mapping[str, Any]
    followup_author_evidence_content_bridge_history: Sequence[Mapping[str, Any]]
    followup_author_execution_from_ad_state: Mapping[str, Any]
    followup_author_execution_from_ad_projection: Mapping[str, Any]
    followup_author_execution_from_ad_history: Sequence[Mapping[str, Any]]
    followup_author_invocation_construction_state: Mapping[str, Any]
    followup_author_invocation_construction_projection: Mapping[str, Any]
    followup_author_invocation_construction_history: Sequence[Mapping[str, Any]]
    followup_author_model_request_assembly_state: Mapping[str, Any]
    followup_author_model_request_assembly_projection: Mapping[str, Any]
    followup_author_model_request_assembly_history: Sequence[Mapping[str, Any]]
    followup_author_execution_from_af4d_state: Mapping[str, Any]
    followup_author_execution_from_af4d_projection: Mapping[str, Any]
    followup_author_execution_from_af4d_history: Sequence[Mapping[str, Any]]
    followup_author_response_finalization_state: Mapping[str, Any]
    followup_author_response_finalization_projection: Mapping[str, Any]
    followup_author_response_finalization_history: Sequence[Mapping[str, Any]]
    followup_final_answer_packet_state: Mapping[str, Any]
    followup_final_answer_packet_projection: Mapping[str, Any]
    followup_final_answer_packet_history: Sequence[Mapping[str, Any]]
    followup_author_gate_state: Mapping[str, Any]
    followup_author_gate_projection: Mapping[str, Any]
    followup_author_gate_history: Sequence[Mapping[str, Any]]
    followup_author_observation_state: Mapping[str, Any]
    followup_author_observation_projection: Mapping[str, Any]
    followup_author_observation_history: Sequence[Mapping[str, Any]]
    next_action_sequence: int
    next_observation_sequence: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "request": _safe_mapping(self.request),
            "stage_statuses": dict(self.stage_statuses),
            "action_statuses": dict(self.action_statuses),
            "actions": [_safe_mapping(action) for action in self.actions],
            "observations": [
                _safe_mapping(observation) for observation in self.observations
            ],
            "projections": _safe_mapping(self.projections),
            "run_contract": _safe_mapping(self.run_contract),
            "run_contract_projection": _safe_mapping(self.run_contract_projection),
            "run_contract_validation": _safe_mapping(self.run_contract_validation),
            "initial_answer_contract": _safe_mapping(self.initial_answer_contract),
            "initial_answer_contract_projection": _safe_mapping(
                self.initial_answer_contract_projection
            ),
            "initial_answer_contract_history": [
                _safe_mapping(item)
                for item in self.initial_answer_contract_history
            ],
            "semantic_observation_admission_state": _safe_mapping(
                self.semantic_observation_admission_state
            ),
            "semantic_observation_admission_projection": _safe_mapping(
                self.semantic_observation_admission_projection
            ),
            "semantic_observation_admission_history": [
                _safe_mapping(item)
                for item in self.semantic_observation_admission_history
            ],
            "component_coverage_state": _safe_mapping(self.component_coverage_state),
            "component_coverage_projection": _safe_mapping(
                self.component_coverage_projection
            ),
            "component_coverage_history": [
                _safe_mapping(item) for item in self.component_coverage_history
            ],
            "component_gap_recovery_history": [
                _safe_mapping(item)
                for item in self.component_gap_recovery_history
            ],
            "contract_amendment_admission_state": _safe_mapping(
                self.contract_amendment_admission_state
            ),
            "contract_amendment_admission_projection": _safe_mapping(
                self.contract_amendment_admission_projection
            ),
            "contract_amendment_admission_history": [
                _safe_mapping(item)
                for item in self.contract_amendment_admission_history
            ],
            "search_work_plan": _safe_mapping(self.search_work_plan),
            "search_work_plan_projection": _safe_mapping(
                self.search_work_plan_projection
            ),
            "search_work_plan_validation": _safe_mapping(
                self.search_work_plan_validation
            ),
            "evidence_ledger": _safe_mapping(self.evidence_ledger),
            "search_judgment": _safe_mapping(self.search_judgment),
            "search_judgment_projection": _safe_mapping(
                self.search_judgment_projection
            ),
            "search_judgment_history": [
                _safe_mapping(item) for item in self.search_judgment_history
            ],
            "sufficiency_judgment": _safe_mapping(self.sufficiency_judgment),
            "sufficiency_judgment_projection": _safe_mapping(
                self.sufficiency_judgment_projection
            ),
            "sufficiency_judgment_history": [
                _safe_mapping(item) for item in self.sufficiency_judgment_history
            ],
            "final_answer_packet": _safe_mapping(self.final_answer_packet),
            "author_observation": _safe_mapping(self.author_observation),
            "final_answer_outcome": _safe_mapping(self.final_answer_outcome),
            "final_answer_authority_projection": _safe_mapping(
                self.final_answer_authority_projection
            ),
            "followup_authorization_state": _safe_mapping(
                self.followup_authorization_state
            ),
            "followup_authorization_projection": _safe_mapping(
                self.followup_authorization_projection
            ),
            "followup_authorization_history": [
                _safe_mapping(item) for item in self.followup_authorization_history
            ],
            "followup_execution_state": _safe_mapping(self.followup_execution_state),
            "followup_execution_projection": _safe_mapping(
                self.followup_execution_projection
            ),
            "followup_execution_history": [
                _safe_mapping(item) for item in self.followup_execution_history
            ],
            "followup_evidence_intake_state": _safe_mapping(
                self.followup_evidence_intake_state
            ),
            "followup_evidence_intake_projection": _safe_mapping(
                self.followup_evidence_intake_projection
            ),
            "followup_evidence_intake_history": [
                _safe_mapping(item) for item in self.followup_evidence_intake_history
            ],
            "followup_sufficiency_recheck_state": _safe_mapping(
                self.followup_sufficiency_recheck_state
            ),
            "followup_sufficiency_recheck_projection": _safe_mapping(
                self.followup_sufficiency_recheck_projection
            ),
            "followup_sufficiency_recheck_history": [
                _safe_mapping(item)
                for item in self.followup_sufficiency_recheck_history
            ],
            "followup_final_answer_packet_readiness_state": _safe_mapping(
                self.followup_final_answer_packet_readiness_state
            ),
            "followup_final_answer_packet_readiness_projection": _safe_mapping(
                self.followup_final_answer_packet_readiness_projection
            ),
            "followup_final_answer_packet_readiness_history": [
                _safe_mapping(item)
                for item in self.followup_final_answer_packet_readiness_history
            ],
            "followup_blocked_final_answer_packet_shell_state": _safe_mapping(
                self.followup_blocked_final_answer_packet_shell_state
            ),
            "followup_blocked_final_answer_packet_shell_projection": _safe_mapping(
                self.followup_blocked_final_answer_packet_shell_projection
            ),
            "followup_blocked_final_answer_packet_shell_history": [
                _safe_mapping(item)
                for item in self.followup_blocked_final_answer_packet_shell_history
            ],
            "followup_final_evidence_selection_state": _safe_mapping(
                self.followup_final_evidence_selection_state
            ),
            "followup_final_evidence_selection_projection": _safe_mapping(
                self.followup_final_evidence_selection_projection
            ),
            "followup_final_evidence_selection_history": [
                _safe_mapping(item)
                for item in self.followup_final_evidence_selection_history
            ],
            "followup_citation_eligibility_state": _safe_mapping(
                self.followup_citation_eligibility_state
            ),
            "followup_citation_eligibility_projection": _safe_mapping(
                self.followup_citation_eligibility_projection
            ),
            "followup_citation_eligibility_history": [
                _safe_mapping(item)
                for item in self.followup_citation_eligibility_history
            ],
            "followup_citation_source_handoff_state": _safe_mapping(
                self.followup_citation_source_handoff_state
            ),
            "followup_citation_source_handoff_projection": _safe_mapping(
                self.followup_citation_source_handoff_projection
            ),
            "followup_citation_source_handoff_history": [
                _safe_mapping(item)
                for item in self.followup_citation_source_handoff_history
            ],
            "followup_citation_rendering_state": _safe_mapping(
                self.followup_citation_rendering_state
            ),
            "followup_citation_rendering_projection": _safe_mapping(
                self.followup_citation_rendering_projection
            ),
            "followup_citation_rendering_history": [
                _safe_mapping(item)
                for item in self.followup_citation_rendering_history
            ],
            "followup_author_input_authority_state": _safe_mapping(
                self.followup_author_input_authority_state
            ),
            "followup_author_input_authority_projection": _safe_mapping(
                self.followup_author_input_authority_projection
            ),
            "followup_author_input_authority_history": [
                _safe_mapping(item)
                for item in self.followup_author_input_authority_history
            ],
            "followup_author_execution_readiness_state": _safe_mapping(
                self.followup_author_execution_readiness_state
            ),
            "followup_author_execution_readiness_projection": _safe_mapping(
                self.followup_author_execution_readiness_projection
            ),
            "followup_author_execution_readiness_history": [
                _safe_mapping(item)
                for item in self.followup_author_execution_readiness_history
            ],
            "followup_author_input_materialization_state": _safe_mapping(
                self.followup_author_input_materialization_state
            ),
            "followup_author_input_materialization_projection": _safe_mapping(
                self.followup_author_input_materialization_projection
            ),
            "followup_author_input_materialization_history": [
                _safe_mapping(item)
                for item in self.followup_author_input_materialization_history
            ],
            "followup_author_execution_activation_state": _safe_mapping(
                self.followup_author_execution_activation_state
            ),
            "followup_author_execution_activation_projection": _safe_mapping(
                self.followup_author_execution_activation_projection
            ),
            "followup_author_execution_activation_history": [
                _safe_mapping(item)
                for item in self.followup_author_execution_activation_history
            ],
            "followup_author_prompt_assembly_manifest_state": _safe_mapping(
                self.followup_author_prompt_assembly_manifest_state
            ),
            "followup_author_prompt_assembly_manifest_projection": _safe_mapping(
                self.followup_author_prompt_assembly_manifest_projection
            ),
            "followup_author_prompt_assembly_manifest_history": [
                _safe_mapping(item)
                for item in self.followup_author_prompt_assembly_manifest_history
            ],
            "followup_author_payload_authority_state": _safe_mapping(
                self.followup_author_payload_authority_state
            ),
            "followup_author_payload_authority_projection": _safe_mapping(
                self.followup_author_payload_authority_projection
            ),
            "followup_author_payload_authority_history": [
                _safe_mapping(item)
                for item in self.followup_author_payload_authority_history
            ],
            "followup_author_payload_construction_state": _safe_mapping(
                self.followup_author_payload_construction_state
            ),
            "followup_author_payload_construction_projection": _safe_mapping(
                self.followup_author_payload_construction_projection
            ),
            "followup_author_payload_construction_history": [
                _safe_mapping(item)
                for item in self.followup_author_payload_construction_history
            ],
            "followup_author_evidence_content_bridge_state": _safe_mapping(
                self.followup_author_evidence_content_bridge_state
            ),
            "followup_author_evidence_content_bridge_projection": _safe_mapping(
                self.followup_author_evidence_content_bridge_projection
            ),
            "followup_author_evidence_content_bridge_history": [
                _safe_mapping(item)
                for item in self.followup_author_evidence_content_bridge_history
            ],
            "followup_author_execution_from_ad_state": _safe_mapping(
                self.followup_author_execution_from_ad_state
            ),
            "followup_author_execution_from_ad_projection": _safe_mapping(
                self.followup_author_execution_from_ad_projection
            ),
            "followup_author_execution_from_ad_history": [
                _safe_mapping(item)
                for item in self.followup_author_execution_from_ad_history
            ],
            "followup_author_invocation_construction_state": _safe_mapping(
                self.followup_author_invocation_construction_state
            ),
            "followup_author_invocation_construction_projection": _safe_mapping(
                self.followup_author_invocation_construction_projection
            ),
            "followup_author_invocation_construction_history": [
                _safe_mapping(item)
                for item in self.followup_author_invocation_construction_history
            ],
            "followup_author_model_request_assembly_state": _safe_mapping(
                self.followup_author_model_request_assembly_state
            ),
            "followup_author_model_request_assembly_projection": _safe_mapping(
                self.followup_author_model_request_assembly_projection
            ),
            "followup_author_model_request_assembly_history": [
                _safe_mapping(item)
                for item in self.followup_author_model_request_assembly_history
            ],
            "followup_author_execution_from_af4d_state": _safe_mapping(
                self.followup_author_execution_from_af4d_state
            ),
            "followup_author_execution_from_af4d_projection": _safe_mapping(
                self.followup_author_execution_from_af4d_projection
            ),
            "followup_author_execution_from_af4d_history": [
                _safe_mapping(item)
                for item in self.followup_author_execution_from_af4d_history
            ],
            "followup_author_response_finalization_state": _safe_mapping(
                self.followup_author_response_finalization_state
            ),
            "followup_author_response_finalization_projection": _safe_mapping(
                self.followup_author_response_finalization_projection
            ),
            "followup_author_response_finalization_history": [
                _safe_mapping(item)
                for item in self.followup_author_response_finalization_history
            ],
            "followup_final_answer_packet_state": _safe_mapping(
                self.followup_final_answer_packet_state
            ),
            "followup_final_answer_packet_projection": _safe_mapping(
                self.followup_final_answer_packet_projection
            ),
            "followup_final_answer_packet_history": [
                _safe_mapping(item)
                for item in self.followup_final_answer_packet_history
            ],
            "followup_author_gate_state": _safe_mapping(
                self.followup_author_gate_state
            ),
            "followup_author_gate_projection": _safe_mapping(
                self.followup_author_gate_projection
            ),
            "followup_author_gate_history": [
                _safe_mapping(item) for item in self.followup_author_gate_history
            ],
            "followup_author_observation_state": _safe_mapping(
                self.followup_author_observation_state
            ),
            "followup_author_observation_projection": _safe_mapping(
                self.followup_author_observation_projection
            ),
            "followup_author_observation_history": [
                _safe_mapping(item)
                for item in self.followup_author_observation_history
            ],
            "next_action_sequence": self.next_action_sequence,
            "next_observation_sequence": self.next_observation_sequence,
        }

    def to_trace_fragment(self) -> dict[str, Any]:
        return {RUN_KERNEL_TRACE_KEY: self.to_dict()}


class RunKernel:
    """Small runtime-consumed authority spine for migrated stages."""

    def __init__(self, state: RunState) -> None:
        self.state = state

    @classmethod
    def start(
        cls,
        *,
        run_id: str,
        request_id: str,
        request: Mapping[str, Any] | None = None,
    ) -> "RunKernel":
        return cls(
            RunState(
                run_id=run_id,
                request_id=request_id,
                request=dict(request or {}),
            )
        )

    def authorize(
        self,
        *,
        stage: str,
        action_type: ActionType | str,
        reason: str,
        inputs: Mapping[str, Any] | None,
        expected_observation_type: ObservationType | str,
    ) -> AuthorizedAction:
        action_type_value = ActionType(action_type)
        observation_type_value = ObservationType(expected_observation_type)
        sequence = self.state.next_action_sequence
        action = AuthorizedAction(
            action_id=f"{self.state.run_id}:action:{sequence}:{action_type_value.value}",
            run_id=self.state.run_id,
            stage=stage,
            action_type=action_type_value,
            reason=reason,
            inputs=dict(inputs or {}),
            expected_observation_type=observation_type_value,
            sequence=sequence,
        )
        self.state.issued_actions[action.action_id] = action
        self.state.action_statuses[action.action_id] = RunStageStatus.AUTHORIZED
        self.state.stage_statuses[stage] = RunStageStatus.AUTHORIZED
        self.state.next_action_sequence += 1
        return action

    def authorize_route_request(
        self,
        *,
        reason: str = "route_request_before_model_execution",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=ROUTE_REQUEST_STAGE,
            action_type=ActionType.ROUTE_REQUEST,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.ROUTE_RESULT,
        )

    def authorize_run_contract_synthesis(
        self,
        *,
        reason: str = "run_authority_contract_synthesis_before_query_production",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=RUN_CONTRACT_STAGE,
            action_type=ActionType.RUN_CONTRACT_SYNTHESIZE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.RUN_CONTRACT_SYNTHESIZED,
        )

    def authorize_initial_answer_contract_acceptance(
        self,
        *,
        parent_question_meaning_record_id: str,
        parent_proposal_digest: str,
        request_id: str | None = None,
        reason: str = INITIAL_ANSWER_CONTRACT_ACCEPTANCE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not _clean_text(parent_question_meaning_record_id, limit=160):
            raise RunKernelTransitionError(
                "initial answer contract acceptance requires a parent "
                "QuestionMeaningRecord id binding"
            )
        if not _clean_text(parent_proposal_digest, limit=128):
            raise RunKernelTransitionError(
                "initial answer contract acceptance requires a parent proposal "
                "digest binding"
            )
        merged_inputs = {
            "parent_question_meaning_record_id": parent_question_meaning_record_id,
            "parent_proposal_digest": parent_proposal_digest,
            "request_id": request_id or self.state.request_id,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE,
            action_type=ActionType.INITIAL_ANSWER_CONTRACT_ACCEPT,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED
            ),
        )

    def authorize_semantic_observation_admission(
        self,
        *,
        semantic_observation_id: str,
        semantic_observation_digest: str,
        answer_component_id: str,
        component_revision: str,
        component_digest: str,
        accepted_contract_digest: str | None = None,
        accepted_contract_version: str | None = None,
        request_id: str | None = None,
        reason: str = SEMANTIC_OBSERVATION_ADMISSION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.initial_answer_contract_projection:
            raise RunKernelTransitionError(
                "semantic observation admission requires an accepted initial "
                "answer contract"
            )
        accepted = self.state.initial_answer_contract
        resolved_contract_digest = (
            accepted_contract_digest
            or accepted.get("accepted_contract_digest")
        )
        resolved_contract_version = (
            accepted_contract_version
            or accepted.get("accepted_contract_version")
        )
        for label, value in (
            ("semantic_observation_id", semantic_observation_id),
            ("semantic_observation_digest", semantic_observation_digest),
            ("answer_component_id", answer_component_id),
            ("component_revision", component_revision),
            ("component_digest", component_digest),
            ("accepted_contract_digest", resolved_contract_digest),
            ("accepted_contract_version", resolved_contract_version),
        ):
            if not _clean_text(value, limit=200):
                raise RunKernelTransitionError(
                    "semantic observation admission requires "
                    f"{label} binding"
                )
        merged_inputs = {
            "semantic_observation_id": semantic_observation_id,
            "semantic_observation_digest": semantic_observation_digest,
            "answer_component_id": answer_component_id,
            "component_revision": component_revision,
            "component_digest": component_digest,
            "accepted_contract_digest": resolved_contract_digest,
            "accepted_contract_version": resolved_contract_version,
            "request_id": request_id or self.state.request_id,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=SEMANTIC_OBSERVATION_ADMISSION_STAGE,
            action_type=ActionType.SEMANTIC_OBSERVATION_ADMIT,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.SEMANTIC_OBSERVATION_ADMITTED
            ),
        )

    def authorize_component_coverage_reduction(
        self,
        *,
        coverage_record_id: str,
        coverage_record_digest: str,
        answer_component_id: str,
        component_revision: str,
        component_digest: str,
        accepted_contract_digest: str | None = None,
        accepted_contract_version: str | None = None,
        request_id: str | None = None,
        reason: str = COMPONENT_COVERAGE_REDUCTION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.initial_answer_contract_projection:
            raise RunKernelTransitionError(
                "component coverage reduction requires an accepted initial answer contract"
            )
        if not self.state.semantic_observation_admission_history:
            raise RunKernelTransitionError(
                "component coverage reduction requires at least one admitted "
                "SemanticObservation"
            )
        accepted = self.state.initial_answer_contract
        resolved_contract_digest = (
            accepted_contract_digest
            or accepted.get("accepted_contract_digest")
        )
        resolved_contract_version = (
            accepted_contract_version
            or accepted.get("accepted_contract_version")
        )
        for label, value in (
            ("coverage_record_id", coverage_record_id),
            ("coverage_record_digest", coverage_record_digest),
            ("answer_component_id", answer_component_id),
            ("component_revision", component_revision),
            ("component_digest", component_digest),
            ("accepted_contract_digest", resolved_contract_digest),
            ("accepted_contract_version", resolved_contract_version),
        ):
            if not _clean_text(value, limit=200):
                raise RunKernelTransitionError(
                    "component coverage reduction requires " f"{label} binding"
                )
        merged_inputs = {
            "coverage_record_id": coverage_record_id,
            "coverage_record_digest": coverage_record_digest,
            "answer_component_id": answer_component_id,
            "component_revision": component_revision,
            "component_digest": component_digest,
            "accepted_contract_digest": resolved_contract_digest,
            "accepted_contract_version": resolved_contract_version,
            "request_id": request_id or self.state.request_id,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=COMPONENT_COVERAGE_REDUCTION_STAGE,
            action_type=ActionType.COMPONENT_COVERAGE_REDUCE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
        )

    def authorize_semantic_producer_bundle_commit(
        self,
        *,
        parent_question_meaning_record_id: str,
        parent_proposal_digest: str,
        component_count: int,
        request_id: str | None = None,
        reason: str = SEMANTIC_PRODUCER_BUNDLE_COMMIT_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not _clean_text(parent_question_meaning_record_id, limit=160):
            raise RunKernelTransitionError(
                "semantic producer bundle commit requires a parent "
                "QuestionMeaningRecord id binding"
            )
        if not _clean_text(parent_proposal_digest, limit=128):
            raise RunKernelTransitionError(
                "semantic producer bundle commit requires a parent proposal "
                "digest binding"
            )
        if int(component_count or 0) <= 0:
            raise RunKernelTransitionError(
                "semantic producer bundle commit requires at least one component"
            )
        merged_inputs = {
            "parent_question_meaning_record_id": parent_question_meaning_record_id,
            "parent_proposal_digest": parent_proposal_digest,
            "component_count": int(component_count),
            "request_id": request_id or self.state.request_id,
            "atomic_semantic_producer_commit": True,
            "semantic_producer_commit_boundary": (
                "accepted_contract_observations_coverage"
            ),
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=SEMANTIC_PRODUCER_BUNDLE_COMMIT_STAGE,
            action_type=ActionType.SEMANTIC_PRODUCER_BUNDLE_COMMIT,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.SEMANTIC_PRODUCER_BUNDLE_COMMITTED
            ),
        )

    def authorize_recovered_semantic_delta_commit(
        self,
        *,
        semantic_observation_id: str,
        semantic_observation_digest: str,
        coverage_record_id: str,
        coverage_record_digest: str,
        answer_component_id: str,
        component_revision: str,
        component_digest: str,
        accepted_contract_digest: str | None = None,
        accepted_contract_version: str | None = None,
        request_id: str | None = None,
        reason: str = RECOVERED_SEMANTIC_DELTA_COMMIT_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.initial_answer_contract_projection:
            raise RunKernelTransitionError(
                "recovered semantic delta commit requires an accepted initial "
                "answer contract"
            )
        accepted = self.state.initial_answer_contract
        resolved_contract_digest = (
            accepted_contract_digest
            or accepted.get("accepted_contract_digest")
        )
        resolved_contract_version = (
            accepted_contract_version
            or accepted.get("accepted_contract_version")
        )
        for label, value in (
            ("semantic_observation_id", semantic_observation_id),
            ("semantic_observation_digest", semantic_observation_digest),
            ("coverage_record_id", coverage_record_id),
            ("coverage_record_digest", coverage_record_digest),
            ("answer_component_id", answer_component_id),
            ("component_revision", component_revision),
            ("component_digest", component_digest),
            ("accepted_contract_digest", resolved_contract_digest),
            ("accepted_contract_version", resolved_contract_version),
        ):
            if not _clean_text(value, limit=200):
                raise RunKernelTransitionError(
                    "recovered semantic delta commit requires "
                    f"{label} binding"
                )
        merged_inputs = {
            "semantic_observation_id": semantic_observation_id,
            "semantic_observation_digest": semantic_observation_digest,
            "coverage_record_id": coverage_record_id,
            "coverage_record_digest": coverage_record_digest,
            "answer_component_id": answer_component_id,
            "component_revision": component_revision,
            "component_digest": component_digest,
            "accepted_contract_digest": resolved_contract_digest,
            "accepted_contract_version": resolved_contract_version,
            "request_id": request_id or self.state.request_id,
            "atomic_recovered_semantic_delta_commit": True,
            "semantic_delta_boundary": (
                "semantic_observation_plus_component_coverage"
            ),
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=RECOVERED_SEMANTIC_DELTA_COMMIT_STAGE,
            action_type=ActionType.RECOVERED_SEMANTIC_DELTA_COMMIT,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.RECOVERED_SEMANTIC_DELTA_COMMITTED
            ),
        )

    def commit_semantic_producer_bundle(
        self,
        *,
        question_meaning_record: Mapping[str, Any],
        component_bundles: Sequence[Mapping[str, Any]],
        request_id: str | None = None,
        reason: str = SEMANTIC_PRODUCER_BUNDLE_COMMIT_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> RunState:
        """Atomically commit accepted contract, observations, and coverage.

        The ordinary semantic producer preflights the same payloads before
        calling this method. This method repeats the canonical reducer
        validation against staged in-memory state and mutates RunState only
        after every accepted contract, SemanticObservation admission, and
        ComponentCoverageRecord reduction has been built successfully.
        """

        bundle_payload = normalize_semantic_producer_bundle_payload(
            question_meaning_record=question_meaning_record,
            component_bundles=component_bundles,
        )
        qmr_payload = dict(bundle_payload.get("question_meaning_record") or {})
        component_payloads = list(bundle_payload.get("component_bundles") or ())
        action = self.authorize_semantic_producer_bundle_commit(
            parent_question_meaning_record_id=str(qmr_payload.get("record_id") or ""),
            parent_proposal_digest=str(qmr_payload.get("record_digest") or ""),
            component_count=len(component_payloads),
            request_id=request_id,
            reason=reason,
            inputs=inputs,
        )
        try:
            if action.action_id in self.state.reduced_action_ids:
                raise RunKernelTransitionError("authorized action was already reduced")
            if action.sequence != self.state.next_observation_sequence:
                raise RunKernelTransitionError(
                    "semantic producer bundle commit observation reduced out of order"
                )
            if (
                self.state.initial_answer_contract_projection
                or self.state.initial_answer_contract_history
                or self.state.semantic_observation_admission_history
                or self.state.component_coverage_history
            ):
                raise RunKernelTransitionError(
                    "semantic producer bundle commit requires empty canonical "
                    "semantic state"
                )
            staged = stage_semantic_producer_bundle_commit(
                action_id=action.action_id,
                action_inputs=action.inputs,
                payload=bundle_payload,
                run_id=self.state.run_id,
                request_id=self.state.request_id,
                evidence_ledger_projection=(
                    self.state.evidence_ledger.to_projection().to_dict()
                ),
            )
        except SemanticProducerBundleCommitStagingError as exc:
            transition_error = RunKernelTransitionError(str(exc))
            self._record_semantic_producer_bundle_commit_failure(
                action=action,
                exc=transition_error,
            )
            raise transition_error from exc
        except Exception as exc:
            self._record_semantic_producer_bundle_commit_failure(
                action=action,
                exc=exc,
            )
            if isinstance(exc, RunKernelTransitionError):
                raise
            raise RunKernelTransitionError(
                "semantic producer bundle commit failed before canonical "
                "semantic state mutation"
            ) from exc
        observation = Observation.from_action(
            action,
            observation_type=ObservationType.SEMANTIC_PRODUCER_BUNDLE_COMMITTED,
            status=RunStageStatus.COMPLETED,
            payload=bundle_payload,
        )
        self._apply_semantic_producer_bundle_commit(
            action=action,
            observation=observation,
            staged=staged,
        )
        return self.state

    def _apply_semantic_producer_bundle_commit(
        self,
        *,
        action: AuthorizedAction,
        observation: Observation,
        staged: Mapping[str, Any],
    ) -> None:
        acceptance_state = deepcopy(dict(staged.get("acceptance_state") or {}))
        acceptance_projection = deepcopy(
            dict(staged.get("acceptance_projection") or {})
        )
        admission_states = [
            deepcopy(dict(item))
            for item in staged.get("admission_states") or ()
            if isinstance(item, Mapping)
        ]
        admission_projections = [
            deepcopy(dict(item))
            for item in staged.get("admission_projections") or ()
            if isinstance(item, Mapping)
        ]
        coverage_states = [
            deepcopy(dict(item))
            for item in staged.get("coverage_states") or ()
            if isinstance(item, Mapping)
        ]
        coverage_projections = [
            deepcopy(dict(item))
            for item in staged.get("coverage_projections") or ()
            if isinstance(item, Mapping)
        ]

        self.state.reduced_action_ids.add(action.action_id)
        self.state.action_statuses[action.action_id] = observation.status
        self.state.stage_statuses[action.stage] = observation.status
        self.state.initial_answer_contract = acceptance_state
        self.state.initial_answer_contract_projection = acceptance_projection
        self.state.initial_answer_contract_history.append(
            deepcopy(acceptance_projection)
        )
        self.state.projections[INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE] = (
            deepcopy(acceptance_projection)
        )
        for state, projection in zip(
            admission_states,
            admission_projections,
            strict=True,
        ):
            self.state.semantic_observation_admission_state = state
            self.state.semantic_observation_admission_projection = projection
            self.state.semantic_observation_admission_history.append(
                deepcopy(projection)
            )
        if admission_projections:
            self.state.projections[SEMANTIC_OBSERVATION_ADMISSION_STAGE] = (
                deepcopy(admission_projections[-1])
            )
        for state, projection in zip(
            coverage_states,
            coverage_projections,
            strict=True,
        ):
            self.state.component_coverage_state = state
            self.state.component_coverage_projection = projection
            self.state.component_coverage_history.append(deepcopy(projection))
        if coverage_projections:
            self.state.projections[COMPONENT_COVERAGE_REDUCTION_STAGE] = (
                deepcopy(coverage_projections[-1])
            )
        self.state.projections[action.stage] = {
            "owner": "RunKernel.SemanticProducerBundleCommit",
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "atomic_semantic_producer_commit": True,
            "accepted_contract_committed": True,
            "semantic_observation_count": len(admission_projections),
            "component_coverage_count": len(coverage_projections),
            "accepted_contract_digest": acceptance_projection.get(
                "accepted_contract_digest"
            ),
            "coverage_record_ids": [
                projection.get("coverage_record_id")
                for projection in coverage_projections
            ],
            "live_validation_not_run": True,
        }
        self.state.observations.append(observation)
        self.state.next_observation_sequence += 1

    def commit_recovered_semantic_delta(
        self,
        *,
        semantic_observation: Mapping[str, Any],
        sanitized_content_references: Sequence[Mapping[str, Any]],
        component_coverage_record: Mapping[str, Any],
        answer_component_id: str,
        component_revision: str,
        component_digest: str,
        accepted_contract_digest: str | None = None,
        accepted_contract_version: str | None = None,
        request_id: str | None = None,
        reason: str = RECOVERED_SEMANTIC_DELTA_COMMIT_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically commit a recovered SemanticObservation plus coverage.

        This commit is for an already accepted contract. It stages both existing
        canonical reducers before mutating RunState, then applies observation and
        coverage together through one RunKernel-owned transaction boundary.
        """

        observation_payload = _safe_mapping(semantic_observation)
        content_reference_payloads = [
            _safe_mapping(ref)
            for ref in sanitized_content_references
            if isinstance(ref, Mapping)
        ]
        coverage_payload = _safe_mapping(component_coverage_record)
        action = self.authorize_recovered_semantic_delta_commit(
            semantic_observation_id=str(
                observation_payload.get("observation_id") or ""
            ),
            semantic_observation_digest=str(
                observation_payload.get("observation_digest") or ""
            ),
            coverage_record_id=str(
                coverage_payload.get("record_id")
                or coverage_payload.get("coverage_record_id")
                or ""
            ),
            coverage_record_digest=str(
                coverage_payload.get("record_digest")
                or coverage_payload.get("coverage_record_digest")
                or ""
            ),
            answer_component_id=answer_component_id,
            component_revision=component_revision,
            component_digest=component_digest,
            accepted_contract_digest=accepted_contract_digest,
            accepted_contract_version=accepted_contract_version,
            request_id=request_id,
            reason=reason,
            inputs=inputs,
        )
        try:
            if action.action_id in self.state.reduced_action_ids:
                raise RunKernelTransitionError("authorized action was already reduced")
            if action.sequence != self.state.next_observation_sequence:
                raise RunKernelTransitionError(
                    "recovered semantic delta commit observation reduced out of order"
                )
            if not observation_payload or not content_reference_payloads:
                raise RunKernelTransitionError(
                    "recovered semantic delta commit requires SemanticObservation "
                    "and sanitized content references"
                )
            if not coverage_payload:
                raise RunKernelTransitionError(
                    "recovered semantic delta commit requires ComponentCoverageRecord"
                )
            existing_observation_ids = [
                _safe_mapping(item).get("observation_id")
                for item in self.state.semantic_observation_admission_history
            ]
            existing_observation_digests = [
                _safe_mapping(item).get("observation_digest")
                for item in self.state.semantic_observation_admission_history
            ]
            admission_state = build_semantic_observation_admission_state(
                action_id=action.action_id,
                action_inputs=action.inputs,
                observation_payload={
                    "semantic_observation": observation_payload,
                    "sanitized_content_references": content_reference_payloads,
                },
                accepted_contract=self.state.initial_answer_contract,
                evidence_ledger_projection=(
                    self.state.evidence_ledger.to_projection().to_dict()
                ),
                existing_observation_ids=existing_observation_ids,
                existing_observation_digests=existing_observation_digests,
                run_id=self.state.run_id,
                request_id=self.state.request_id,
            )
            admission_projection = build_semantic_observation_admission_projection(
                admission_state=admission_state
            )
            staged_admission_history = [
                *[
                    deepcopy(dict(item))
                    for item in self.state.semantic_observation_admission_history
                    if isinstance(item, Mapping)
                ],
                deepcopy(admission_projection),
            ]
            existing_coverage_record_ids = [
                _safe_mapping(item).get("coverage_record_id")
                for item in self.state.component_coverage_history
            ]
            existing_coverage_record_digests = [
                _safe_mapping(item).get("coverage_record_digest")
                for item in self.state.component_coverage_history
            ]
            coverage_state = build_component_coverage_reduction_state(
                action_id=action.action_id,
                action_inputs=action.inputs,
                coverage_payload={
                    "component_coverage_record": coverage_payload,
                },
                accepted_contract=self.state.initial_answer_contract,
                admission_history=staged_admission_history,
                evidence_ledger_projection=(
                    self.state.evidence_ledger.to_projection().to_dict()
                ),
                existing_coverage_record_ids=existing_coverage_record_ids,
                existing_coverage_record_digests=existing_coverage_record_digests,
                run_id=self.state.run_id,
                request_id=self.state.request_id,
            )
            coverage_projection = build_component_coverage_reduction_projection(
                coverage_state=coverage_state
            )
        except (SemanticObservationAdmissionError, ComponentCoverageReductionError) as exc:
            transition_error = RunKernelTransitionError(str(exc))
            self._record_recovered_semantic_delta_commit_failure(
                action=action,
                exc=transition_error,
            )
            raise transition_error from exc
        except Exception as exc:
            self._record_recovered_semantic_delta_commit_failure(
                action=action,
                exc=exc,
            )
            if isinstance(exc, RunKernelTransitionError):
                raise
            raise RunKernelTransitionError(
                "recovered semantic delta commit failed before canonical "
                "semantic state mutation"
            ) from exc

        observation = Observation.from_action(
            action,
            observation_type=(
                ObservationType.RECOVERED_SEMANTIC_DELTA_COMMITTED
            ),
            status=RunStageStatus.COMPLETED,
            payload={
                "semantic_observation": observation_payload,
                "sanitized_content_references": content_reference_payloads,
                "component_coverage_record": coverage_payload,
            },
        )
        admission_state = deepcopy(dict(admission_state))
        admission_projection = deepcopy(dict(admission_projection))
        coverage_state = deepcopy(dict(coverage_state))
        coverage_projection = deepcopy(dict(coverage_projection))
        self.state.reduced_action_ids.add(action.action_id)
        self.state.action_statuses[action.action_id] = observation.status
        self.state.stage_statuses[action.stage] = observation.status
        self.state.semantic_observation_admission_state = admission_state
        self.state.semantic_observation_admission_projection = admission_projection
        self.state.semantic_observation_admission_history.append(
            deepcopy(admission_projection)
        )
        self.state.projections[SEMANTIC_OBSERVATION_ADMISSION_STAGE] = (
            deepcopy(admission_projection)
        )
        self.state.component_coverage_state = coverage_state
        self.state.component_coverage_projection = coverage_projection
        self.state.component_coverage_history.append(deepcopy(coverage_projection))
        self.state.projections[COMPONENT_COVERAGE_REDUCTION_STAGE] = (
            deepcopy(coverage_projection)
        )
        projection = {
            "owner": "RunKernel.RecoveredSemanticDeltaCommit",
            "canonical_state": True,
            "trace_only": False,
            "storage_only": False,
            "atomic_recovered_semantic_delta_commit": True,
            "accepted_contract_digest": self.state.initial_answer_contract.get(
                "accepted_contract_digest"
            ),
            "accepted_contract_version": self.state.initial_answer_contract.get(
                "accepted_contract_version"
            ),
            "semantic_observation_id": admission_projection.get(
                "observation_id"
            ),
            "coverage_record_id": coverage_projection.get("coverage_record_id"),
            "answer_component_id": coverage_projection.get(
                "answer_component_id"
            ),
            "live_validation_not_run": True,
        }
        self.state.projections[action.stage] = projection
        self.state.observations.append(observation)
        self.state.next_observation_sequence += 1
        return projection

    def _record_recovered_semantic_delta_commit_failure(
        self,
        *,
        action: AuthorizedAction,
        exc: Exception,
    ) -> None:
        if action.action_id in self.state.reduced_action_ids:
            return
        observation = Observation.from_action(
            action,
            observation_type=(
                ObservationType.RECOVERED_SEMANTIC_DELTA_COMMITTED
            ),
            status=RunStageStatus.FAILED,
            payload={
                "recovered_semantic_delta_commit_failed": True,
                "semantic_state_mutated": False,
                "error_type": type(exc).__name__,
                "error_message": _clean_text(str(exc), limit=300),
            },
        )
        self.state.reduced_action_ids.add(action.action_id)
        self.state.action_statuses[action.action_id] = RunStageStatus.FAILED
        self.state.stage_statuses[action.stage] = RunStageStatus.FAILED
        self.state.projections[action.stage] = dict(observation.payload)
        self.state.observations.append(observation)
        self.state.next_observation_sequence += 1

    def _record_semantic_producer_bundle_commit_failure(
        self,
        *,
        action: AuthorizedAction,
        exc: Exception,
    ) -> None:
        if action.action_id in self.state.reduced_action_ids:
            return
        observation = Observation.from_action(
            action,
            observation_type=ObservationType.SEMANTIC_PRODUCER_BUNDLE_COMMITTED,
            status=RunStageStatus.FAILED,
            payload={
                "semantic_producer_bundle_commit_failed": True,
                "semantic_state_mutated": False,
                "error_type": type(exc).__name__,
                "error_message": _clean_text(str(exc), limit=300),
            },
        )
        self.state.reduced_action_ids.add(action.action_id)
        self.state.action_statuses[action.action_id] = RunStageStatus.FAILED
        self.state.stage_statuses[action.stage] = RunStageStatus.FAILED
        self.state.projections[action.stage] = dict(observation.payload)
        self.state.observations.append(observation)
        self.state.next_observation_sequence += 1

    def authorize_contract_amendment_admission(
        self,
        *,
        amendment_record_id: str,
        amendment_record_digest: str,
        parent_contract_digest: str | None = None,
        parent_contract_version: str | None = None,
        accepted_contract_digest: str | None = None,
        accepted_contract_version: str | None = None,
        request_id: str | None = None,
        reason: str = CONTRACT_AMENDMENT_ADMISSION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.initial_answer_contract_projection:
            raise RunKernelTransitionError(
                "contract amendment admission requires an accepted initial answer contract"
            )
        accepted = self.state.initial_answer_contract
        resolved_contract_digest = (
            accepted_contract_digest or accepted.get("accepted_contract_digest")
        )
        resolved_contract_version = (
            accepted_contract_version or accepted.get("accepted_contract_version")
        )
        resolved_parent_digest = parent_contract_digest or resolved_contract_digest
        resolved_parent_version = parent_contract_version or resolved_contract_version
        for label, value in (
            ("amendment_record_id", amendment_record_id),
            ("amendment_record_digest", amendment_record_digest),
            ("parent_contract_digest", resolved_parent_digest),
            ("parent_contract_version", resolved_parent_version),
            ("accepted_contract_digest", resolved_contract_digest),
            ("accepted_contract_version", resolved_contract_version),
        ):
            if not _clean_text(value, limit=200):
                raise RunKernelTransitionError(
                    "contract amendment admission requires " f"{label} binding"
                )
        merged_inputs = {
            "amendment_record_id": amendment_record_id,
            "amendment_record_digest": amendment_record_digest,
            "parent_contract_digest": resolved_parent_digest,
            "parent_contract_version": resolved_parent_version,
            "accepted_contract_digest": resolved_contract_digest,
            "accepted_contract_version": resolved_contract_version,
            "request_id": request_id or self.state.request_id,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=CONTRACT_AMENDMENT_ADMISSION_STAGE,
            action_type=ActionType.CONTRACT_AMENDMENT_ADMIT,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
        )

    def authorize_search_work_plan_construction(
        self,
        *,
        reason: str = "search_work_plan_shadow_construction_after_run_contract",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.run_contract_projection:
            raise RunKernelTransitionError(
                "SearchWorkPlan construction requires a reduced RunAuthority contract"
            )
        merged_inputs = {
            "run_contract_ref": {
                "contract_id": self.state.run_contract_projection.get("contract_id"),
                "schema_version": self.state.run_contract_projection.get(
                    "schema_version"
                ),
            },
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=SEARCH_WORK_PLAN_CONSTRUCTION_STAGE,
            action_type=ActionType.SEARCH_WORK_PLAN_CONSTRUCT,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.SEARCH_WORK_PLAN_CONSTRUCTED,
        )

    def authorize_query_plan_admission(
        self,
        *,
        reason: str = "query_plan_admission_before_queryplan_consumption",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=QUERY_PLAN_ADMISSION_STAGE,
            action_type=ActionType.QUERY_PLAN_ADMISSION,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.QUERY_PLAN_ADMITTED,
        )

    def authorize_query_production(
        self,
        *,
        reason: str = "query_production_before_candidate_generation",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=QUERY_PRODUCTION_STAGE,
            action_type=ActionType.QUERY_PRODUCTION,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.QUERY_CANDIDATES_PRODUCED,
        )

    def authorize_main_retrieval_pass(
        self,
        *,
        reason: str = "main_retrieval_scheduling_dispatch",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=MAIN_RETRIEVAL_STAGE,
            action_type=ActionType.MAIN_RETRIEVAL_PASS,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.RETRIEVAL_PASS_RESULT,
        )

    def authorize_retrieval_stop_checkpoint(
        self,
        *,
        reason: str = "retrieval_stop_continue_checkpoint",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=RETRIEVAL_STOP_CHECKPOINT_STAGE,
            action_type=ActionType.RETRIEVAL_STOP_CHECKPOINT,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.RETRIEVAL_STOP_DECISION,
        )

    def authorize_evidence_ledger_reduction(
        self,
        *,
        reason: str = "evidence_custody_observation_reduction",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=EVIDENCE_LEDGER_STAGE,
            action_type=ActionType.EVIDENCE_LEDGER_REDUCE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.EVIDENCE_CUSTODY_OBSERVED,
        )

    def authorize_search_judgment(
        self,
        *,
        reason: str = "run_authority_iterative_search_judgment",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.run_contract_projection:
            raise RunKernelTransitionError(
                "search judgment requires a reduced RunAuthority contract"
            )
        if self.state.evidence_ledger.to_projection().to_dict().get(
            "requirement_count",
            0,
        ) <= 0:
            raise RunKernelTransitionError(
                "search judgment requires a reduced EvidenceLedger projection"
            )
        return self.authorize(
            stage=SEARCH_JUDGMENT_STAGE,
            action_type=ActionType.SEARCH_JUDGMENT_DECIDE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.SEARCH_JUDGMENT_DECIDED,
        )

    def authorize_sufficiency_judgment(
        self,
        *,
        reason: str = "run_authority_final_sufficiency_judgment",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.run_contract_projection:
            raise RunKernelTransitionError(
                "sufficiency judgment requires a reduced RunAuthority contract"
            )
        if self.state.evidence_ledger.to_projection().to_dict().get(
            "requirement_count",
            0,
        ) <= 0:
            raise RunKernelTransitionError(
                "sufficiency judgment requires a reduced EvidenceLedger projection"
            )
        return self.authorize(
            stage=SUFFICIENCY_JUDGMENT_STAGE,
            action_type=ActionType.SUFFICIENCY_JUDGMENT_DECIDE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.SUFFICIENCY_JUDGMENT_DECIDED,
        )

    def authorize_final_answer_packet_prepare(
        self,
        *,
        reason: str = "final_answer_packet_preparation_before_author_execution",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=FINAL_ANSWER_PACKET_STAGE,
            action_type=ActionType.FINAL_ANSWER_PACKET_PREPARE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.FINAL_ANSWER_PACKET_PREPARED,
        )

    def authorize_author_execution(
        self,
        *,
        reason: str = "author_execution_from_final_answer_packet_payload",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if self.state.followup_author_payload_construction_state:
            raise RunKernelTransitionError(
                "AG-96I3 Author execution must consume AG-96I3AD Author "
                "payload envelope in a future execution phase"
            )
        if self.state.followup_author_payload_authority_state:
            raise RunKernelTransitionError(
                "AG-96I3 Author execution must consume AG-96I3AC Author "
                "payload authority in a future execution phase"
            )
        if not self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "author execution requires a reduced FinalAnswerPacket"
            )
        payload_ref = self.state.final_answer_authority_projection.get(
            "author_payload_ref",
            {},
        )
        if payload_ref.get("status") != "author_input_ready":
            raise RunKernelTransitionError(
                "author execution requires packet-ready author input payload"
            )
        if self._ag96i3_author_execution_lane_active():
            raise RunKernelTransitionError(
                "AG-96I3 Author execution is subordinated to a future "
                "X-bound activation consumer"
            )
        expected_author_payload_ref_digest = _stable_packet_safe_json_digest(
            payload_ref
        )
        merged_inputs = {
            **dict(inputs or {}),
            "packet_id": self.state.final_answer_packet.get("packet_id"),
            "author_payload_status": payload_ref.get("status"),
            "expected_author_payload_ref_digest": expected_author_payload_ref_digest,
            "author_system_prompt_key": payload_ref.get("author_system_prompt_key"),
            "author_effort": payload_ref.get("author_effort"),
            "author_provider": payload_ref.get("author_provider"),
            "author_model": payload_ref.get("author_model"),
        }
        return self.authorize(
            stage=AUTHOR_EXECUTION_STAGE,
            action_type=ActionType.AUTHOR_EXECUTE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.AUTHOR_OUTPUT_OBSERVED,
        )

    def _ag96i3_author_execution_lane_active(self) -> bool:
        return bool(
            self.state.followup_author_input_authority_state
            or self.state.followup_author_execution_readiness_state
            or self.state.followup_author_input_materialization_state
            or self.state.followup_author_execution_activation_state
            or self.state.followup_author_prompt_assembly_manifest_state
            or self.state.followup_author_payload_authority_state
            or self.state.followup_author_payload_construction_state
            or self.state.followup_author_evidence_content_bridge_state
            or self.state.followup_author_execution_from_ad_state
            or self.state.followup_author_gate_state.get("author_gate_mode")
            == AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
            or self.state.followup_author_model_request_assembly_state
            or self.state.followup_author_execution_from_af4d_state
            or self.state.followup_author_response_finalization_state
        )

    def authorize_followup_authorization_consumption(
        self,
        *,
        reason: str = "ag96i2a_followup_checkpoint_runtime_consumption",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        return self.authorize(
            stage=FOLLOWUP_AUTHORIZATION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHORIZATION_CONSUME,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.FOLLOWUP_AUTHORIZATION_CONSUMED,
        )

    def authorize_followup_fixture_execution(
        self,
        *,
        candidate_id: str,
        reason: str = "ag96i2b_followup_fixture_execution_observation",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_authorization_state:
            raise RunKernelTransitionError(
                "follow-up fixture execution requires reduced follow-up authorization state"
            )
        candidate = _followup_checked(
            followup_sealed_candidate,
            self.state.followup_authorization_state,
            candidate_id,
        )
        merged_inputs = {
            **dict(inputs or {}),
            "followup_authorization_consumption_id": (
                self.state.followup_authorization_state.get("consumption_id")
            ),
            "sealed_candidate_id": candidate.get("candidate_id"),
            "fixture_execution_mode": "fixture_only",
            "provider_job_kind": candidate.get("provider_job_kind"),
            "provider_execution_licensed": False,
            "requirement_ids": candidate.get("requirement_ids", []),
        }
        if merged_inputs.get("fixture_execution_mode") != "fixture_only":
            raise RunKernelTransitionError(
                "follow-up fixture execution only authorizes fixture_only mode"
            )
        return self.authorize(
            stage=FOLLOWUP_EXECUTION_STAGE,
            action_type=ActionType.FOLLOWUP_FIXTURE_EXECUTE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.FOLLOWUP_EXECUTION_OBSERVED,
        )

    def authorize_followup_provider_job_execution(
        self,
        *,
        candidate_id: str,
        reason: str = "ag96i3a_offline_followup_provider_job_execution",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_authorization_state:
            raise RunKernelTransitionError(
                "follow-up provider-job execution requires reduced follow-up "
                "authorization state"
            )
        candidate = _followup_checked(
            followup_sealed_candidate,
            self.state.followup_authorization_state,
            candidate_id,
        )
        if candidate.get("provider_job_kind") != FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND:
            raise RunKernelTransitionError(
                "AG-96I3A only authorizes official_current_candidate_acquisition"
            )
        expected_update = _safe_mapping(
            candidate.get("expected_evidence_ledger_custody_update")
        )
        expected_source_classes = _string_list(expected_update.get("source_classes"))
        if not expected_source_classes or "[redacted]" in expected_source_classes:
            expected_source_classes = [
                "official_government",
                "official_current_rules",
            ]
        if not set(expected_source_classes).intersection(
            {"official_government", "official_current_rules"}
        ):
            raise RunKernelTransitionError(
                "follow-up provider-job execution requires official/current source classes"
            )
        authorized_query_ref = _clean_text(
            candidate.get("authorized_query_ref"),
            limit=180,
        )
        authorized_query = _clean_text(candidate.get("authorized_query"), limit=300)
        if not (authorized_query_ref or authorized_query):
            raise RunKernelTransitionError(
                "follow-up provider-job execution requires authorized query/ref"
            )
        budget_debit = _safe_mapping(candidate.get("budget_debit"))
        _require_followup_provider_job_budget(
            authorization_state=self.state.followup_authorization_state,
            budget_debit=budget_debit,
        )
        merged_inputs = {
            **dict(inputs or {}),
            "run_id": self.state.run_id,
            "checkpoint_id": self.state.followup_authorization_state.get(
                "checkpoint_id"
            ),
            "followup_authorization_consumption_id": (
                self.state.followup_authorization_state.get("consumption_id")
            ),
            "sealed_candidate_id": candidate.get("candidate_id"),
            "execution_mode": FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
            "provider_job_kind": candidate.get("provider_job_kind"),
            "component_id": candidate.get("component_id"),
            "source_obligation_id": candidate.get("source_obligation_id"),
            "requirement_ids": candidate.get("requirement_ids", []),
            "expected_source_classes": expected_source_classes,
            "expected_evidence_ledger_custody_update": expected_update,
            "budget_debit": budget_debit,
            "authorized_query_ref": authorized_query_ref,
            "authorized_query": authorized_query,
            "provider_execution_licensed": False,
            "live_provider_call_executed": False,
            "search_executed": False,
            "retrieval_executed": False,
            "fetch_executed": False,
            "model_called": False,
            "author_activation_allowed": False,
            "author_executor_invoked": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
        }
        return self.authorize(
            stage=FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE,
            action_type=ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_PROVIDER_JOB_EXECUTION_OBSERVED
            ),
        )

    def authorize_followup_evidence_intake(
        self,
        *,
        reason: str = "ag96i2c_followup_fixture_evidence_ledger_intake",
        inputs: Mapping[str, Any] | None = None,
        ag96i3l_admission_review_candidate: Mapping[str, Any] | None = None,
        evidence_ledger_intake_binding: Any | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_execution_state:
            raise RunKernelTransitionError(
                "follow-up evidence intake requires reduced follow-up execution state"
            )
        execution_state = self.state.followup_execution_state
        caller_inputs = dict(inputs or {})
        requested_mode = caller_inputs.get("evidence_ledger_intake_mode")
        candidate_projection = (
            ag96i3m2_admission_review_authorization_projection(
                ag96i3l_admission_review_candidate
            )
            if ag96i3l_admission_review_candidate is not None
            else {}
        )
        binding_projection = (
            ag96i3m2_intake_binding_authorization_projection(
                evidence_ledger_intake_binding
            )
            if evidence_ledger_intake_binding is not None
            else {}
        )
        ag96i3m2_intake_requested = bool(
            requested_mode == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
            or candidate_projection
            or binding_projection
        )
        merged_inputs = {
            **caller_inputs,
            "followup_authorization_consumption_id": execution_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": execution_state.get("sealed_candidate_id"),
            "followup_execution_id": execution_state.get("execution_id"),
            "execution_id": execution_state.get("execution_id"),
            "followup_execution_observation_id": execution_state.get(
                "observation_id"
            ),
            "observation_id": execution_state.get("observation_id"),
            "fixture_execution_mode": execution_state.get("fixture_execution_mode"),
            "execution_mode": execution_state.get("execution_mode")
            or execution_state.get("fixture_execution_mode"),
            "provider_job_kind": execution_state.get("provider_job_kind"),
            "component_id": execution_state.get("component_id"),
            "source_obligation_id": execution_state.get("source_obligation_id"),
            "requirement_ids": execution_state.get("requirement_ids", []),
            "expected_source_classes": execution_state.get(
                "expected_source_classes",
                [],
            ),
            "result_status": execution_state.get("result_status"),
            "bridge_only": execution_state.get("bridge_only"),
            "authorized_query_ref": execution_state.get("authorized_query_ref"),
            "authorized_query": execution_state.get("authorized_query"),
            "provider_execution_licensed": False,
            "evidence_ledger_intake_mode": (
                AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
                if ag96i3m2_intake_requested
                else (
                    "bounded_provider_job_offline_followup_intake"
                    if (
                        execution_state.get("execution_mode")
                        == FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE
                    )
                    else "fixture_only_followup_intake"
                )
            ),
            "expected_observation_record_type": (
                "followup_evidence_intake_consumption_record"
            ),
        }
        if ag96i3m2_intake_requested:
            merged_inputs["ag96i3m2_admission_review_candidate"] = (
                candidate_projection
            )
            merged_inputs["ag96i3m2_evidence_ledger_intake_binding"] = (
                binding_projection
            )
        if merged_inputs.get("execution_mode") not in {
            "fixture_only",
            FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
        }:
            raise RunKernelTransitionError(
                "follow-up evidence intake only authorizes known execution modes"
            )
        if merged_inputs.get("evidence_ledger_intake_mode") not in {
            "fixture_only_followup_intake",
            "bounded_provider_job_offline_followup_intake",
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
        }:
            raise RunKernelTransitionError(
                "follow-up evidence intake only authorizes known intake modes"
            )
        return self.authorize(
            stage=FOLLOWUP_EVIDENCE_INTAKE_STAGE,
            action_type=ActionType.FOLLOWUP_EVIDENCE_INTAKE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_EVIDENCE_INTAKE_OBSERVED
            ),
        )

    def authorize_followup_sufficiency_recheck(
        self,
        *,
        reason: str = "ag96i2d_followup_fixture_sufficiency_recheck",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_evidence_intake_state:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires reduced follow-up "
                "EvidenceLedger intake state"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires canonical intake state"
            )
        execution_mode = (
            intake_state.get("execution_mode")
            or intake_state.get("fixture_execution_mode")
        )
        if intake_state.get("evidence_ledger_intake_mode") not in {
            "fixture_only_followup_intake",
            "bounded_provider_job_offline_followup_intake",
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
        }:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires known intake state"
            )
        if intake_state.get(
            "evidence_ledger_intake_mode"
        ) == AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE:
            if intake_state.get("runtime_evidence_intake_occurred") is not True:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck requires runtime "
                    "EvidenceLedger intake"
                )
            if intake_state.get("source_obligation_satisfied") not in {
                True,
                False,
            }:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck requires explicit source "
                    "obligation posture"
                )
            if intake_state.get("sufficiency_judgment_recheck_deferred") is not True:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck requires deferred "
                    "SufficiencyJudgment"
                )
            if intake_state.get("citation_eligible") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must keep citations closed"
                )
            if intake_state.get("final_evidence_satisfied") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must not consume final evidence"
                )
            if intake_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must keep Author closed"
                )
            if intake_state.get("final_answer_packet_updated") is not False:
                raise RunKernelTransitionError(
                    "AG-96I3M2 sufficiency recheck must not update FinalAnswerPacket"
                )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires EvidenceLedger projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires canonical EvidenceLedger"
            )
        if int(ledger_projection.get("requirement_count") or 0) <= 0:
            raise RunKernelTransitionError(
                "follow-up sufficiency recheck requires EvidenceLedger requirements"
            )
        canonical_inputs = {
            "run_id": intake_state.get("run_id"),
            "checkpoint_id": intake_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": intake_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": intake_state.get("sealed_candidate_id"),
            "followup_execution_id": intake_state.get("followup_execution_id"),
            "execution_id": intake_state.get("execution_id"),
            "followup_execution_observation_id": intake_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": intake_state.get("intake_id"),
            "intake_id": intake_state.get("intake_id"),
            "followup_evidence_intake_observation_id": intake_state.get(
                "observation_id"
            ),
            "provider_job_kind": intake_state.get("provider_job_kind"),
            "component_id": intake_state.get("component_id"),
            "source_obligation_id": intake_state.get("source_obligation_id"),
            "requirement_ids": intake_state.get("requirement_ids", []),
            "expected_source_classes": intake_state.get(
                "expected_source_classes",
                [],
            ),
            "result_status": intake_state.get("result_status"),
            "bridge_only": intake_state.get("bridge_only"),
            "fixture_execution_mode": intake_state.get("fixture_execution_mode"),
            "execution_mode": execution_mode,
            "evidence_ledger_intake_mode": intake_state.get(
                "evidence_ledger_intake_mode"
            ),
            "provider_execution_licensed": False,
            "sufficiency_recheck_mode": FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "evidence_ledger_custody_summary": evidence_ledger_custody_summary(
                ledger_projection
            ),
            "final_answer_packet_deferred": True,
            "author_activation_allowed": False,
            "citation_behavior_changed": False,
            "citation_eligible": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_sufficiency_recheck_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
            action_type=ActionType.FOLLOWUP_SUFFICIENCY_RECHECK,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_SUFFICIENCY_RECHECK_OBSERVED
            ),
        )

    def authorize_followup_final_answer_packet_readiness(
        self,
        *,
        reason: str = "ag96i3o1_final_answer_packet_preparation_readiness",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_sufficiency_recheck_state:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires reduced "
                "follow-up sufficiency recheck state"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires canonical "
                "recheck state"
            )
        if recheck_state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires RunKernel "
                "recheck state"
            )
        if recheck_state.get("sufficiency_recheck_mode") != (
            FOLLOWUP_SUFFICIENCY_RECHECK_MODE
        ):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires fixture-only "
                "sufficiency recheck mode"
            )
        if recheck_state.get("evidence_ledger_intake_mode") != (
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
        ):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires AG-96I3M2 "
                "intake mode"
            )
        if recheck_state.get("final_answer_packet_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires packet-deferred "
                "posture"
            )
        if recheck_state.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires Author closed"
            )
        if recheck_state.get("citation_eligible") is not False:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires citations closed"
            )
        if self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires canonical "
                "FinalAnswerPacket unchanged"
            )
        if self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires final-answer "
                "authority projection unchanged"
            )
        if self.state.followup_final_answer_packet_readiness_state.get(
            "recheck_id"
        ) == recheck_state.get("recheck_id"):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness already recorded for "
                "this recheck"
            )
        if not self.state.sufficiency_judgment_projection:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires canonical "
                "SufficiencyJudgment projection"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires RunAuthority "
                "SufficiencyJudgment"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires canonical "
                "SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires EvidenceLedger "
                "projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires canonical "
                "EvidenceLedger"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket readiness requires canonical "
                "EvidenceLedger intake state"
            )
        canonical_inputs = {
            "run_id": recheck_state.get("run_id"),
            "checkpoint_id": recheck_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": recheck_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": recheck_state.get("sealed_candidate_id"),
            "followup_execution_id": recheck_state.get("followup_execution_id"),
            "execution_id": recheck_state.get("execution_id"),
            "followup_execution_observation_id": recheck_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": recheck_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": recheck_state.get("intake_id"),
            "followup_evidence_intake_observation_id": recheck_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": recheck_state.get("recheck_id"),
            "recheck_id": recheck_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": recheck_state.get(
                "observation_id"
            ),
            "provider_job_kind": recheck_state.get("provider_job_kind"),
            "component_id": recheck_state.get("component_id"),
            "source_obligation_id": recheck_state.get("source_obligation_id"),
            "requirement_ids": recheck_state.get("requirement_ids", []),
            "expected_source_classes": list(
                followup_expected_source_classes(recheck_state)
            ),
            "fixture_execution_mode": recheck_state.get("fixture_execution_mode"),
            "execution_mode": recheck_state.get("execution_mode")
            or recheck_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": recheck_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": recheck_state.get(
                "sufficiency_recheck_mode"
            ),
            "provider_execution_licensed": False,
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "canonical_final_answer_packet_mutated": False,
            "final_evidence_selected": False,
            "citation_eligible": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "author_execution_deferred": True,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "answer_ready": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_final_answer_packet_readiness_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE,
            action_type=ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_READINESS,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_PREPARED
            ),
        )

    def authorize_followup_blocked_final_answer_packet_shell(
        self,
        *,
        reason: str = FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_GATE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        readiness_state = self.state.followup_final_answer_packet_readiness_state
        if not readiness_state:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires O1 readiness state"
            )
        if readiness_state.get("owner") != (
            "RunKernel.FollowupFinalAnswerPacketReadiness"
        ):
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires RunKernel readiness owner"
            )
        if readiness_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires canonical readiness"
            )
        if readiness_state.get("diagnostic_only") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires diagnostic readiness"
            )
        if readiness_state.get("not_final_answer_packet_authority") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires non-authority readiness"
            )
        if readiness_state.get("not_role_consumption_payload") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires non-role readiness"
            )
        for boundary_field in (
            "canonical_final_answer_packet_mutated",
            "final_evidence_selected",
            "citation_eligible",
            "citations_rendered",
            "citation_rendering_changed",
            "citation_behavior_changed",
            "citation_formatter_invoked",
            "author_activation_allowed",
            "author_payload_created",
            "analyst_activation_allowed",
            "analyst_handoff_created",
            "economist_activation_allowed",
            "economist_handoff_created",
            "economist_code_execution_allowed",
            "answer_ready",
            "prompt_behavior_changed",
            "product_answer_behavior_changed",
        ):
            if readiness_state.get(boundary_field) is not False:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell requires readiness "
                    f"{boundary_field}=False"
                )
        if readiness_state.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires Author deferred"
            )
        if readiness_state.get("live_validation_not_run") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires no live validation"
            )
        if self.state.followup_blocked_final_answer_packet_shell_state.get(
            "packet_preparation_readiness_id"
        ) == readiness_state.get("packet_preparation_readiness_id"):
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell already activated for this readiness"
            )
        if self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires no existing canonical "
                "FinalAnswerPacket"
            )
        if self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires final-answer authority "
                "projection unchanged"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires canonical recheck state"
            )
        if recheck_state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires RunKernel recheck state"
            )
        if recheck_state.get("evidence_ledger_intake_mode") != (
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
        ):
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires AG-96I3M2 intake mode"
            )
        if not self.state.sufficiency_judgment_projection:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires canonical SufficiencyJudgment"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires RunAuthority SufficiencyJudgment"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires canonical SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires EvidenceLedger projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires canonical EvidenceLedger"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "blocked FinalAnswerPacket shell requires canonical intake state"
            )
        readiness_id = readiness_state.get("packet_preparation_readiness_id")
        shell_id = f"followup-blocked-final-answer-packet-shell:{readiness_id}"
        canonical_inputs = {
            "run_id": readiness_state.get("run_id"),
            "checkpoint_id": readiness_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": readiness_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": readiness_state.get("sealed_candidate_id"),
            "followup_execution_id": readiness_state.get("followup_execution_id"),
            "execution_id": readiness_state.get("execution_id"),
            "followup_execution_observation_id": readiness_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": readiness_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": readiness_state.get("intake_id"),
            "followup_evidence_intake_observation_id": readiness_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": readiness_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": readiness_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": readiness_state.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "packet_preparation_readiness_id": readiness_id,
            "readiness_observation_id": readiness_state.get("observation_id"),
            "blocked_final_answer_packet_shell_id": shell_id,
            "provider_job_kind": readiness_state.get("provider_job_kind"),
            "component_id": readiness_state.get("component_id"),
            "source_obligation_id": readiness_state.get("source_obligation_id"),
            "requirement_ids": readiness_state.get("requirement_ids", []),
            "expected_source_classes": readiness_state.get(
                "expected_source_classes",
                [],
            ),
            "fixture_execution_mode": readiness_state.get("fixture_execution_mode"),
            "execution_mode": readiness_state.get("execution_mode")
            or readiness_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": readiness_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": readiness_state.get(
                "sufficiency_recheck_mode"
            ),
            "provider_execution_licensed": False,
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "blocked_final_answer_packet_mode": (
                AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
            ),
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "followup_final_answer_packet_readiness_digest": (
                followup_projection_digest(readiness_state)
            ),
            "final_evidence_selected": False,
            "citation_eligible": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "author_execution_deferred": True,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "answer_ready": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_blocked_final_answer_packet_shell_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE,
            action_type=ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_PREPARED
            ),
        )

    def authorize_followup_final_evidence_selection(
        self,
        *,
        reason: str = FOLLOWUP_FINAL_EVIDENCE_SELECTION_GATE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        shell_state = self.state.followup_blocked_final_answer_packet_shell_state
        if not shell_state:
            raise RunKernelTransitionError(
                "final evidence selection requires AG-96I3O2 blocked shell state"
            )
        if shell_state.get("owner") != (
            "RunKernel.FollowupBlockedFinalAnswerPacketShell"
        ):
            raise RunKernelTransitionError(
                "final evidence selection requires RunKernel O2 shell owner"
            )
        if shell_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires canonical O2 shell"
            )
        if shell_state.get("blocked_final_answer_packet_mode") != (
            AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
        ):
            raise RunKernelTransitionError(
                "final evidence selection requires AG-96I3O2 shell mode"
            )
        if not self.state.followup_blocked_final_answer_packet_shell_projection:
            raise RunKernelTransitionError(
                "final evidence selection requires O2 shell projection"
            )
        if not self.state.followup_blocked_final_answer_packet_shell_history:
            raise RunKernelTransitionError(
                "final evidence selection requires O2 shell history"
            )
        packet = self.state.final_answer_packet
        if packet.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "final evidence selection requires RunKernel FinalAnswerPacket"
            )
        if packet.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires canonical FinalAnswerPacket"
            )
        if packet.get("readiness_status") != "blocked":
            raise RunKernelTransitionError(
                "final evidence selection requires blocked FinalAnswerPacket"
            )
        if packet.get("final_answer_allowed") is not False:
            raise RunKernelTransitionError(
                "final evidence selection requires final answers disallowed"
            )
        if packet.get("answer_ready") is not False:
            raise RunKernelTransitionError(
                "final evidence selection requires answer_ready=False"
            )
        if self.state.followup_final_evidence_selection_state.get(
            "blocked_final_answer_packet_shell_id"
        ) == shell_state.get("blocked_final_answer_packet_shell_id"):
            raise RunKernelTransitionError(
                "final evidence selection already activated for this O2 shell"
            )
        if packet.get("final_evidence_selected") is True:
            raise RunKernelTransitionError(
                "final evidence selection cannot supersede selected packet"
            )
        for empty_field in (
            "evidence_allowed",
            "evidence_excluded",
            "author_evidence",
            "citation_eligible",
            "citation_ineligible",
        ):
            if packet.get(empty_field) != []:
                raise RunKernelTransitionError(
                    "final evidence selection requires O2 packet "
                    f"{empty_field} empty"
                )
        if packet.get("author_input_refs") != {}:
            raise RunKernelTransitionError(
                "final evidence selection requires empty author_input_refs"
            )
        if packet.get("final_evidence_selection_deferred") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires deferred O2 evidence selection"
            )
        if packet.get("citation_eligibility_deferred") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires citation eligibility deferred"
            )
        if self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "final evidence selection requires final-answer authority "
                "projection unchanged"
            )
        readiness_state = self.state.followup_final_answer_packet_readiness_state
        if readiness_state.get("owner") != (
            "RunKernel.FollowupFinalAnswerPacketReadiness"
        ):
            raise RunKernelTransitionError(
                "final evidence selection requires O1 readiness state"
            )
        if readiness_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires canonical O1 readiness"
            )
        if not self.state.followup_final_answer_packet_readiness_projection:
            raise RunKernelTransitionError(
                "final evidence selection requires O1 readiness projection"
            )
        if not self.state.followup_final_answer_packet_readiness_history:
            raise RunKernelTransitionError(
                "final evidence selection requires O1 readiness history"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
            raise RunKernelTransitionError(
                "final evidence selection requires AG-96I3N recheck state"
            )
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires canonical AG-96I3N recheck"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires canonical AG-96I3M2 intake"
            )
        if intake_state.get("evidence_ledger_intake_mode") != (
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
        ):
            raise RunKernelTransitionError(
                "final evidence selection requires AG-96I3M2 intake mode"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "final evidence selection requires SufficiencyJudgment projection"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires canonical SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "final evidence selection requires EvidenceLedger projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "final evidence selection requires canonical EvidenceLedger"
            )
        shell_id = shell_state.get("blocked_final_answer_packet_shell_id")
        readiness_id = readiness_state.get("packet_preparation_readiness_id")
        shell_digest = followup_projection_digest(shell_state)
        readiness_digest = followup_projection_digest(readiness_state)
        selection_id = (
            "followup-final-evidence-selection:"
            f"{readiness_digest[:16]}:{shell_digest[:16]}"
        )
        canonical_inputs = {
            "run_id": shell_state.get("run_id"),
            "checkpoint_id": shell_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": shell_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": shell_state.get("sealed_candidate_id"),
            "followup_execution_id": shell_state.get("followup_execution_id"),
            "execution_id": shell_state.get("execution_id"),
            "followup_execution_observation_id": shell_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": shell_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": shell_state.get("intake_id"),
            "followup_evidence_intake_observation_id": shell_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": shell_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": shell_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": shell_state.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "packet_preparation_readiness_id": readiness_id,
            "readiness_observation_id": readiness_state.get("observation_id"),
            "blocked_final_answer_packet_shell_id": shell_id,
            "blocked_final_answer_packet_shell_observation_id": shell_state.get(
                "observation_id"
            ),
            "final_evidence_selection_id": selection_id,
            "provider_job_kind": shell_state.get("provider_job_kind"),
            "component_id": shell_state.get("component_id"),
            "source_obligation_id": shell_state.get("source_obligation_id"),
            "requirement_ids": shell_state.get("requirement_ids", []),
            "expected_source_classes": shell_state.get(
                "expected_source_classes",
                [],
            ),
            "fixture_execution_mode": shell_state.get("fixture_execution_mode"),
            "execution_mode": shell_state.get("execution_mode")
            or shell_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": shell_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": shell_state.get(
                "sufficiency_recheck_mode"
            ),
            "provider_execution_licensed": False,
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "blocked_final_answer_packet_mode": (
                AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
            ),
            "final_evidence_selection_mode": (
                AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
            ),
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "followup_final_answer_packet_readiness_digest": readiness_digest,
            "blocked_final_answer_packet_shell_digest": shell_digest,
            "blocked_final_answer_packet_digest": followup_projection_digest(
                packet
            ),
            "final_answer_allowed": False,
            "answer_ready": False,
            "citation_eligibility_deferred": True,
            "author_execution_deferred": True,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "citation_eligible": [],
            "citation_ineligible": [],
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_final_evidence_selection_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE,
            action_type=ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_FINAL_EVIDENCE_SELECTION_PREPARED
            ),
        )

    def authorize_followup_citation_eligibility(
        self,
        *,
        reason: str = FOLLOWUP_CITATION_ELIGIBILITY_GATE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        selection_state = self.state.followup_final_evidence_selection_state
        if not selection_state:
            raise RunKernelTransitionError(
                "citation eligibility requires AG-96I3P1 final evidence selection"
            )
        if selection_state.get("owner") != "RunKernel.FollowupFinalEvidenceSelection":
            raise RunKernelTransitionError(
                "citation eligibility requires RunKernel P1 selection owner"
            )
        if selection_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical P1 selection"
            )
        if selection_state.get("final_evidence_selection_mode") != (
            AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
        ):
            raise RunKernelTransitionError(
                "citation eligibility requires AG-96I3P1 selection mode"
            )
        if not self.state.followup_final_evidence_selection_projection:
            raise RunKernelTransitionError(
                "citation eligibility requires P1 selection projection"
            )
        if not self.state.followup_final_evidence_selection_history:
            raise RunKernelTransitionError(
                "citation eligibility requires P1 selection history"
            )
        if self.state.followup_citation_eligibility_state.get(
            "final_evidence_selection_id"
        ) == selection_state.get("final_evidence_selection_id"):
            raise RunKernelTransitionError(
                "citation eligibility already activated for this P1 packet"
            )
        packet = self.state.final_answer_packet
        if packet.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "citation eligibility requires RunKernel FinalAnswerPacket"
            )
        if packet.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical FinalAnswerPacket"
            )
        if packet.get("readiness_status") != "blocked":
            raise RunKernelTransitionError(
                "citation eligibility requires blocked FinalAnswerPacket"
            )
        if packet.get("final_answer_allowed") is not False:
            raise RunKernelTransitionError(
                "citation eligibility requires final answers disallowed"
            )
        if packet.get("answer_ready") is not False:
            raise RunKernelTransitionError(
                "citation eligibility requires answer_ready=False"
            )
        if packet.get("final_evidence_selected") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires selected final evidence"
            )
        if not packet.get("evidence_allowed"):
            raise RunKernelTransitionError(
                "citation eligibility requires non-empty evidence_allowed"
            )
        if packet.get("citation_eligible") != []:
            raise RunKernelTransitionError(
                "citation eligibility requires empty citation_eligible"
            )
        if packet.get("citation_ineligible") != []:
            raise RunKernelTransitionError(
                "citation eligibility requires empty citation_ineligible"
            )
        if packet.get("author_input_refs") != {}:
            raise RunKernelTransitionError(
                "citation eligibility requires empty author_input_refs"
            )
        if packet.get("citation_eligibility_deferred") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires deferred P1 packet"
            )
        if packet.get("not_role_consumption_payload") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires non-role packet"
            )
        if self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "citation eligibility requires final-answer authority projection unchanged"
            )
        for closed_field in (
            "citations_rendered",
            "citation_rendering_changed",
            "citation_behavior_changed",
            "citation_formatter_invoked",
            "author_payload_created",
            "author_activation_allowed",
            "analyst_activation_allowed",
            "analyst_handoff_created",
            "economist_activation_allowed",
            "economist_handoff_created",
            "economist_code_execution_allowed",
            "prompt_behavior_changed",
            "product_answer_behavior_changed",
        ):
            if packet.get(closed_field) is not False:
                raise RunKernelTransitionError(
                    "citation eligibility requires P1 packet "
                    f"{closed_field}=False"
                )
        if packet.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires deferred Author execution"
            )
        if packet.get("live_validation_not_run") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires no live validation"
            )
        shell_state = self.state.followup_blocked_final_answer_packet_shell_state
        if shell_state.get("owner") != (
            "RunKernel.FollowupBlockedFinalAnswerPacketShell"
        ):
            raise RunKernelTransitionError(
                "citation eligibility requires O2 blocked packet shell"
            )
        if shell_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical O2 shell"
            )
        readiness_state = self.state.followup_final_answer_packet_readiness_state
        if readiness_state.get("owner") != (
            "RunKernel.FollowupFinalAnswerPacketReadiness"
        ):
            raise RunKernelTransitionError(
                "citation eligibility requires O1 readiness state"
            )
        if readiness_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical O1 readiness"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
            raise RunKernelTransitionError(
                "citation eligibility requires AG-96I3N recheck state"
            )
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical AG-96I3N recheck"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical AG-96I3M2 intake"
            )
        if intake_state.get("evidence_ledger_intake_mode") != (
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
        ):
            raise RunKernelTransitionError(
                "citation eligibility requires AG-96I3M2 intake mode"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "citation eligibility requires SufficiencyJudgment projection"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "citation eligibility requires EvidenceLedger projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation eligibility requires canonical EvidenceLedger"
            )
        selection_digest = followup_projection_digest(selection_state)
        packet_digest = followup_projection_digest(packet)
        citation_eligibility_id = (
            "followup-citation-eligibility:"
            f"{selection_digest[:16]}:{packet_digest[:16]}"
        )
        canonical_inputs = {
            "run_id": selection_state.get("run_id"),
            "checkpoint_id": selection_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": selection_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": selection_state.get("sealed_candidate_id"),
            "followup_execution_id": selection_state.get("followup_execution_id"),
            "execution_id": selection_state.get("execution_id"),
            "followup_execution_observation_id": selection_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": selection_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": selection_state.get("intake_id"),
            "followup_evidence_intake_observation_id": selection_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": selection_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": selection_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": selection_state.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "packet_preparation_readiness_id": selection_state.get(
                "packet_preparation_readiness_id"
            ),
            "readiness_observation_id": selection_state.get(
                "readiness_observation_id"
            ),
            "blocked_final_answer_packet_shell_id": selection_state.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "blocked_final_answer_packet_shell_observation_id": (
                selection_state.get(
                    "blocked_final_answer_packet_shell_observation_id"
                )
            ),
            "final_evidence_selection_id": selection_state.get(
                "final_evidence_selection_id"
            ),
            "final_evidence_selection_observation_id": selection_state.get(
                "observation_id"
            ),
            "citation_eligibility_id": citation_eligibility_id,
            "provider_job_kind": selection_state.get("provider_job_kind"),
            "component_id": selection_state.get("component_id"),
            "source_obligation_id": selection_state.get("source_obligation_id"),
            "requirement_ids": selection_state.get("requirement_ids", []),
            "expected_source_classes": selection_state.get(
                "expected_source_classes",
                [],
            ),
            "fixture_execution_mode": selection_state.get("fixture_execution_mode"),
            "execution_mode": selection_state.get("execution_mode")
            or selection_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": selection_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": selection_state.get(
                "sufficiency_recheck_mode"
            ),
            "provider_execution_licensed": False,
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "blocked_final_answer_packet_mode": (
                AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
            ),
            "final_evidence_selection_mode": (
                AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
            ),
            "citation_eligibility_mode": (
                AG96I3Q1_CITATION_ELIGIBILITY_MODE
            ),
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "followup_final_answer_packet_readiness_digest": (
                followup_projection_digest(readiness_state)
            ),
            "blocked_final_answer_packet_shell_digest": (
                followup_projection_digest(shell_state)
            ),
            "blocked_final_answer_packet_digest": selection_state.get(
                "blocked_final_answer_packet_digest"
            ),
            "followup_final_evidence_selection_digest": selection_digest,
            "current_final_answer_packet_digest": packet_digest,
            "final_answer_allowed": False,
            "answer_ready": False,
            "citation_eligibility_deferred_before_q1": True,
            "citation_rendering_deferred": True,
            "author_execution_deferred": True,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_citation_eligibility_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_CITATION_ELIGIBILITY_STAGE,
            action_type=ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_CITATION_ELIGIBILITY_PREPARED
            ),
        )

    def authorize_followup_citation_source_handoff(
        self,
        *,
        reason: str = FOLLOWUP_CITATION_SOURCE_HANDOFF_GATE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        q1_state = self.state.followup_citation_eligibility_state
        if not q1_state:
            raise RunKernelTransitionError(
                "citation source handoff requires AG-96I3Q1 citation eligibility"
            )
        if q1_state.get("owner") != "RunKernel.FollowupCitationEligibility":
            raise RunKernelTransitionError(
                "citation source handoff requires RunKernel Q1 owner"
            )
        if q1_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical Q1 state"
            )
        if q1_state.get("citation_eligibility_mode") != (
            AG96I3Q1_CITATION_ELIGIBILITY_MODE
        ):
            raise RunKernelTransitionError(
                "citation source handoff requires AG-96I3Q1 mode"
            )
        q1_projection = self.state.followup_citation_eligibility_projection
        if not q1_projection:
            raise RunKernelTransitionError(
                "citation source handoff requires Q1 projection"
            )
        if q1_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical Q1 projection"
            )
        if not self.state.followup_citation_eligibility_history:
            raise RunKernelTransitionError(
                "citation source handoff requires Q1 history"
            )
        if self.state.followup_citation_eligibility_history[-1] != q1_projection:
            raise RunKernelTransitionError(
                "citation source handoff requires current Q1 history"
            )
        if self.state.followup_citation_source_handoff_state.get(
            "citation_eligibility_id"
        ) == q1_state.get("citation_eligibility_id"):
            raise RunKernelTransitionError(
                "citation source handoff already activated for this Q1 packet"
            )
        packet = self.state.final_answer_packet
        if packet.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "citation source handoff requires RunKernel FinalAnswerPacket"
            )
        if packet.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical FinalAnswerPacket"
            )
        if packet.get("packet_id") != q1_state.get("packet_id"):
            raise RunKernelTransitionError(
                "citation source handoff requires Q1 packet ID match"
            )
        if packet.get("readiness_status") != "blocked":
            raise RunKernelTransitionError(
                "citation source handoff requires blocked FinalAnswerPacket"
            )
        if packet.get("final_answer_allowed") is not False:
            raise RunKernelTransitionError(
                "citation source handoff requires final answers disallowed"
            )
        if packet.get("answer_ready") is not False:
            raise RunKernelTransitionError(
                "citation source handoff requires answer_ready=False"
            )
        if packet.get("final_evidence_selected") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires selected final evidence"
            )
        if packet.get("packet_local_citation_eligibility_created") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires packet-local Q1 marker"
            )
        if not packet.get("citation_eligible"):
            raise RunKernelTransitionError(
                "citation source handoff requires packet-local eligible citations"
            )
        if packet.get("citation_rendering_deferred") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires deferred citation rendering"
            )
        if packet.get("citations_rendered") is not False:
            raise RunKernelTransitionError(
                "citation source handoff requires citations_rendered=False"
            )
        if packet.get("citation_formatter_invoked") is not False:
            raise RunKernelTransitionError(
                "citation source handoff requires formatter closed"
            )
        if packet.get("author_input_refs") != {}:
            raise RunKernelTransitionError(
                "citation source handoff requires empty author_input_refs"
            )
        if packet.get("author_payload_ref") not in (None, False, [], {}, ()):
            raise RunKernelTransitionError(
                "citation source handoff requires no author_payload_ref"
            )
        if self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "citation source handoff requires empty authority projection"
            )
        if (
            self.state.followup_final_answer_packet_state
            or self.state.followup_author_gate_state
            or self.state.followup_author_observation_state
            or self.state.author_observation
            or self.state.final_answer_outcome
        ):
            raise RunKernelTransitionError(
                "citation source handoff requires Author surfaces closed"
            )
        for closed_field in (
            "citation_rendering_changed",
            "citation_behavior_changed",
            "author_payload_created",
            "author_activation_allowed",
            "analyst_activation_allowed",
            "analyst_handoff_created",
            "economist_activation_allowed",
            "economist_handoff_created",
            "economist_code_execution_allowed",
            "prompt_behavior_changed",
            "product_answer_behavior_changed",
        ):
            if packet.get(closed_field) is not False:
                raise RunKernelTransitionError(
                    "citation source handoff requires Q1 packet "
                    f"{closed_field}=False"
                )
        if packet.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires deferred Author execution"
            )
        if packet.get("live_validation_not_run") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires no live validation"
            )
        selection_state = self.state.followup_final_evidence_selection_state
        if selection_state.get("owner") != "RunKernel.FollowupFinalEvidenceSelection":
            raise RunKernelTransitionError(
                "citation source handoff requires P1 selection"
            )
        if selection_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical P1 selection"
            )
        if not self.state.followup_final_evidence_selection_projection:
            raise RunKernelTransitionError(
                "citation source handoff requires P1 projection"
            )
        if not self.state.followup_final_evidence_selection_history:
            raise RunKernelTransitionError(
                "citation source handoff requires P1 history"
            )
        shell_state = self.state.followup_blocked_final_answer_packet_shell_state
        if shell_state.get("owner") != (
            "RunKernel.FollowupBlockedFinalAnswerPacketShell"
        ):
            raise RunKernelTransitionError(
                "citation source handoff requires O2 shell"
            )
        if shell_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical O2 shell"
            )
        if not self.state.followup_blocked_final_answer_packet_shell_projection:
            raise RunKernelTransitionError(
                "citation source handoff requires O2 projection"
            )
        if not self.state.followup_blocked_final_answer_packet_shell_history:
            raise RunKernelTransitionError(
                "citation source handoff requires O2 history"
            )
        readiness_state = self.state.followup_final_answer_packet_readiness_state
        if readiness_state.get("owner") != (
            "RunKernel.FollowupFinalAnswerPacketReadiness"
        ):
            raise RunKernelTransitionError(
                "citation source handoff requires O1 readiness"
            )
        if readiness_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical O1 readiness"
            )
        if not self.state.followup_final_answer_packet_readiness_projection:
            raise RunKernelTransitionError(
                "citation source handoff requires O1 projection"
            )
        if not self.state.followup_final_answer_packet_readiness_history:
            raise RunKernelTransitionError(
                "citation source handoff requires O1 history"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
            raise RunKernelTransitionError(
                "citation source handoff requires AG-96I3N recheck"
            )
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical AG-96I3N recheck"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical AG-96I3M2 intake"
            )
        if intake_state.get("evidence_ledger_intake_mode") != (
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
        ):
            raise RunKernelTransitionError(
                "citation source handoff requires AG-96I3M2 intake mode"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "citation source handoff requires SufficiencyJudgment projection"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "citation source handoff requires EvidenceLedger projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation source handoff requires canonical EvidenceLedger"
            )
        q1_digest = followup_projection_digest(q1_state)
        packet_digest = followup_projection_digest(packet)
        handoff_id = (
            "followup-citation-source-handoff:"
            f"{q1_digest[:16]}:{packet_digest[:16]}"
        )
        canonical_inputs = {
            "run_id": q1_state.get("run_id"),
            "checkpoint_id": q1_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": q1_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": q1_state.get("sealed_candidate_id"),
            "followup_execution_id": q1_state.get("followup_execution_id"),
            "execution_id": q1_state.get("execution_id"),
            "followup_execution_observation_id": q1_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": q1_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": q1_state.get("intake_id"),
            "followup_evidence_intake_observation_id": q1_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": q1_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": q1_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": q1_state.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "packet_preparation_readiness_id": q1_state.get(
                "packet_preparation_readiness_id"
            ),
            "readiness_observation_id": q1_state.get("readiness_observation_id"),
            "blocked_final_answer_packet_shell_id": q1_state.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "blocked_final_answer_packet_shell_observation_id": q1_state.get(
                "blocked_final_answer_packet_shell_observation_id"
            ),
            "final_evidence_selection_id": q1_state.get(
                "final_evidence_selection_id"
            ),
            "final_evidence_selection_observation_id": q1_state.get(
                "final_evidence_selection_observation_id"
            ),
            "citation_eligibility_id": q1_state.get("citation_eligibility_id"),
            "citation_eligibility_observation_id": q1_state.get("observation_id"),
            "citation_source_handoff_id": handoff_id,
            "provider_job_kind": q1_state.get("provider_job_kind"),
            "component_id": q1_state.get("component_id"),
            "source_obligation_id": q1_state.get("source_obligation_id"),
            "requirement_ids": q1_state.get("requirement_ids", []),
            "expected_source_classes": q1_state.get("expected_source_classes", []),
            "fixture_execution_mode": q1_state.get("fixture_execution_mode"),
            "execution_mode": q1_state.get("execution_mode")
            or q1_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": q1_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": q1_state.get("sufficiency_recheck_mode"),
            "provider_execution_licensed": False,
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "blocked_final_answer_packet_mode": (
                AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
            ),
            "final_evidence_selection_mode": (
                AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
            ),
            "citation_eligibility_mode": AG96I3Q1_CITATION_ELIGIBILITY_MODE,
            "citation_source_handoff_mode": AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "followup_final_answer_packet_readiness_digest": (
                followup_projection_digest(readiness_state)
            ),
            "blocked_final_answer_packet_shell_digest": (
                followup_projection_digest(shell_state)
            ),
            "blocked_final_answer_packet_digest": q1_state.get(
                "blocked_final_answer_packet_digest"
            ),
            "followup_final_evidence_selection_digest": q1_state.get(
                "followup_final_evidence_selection_digest"
            ),
            "followup_citation_eligibility_digest": q1_digest,
            "current_final_answer_packet_digest": packet_digest,
            "final_answer_allowed": False,
            "answer_ready": False,
            "citation_rendering_deferred": True,
            "author_execution_deferred": True,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "canonical_final_answer_packet_mutated": False,
            "final_answer_packet_updated": False,
            "final_answer_packet_rebuilt": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "ordered_product_source_output_created": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_citation_source_handoff_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE,
            action_type=ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_CITATION_SOURCE_HANDOFF_PREPARED
            ),
        )

    def authorize_followup_citation_rendering(
        self,
        *,
        reason: str = FOLLOWUP_CITATION_RENDERING_GATE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        r1_state = self.state.followup_citation_source_handoff_state
        if not r1_state:
            raise RunKernelTransitionError(
                "citation rendering requires AG-96I3R1 citation source handoff"
            )
        if r1_state.get("owner") != "RunKernel.FollowupCitationSourceHandoff":
            raise RunKernelTransitionError(
                "citation rendering requires RunKernel R1 owner"
            )
        if r1_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical R1 state"
            )
        if r1_state.get("citation_source_handoff_mode") != (
            AG96I3R1_CITATION_SOURCE_HANDOFF_MODE
        ):
            raise RunKernelTransitionError(
                "citation rendering requires AG-96I3R1 mode"
            )
        r1_projection = self.state.followup_citation_source_handoff_projection
        if not r1_projection:
            raise RunKernelTransitionError(
                "citation rendering requires R1 projection"
            )
        if r1_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical R1 projection"
            )
        if not self.state.followup_citation_source_handoff_history:
            raise RunKernelTransitionError(
                "citation rendering requires R1 history"
            )
        if self.state.followup_citation_source_handoff_history[-1] != r1_projection:
            raise RunKernelTransitionError(
                "citation rendering requires current R1 history"
            )
        if self.state.followup_citation_rendering_state.get(
            "citation_source_handoff_id"
        ) == r1_state.get("citation_source_handoff_id"):
            raise RunKernelTransitionError(
                "citation rendering already activated for this R1 handoff"
            )
        if not r1_state.get("source_identity_records"):
            raise RunKernelTransitionError(
                "citation rendering requires R1 source identity records"
            )
        if not r1_state.get("citation_eligible_source_ids"):
            raise RunKernelTransitionError(
                "citation rendering requires R1 citation-eligible source IDs"
            )
        if not r1_state.get("citation_eligibility_refs"):
            raise RunKernelTransitionError(
                "citation rendering requires R1 citation eligibility refs"
            )
        if r1_state.get("citations_rendered") is not False:
            raise RunKernelTransitionError(
                "citation rendering requires R1 citations_rendered=False"
            )
        if r1_state.get("citation_formatter_invoked") is not False:
            raise RunKernelTransitionError(
                "citation rendering requires R1 formatter closed"
            )
        if r1_state.get("ordered_product_source_output_created") is not False:
            raise RunKernelTransitionError(
                "citation rendering requires R1 ordered product output closed"
            )
        packet = self.state.final_answer_packet
        if packet.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "citation rendering requires RunKernel FinalAnswerPacket"
            )
        if packet.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical FinalAnswerPacket"
            )
        if packet.get("packet_id") != r1_state.get("packet_id"):
            raise RunKernelTransitionError(
                "citation rendering requires R1 packet ID match"
            )
        if packet.get("readiness_status") != "blocked":
            raise RunKernelTransitionError(
                "citation rendering requires blocked FinalAnswerPacket"
            )
        if packet.get("final_answer_allowed") is not False:
            raise RunKernelTransitionError(
                "citation rendering requires final answers disallowed"
            )
        if packet.get("answer_ready") is not False:
            raise RunKernelTransitionError(
                "citation rendering requires answer_ready=False"
            )
        if packet.get("author_input_refs") != {}:
            raise RunKernelTransitionError(
                "citation rendering requires empty author_input_refs"
            )
        if packet.get("author_payload_ref") not in (None, False, [], {}, ()):
            raise RunKernelTransitionError(
                "citation rendering requires no author_payload_ref"
            )
        if self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "citation rendering requires empty authority projection"
            )
        if (
            self.state.followup_final_answer_packet_state
            or self.state.followup_author_gate_state
            or self.state.followup_author_observation_state
            or self.state.author_observation
            or self.state.final_answer_outcome
            or getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "citation rendering requires Author/Analyst/Economist surfaces closed"
            )
        for closed_field in (
            "citations_rendered",
            "citation_rendering_changed",
            "citation_behavior_changed",
            "citation_formatter_invoked",
            "author_payload_created",
            "author_activation_allowed",
            "analyst_activation_allowed",
            "analyst_handoff_created",
            "economist_activation_allowed",
            "economist_handoff_created",
            "economist_code_execution_allowed",
            "prompt_behavior_changed",
            "product_answer_behavior_changed",
        ):
            if packet.get(closed_field) is not False:
                raise RunKernelTransitionError(
                    "citation rendering requires packet "
                    f"{closed_field}=False"
                )
        if packet.get("ordered_product_source_output_created", False) is not False:
            raise RunKernelTransitionError(
                "citation rendering requires ordered product output closed"
            )
        if packet.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires deferred Author execution"
            )
        if packet.get("live_validation_not_run") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires no live validation"
            )
        q1_state = self.state.followup_citation_eligibility_state
        if q1_state.get("owner") != "RunKernel.FollowupCitationEligibility":
            raise RunKernelTransitionError(
                "citation rendering requires Q1 citation eligibility"
            )
        if q1_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical Q1"
            )
        q1_projection = self.state.followup_citation_eligibility_projection
        if q1_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical Q1 projection"
            )
        if (
            not self.state.followup_citation_eligibility_history
            or self.state.followup_citation_eligibility_history[-1] != q1_projection
        ):
            raise RunKernelTransitionError(
                "citation rendering requires current Q1 history"
            )
        selection_state = self.state.followup_final_evidence_selection_state
        if selection_state.get("owner") != "RunKernel.FollowupFinalEvidenceSelection":
            raise RunKernelTransitionError(
                "citation rendering requires P1 final evidence selection"
            )
        if selection_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical P1 selection"
            )
        if not self.state.followup_final_evidence_selection_projection:
            raise RunKernelTransitionError(
                "citation rendering requires P1 projection"
            )
        if not self.state.followup_final_evidence_selection_history:
            raise RunKernelTransitionError(
                "citation rendering requires P1 history"
            )
        shell_state = self.state.followup_blocked_final_answer_packet_shell_state
        if shell_state.get("owner") != (
            "RunKernel.FollowupBlockedFinalAnswerPacketShell"
        ):
            raise RunKernelTransitionError(
                "citation rendering requires O2 shell"
            )
        if shell_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical O2 shell"
            )
        if not self.state.followup_blocked_final_answer_packet_shell_projection:
            raise RunKernelTransitionError(
                "citation rendering requires O2 projection"
            )
        if not self.state.followup_blocked_final_answer_packet_shell_history:
            raise RunKernelTransitionError(
                "citation rendering requires O2 history"
            )
        readiness_state = self.state.followup_final_answer_packet_readiness_state
        if readiness_state.get("owner") != (
            "RunKernel.FollowupFinalAnswerPacketReadiness"
        ):
            raise RunKernelTransitionError(
                "citation rendering requires O1 readiness"
            )
        if readiness_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical O1 readiness"
            )
        if not self.state.followup_final_answer_packet_readiness_projection:
            raise RunKernelTransitionError(
                "citation rendering requires O1 projection"
            )
        if not self.state.followup_final_answer_packet_readiness_history:
            raise RunKernelTransitionError(
                "citation rendering requires O1 history"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("owner") != "RunKernel.FollowupSufficiencyRecheck":
            raise RunKernelTransitionError(
                "citation rendering requires AG-96I3N recheck"
            )
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical AG-96I3N recheck"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical AG-96I3M2 intake"
            )
        if intake_state.get("evidence_ledger_intake_mode") != (
            AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE
        ):
            raise RunKernelTransitionError(
                "citation rendering requires AG-96I3M2 intake mode"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "citation rendering requires SufficiencyJudgment projection"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "citation rendering requires EvidenceLedger projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "citation rendering requires canonical EvidenceLedger"
            )
        r1_digest = followup_projection_digest(r1_state)
        packet_digest = followup_projection_digest(packet)
        rendering_id = (
            "followup-citation-rendering:"
            f"{r1_digest[:16]}:{packet_digest[:16]}"
        )
        canonical_inputs = {
            "run_id": r1_state.get("run_id"),
            "checkpoint_id": r1_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": r1_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": r1_state.get("sealed_candidate_id"),
            "followup_execution_id": r1_state.get("followup_execution_id"),
            "execution_id": r1_state.get("execution_id"),
            "followup_execution_observation_id": r1_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": r1_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": r1_state.get("intake_id"),
            "followup_evidence_intake_observation_id": r1_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": r1_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": r1_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": r1_state.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "packet_preparation_readiness_id": r1_state.get(
                "packet_preparation_readiness_id"
            ),
            "readiness_observation_id": r1_state.get("readiness_observation_id"),
            "blocked_final_answer_packet_shell_id": r1_state.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "blocked_final_answer_packet_shell_observation_id": r1_state.get(
                "blocked_final_answer_packet_shell_observation_id"
            ),
            "final_evidence_selection_id": r1_state.get(
                "final_evidence_selection_id"
            ),
            "final_evidence_selection_observation_id": r1_state.get(
                "final_evidence_selection_observation_id"
            ),
            "citation_eligibility_id": r1_state.get("citation_eligibility_id"),
            "citation_eligibility_observation_id": r1_state.get(
                "citation_eligibility_observation_id"
            ),
            "citation_source_handoff_id": r1_state.get(
                "citation_source_handoff_id"
            ),
            "citation_source_handoff_observation_id": r1_state.get("observation_id"),
            "citation_rendering_id": rendering_id,
            "provider_job_kind": r1_state.get("provider_job_kind"),
            "component_id": r1_state.get("component_id"),
            "source_obligation_id": r1_state.get("source_obligation_id"),
            "requirement_ids": r1_state.get("requirement_ids", []),
            "expected_source_classes": r1_state.get("expected_source_classes", []),
            "fixture_execution_mode": r1_state.get("fixture_execution_mode"),
            "execution_mode": r1_state.get("execution_mode")
            or r1_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": r1_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": r1_state.get("sufficiency_recheck_mode"),
            "provider_execution_licensed": False,
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "blocked_final_answer_packet_mode": (
                AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
            ),
            "final_evidence_selection_mode": (
                AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
            ),
            "citation_eligibility_mode": AG96I3Q1_CITATION_ELIGIBILITY_MODE,
            "citation_source_handoff_mode": AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
            "citation_rendering_mode": AG96I3T1_CITATION_RENDERING_MODE,
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "followup_final_answer_packet_readiness_digest": (
                followup_projection_digest(readiness_state)
            ),
            "blocked_final_answer_packet_shell_digest": (
                followup_projection_digest(shell_state)
            ),
            "blocked_final_answer_packet_digest": r1_state.get(
                "blocked_final_answer_packet_digest"
            ),
            "followup_final_evidence_selection_digest": r1_state.get(
                "followup_final_evidence_selection_digest"
            ),
            "followup_citation_eligibility_digest": r1_state.get(
                "followup_citation_eligibility_digest"
            ),
            "followup_citation_source_handoff_digest": r1_digest,
            "source_identity_digest": r1_state.get("source_identity_digest"),
            "current_final_answer_packet_digest": packet_digest,
            "final_answer_allowed": False,
            "answer_ready": False,
            "citation_rendering_deferred": True,
            "author_execution_deferred": True,
            "author_activation_allowed": False,
            "author_payload_created": False,
            "analyst_activation_allowed": False,
            "analyst_handoff_created": False,
            "economist_activation_allowed": False,
            "economist_handoff_created": False,
            "economist_code_execution_allowed": False,
            "citations_rendered": False,
            "citation_rendering_changed": False,
            "citation_behavior_changed": False,
            "citation_formatter_invoked": False,
            "canonical_final_answer_packet_mutated": False,
            "final_answer_packet_updated": False,
            "final_answer_packet_rebuilt": False,
            "prompt_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "ordered_product_source_output_created": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_citation_rendering_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_CITATION_RENDERING_STAGE,
            action_type=ActionType.FOLLOWUP_CITATION_RENDERING,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_CITATION_RENDERING_PREPARED
            ),
        )

    def authorize_followup_author_input_authority(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_INPUT_AUTHORITY_GATE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        t1_state = self.state.followup_citation_rendering_state
        if not t1_state:
            raise RunKernelTransitionError(
                "author input authority requires AG-96I3T1 citation rendering"
            )
        if (
            self.state.followup_author_input_authority_state
            or self.state.followup_author_input_authority_projection
            or self.state.followup_author_input_authority_history
        ):
            raise RunKernelTransitionError(
                "author input authority already prepared for this packet"
            )
        if (
            self.state.followup_final_answer_packet_state
            or self.state.followup_author_gate_state
            or self.state.followup_author_observation_state
            or self.state.author_observation
            or self.state.final_answer_outcome
            or getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "author input authority requires Author/Analyst/Economist surfaces closed"
            )
        packet = self.state.final_answer_packet
        packet_digest = followup_projection_digest(packet)
        t1_digest = followup_projection_digest(t1_state)
        authority_id = (
            "followup-author-input-authority:"
            f"{t1_digest[:16]}:{packet_digest[:16]}"
        )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        canonical_inputs = {
            "run_id": t1_state.get("run_id"),
            "checkpoint_id": t1_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": t1_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": t1_state.get("sealed_candidate_id"),
            "followup_execution_id": t1_state.get("followup_execution_id"),
            "execution_id": t1_state.get("execution_id"),
            "followup_execution_observation_id": t1_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": t1_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": t1_state.get("intake_id"),
            "followup_evidence_intake_observation_id": t1_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": t1_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": t1_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": t1_state.get(
                "followup_sufficiency_recheck_observation_id"
            ),
            "packet_preparation_readiness_id": t1_state.get(
                "packet_preparation_readiness_id"
            ),
            "readiness_observation_id": t1_state.get("readiness_observation_id"),
            "blocked_final_answer_packet_shell_id": t1_state.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "blocked_final_answer_packet_shell_observation_id": t1_state.get(
                "blocked_final_answer_packet_shell_observation_id"
            ),
            "final_evidence_selection_id": t1_state.get(
                "final_evidence_selection_id"
            ),
            "final_evidence_selection_observation_id": t1_state.get(
                "final_evidence_selection_observation_id"
            ),
            "citation_eligibility_id": t1_state.get("citation_eligibility_id"),
            "citation_eligibility_observation_id": t1_state.get(
                "citation_eligibility_observation_id"
            ),
            "citation_source_handoff_id": t1_state.get(
                "citation_source_handoff_id"
            ),
            "citation_source_handoff_observation_id": t1_state.get(
                "citation_source_handoff_observation_id"
            ),
            "citation_rendering_id": t1_state.get("citation_rendering_id"),
            "citation_rendering_observation_id": t1_state.get("observation_id"),
            "author_input_authority_id": authority_id,
            "provider_job_kind": t1_state.get("provider_job_kind"),
            "component_id": t1_state.get("component_id"),
            "source_obligation_id": t1_state.get("source_obligation_id"),
            "requirement_ids": t1_state.get("requirement_ids", []),
            "expected_source_classes": t1_state.get("expected_source_classes", []),
            "fixture_execution_mode": t1_state.get("fixture_execution_mode"),
            "execution_mode": t1_state.get("execution_mode")
            or t1_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": t1_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": t1_state.get("sufficiency_recheck_mode"),
            "packet_preparation_readiness_mode": (
                AG96I3O1_FINAL_ANSWER_PACKET_READINESS_MODE
            ),
            "blocked_final_answer_packet_mode": (
                AG96I3O2_BLOCKED_FINAL_ANSWER_PACKET_MODE
            ),
            "final_evidence_selection_mode": (
                AG96I3P1_FINAL_EVIDENCE_SELECTION_MODE
            ),
            "citation_eligibility_mode": AG96I3Q1_CITATION_ELIGIBILITY_MODE,
            "citation_source_handoff_mode": AG96I3R1_CITATION_SOURCE_HANDOFF_MODE,
            "citation_rendering_mode": AG96I3T1_CITATION_RENDERING_MODE,
            "author_input_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
            "evidence_ledger_projection_digest": evidence_ledger_projection_digest(
                ledger_projection
            ),
            "sufficiency_judgment_digest": followup_projection_digest(
                self.state.sufficiency_judgment_projection
            ),
            "followup_evidence_intake_digest": followup_projection_digest(
                self.state.followup_evidence_intake_state
            ),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                self.state.followup_sufficiency_recheck_state
            ),
            "followup_final_answer_packet_readiness_digest": (
                followup_projection_digest(
                    self.state.followup_final_answer_packet_readiness_state
                )
            ),
            "blocked_final_answer_packet_shell_digest": (
                followup_projection_digest(
                    self.state.followup_blocked_final_answer_packet_shell_state
                )
            ),
            "blocked_final_answer_packet_digest": t1_state.get(
                "blocked_final_answer_packet_digest"
            ),
            "followup_final_evidence_selection_digest": followup_projection_digest(
                self.state.followup_final_evidence_selection_state
            ),
            "followup_citation_eligibility_digest": followup_projection_digest(
                self.state.followup_citation_eligibility_state
            ),
            "followup_citation_source_handoff_digest": followup_projection_digest(
                self.state.followup_citation_source_handoff_state
            ),
            "followup_citation_rendering_digest": t1_digest,
            "source_identity_digest": t1_state.get("source_identity_digest"),
            "rendered_source_entry_digest": t1_state.get(
                "rendered_source_entry_digest"
            ),
            "current_final_answer_packet_digest": packet_digest,
            "prompt_text_included": False,
            "final_text_included": False,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_gate_deferred": True,
            "product_answer_ready": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_author_input_authority_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_input_authority_record(
                action_inputs=merged_inputs,
                evidence_ledger_projection=ledger_projection,
                sufficiency_judgment_projection=(
                    self.state.sufficiency_judgment_projection
                ),
                followup_evidence_intake_state=(
                    self.state.followup_evidence_intake_state
                ),
                followup_sufficiency_recheck_state=(
                    self.state.followup_sufficiency_recheck_state
                ),
                followup_final_answer_packet_readiness_state=(
                    self.state.followup_final_answer_packet_readiness_state
                ),
                followup_final_answer_packet_readiness_projection=(
                    self.state.followup_final_answer_packet_readiness_projection
                ),
                followup_final_answer_packet_readiness_history=(
                    self.state.followup_final_answer_packet_readiness_history
                ),
                followup_blocked_final_answer_packet_shell_state=(
                    self.state.followup_blocked_final_answer_packet_shell_state
                ),
                followup_blocked_final_answer_packet_shell_projection=(
                    self.state.followup_blocked_final_answer_packet_shell_projection
                ),
                followup_blocked_final_answer_packet_shell_history=(
                    self.state.followup_blocked_final_answer_packet_shell_history
                ),
                followup_final_evidence_selection_state=(
                    self.state.followup_final_evidence_selection_state
                ),
                followup_final_evidence_selection_projection=(
                    self.state.followup_final_evidence_selection_projection
                ),
                followup_final_evidence_selection_history=(
                    self.state.followup_final_evidence_selection_history
                ),
                followup_citation_eligibility_state=(
                    self.state.followup_citation_eligibility_state
                ),
                followup_citation_eligibility_projection=(
                    self.state.followup_citation_eligibility_projection
                ),
                followup_citation_eligibility_history=(
                    self.state.followup_citation_eligibility_history
                ),
                followup_citation_source_handoff_state=(
                    self.state.followup_citation_source_handoff_state
                ),
                followup_citation_source_handoff_projection=(
                    self.state.followup_citation_source_handoff_projection
                ),
                followup_citation_source_handoff_history=(
                    self.state.followup_citation_source_handoff_history
                ),
                followup_citation_rendering_state=t1_state,
                followup_citation_rendering_projection=(
                    self.state.followup_citation_rendering_projection
                ),
                followup_citation_rendering_history=(
                    self.state.followup_citation_rendering_history
                ),
                final_answer_packet=packet,
                final_answer_authority_projection=(
                    self.state.final_answer_authority_projection
                ),
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY_PREPARED
            ),
        )

    def authorize_followup_final_answer_packet_prepare(
        self,
        *,
        reason: str = "ag96i2e_followup_fixture_final_answer_packet_prepare",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if self.state.followup_citation_rendering_state:
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot overwrite "
                "an AG-96I3T1 citation rendering state"
            )
        if self.state.followup_citation_source_handoff_state:
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot overwrite "
                "an AG-96I3R1 citation source handoff"
            )
        if self.state.followup_citation_eligibility_state:
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot overwrite "
                "an AG-96I3Q1 citation-eligible packet"
            )
        if self.state.followup_final_evidence_selection_state:
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot overwrite "
                "an AG-96I3P1 evidence-selected packet"
            )
        if self.state.followup_blocked_final_answer_packet_shell_state:
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot overwrite "
                "an AG-96I3O2 blocked packet shell"
            )
        if not self.state.followup_sufficiency_recheck_state:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires reduced "
                "follow-up sufficiency recheck state"
            )
        recheck_state = self.state.followup_sufficiency_recheck_state
        if recheck_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "recheck state"
            )
        if recheck_state.get("sufficiency_recheck_mode") != (
            FOLLOWUP_SUFFICIENCY_RECHECK_MODE
        ):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires fixture-only "
                "sufficiency recheck mode"
            )
        if recheck_state.get("final_answer_packet_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires recheck packet "
                "deferral posture"
            )
        if recheck_state.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires Author closed"
            )
        if self.state.followup_final_answer_packet_state.get("recheck_id") == (
            recheck_state.get("recheck_id")
        ):
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket already prepared for this recheck"
            )
        if not self.state.sufficiency_judgment_projection:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "SufficiencyJudgment projection"
            )
        sufficiency = self.state.sufficiency_judgment_projection
        if sufficiency.get("owner") != "RunKernel.RunAuthoritySufficiencyJudgment":
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires "
                "RunAuthority SufficiencyJudgment"
            )
        if sufficiency.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "SufficiencyJudgment"
            )
        ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
        if ledger_projection.get("owner") != "RunKernel.EvidenceLedger":
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires EvidenceLedger "
                "projection"
            )
        if ledger_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "EvidenceLedger"
            )
        intake_state = self.state.followup_evidence_intake_state
        if intake_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up FinalAnswerPacket preparation requires canonical "
                "EvidenceLedger intake state"
            )
        canonical_inputs = {
            "run_id": recheck_state.get("run_id"),
            "checkpoint_id": recheck_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": recheck_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": recheck_state.get("sealed_candidate_id"),
            "followup_execution_id": recheck_state.get("followup_execution_id"),
            "execution_id": recheck_state.get("execution_id"),
            "followup_execution_observation_id": recheck_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": recheck_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": recheck_state.get("intake_id"),
            "followup_evidence_intake_observation_id": recheck_state.get(
                "followup_evidence_intake_observation_id"
            ),
            "followup_sufficiency_recheck_id": recheck_state.get("recheck_id"),
            "recheck_id": recheck_state.get("recheck_id"),
            "followup_sufficiency_recheck_observation_id": recheck_state.get(
                "observation_id"
            ),
            "provider_job_kind": recheck_state.get("provider_job_kind"),
            "component_id": recheck_state.get("component_id"),
            "source_obligation_id": recheck_state.get("source_obligation_id"),
            "requirement_ids": recheck_state.get("requirement_ids", []),
            "expected_source_classes": list(
                followup_expected_source_classes(recheck_state)
            ),
            "fixture_execution_mode": recheck_state.get("fixture_execution_mode"),
            "execution_mode": recheck_state.get("execution_mode")
            or recheck_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": recheck_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": recheck_state.get(
                "sufficiency_recheck_mode"
            ),
            "provider_execution_licensed": False,
            "final_answer_packet_mode": FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
            "evidence_ledger_projection_digest": (
                evidence_ledger_projection_digest(ledger_projection)
            ),
            "sufficiency_judgment_digest": followup_projection_digest(sufficiency),
            "followup_sufficiency_recheck_digest": followup_projection_digest(
                recheck_state
            ),
            "evidence_ledger_custody_summary": evidence_ledger_custody_summary(
                ledger_projection
            ),
            "final_answer_packet_prepared": False,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "citation_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "final_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_final_answer_packet_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
            action_type=ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARED
            ),
        )

    def authorize_followup_author_gate(
        self,
        *,
        reason: str = "ag96i2f_followup_fixture_author_gate_consumption",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if self.state.followup_author_input_authority_state:
            gate_reason = (
                AG96I3V1_U1_BOUND_AUTHOR_GATE_REASON
                if reason == "ag96i2f_followup_fixture_author_gate_consumption"
                else reason
            )
            return self._authorize_followup_u1_bound_author_gate(
                reason=gate_reason,
                inputs=inputs,
            )
        if not self.state.followup_final_answer_packet_state:
            raise RunKernelTransitionError(
                "follow-up Author gate requires reduced follow-up FinalAnswerPacket state"
            )
        packet_state = self.state.followup_final_answer_packet_state
        if packet_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical FinalAnswerPacket state"
            )
        if packet_state.get("final_answer_packet_mode") != (
            FOLLOWUP_FINAL_ANSWER_PACKET_MODE
        ):
            raise RunKernelTransitionError(
                "follow-up Author gate requires fixture-only FinalAnswerPacket mode"
            )
        if packet_state.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author activation closed"
            )
        if packet_state.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires deferred Author execution"
            )
        if not self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical FinalAnswerPacket"
            )
        if not self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical FinalAnswerPacket "
                "authority projection"
            )
        authority = self.state.final_answer_authority_projection
        if authority.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "follow-up Author gate requires RunKernel FinalAnswerPacket owner"
            )
        if authority.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires canonical packet authority"
            )
        if authority.get("packet_id") != self.state.final_answer_packet.get(
            "packet_id"
        ):
            raise RunKernelTransitionError(
                "follow-up Author gate requires packet/projection packet_id match"
            )
        if authority.get("packet_id") != packet_state.get("packet_id"):
            raise RunKernelTransitionError(
                "follow-up Author gate requires follow-up packet_id match"
            )
        payload_ref = _safe_mapping(authority.get("author_payload_ref"))
        if payload_ref.get("status") != "author_execution_deferred":
            raise RunKernelTransitionError(
                "follow-up Author gate requires deferred Author payload"
            )
        if authority.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author activation closed"
            )
        if authority.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author execution deferred"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "follow-up Author gate requires Author execution not yet reduced"
            )
        if self.state.followup_author_gate_state.get(
            "packet_preparation_id"
        ) == packet_state.get("packet_preparation_id"):
            raise RunKernelTransitionError(
                "follow-up Author gate already consumed this packet"
            )
        canonical_inputs = {
            "run_id": packet_state.get("run_id"),
            "checkpoint_id": packet_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": packet_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": packet_state.get("sealed_candidate_id"),
            "followup_execution_id": packet_state.get("followup_execution_id"),
            "execution_id": packet_state.get("execution_id"),
            "followup_evidence_intake_id": packet_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": packet_state.get("intake_id"),
            "followup_sufficiency_recheck_id": packet_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": packet_state.get("recheck_id"),
            "followup_final_answer_packet_id": packet_state.get(
                "packet_preparation_id"
            ),
            "packet_preparation_id": packet_state.get("packet_preparation_id"),
            "packet_id": self.state.final_answer_packet.get("packet_id"),
            "provider_job_kind": packet_state.get("provider_job_kind"),
            "component_id": packet_state.get("component_id"),
            "source_obligation_id": packet_state.get("source_obligation_id"),
            "requirement_ids": packet_state.get("requirement_ids", []),
            "expected_source_classes": packet_state.get(
                "expected_source_classes",
                [],
            ),
            "fixture_execution_mode": packet_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": packet_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": packet_state.get(
                "sufficiency_recheck_mode"
            ),
            "final_answer_packet_mode": packet_state.get(
                "final_answer_packet_mode"
            ),
            "final_answer_packet_digest": followup_projection_digest(
                self.state.final_answer_packet
            ),
            "final_answer_authority_projection_digest": followup_projection_digest(
                authority
            ),
            "provider_execution_licensed": False,
            "author_gate_mode": FOLLOWUP_AUTHOR_GATE_MODE,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_author_gate_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_GATE_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_GATE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.FOLLOWUP_AUTHOR_GATE_OBSERVED,
        )

    def _authorize_followup_u1_bound_author_gate(
        self,
        *,
        reason: str,
        inputs: Mapping[str, Any] | None,
    ) -> AuthorizedAction:
        u1_state = self.state.followup_author_input_authority_state
        u1_projection = self.state.followup_author_input_authority_projection
        u1_history = self.state.followup_author_input_authority_history
        if u1_state.get("owner") != "RunKernel.FollowupAuthorInputAuthority":
            raise RunKernelTransitionError(
                "V1 Author gate requires RunKernel U1 authority state"
            )
        if u1_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "V1 Author gate requires canonical U1 authority state"
            )
        if u1_state.get("author_input_authority_mode") != (
            AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE
        ):
            raise RunKernelTransitionError(
                "V1 Author gate requires AG-96I3U1 authority mode"
            )
        if not u1_projection:
            raise RunKernelTransitionError(
                "V1 Author gate requires U1 authority projection"
            )
        if u1_projection.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "V1 Author gate requires canonical U1 authority projection"
            )
        if not u1_history:
            raise RunKernelTransitionError(
                "V1 Author gate requires U1 authority history"
            )
        if _safe_mapping(u1_history[-1]) != u1_projection:
            raise RunKernelTransitionError(
                "V1 Author gate requires current U1 authority history"
            )
        authority = self.state.final_answer_authority_projection
        if not authority:
            raise RunKernelTransitionError(
                "V1 Author gate requires final_answer_authority_projection"
            )
        if authority != u1_projection:
            raise RunKernelTransitionError(
                "V1 Author gate requires final_answer_authority_projection "
                "equal to U1 projection"
            )
        if _safe_mapping(u1_state.get("final_answer_authority_projection")) != (
            u1_projection
        ):
            raise RunKernelTransitionError(
                "V1 Author gate requires U1 state/projection binding"
            )
        packet = self.state.final_answer_packet
        if not packet:
            raise RunKernelTransitionError(
                "V1 Author gate requires canonical FinalAnswerPacket"
            )
        if packet.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "V1 Author gate requires RunKernel FinalAnswerPacket"
            )
        if packet.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "V1 Author gate requires canonical FinalAnswerPacket"
            )
        if packet.get("readiness_status") != "blocked":
            raise RunKernelTransitionError(
                "V1 Author gate requires blocked FinalAnswerPacket"
            )
        if packet.get("final_answer_allowed") is not False:
            raise RunKernelTransitionError(
                "V1 Author gate requires final_answer_allowed=false"
            )
        if packet.get("answer_ready") is not False:
            raise RunKernelTransitionError(
                "V1 Author gate requires answer_ready=false"
            )
        if packet.get("product_answer_ready") is not False:
            raise RunKernelTransitionError(
                "V1 Author gate requires product_answer_ready=false"
            )
        author_input_refs = _safe_mapping(packet.get("author_input_refs"))
        if author_input_refs.get("status") != FOLLOWUP_AUTHOR_INPUT_REFS_STATUS:
            raise RunKernelTransitionError(
                "V1 Author gate requires U1 packet author_input_refs"
            )
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "V1 Author gate requires deferred U1 author_payload_ref"
            )
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "V1 Author gate requires non-executable Author payload"
            )
        if author_input_refs != _safe_mapping(u1_state.get("author_input_refs")):
            raise RunKernelTransitionError(
                "V1 Author gate requires packet author_input_refs to match U1"
            )
        if author_payload_ref != _safe_mapping(u1_state.get("author_payload_ref")):
            raise RunKernelTransitionError(
                "V1 Author gate requires packet author_payload_ref to match U1"
            )
        if author_payload_ref != _safe_mapping(u1_projection.get("author_payload_ref")):
            raise RunKernelTransitionError(
                "V1 Author gate requires U1 projection payload ref"
            )
        if author_input_refs.get("author_input_authority_id") != u1_state.get(
            "author_input_authority_id"
        ):
            raise RunKernelTransitionError(
                "V1 Author gate requires U1 authority id in packet refs"
            )
        if author_input_refs.get("final_answer_authority_projection_digest") != (
            followup_projection_digest(authority)
        ):
            raise RunKernelTransitionError(
                "V1 Author gate requires current U1 projection digest in packet refs"
            )
        if author_input_refs.get("author_payload_ref_id") != (
            author_payload_ref.get("payload_ref_id")
        ):
            raise RunKernelTransitionError(
                "V1 Author gate requires packet ref/payload ref match"
            )
        if self.state.followup_author_gate_state:
            raise RunKernelTransitionError(
                "V1 Author gate requires no existing Author gate state"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "V1 Author gate requires no Author observation state"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "V1 Author gate requires Author/final answer output closed"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "V1 Author gate requires Analyst/Economist handoff closed"
            )
        canonical_inputs = {
            "run_id": u1_state.get("run_id"),
            "checkpoint_id": u1_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": u1_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": u1_state.get("sealed_candidate_id"),
            "followup_execution_id": u1_state.get("followup_execution_id"),
            "execution_id": u1_state.get("execution_id"),
            "followup_execution_observation_id": u1_state.get(
                "followup_execution_observation_id"
            ),
            "followup_evidence_intake_id": u1_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": u1_state.get("intake_id"),
            "followup_sufficiency_recheck_id": u1_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": u1_state.get("recheck_id"),
            "packet_preparation_readiness_id": u1_state.get(
                "packet_preparation_readiness_id"
            ),
            "blocked_final_answer_packet_shell_id": u1_state.get(
                "blocked_final_answer_packet_shell_id"
            ),
            "final_evidence_selection_id": u1_state.get(
                "final_evidence_selection_id"
            ),
            "citation_eligibility_id": u1_state.get("citation_eligibility_id"),
            "citation_source_handoff_id": u1_state.get(
                "citation_source_handoff_id"
            ),
            "citation_rendering_id": u1_state.get("citation_rendering_id"),
            "packet_id": packet.get("packet_id"),
            "provider_job_kind": u1_state.get("provider_job_kind"),
            "component_id": u1_state.get("component_id"),
            "source_obligation_id": u1_state.get("source_obligation_id"),
            "requirement_ids": u1_state.get("requirement_ids", []),
            "expected_source_classes": u1_state.get("expected_source_classes", []),
            "evidence_ledger_intake_mode": u1_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": u1_state.get("sufficiency_recheck_mode"),
            "packet_preparation_readiness_mode": u1_state.get(
                "packet_preparation_readiness_mode"
            ),
            "blocked_final_answer_packet_mode": u1_state.get(
                "blocked_final_answer_packet_mode"
            ),
            "final_evidence_selection_mode": u1_state.get(
                "final_evidence_selection_mode"
            ),
            "citation_eligibility_mode": u1_state.get("citation_eligibility_mode"),
            "citation_source_handoff_mode": u1_state.get(
                "citation_source_handoff_mode"
            ),
            "citation_rendering_mode": u1_state.get("citation_rendering_mode"),
            "author_input_authority_id": u1_state.get("author_input_authority_id"),
            "author_input_authority_mode": AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
            "author_gate_id": (
                "followup-author-gate:"
                f"{u1_state.get('author_input_authority_id')}"
            ),
            "author_gate_mode": AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
            "followup_author_input_authority_digest": followup_projection_digest(
                u1_state
            ),
            "followup_author_input_authority_projection_digest": (
                followup_projection_digest(u1_projection)
            ),
            "final_answer_authority_projection_digest": followup_projection_digest(
                authority
            ),
            "final_answer_packet_digest": followup_projection_digest(packet),
            "current_final_answer_packet_digest": followup_projection_digest(packet),
            "author_input_refs_digest": followup_projection_digest(
                author_input_refs
            ),
            "author_payload_ref_id": author_payload_ref.get("payload_ref_id"),
            "author_payload_ref_status": author_payload_ref.get("status"),
            "rendered_source_entry_digest": author_input_refs.get(
                "rendered_source_entry_digest"
            ),
            "packet_authority_consumed": True,
            "author_input_authority_consumed": True,
            "author_gate_consumed": True,
            "author_activation_allowed": False,
            "author_execution_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "model_called": False,
            "prompt_text_included": False,
            "final_text_included": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "citation_behavior_changed": False,
            "product_answer_behavior_changed": False,
            "product_answer_ready": False,
            "final_answer_behavior_changed": False,
            "provider_execution_licensed": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_author_gate_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_GATE_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_GATE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.FOLLOWUP_AUTHOR_GATE_OBSERVED,
        )

    def authorize_followup_author_execution_readiness(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_EXECUTION_READINESS_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        v1_state = self.state.followup_author_gate_state
        if not v1_state:
            raise RunKernelTransitionError(
                "W Author execution readiness requires reduced V1 Author gate"
            )
        if (
            self.state.followup_author_execution_readiness_state
            or self.state.followup_author_execution_readiness_projection
            or self.state.followup_author_execution_readiness_history
        ):
            raise RunKernelTransitionError(
                "W Author execution readiness already prepared"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "W Author execution readiness requires no Author observation"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "W Author execution readiness requires Author/final output closed"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "W Author execution readiness requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "W Author execution readiness rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "W Author execution readiness requires deferred U1 payload status"
            )

        u1_state = self.state.followup_author_input_authority_state
        u1_projection = self.state.followup_author_input_authority_projection
        canonical_inputs = build_followup_author_execution_readiness_action_inputs(
            followup_author_gate_state=v1_state,
            followup_author_gate_projection=self.state.followup_author_gate_projection,
            followup_author_input_authority_state=u1_state,
            followup_author_input_authority_projection=u1_projection,
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_execution_readiness_record(
                action_inputs=merged_inputs,
                followup_author_gate_state=v1_state,
                followup_author_gate_projection=(
                    self.state.followup_author_gate_projection
                ),
                followup_author_gate_history=self.state.followup_author_gate_history,
                followup_author_input_authority_state=u1_state,
                followup_author_input_authority_projection=u1_projection,
                followup_author_input_authority_history=(
                    self.state.followup_author_input_authority_history
                ),
                final_answer_packet=packet,
                final_answer_authority_projection=authority,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_EXECUTION_READINESS_PREPARED
            ),
        )

    def authorize_followup_author_input_materialization(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        w_state = self.state.followup_author_execution_readiness_state
        if not w_state:
            raise RunKernelTransitionError(
                "X Author input materialization requires reduced W readiness"
            )
        if (
            self.state.followup_author_input_materialization_state
            or self.state.followup_author_input_materialization_projection
            or self.state.followup_author_input_materialization_history
        ):
            raise RunKernelTransitionError(
                "X Author input materialization already prepared"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "X Author input materialization requires no Author observation"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "X Author input materialization requires Author/final output closed"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "X Author input materialization requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "X Author input materialization rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "X Author input materialization requires deferred U1 payload status"
            )
        try:
            reject_followup_author_input_materialization_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        canonical_inputs = build_followup_author_input_materialization_action_inputs(
            followup_author_execution_readiness_state=w_state,
            followup_author_execution_readiness_projection=(
                self.state.followup_author_execution_readiness_projection
            ),
            followup_author_gate_state=self.state.followup_author_gate_state,
            followup_author_gate_projection=self.state.followup_author_gate_projection,
            followup_author_input_authority_state=(
                self.state.followup_author_input_authority_state
            ),
            followup_author_input_authority_projection=(
                self.state.followup_author_input_authority_projection
            ),
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_input_materialization_record(
                action_inputs=merged_inputs,
                followup_author_execution_readiness_state=w_state,
                followup_author_execution_readiness_projection=(
                    self.state.followup_author_execution_readiness_projection
                ),
                followup_author_execution_readiness_history=(
                    self.state.followup_author_execution_readiness_history
                ),
                followup_author_gate_state=self.state.followup_author_gate_state,
                followup_author_gate_projection=(
                    self.state.followup_author_gate_projection
                ),
                followup_author_gate_history=self.state.followup_author_gate_history,
                followup_author_input_authority_state=(
                    self.state.followup_author_input_authority_state
                ),
                followup_author_input_authority_projection=(
                    self.state.followup_author_input_authority_projection
                ),
                followup_author_input_authority_history=(
                    self.state.followup_author_input_authority_history
                ),
                final_answer_packet=packet,
                final_answer_authority_projection=authority,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZED
            ),
        )

    def authorize_followup_author_execution_activation(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        x_state = self.state.followup_author_input_materialization_state
        if not x_state:
            raise RunKernelTransitionError(
                "Y Author execution activation requires reduced X materialization"
            )
        if (
            self.state.followup_author_execution_activation_state
            or self.state.followup_author_execution_activation_projection
            or self.state.followup_author_execution_activation_history
        ):
            raise RunKernelTransitionError(
                "Y Author execution activation already prepared"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "Y Author execution activation requires no Author observation"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "Y Author execution activation requires Author/final output closed"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "Y Author execution activation requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "Y Author execution activation rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "Y Author execution activation requires deferred U1 payload status"
            )
        try:
            reject_followup_author_execution_activation_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        canonical_inputs = build_followup_author_execution_activation_action_inputs(
            followup_author_input_materialization_state=x_state,
            followup_author_input_materialization_projection=(
                self.state.followup_author_input_materialization_projection
            ),
            followup_author_execution_readiness_state=(
                self.state.followup_author_execution_readiness_state
            ),
            followup_author_execution_readiness_projection=(
                self.state.followup_author_execution_readiness_projection
            ),
            followup_author_gate_state=self.state.followup_author_gate_state,
            followup_author_gate_projection=self.state.followup_author_gate_projection,
            followup_author_input_authority_state=(
                self.state.followup_author_input_authority_state
            ),
            followup_author_input_authority_projection=(
                self.state.followup_author_input_authority_projection
            ),
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_execution_activation_record(
                action_inputs=merged_inputs,
                followup_author_input_materialization_state=x_state,
                followup_author_input_materialization_projection=(
                    self.state.followup_author_input_materialization_projection
                ),
                followup_author_input_materialization_history=(
                    self.state.followup_author_input_materialization_history
                ),
                followup_author_execution_readiness_state=(
                    self.state.followup_author_execution_readiness_state
                ),
                followup_author_execution_readiness_projection=(
                    self.state.followup_author_execution_readiness_projection
                ),
                followup_author_execution_readiness_history=(
                    self.state.followup_author_execution_readiness_history
                ),
                followup_author_gate_state=self.state.followup_author_gate_state,
                followup_author_gate_projection=(
                    self.state.followup_author_gate_projection
                ),
                followup_author_gate_history=self.state.followup_author_gate_history,
                followup_author_input_authority_state=(
                    self.state.followup_author_input_authority_state
                ),
                followup_author_input_authority_projection=(
                    self.state.followup_author_input_authority_projection
                ),
                followup_author_input_authority_history=(
                    self.state.followup_author_input_authority_history
                ),
                final_answer_packet=packet,
                final_answer_authority_projection=authority,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_PREPARED
            ),
        )

    def authorize_followup_author_prompt_assembly_manifest(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        y_state = self.state.followup_author_execution_activation_state
        if not y_state:
            raise RunKernelTransitionError(
                "Z Author prompt assembly manifest requires reduced Y activation"
            )
        if (
            self.state.followup_author_prompt_assembly_manifest_state
            or self.state.followup_author_prompt_assembly_manifest_projection
            or self.state.followup_author_prompt_assembly_manifest_history
        ):
            raise RunKernelTransitionError(
                "Z Author prompt assembly manifest already prepared"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "Z Author prompt assembly manifest requires no Author observation"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "Z Author prompt assembly manifest requires Author/final output closed"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "Z Author prompt assembly manifest requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "Z Author prompt assembly manifest rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "Z Author prompt assembly manifest requires deferred payload status"
            )
        try:
            reject_followup_author_prompt_assembly_manifest_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        canonical_inputs = build_followup_author_prompt_assembly_manifest_action_inputs(
            followup_author_execution_activation_state=y_state,
            followup_author_execution_activation_projection=(
                self.state.followup_author_execution_activation_projection
            ),
            followup_author_input_materialization_state=(
                self.state.followup_author_input_materialization_state
            ),
            followup_author_execution_readiness_state=(
                self.state.followup_author_execution_readiness_state
            ),
            followup_author_gate_state=self.state.followup_author_gate_state,
            followup_author_input_authority_state=(
                self.state.followup_author_input_authority_state
            ),
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_prompt_assembly_manifest_record(
                action_inputs=merged_inputs,
                followup_author_execution_activation_state=y_state,
                followup_author_execution_activation_projection=(
                    self.state.followup_author_execution_activation_projection
                ),
                followup_author_execution_activation_history=(
                    self.state.followup_author_execution_activation_history
                ),
                followup_author_input_materialization_state=(
                    self.state.followup_author_input_materialization_state
                ),
                followup_author_input_materialization_projection=(
                    self.state.followup_author_input_materialization_projection
                ),
                followup_author_input_materialization_history=(
                    self.state.followup_author_input_materialization_history
                ),
                followup_author_execution_readiness_state=(
                    self.state.followup_author_execution_readiness_state
                ),
                followup_author_execution_readiness_projection=(
                    self.state.followup_author_execution_readiness_projection
                ),
                followup_author_execution_readiness_history=(
                    self.state.followup_author_execution_readiness_history
                ),
                followup_author_gate_state=self.state.followup_author_gate_state,
                followup_author_gate_projection=(
                    self.state.followup_author_gate_projection
                ),
                followup_author_gate_history=self.state.followup_author_gate_history,
                followup_author_input_authority_state=(
                    self.state.followup_author_input_authority_state
                ),
                followup_author_input_authority_projection=(
                    self.state.followup_author_input_authority_projection
                ),
                followup_author_input_authority_history=(
                    self.state.followup_author_input_authority_history
                ),
                final_answer_packet=packet,
                final_answer_authority_projection=authority,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_PREPARED
            ),
        )

    def authorize_followup_author_payload_authority(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        z_state = self.state.followup_author_prompt_assembly_manifest_state
        if not z_state:
            raise RunKernelTransitionError(
                "AC Author payload authority requires reduced Z prompt manifest"
            )
        if (
            self.state.followup_author_payload_authority_state
            or self.state.followup_author_payload_authority_projection
            or self.state.followup_author_payload_authority_history
        ):
            raise RunKernelTransitionError("AC Author payload authority already prepared")
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "AC Author payload authority requires no Author observation"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "AC Author payload authority requires Author/final output closed"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "AC Author payload authority requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "AC Author payload authority rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "AC Author payload authority requires deferred payload status"
            )
        try:
            reject_followup_author_payload_authority_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        canonical_inputs = build_followup_author_payload_authority_action_inputs(
            followup_author_prompt_assembly_manifest_state=z_state,
            followup_author_prompt_assembly_manifest_projection=(
                self.state.followup_author_prompt_assembly_manifest_projection
            ),
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_payload_authority_record(
                action_inputs=merged_inputs,
                followup_author_prompt_assembly_manifest_state=z_state,
                followup_author_prompt_assembly_manifest_projection=(
                    self.state.followup_author_prompt_assembly_manifest_projection
                ),
                followup_author_prompt_assembly_manifest_history=(
                    self.state.followup_author_prompt_assembly_manifest_history
                ),
                followup_author_execution_activation_state=(
                    self.state.followup_author_execution_activation_state
                ),
                followup_author_input_materialization_state=(
                    self.state.followup_author_input_materialization_state
                ),
                followup_author_execution_readiness_state=(
                    self.state.followup_author_execution_readiness_state
                ),
                followup_author_gate_state=self.state.followup_author_gate_state,
                followup_author_input_authority_state=(
                    self.state.followup_author_input_authority_state
                ),
                final_answer_packet=packet,
                final_answer_authority_projection=authority,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_PREPARED
            ),
        )

    def authorize_followup_author_payload_construction(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        ac_state = self.state.followup_author_payload_authority_state
        if not ac_state:
            raise RunKernelTransitionError(
                "AD Author payload construction requires reduced AC payload authority"
            )
        if (
            self.state.followup_author_payload_construction_state
            or self.state.followup_author_payload_construction_projection
            or self.state.followup_author_payload_construction_history
        ):
            raise RunKernelTransitionError("AD Author payload envelope already constructed")
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "AD Author payload construction requires no Author observation"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "AD Author payload construction requires Author/final output closed"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "AD Author payload construction requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "AD Author payload construction rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "AD Author payload construction requires deferred payload status"
            )
        try:
            reject_followup_author_payload_construction_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        canonical_inputs = build_followup_author_payload_construction_action_inputs(
            followup_author_payload_authority_state=ac_state,
            followup_author_payload_authority_projection=(
                self.state.followup_author_payload_authority_projection
            ),
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_payload_construction_record(
                action_inputs=merged_inputs,
                followup_author_payload_authority_state=ac_state,
                followup_author_payload_authority_projection=(
                    self.state.followup_author_payload_authority_projection
                ),
                followup_author_payload_authority_history=(
                    self.state.followup_author_payload_authority_history
                ),
                followup_author_prompt_assembly_manifest_state=(
                    self.state.followup_author_prompt_assembly_manifest_state
                ),
                followup_author_execution_activation_state=(
                    self.state.followup_author_execution_activation_state
                ),
                followup_author_input_materialization_state=(
                    self.state.followup_author_input_materialization_state
                ),
                followup_author_execution_readiness_state=(
                    self.state.followup_author_execution_readiness_state
                ),
                followup_author_gate_state=self.state.followup_author_gate_state,
                followup_author_input_authority_state=(
                    self.state.followup_author_input_authority_state
                ),
                final_answer_packet=packet,
                final_answer_authority_projection=authority,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTED
            ),
        )

    def _followup_author_execution_from_ad_runtime_inputs(self) -> dict[str, Any]:
        state = self.state
        prefixes = (
            "followup_author_payload_construction",
            "followup_author_payload_authority",
            "followup_author_prompt_assembly_manifest",
            "followup_author_execution_activation",
            "followup_author_input_materialization",
            "followup_author_execution_readiness",
            "followup_author_gate",
            "followup_author_input_authority",
        )
        runtime_inputs = {
            f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
            for prefix in prefixes
            for suffix in ("state", "projection", "history")
        }
        runtime_inputs["final_answer_packet"] = state.final_answer_packet
        runtime_inputs["final_answer_authority_projection"] = (
            state.final_answer_authority_projection
        )
        return runtime_inputs

    def _followup_author_evidence_content_bridge_runtime_inputs(
        self,
    ) -> dict[str, Any]:
        state = self.state
        prefixes = (
            "followup_author_payload_construction",
            "followup_author_payload_authority",
            "followup_author_prompt_assembly_manifest",
            "followup_author_execution_activation",
            "followup_author_input_materialization",
            "followup_author_execution_readiness",
            "followup_author_gate",
            "followup_author_input_authority",
            "followup_final_evidence_selection",
            "followup_citation_eligibility",
            "followup_citation_source_handoff",
            "followup_citation_rendering",
        )
        runtime_inputs = {
            f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
            for prefix in prefixes
            for suffix in ("state", "projection", "history")
        }
        runtime_inputs["final_answer_packet"] = state.final_answer_packet
        runtime_inputs["final_answer_authority_projection"] = (
            state.final_answer_authority_projection
        )
        return runtime_inputs

    def _followup_author_invocation_construction_runtime_inputs(
        self,
    ) -> dict[str, Any]:
        state = self.state
        prefixes = (
            "followup_author_payload_construction",
            "followup_author_payload_authority",
            "followup_author_prompt_assembly_manifest",
            "followup_author_execution_activation",
            "followup_author_input_materialization",
            "followup_author_execution_readiness",
            "followup_author_gate",
            "followup_author_input_authority",
            "followup_author_evidence_content_bridge",
            "followup_final_evidence_selection",
            "followup_citation_eligibility",
            "followup_citation_source_handoff",
            "followup_citation_rendering",
        )
        runtime_inputs = {
            f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
            for prefix in prefixes
            for suffix in ("state", "projection", "history")
        }
        runtime_inputs["final_answer_packet"] = state.final_answer_packet
        runtime_inputs["final_answer_authority_projection"] = (
            state.final_answer_authority_projection
        )
        return runtime_inputs

    def _followup_author_model_request_assembly_runtime_inputs(
        self,
    ) -> dict[str, Any]:
        state = self.state
        prefixes = "followup_author_payload_construction followup_author_payload_authority followup_author_prompt_assembly_manifest followup_author_execution_activation followup_author_input_materialization followup_author_execution_readiness followup_author_gate followup_author_input_authority followup_author_evidence_content_bridge followup_author_invocation_construction followup_final_evidence_selection followup_citation_eligibility followup_citation_source_handoff followup_citation_rendering".split()
        runtime_inputs = {
            f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
            for prefix in prefixes
            for suffix in ("state", "projection", "history")
        }
        runtime_inputs["run_request"] = state.request
        return runtime_inputs

    def _followup_author_execution_from_af4d_runtime_inputs(
        self,
    ) -> dict[str, Any]:
        state = self.state
        prefixes = (
            "followup_author_evidence_content_bridge",
            "followup_author_invocation_construction",
            "followup_author_model_request_assembly",
        )
        runtime_inputs = {
            f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
            for prefix in prefixes
            for suffix in ("state", "projection", "history")
        }
        runtime_inputs["run_request"] = state.request
        return runtime_inputs

    def _followup_author_response_finalization_runtime_inputs(
        self,
    ) -> dict[str, Any]:
        state = self.state
        prefixes = ("followup_author_execution_from_af4d",)
        runtime_inputs = {
            f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
            for prefix in prefixes
            for suffix in ("state", "projection", "history")
        }
        runtime_inputs["final_answer_packet"] = state.final_answer_packet
        runtime_inputs["final_answer_authority_projection"] = (
            state.final_answer_authority_projection
        )
        return runtime_inputs

    def authorize_followup_author_evidence_content_bridge(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        ad_state = self.state.followup_author_payload_construction_state
        if not ad_state:
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge requires reduced AD payload envelope"
            )
        if (
            self.state.followup_author_evidence_content_bridge_state
            or self.state.followup_author_evidence_content_bridge_projection
            or self.state.followup_author_evidence_content_bridge_history
        ):
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge already prepared"
            )
        if (
            self.state.followup_author_invocation_construction_state
            or self.state.followup_author_invocation_construction_projection
            or self.state.followup_author_invocation_construction_history
        ):
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge requires AF4a absent"
            )
        if (
            self.state.followup_author_execution_from_ad_state
            or self.state.followup_author_execution_from_ad_projection
            or self.state.followup_author_execution_from_ad_history
        ):
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge requires AE execution absent"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge requires legacy fixture observation closed"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge requires no Author/final outcome"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "AF4B2 Author evidence-content bridge requires deferred payload status"
            )
        try:
            reject_followup_author_evidence_content_bridge_input_spoof(inputs)
            canonical_inputs = (
                build_followup_author_evidence_content_bridge_action_inputs(
                    followup_author_payload_construction_state=ad_state,
                    followup_author_payload_construction_projection=(
                        self.state.followup_author_payload_construction_projection
                    ),
                    final_answer_packet=packet,
                    final_answer_authority_projection=authority,
                    sanitized_author_evidence_excerpt_candidates=(
                        dict(inputs or {}).get(
                            "sanitized_author_evidence_excerpt_candidates"
                        )
                    ),
                )
            )
            merged_inputs = {**dict(inputs or {}), **canonical_inputs}
            build_followup_author_evidence_content_bridge_record(
                action_inputs=merged_inputs,
                **self._followup_author_evidence_content_bridge_runtime_inputs(),
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGED
            ),
        )

    def authorize_followup_author_execution_from_ad(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        ad_state = self.state.followup_author_payload_construction_state
        if not ad_state:
            raise RunKernelTransitionError(
                "AE Author execution requires reduced AD payload envelope"
            )
        if (
            self.state.followup_author_execution_from_ad_state
            or self.state.followup_author_execution_from_ad_projection
            or self.state.followup_author_execution_from_ad_history
        ):
            raise RunKernelTransitionError("AE Author execution already observed")
        if (
            self.state.followup_author_evidence_content_bridge_state
            or self.state.followup_author_evidence_content_bridge_projection
            or self.state.followup_author_evidence_content_bridge_history
        ):
            raise RunKernelTransitionError(
                "AE Author execution requires AF4B2 bridge consumption in a later phase"
            )
        if (
            self.state.followup_author_invocation_construction_state
            or self.state.followup_author_invocation_construction_projection
            or self.state.followup_author_invocation_construction_history
        ):
            raise RunKernelTransitionError(
                "AE Author execution requires AF4 invocation construction absent"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "AE Author execution requires legacy fixture observation closed"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "AE Author execution requires no prior Author/final outcome"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "AE Author execution requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "AE Author execution rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "AE Author execution requires deferred payload status"
            )
        try:
            reject_followup_author_execution_from_ad_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        canonical_inputs = build_followup_author_execution_from_ad_action_inputs(
            followup_author_payload_construction_state=ad_state,
            followup_author_payload_construction_projection=(
                self.state.followup_author_payload_construction_projection
            ),
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_execution_from_ad_record(
                action_inputs=merged_inputs,
                **self._followup_author_execution_from_ad_runtime_inputs(),
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_OBSERVED
            ),
        )

    def authorize_followup_author_invocation_construction(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        ad_state = self.state.followup_author_payload_construction_state
        if not ad_state:
            raise RunKernelTransitionError(
                "AF4 Author invocation construction requires reduced AD payload envelope"
            )
        if (
            self.state.followup_author_invocation_construction_state
            or self.state.followup_author_invocation_construction_projection
            or self.state.followup_author_invocation_construction_history
        ):
            raise RunKernelTransitionError(
                "AF4 Author invocation construction already prepared"
            )
        if (
            self.state.followup_author_execution_from_ad_state
            or self.state.followup_author_execution_from_ad_projection
            or self.state.followup_author_execution_from_ad_history
        ):
            raise RunKernelTransitionError(
                "AF4 Author invocation construction requires no AE execution"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "AF4 Author invocation construction requires legacy fixture observation closed"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "AF4 Author invocation construction requires no Author/final outcome"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "AF4 Author invocation construction requires Analyst/Economist closed"
            )

        packet = self.state.final_answer_packet
        authority = self.state.final_answer_authority_projection
        author_payload_ref = _safe_mapping(packet.get("author_payload_ref"))
        if author_payload_ref.get("status") == "author_input_ready":
            raise RunKernelTransitionError(
                "AF4 Author invocation construction rejects executable payload status"
            )
        if author_payload_ref.get("status") != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
            raise RunKernelTransitionError(
                "AF4 Author invocation construction requires deferred payload status"
            )
        try:
            reject_followup_author_invocation_construction_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        runtime_inputs = self._followup_author_invocation_construction_runtime_inputs()
        canonical_inputs = build_followup_author_invocation_construction_action_inputs(
            followup_author_payload_construction_state=ad_state,
            followup_author_payload_construction_projection=(
                self.state.followup_author_payload_construction_projection
            ),
            final_answer_packet=packet,
            final_answer_authority_projection=authority,
            followup_author_evidence_content_bridge_state=(
                self.state.followup_author_evidence_content_bridge_state
            ),
            followup_author_evidence_content_bridge_projection=(
                self.state.followup_author_evidence_content_bridge_projection
            ),
            followup_author_evidence_content_bridge_history=(
                self.state.followup_author_evidence_content_bridge_history
            ),
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_invocation_construction_record(
                action_inputs=merged_inputs,
                **runtime_inputs,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED
            ),
        )

    def authorize_followup_author_model_request_assembly(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        invocation_state = self.state.followup_author_invocation_construction_state
        if not invocation_state:
            raise RunKernelTransitionError(
                "AF4D Author model request assembly requires constructed AF4C invocation"
            )
        if invocation_state.get("status") != FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS:
            raise RunKernelTransitionError("AF4D Author model request assembly requires successful AF4C invocation")
        if invocation_state.get("author_invocation_ready_for_model") is not True:
            raise RunKernelTransitionError("AF4D Author model request assembly requires AF4C model-ready invocation")
        if invocation_state.get("model_execution_allowed") is not False:
            raise RunKernelTransitionError("AF4D Author model request assembly requires model execution closed")
        if not self.state.followup_author_evidence_content_bridge_state:
            raise RunKernelTransitionError("AF4D Author model request assembly requires AF4B2 evidence content")
        if (
            self.state.followup_author_model_request_assembly_state
            or self.state.followup_author_model_request_assembly_projection
            or self.state.followup_author_model_request_assembly_history
        ):
            raise RunKernelTransitionError("AF4D Author model request assembly already prepared")
        if (
            self.state.followup_author_execution_from_ad_state
            or self.state.followup_author_execution_from_ad_projection
            or self.state.followup_author_execution_from_ad_history
        ):
            raise RunKernelTransitionError("AF4D Author model request assembly requires no AE execution")
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError("AF4D Author model request assembly requires legacy fixture observation closed")
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError("AF4D Author model request assembly requires no Author/final outcome")
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError("AF4D Author model request assembly requires Analyst/Economist closed")
        try:
            reject_followup_author_model_request_assembly_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        runtime_inputs = self._followup_author_model_request_assembly_runtime_inputs()
        canonical_inputs = build_followup_author_model_request_assembly_action_inputs(
            run_request=self.state.request,
            followup_author_invocation_construction_state=(
                self.state.followup_author_invocation_construction_state
            ),
            followup_author_invocation_construction_projection=(
                self.state.followup_author_invocation_construction_projection
            ),
            followup_author_invocation_construction_history=(
                self.state.followup_author_invocation_construction_history
            ),
            followup_author_evidence_content_bridge_state=(
                self.state.followup_author_evidence_content_bridge_state
            ),
            followup_author_evidence_content_bridge_projection=(
                self.state.followup_author_evidence_content_bridge_projection
            ),
            followup_author_evidence_content_bridge_history=(
                self.state.followup_author_evidence_content_bridge_history
            ),
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            build_followup_author_model_request_assembly_record(
                action_inputs=merged_inputs,
                **runtime_inputs,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED
            ),
        )

    def authorize_followup_author_execution_from_af4d(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        af4d_state = self.state.followup_author_model_request_assembly_state
        if not af4d_state:
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D requires canonical AF4D model request assembly"
            )
        if af4d_state.get("author_model_request_ready_for_execution") is not True:
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D requires execution-ready AF4D"
            )
        if af4d_state.get("model_execution_allowed") is not False:
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D requires live execution disabled"
            )
        if (
            self.state.followup_author_execution_from_af4d_state
            or self.state.followup_author_execution_from_af4d_projection
            or self.state.followup_author_execution_from_af4d_history
        ):
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D already completed"
            )
        if (
            self.state.followup_author_execution_from_ad_state
            or self.state.followup_author_execution_from_ad_projection
            or self.state.followup_author_execution_from_ad_history
        ):
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D rejects old AE execution"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D requires legacy fixture observation closed"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D requires no Author/final outcome"
            )
        if (
            getattr(self.state, "analyst_author_handoff_state", {})
            or getattr(self.state, "economist_handoff_state", {})
        ):
            raise RunKernelTransitionError(
                "AF5A Author execution from AF4D requires Analyst/Economist closed"
            )
        try:
            reject_followup_author_execution_from_af4d_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        runtime_inputs = self._followup_author_execution_from_af4d_runtime_inputs()
        canonical_inputs = build_followup_author_execution_from_af4d_action_inputs(
            followup_author_model_request_assembly_state=(
                self.state.followup_author_model_request_assembly_state
            ),
            followup_author_model_request_assembly_projection=(
                self.state.followup_author_model_request_assembly_projection
            ),
            followup_author_model_request_assembly_history=(
                self.state.followup_author_model_request_assembly_history
            ),
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            validate_followup_author_execution_from_af4d_authorization(
                action_inputs=merged_inputs,
                **runtime_inputs,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_OBSERVED
            ),
        )

    def authorize_followup_author_response_finalization(
        self,
        *,
        reason: str = FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        af5a_state = self.state.followup_author_execution_from_af4d_state
        if not af5a_state:
            raise RunKernelTransitionError(
                "AF5B Author response finalization requires canonical AF5A state"
            )
        if (
            self.state.followup_author_response_finalization_state
            or self.state.followup_author_response_finalization_projection
            or self.state.followup_author_response_finalization_history
        ):
            raise RunKernelTransitionError(
                "AF5B Author response finalization already completed"
            )
        if (
            self.state.followup_author_execution_from_ad_state
            or self.state.followup_author_execution_from_ad_projection
            or self.state.followup_author_execution_from_ad_history
        ):
            raise RunKernelTransitionError(
                "AF5B Author response finalization rejects old AE execution"
            )
        if self.state.followup_author_observation_state:
            raise RunKernelTransitionError(
                "AF5B Author response finalization requires legacy fixture observation closed"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "AF5B Author response finalization requires no prior Author/final outcome"
            )
        if not self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "AF5B Author response finalization requires FinalAnswerPacket"
            )
        if not self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "AF5B Author response finalization requires final-answer authority projection"
            )
        try:
            reject_followup_author_response_finalization_input_spoof(inputs)
        except PermissionError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        runtime_inputs = self._followup_author_response_finalization_runtime_inputs()
        canonical_inputs = (
            build_followup_author_response_finalization_action_inputs(
                followup_author_execution_from_af4d_state=(
                    self.state.followup_author_execution_from_af4d_state
                ),
                followup_author_execution_from_af4d_projection=(
                    self.state.followup_author_execution_from_af4d_projection
                ),
                followup_author_execution_from_af4d_history=(
                    self.state.followup_author_execution_from_af4d_history
                ),
                final_answer_packet=self.state.final_answer_packet,
                final_answer_authority_projection=(
                    self.state.final_answer_authority_projection
                ),
            )
        )
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        try:
            validate_followup_author_response_finalization_authorization(
                action_inputs=merged_inputs,
                **runtime_inputs,
            )
        except (PermissionError, ValueError) as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZED
            ),
        )

    def authorize_followup_author_observation(
        self,
        *,
        reason: str = "ag96i2h_followup_fixture_author_output_observation",
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.followup_author_gate_state:
            raise RunKernelTransitionError(
                "follow-up Author observation requires reduced Author gate state"
            )
        gate_state = self.state.followup_author_gate_state
        if gate_state.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical Author gate state"
            )
        if gate_state.get("author_gate_mode") != FOLLOWUP_AUTHOR_GATE_MODE:
            raise RunKernelTransitionError(
                "follow-up Author observation requires fixture-only Author gate"
            )
        if gate_state.get("packet_authority_consumed") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires consumed packet authority"
            )
        if gate_state.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author activation closed"
            )
        if gate_state.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires deferred Author execution"
            )
        if gate_state.get("final_text_included") is not False:
            raise RunKernelTransitionError(
                "follow-up Author observation requires no final text in gate state"
            )
        if not self.state.final_answer_packet:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical FinalAnswerPacket"
            )
        if not self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical packet authority"
            )
        authority = self.state.final_answer_authority_projection
        if authority.get("owner") != "RunKernel.FinalAnswerPacket":
            raise RunKernelTransitionError(
                "follow-up Author observation requires RunKernel packet authority"
            )
        if authority.get("canonical_state") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires canonical packet authority"
            )
        if authority.get("packet_id") != self.state.final_answer_packet.get(
            "packet_id"
        ):
            raise RunKernelTransitionError(
                "follow-up Author observation requires packet/projection match"
            )
        if authority.get("packet_id") != gate_state.get("packet_id"):
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author gate packet match"
            )
        payload_ref = _safe_mapping(authority.get("author_payload_ref"))
        if payload_ref.get("status") != "author_execution_deferred":
            raise RunKernelTransitionError(
                "follow-up Author observation requires deferred Author payload"
            )
        if authority.get("author_activation_allowed") is not False:
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author activation closed"
            )
        if authority.get("author_execution_deferred") is not True:
            raise RunKernelTransitionError(
                "follow-up Author observation requires Author execution deferred"
            )
        if self.state.author_observation or self.state.final_answer_outcome:
            raise RunKernelTransitionError(
                "follow-up Author observation requires product Author output closed"
            )
        if self.state.followup_author_observation_state.get(
            "author_gate_id"
        ) == gate_state.get("author_gate_id"):
            raise RunKernelTransitionError(
                "follow-up Author observation already reduced for this Author gate"
            )
        canonical_inputs = {
            "run_id": gate_state.get("run_id"),
            "checkpoint_id": gate_state.get("checkpoint_id"),
            "followup_authorization_consumption_id": gate_state.get(
                "followup_authorization_consumption_id"
            ),
            "sealed_candidate_id": gate_state.get("sealed_candidate_id"),
            "followup_execution_id": gate_state.get("followup_execution_id"),
            "execution_id": gate_state.get("execution_id"),
            "followup_evidence_intake_id": gate_state.get(
                "followup_evidence_intake_id"
            ),
            "intake_id": gate_state.get("intake_id"),
            "followup_sufficiency_recheck_id": gate_state.get(
                "followup_sufficiency_recheck_id"
            ),
            "recheck_id": gate_state.get("recheck_id"),
            "followup_final_answer_packet_id": gate_state.get(
                "followup_final_answer_packet_id"
            ),
            "packet_preparation_id": gate_state.get("packet_preparation_id"),
            "followup_author_gate_id": gate_state.get("author_gate_id"),
            "author_gate_id": gate_state.get("author_gate_id"),
            "packet_id": self.state.final_answer_packet.get("packet_id"),
            "provider_job_kind": gate_state.get("provider_job_kind"),
            "component_id": gate_state.get("component_id"),
            "source_obligation_id": gate_state.get("source_obligation_id"),
            "requirement_ids": gate_state.get("requirement_ids", []),
            "expected_source_classes": gate_state.get(
                "expected_source_classes",
                [],
            ),
            "fixture_execution_mode": gate_state.get("fixture_execution_mode"),
            "evidence_ledger_intake_mode": gate_state.get(
                "evidence_ledger_intake_mode"
            ),
            "sufficiency_recheck_mode": gate_state.get(
                "sufficiency_recheck_mode"
            ),
            "final_answer_packet_mode": gate_state.get(
                "final_answer_packet_mode"
            ),
            "author_gate_mode": gate_state.get("author_gate_mode"),
            "fixture_author_observation_mode": FOLLOWUP_AUTHOR_OBSERVATION_MODE,
            "final_answer_packet_digest": followup_projection_digest(
                self.state.final_answer_packet
            ),
            "final_answer_authority_projection_digest": followup_projection_digest(
                authority
            ),
            "followup_author_gate_digest": followup_projection_digest(gate_state),
            "provider_execution_licensed": False,
            "author_activation_allowed": False,
            "author_execution_deferred": True,
            "author_executor_invoked": False,
            "model_called": False,
            "author_prompt_changed": False,
            "author_prose_behavior_changed": False,
            "citation_rendering_changed": False,
            "citation_formatter_invoked": False,
            "product_answer_behavior_changed": False,
            "final_text_included": False,
            "live_validation_not_run": True,
            "expected_observation_record_type": (
                "followup_author_observation_consumption_record"
            ),
        }
        merged_inputs = {**dict(inputs or {}), **canonical_inputs}
        return self.authorize(
            stage=FOLLOWUP_AUTHOR_OBSERVATION_STAGE,
            action_type=ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.FOLLOWUP_AUTHOR_OBSERVATION_OBSERVED
            ),
        )

    def reduce(self, observation: Observation) -> RunState:
        action = self.state.issued_actions.get(observation.action_id)
        if action is None:
            raise RunKernelTransitionError(
                f"observation {observation.observation_id!r} has no matching issued action"
            )
        if observation.run_id != self.state.run_id or observation.run_id != action.run_id:
            raise RunKernelTransitionError("observation run_id does not match RunKernel/action")
        if observation.action_id != action.action_id:
            raise RunKernelTransitionError("observation action_id does not match authorized action")
        if observation.stage != action.stage:
            raise RunKernelTransitionError(
                f"observation stage {observation.stage!r} does not match action stage {action.stage!r}"
            )
        if observation.observation_type is not action.expected_observation_type:
            raise RunKernelTransitionError(
                "observation type "
                f"{observation.observation_type.value!r} does not match expected "
                f"{action.expected_observation_type.value!r}"
            )
        if observation.sequence != action.sequence:
            raise RunKernelTransitionError("observation sequence does not match action sequence")
        if action.action_id in self.state.reduced_action_ids:
            raise RunKernelTransitionError("authorized action was already reduced")
        if observation.sequence != self.state.next_observation_sequence:
            raise RunKernelTransitionError(
                "observation reduced out of order: "
                f"expected sequence {self.state.next_observation_sequence}, "
                f"got {observation.sequence}"
        )
        p1_observed_selection_state: dict[str, Any] = {}
        p1_canonical_record: Any | None = None
        q1_observed_citation_state: dict[str, Any] = {}
        q1_canonical_record: Any | None = None
        r1_observed_handoff_state: dict[str, Any] = {}
        r1_canonical_record: Any | None = None
        t1_observed_rendering_state: dict[str, Any] = {}
        t1_canonical_record: Any | None = None
        u1_observed_authority_state: dict[str, Any] = {}
        u1_canonical_record: Any | None = None
        u1_authority_state: dict[str, Any] = {}
        u1_authority_projection: dict[str, Any] = {}
        u1_packet_projection: dict[str, Any] = {}
        v1_canonical_gate_record: Any | None = None
        w_observed_readiness_state: dict[str, Any] = {}
        w_canonical_readiness_state: dict[str, Any] = {}
        w_readiness_flags: dict[str, Any] = {}
        x_observed_materialization_state: dict[str, Any] = {}
        x_canonical_materialization_state: dict[str, Any] = {}
        x_materialization_flags: dict[str, Any] = {}
        y_observed_activation_state: dict[str, Any] = {}
        y_canonical_activation_state: dict[str, Any] = {}
        y_activation_flags: dict[str, Any] = {}
        y_packet_projection: dict[str, Any] = {}
        y_authority_projection: dict[str, Any] = {}
        z_observed_manifest_state: dict[str, Any] = {}
        z_canonical_manifest_state: dict[str, Any] = {}
        z_packet_projection: dict[str, Any] = {}
        z_authority_projection: dict[str, Any] = {}
        z_manifest_projection: dict[str, Any] = {}
        ac_observed_payload_authority_state: dict[str, Any] = {}
        ac_canonical_payload_authority_state: dict[str, Any] = {}
        ac_packet_projection: dict[str, Any] = {}
        ac_authority_projection: dict[str, Any] = {}
        ac_payload_authority_projection: dict[str, Any] = {}
        ad_observed_payload_construction_state: dict[str, Any] = {}
        ad_canonical_payload_construction_state: dict[str, Any] = {}
        ad_packet_projection: dict[str, Any] = {}
        ad_authority_projection: dict[str, Any] = {}
        ad_payload_construction_projection: dict[str, Any] = {}
        af4b2_observed_bridge_state: dict[str, Any] = {}
        af4b2_canonical_bridge_state: dict[str, Any] = {}
        af4b2_packet_projection: dict[str, Any] = {}
        af4b2_authority_projection: dict[str, Any] = {}
        af4b2_bridge_projection: dict[str, Any] = {}
        ae_observed_execution_state: dict[str, Any] = {}
        ae_canonical_execution_state: dict[str, Any] = {}
        ae_packet_projection: dict[str, Any] = {}
        ae_authority_projection: dict[str, Any] = {}
        ae_execution_projection: dict[str, Any] = {}
        ae_author_observation: dict[str, Any] = {}
        ae_final_answer_outcome: dict[str, Any] = {}
        af4_observed_invocation_state: dict[str, Any] = {}
        af4_canonical_invocation_state: dict[str, Any] = {}
        af4_packet_projection: dict[str, Any] = {}
        af4_authority_projection: dict[str, Any] = {}
        af4_invocation_projection: dict[str, Any] = {}
        af4d_observed_model_request_state: dict[str, Any] = {}
        af4d_canonical_model_request_state: dict[str, Any] = {}
        af4d_model_request_projection: dict[str, Any] = {}
        af5a_observed_execution_state: dict[str, Any] = {}
        af5a_canonical_execution_state: dict[str, Any] = {}
        af5a_execution_projection: dict[str, Any] = {}
        af5b_observed_finalization_state: dict[str, Any] = {}
        af5b_canonical_finalization_state: dict[str, Any] = {}
        af5b_finalization_projection: dict[str, Any] = {}
        af5b_author_observation: dict[str, Any] = {}
        af5b_final_answer_outcome: dict[str, Any] = {}
        if self.state.followup_author_response_finalization_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE,
                ActionType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AF5B Author response finalization"
                )
            if action.action_type is ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AF5B Author response finalization cannot reduce"
                )
        if self.state.followup_author_execution_from_af4d_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE,
                ActionType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AF5A Author execution from AF4D"
                )
            if action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AF5A Author execution from AF4D cannot reduce"
                )
        if self.state.followup_author_model_request_assembly_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE,
                ActionType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AF4D Author model request assembly"
                )
            if (
                action.action_type
                is ActionType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AF4D Author model request assembly cannot reduce"
                )
        if self.state.followup_author_evidence_content_bridge_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AF4B2 Author evidence-content bridge"
                )
            if (
                action.action_type
                is ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AF4B2 Author evidence-content bridge cannot reduce"
                )
        if self.state.followup_author_invocation_construction_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AF4 Author invocation construction"
                )
            if (
                action.action_type
                is ActionType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AF4 Author invocation construction cannot reduce"
                )
        if self.state.followup_author_execution_from_ad_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION,
                ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AE Author execution from AD"
                )
            if action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AE Author execution from AD cannot reduce"
                )
        if self.state.followup_author_payload_construction_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AD Author payload construction"
                )
            if action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AD Author payload construction cannot reduce"
                )
        if self.state.followup_author_payload_authority_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3AC Author payload authority"
                )
            if action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3AC Author payload authority cannot reduce"
                )
        if self.state.followup_author_prompt_assembly_manifest_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3Z Author prompt assembly manifest"
                )
            if (
                action.action_type
                is ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3Z Author prompt assembly manifest cannot reduce"
                )
        if self.state.followup_author_execution_activation_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3Y Author execution activation"
                )
            if (
                action.action_type
                is ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3Y Author execution activation cannot reduce"
                )
        if self.state.followup_author_input_materialization_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
                ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS,
                ActionType.FOLLOWUP_AUTHOR_OBSERVATION,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3X Author input materialization"
                )
            if (
                action.action_type
                is ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3X Author input materialization cannot reduce"
                )
        if self.state.followup_author_execution_readiness_state:
            if action.action_type in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
                ActionType.FOLLOWUP_AUTHOR_GATE,
            }:
                raise RunKernelTransitionError(
                    "stale upstream follow-up action cannot reduce after "
                    "AG-96I3W Author execution readiness"
                )
            if (
                action.action_type
                is ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3W Author execution readiness cannot reduce"
                )
        if (
            self.state.followup_author_gate_state.get("author_gate_mode")
            == AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
            and action.action_type
            in {
                ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
                ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
                ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
                ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
                ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
                ActionType.FOLLOWUP_CITATION_RENDERING,
                ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY,
            }
        ):
            raise RunKernelTransitionError(
                "stale upstream follow-up action cannot reduce after AG-96I3V1 "
                "U1-bound Author gate"
            )
        if (
            self.state.followup_author_gate_state
            and action.action_type is ActionType.FOLLOWUP_AUTHOR_GATE
        ):
            if self.state.followup_author_gate_state.get("author_gate_mode") == (
                AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3V1 U1-bound Author gate cannot reduce"
                )
            raise RunKernelTransitionError(
                "duplicate follow-up Author gate cannot reduce"
            )
        if self.state.followup_author_input_authority_state and action.action_type in {
            ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE,
            ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL,
            ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION,
            ActionType.FOLLOWUP_CITATION_ELIGIBILITY,
            ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF,
            ActionType.FOLLOWUP_CITATION_RENDERING,
        }:
            raise RunKernelTransitionError(
                "stale upstream follow-up action cannot reduce after AG-96I3U1 "
                "author input authority"
            )
        if (
            self.state.followup_author_input_authority_state
            and action.action_type is ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY
        ):
            raise RunKernelTransitionError(
                "duplicate AG-96I3U1 author input authority cannot reduce"
            )
        if (
            action.action_type is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE
            and self.state.followup_citation_rendering_state
        ):
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot reduce "
                "after AG-96I3T1 citation rendering"
            )
        if (
            action.action_type is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE
            and self.state.followup_citation_source_handoff_state
        ):
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot reduce "
                "after AG-96I3R1 citation source handoff"
            )
        if (
            action.action_type is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE
            and self.state.followup_citation_eligibility_state
        ):
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot reduce "
                "after AG-96I3Q1 citation eligibility"
            )
        if (
            action.action_type is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE
            and self.state.followup_final_evidence_selection_state
        ):
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot reduce "
                "after AG-96I3P1 final evidence selection"
            )
        if (
            action.action_type is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE
            and self.state.followup_blocked_final_answer_packet_shell_state
        ):
            raise RunKernelTransitionError(
                "legacy follow-up FinalAnswerPacket preparation cannot reduce "
                "after AG-96I3O2 blocked packet shell activation"
            )
        if (
            action.action_type
            is ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL
            and self.state.followup_citation_rendering_state
        ):
            raise RunKernelTransitionError(
                "stale AG-96I3O2 blocked packet shell cannot reduce after "
                "AG-96I3T1 citation rendering"
            )
        if (
            action.action_type
            is ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL
            and self.state.followup_citation_source_handoff_state
        ):
            raise RunKernelTransitionError(
                "stale AG-96I3O2 blocked packet shell cannot reduce after "
                "AG-96I3R1 citation source handoff"
            )
        if (
            action.action_type
            is ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL
            and self.state.followup_citation_eligibility_state
        ):
            raise RunKernelTransitionError(
                "stale AG-96I3O2 blocked packet shell cannot reduce after "
                "AG-96I3Q1 citation eligibility"
            )
        if (
            action.action_type
            is ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL
            and self.state.followup_final_evidence_selection_state
        ):
            raise RunKernelTransitionError(
                "stale AG-96I3O2 blocked packet shell cannot reduce after "
                "AG-96I3P1 final evidence selection"
            )
        if action.action_type is ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION:
            if self.state.followup_citation_rendering_state:
                raise RunKernelTransitionError(
                    "stale AG-96I3P1 final evidence selection cannot reduce "
                    "after AG-96I3T1 citation rendering"
                )
            if self.state.followup_citation_source_handoff_state:
                raise RunKernelTransitionError(
                    "stale AG-96I3P1 final evidence selection cannot reduce "
                    "after AG-96I3R1 citation source handoff"
                )
            if self.state.followup_citation_eligibility_state:
                raise RunKernelTransitionError(
                    "stale AG-96I3P1 final evidence selection cannot reduce "
                    "after AG-96I3Q1 citation eligibility"
                )
            if self.state.followup_final_evidence_selection_state:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3P1 final evidence selection cannot reduce"
                )
            if self.state.final_answer_packet.get("final_evidence_selected") is True:
                raise RunKernelTransitionError(
                    "AG-96I3P1 final evidence selection cannot overwrite a "
                    "selected packet"
                )
            p1_observed_selection_state = _safe_mapping(
                observation.payload.get("followup_final_evidence_selection_state")
            )
            if not p1_observed_selection_state:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection observation requires "
                    "followup_final_evidence_selection_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_final_evidence_selection_observation_binding,
                action_inputs=action_inputs,
                observed_selection_state=p1_observed_selection_state,
            )
            try:
                p1_canonical_record = build_followup_final_evidence_selection_record(
                    action_inputs=action_inputs,
                    followup_blocked_final_answer_packet_shell_state=(
                        self.state.followup_blocked_final_answer_packet_shell_state
                    ),
                    final_answer_packet=self.state.final_answer_packet,
                    followup_final_answer_packet_readiness_state=(
                        self.state.followup_final_answer_packet_readiness_state
                    ),
                    followup_sufficiency_recheck_state=(
                        self.state.followup_sufficiency_recheck_state
                    ),
                    sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
        if action.action_type is ActionType.FOLLOWUP_CITATION_ELIGIBILITY:
            if self.state.followup_citation_rendering_state:
                raise RunKernelTransitionError(
                    "stale AG-96I3Q1 citation eligibility cannot reduce after "
                    "AG-96I3T1 citation rendering"
                )
            if self.state.followup_citation_source_handoff_state:
                raise RunKernelTransitionError(
                    "stale AG-96I3Q1 citation eligibility cannot reduce after "
                    "AG-96I3R1 citation source handoff"
                )
            if self.state.followup_citation_eligibility_state:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3Q1 citation eligibility cannot reduce"
                )
            if self.state.final_answer_packet.get(
                "citation_eligibility_deferred"
            ) is not True:
                raise RunKernelTransitionError(
                    "AG-96I3Q1 citation eligibility cannot overwrite a "
                    "citation-eligible packet"
                )
            q1_observed_citation_state = _safe_mapping(
                observation.payload.get("followup_citation_eligibility_state")
            )
            if not q1_observed_citation_state:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility observation requires "
                    "followup_citation_eligibility_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_citation_eligibility_observation_binding,
                action_inputs=action_inputs,
                observed_citation_state=q1_observed_citation_state,
            )
            try:
                q1_canonical_record = build_followup_citation_eligibility_record(
                    action_inputs=action_inputs,
                    followup_final_evidence_selection_state=(
                        self.state.followup_final_evidence_selection_state
                    ),
                    final_answer_packet=self.state.final_answer_packet,
                    followup_blocked_final_answer_packet_shell_state=(
                        self.state.followup_blocked_final_answer_packet_shell_state
                    ),
                    followup_final_answer_packet_readiness_state=(
                        self.state.followup_final_answer_packet_readiness_state
                    ),
                    followup_sufficiency_recheck_state=(
                        self.state.followup_sufficiency_recheck_state
                    ),
                    sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
        if action.action_type is ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF:
            if self.state.followup_citation_rendering_state:
                raise RunKernelTransitionError(
                    "stale AG-96I3R1 citation source handoff cannot reduce after "
                    "AG-96I3T1 citation rendering"
                )
            if self.state.followup_citation_source_handoff_state:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3R1 citation source handoff cannot reduce"
                )
            r1_observed_handoff_state = _safe_mapping(
                observation.payload.get("followup_citation_source_handoff_state")
            )
            if not r1_observed_handoff_state:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff observation requires "
                    "followup_citation_source_handoff_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_citation_source_handoff_observation_binding,
                action_inputs=action_inputs,
                observed_handoff_state=r1_observed_handoff_state,
            )
            try:
                r1_canonical_record = build_followup_citation_source_handoff_record(
                    action_inputs=action_inputs,
                    followup_citation_eligibility_state=(
                        self.state.followup_citation_eligibility_state
                    ),
                    followup_citation_eligibility_projection=(
                        self.state.followup_citation_eligibility_projection
                    ),
                    followup_citation_eligibility_history=(
                        self.state.followup_citation_eligibility_history
                    ),
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    followup_final_evidence_selection_state=(
                        self.state.followup_final_evidence_selection_state
                    ),
                    followup_final_evidence_selection_projection=(
                        self.state.followup_final_evidence_selection_projection
                    ),
                    followup_final_evidence_selection_history=(
                        self.state.followup_final_evidence_selection_history
                    ),
                    followup_blocked_final_answer_packet_shell_state=(
                        self.state.followup_blocked_final_answer_packet_shell_state
                    ),
                    followup_blocked_final_answer_packet_shell_projection=(
                        self.state.followup_blocked_final_answer_packet_shell_projection
                    ),
                    followup_blocked_final_answer_packet_shell_history=(
                        self.state.followup_blocked_final_answer_packet_shell_history
                    ),
                    followup_final_answer_packet_readiness_state=(
                        self.state.followup_final_answer_packet_readiness_state
                    ),
                    followup_final_answer_packet_readiness_projection=(
                        self.state.followup_final_answer_packet_readiness_projection
                    ),
                    followup_final_answer_packet_readiness_history=(
                        self.state.followup_final_answer_packet_readiness_history
                    ),
                    followup_sufficiency_recheck_state=(
                        self.state.followup_sufficiency_recheck_state
                    ),
                    sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
        if action.action_type is ActionType.FOLLOWUP_CITATION_RENDERING:
            if self.state.followup_citation_rendering_state:
                raise RunKernelTransitionError(
                    "duplicate AG-96I3T1 citation rendering cannot reduce"
                )
            t1_observed_rendering_state = _safe_mapping(
                observation.payload.get("followup_citation_rendering_state")
            )
            if not t1_observed_rendering_state:
                raise RunKernelTransitionError(
                    "follow-up citation rendering observation requires "
                    "followup_citation_rendering_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_citation_rendering_observation_binding,
                action_inputs=action_inputs,
                observed_rendering_state=t1_observed_rendering_state,
            )
            try:
                t1_canonical_record = build_followup_citation_rendering_record(
                    action_inputs=action_inputs,
                    followup_citation_source_handoff_state=(
                        self.state.followup_citation_source_handoff_state
                    ),
                    followup_citation_source_handoff_projection=(
                        self.state.followup_citation_source_handoff_projection
                    ),
                    followup_citation_source_handoff_history=(
                        self.state.followup_citation_source_handoff_history
                    ),
                    followup_citation_eligibility_state=(
                        self.state.followup_citation_eligibility_state
                    ),
                    followup_citation_eligibility_projection=(
                        self.state.followup_citation_eligibility_projection
                    ),
                    followup_citation_eligibility_history=(
                        self.state.followup_citation_eligibility_history
                    ),
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    followup_final_evidence_selection_state=(
                        self.state.followup_final_evidence_selection_state
                    ),
                    followup_final_evidence_selection_projection=(
                        self.state.followup_final_evidence_selection_projection
                    ),
                    followup_final_evidence_selection_history=(
                        self.state.followup_final_evidence_selection_history
                    ),
                    followup_blocked_final_answer_packet_shell_state=(
                        self.state.followup_blocked_final_answer_packet_shell_state
                    ),
                    followup_blocked_final_answer_packet_shell_projection=(
                        self.state.followup_blocked_final_answer_packet_shell_projection
                    ),
                    followup_blocked_final_answer_packet_shell_history=(
                        self.state.followup_blocked_final_answer_packet_shell_history
                    ),
                    followup_final_answer_packet_readiness_state=(
                        self.state.followup_final_answer_packet_readiness_state
                    ),
                    followup_final_answer_packet_readiness_projection=(
                        self.state.followup_final_answer_packet_readiness_projection
                    ),
                    followup_final_answer_packet_readiness_history=(
                        self.state.followup_final_answer_packet_readiness_history
                    ),
                    followup_sufficiency_recheck_state=(
                        self.state.followup_sufficiency_recheck_state
                    ),
                    sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
        if action.action_type is ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY:
            if (
                self.state.followup_author_input_authority_state
                or self.state.followup_author_input_authority_projection
                or self.state.followup_author_input_authority_history
            ):
                raise RunKernelTransitionError(
                    "duplicate AG-96I3U1 author input authority cannot reduce"
                )
            u1_observed_authority_state = _safe_mapping(
                observation.payload.get("followup_author_input_authority_state")
            )
            if not u1_observed_authority_state:
                raise RunKernelTransitionError(
                    "follow-up author input authority observation requires "
                    "followup_author_input_authority_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_input_authority_observation_binding(
                    action_inputs=action_inputs,
                    observed_author_input_authority_state=(
                        u1_observed_authority_state
                    ),
                )
                u1_canonical_record = build_followup_author_input_authority_record(
                    action_inputs=action_inputs,
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                    followup_sufficiency_recheck_state=(
                        self.state.followup_sufficiency_recheck_state
                    ),
                    followup_final_answer_packet_readiness_state=(
                        self.state.followup_final_answer_packet_readiness_state
                    ),
                    followup_final_answer_packet_readiness_projection=(
                        self.state.followup_final_answer_packet_readiness_projection
                    ),
                    followup_final_answer_packet_readiness_history=(
                        self.state.followup_final_answer_packet_readiness_history
                    ),
                    followup_blocked_final_answer_packet_shell_state=(
                        self.state.followup_blocked_final_answer_packet_shell_state
                    ),
                    followup_blocked_final_answer_packet_shell_projection=(
                        self.state.followup_blocked_final_answer_packet_shell_projection
                    ),
                    followup_blocked_final_answer_packet_shell_history=(
                        self.state.followup_blocked_final_answer_packet_shell_history
                    ),
                    followup_final_evidence_selection_state=(
                        self.state.followup_final_evidence_selection_state
                    ),
                    followup_final_evidence_selection_projection=(
                        self.state.followup_final_evidence_selection_projection
                    ),
                    followup_final_evidence_selection_history=(
                        self.state.followup_final_evidence_selection_history
                    ),
                    followup_citation_eligibility_state=(
                        self.state.followup_citation_eligibility_state
                    ),
                    followup_citation_eligibility_projection=(
                        self.state.followup_citation_eligibility_projection
                    ),
                    followup_citation_eligibility_history=(
                        self.state.followup_citation_eligibility_history
                    ),
                    followup_citation_source_handoff_state=(
                        self.state.followup_citation_source_handoff_state
                    ),
                    followup_citation_source_handoff_projection=(
                        self.state.followup_citation_source_handoff_projection
                    ),
                    followup_citation_source_handoff_history=(
                        self.state.followup_citation_source_handoff_history
                    ),
                    followup_citation_rendering_state=(
                        self.state.followup_citation_rendering_state
                    ),
                    followup_citation_rendering_projection=(
                        self.state.followup_citation_rendering_projection
                    ),
                    followup_citation_rendering_history=(
                        self.state.followup_citation_rendering_history
                    ),
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                )
                u1_packet_projection = u1_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=u1_canonical_record.to_dict(),
                )
                u1_authority_state = {
                    **u1_canonical_record.to_dict(),
                    "owner": "RunKernel.FollowupAuthorInputAuthority",
                    "canonical_state": True,
                    "trace_only": False,
                    "storage_only": False,
                    "observation_id": u1_observed_authority_state.get(
                        "observation_id"
                    ),
                }
                u1_authority_projection = _safe_mapping(
                    u1_authority_state.get("final_answer_authority_projection")
                )
                if not u1_authority_projection:
                    raise PermissionError(
                        "U1 requires canonical final answer authority projection"
                    )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_GATE:
            action_inputs = _safe_mapping(action.inputs)
            if action_inputs.get("author_gate_mode") == (
                AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
            ):
                observed_gate_state = _safe_mapping(
                    observation.payload.get("followup_author_gate_state")
                )
                if not observed_gate_state:
                    raise RunKernelTransitionError(
                        "V1 Author gate observation requires "
                        "followup_author_gate_state"
                    )
                try:
                    validate_followup_u1_bound_author_gate_observation_binding(
                        action_inputs=action_inputs,
                        observed_gate_state=observed_gate_state,
                    )
                    v1_canonical_gate_record = (
                        build_followup_u1_bound_author_gate_record(
                            action_inputs=action_inputs,
                            followup_author_input_authority_state=(
                                self.state.followup_author_input_authority_state
                            ),
                            followup_author_input_authority_projection=(
                                self.state.followup_author_input_authority_projection
                            ),
                            followup_author_input_authority_history=(
                                self.state.followup_author_input_authority_history
                            ),
                            final_answer_packet=self.state.final_answer_packet,
                            final_answer_authority_projection=(
                                self.state.final_answer_authority_projection
                            ),
                        )
                    )
                except (PermissionError, ValueError) as exc:
                    raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS:
            w_observed_readiness_state = _safe_mapping(
                observation.payload.get("followup_author_execution_readiness_state")
            )
            if not w_observed_readiness_state:
                raise RunKernelTransitionError(
                    "W Author execution readiness observation requires "
                    "followup_author_execution_readiness_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_execution_readiness_observation_binding(
                    action_inputs=action_inputs,
                    observed_readiness_state=w_observed_readiness_state,
                )
                w_canonical_readiness_record = (
                    build_followup_author_execution_readiness_record(
                        action_inputs=action_inputs,
                        followup_author_gate_state=(
                            self.state.followup_author_gate_state
                        ),
                        followup_author_gate_projection=(
                            self.state.followup_author_gate_projection
                        ),
                        followup_author_gate_history=(
                            self.state.followup_author_gate_history
                        ),
                        followup_author_input_authority_state=(
                            self.state.followup_author_input_authority_state
                        ),
                        followup_author_input_authority_projection=(
                            self.state.followup_author_input_authority_projection
                        ),
                        followup_author_input_authority_history=(
                            self.state.followup_author_input_authority_history
                        ),
                        final_answer_packet=self.state.final_answer_packet,
                        final_answer_authority_projection=(
                            self.state.final_answer_authority_projection
                        ),
                    )
                )
                w_canonical_readiness_state = {
                    **w_canonical_readiness_record.to_dict(),
                    "owner": "RunKernel.FollowupAuthorExecutionReadiness",
                    "canonical_state": True,
                    "trace_only": False,
                    "storage_only": False,
                    "observation_id": w_observed_readiness_state.get(
                        "observation_id"
                    ),
                }
                w_readiness_flags = _safe_mapping(
                    w_canonical_readiness_state.get("behavior_boundary_flags")
                )
                _followup_checked(
                    require_followup_flags_false,
                    w_readiness_flags,
                    _FOLLOWUP_AUTHOR_EXECUTION_READINESS_FALSE_FLAGS,
                    context="W Author execution readiness",
                )
                if w_canonical_readiness_state.get("status") != (
                    FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS
                ):
                    raise PermissionError(
                        "W Author execution readiness status mismatch"
                    )
                for field in (
                    "v1_author_gate_consumed",
                    "u1_authority_consumed",
                    "packet_authority_consumed",
                    "author_execution_readiness_recorded",
                    "author_execution_deferred",
                    "live_validation_not_run",
                    "not_for_product_answer_activation",
                ):
                    if w_canonical_readiness_state.get(field) is not True:
                        raise PermissionError(
                            "W Author execution readiness requires "
                            f"{field}=True"
                        )
                for field in (
                    "author_execution_allowed",
                    "author_activation_allowed",
                    "author_payload_status_changed",
                    "prompt_text_included",
                    "final_text_included",
                    "product_answer_ready",
                    "model_called",
                    "author_executor_invoked",
                    "provider_execution_licensed",
                ):
                    if w_canonical_readiness_state.get(field) is not False:
                        raise PermissionError(
                            "W Author execution readiness requires "
                            f"{field}=False"
                        )
                if w_canonical_readiness_state.get("author_payload_ref_status") != (
                    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
                ):
                    raise PermissionError(
                        "W Author execution readiness requires deferred payload status"
                    )
                if w_canonical_readiness_state.get("author_payload_ref_status") == (
                    "author_input_ready"
                ):
                    raise PermissionError(
                        "W Author execution readiness must not make payload executable"
                    )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION:
            x_observed_materialization_state = _safe_mapping(
                observation.payload.get("followup_author_input_materialization_state")
            )
            if not x_observed_materialization_state:
                raise RunKernelTransitionError(
                    "X Author input materialization observation requires "
                    "followup_author_input_materialization_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_input_materialization_observation_binding(
                    action_inputs=action_inputs,
                    observed_materialization_state=(
                        x_observed_materialization_state
                    ),
                )
                x_canonical_materialization_record = (
                    build_followup_author_input_materialization_record(
                        action_inputs=action_inputs,
                        followup_author_execution_readiness_state=(
                            self.state.followup_author_execution_readiness_state
                        ),
                        followup_author_execution_readiness_projection=(
                            self.state.followup_author_execution_readiness_projection
                        ),
                        followup_author_execution_readiness_history=(
                            self.state.followup_author_execution_readiness_history
                        ),
                        followup_author_gate_state=(
                            self.state.followup_author_gate_state
                        ),
                        followup_author_gate_projection=(
                            self.state.followup_author_gate_projection
                        ),
                        followup_author_gate_history=(
                            self.state.followup_author_gate_history
                        ),
                        followup_author_input_authority_state=(
                            self.state.followup_author_input_authority_state
                        ),
                        followup_author_input_authority_projection=(
                            self.state.followup_author_input_authority_projection
                        ),
                        followup_author_input_authority_history=(
                            self.state.followup_author_input_authority_history
                        ),
                        final_answer_packet=self.state.final_answer_packet,
                        final_answer_authority_projection=(
                            self.state.final_answer_authority_projection
                        ),
                    )
                )
                x_canonical_materialization_state = {
                    **x_canonical_materialization_record.to_dict(),
                    "owner": "RunKernel.FollowupAuthorInputMaterialization",
                    "canonical_state": True,
                    "trace_only": False,
                    "storage_only": False,
                    "observation_id": x_observed_materialization_state.get(
                        "observation_id"
                    ),
                }
                x_materialization_flags = _safe_mapping(
                    x_canonical_materialization_state.get(
                        "behavior_boundary_flags"
                    )
                )
                _followup_checked(
                    require_followup_flags_false,
                    x_materialization_flags,
                    _FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_FALSE_FLAGS,
                    context="X Author input materialization",
                )
                if x_canonical_materialization_state.get("status") != (
                    FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STATUS
                ):
                    raise PermissionError(
                        "X Author input materialization status mismatch"
                    )
                if x_canonical_materialization_state.get(
                    "author_input_materialization_mode"
                ) != AG96I3X_AUTHOR_INPUT_MATERIALIZATION_MODE:
                    raise PermissionError(
                        "X Author input materialization mode mismatch"
                    )
                for field in (
                    "w_author_execution_readiness_consumed",
                    "v1_author_gate_consumed",
                    "u1_authority_consumed",
                    "packet_authority_consumed",
                    "author_input_materialized",
                    "author_execution_deferred",
                    "live_validation_not_run",
                    "not_for_product_answer_activation",
                ):
                    if x_canonical_materialization_state.get(field) is not True:
                        raise PermissionError(
                            "X Author input materialization requires "
                            f"{field}=True"
                        )
                for field in (
                    "author_input_ready",
                    "author_execution_allowed",
                    "author_activation_allowed",
                    "author_payload_status_changed",
                    "prompt_text_retained",
                    "prompt_text_included",
                    "final_text_included",
                    "product_answer_ready",
                    "model_called",
                    "author_executor_invoked",
                    "provider_execution_licensed",
                    "author_observation_created",
                    "final_answer_outcome_created",
                    "analyst_handoff_created",
                    "economist_handoff_created",
                ):
                    if x_canonical_materialization_state.get(field) is not False:
                        raise PermissionError(
                            "X Author input materialization requires "
                            f"{field}=False"
                        )
                if x_canonical_materialization_state.get(
                    "author_payload_ref_status"
                ) != FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS:
                    raise PermissionError(
                        "X Author input materialization requires deferred payload"
                    )
                if x_canonical_materialization_state.get(
                    "author_payload_ref_status"
                ) == "author_input_ready":
                    raise PermissionError(
                        "X Author input materialization must not make payload executable"
                    )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION:
            y_observed_activation_state = _safe_mapping(
                observation.payload.get("followup_author_execution_activation_state")
            )
            if not y_observed_activation_state:
                raise RunKernelTransitionError(
                    "Y Author execution activation observation requires "
                    "followup_author_execution_activation_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_execution_activation_observation_binding(
                    action_inputs=action_inputs,
                    observed_activation_state=y_observed_activation_state,
                )
                y_canonical_activation_record = (
                    build_followup_author_execution_activation_record(
                        action_inputs=action_inputs,
                        followup_author_input_materialization_state=(
                            self.state.followup_author_input_materialization_state
                        ),
                        followup_author_input_materialization_projection=(
                            self.state.followup_author_input_materialization_projection
                        ),
                        followup_author_input_materialization_history=(
                            self.state.followup_author_input_materialization_history
                        ),
                        followup_author_execution_readiness_state=(
                            self.state.followup_author_execution_readiness_state
                        ),
                        followup_author_execution_readiness_projection=(
                            self.state.followup_author_execution_readiness_projection
                        ),
                        followup_author_execution_readiness_history=(
                            self.state.followup_author_execution_readiness_history
                        ),
                        followup_author_gate_state=(
                            self.state.followup_author_gate_state
                        ),
                        followup_author_gate_projection=(
                            self.state.followup_author_gate_projection
                        ),
                        followup_author_gate_history=(
                            self.state.followup_author_gate_history
                        ),
                        followup_author_input_authority_state=(
                            self.state.followup_author_input_authority_state
                        ),
                        followup_author_input_authority_projection=(
                            self.state.followup_author_input_authority_projection
                        ),
                        followup_author_input_authority_history=(
                            self.state.followup_author_input_authority_history
                        ),
                        final_answer_packet=self.state.final_answer_packet,
                        final_answer_authority_projection=(
                            self.state.final_answer_authority_projection
                        ),
                    )
                )
                y_canonical_activation_state = (
                    build_run_kernel_followup_author_execution_activation_state(
                        activation_record_state=(
                            y_canonical_activation_record.to_dict()
                        ),
                        observation_id=y_observed_activation_state.get(
                            "observation_id"
                        ),
                    )
                )
                y_activation_flags = _safe_mapping(
                    y_canonical_activation_state.get("behavior_boundary_flags")
                )
                y_packet_projection = y_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=y_canonical_activation_state,
                )
                y_authority_projection = y_authority_projection_from_record(
                    current_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    record_state=y_canonical_activation_state,
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if (
            action.action_type
            is ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST
        ):
            z_observed_manifest_state = _safe_mapping(
                observation.payload.get(
                    "followup_author_prompt_assembly_manifest_state"
                )
            )
            if not z_observed_manifest_state:
                raise RunKernelTransitionError(
                    "Z Author prompt assembly manifest observation requires "
                    "followup_author_prompt_assembly_manifest_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_prompt_assembly_manifest_observation_binding(
                    action_inputs=action_inputs,
                    observed_manifest_state=z_observed_manifest_state,
                )
                z_canonical_manifest_record = (
                    build_followup_author_prompt_assembly_manifest_record(
                        action_inputs=action_inputs,
                        followup_author_execution_activation_state=(
                            self.state.followup_author_execution_activation_state
                        ),
                        followup_author_execution_activation_projection=(
                            self.state.followup_author_execution_activation_projection
                        ),
                        followup_author_execution_activation_history=(
                            self.state.followup_author_execution_activation_history
                        ),
                        followup_author_input_materialization_state=(
                            self.state.followup_author_input_materialization_state
                        ),
                        followup_author_input_materialization_projection=(
                            self.state.followup_author_input_materialization_projection
                        ),
                        followup_author_input_materialization_history=(
                            self.state.followup_author_input_materialization_history
                        ),
                        followup_author_execution_readiness_state=(
                            self.state.followup_author_execution_readiness_state
                        ),
                        followup_author_execution_readiness_projection=(
                            self.state.followup_author_execution_readiness_projection
                        ),
                        followup_author_execution_readiness_history=(
                            self.state.followup_author_execution_readiness_history
                        ),
                        followup_author_gate_state=(
                            self.state.followup_author_gate_state
                        ),
                        followup_author_gate_projection=(
                            self.state.followup_author_gate_projection
                        ),
                        followup_author_gate_history=(
                            self.state.followup_author_gate_history
                        ),
                        followup_author_input_authority_state=(
                            self.state.followup_author_input_authority_state
                        ),
                        followup_author_input_authority_projection=(
                            self.state.followup_author_input_authority_projection
                        ),
                        followup_author_input_authority_history=(
                            self.state.followup_author_input_authority_history
                        ),
                        final_answer_packet=self.state.final_answer_packet,
                        final_answer_authority_projection=(
                            self.state.final_answer_authority_projection
                        ),
                    )
                )
                z_canonical_manifest_state = (
                    build_run_kernel_followup_author_prompt_assembly_manifest_state(
                        manifest_record_state=(
                            z_canonical_manifest_record.to_dict()
                        ),
                        observation_id=z_observed_manifest_state.get(
                            "observation_id"
                        ),
                    )
                )
                z_packet_projection = z_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=z_canonical_manifest_state,
                )
                z_authority_projection = z_authority_projection_from_record(
                    current_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    record_state=z_canonical_manifest_state,
                )
                z_manifest_projection = (
                    build_followup_author_prompt_assembly_manifest_projection(
                        manifest_state=z_canonical_manifest_state,
                        behavior_boundary_flags=_safe_mapping(
                            z_canonical_manifest_state.get(
                                "behavior_boundary_flags"
                            )
                        ),
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_execution_activation_stage=(
                            FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE
                        ),
                        followup_author_input_materialization_stage=(
                            FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE
                        ),
                        followup_author_execution_readiness_stage=(
                            FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE
                        ),
                        followup_author_gate_stage=FOLLOWUP_AUTHOR_GATE_STAGE,
                        followup_author_input_authority_stage=(
                            FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY:
            ac_observed_payload_authority_state = _safe_mapping(
                observation.payload.get("followup_author_payload_authority_state")
            )
            if not ac_observed_payload_authority_state:
                raise RunKernelTransitionError(
                    "AC Author payload authority observation requires "
                    "followup_author_payload_authority_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_payload_authority_observation_binding(
                    action_inputs=action_inputs,
                    observed_payload_authority_state=(
                        ac_observed_payload_authority_state
                    ),
                )
                ac_canonical_payload_authority_record = (
                    build_followup_author_payload_authority_record(
                        action_inputs=action_inputs,
                        followup_author_prompt_assembly_manifest_state=(
                            self.state.followup_author_prompt_assembly_manifest_state
                        ),
                        followup_author_prompt_assembly_manifest_projection=(
                            self.state.followup_author_prompt_assembly_manifest_projection
                        ),
                        followup_author_prompt_assembly_manifest_history=(
                            self.state.followup_author_prompt_assembly_manifest_history
                        ),
                        followup_author_execution_activation_state=(
                            self.state.followup_author_execution_activation_state
                        ),
                        followup_author_input_materialization_state=(
                            self.state.followup_author_input_materialization_state
                        ),
                        followup_author_execution_readiness_state=(
                            self.state.followup_author_execution_readiness_state
                        ),
                        followup_author_gate_state=(
                            self.state.followup_author_gate_state
                        ),
                        followup_author_input_authority_state=(
                            self.state.followup_author_input_authority_state
                        ),
                        final_answer_packet=self.state.final_answer_packet,
                        final_answer_authority_projection=(
                            self.state.final_answer_authority_projection
                        ),
                    )
                )
                ac_canonical_payload_authority_state = (
                    build_run_kernel_followup_author_payload_authority_state(
                        payload_authority_record_state=(
                            ac_canonical_payload_authority_record.to_dict()
                        ),
                        observation_id=ac_observed_payload_authority_state.get(
                            "observation_id"
                        ),
                    )
                )
                ac_packet_projection = ac_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=ac_canonical_payload_authority_state,
                )
                ac_authority_projection = ac_authority_projection_from_record(
                    current_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    record_state=ac_canonical_payload_authority_state,
                )
                ac_payload_authority_projection = (
                    build_followup_author_payload_authority_projection(
                        payload_authority_state=(
                            ac_canonical_payload_authority_state
                        ),
                        behavior_boundary_flags=_safe_mapping(
                            ac_canonical_payload_authority_state.get(
                                "behavior_boundary_flags"
                            )
                        ),
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_prompt_assembly_manifest_stage=(
                            FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION:
            ad_observed_payload_construction_state = _safe_mapping(
                observation.payload.get("followup_author_payload_construction_state")
            )
            if not ad_observed_payload_construction_state:
                raise RunKernelTransitionError(
                    "AD Author payload construction observation requires "
                    "followup_author_payload_construction_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_payload_construction_observation_binding(
                    action_inputs=action_inputs,
                    observed_payload_construction_state=(
                        ad_observed_payload_construction_state
                    ),
                )
                ad_canonical_payload_construction_record = (
                    build_followup_author_payload_construction_record(
                        action_inputs=action_inputs,
                        followup_author_payload_authority_state=(
                            self.state.followup_author_payload_authority_state
                        ),
                        followup_author_payload_authority_projection=(
                            self.state.followup_author_payload_authority_projection
                        ),
                        followup_author_payload_authority_history=(
                            self.state.followup_author_payload_authority_history
                        ),
                        followup_author_prompt_assembly_manifest_state=(
                            self.state.followup_author_prompt_assembly_manifest_state
                        ),
                        followup_author_execution_activation_state=(
                            self.state.followup_author_execution_activation_state
                        ),
                        followup_author_input_materialization_state=(
                            self.state.followup_author_input_materialization_state
                        ),
                        followup_author_execution_readiness_state=(
                            self.state.followup_author_execution_readiness_state
                        ),
                        followup_author_gate_state=(
                            self.state.followup_author_gate_state
                        ),
                        followup_author_input_authority_state=(
                            self.state.followup_author_input_authority_state
                        ),
                        final_answer_packet=self.state.final_answer_packet,
                        final_answer_authority_projection=(
                            self.state.final_answer_authority_projection
                        ),
                    )
                )
                ad_canonical_payload_construction_state = (
                    build_run_kernel_followup_author_payload_construction_state(
                        payload_construction_record_state=(
                            ad_canonical_payload_construction_record.to_dict()
                        ),
                        observation_id=(
                            ad_observed_payload_construction_state.get(
                                "observation_id"
                            )
                        ),
                    )
                )
                ad_packet_projection = ad_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=ad_canonical_payload_construction_state,
                )
                ad_authority_projection = ad_authority_projection_from_record(
                    current_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    record_state=ad_canonical_payload_construction_state,
                )
                ad_payload_construction_projection = (
                    build_followup_author_payload_construction_projection(
                        payload_construction_state=(
                            ad_canonical_payload_construction_state
                        ),
                        behavior_boundary_flags=_safe_mapping(
                            ad_canonical_payload_construction_state.get(
                                "behavior_boundary_flags"
                            )
                        ),
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_payload_authority_stage=(
                            FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE:
            af4b2_observed_bridge_state = _safe_mapping(
                observation.payload.get("followup_author_evidence_content_bridge_state")
            )
            if not af4b2_observed_bridge_state:
                raise RunKernelTransitionError(
                    "AF4B2 Author evidence-content bridge observation requires "
                    "followup_author_evidence_content_bridge_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_evidence_content_bridge_observation_binding(
                    action_inputs=action_inputs,
                    observed_bridge_state=af4b2_observed_bridge_state,
                )
                af4b2_canonical_bridge_record = (
                    build_followup_author_evidence_content_bridge_record(
                        action_inputs=action_inputs,
                        **self._followup_author_evidence_content_bridge_runtime_inputs(),
                    )
                )
                af4b2_canonical_bridge_state = (
                    build_run_kernel_followup_author_evidence_content_bridge_state(
                        bridge_record_state=af4b2_canonical_bridge_record.to_dict(),
                        observation_id=af4b2_observed_bridge_state.get(
                            "observation_id"
                        ),
                    )
                )
                af4b2_packet_projection = af4b2_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=af4b2_canonical_bridge_state,
                )
                af4b2_authority_projection = (
                    af4b2_authority_projection_from_record(
                        current_projection=(
                            self.state.final_answer_authority_projection
                        ),
                        record_state=af4b2_canonical_bridge_state,
                    )
                )
                af4b2_bridge_projection = (
                    build_followup_author_evidence_content_bridge_projection(
                        bridge_state=af4b2_canonical_bridge_state,
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_payload_construction_stage=(
                            FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD:
            ae_observed_execution_state = _safe_mapping(
                observation.payload.get("followup_author_execution_from_ad_state")
            )
            if not ae_observed_execution_state:
                raise RunKernelTransitionError(
                    "AE Author execution observation requires "
                    "followup_author_execution_from_ad_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_execution_from_ad_observation_binding(
                    action_inputs=action_inputs,
                    observed_execution_state=ae_observed_execution_state,
                )
                ae_canonical_execution_record = (
                    build_followup_author_execution_from_ad_record(
                        action_inputs=action_inputs,
                        **self._followup_author_execution_from_ad_runtime_inputs(),
                    )
                )
                ae_canonical_execution_state = (
                    build_run_kernel_followup_author_execution_from_ad_state(
                        execution_record_state=(
                            ae_canonical_execution_record.to_dict()
                        ),
                        observation_id=ae_observed_execution_state.get(
                            "observation_id"
                        ),
                    )
                )
                ae_packet_projection = ae_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=ae_canonical_execution_state,
                )
                ae_authority_projection = ae_authority_projection_from_record(
                    current_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    record_state=ae_canonical_execution_state,
                )
                ae_author_observation = _safe_mapping(
                    ae_canonical_execution_state.get("author_observation")
                )
                ae_final_answer_outcome = _safe_mapping(
                    ae_canonical_execution_state.get("final_answer_outcome")
                )
                ae_execution_projection = (
                    build_followup_author_execution_from_ad_projection(
                        execution_state=ae_canonical_execution_state,
                        behavior_boundary_flags=_safe_mapping(
                            ae_canonical_execution_state.get(
                                "behavior_boundary_flags"
                            )
                        ),
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_payload_construction_stage=(
                            FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION:
            af4_observed_invocation_state = _safe_mapping(
                observation.payload.get("followup_author_invocation_construction_state")
            )
            if not af4_observed_invocation_state:
                raise RunKernelTransitionError(
                    "AF4 Author invocation construction observation requires "
                    "followup_author_invocation_construction_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_invocation_construction_observation_binding(
                    action_inputs=action_inputs,
                    observed_invocation_state=af4_observed_invocation_state,
                )
                af4_canonical_invocation_record = (
                    build_followup_author_invocation_construction_record(
                        action_inputs=action_inputs,
                        **self._followup_author_invocation_construction_runtime_inputs(),
                    )
                )
                af4_canonical_invocation_state = (
                    build_run_kernel_followup_author_invocation_construction_state(
                        invocation_record_state=(
                            af4_canonical_invocation_record.to_dict()
                        ),
                        observation_id=af4_observed_invocation_state.get(
                            "observation_id"
                        ),
                    )
                )
                af4_packet_projection = af4_packet_projection_from_record(
                    current_packet=self.state.final_answer_packet,
                    record_state=af4_canonical_invocation_state,
                )
                af4_authority_projection = af4_authority_projection_from_record(
                    current_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    record_state=af4_canonical_invocation_state,
                )
                af4_invocation_projection = (
                    build_followup_author_invocation_construction_projection(
                        invocation_state=af4_canonical_invocation_state,
                        behavior_boundary_flags=_safe_mapping(
                            af4_canonical_invocation_state.get(
                                "behavior_boundary_flags"
                            )
                        ),
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_payload_construction_stage=(
                            FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY:
            af4d_observed_model_request_state = _safe_mapping(
                observation.payload.get("followup_author_model_request_assembly_state")
            )
            if not af4d_observed_model_request_state:
                raise RunKernelTransitionError(
                    "AF4D Author model request assembly observation requires "
                    "followup_author_model_request_assembly_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_model_request_assembly_observation_binding(
                    action_inputs=action_inputs,
                    observed_model_request_state=af4d_observed_model_request_state,
                )
                af4d_canonical_model_request_record = (
                    build_followup_author_model_request_assembly_record(
                        action_inputs=action_inputs,
                        **self._followup_author_model_request_assembly_runtime_inputs(),
                    )
                )
                af4d_canonical_model_request_state = (
                    build_run_kernel_followup_author_model_request_assembly_state(
                        model_request_record_state=(
                            af4d_canonical_model_request_record.to_dict()
                        ),
                        observation_id=af4d_observed_model_request_state.get(
                            "observation_id"
                        ),
                    )
                )
                af4d_model_request_projection = (
                    build_followup_author_model_request_assembly_projection(
                        model_request_state=af4d_canonical_model_request_state,
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_invocation_construction_stage=(
                            FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE
                        ),
                        followup_author_evidence_content_bridge_stage=(
                            FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D:
            af5a_observed_execution_state = _safe_mapping(
                observation.payload.get("followup_author_execution_from_af4d_state")
            )
            if not af5a_observed_execution_state:
                raise RunKernelTransitionError(
                    "AF5A Author execution from AF4D observation requires "
                    "followup_author_execution_from_af4d_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_execution_from_af4d_observation_binding(
                    action_inputs=action_inputs,
                    observed_execution_state=af5a_observed_execution_state,
                )
                af5a_canonical_execution_record = (
                    build_followup_author_execution_from_af4d_record(
                        action_inputs=action_inputs,
                        observed_execution_state=af5a_observed_execution_state,
                        **self._followup_author_execution_from_af4d_runtime_inputs(),
                    )
                )
                af5a_canonical_execution_state = (
                    build_run_kernel_followup_author_execution_from_af4d_state(
                        execution_record_state=(
                            af5a_canonical_execution_record.to_dict()
                        ),
                        observation_id=af5a_observed_execution_state.get(
                            "observation_id"
                        ),
                    )
                )
                af5a_execution_projection = (
                    build_followup_author_execution_from_af4d_projection(
                        execution_state=af5a_canonical_execution_state,
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_model_request_assembly_stage=(
                            FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        if action.action_type is ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE:
            af5b_observed_finalization_state = _safe_mapping(
                observation.payload.get("followup_author_response_finalization_state")
            )
            if not af5b_observed_finalization_state:
                raise RunKernelTransitionError(
                    "AF5B Author response finalization observation requires "
                    "followup_author_response_finalization_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            try:
                validate_followup_author_response_finalization_observation_binding(
                    action_inputs=action_inputs,
                    observed_finalization_state=af5b_observed_finalization_state,
                )
                af5b_canonical_finalization_record = (
                    build_followup_author_response_finalization_record(
                        action_inputs=action_inputs,
                        observed_finalization_state=af5b_observed_finalization_state,
                        **self._followup_author_response_finalization_runtime_inputs(),
                    )
                )
                af5b_canonical_finalization_state = (
                    build_run_kernel_followup_author_response_finalization_state(
                        finalization_record_state=(
                            af5b_canonical_finalization_record.to_dict()
                        ),
                        observation_id=af5b_observed_finalization_state.get(
                            "observation_id"
                        ),
                    )
                )
                af5b_finalization_projection = (
                    build_followup_author_response_finalization_projection(
                        finalization_state=af5b_canonical_finalization_state,
                        final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                        followup_author_execution_from_af4d_stage=(
                            FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE
                        ),
                    )
                )
                af5b_author_observation = _safe_mapping(
                    af5b_canonical_finalization_state.get("author_observation")
                )
                af5b_final_answer_outcome = _safe_mapping(
                    af5b_canonical_finalization_state.get("final_answer_outcome")
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc

        self.state.reduced_action_ids.add(action.action_id)
        self.state.action_statuses[action.action_id] = observation.status
        self.state.stage_statuses[action.stage] = observation.status
        if action.action_type is ActionType.RUN_CONTRACT_SYNTHESIZE:
            contract_projection = _safe_mapping(
                observation.payload.get("contract_projection")
            )
            if not contract_projection:
                raise RunKernelTransitionError(
                    "run contract synthesis observation requires contract_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            self.state.run_contract = contract_projection
            self.state.run_contract_projection = {
                "owner": "RunKernel.RunAuthorityContract",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "contract_id": contract_projection.get("contract_id"),
                "schema_version": contract_projection.get("schema_version"),
                "synthesis_mode": contract_projection.get("synthesis_mode"),
                "selected_template_ids": contract_projection.get(
                    "selected_template_ids",
                    [],
                ),
                "query_ref": contract_projection.get("query_ref")
                or contract_projection.get("user_query_ref", {}),
                "user_query_ref": contract_projection.get("user_query_ref", {}),
                "selected_depth": contract_projection.get("selected_depth"),
                "source_requirement_summary": contract_projection.get(
                    "source_requirement_summary",
                    [],
                ),
                "source_requirements": contract_projection.get(
                    "source_requirements",
                    [],
                ),
                "inference_policy": contract_projection.get("inference_policy", {}),
                "conflict_policy": contract_projection.get("conflict_policy", {}),
                "numeric_policy": contract_projection.get("numeric_policy", {}),
                "final_posture_policy": contract_projection.get(
                    "final_posture_policy",
                    {},
                ),
                "downstream_hints": contract_projection.get("downstream_hints", {}),
                "validation_status": validation.get("status"),
                "prompt_hash": validation.get("prompt_hash")
                or observation.payload.get("prompt_hash"),
                "prompt_length": validation.get("prompt_length")
                or observation.payload.get("prompt_length"),
                "model_identity": {
                    "provider": validation.get("provider"),
                    "model": validation.get("model"),
                    "effort": validation.get("effort"),
                    "use_reasoning": validation.get("use_reasoning"),
                },
                "prompt_text_retained": False,
                "model_response_text_retained": False,
                "provider_payload_retained": False,
            }
            self.state.run_contract_validation = validation
            self.state.projections[action.stage] = deepcopy(
                self.state.run_contract_projection
            )
        elif action.action_type is ActionType.INITIAL_ANSWER_CONTRACT_ACCEPT:
            proposal_payload = _safe_mapping(
                observation.payload.get("question_meaning_record")
            )
            if not proposal_payload:
                raise RunKernelTransitionError(
                    "initial answer contract acceptance observation requires a "
                    "question_meaning_record proposal payload"
                )
            if self.state.initial_answer_contract_projection:
                raise RunKernelTransitionError(
                    "initial answer contract has already been accepted for this run"
                )
            try:
                acceptance_state = build_initial_answer_contract_acceptance_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    question_meaning_record=proposal_payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                )
                acceptance_projection = (
                    build_initial_answer_contract_acceptance_projection(
                        acceptance_state=acceptance_state
                    )
                )
            except InitialAnswerContractAcceptanceError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.initial_answer_contract = acceptance_state
            self.state.initial_answer_contract_projection = acceptance_projection
            self.state.initial_answer_contract_history.append(
                deepcopy(acceptance_projection)
            )
            self.state.projections[action.stage] = deepcopy(acceptance_projection)
        elif action.action_type is ActionType.SEMANTIC_OBSERVATION_ADMIT:
            if not self.state.initial_answer_contract_projection:
                raise RunKernelTransitionError(
                    "semantic observation admission requires an accepted "
                    "initial answer contract"
                )
            admission_payload = {
                "semantic_observation": _safe_mapping(
                    observation.payload.get("semantic_observation")
                ),
                "sanitized_content_references": [
                    _safe_mapping(ref)
                    for ref in (
                        observation.payload.get("sanitized_content_references")
                        or observation.payload.get("content_references")
                        or []
                    )
                ],
            }
            existing_ids = [
                _safe_mapping(item).get("observation_id")
                for item in self.state.semantic_observation_admission_history
            ]
            existing_digests = [
                _safe_mapping(item).get("observation_digest")
                for item in self.state.semantic_observation_admission_history
            ]
            try:
                admission_state = build_semantic_observation_admission_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=admission_payload,
                    accepted_contract=self.state.initial_answer_contract,
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    existing_observation_ids=existing_ids,
                    existing_observation_digests=existing_digests,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                )
                admission_projection = (
                    build_semantic_observation_admission_projection(
                        admission_state=admission_state
                    )
                )
            except SemanticObservationAdmissionError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.semantic_observation_admission_state = admission_state
            self.state.semantic_observation_admission_projection = (
                admission_projection
            )
            self.state.semantic_observation_admission_history.append(
                deepcopy(admission_projection)
            )
            self.state.projections[action.stage] = deepcopy(admission_projection)
        elif action.action_type is ActionType.COMPONENT_COVERAGE_REDUCE:
            if not self.state.initial_answer_contract_projection:
                raise RunKernelTransitionError(
                    "component coverage reduction requires an accepted "
                    "initial answer contract"
                )
            reduction_payload = _safe_mapping(observation.payload)
            if not reduction_payload.get("component_coverage_record"):
                raise RunKernelTransitionError(
                    "component coverage reduction observation requires a "
                    "component_coverage_record proposal payload"
                )
            existing_ids = [
                _safe_mapping(item).get("coverage_record_id")
                for item in self.state.component_coverage_history
            ]
            existing_digests = [
                _safe_mapping(item).get("coverage_record_digest")
                for item in self.state.component_coverage_history
            ]
            try:
                coverage_state = build_component_coverage_reduction_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    coverage_payload=reduction_payload,
                    accepted_contract=self.state.initial_answer_contract,
                    admission_history=self.state.semantic_observation_admission_history,
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    existing_coverage_record_ids=existing_ids,
                    existing_coverage_record_digests=existing_digests,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                )
                coverage_projection = build_component_coverage_reduction_projection(
                    coverage_state=coverage_state
                )
            except ComponentCoverageReductionError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.component_coverage_state = coverage_state
            self.state.component_coverage_projection = coverage_projection
            self.state.component_coverage_history.append(deepcopy(coverage_projection))
            self.state.projections[action.stage] = deepcopy(coverage_projection)
        elif action.action_type is ActionType.CONTRACT_AMENDMENT_ADMIT:
            if not self.state.initial_answer_contract_projection:
                raise RunKernelTransitionError(
                    "contract amendment admission requires an accepted "
                    "initial answer contract"
                )
            admission_payload = _safe_mapping(observation.payload)
            if not admission_payload.get("contract_amendment_record"):
                raise RunKernelTransitionError(
                    "contract amendment admission observation requires a "
                    "contract_amendment_record proposal payload"
                )
            existing_ids = [
                _safe_mapping(item).get("amendment_record_id")
                for item in self.state.contract_amendment_admission_history
            ]
            existing_digests = [
                _safe_mapping(item).get("amendment_record_digest")
                for item in self.state.contract_amendment_admission_history
            ]
            try:
                amendment_state = build_contract_amendment_admission_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    amendment_payload=admission_payload,
                    accepted_contract=self.state.initial_answer_contract,
                    admission_history=self.state.semantic_observation_admission_history,
                    coverage_history=self.state.component_coverage_history,
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    existing_amendment_record_ids=existing_ids,
                    existing_amendment_record_digests=existing_digests,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                )
                amendment_projection = build_contract_amendment_admission_projection(
                    admission_state=amendment_state
                )
            except ContractAmendmentAdmissionError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.contract_amendment_admission_state = amendment_state
            self.state.contract_amendment_admission_projection = amendment_projection
            self.state.contract_amendment_admission_history.append(
                deepcopy(amendment_projection)
            )
            self.state.projections[action.stage] = deepcopy(amendment_projection)
        elif action.action_type is ActionType.SEARCH_WORK_PLAN_CONSTRUCT:
            construction_result = _safe_mapping(
                observation.payload.get("construction_result")
            )
            plan_projection = _safe_mapping(
                observation.payload.get("search_work_plan_projection")
            )
            if not plan_projection:
                plan_projection = _safe_mapping(
                    construction_result.get("search_work_plan")
                )
            if not plan_projection:
                raise RunKernelTransitionError(
                    "SearchWorkPlan construction observation requires "
                    "search_work_plan_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            if not validation:
                validation = _safe_mapping(construction_result.get("validation"))
            follow_up_authority = _safe_mapping(
                plan_projection.get("follow_up_authority")
            )
            self.state.search_work_plan = plan_projection
            self.state.search_work_plan_validation = validation
            self.state.search_work_plan_projection = {
                "owner": "RunKernel.SearchWorkPlan",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "construction_id": plan_projection.get("metadata", {}).get(
                    "construction_id"
                )
                or construction_result.get("construction_id"),
                "schema_version": plan_projection.get("schema_version"),
                "planning_posture": plan_projection.get("planning_posture"),
                "requested_mode": plan_projection.get("requested_mode", {}),
                "effective_contract": plan_projection.get("effective_contract", {}),
                "query_shape": plan_projection.get("query_shape", {}),
                "component_count": len(plan_projection.get("components", []) or []),
                "provider_job_count": len(
                    plan_projection.get("provider_jobs", []) or []
                ),
                "quant_work_unit_count": len(
                    plan_projection.get("quant_work_units", []) or []
                ),
                "audit_job_count": len(plan_projection.get("audit_jobs", []) or []),
                "stop_condition_count": len(
                    plan_projection.get("stop_conditions", []) or []
                ),
                "follow_up_permission": follow_up_authority.get("permission"),
                "validation_status": _validation_status(validation),
                "search_work_plan_runtime_consumed": False,
                "runtime_consumed_by_query_plan": False,
                "provider_search_behavior_changed": False,
                "query_plan_behavior_changed": False,
                "prompt_behavior_changed": False,
                "final_answer_behavior_changed": False,
            }
            self.state.projections[action.stage] = deepcopy(
                self.state.search_work_plan_projection
            )
        elif action.action_type is ActionType.EVIDENCE_LEDGER_REDUCE:
            self.state.evidence_ledger.reduce_observation(observation.payload)
            self.state.projections[action.stage] = (
                self.state.evidence_ledger.to_projection().to_dict()
            )
        elif action.action_type is ActionType.SEARCH_JUDGMENT_DECIDE:
            judgment_projection = _safe_mapping(
                observation.payload.get("judgment_projection")
            )
            if not judgment_projection:
                raise RunKernelTransitionError(
                    "search judgment observation requires judgment_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            self.state.search_judgment = judgment_projection
            self.state.search_judgment_projection = {
                "owner": "RunKernel.RunAuthoritySearchJudgment",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "schema_version": judgment_projection.get("schema_version"),
                "judgment_id": judgment_projection.get("judgment_id"),
                "decision": judgment_projection.get("decision"),
                "mode": judgment_projection.get("mode"),
                "classifications": judgment_projection.get("classifications", []),
                "contract_id": judgment_projection.get("contract_id"),
                "selected_template_ids": judgment_projection.get(
                    "selected_template_ids",
                    [],
                ),
                "satisfaction": judgment_projection.get("satisfaction", {}),
                "gaps": judgment_projection.get("gaps", []),
                "redundancy": judgment_projection.get("redundancy", {}),
                "continuation": judgment_projection.get("continuation", {}),
                "target_source_classes": judgment_projection.get(
                    "target_source_classes",
                    [],
                ),
                "recommended_queries": judgment_projection.get(
                    "recommended_queries",
                    [],
                ),
                "helper_assessments": judgment_projection.get(
                    "helper_assessments",
                    {},
                ),
                "insufficient_posture": judgment_projection.get(
                    "insufficient_posture",
                    {},
                ),
                "rationale": judgment_projection.get("rationale"),
                "validation_status": validation.get("status")
                or judgment_projection.get("validation", {}).get("status"),
                "prompt_hash": validation.get("prompt_hash")
                or observation.payload.get("prompt_hash"),
                "prompt_length": validation.get("prompt_length")
                or observation.payload.get("prompt_length"),
                "model_identity": {
                    "provider": validation.get("provider"),
                    "model": validation.get("model"),
                    "effort": validation.get("effort"),
                    "use_reasoning": validation.get("use_reasoning"),
                },
                "prompt_text_retained": False,
                "model_response_text_retained": False,
                "provider_payload_retained": False,
            }
            self.state.search_judgment_history.append(
                deepcopy(self.state.search_judgment_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.search_judgment_projection
            )
        elif action.action_type is ActionType.SUFFICIENCY_JUDGMENT_DECIDE:
            raw_judgment_projection = observation.payload.get("judgment_projection")
            judgment_projection = _safe_mapping(raw_judgment_projection)
            if isinstance(raw_judgment_projection, Mapping):
                semantic_consumption = _safe_semantic_consumption(
                    raw_judgment_projection.get("semantic_consumption")
                )
                if semantic_consumption:
                    judgment_projection["semantic_consumption"] = semantic_consumption
            if not judgment_projection:
                raise RunKernelTransitionError(
                    "sufficiency judgment observation requires judgment_projection"
                )
            validation = _safe_mapping(observation.payload.get("validation"))
            self.state.sufficiency_judgment = judgment_projection
            self.state.sufficiency_judgment_projection = (
                _canonical_sufficiency_judgment_projection(
                    judgment_projection=judgment_projection,
                    validation=validation,
                    observation_payload=observation.payload,
                )
            )
            self.state.sufficiency_judgment_history.append(
                deepcopy(self.state.sufficiency_judgment_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.sufficiency_judgment_projection
            )
        elif action.action_type is ActionType.FINAL_ANSWER_PACKET_PREPARE:
            packet_projection = _safe_mapping(
                observation.payload.get("packet_projection")
            )
            if not packet_projection:
                raise RunKernelTransitionError(
                    "final answer packet observation requires packet_projection"
                )
            author_payload_ref = _safe_mapping(
                observation.payload.get("author_payload_ref")
            )
            self.state.final_answer_packet = packet_projection
            self.state.final_answer_authority_projection = {
                "owner": "RunKernel.FinalAnswerPacket",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "packet_id": packet_projection.get("packet_id"),
                "readiness_status": packet_projection.get("readiness_status"),
                "readiness_reasons": packet_projection.get("readiness_reasons", []),
                "author_payload_ref": author_payload_ref,
                "citation_eligible_source_ids": author_payload_ref.get(
                    "citation_source_ids",
                    [],
                ),
                "missing_source_obligation_count": len(
                    author_payload_ref.get("missing_source_obligations", []) or []
                ),
                "partial_source_obligation_count": len(
                    author_payload_ref.get("partial_source_obligations", []) or []
                ),
                "satisfied_source_obligation_count": len(
                    author_payload_ref.get("satisfied_source_obligations", []) or []
                ),
                "source_bound_numeric_unknown_count": len(
                    author_payload_ref.get("source_bound_numeric_unknowns", []) or []
                ),
                "mandatory_caveat_count": author_payload_ref.get(
                    "mandatory_caveat_count",
                    0,
                ),
                "prohibited_upgrade_count": author_payload_ref.get(
                    "prohibited_upgrade_count",
                    0,
                ),
                "author_authority_payload_ref": author_payload_ref.get(
                    "authority_payload",
                    {},
                ),
            }
            self.state.projections[action.stage] = deepcopy(
                self.state.final_answer_authority_projection
            )
        elif action.action_type is ActionType.AUTHOR_EXECUTE:
            payload = _safe_mapping(observation.payload)
            self.state.author_observation = payload
            self.state.final_answer_outcome = {
                "owner": "RunKernel.AuthorObservation",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "packet_id": payload.get("packet_id"),
                "report_hash": payload.get("report_hash"),
                "report_length": payload.get("report_length"),
                "author_seconds": payload.get("author_seconds"),
                "stream_displayed": payload.get("stream_displayed"),
                "author_provider": payload.get("author_provider"),
                "author_model": payload.get("author_model"),
                "author_effort": payload.get("author_effort"),
                "final_text_included": False,
            }
            self.state.projections[action.stage] = deepcopy(
                self.state.final_answer_outcome
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHORIZATION_CONSUME:
            followup_state = _safe_mapping(
                observation.payload.get("followup_authorization_state")
            )
            if not followup_state:
                raise RunKernelTransitionError(
                    "follow-up authorization observation requires "
                    "followup_authorization_state"
                )
            for sealed in followup_state.get("sealed_candidates", []) or []:
                if not isinstance(sealed, Mapping):
                    continue
                gate = sealed.get("execution_gate", {})
                if not isinstance(gate, Mapping):
                    raise RunKernelTransitionError(
                        "follow-up authorization seal requires execution gate"
                    )
                if (
                    gate.get("execution_permission") is not False
                    or gate.get("executable_in_current_phase") is not False
                    or gate.get("provider_execution_licensed") is not False
                ):
                    raise RunKernelTransitionError(
                        "AG-96I2A follow-up authorization must be non-executable"
                    )
            gate = followup_state.get("execution_gate", {})
            if not isinstance(gate, Mapping) or gate.get("execution_permission") is not False:
                raise RunKernelTransitionError(
                    "AG-96I2A follow-up authorization state requires closed execution gate"
                )
            self.state.followup_authorization_state = followup_state
            self.state.followup_authorization_projection = (
                build_followup_authorization_projection(
                    followup_state=followup_state,
                    execution_gate=_safe_mapping(gate),
                    behavior_boundary_flags=_safe_mapping(
                        followup_state.get("behavior_boundary_flags")
                    ),
                )
            )
            self.state.followup_authorization_history.append(
                deepcopy(self.state.followup_authorization_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_authorization_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_FIXTURE_EXECUTE:
            execution_state = _safe_mapping(
                observation.payload.get("followup_execution_state")
            )
            if not execution_state:
                raise RunKernelTransitionError(
                    "follow-up execution observation requires followup_execution_state"
                )
            if not self.state.followup_authorization_state:
                raise RunKernelTransitionError(
                    "follow-up execution requires existing authorization state"
                )
            if (
                execution_state.get("followup_authorization_consumption_id")
                != self.state.followup_authorization_state.get("consumption_id")
            ):
                raise RunKernelTransitionError(
                    "follow-up execution must reference current authorization state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_execution_action_binding,
                action_inputs=action_inputs,
                execution_state=execution_state,
            )
            gate = _safe_mapping(execution_state.get("execution_gate"))
            flags = _safe_mapping(execution_state.get("behavior_boundary_flags"))
            if gate.get("allowed_execution_mode") != "fixture_only":
                raise RunKernelTransitionError(
                    "follow-up execution reducer only accepts fixture_only observations"
                )
            if gate.get("provider_execution_licensed") is not False:
                raise RunKernelTransitionError(
                    "follow-up execution observation must keep provider execution unlicensed"
                )
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_EXECUTION_FALSE_FLAGS,
                context="follow-up execution observation",
            )
            if execution_state.get("evidence_ledger_intake_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up execution must defer EvidenceLedger intake"
                )
            if execution_state.get("evidence_ledger_evidence_admitted") is not False:
                raise RunKernelTransitionError(
                    "follow-up execution must not admit EvidenceLedger evidence"
                )
            self.state.followup_execution_state = execution_state
            self.state.followup_execution_projection = (
                build_followup_execution_projection(
                    execution_state=execution_state,
                    execution_gate=gate,
                    behavior_boundary_flags=flags,
                    budget_semantics=_safe_mapping(
                        execution_state.get("budget_semantics")
                    ),
                )
            )
            self.state.followup_execution_history.append(
                deepcopy(self.state.followup_execution_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_execution_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_PROVIDER_JOB_EXECUTE:
            observed_execution_state = _safe_mapping(
                observation.payload.get("followup_execution_state")
            )
            if not observed_execution_state:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution observation requires "
                    "followup_execution_state"
                )
            if not self.state.followup_authorization_state:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution requires existing "
                    "authorization state"
                )
            if (
                observed_execution_state.get("followup_authorization_consumption_id")
                != self.state.followup_authorization_state.get("consumption_id")
            ):
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must reference current "
                    "authorization state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_provider_job_execution_action_binding,
                action_inputs=action_inputs,
                execution_state=observed_execution_state,
            )
            if _followup_provider_job_closed_surface_claimed(
                observed_execution_state
            ):
                raise RunKernelTransitionError(
                    "follow-up provider-job execution observation claims closed "
                    "answer authority"
                )
            flags = _safe_mapping(
                observed_execution_state.get("behavior_boundary_flags")
            )
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_PROVIDER_JOB_EXECUTION_FALSE_FLAGS,
                context="follow-up provider-job execution observation",
            )
            for field_name in (
                "provider_execution_licensed",
                "live_provider_call_executed",
                "search_executed",
                "retrieval_executed",
                "fetch_executed",
                "model_called",
            ):
                if observed_execution_state.get(field_name) is not False:
                    raise RunKernelTransitionError(
                        "follow-up provider-job execution observation requires "
                        f"{field_name}=False"
                    )
            if observed_execution_state.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must not run live validation"
                )
            if observed_execution_state.get("offline_live_shaped_execution") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must be offline live-shaped"
                )
            if observed_execution_state.get("adapter_result_injected") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution requires injected adapter result"
                )
            if observed_execution_state.get("evidence_ledger_intake_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must defer EvidenceLedger intake"
                )
            if observed_execution_state.get("evidence_ledger_evidence_admitted") is not False:
                raise RunKernelTransitionError(
                    "follow-up provider-job execution must not admit EvidenceLedger evidence"
                )
            summary = _safe_mapping(
                observed_execution_state.get("sanitized_candidate_summary")
            )
            canonical_budget_semantics = (
                _canonical_followup_provider_job_budget_semantics(
                    _safe_mapping(action_inputs.get("budget_debit"))
                )
            )
            canonical_execution_gate = (
                _canonical_followup_provider_job_execution_gate()
            )
            canonical_redaction_posture = (
                _canonical_followup_provider_job_redaction_posture()
            )
            execution_state = {
                **observed_execution_state,
                "owner": "RunKernel.FollowupProviderJobExecution",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "run_id": action_inputs.get("run_id"),
                "checkpoint_id": action_inputs.get("checkpoint_id"),
                "followup_authorization_consumption_id": action_inputs.get(
                    "followup_authorization_consumption_id"
                ),
                "sealed_candidate_id": action_inputs.get("sealed_candidate_id"),
                "execution_mode": FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
                "provider_job_kind": action_inputs.get("provider_job_kind"),
                "component_id": action_inputs.get("component_id"),
                "source_obligation_id": action_inputs.get("source_obligation_id"),
                "requirement_ids": action_inputs.get("requirement_ids", []),
                "expected_source_classes": action_inputs.get(
                    "expected_source_classes",
                    [],
                ),
                "expected_evidence_ledger_custody_update": action_inputs.get(
                    "expected_evidence_ledger_custody_update",
                    {},
                ),
                "budget_debit": action_inputs.get("budget_debit", {}),
                "authorized_query_ref": action_inputs.get("authorized_query_ref"),
                "authorized_query": action_inputs.get("authorized_query"),
                "sanitized_candidate_summary": summary,
                "provider_execution_licensed": False,
                "live_provider_call_executed": False,
                "search_executed": False,
                "retrieval_executed": False,
                "fetch_executed": False,
                "model_called": False,
                "live_validation_not_run": True,
                "source_obligation_satisfied": False,
                "final_evidence_satisfied": False,
                "citation_eligible": False,
                "sufficiency_ready": False,
                "final_answer_packet_ready": False,
                "author_activation_allowed": False,
                "author_executor_invoked": False,
                "citation_rendering_changed": False,
                "citation_formatter_invoked": False,
                "product_answer_behavior_changed": False,
                "evidence_ledger_intake_deferred": True,
                "evidence_ledger_evidence_admitted": False,
                "budget_semantics": canonical_budget_semantics,
                "execution_gate": canonical_execution_gate,
                "redaction_posture": canonical_redaction_posture,
                "behavior_boundary_flags": {
                    **flags,
                    "provider_execution_licensed": False,
                    "live_provider_call_executed": False,
                    "provider_job_scheduled": False,
                    "provider_job_dispatched": False,
                    "search_executed": False,
                    "retrieval_executed": False,
                    "fetch_executed": False,
                    "model_called": False,
                    "query_generation_changed": False,
                    "retrieval_ranking_filtering_changed": False,
                    "pipeline_orchestrator_domain_logic_changed": False,
                    "evidence_ledger_mutated": False,
                    "sufficiency_judgment_rechecked": False,
                    "final_answer_packet_updated": False,
                    "author_executor_invoked": False,
                    "citation_formatter_invoked": False,
                    "citation_behavior_changed": False,
                    "product_answer_behavior_changed": False,
                    "final_answer_behavior_changed": False,
                },
            }
            self.state.followup_execution_state = execution_state
            canonical_flags = _safe_mapping(
                execution_state.get("behavior_boundary_flags")
            )
            self.state.followup_execution_projection = (
                build_followup_execution_projection(
                    execution_state=execution_state,
                    execution_gate=_safe_mapping(execution_state.get("execution_gate")),
                    behavior_boundary_flags=canonical_flags,
                    budget_semantics=canonical_budget_semantics,
                )
            )
            self.state.followup_execution_history.append(
                deepcopy(self.state.followup_execution_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_execution_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_EVIDENCE_INTAKE:
            intake_state = _safe_mapping(
                observation.payload.get("followup_evidence_intake_state")
            )
            if not intake_state:
                raise RunKernelTransitionError(
                    "follow-up evidence intake observation requires "
                    "followup_evidence_intake_state"
                )
            if not self.state.followup_execution_state:
                raise RunKernelTransitionError(
                    "follow-up evidence intake requires existing execution state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_evidence_intake_action_binding,
                action_inputs=action_inputs,
                execution_state=self.state.followup_execution_state,
                intake_state=intake_state,
            )
            flags = _safe_mapping(intake_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_INTAKE_FALSE_FLAGS,
                context="follow-up evidence intake observation",
            )
            if flags.get("evidence_ledger_mutated") is not True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must be the EvidenceLedger mutation seam"
                )
            if flags.get("evidence_ledger_intake_only_opened_surface") is not True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake may only open EvidenceLedger intake"
                )
            if intake_state.get("provider_execution_licensed") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must keep provider execution unlicensed"
                )
            if intake_state.get("evidence_ledger_intake_mode") not in {
                "fixture_only_followup_intake",
                "bounded_provider_job_offline_followup_intake",
                AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
            }:
                raise RunKernelTransitionError(
                    "follow-up evidence intake requires known intake mode"
                )
            if intake_state.get("final_evidence_satisfied") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not satisfy final evidence"
                )
            if intake_state.get("citation_eligible") is not False:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not create citation eligibility"
                )
            if intake_state.get("author_activation_allowed") is True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not activate Author"
                )
            if intake_state.get("final_answer_packet_updated") is True:
                raise RunKernelTransitionError(
                    "follow-up evidence intake must not update FinalAnswerPacket"
                )
            ledger_observation = build_followup_evidence_intake_ledger_observation(
                intake_state=intake_state,
                execution_state=self.state.followup_execution_state,
            )
            derived_outcome = followup_evidence_intake_outcome(ledger_observation)
            intake_state = {
                **intake_state,
                **derived_outcome,
                "ledger_observation": deepcopy(ledger_observation),
                "ledger_requirements": deepcopy(
                    ledger_observation.get("requirements", [])
                ),
                "ledger_candidates": deepcopy(ledger_observation.get("candidates", [])),
                "ledger_requirement_links": deepcopy(
                    ledger_observation.get("requirement_links", [])
                ),
                "ledger_followup_fixture_intake": deepcopy(
                    ledger_observation.get("followup_fixture_intake", {})
                ),
                "ledger_followup_provider_job_intake": deepcopy(
                    ledger_observation.get("followup_provider_job_intake", {})
                ),
            }
            self.state.evidence_ledger.reduce_observation(ledger_observation)
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            self.state.projections[EVIDENCE_LEDGER_STAGE] = deepcopy(
                ledger_projection
            )
            self.state.followup_evidence_intake_state = intake_state
            self.state.followup_evidence_intake_projection = (
                build_followup_evidence_intake_projection(
                    intake_state=intake_state,
                    ledger_observation=ledger_observation,
                    ledger_projection=ledger_projection,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_evidence_intake_history.append(
                deepcopy(self.state.followup_evidence_intake_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_evidence_intake_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_SUFFICIENCY_RECHECK:
            observed_recheck_state = _safe_mapping(
                observation.payload.get("followup_sufficiency_recheck_state")
            )
            if not observed_recheck_state:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck observation requires "
                    "followup_sufficiency_recheck_state"
                )
            if not self.state.followup_evidence_intake_state:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck requires existing intake state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_sufficiency_recheck_observation_binding,
                action_inputs=action_inputs,
                observed_recheck_state=observed_recheck_state,
            )
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            try:
                canonical_record = build_followup_sufficiency_recheck_record(
                    action_inputs=action_inputs,
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                    evidence_ledger_projection=ledger_projection,
                    prior_sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    sufficiency_handoff=_safe_mapping(
                        self.state.followup_authorization_state.get(
                            "sufficiency_handoff"
                        )
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            recheck_state = canonical_record.to_dict()
            judgment_projection = _safe_mapping(
                recheck_state.get("sufficiency_judgment_projection")
            )
            if not judgment_projection:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck requires SufficiencyJudgment "
                    "projection"
                )
            flags = _safe_mapping(recheck_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_RECHECK_FALSE_FLAGS,
                context="follow-up sufficiency recheck",
            )
            if flags.get("sufficiency_judgment_rechecked") is not True:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must recheck SufficiencyJudgment"
                )
            if recheck_state.get("final_answer_packet_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must defer FinalAnswerPacket"
                )
            if recheck_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must keep Author closed"
                )
            if recheck_state.get("citation_behavior_changed") is not False:
                raise RunKernelTransitionError(
                    "follow-up sufficiency recheck must not change citations"
                )
            recheck_state = {
                **recheck_state,
                "owner": "RunKernel.FollowupSufficiencyRecheck",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "observation_id": observed_recheck_state.get("observation_id"),
            }
            self.state.followup_sufficiency_recheck_state = recheck_state
            validation = _safe_mapping(judgment_projection.get("validation"))
            self.state.sufficiency_judgment = judgment_projection
            self.state.sufficiency_judgment_projection = (
                _canonical_sufficiency_judgment_projection(
                    judgment_projection=judgment_projection,
                    validation=validation,
                    observation_payload=judgment_projection,
                )
            )
            self.state.sufficiency_judgment_history.append(
                deepcopy(self.state.sufficiency_judgment_projection)
            )
            self.state.projections[SUFFICIENCY_JUDGMENT_STAGE] = deepcopy(
                self.state.sufficiency_judgment_projection
            )
            self.state.followup_sufficiency_recheck_projection = (
                build_followup_sufficiency_recheck_projection(
                    recheck_state=recheck_state,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_sufficiency_recheck_history.append(
                deepcopy(self.state.followup_sufficiency_recheck_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_sufficiency_recheck_projection
            )
        elif (
            action.action_type
            is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_READINESS
        ):
            observed_readiness_state = _safe_mapping(
                observation.payload.get(
                    "followup_final_answer_packet_readiness_state"
                )
            )
            if not observed_readiness_state:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness observation requires "
                    "followup_final_answer_packet_readiness_state"
                )
            if not self.state.followup_sufficiency_recheck_state:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness requires existing "
                    "recheck state"
                )
            if self.state.final_answer_packet:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must not follow a "
                    "canonical FinalAnswerPacket mutation"
                )
            if self.state.final_answer_authority_projection:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must not follow a "
                    "final-answer authority projection mutation"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_final_answer_packet_readiness_observation_binding,
                action_inputs=action_inputs,
                observed_readiness_state=observed_readiness_state,
            )
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            try:
                canonical_record = (
                    build_followup_final_answer_packet_readiness_record(
                        action_inputs=action_inputs,
                        followup_sufficiency_recheck_state=(
                            self.state.followup_sufficiency_recheck_state
                        ),
                        sufficiency_judgment_projection=(
                            self.state.sufficiency_judgment_projection
                        ),
                        evidence_ledger_projection=ledger_projection,
                        followup_evidence_intake_state=(
                            self.state.followup_evidence_intake_state
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            readiness_state = {
                **canonical_record.to_dict(),
                "owner": "RunKernel.FollowupFinalAnswerPacketReadiness",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "diagnostic_only": True,
                "not_final_answer_packet_authority": True,
                "not_role_consumption_payload": True,
                "observation_id": observed_readiness_state.get("observation_id"),
            }
            flags = _safe_mapping(readiness_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_PACKET_READINESS_FALSE_FLAGS,
                context="follow-up FinalAnswerPacket readiness",
            )
            if flags.get("packet_preparation_readiness_recorded") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must record readiness"
                )
            if readiness_state.get("canonical_final_answer_packet_mutated") is not False:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must not mutate packet"
                )
            if readiness_state.get("final_evidence_selected") is not False:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must not select evidence"
                )
            if readiness_state.get("citation_eligible") is not False:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must not create citations"
                )
            if readiness_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must keep Author closed"
                )
            if readiness_state.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must defer Author"
                )
            if readiness_state.get("answer_ready") is not False:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must keep answer_ready false"
                )
            if readiness_state.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket readiness must not run live validation"
                )
            self.state.followup_final_answer_packet_readiness_state = (
                readiness_state
            )
            self.state.followup_final_answer_packet_readiness_projection = (
                build_followup_final_answer_packet_readiness_projection(
                    readiness_state=readiness_state,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_final_answer_packet_readiness_history.append(
                deepcopy(self.state.followup_final_answer_packet_readiness_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_final_answer_packet_readiness_projection
            )
        elif (
            action.action_type
            is ActionType.FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL
        ):
            observed_shell_state = _safe_mapping(
                observation.payload.get(
                    "followup_blocked_final_answer_packet_shell_state"
                )
            )
            if not observed_shell_state:
                raise RunKernelTransitionError(
                    "follow-up blocked FinalAnswerPacket shell observation "
                    "requires followup_blocked_final_answer_packet_shell_state"
                )
            if not self.state.followup_final_answer_packet_readiness_state:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell requires existing O1 readiness"
                )
            if self.state.final_answer_packet:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must not overwrite an "
                    "existing canonical FinalAnswerPacket"
                )
            if self.state.final_answer_authority_projection:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must not follow final-answer "
                    "authority projection mutation"
                )
            if self.state.followup_blocked_final_answer_packet_shell_state.get(
                "packet_preparation_readiness_id"
            ) == self.state.followup_final_answer_packet_readiness_state.get(
                "packet_preparation_readiness_id"
            ):
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell already activated for this readiness"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_blocked_final_answer_packet_shell_observation_binding,
                action_inputs=action_inputs,
                observed_shell_state=observed_shell_state,
            )
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            try:
                canonical_record = (
                    build_followup_blocked_final_answer_packet_shell_record(
                        action_inputs=action_inputs,
                        followup_final_answer_packet_readiness_state=(
                            self.state.followup_final_answer_packet_readiness_state
                        ),
                        followup_sufficiency_recheck_state=(
                            self.state.followup_sufficiency_recheck_state
                        ),
                        sufficiency_judgment_projection=(
                            self.state.sufficiency_judgment_projection
                        ),
                        evidence_ledger_projection=ledger_projection,
                        followup_evidence_intake_state=(
                            self.state.followup_evidence_intake_state
                        ),
                    )
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            shell_state = {
                **canonical_record.to_dict(),
                "owner": "RunKernel.FollowupBlockedFinalAnswerPacketShell",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "observation_id": observed_shell_state.get("observation_id"),
            }
            packet_projection = _safe_mapping(shell_state.get("packet_projection"))
            if not packet_projection:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell requires packet_projection"
                )
            flags = _safe_mapping(shell_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_BLOCKED_PACKET_SHELL_FALSE_FLAGS,
                context="blocked FinalAnswerPacket shell",
            )
            if flags.get("packet_preparation_readiness_consumed") is not True:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must consume O1 readiness"
                )
            if flags.get("canonical_final_answer_packet_mutated") is not True:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must mutate canonical packet"
                )
            if packet_projection.get("owner") != "RunKernel.FinalAnswerPacket":
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell requires RunKernel packet owner"
                )
            if packet_projection.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell requires canonical packet"
                )
            if packet_projection.get("readiness_status") != "blocked":
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must keep readiness_status=blocked"
                )
            if packet_projection.get("final_answer_allowed") is not False:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must keep final answers disallowed"
                )
            if packet_projection.get("answer_ready") is not False:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must keep answer_ready false"
                )
            for empty_field in (
                "evidence_allowed",
                "evidence_excluded",
                "author_evidence",
                "citation_eligible",
                "citation_ineligible",
            ):
                if packet_projection.get(empty_field) != []:
                    raise RunKernelTransitionError(
                        "blocked FinalAnswerPacket shell must keep "
                        f"{empty_field} empty"
                    )
            if packet_projection.get("author_input_refs") != {}:
                raise RunKernelTransitionError(
                    "blocked FinalAnswerPacket shell must keep author_input_refs empty"
                )
            for forbidden_field in (
                "final_evidence_refs",
                "citation_eligible_source_ids",
                "citation_eligibility_refs",
                "author_payload_ref",
            ):
                if packet_projection.get(forbidden_field) not in (
                    None,
                    False,
                    [],
                    (),
                    {},
                ):
                    raise RunKernelTransitionError(
                        "blocked FinalAnswerPacket shell must not create "
                        f"{forbidden_field}"
                    )
            self.state.followup_blocked_final_answer_packet_shell_state = (
                shell_state
            )
            self.state.final_answer_packet = packet_projection
            self.state.followup_blocked_final_answer_packet_shell_projection = (
                build_followup_blocked_final_answer_packet_shell_projection(
                    shell_state=shell_state,
                    packet_projection=packet_projection,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_blocked_final_answer_packet_shell_history.append(
                deepcopy(
                    self.state.followup_blocked_final_answer_packet_shell_projection
                )
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_blocked_final_answer_packet_shell_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_FINAL_EVIDENCE_SELECTION:
            observed_selection_state = p1_observed_selection_state or _safe_mapping(
                observation.payload.get("followup_final_evidence_selection_state")
            )
            if p1_canonical_record is None:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection preflight did not rebuild "
                    "canonical packet"
                )
            selection_state = {
                **p1_canonical_record.to_dict(),
                "owner": "RunKernel.FollowupFinalEvidenceSelection",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "observation_id": observed_selection_state.get("observation_id"),
            }
            packet_projection = _safe_mapping(
                selection_state.get("packet_projection")
            )
            if not packet_projection:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection requires packet_projection"
                )
            flags = _safe_mapping(selection_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_FINAL_EVIDENCE_SELECTION_FALSE_FLAGS,
                context="follow-up final evidence selection",
            )
            if flags.get("packet_preparation_readiness_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must consume O1 readiness"
                )
            if flags.get("blocked_final_answer_packet_shell_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must consume O2 shell"
                )
            if flags.get("canonical_final_answer_packet_mutated") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must mutate packet"
                )
            if flags.get("final_evidence_selected") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection flags must select evidence"
                )
            if selection_state.get("final_evidence_selected") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must select evidence"
                )
            if packet_projection.get("owner") != "RunKernel.FinalAnswerPacket":
                raise RunKernelTransitionError(
                    "follow-up final evidence selection requires packet owner"
                )
            if packet_projection.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection requires canonical packet"
                )
            if packet_projection.get("readiness_status") != "blocked":
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must remain blocked"
                )
            if packet_projection.get("final_answer_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must disallow final answers"
                )
            if packet_projection.get("answer_ready") is not False:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must keep answer_ready false"
                )
            if not packet_projection.get("evidence_allowed"):
                raise RunKernelTransitionError(
                    "follow-up final evidence selection requires selected evidence"
                )
            for empty_field in (
                "citation_eligible",
                "citation_ineligible",
                "author_evidence",
            ):
                if packet_projection.get(empty_field) != []:
                    raise RunKernelTransitionError(
                        "follow-up final evidence selection must keep "
                        f"{empty_field} empty"
                    )
            if packet_projection.get("author_input_refs") != {}:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must keep "
                    "author_input_refs empty"
                )
            for forbidden_field in (
                "citation_eligible_source_ids",
                "citation_eligibility_refs",
                "author_payload_ref",
            ):
                if packet_projection.get(forbidden_field) not in (
                    None,
                    False,
                    [],
                    (),
                    {},
                ):
                    raise RunKernelTransitionError(
                        "follow-up final evidence selection must not create "
                        f"{forbidden_field}"
                    )
            for closed_field in (
                "citations_rendered",
                "citation_rendering_changed",
                "citation_behavior_changed",
                "citation_formatter_invoked",
                "author_payload_created",
                "author_activation_allowed",
                "analyst_activation_allowed",
                "analyst_handoff_created",
                "economist_activation_allowed",
                "economist_handoff_created",
                "economist_code_execution_allowed",
                "prompt_behavior_changed",
                "product_answer_behavior_changed",
            ):
                if packet_projection.get(closed_field) is not False:
                    raise RunKernelTransitionError(
                        "follow-up final evidence selection must keep "
                        f"{closed_field}=False"
                    )
            if packet_projection.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must defer Author"
                )
            if packet_projection.get("citation_eligibility_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must defer citation "
                    "eligibility"
                )
            if packet_projection.get("not_role_consumption_payload") is not True:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection must not be "
                    "role-consumable"
                )
            if self.state.final_answer_authority_projection:
                raise RunKernelTransitionError(
                    "follow-up final evidence selection cannot follow authority "
                    "projection mutation"
                )
            self.state.followup_final_evidence_selection_state = selection_state
            self.state.final_answer_packet = packet_projection
            self.state.followup_final_evidence_selection_projection = (
                build_followup_final_evidence_selection_projection(
                    selection_state=selection_state,
                    packet_projection=packet_projection,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_final_evidence_selection_history.append(
                deepcopy(self.state.followup_final_evidence_selection_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_final_evidence_selection_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_CITATION_ELIGIBILITY:
            observed_citation_state = q1_observed_citation_state or _safe_mapping(
                observation.payload.get("followup_citation_eligibility_state")
            )
            if q1_canonical_record is None:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility preflight did not rebuild "
                    "canonical packet"
                )
            citation_state = {
                **q1_canonical_record.to_dict(),
                "owner": "RunKernel.FollowupCitationEligibility",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "observation_id": observed_citation_state.get("observation_id"),
            }
            packet_projection = _safe_mapping(
                citation_state.get("packet_projection")
            )
            if not packet_projection:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility requires packet_projection"
                )
            flags = _safe_mapping(citation_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_CITATION_ELIGIBILITY_FALSE_FLAGS,
                context="follow-up citation eligibility",
            )
            if flags.get("packet_preparation_readiness_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must consume O1 readiness"
                )
            if flags.get("blocked_final_answer_packet_shell_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must consume O2 shell"
                )
            if flags.get("final_evidence_selection_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must consume P1 selection"
                )
            if flags.get("canonical_final_answer_packet_mutated") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must mutate packet"
                )
            if flags.get("citation_eligibility_created") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility flags must create eligibility"
                )
            if packet_projection.get("owner") != "RunKernel.FinalAnswerPacket":
                raise RunKernelTransitionError(
                    "follow-up citation eligibility requires packet owner"
                )
            if packet_projection.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility requires canonical packet"
                )
            if packet_projection.get("readiness_status") != "blocked":
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must remain blocked"
                )
            if packet_projection.get("final_answer_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must disallow final answers"
                )
            if packet_projection.get("answer_ready") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must keep answer_ready false"
                )
            if not packet_projection.get("evidence_allowed"):
                raise RunKernelTransitionError(
                    "follow-up citation eligibility requires selected evidence"
                )
            if packet_projection.get("author_input_refs") != {}:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must keep author_input_refs empty"
                )
            if packet_projection.get("citation_eligibility_deferred") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must close eligibility deferral"
                )
            if packet_projection.get("citation_rendering_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must defer rendering"
                )
            if packet_projection.get("not_role_consumption_payload") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must not be role-consumable"
                )
            for forbidden_field in (
                "citation_eligible_source_ids",
                "citation_eligibility_refs",
                "author_payload_ref",
            ):
                if packet_projection.get(forbidden_field) not in (
                    None,
                    False,
                    [],
                    (),
                    {},
                ):
                    raise RunKernelTransitionError(
                        "follow-up citation eligibility must not create "
                        f"{forbidden_field}"
                    )
            for closed_field in (
                "citations_rendered",
                "citation_rendering_changed",
                "citation_behavior_changed",
                "citation_formatter_invoked",
                "author_payload_created",
                "author_activation_allowed",
                "analyst_activation_allowed",
                "analyst_handoff_created",
                "economist_activation_allowed",
                "economist_handoff_created",
                "economist_code_execution_allowed",
                "prompt_behavior_changed",
                "product_answer_behavior_changed",
            ):
                if packet_projection.get(closed_field) is not False:
                    raise RunKernelTransitionError(
                        "follow-up citation eligibility must keep "
                        f"{closed_field}=False"
                    )
            if packet_projection.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility must defer Author"
                )
            if self.state.final_answer_authority_projection:
                raise RunKernelTransitionError(
                    "follow-up citation eligibility cannot follow authority "
                    "projection mutation"
                )
            self.state.followup_citation_eligibility_state = citation_state
            self.state.final_answer_packet = packet_projection
            self.state.followup_citation_eligibility_projection = (
                build_followup_citation_eligibility_projection(
                    citation_state=citation_state,
                    packet_projection=packet_projection,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_citation_eligibility_history.append(
                deepcopy(self.state.followup_citation_eligibility_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_citation_eligibility_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_CITATION_SOURCE_HANDOFF:
            observed_handoff_state = r1_observed_handoff_state or _safe_mapping(
                observation.payload.get("followup_citation_source_handoff_state")
            )
            if r1_canonical_record is None:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff preflight did not rebuild "
                    "canonical handoff"
                )
            handoff_state = {
                **r1_canonical_record.to_dict(),
                "owner": "RunKernel.FollowupCitationSourceHandoff",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "observation_id": observed_handoff_state.get("observation_id"),
            }
            flags = _safe_mapping(handoff_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_CITATION_SOURCE_HANDOFF_FALSE_FLAGS,
                context="follow-up citation source handoff",
            )
            for required_flag in (
                "packet_local_citation_eligibility_consumed",
                "citation_source_handoff_created",
                "source_identity_records_created",
            ):
                if flags.get(required_flag) is not True:
                    raise RunKernelTransitionError(
                        "follow-up citation source handoff must set "
                        f"{required_flag}=True"
                    )
            if handoff_state.get("owner") != (
                "RunKernel.FollowupCitationSourceHandoff"
            ):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff requires RunKernel owner"
                )
            if handoff_state.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff requires canonical state"
                )
            if handoff_state.get("trace_only") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff must not be trace-only"
                )
            if handoff_state.get("storage_only") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff must not be storage-only"
                )
            if handoff_state.get("citation_source_handoff_mode") != (
                AG96I3R1_CITATION_SOURCE_HANDOFF_MODE
            ):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff requires AG-96I3R1 mode"
                )
            packet = _safe_mapping(self.state.final_answer_packet)
            if handoff_state.get("packet_id") != packet.get("packet_id"):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff packet mismatch"
                )
            if handoff_state.get("current_final_answer_packet_digest") != (
                followup_projection_digest(packet)
            ):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff FinalAnswerPacket "
                    "digest mismatch"
                )
            if handoff_state.get("source_identity_count", 0) <= 0:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff requires source identities"
                )
            source_records = list(
                handoff_state.get("source_identity_records") or []
            )
            if len(source_records) != handoff_state.get("source_identity_count"):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff source count mismatch"
                )
            source_ids = [
                str(record.get("source_id"))
                for record in source_records
                if record.get("source_id")
            ]
            if source_ids != list(
                handoff_state.get("citation_eligible_source_ids") or []
            ):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff source IDs must match "
                    "identity records"
                )
            citation_refs = list(
                handoff_state.get("citation_eligibility_refs") or []
            )
            if len(citation_refs) != len(source_records):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff citation refs mismatch"
                )
            if self.state.final_answer_authority_projection:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff cannot follow authority "
                    "projection mutation"
                )
            if packet.get("author_input_refs") != {}:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff requires empty "
                    "author_input_refs"
                )
            if packet.get("author_payload_ref") not in (None, False, [], (), {}):
                raise RunKernelTransitionError(
                    "follow-up citation source handoff must not create "
                    "author_payload_ref"
                )
            for closed_field in (
                "canonical_final_answer_packet_mutated",
                "final_answer_packet_updated",
                "final_answer_packet_rebuilt",
                "citations_rendered",
                "citation_formatter_invoked",
                "author_payload_created",
                "author_activation_allowed",
                "analyst_activation_allowed",
                "analyst_handoff_created",
                "economist_activation_allowed",
                "economist_handoff_created",
                "economist_code_execution_allowed",
                "prompt_behavior_changed",
                "product_answer_behavior_changed",
                "ordered_product_source_output_created",
            ):
                if handoff_state.get(closed_field) is not False:
                    raise RunKernelTransitionError(
                        "follow-up citation source handoff must keep "
                        f"{closed_field}=False"
                    )
            if handoff_state.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff must defer Author"
                )
            if handoff_state.get("answer_ready") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation source handoff must keep answer_ready=false"
                )
            self.state.followup_citation_source_handoff_state = handoff_state
            self.state.followup_citation_source_handoff_projection = (
                build_followup_citation_source_handoff_projection(
                    handoff_state=handoff_state,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_citation_source_handoff_history.append(
                deepcopy(self.state.followup_citation_source_handoff_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_citation_source_handoff_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_CITATION_RENDERING:
            observed_rendering_state = t1_observed_rendering_state or _safe_mapping(
                observation.payload.get("followup_citation_rendering_state")
            )
            if t1_canonical_record is None:
                raise RunKernelTransitionError(
                    "follow-up citation rendering preflight did not rebuild "
                    "canonical rendering"
                )
            rendering_state = {
                **t1_canonical_record.to_dict(),
                "owner": "RunKernel.FollowupCitationRendering",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "observation_id": observed_rendering_state.get("observation_id"),
            }
            flags = _safe_mapping(rendering_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_CITATION_RENDERING_FALSE_FLAGS,
                context="follow-up citation rendering",
            )
            for required_flag in (
                "packet_local_citation_eligibility_consumed",
                "citation_source_handoff_consumed",
                "r1_source_identity_records_consumed",
                "machine_readable_rendered_source_entries_created",
            ):
                if flags.get(required_flag) is not True:
                    raise RunKernelTransitionError(
                        "follow-up citation rendering must set "
                        f"{required_flag}=True"
                    )
            if rendering_state.get("owner") != "RunKernel.FollowupCitationRendering":
                raise RunKernelTransitionError(
                    "follow-up citation rendering requires RunKernel owner"
                )
            if rendering_state.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation rendering requires canonical state"
                )
            if rendering_state.get("trace_only") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation rendering must not be trace-only"
                )
            if rendering_state.get("storage_only") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation rendering must not be storage-only"
                )
            if rendering_state.get("citation_rendering_mode") != (
                AG96I3T1_CITATION_RENDERING_MODE
            ):
                raise RunKernelTransitionError(
                    "follow-up citation rendering requires AG-96I3T1 mode"
                )
            packet = _safe_mapping(self.state.final_answer_packet)
            if rendering_state.get("packet_id") != packet.get("packet_id"):
                raise RunKernelTransitionError(
                    "follow-up citation rendering packet mismatch"
                )
            if rendering_state.get("current_final_answer_packet_digest") != (
                followup_projection_digest(packet)
            ):
                raise RunKernelTransitionError(
                    "follow-up citation rendering FinalAnswerPacket digest mismatch"
                )
            r1_state = self.state.followup_citation_source_handoff_state
            if rendering_state.get("citation_source_handoff_id") != (
                r1_state.get("citation_source_handoff_id")
            ):
                raise RunKernelTransitionError(
                    "follow-up citation rendering R1 handoff mismatch"
                )
            if rendering_state.get("followup_citation_source_handoff_digest") != (
                followup_projection_digest(r1_state)
            ):
                raise RunKernelTransitionError(
                    "follow-up citation rendering R1 digest mismatch"
                )
            source_records = list(r1_state.get("source_identity_records") or [])
            rendered_entries = list(rendering_state.get("rendered_source_entries") or [])
            if not rendered_entries:
                raise RunKernelTransitionError(
                    "follow-up citation rendering requires rendered source entries"
                )
            if len(rendered_entries) != len(source_records):
                raise RunKernelTransitionError(
                    "follow-up citation rendering rendered entry count mismatch"
                )
            rendered_source_ids = [
                str(entry.get("source_id"))
                for entry in rendered_entries
                if entry.get("source_id")
            ]
            r1_source_ids = [
                str(record.get("source_id"))
                for record in source_records
                if record.get("source_id")
            ]
            if rendered_source_ids != r1_source_ids:
                raise RunKernelTransitionError(
                    "follow-up citation rendering source IDs must match R1 identities"
                )
            if rendering_state.get("rendered_source_entry_count") != (
                len(rendered_entries)
            ):
                raise RunKernelTransitionError(
                    "follow-up citation rendering rendered count mismatch"
                )
            if not rendering_state.get("rendered_source_entry_digest"):
                raise RunKernelTransitionError(
                    "follow-up citation rendering requires rendered digest"
                )
            if self.state.final_answer_authority_projection:
                raise RunKernelTransitionError(
                    "follow-up citation rendering cannot follow authority "
                    "projection mutation"
                )
            if packet.get("author_input_refs") != {}:
                raise RunKernelTransitionError(
                    "follow-up citation rendering requires empty author_input_refs"
                )
            if packet.get("author_payload_ref") not in (None, False, [], (), {}):
                raise RunKernelTransitionError(
                    "follow-up citation rendering must not create author_payload_ref"
                )
            for closed_field in (
                "canonical_final_answer_packet_mutated",
                "final_answer_packet_updated",
                "final_answer_packet_rebuilt",
                "citations_rendered",
                "citation_formatter_invoked",
                "author_payload_created",
                "author_activation_allowed",
                "analyst_activation_allowed",
                "analyst_handoff_created",
                "economist_activation_allowed",
                "economist_handoff_created",
                "economist_code_execution_allowed",
                "prompt_behavior_changed",
                "product_answer_behavior_changed",
                "ordered_product_source_output_created",
            ):
                if rendering_state.get(closed_field) is not False:
                    raise RunKernelTransitionError(
                        "follow-up citation rendering must keep "
                        f"{closed_field}=False"
                    )
            if rendering_state.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up citation rendering must defer Author"
                )
            if rendering_state.get("answer_ready") is not False:
                raise RunKernelTransitionError(
                    "follow-up citation rendering must keep answer_ready=false"
                )
            self.state.followup_citation_rendering_state = rendering_state
            self.state.followup_citation_rendering_projection = (
                build_followup_citation_rendering_projection(
                    rendering_state=rendering_state,
                    behavior_boundary_flags=flags,
                )
            )
            self.state.followup_citation_rendering_history.append(
                deepcopy(self.state.followup_citation_rendering_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_citation_rendering_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_INPUT_AUTHORITY:
            self.state.followup_author_input_authority_state = u1_authority_state
            self.state.followup_author_input_authority_projection = (
                u1_authority_projection
            )
            self.state.followup_author_input_authority_history.append(
                deepcopy(u1_authority_projection)
            )
            self.state.final_answer_authority_projection = deepcopy(
                u1_authority_projection
            )
            self.state.final_answer_packet = u1_packet_projection
            self.state.projections[FINAL_ANSWER_PACKET_STAGE] = deepcopy(
                self.state.final_answer_authority_projection
            )
            self.state.projections[action.stage] = deepcopy(u1_authority_projection)
        elif (
            action.action_type
            is ActionType.FOLLOWUP_FINAL_ANSWER_PACKET_PREPARE
        ):
            observed_packet_state = _safe_mapping(
                observation.payload.get("followup_final_answer_packet_state")
            )
            if not observed_packet_state:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket observation requires "
                    "followup_final_answer_packet_state"
                )
            if not self.state.followup_sufficiency_recheck_state:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket requires existing recheck state"
                )
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_final_answer_packet_observation_binding,
                action_inputs=action_inputs,
                observed_packet_state=observed_packet_state,
            )
            ledger_projection = self.state.evidence_ledger.to_projection().to_dict()
            try:
                canonical_record = build_followup_final_answer_packet_record(
                    action_inputs=action_inputs,
                    followup_sufficiency_recheck_state=(
                        self.state.followup_sufficiency_recheck_state
                    ),
                    sufficiency_judgment_projection=(
                        self.state.sufficiency_judgment_projection
                    ),
                    evidence_ledger_projection=ledger_projection,
                    followup_evidence_intake_state=(
                        self.state.followup_evidence_intake_state
                    ),
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            packet_state = {
                **canonical_record.to_dict(),
                "owner": "RunKernel.FollowupFinalAnswerPacket",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
            }
            packet_projection = _safe_mapping(packet_state.get("packet_projection"))
            if not packet_projection:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket requires packet_projection"
                )
            flags = _safe_mapping(packet_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_PACKET_FALSE_FLAGS,
                context="follow-up FinalAnswerPacket",
            )
            if flags.get("final_answer_packet_prepared") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must prepare packet state"
                )
            if flags.get("final_answer_packet_updated") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must update packet projection"
                )
            if flags.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must keep Author closed"
                )
            if flags.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must defer Author execution"
                )
            if flags.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up FinalAnswerPacket must not run live validation"
                )
            self.state.followup_final_answer_packet_state = packet_state
            citation_eligible = list(packet_projection.get("citation_eligible") or [])
            citation_eligible_source_ids = [
                item.get("source_id")
                for item in citation_eligible
                if isinstance(item, Mapping) and item.get("source_id") is not None
            ]
            author_payload_ref = {
                "packet_id": packet_projection.get("packet_id"),
                "status": "author_execution_deferred",
                "prompt_text_included": False,
                "fixture_only": True,
                "author_activation_allowed": False,
                "author_execution_deferred": True,
                "not_for_product_answer_activation": True,
                "citation_formatter_invoked": False,
            }
            self.state.final_answer_packet = packet_projection
            self.state.final_answer_authority_projection = (
                build_final_answer_authority_projection(
                    packet_state=packet_state,
                    packet_projection=packet_projection,
                    author_payload_ref=author_payload_ref,
                    citation_eligible_source_ids=citation_eligible_source_ids,
                )
            )
            self.state.projections[FINAL_ANSWER_PACKET_STAGE] = deepcopy(
                self.state.final_answer_authority_projection
            )
            self.state.followup_final_answer_packet_projection = (
                build_followup_final_answer_packet_projection(
                    packet_state=packet_state,
                    packet_projection=packet_projection,
                    behavior_boundary_flags=flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                )
            )
            self.state.followup_final_answer_packet_history.append(
                deepcopy(self.state.followup_final_answer_packet_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_final_answer_packet_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_GATE:
            observed_gate_state = _safe_mapping(
                observation.payload.get("followup_author_gate_state")
            )
            if not observed_gate_state:
                raise RunKernelTransitionError(
                    "follow-up Author gate observation requires "
                    "followup_author_gate_state"
                )
            action_inputs = _safe_mapping(action.inputs)
            if action_inputs.get("author_gate_mode") == (
                AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
            ):
                if v1_canonical_gate_record is None:
                    raise RunKernelTransitionError(
                        "V1 Author gate canonical record was not validated"
                    )
                canonical_record = v1_canonical_gate_record
            else:
                if not self.state.followup_final_answer_packet_state:
                    raise RunKernelTransitionError(
                        "follow-up Author gate requires existing packet state"
                    )
                _followup_checked(
                    validate_followup_author_gate_observation_binding,
                    action_inputs=action_inputs,
                    observed_gate_state=observed_gate_state,
                )
                try:
                    canonical_record = build_followup_author_gate_record(
                        action_inputs=action_inputs,
                        followup_final_answer_packet_state=(
                            self.state.followup_final_answer_packet_state
                        ),
                        final_answer_packet=self.state.final_answer_packet,
                        final_answer_authority_projection=(
                            self.state.final_answer_authority_projection
                        ),
                    )
                except (PermissionError, ValueError) as exc:
                    raise RunKernelTransitionError(str(exc)) from exc
            gate_state = {
                **canonical_record.to_dict(),
                "owner": "RunKernel.FollowupAuthorGate",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
            }
            flags = _safe_mapping(gate_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_AUTHOR_GATE_FALSE_FLAGS,
                context="follow-up Author gate",
            )
            if gate_state.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate must consume packet authority"
                )
            if flags.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate flags must consume packet authority"
                )
            if gate_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author gate must keep Author activation closed"
                )
            if gate_state.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate must defer Author execution"
                )
            if action_inputs.get("author_gate_mode") == (
                AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
            ):
                if gate_state.get("author_input_authority_consumed") is not True:
                    raise RunKernelTransitionError(
                        "V1 Author gate must consume U1 authority"
                    )
                if flags.get("author_input_authority_consumed") is not True:
                    raise RunKernelTransitionError(
                        "V1 Author gate flags must consume U1 authority"
                    )
                if gate_state.get("author_gate_consumed") is not True:
                    raise RunKernelTransitionError(
                        "V1 Author gate must record gate consumption"
                    )
                if gate_state.get("author_execution_allowed") is not False:
                    raise RunKernelTransitionError(
                        "V1 Author gate must keep Author execution disallowed"
                    )
                if gate_state.get("prompt_text_included") is not False:
                    raise RunKernelTransitionError(
                        "V1 Author gate must not include prompt text"
                    )
                if gate_state.get("product_answer_ready") is not False:
                    raise RunKernelTransitionError(
                        "V1 Author gate must not ready product answer"
                    )
            if gate_state.get("final_text_included") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author gate must not include final text"
                )
            if gate_state.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author gate must not run live validation"
                )
            self.state.followup_author_gate_state = gate_state
            self.state.followup_author_gate_projection = (
                build_followup_author_gate_projection(
                    gate_state=gate_state,
                    behavior_boundary_flags=flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                )
            )
            self.state.followup_author_gate_history.append(
                deepcopy(self.state.followup_author_gate_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_gate_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS:
            self.state.followup_author_execution_readiness_state = (
                w_canonical_readiness_state
            )
            self.state.followup_author_execution_readiness_projection = (
                build_followup_author_execution_readiness_projection(
                    readiness_state=w_canonical_readiness_state,
                    behavior_boundary_flags=w_readiness_flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                    followup_author_gate_stage=FOLLOWUP_AUTHOR_GATE_STAGE,
                    followup_author_input_authority_stage=(
                        FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE
                    ),
                )
            )
            self.state.followup_author_execution_readiness_history.append(
                deepcopy(self.state.followup_author_execution_readiness_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_execution_readiness_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION:
            self.state.followup_author_input_materialization_state = (
                x_canonical_materialization_state
            )
            self.state.followup_author_input_materialization_projection = (
                build_followup_author_input_materialization_projection(
                    materialization_state=x_canonical_materialization_state,
                    behavior_boundary_flags=x_materialization_flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                    followup_author_execution_readiness_stage=(
                        FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE
                    ),
                    followup_author_gate_stage=FOLLOWUP_AUTHOR_GATE_STAGE,
                    followup_author_input_authority_stage=(
                        FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE
                    ),
                )
            )
            self.state.followup_author_input_materialization_history.append(
                deepcopy(self.state.followup_author_input_materialization_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_input_materialization_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION:
            self.state.final_answer_packet = y_packet_projection
            self.state.final_answer_authority_projection = y_authority_projection
            self.state.followup_author_execution_activation_state = (
                y_canonical_activation_state
            )
            self.state.followup_author_execution_activation_projection = (
                build_followup_author_execution_activation_projection(
                    activation_state=y_canonical_activation_state,
                    behavior_boundary_flags=y_activation_flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                    followup_author_input_materialization_stage=(
                        FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE
                    ),
                    followup_author_execution_readiness_stage=(
                        FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE
                    ),
                    followup_author_gate_stage=FOLLOWUP_AUTHOR_GATE_STAGE,
                    followup_author_input_authority_stage=(
                        FOLLOWUP_AUTHOR_INPUT_AUTHORITY_STAGE
                    ),
                )
            )
            self.state.followup_author_execution_activation_history.append(
                deepcopy(self.state.followup_author_execution_activation_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_execution_activation_projection
            )
        elif (
            action.action_type
            is ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST
        ):
            self.state.final_answer_packet = z_packet_projection
            self.state.final_answer_authority_projection = z_authority_projection
            self.state.followup_author_prompt_assembly_manifest_state = (
                z_canonical_manifest_state
            )
            self.state.followup_author_prompt_assembly_manifest_projection = (
                z_manifest_projection
            )
            self.state.followup_author_prompt_assembly_manifest_history.append(
                deepcopy(
                    self.state.followup_author_prompt_assembly_manifest_projection
                )
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_prompt_assembly_manifest_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY:
            self.state.final_answer_packet = ac_packet_projection
            self.state.final_answer_authority_projection = ac_authority_projection
            self.state.followup_author_payload_authority_state = (
                ac_canonical_payload_authority_state
            )
            self.state.followup_author_payload_authority_projection = (
                ac_payload_authority_projection
            )
            self.state.followup_author_payload_authority_history.append(
                deepcopy(self.state.followup_author_payload_authority_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_payload_authority_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION:
            self.state.final_answer_packet = ad_packet_projection
            self.state.final_answer_authority_projection = ad_authority_projection
            self.state.followup_author_payload_construction_state = (
                ad_canonical_payload_construction_state
            )
            self.state.followup_author_payload_construction_projection = (
                ad_payload_construction_projection
            )
            self.state.followup_author_payload_construction_history.append(
                deepcopy(self.state.followup_author_payload_construction_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_payload_construction_projection
            )
        elif (
            action.action_type
            is ActionType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE
        ):
            self.state.final_answer_packet = af4b2_packet_projection
            self.state.final_answer_authority_projection = (
                af4b2_authority_projection
            )
            self.state.followup_author_evidence_content_bridge_state = (
                af4b2_canonical_bridge_state
            )
            self.state.followup_author_evidence_content_bridge_projection = (
                af4b2_bridge_projection
            )
            self.state.followup_author_evidence_content_bridge_history.append(
                deepcopy(
                    self.state.followup_author_evidence_content_bridge_projection
                )
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_evidence_content_bridge_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AD:
            self.state.final_answer_packet = ae_packet_projection
            self.state.final_answer_authority_projection = ae_authority_projection
            self.state.author_observation = ae_author_observation
            self.state.final_answer_outcome = ae_final_answer_outcome
            self.state.followup_author_execution_from_ad_state = (
                ae_canonical_execution_state
            )
            self.state.followup_author_execution_from_ad_projection = (
                ae_execution_projection
            )
            self.state.followup_author_execution_from_ad_history.append(
                deepcopy(self.state.followup_author_execution_from_ad_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_execution_from_ad_projection
            )
        elif (
            action.action_type
            is ActionType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION
        ):
            self.state.final_answer_packet = af4_packet_projection
            self.state.final_answer_authority_projection = af4_authority_projection
            self.state.followup_author_invocation_construction_state = (
                af4_canonical_invocation_state
            )
            self.state.followup_author_invocation_construction_projection = (
                af4_invocation_projection
            )
            self.state.followup_author_invocation_construction_history.append(
                deepcopy(
                    self.state.followup_author_invocation_construction_projection
                )
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_invocation_construction_projection
            )
        elif (
            action.action_type
            is ActionType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY
        ):
            self.state.followup_author_model_request_assembly_state = (
                af4d_canonical_model_request_state
            )
            self.state.followup_author_model_request_assembly_projection = (
                af4d_model_request_projection
            )
            self.state.followup_author_model_request_assembly_history.append(
                deepcopy(
                    self.state.followup_author_model_request_assembly_projection
                )
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_model_request_assembly_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D:
            self.state.followup_author_execution_from_af4d_state = (
                af5a_canonical_execution_state
            )
            self.state.followup_author_execution_from_af4d_projection = (
                af5a_execution_projection
            )
            self.state.followup_author_execution_from_af4d_history.append(
                deepcopy(self.state.followup_author_execution_from_af4d_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_execution_from_af4d_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE:
            self.state.author_observation = af5b_author_observation
            self.state.final_answer_outcome = af5b_final_answer_outcome
            self.state.followup_author_response_finalization_state = (
                af5b_canonical_finalization_state
            )
            self.state.followup_author_response_finalization_projection = (
                af5b_finalization_projection
            )
            self.state.followup_author_response_finalization_history.append(
                deepcopy(
                    self.state.followup_author_response_finalization_projection
                )
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_response_finalization_projection
            )
        elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION:
            observed_author_state = _safe_mapping(
                observation.payload.get("followup_author_observation_state")
            )
            if not observed_author_state:
                raise RunKernelTransitionError(
                    "follow-up Author observation requires "
                    "followup_author_observation_state"
                )
            if not self.state.followup_author_gate_state:
                raise RunKernelTransitionError(
                    "follow-up Author observation requires existing Author gate state"
                )
            try:
                reject_followup_author_observation_boundary_spoof(
                    observed_author_state
                )
            except PermissionError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            action_inputs = _safe_mapping(action.inputs)
            _followup_checked(
                validate_followup_author_observation_binding,
                action_inputs=action_inputs,
                observed_author_state=observed_author_state,
            )
            observed_output_facts = _safe_mapping(
                observed_author_state.get("observed_output_facts")
            )
            if not observed_output_facts:
                raise RunKernelTransitionError(
                    "follow-up Author observation requires sanitized output facts"
                )
            try:
                canonical_record = build_followup_author_observation_record(
                    action_inputs=action_inputs,
                    followup_author_gate_state=self.state.followup_author_gate_state,
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    observed_output_facts=observed_output_facts,
                )
                compliance = derive_followup_author_observation_compliance(
                    final_answer_packet=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                    followup_author_gate_state=self.state.followup_author_gate_state,
                    observed_output_facts=observed_output_facts,
                )
            except (PermissionError, ValueError) as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            author_state = {
                **canonical_record.to_dict(),
                **compliance,
                "owner": "RunKernel.FollowupAuthorObservation",
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
            }
            flags = _safe_mapping(author_state.get("behavior_boundary_flags"))
            _followup_checked(
                require_followup_flags_false,
                flags,
                _FOLLOWUP_AUTHOR_OBSERVATION_FALSE_FLAGS,
                context="follow-up Author observation",
            )
            if author_state.get("author_output_observed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must observe Author output facts"
                )
            if author_state.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must consume packet authority"
                )
            if flags.get("author_output_observed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation flags must record output observation"
                )
            if flags.get("packet_authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation flags must consume packet authority"
                )
            if author_state.get("author_activation_allowed") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author observation must keep Author activation closed"
                )
            if author_state.get("author_execution_deferred") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must defer Author execution"
                )
            if author_state.get("final_text_included") is not False:
                raise RunKernelTransitionError(
                    "follow-up Author observation must not retain final text"
                )
            if author_state.get("live_validation_not_run") is not True:
                raise RunKernelTransitionError(
                    "follow-up Author observation must not run live validation"
                )
            self.state.followup_author_observation_state = author_state
            self.state.followup_author_observation_projection = (
                build_followup_author_observation_projection(
                    author_state=author_state,
                    behavior_boundary_flags=flags,
                    final_answer_packet_stage=FINAL_ANSWER_PACKET_STAGE,
                    followup_author_gate_stage=FOLLOWUP_AUTHOR_GATE_STAGE,
                )
            )
            self.state.followup_author_observation_history.append(
                deepcopy(self.state.followup_author_observation_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                self.state.followup_author_observation_projection
            )
        else:
            self.state.projections[action.stage] = _safe_mapping(observation.payload)
        self.state.observations.append(observation)
        self.state.next_observation_sequence += 1
        return self.state

    def trace_projection(self) -> KernelTraceProjection:
        return self.state.to_trace_projection()

    def to_trace_fragment(self) -> dict[str, Any]:
        return self.trace_projection().to_trace_fragment()


def validate_authorized_action(
    action: AuthorizedAction | None,
    *,
    action_type: ActionType | str,
    stage: str,
    expected_observation_type: ObservationType | str | None = None,
) -> AuthorizedAction:
    if not isinstance(action, AuthorizedAction):
        raise ValueError("executor requires an AuthorizedAction")
    action.validate(
        action_type=action_type,
        stage=stage,
        expected_observation_type=expected_observation_type,
    )
    return action


def _followup_checked(callable_: Any, /, *args: Any, **kwargs: Any) -> Any:
    try:
        return callable_(*args, **kwargs)
    except FollowupRunKernelReducerError as exc:
        raise RunKernelTransitionError(str(exc)) from exc


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_text(item, limit=180)
        if text:
            token = text.casefold().replace("-", "_").replace(" ", "_")
            if token not in out:
                out.append(token)
    return out


def _positive_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _require_followup_provider_job_budget(
    *,
    authorization_state: Mapping[str, Any],
    budget_debit: Mapping[str, Any],
) -> None:
    required = {
        "cost_points": budget_debit.get("cost_points"),
        "provider_calls": budget_debit.get("provider_calls"),
        "fetches_reserved": budget_debit.get("fetches_reserved"),
        "read_units_reserved": budget_debit.get("read_units_reserved"),
        "followup_rounds": budget_debit.get("followup_rounds"),
    }
    exhausted = [name for name, value in required.items() if _positive_int(value) <= 0]
    if exhausted:
        raise RunKernelTransitionError(
            "follow-up provider-job execution requires authorized budget debit for "
            + ", ".join(exhausted)
        )
    for decision in authorization_state.get("consumed_budget_decisions", []) or []:
        if not isinstance(decision, Mapping):
            continue
        if decision.get("debit_authorized_for_future_phase") is not True:
            continue
        planned = _safe_mapping(decision.get("planned_or_denied_debit"))
        if all(
            _positive_int(planned.get(name)) == _positive_int(budget_debit.get(name))
            for name in required
        ):
            return
    raise RunKernelTransitionError(
        "follow-up provider-job execution requires budget authorized by sealed state"
    )


def _canonical_followup_provider_job_budget_semantics(
    budget_debit: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "planned_debit_authorized": dict(budget_debit),
        "offline_provider_job_execution_did_not_incur_live_cost": True,
        "actual_provider_search_fetch_read_cost_incurred": False,
        "actual_provider_account_debited": False,
        "provider_cost_accounting_deferred": True,
    }


def _canonical_followup_provider_job_execution_gate() -> dict[str, Any]:
    return {
        "allowed_execution_mode": FOLLOWUP_PROVIDER_JOB_OFFLINE_EXECUTION_MODE,
        "provider_job_kind_allowlist": [FOLLOWUP_PROVIDER_JOB_ALLOWED_KIND],
        "provider_execution_licensed": False,
        "provider_execution_available_in_this_phase": False,
        "offline_live_shaped_execution": True,
        "adapter_result_injected_required": True,
        "reason": FOLLOWUP_PROVIDER_JOB_EXECUTION_GATE_REASON,
    }


def _canonical_followup_provider_job_redaction_posture() -> dict[str, bool]:
    return {
        "sanitized_candidate_facts_only": True,
        "raw_provider_payloads_retained": False,
        "raw_provider_payload_retained": False,
        "raw_text_retained": False,
        "raw_prompt_retained": False,
        "raw_trace_retained": False,
        "provider_payload_retained": False,
        "provider_payloads_retained": False,
        "secrets_retained": False,
        "db_rows_retained": False,
        "cache_rows_retained": False,
        "private_logs_retained": False,
        "full_trace_retained": False,
    }


def _followup_provider_job_closed_surface_claimed(value: Any) -> bool:
    dangerous_true_keys = {
        "source_obligation_satisfied",
        "final_evidence_satisfied",
        "citation_eligible",
        "sufficiency_ready",
        "sufficiency_judgment_ready",
        "final_answer_packet_ready",
        "author_activation_allowed",
        "author_executor_invoked",
        "citation_rendered",
        "citation_rendering_changed",
        "citation_formatter_invoked",
        "product_answer_behavior_changed",
        "final_answer_behavior_changed",
        "query_generation_changed",
        "query_mutation_changed",
        "provider_routing_changed",
        "provider_selection_changed",
        "provider_depth_changed",
        "search_depth_changed",
        "retrieval_ranking_filtering_changed",
        "raw_payload_retained",
        "raw_text_retained",
        "provider_payload_retained",
    }
    dangerous_false_keys = {
        "live_validation_not_run",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")
            if token in {
                "budget_semantics",
                "execution_gate",
                "redaction_posture",
            }:
                continue
            if token in dangerous_true_keys and item is True:
                return True
            if token in dangerous_false_keys and item is False:
                return True
            if _followup_provider_job_closed_surface_claimed(item):
                return True
    elif isinstance(value, (list, tuple, set, frozenset)):
        return any(_followup_provider_job_closed_surface_claimed(item) for item in value)
    return False


def _canonical_sufficiency_judgment_projection(
    *,
    judgment_projection: Mapping[str, Any],
    validation: Mapping[str, Any],
    observation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    validation_mapping = _safe_mapping(validation)
    judgment_validation = _safe_mapping(judgment_projection.get("validation"))
    return {
        "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "schema_version": judgment_projection.get("schema_version"),
        "judgment_id": judgment_projection.get("judgment_id"),
        "decision": judgment_projection.get("decision"),
        "mode": judgment_projection.get("mode"),
        "contract_id": judgment_projection.get("contract_id"),
        "selected_template_ids": judgment_projection.get(
            "selected_template_ids",
            [],
        ),
        "contract_fulfilled": judgment_projection.get("contract_fulfilled"),
        "required_obligations_satisfied": judgment_projection.get(
            "required_obligations_satisfied"
        ),
        "missing_required_obligations": judgment_projection.get(
            "missing_required_obligations",
            [],
        ),
        "partial_obligations": judgment_projection.get(
            "partial_obligations",
            [],
        ),
        "satisfied_obligations": judgment_projection.get(
            "satisfied_obligations",
            [],
        ),
        "unresolved_conflicts": judgment_projection.get(
            "unresolved_conflicts",
            [],
        ),
        "indirect_inference_claims": judgment_projection.get(
            "indirect_inference_claims",
            [],
        ),
        "source_bound_numeric_unknowns": judgment_projection.get(
            "source_bound_numeric_unknowns",
            [],
        ),
        "source_bound_numeric_resolutions": judgment_projection.get(
            "source_bound_numeric_resolutions",
            [],
        ),
        "weak_or_thin_evidence": judgment_projection.get(
            "weak_or_thin_evidence",
            [],
        ),
        "failure_card_authorized": judgment_projection.get(
            "failure_card_authorized"
        ),
        "final_answer_allowed": judgment_projection.get("final_answer_allowed"),
        "final_answer_posture": judgment_projection.get("final_answer_posture"),
        "mandatory_caveats": judgment_projection.get("mandatory_caveats", []),
        "prohibited_upgrades": judgment_projection.get("prohibited_upgrades", []),
        "readiness_reasons": judgment_projection.get("readiness_reasons", []),
        "semantic_consumption": judgment_projection.get("semantic_consumption", {}),
        "semantic_state_facts_summary": judgment_projection.get(
            "semantic_state_facts_summary",
            {},
        ),
        "final_packet_inputs": judgment_projection.get("final_packet_inputs", {}),
        "rationale": judgment_projection.get("rationale"),
        "validation_status": validation_mapping.get("status")
        or judgment_validation.get("status"),
        "prompt_hash": validation_mapping.get("prompt_hash")
        or observation_payload.get("prompt_hash"),
        "prompt_length": validation_mapping.get("prompt_length")
        or observation_payload.get("prompt_length"),
        "model_identity": {
            "provider": validation_mapping.get("provider"),
            "model": validation_mapping.get("model"),
            "effort": validation_mapping.get("effort"),
            "use_reasoning": validation_mapping.get("use_reasoning"),
        },
        "prompt_text_retained": False,
        "model_response_text_retained": False,
        "provider_payload_retained": False,
    }


__all__ = [
    "AUTHOR_EXECUTION_STAGE",
    "FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_AUTHORIZATION_STAGE",
    "FOLLOWUP_EVIDENCE_INTAKE_STAGE",
    "FOLLOWUP_EXECUTION_STAGE",
    "FOLLOWUP_PROVIDER_JOB_EXECUTION_STAGE",
    "FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE",
    "FOLLOWUP_AUTHOR_EXECUTION_ACTIVATION_STAGE",
    "FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE",
    "FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE",
    "FOLLOWUP_AUTHOR_PAYLOAD_CONSTRUCTION_STAGE",
    "FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE",
    "FOLLOWUP_AUTHOR_EXECUTION_FROM_AD_STAGE",
    "FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE",
    "FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE",
    "FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE",
    "FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE",
    "FOLLOWUP_AUTHOR_INPUT_MATERIALIZATION_STAGE",
    "FOLLOWUP_AUTHOR_GATE_STAGE",
    "FOLLOWUP_AUTHOR_OBSERVATION_STAGE",
    "FOLLOWUP_BLOCKED_FINAL_ANSWER_PACKET_SHELL_STAGE",
    "FOLLOWUP_CITATION_ELIGIBILITY_STAGE",
    "FOLLOWUP_CITATION_RENDERING_STAGE",
    "FOLLOWUP_CITATION_SOURCE_HANDOFF_STAGE",
    "FOLLOWUP_FINAL_EVIDENCE_SELECTION_STAGE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_READINESS_STAGE",
    "FOLLOWUP_FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_SUFFICIENCY_RECHECK_STAGE",
    "MAIN_RETRIEVAL_STAGE",
    "EVIDENCE_LEDGER_STAGE",
    "SEARCH_JUDGMENT_STAGE",
    "SEARCH_WORK_PLAN_CONSTRUCTION_STAGE",
    "SUFFICIENCY_JUDGMENT_STAGE",
    "RUN_CONTRACT_STAGE",
    "QUERY_PRODUCTION_STAGE",
    "QUERY_PLAN_ADMISSION_STAGE",
    "RETRIEVAL_STOP_CHECKPOINT_STAGE",
    "ROUTE_REQUEST_STAGE",
    "RUN_KERNEL_TRACE_KEY",
    "SEMANTIC_PRODUCER_BUNDLE_COMMIT_REASON",
    "SEMANTIC_PRODUCER_BUNDLE_COMMIT_STAGE",
    "ActionType",
    "AuthorizedAction",
    "KernelTraceProjection",
    "Observation",
    "ObservationType",
    "RunKernel",
    "RunKernelTransitionError",
    "RunStageStatus",
    "RunState",
    "validate_authorized_action",
]
