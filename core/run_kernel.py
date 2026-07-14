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
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from core.author_prose_finalization_runtime import (
    AUTHOR_PROSE_FINALIZATION_REASON,
    AuthorProseFinalizationRuntimeError,
    build_author_prose_finalization_action_inputs,
    build_author_prose_finalization_projection,
    build_author_prose_finalization_state,
)
from core.author_prose_finalization_runtime import (
    AUTHOR_PROSE_FINALIZATION_STAGE as AUTHOR_PROSE_FINALIZATION_STAGE_NAME,
)
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
from core.contract_amendment_application_runtime import (
    CONTRACT_AMENDMENT_APPLICATION_REASON,
    ContractAmendmentApplicationError,
    build_contract_amendment_application_projection,
    build_contract_amendment_application_state,
    build_current_answer_contract_projection,
)
from core.contract_amendment_application_runtime import (
    CONTRACT_AMENDMENT_APPLICATION_STAGE as CONTRACT_AMENDMENT_APPLICATION_STAGE_NAME,
)
from core.evidence_ledger import EvidenceLedger
from core.final_answer_packet import _safe_json
from core.final_answer_packet_hardening_runtime import (
    FINAL_ANSWER_PACKET_HARDENING_REASON,
    FinalAnswerPacketHardeningRuntimeError,
    build_final_answer_packet_hardening_action_inputs,
    build_hardened_final_answer_packet_projection,
    build_hardened_final_answer_packet_state,
)
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
from core.followup_search_authorization_runtime import (
    FOLLOWUP_SEARCH_AUTHORIZATION_REASON,
    FollowupSearchAuthorizationRuntimeError,
    build_followup_search_authorization_action_inputs,
    build_followup_search_authorization_projection,
    build_followup_search_authorization_state,
)
from core.followup_search_authorization_runtime import (
    FOLLOWUP_SEARCH_AUTHORIZATION_STAGE as FOLLOWUP_SEARCH_AUTHORIZATION_STAGE_NAME,
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
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_DEFAULT_PROVIDER_CALL_CAP,
    LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP,
    LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP,
    LIVE_SEARCH_VALIDATION_MAX_SELECTED_TASKS,
    LIVE_SEARCH_VALIDATION_REASON,
    LIVE_SEARCH_VALIDATION_SCHEMA_VERSION,
    LiveSearchValidationRuntimeError,
    build_live_search_validation_projection,
    build_live_search_validation_state,
)
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_STAGE as LIVE_SEARCH_VALIDATION_STAGE_NAME,
)
from core.live_search_validation_runtime import (
    contract_ref_from_contract as _live_validation_contract_ref_from_contract,
)
from core.live_search_validation_runtime import (
    handoff_ref_from_handoff_state as _live_validation_handoff_ref_from_handoff_state,
)
from core.scout_disambiguation_runtime import (
    SCOUT_DISAMBIGUATION_REASON,
    SCOUT_DISAMBIGUATION_SCHEMA_VERSION,
    SCOUT_MAX_DIMENSIONS_PER_COMPONENT,
    SCOUT_MAX_QUERIES_PER_COMPONENT,
    ScoutDisambiguationRuntimeError,
    build_scout_disambiguation_report_projection,
    build_scout_disambiguation_report_state,
    planner_ref_from_search_planner_state,
)
from core.scout_disambiguation_runtime import (
    SCOUT_DISAMBIGUATION_STAGE as SCOUT_DISAMBIGUATION_STAGE_NAME,
)
from core.scout_disambiguation_runtime import (
    contract_ref_from_contract as _scout_contract_ref_from_contract,
)
from core.scrutineer_review_runtime import (
    SCRUTINEER_REVIEW_REASON,
    ScrutineerReviewRuntimeError,
    build_scrutineer_review_action_inputs,
    build_scrutineer_review_projection,
    build_scrutineer_review_state,
)
from core.scrutineer_review_runtime import (
    SCRUTINEER_REVIEW_STAGE as SCRUTINEER_REVIEW_STAGE_NAME,
)
from core.search_executor_handoff_runtime import (
    SEARCH_EXECUTOR_HANDOFF_REASON,
    SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
    SearchExecutorHandoffRuntimeError,
    build_search_executor_handoff_projection,
    build_search_executor_handoff_state,
)
from core.search_executor_handoff_runtime import (
    SEARCH_EXECUTOR_HANDOFF_STAGE as SEARCH_EXECUTOR_HANDOFF_STAGE_NAME,
)
from core.search_executor_handoff_runtime import (
    contract_ref_from_contract as _handoff_contract_ref_from_contract,
)
from core.search_planner_revision_runtime import (
    SEARCH_PLANNER_REVISION_REASON,
    SEARCH_PLANNER_REVISION_SCHEMA_VERSION,
    SearchPlannerRevisionRuntimeError,
    build_search_planner_revision_projection,
    build_search_planner_revision_state,
    revision_ref_from_revision_state,
    scout_ref_from_scout_report_state,
)
from core.search_planner_revision_runtime import (
    SEARCH_PLANNER_REVISION_STAGE as SEARCH_PLANNER_REVISION_STAGE_NAME,
)
from core.search_planner_revision_runtime import (
    contract_ref_from_contract as _revision_contract_ref_from_contract,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_PRODUCTION_REASON,
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerRuntimeError,
    build_search_planner_proposal_projection,
    build_search_planner_proposal_state,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_PRODUCTION_STAGE as SEARCH_PLANNER_PRODUCTION_STAGE_NAME,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as _search_planner_contract_ref_from_contract,
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
from core.single_relation_source_obligation_recovery_authorization import (
    build_single_relation_source_obligation_recovery_authorization,
)
from core.specialist_source_bound_calculation_runtime import (
    SPECIALIST_SOURCE_BOUND_CALCULATION_REASON,
    SpecialistSourceBoundCalculationRuntimeError,
    build_specialist_source_bound_calculation_action_inputs,
    build_specialist_source_bound_calculation_projection,
    build_specialist_source_bound_calculation_state,
)
from core.specialist_source_bound_calculation_runtime import (
    SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE as SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE_NAME,
)
from core.sufficiency_readiness_runtime import (
    SUFFICIENCY_READINESS_REASON,
    SufficiencyReadinessRuntimeError,
    build_sufficiency_readiness_action_inputs,
    build_sufficiency_readiness_projection,
    build_sufficiency_readiness_state,
)
from core.sufficiency_readiness_runtime import (
    SUFFICIENCY_READINESS_STAGE as SUFFICIENCY_READINESS_STAGE_NAME,
)

RUN_KERNEL_TRACE_KEY = "run_kernel"

ROUTE_REQUEST_STAGE = "route_request"
QUERY_PRODUCTION_STAGE = "query_production"
QUERY_PLAN_ADMISSION_STAGE = "query_plan_admission"
RUN_CONTRACT_STAGE = "run_contract"
SEARCH_PLANNER_PRODUCTION_STAGE = SEARCH_PLANNER_PRODUCTION_STAGE_NAME
SCOUT_DISAMBIGUATION_STAGE = SCOUT_DISAMBIGUATION_STAGE_NAME
SEARCH_PLANNER_REVISION_STAGE = SEARCH_PLANNER_REVISION_STAGE_NAME
SEARCH_EXECUTOR_HANDOFF_STAGE = SEARCH_EXECUTOR_HANDOFF_STAGE_NAME
LIVE_SEARCH_VALIDATION_STAGE = LIVE_SEARCH_VALIDATION_STAGE_NAME
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
MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE = (
    "multicomponent_missing_component_recovery_authorization"
)
MULTICOMPONENT_RECOVERY_OUTCOME_STAGE = "multicomponent_recovery_outcome"
MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE = (
    "multicomponent_selective_recomputation_closure"
)
_MULTICOMPONENT_RECOVERY_OUTCOME_DISPOSITIONS = frozenset(
    {
        "acquired",
        "blocked_requires_user_confirmation",
        "blocked_no_candidates",
        "blocked_no_readable_evidence",
        "blocked_component_admission",
        "blocked_resynthesis",
    }
)
_MULTICOMPONENT_RECOVERY_ORDINARY_PROVIDERS = frozenset(
    {"tavily", "linkup", "exa"}
)
SEMANTIC_PRODUCER_BUNDLE_COMMIT_REASON = (
    "ordinary_semantic_producer_atomic_bundle_commit"
)
RECOVERED_SEMANTIC_DELTA_COMMIT_REASON = (
    "component_gap_recovery_atomic_semantic_delta_commit"
)
CONTRACT_AMENDMENT_ADMISSION_STAGE = CONTRACT_AMENDMENT_ADMISSION_STAGE_NAME
CONTRACT_AMENDMENT_APPLICATION_STAGE = CONTRACT_AMENDMENT_APPLICATION_STAGE_NAME
DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY_STAGE = (
    "dprime_current_answer_contract_authority"
)
DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY_REASON = (
    "dprime_current_answer_contract_authority_from_ordinary_product_status"
)
DPRIME_SOURCE_OBLIGATION_AUTHORITY_STAGE = "dprime_source_obligation_authority"
DPRIME_SOURCE_OBLIGATION_AUTHORITY_REASON = (
    "dprime_source_obligation_authority_from_bound_component_coverage"
)
DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_STAGE = (
    "dprime_citation_source_handoff_authority"
)
DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_REASON = (
    "dprime_citation_source_handoff_authority_from_source_obligation_authority"
)
DPRIME_CITATION_SOURCE_DISPLAY_STAGE = "dprime_citation_source_display"
DPRIME_CITATION_SOURCE_DISPLAY_REASON = (
    "dprime_citation_source_display_from_single_lane_author_answer"
)
SEARCH_WORK_PLAN_CONSTRUCTION_STAGE = "search_work_plan_construction"
ANSWER_CONTRACT_AUTHORITY_MAP_STAGE = "answer_contract_authority_map"
OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE = "offline_search_executor_bridge"
COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE = "component_scoped_source_custody"
MAIN_RETRIEVAL_STAGE = "main_retrieval"
RETRIEVAL_STOP_CHECKPOINT_STAGE = "retrieval_stop_checkpoint"
EVIDENCE_LEDGER_STAGE = "evidence_ledger"
SEARCH_JUDGMENT_STAGE = "search_judgment"
SUFFICIENCY_JUDGMENT_STAGE = "sufficiency_judgment"
FINAL_ANSWER_PACKET_STAGE = "final_answer_packet"
AUTHOR_PROSE_FINALIZATION_STAGE = AUTHOR_PROSE_FINALIZATION_STAGE_NAME
AUTHOR_EXECUTION_STAGE = "author_execution"
FOLLOWUP_SEARCH_AUTHORIZATION_STAGE = FOLLOWUP_SEARCH_AUTHORIZATION_STAGE_NAME
SCRUTINEER_REVIEW_STAGE = SCRUTINEER_REVIEW_STAGE_NAME
SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE = (
    SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE_NAME
)
SUFFICIENCY_READINESS_STAGE = SUFFICIENCY_READINESS_STAGE_NAME
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
SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE = (
    "single_relation_source_obligation_recovery_authorization"
)

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
    SEARCH_PLANNER_PRODUCE = "search_planner_produce"
    SCOUT_DISAMBIGUATE = "scout_disambiguate"
    SEARCH_PLANNER_REVISE = "search_planner_revise"
    SEARCH_EXECUTOR_HANDOFF = "search_executor_handoff"
    LIVE_SEARCH_VALIDATE = "live_search_validate"
    INITIAL_ANSWER_CONTRACT_ACCEPT = "initial_answer_contract_accept"
    SEMANTIC_OBSERVATION_ADMIT = "semantic_observation_admit"
    COMPONENT_COVERAGE_REDUCE = "component_coverage_reduce"
    RECOVERED_SEMANTIC_DELTA_COMMIT = (
        "component_gap_recovery_semantic_delta_commit"
    )
    SEMANTIC_PRODUCER_BUNDLE_COMMIT = "semantic_producer_bundle_commit"
    MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE = (
        "multicomponent_component_analyst_execute"
    )
    MULTICOMPONENT_SCHEDULER_INITIALIZE = (
        "multicomponent_graph_scheduler_initialize"
    )
    MULTICOMPONENT_LEASE_GRANT = "multicomponent_semantic_lease_grant"
    MULTICOMPONENT_LEASE_DISPATCH = "multicomponent_semantic_lease_dispatch"
    MULTICOMPONENT_LEASE_CANCEL = "multicomponent_semantic_lease_cancel"
    MULTICOMPONENT_BATCH_GRANT = "multicomponent_semantic_batch_grant"
    MULTICOMPONENT_BATCH_DISPATCH = "multicomponent_semantic_batch_dispatch"
    MULTICOMPONENT_BATCH_CANCEL = "multicomponent_semantic_batch_cancel"
    MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE = (
        "multicomponent_component_dprime_execute"
    )
    MULTICOMPONENT_CROSS_ANALYST_EXECUTE = (
        "multicomponent_cross_analyst_execute"
    )
    MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE = (
        "multicomponent_synthesis_dprime_execute"
    )
    MULTICOMPONENT_SCRUTINEER_EXECUTE = "multicomponent_scrutineer_execute"
    SPECIALIST_PROPOSAL_BIND = "specialist_proposal_bind"
    SPECIALIST_PROPOSAL_DISPOSE = "specialist_proposal_dispose"
    SPECIALIST_CAPABILITY_EXECUTE = "specialist_capability_execute"
    SPECIALIST_VALIDATOR_CONSUME = "specialist_validator_consume"
    MULTICOMPONENT_COMPONENT_ADMISSION_REDUCE = (
        "multicomponent_component_admission_reduce"
    )
    MULTICOMPONENT_GRAPH_REDUCE = "multicomponent_graph_reduce"
    MULTICOMPONENT_RECOVERY_AUTHORIZE = (
        "multicomponent_missing_component_recovery_authorize"
    )
    MULTICOMPONENT_RECOVERY_OUTCOME_REDUCE = (
        "multicomponent_recovery_outcome_reduce"
    )
    CONTRACT_AMENDMENT_ADMIT = "contract_amendment_admit"
    CONTRACT_AMENDMENT_APPLY = "contract_amendment_apply"
    DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY = (
        "dprime_current_answer_contract_authority"
    )
    DPRIME_SOURCE_OBLIGATION_AUTHORITY = "dprime_source_obligation_authority"
    DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY = (
        "dprime_citation_source_handoff_authority"
    )
    DPRIME_CITATION_SOURCE_DISPLAY = "dprime_citation_source_display"
    SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE = (
        "single_relation_source_obligation_recovery_authorize"
    )
    SEARCH_WORK_PLAN_CONSTRUCT = "search_work_plan_construct"
    QUERY_PRODUCTION = "query_production"
    QUERY_PLAN_ADMISSION = "query_plan_admission"
    MAIN_RETRIEVAL_PASS = "main_retrieval_pass"
    RETRIEVAL_STOP_CHECKPOINT = "retrieval_stop_checkpoint"
    EVIDENCE_LEDGER_REDUCE = "evidence_ledger_reduce"
    SEARCH_JUDGMENT_DECIDE = "search_judgment_decide"
    SUFFICIENCY_JUDGMENT_DECIDE = "sufficiency_judgment_decide"
    FINAL_ANSWER_PACKET_HARDEN = "final_answer_packet_harden"
    AUTHOR_PROSE_FINALIZE = "author_prose_finalize"
    FINAL_ANSWER_PACKET_PREPARE = "final_answer_packet_prepare"
    AUTHOR_EXECUTE = "author_execute"
    FOLLOWUP_SEARCH_AUTHORIZE = "followup_search_authorize"
    SCRUTINEER_REVIEW_REDUCE = "scrutineer_review_reduce"
    SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCE = (
        "specialist_source_bound_calculation_reduce"
    )
    SUFFICIENCY_READINESS_DECIDE = "sufficiency_readiness_decide"
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
    SEARCH_PLANNER_PRODUCED = "search_planner_produced"
    SCOUT_DISAMBIGUATION_REPORTED = "scout_disambiguation_reported"
    SEARCH_PLANNER_REVISED = "search_planner_revised"
    SEARCH_EXECUTOR_HANDOFF_CREATED = "search_executor_handoff_created"
    LIVE_SEARCH_VALIDATED = "live_search_validated"
    INITIAL_ANSWER_CONTRACT_ACCEPTED = "initial_answer_contract_accepted"
    SEMANTIC_OBSERVATION_ADMITTED = "semantic_observation_admitted"
    COMPONENT_COVERAGE_REDUCED = "component_coverage_reduced"
    RECOVERED_SEMANTIC_DELTA_COMMITTED = (
        "component_gap_recovery_semantic_delta_committed"
    )
    SEMANTIC_PRODUCER_BUNDLE_COMMITTED = "semantic_producer_bundle_committed"
    MULTICOMPONENT_COMPONENT_ANALYST_COMPLETED = (
        "multicomponent_component_analyst_completed"
    )
    MULTICOMPONENT_SCHEDULER_INITIALIZED = (
        "multicomponent_graph_scheduler_initialized"
    )
    MULTICOMPONENT_LEASE_GRANTED = "multicomponent_semantic_lease_granted"
    MULTICOMPONENT_LEASE_DISPATCHED = "multicomponent_semantic_lease_dispatched"
    MULTICOMPONENT_LEASE_CANCELLED = "multicomponent_semantic_lease_cancelled"
    MULTICOMPONENT_BATCH_GRANTED = "multicomponent_semantic_batch_granted"
    MULTICOMPONENT_BATCH_DISPATCHED = "multicomponent_semantic_batch_dispatched"
    MULTICOMPONENT_BATCH_CANCELLED = "multicomponent_semantic_batch_cancelled"
    MULTICOMPONENT_COMPONENT_DPRIME_COMPLETED = (
        "multicomponent_component_dprime_completed"
    )
    MULTICOMPONENT_CROSS_ANALYST_COMPLETED = (
        "multicomponent_cross_analyst_completed"
    )
    MULTICOMPONENT_SYNTHESIS_DPRIME_COMPLETED = (
        "multicomponent_synthesis_dprime_completed"
    )
    MULTICOMPONENT_SCRUTINEER_COMPLETED = "multicomponent_scrutineer_completed"
    SPECIALIST_PROPOSAL_BOUND = "specialist_proposal_bound"
    SPECIALIST_PROPOSAL_DISPOSED = "specialist_proposal_disposed"
    SPECIALIST_CAPABILITY_COMPLETED = "specialist_capability_completed"
    SPECIALIST_VALIDATOR_CONSUMED = "specialist_validator_consumed"
    MULTICOMPONENT_COMPONENT_ADMISSION_REDUCED = (
        "multicomponent_component_admission_reduced"
    )
    MULTICOMPONENT_GRAPH_REDUCED = "multicomponent_graph_reduced"
    MULTICOMPONENT_RECOVERY_AUTHORIZED = (
        "multicomponent_missing_component_recovery_authorized"
    )
    MULTICOMPONENT_RECOVERY_OUTCOME_REDUCED = (
        "multicomponent_recovery_outcome_reduced"
    )
    CONTRACT_AMENDMENT_ADMITTED = "contract_amendment_admitted"
    CONTRACT_AMENDMENT_APPLIED = "contract_amendment_applied"
    DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORIZED = (
        "dprime_current_answer_contract_authorized"
    )
    DPRIME_SOURCE_OBLIGATION_AUTHORITY_CONSUMED = (
        "dprime_source_obligation_authority_consumed"
    )
    DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_CONSUMED = (
        "dprime_citation_source_handoff_authority_consumed"
    )
    DPRIME_CITATION_SOURCE_DISPLAY_CREATED = "dprime_citation_source_display_created"
    SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED = (
        "single_relation_source_obligation_recovery_authorized"
    )
    SEARCH_WORK_PLAN_CONSTRUCTED = "search_work_plan_constructed"
    QUERY_CANDIDATES_PRODUCED = "query_candidates_produced"
    QUERY_PLAN_ADMITTED = "query_plan_admitted"
    RETRIEVAL_PASS_RESULT = "retrieval_pass_result"
    RETRIEVAL_STOP_DECISION = "retrieval_stop_decision"
    EVIDENCE_CUSTODY_OBSERVED = "evidence_custody_observed"
    SEARCH_JUDGMENT_DECIDED = "search_judgment_decided"
    SUFFICIENCY_JUDGMENT_DECIDED = "sufficiency_judgment_decided"
    FINAL_ANSWER_PACKET_HARDENED = "final_answer_packet_hardened"
    AUTHOR_PROSE_FINALIZED = "author_prose_finalized"
    FINAL_ANSWER_PACKET_PREPARED = "final_answer_packet_prepared"
    AUTHOR_OUTPUT_OBSERVED = "author_output_observed"
    FOLLOWUP_SEARCH_AUTHORIZED = "followup_search_authorized"
    SCRUTINEER_REVIEW_REDUCED = "scrutineer_review_reduced"
    SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCED = (
        "specialist_source_bound_calculation_reduced"
    )
    SUFFICIENCY_READINESS_DECIDED = "sufficiency_readiness_decided"
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
    if depth > 8:
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
            self.observation_type is ObservationType.SEARCH_PLANNER_REVISED
            and isinstance(self.payload, Mapping)
        ):
            payload = _safe_mapping(
                {
                    key: value
                    for key, value in self.payload.items()
                    if key != "planner_revision"
                }
            )
            raw_planner_revision = self.payload.get("planner_revision")
            if isinstance(raw_planner_revision, Mapping):
                payload["planner_revision"] = dict(raw_planner_revision)
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
    search_planner_proposal_state: dict[str, Any] = field(default_factory=dict)
    search_planner_proposal_projection: dict[str, Any] = field(default_factory=dict)
    search_planner_proposal_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    scout_disambiguation_report_state: dict[str, Any] = field(default_factory=dict)
    scout_disambiguation_report_projection: dict[str, Any] = field(
        default_factory=dict
    )
    scout_disambiguation_report_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    search_planner_revision_state: dict[str, Any] = field(default_factory=dict)
    search_planner_revision_projection: dict[str, Any] = field(
        default_factory=dict
    )
    search_planner_revision_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    search_executor_handoff_state: dict[str, Any] = field(default_factory=dict)
    search_executor_handoff_projection: dict[str, Any] = field(
        default_factory=dict
    )
    search_executor_handoff_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    live_search_validation_state: dict[str, Any] = field(default_factory=dict)
    live_search_validation_projection: dict[str, Any] = field(
        default_factory=dict
    )
    live_search_validation_history: list[dict[str, Any]] = field(
        default_factory=list
    )
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
    dprime_source_obligation_authority_state: dict[str, Any] = field(
        default_factory=dict
    )
    dprime_source_obligation_authority_projection: dict[str, Any] = field(
        default_factory=dict
    )
    dprime_source_obligation_authority_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    dprime_citation_source_handoff_state: dict[str, Any] = field(
        default_factory=dict
    )
    dprime_citation_source_handoff_projection: dict[str, Any] = field(
        default_factory=dict
    )
    dprime_citation_source_handoff_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    scrutineer_review_state: dict[str, Any] = field(default_factory=dict)
    scrutineer_review_projection: dict[str, Any] = field(default_factory=dict)
    scrutineer_review_history: list[dict[str, Any]] = field(default_factory=list)
    specialist_source_bound_calculation_state: dict[str, Any] = field(
        default_factory=dict
    )
    specialist_source_bound_calculation_projection: dict[str, Any] = field(
        default_factory=dict
    )
    specialist_source_bound_calculation_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    sufficiency_readiness_state: dict[str, Any] = field(default_factory=dict)
    sufficiency_readiness_projection: dict[str, Any] = field(default_factory=dict)
    sufficiency_readiness_history: list[dict[str, Any]] = field(
        default_factory=list
    )
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
    current_answer_contract: dict[str, Any] = field(default_factory=dict)
    current_answer_contract_projection: dict[str, Any] = field(default_factory=dict)
    current_answer_contract_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    contract_amendment_application_state: dict[str, Any] = field(
        default_factory=dict
    )
    contract_amendment_application_projection: dict[str, Any] = field(
        default_factory=dict
    )
    contract_amendment_application_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    search_work_plan: dict[str, Any] = field(default_factory=dict)
    search_work_plan_projection: dict[str, Any] = field(default_factory=dict)
    search_work_plan_validation: dict[str, Any] = field(default_factory=dict)
    offline_search_executor_bridge_projection: dict[str, Any] = field(
        default_factory=dict
    )
    offline_search_executor_bridge_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    component_scoped_source_custody_projection: dict[str, Any] = field(
        default_factory=dict
    )
    component_scoped_source_custody_history: list[dict[str, Any]] = field(
        default_factory=list
    )
    evidence_ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    search_judgment: dict[str, Any] = field(default_factory=dict)
    search_judgment_projection: dict[str, Any] = field(default_factory=dict)
    search_judgment_history: list[dict[str, Any]] = field(default_factory=list)
    sufficiency_judgment: dict[str, Any] = field(default_factory=dict)
    sufficiency_judgment_projection: dict[str, Any] = field(default_factory=dict)
    sufficiency_judgment_history: list[dict[str, Any]] = field(default_factory=list)
    final_answer_packet: dict[str, Any] = field(default_factory=dict)
    final_answer_packet_history: list[dict[str, Any]] = field(default_factory=list)
    author_observation: dict[str, Any] = field(default_factory=dict)
    final_answer_outcome: dict[str, Any] = field(default_factory=dict)
    final_answer_authority_projection: dict[str, Any] = field(default_factory=dict)
    author_prose_state: dict[str, Any] = field(default_factory=dict)
    author_prose_projection: dict[str, Any] = field(default_factory=dict)
    author_prose_history: list[dict[str, Any]] = field(default_factory=list)
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
    # Exact scheduler packet context is canonical in-memory state but is not a
    # trace/export surface.  The public projection stores only digests and refs.
    multicomponent_scheduler_context: dict[str, Any] = field(default_factory=dict)
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
            search_planner_proposal_state=deepcopy(
                self.search_planner_proposal_state
            ),
            search_planner_proposal_projection=deepcopy(
                self.search_planner_proposal_projection
            ),
            search_planner_proposal_history=deepcopy(
                self.search_planner_proposal_history
            ),
            scout_disambiguation_report_state=deepcopy(
                self.scout_disambiguation_report_state
            ),
            scout_disambiguation_report_projection=deepcopy(
                self.scout_disambiguation_report_projection
            ),
            scout_disambiguation_report_history=deepcopy(
                self.scout_disambiguation_report_history
            ),
            search_planner_revision_state=deepcopy(
                self.search_planner_revision_state
            ),
            search_planner_revision_projection=deepcopy(
                self.search_planner_revision_projection
            ),
            search_planner_revision_history=deepcopy(
                self.search_planner_revision_history
            ),
            search_executor_handoff_state=deepcopy(
                self.search_executor_handoff_state
            ),
            search_executor_handoff_projection=deepcopy(
                self.search_executor_handoff_projection
            ),
            search_executor_handoff_history=deepcopy(
                self.search_executor_handoff_history
            ),
            live_search_validation_state=deepcopy(
                self.live_search_validation_state
            ),
            live_search_validation_projection=deepcopy(
                self.live_search_validation_projection
            ),
            live_search_validation_history=deepcopy(
                self.live_search_validation_history
            ),
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
            dprime_source_obligation_authority_state=deepcopy(
                self.dprime_source_obligation_authority_state
            ),
            dprime_source_obligation_authority_projection=deepcopy(
                self.dprime_source_obligation_authority_projection
            ),
            dprime_source_obligation_authority_history=deepcopy(
                self.dprime_source_obligation_authority_history
            ),
            dprime_citation_source_handoff_state=deepcopy(
                self.dprime_citation_source_handoff_state
            ),
            dprime_citation_source_handoff_projection=deepcopy(
                self.dprime_citation_source_handoff_projection
            ),
            dprime_citation_source_handoff_history=deepcopy(
                self.dprime_citation_source_handoff_history
            ),
            scrutineer_review_state=deepcopy(self.scrutineer_review_state),
            scrutineer_review_projection=deepcopy(self.scrutineer_review_projection),
            scrutineer_review_history=deepcopy(self.scrutineer_review_history),
            specialist_source_bound_calculation_state=deepcopy(
                self.specialist_source_bound_calculation_state
            ),
            specialist_source_bound_calculation_projection=deepcopy(
                self.specialist_source_bound_calculation_projection
            ),
            specialist_source_bound_calculation_history=deepcopy(
                self.specialist_source_bound_calculation_history
            ),
            sufficiency_readiness_state=deepcopy(
                self.sufficiency_readiness_state
            ),
            sufficiency_readiness_projection=deepcopy(
                self.sufficiency_readiness_projection
            ),
            sufficiency_readiness_history=deepcopy(
                self.sufficiency_readiness_history
            ),
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
            current_answer_contract=deepcopy(self.current_answer_contract),
            current_answer_contract_projection=deepcopy(
                self.current_answer_contract_projection
            ),
            current_answer_contract_history=deepcopy(
                self.current_answer_contract_history
            ),
            contract_amendment_application_state=deepcopy(
                self.contract_amendment_application_state
            ),
            contract_amendment_application_projection=deepcopy(
                self.contract_amendment_application_projection
            ),
            contract_amendment_application_history=deepcopy(
                self.contract_amendment_application_history
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
            final_answer_packet_history=deepcopy(self.final_answer_packet_history),
            author_observation=deepcopy(self.author_observation),
            final_answer_outcome=deepcopy(self.final_answer_outcome),
            final_answer_authority_projection=deepcopy(
                self.final_answer_authority_projection
            ),
            author_prose_state=deepcopy(self.author_prose_state),
            author_prose_projection=deepcopy(self.author_prose_projection),
            author_prose_history=deepcopy(self.author_prose_history),
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
    search_planner_proposal_state: Mapping[str, Any]
    search_planner_proposal_projection: Mapping[str, Any]
    search_planner_proposal_history: Sequence[Mapping[str, Any]]
    scout_disambiguation_report_state: Mapping[str, Any]
    scout_disambiguation_report_projection: Mapping[str, Any]
    scout_disambiguation_report_history: Sequence[Mapping[str, Any]]
    search_planner_revision_state: Mapping[str, Any]
    search_planner_revision_projection: Mapping[str, Any]
    search_planner_revision_history: Sequence[Mapping[str, Any]]
    search_executor_handoff_state: Mapping[str, Any]
    search_executor_handoff_projection: Mapping[str, Any]
    search_executor_handoff_history: Sequence[Mapping[str, Any]]
    live_search_validation_state: Mapping[str, Any]
    live_search_validation_projection: Mapping[str, Any]
    live_search_validation_history: Sequence[Mapping[str, Any]]
    initial_answer_contract: Mapping[str, Any]
    initial_answer_contract_projection: Mapping[str, Any]
    initial_answer_contract_history: Sequence[Mapping[str, Any]]
    semantic_observation_admission_state: Mapping[str, Any]
    semantic_observation_admission_projection: Mapping[str, Any]
    semantic_observation_admission_history: Sequence[Mapping[str, Any]]
    component_coverage_state: Mapping[str, Any]
    component_coverage_projection: Mapping[str, Any]
    component_coverage_history: Sequence[Mapping[str, Any]]
    dprime_source_obligation_authority_state: Mapping[str, Any]
    dprime_source_obligation_authority_projection: Mapping[str, Any]
    dprime_source_obligation_authority_history: Sequence[Mapping[str, Any]]
    dprime_citation_source_handoff_state: Mapping[str, Any]
    dprime_citation_source_handoff_projection: Mapping[str, Any]
    dprime_citation_source_handoff_history: Sequence[Mapping[str, Any]]
    scrutineer_review_state: Mapping[str, Any]
    scrutineer_review_projection: Mapping[str, Any]
    scrutineer_review_history: Sequence[Mapping[str, Any]]
    specialist_source_bound_calculation_state: Mapping[str, Any]
    specialist_source_bound_calculation_projection: Mapping[str, Any]
    specialist_source_bound_calculation_history: Sequence[Mapping[str, Any]]
    sufficiency_readiness_state: Mapping[str, Any]
    sufficiency_readiness_projection: Mapping[str, Any]
    sufficiency_readiness_history: Sequence[Mapping[str, Any]]
    component_gap_recovery_history: Sequence[Mapping[str, Any]]
    contract_amendment_admission_state: Mapping[str, Any]
    contract_amendment_admission_projection: Mapping[str, Any]
    contract_amendment_admission_history: Sequence[Mapping[str, Any]]
    current_answer_contract: Mapping[str, Any]
    current_answer_contract_projection: Mapping[str, Any]
    current_answer_contract_history: Sequence[Mapping[str, Any]]
    contract_amendment_application_state: Mapping[str, Any]
    contract_amendment_application_projection: Mapping[str, Any]
    contract_amendment_application_history: Sequence[Mapping[str, Any]]
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
    final_answer_packet_history: Sequence[Mapping[str, Any]]
    author_observation: Mapping[str, Any]
    final_answer_outcome: Mapping[str, Any]
    final_answer_authority_projection: Mapping[str, Any]
    author_prose_state: Mapping[str, Any]
    author_prose_projection: Mapping[str, Any]
    author_prose_history: Sequence[Mapping[str, Any]]
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
            "search_planner_proposal_state": _safe_mapping(
                self.search_planner_proposal_state
            ),
            "search_planner_proposal_projection": _safe_mapping(
                self.search_planner_proposal_projection
            ),
            "search_planner_proposal_history": [
                _safe_mapping(item)
                for item in self.search_planner_proposal_history
            ],
            "scout_disambiguation_report_state": _safe_mapping(
                self.scout_disambiguation_report_state
            ),
            "scout_disambiguation_report_projection": _safe_mapping(
                self.scout_disambiguation_report_projection
            ),
            "scout_disambiguation_report_history": [
                _safe_mapping(item)
                for item in self.scout_disambiguation_report_history
            ],
            "search_planner_revision_state": _safe_mapping(
                self.search_planner_revision_state
            ),
            "search_planner_revision_projection": _safe_mapping(
                self.search_planner_revision_projection
            ),
            "search_planner_revision_history": [
                _safe_mapping(item)
                for item in self.search_planner_revision_history
            ],
            "search_executor_handoff_state": _safe_mapping(
                self.search_executor_handoff_state
            ),
            "search_executor_handoff_projection": _safe_mapping(
                self.search_executor_handoff_projection
            ),
            "search_executor_handoff_history": [
                _safe_mapping(item)
                for item in self.search_executor_handoff_history
            ],
            "live_search_validation_state": _safe_mapping(
                self.live_search_validation_state
            ),
            "live_search_validation_projection": _safe_mapping(
                self.live_search_validation_projection
            ),
            "live_search_validation_history": [
                _safe_mapping(item) for item in self.live_search_validation_history
            ],
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
            "dprime_source_obligation_authority_state": _safe_mapping(
                self.dprime_source_obligation_authority_state
            ),
            "dprime_source_obligation_authority_projection": _safe_mapping(
                self.dprime_source_obligation_authority_projection
            ),
            "dprime_source_obligation_authority_history": [
                _safe_mapping(item)
                for item in self.dprime_source_obligation_authority_history
            ],
            "dprime_citation_source_handoff_state": _safe_mapping(
                self.dprime_citation_source_handoff_state
            ),
            "dprime_citation_source_handoff_projection": _safe_mapping(
                self.dprime_citation_source_handoff_projection
            ),
            "dprime_citation_source_handoff_history": [
                _safe_mapping(item)
                for item in self.dprime_citation_source_handoff_history
            ],
            "scrutineer_review_state": _safe_mapping(self.scrutineer_review_state),
            "scrutineer_review_projection": _safe_mapping(
                self.scrutineer_review_projection
            ),
            "scrutineer_review_history": [
                _safe_mapping(item) for item in self.scrutineer_review_history
            ],
            "specialist_source_bound_calculation_state": _safe_mapping(
                self.specialist_source_bound_calculation_state
            ),
            "specialist_source_bound_calculation_projection": _safe_mapping(
                self.specialist_source_bound_calculation_projection
            ),
            "specialist_source_bound_calculation_history": [
                _safe_mapping(item)
                for item in self.specialist_source_bound_calculation_history
            ],
            "sufficiency_readiness_state": _safe_mapping(
                self.sufficiency_readiness_state
            ),
            "sufficiency_readiness_projection": _safe_mapping(
                self.sufficiency_readiness_projection
            ),
            "sufficiency_readiness_history": [
                _safe_mapping(item) for item in self.sufficiency_readiness_history
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
            "current_answer_contract": _safe_mapping(self.current_answer_contract),
            "current_answer_contract_projection": _safe_mapping(
                self.current_answer_contract_projection
            ),
            "current_answer_contract_history": [
                _safe_mapping(item) for item in self.current_answer_contract_history
            ],
            "contract_amendment_application_state": _safe_mapping(
                self.contract_amendment_application_state
            ),
            "contract_amendment_application_projection": _safe_mapping(
                self.contract_amendment_application_projection
            ),
            "contract_amendment_application_history": [
                _safe_mapping(item)
                for item in self.contract_amendment_application_history
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
            "final_answer_packet_history": [
                _safe_mapping(item) for item in self.final_answer_packet_history
            ],
            "author_observation": _safe_mapping(self.author_observation),
            "final_answer_outcome": _safe_mapping(self.final_answer_outcome),
            "final_answer_authority_projection": _safe_mapping(
                self.final_answer_authority_projection
            ),
            "author_prose_state": _safe_mapping(self.author_prose_state),
            "author_prose_projection": _safe_mapping(self.author_prose_projection),
            "author_prose_history": [
                _safe_mapping(item) for item in self.author_prose_history
            ],
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

    def authorize_search_planner_production(
        self,
        *,
        user_query_digest: str,
        request_id: str | None = None,
        planner_schema_version: str = SEARCH_PLANNER_SCHEMA_VERSION,
        reason: str = SEARCH_PLANNER_PRODUCTION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        clean_digest = _clean_text(user_query_digest, limit=128)
        if not clean_digest:
            raise RunKernelTransitionError(
                "search planner production requires user_query_digest binding"
            )
        if planner_schema_version != SEARCH_PLANNER_SCHEMA_VERSION:
            raise RunKernelTransitionError(
                "search planner production requires the current planner schema version"
            )
        initial_ref = _search_planner_contract_ref_from_contract(
            self.state.initial_answer_contract,
            source="initial_answer_contract",
        )
        current_ref = _search_planner_contract_ref_from_contract(
            self.state.current_answer_contract,
            source="current_answer_contract",
        )
        merged_inputs = {
            **dict(inputs or {}),
            "run_id": self.state.run_id,
            "request_id": request_id or self.state.request_id,
            "user_query_digest": clean_digest,
            "planner_schema_version": planner_schema_version,
            "parent_initial_contract_version": initial_ref.get("contract_version"),
            "parent_initial_contract_digest": initial_ref.get("contract_digest"),
            "parent_current_contract_version": current_ref.get("contract_version"),
            "parent_current_contract_digest": current_ref.get("contract_digest"),
            "route_context_ref": {},
            "run_context_ref": {},
        }
        return self.authorize(
            stage=SEARCH_PLANNER_PRODUCTION_STAGE,
            action_type=ActionType.SEARCH_PLANNER_PRODUCE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        )

    def authorize_scout_disambiguation(
        self,
        *,
        component_id: str,
        ambiguity_dimension_ids: Sequence[str],
        request_id: str | None = None,
        max_queries_per_component: int = SCOUT_MAX_QUERIES_PER_COMPONENT,
        max_dimensions_per_component: int = SCOUT_MAX_DIMENSIONS_PER_COMPONENT,
        reason: str = SCOUT_DISAMBIGUATION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        clean_component_id = _clean_text(component_id, limit=160)
        if not clean_component_id:
            raise RunKernelTransitionError(
                "Scout disambiguation requires component_id binding"
            )
        if (
            int(max_queries_per_component or 0) > SCOUT_MAX_QUERIES_PER_COMPONENT
            or int(max_queries_per_component or 0) < 0
        ):
            raise RunKernelTransitionError(
                "Scout disambiguation exceeds max queries per component"
            )
        if (
            int(max_dimensions_per_component or 0)
            > SCOUT_MAX_DIMENSIONS_PER_COMPONENT
            or int(max_dimensions_per_component or 0) < 0
        ):
            raise RunKernelTransitionError(
                "Scout disambiguation exceeds max dimensions per component"
            )
        clean_dimension_ids: list[str] = []
        if isinstance(ambiguity_dimension_ids, Sequence) and not isinstance(
            ambiguity_dimension_ids,
            str | bytes,
        ):
            for item in ambiguity_dimension_ids:
                dimension_id = _clean_text(item, limit=160)
                if dimension_id:
                    clean_dimension_ids.append(dimension_id)
        if not clean_dimension_ids:
            raise RunKernelTransitionError(
                "Scout disambiguation requires ambiguity dimension bindings"
            )
        if len(clean_dimension_ids) > SCOUT_MAX_DIMENSIONS_PER_COMPONENT:
            raise RunKernelTransitionError(
                "Scout disambiguation exceeds max dimensions per component"
            )
        if len(clean_dimension_ids) > int(max_dimensions_per_component):
            raise RunKernelTransitionError(
                "Scout disambiguation dimensions exceed the authorized "
                "per-component dimension budget"
            )
        if len(set(clean_dimension_ids)) != len(clean_dimension_ids):
            raise RunKernelTransitionError(
                "Scout disambiguation requires unique ambiguity dimension ids"
            )
        parent_planner_ref = planner_ref_from_search_planner_state(
            self.state.search_planner_proposal_state
        )
        if not parent_planner_ref:
            raise RunKernelTransitionError(
                "Scout disambiguation requires a current SearchPlanner proposal"
            )
        qmr = _safe_mapping(
            self.state.search_planner_proposal_state.get("question_meaning_record")
        )
        components = qmr.get("answer_components")
        if not isinstance(components, Sequence) or isinstance(components, str | bytes):
            raise RunKernelTransitionError(
                "Scout disambiguation requires parent QMR answer components"
            )
        if not any(
            isinstance(item, Mapping)
            and _clean_text(item.get("component_id"), limit=160) == clean_component_id
            for item in components
        ):
            raise RunKernelTransitionError(
                "Scout disambiguation component_id is not present in parent QMR"
            )
        initial_ref = _scout_contract_ref_from_contract(
            self.state.initial_answer_contract,
            source="initial_answer_contract",
        )
        current_ref = _scout_contract_ref_from_contract(
            self.state.current_answer_contract,
            source="current_answer_contract",
        )
        merged_inputs = {
            **dict(inputs or {}),
            "run_id": self.state.run_id,
            "request_id": request_id or self.state.request_id,
            "parent_search_planner_proposal_id": parent_planner_ref.get(
                "proposal_id"
            ),
            "parent_search_planner_proposal_digest": parent_planner_ref.get(
                "proposal_digest"
            ),
            "parent_question_meaning_record_id": parent_planner_ref.get(
                "question_meaning_record_id"
            ),
            "parent_question_meaning_record_digest": parent_planner_ref.get(
                "question_meaning_record_digest"
            ),
            "component_id": clean_component_id,
            "ambiguity_dimension_ids": clean_dimension_ids,
            "max_queries_per_component": int(max_queries_per_component),
            "max_dimensions_per_component": int(max_dimensions_per_component),
            "parent_initial_contract_version": initial_ref.get("contract_version"),
            "parent_initial_contract_digest": initial_ref.get("contract_digest"),
            "parent_current_contract_version": current_ref.get("contract_version"),
            "parent_current_contract_digest": current_ref.get("contract_digest"),
            "scout_schema_version": SCOUT_DISAMBIGUATION_SCHEMA_VERSION,
            "reason": reason,
        }
        return self.authorize(
            stage=SCOUT_DISAMBIGUATION_STAGE,
            action_type=ActionType.SCOUT_DISAMBIGUATE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.SCOUT_DISAMBIGUATION_REPORTED
            ),
        )

    def authorize_search_planner_revision(
        self,
        *,
        component_id: str,
        consumed_ambiguity_dimension_ids: Sequence[str],
        consumed_scout_hint_ids: Sequence[str] = (),
        request_id: str | None = None,
        reason: str = SEARCH_PLANNER_REVISION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        clean_component_id = _clean_text(component_id, limit=160)
        if not clean_component_id:
            raise RunKernelTransitionError(
                "search planner revision requires component_id binding"
            )
        if not self.state.initial_answer_contract_projection:
            raise RunKernelTransitionError(
                "search planner revision requires an accepted initial answer contract"
            )
        parent_planner_ref = planner_ref_from_search_planner_state(
            self.state.search_planner_proposal_state
        )
        if not parent_planner_ref:
            raise RunKernelTransitionError(
                "search planner revision requires a current SearchPlanner proposal"
            )
        parent_scout_ref = scout_ref_from_scout_report_state(
            self.state.scout_disambiguation_report_state
        )
        if not parent_scout_ref:
            raise RunKernelTransitionError(
                "search planner revision requires a current Scout DisambiguationReport"
            )
        if (
            _safe_mapping(parent_scout_ref.get("parent_search_planner_proposal_ref"))
            != parent_planner_ref
        ):
            raise RunKernelTransitionError(
                "search planner revision requires Scout report bound to current planner/QMR"
            )
        if parent_scout_ref.get("component_id") != clean_component_id:
            raise RunKernelTransitionError(
                "search planner revision component_id does not match Scout report"
            )
        qmr = _safe_mapping(
            self.state.search_planner_proposal_state.get("question_meaning_record")
        )
        components = qmr.get("answer_components")
        if not isinstance(components, Sequence) or isinstance(components, str | bytes):
            raise RunKernelTransitionError(
                "search planner revision requires parent QMR answer components"
            )
        if not any(
            isinstance(item, Mapping)
            and _clean_text(item.get("component_id"), limit=160)
            == clean_component_id
            for item in components
        ):
            raise RunKernelTransitionError(
                "search planner revision component_id is not present in parent QMR"
            )

        clean_dimension_ids = _preserve_text_list(consumed_ambiguity_dimension_ids)
        if not clean_dimension_ids:
            raise RunKernelTransitionError(
                "search planner revision requires consumed ambiguity dimensions"
            )
        scout_dimensions = {
            _clean_text(item.get("dimension_id"), limit=160)
            for item in self.state.scout_disambiguation_report_state.get(
                "ambiguity_dimensions",
                [],
            )
            if isinstance(item, Mapping)
        }
        missing_dimensions = [
            item for item in clean_dimension_ids if item not in scout_dimensions
        ]
        if missing_dimensions:
            raise RunKernelTransitionError(
                "search planner revision consumes unknown Scout dimensions: "
                + ", ".join(missing_dimensions)
            )

        clean_hint_ids = _preserve_text_list(consumed_scout_hint_ids)
        scout_hint_ids = _scout_hint_ids_from_report(
            self.state.scout_disambiguation_report_state
        )
        missing_hints = [item for item in clean_hint_ids if item not in scout_hint_ids]
        if missing_hints:
            raise RunKernelTransitionError(
                "search planner revision consumes unknown Scout hints: "
                + ", ".join(missing_hints)
            )

        initial_ref = _revision_contract_ref_from_contract(
            self.state.initial_answer_contract,
            source="initial_answer_contract",
        )
        current_ref = _revision_contract_ref_from_contract(
            self.state.current_answer_contract,
            source="current_answer_contract",
        )
        merged_inputs = {
            **dict(inputs or {}),
            "run_id": self.state.run_id,
            "request_id": request_id or self.state.request_id,
            "parent_search_planner_proposal_id": parent_planner_ref.get(
                "proposal_id"
            ),
            "parent_search_planner_proposal_digest": parent_planner_ref.get(
                "proposal_digest"
            ),
            "parent_question_meaning_record_id": parent_planner_ref.get(
                "question_meaning_record_id"
            ),
            "parent_question_meaning_record_digest": parent_planner_ref.get(
                "question_meaning_record_digest"
            ),
            "parent_scout_disambiguation_report_id": parent_scout_ref.get(
                "report_id"
            ),
            "parent_scout_disambiguation_report_digest": parent_scout_ref.get(
                "report_digest"
            ),
            "component_id": clean_component_id,
            "consumed_ambiguity_dimension_ids": clean_dimension_ids,
            "consumed_scout_hint_ids": clean_hint_ids,
            "parent_initial_contract_version": initial_ref.get(
                "contract_version"
            ),
            "parent_initial_contract_digest": initial_ref.get("contract_digest"),
            "parent_current_contract_version": current_ref.get(
                "contract_version"
            ),
            "parent_current_contract_digest": current_ref.get("contract_digest"),
            "revision_schema_version": SEARCH_PLANNER_REVISION_SCHEMA_VERSION,
            "reason": reason,
        }
        return self.authorize(
            stage=SEARCH_PLANNER_REVISION_STAGE,
            action_type=ActionType.SEARCH_PLANNER_REVISE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.SEARCH_PLANNER_REVISED,
        )

    def authorize_search_executor_handoff(
        self,
        *,
        request_id: str | None = None,
        contract_parent_kind: str | None = None,
        component_ids: Sequence[str] = (),
        source_obligation_candidate_ids: Sequence[str] = (),
        search_requirement_ids: Sequence[str] = (),
        scout_direction_hint_ids: Sequence[str] = (),
        reason: str = SEARCH_EXECUTOR_HANDOFF_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.initial_answer_contract:
            raise RunKernelTransitionError(
                "SearchExecutor handoff requires an accepted initial answer contract"
            )
        parent_planner_ref = planner_ref_from_search_planner_state(
            self.state.search_planner_proposal_state
        )
        if not parent_planner_ref:
            raise RunKernelTransitionError(
                "SearchExecutor handoff requires a current SearchPlanner proposal"
            )
        initial_ref = _handoff_contract_ref_from_contract(
            self.state.initial_answer_contract,
            source="initial_answer_contract",
        )
        current_ref = _handoff_contract_ref_from_contract(
            self.state.current_answer_contract,
            source="current_answer_contract",
        )
        expected_parent_kind = (
            "current_answer_contract"
            if current_ref
            else "initial_answer_contract_fallback"
        )
        clean_parent_kind = _clean_text(contract_parent_kind) or expected_parent_kind
        if clean_parent_kind != expected_parent_kind:
            raise RunKernelTransitionError(
                "SearchExecutor handoff must use current_answer_contract when "
                "present and explicit initial fallback only when current is empty"
            )
        parent_contract = (
            self.state.current_answer_contract
            if current_ref
            else self.state.initial_answer_contract
        )
        clean_component_ids = _preserve_text_list(component_ids) or (
            _handoff_component_ids(parent_contract)
        )
        if not clean_component_ids:
            raise RunKernelTransitionError(
                "SearchExecutor handoff requires component bindings"
            )
        clean_source_ids = _preserve_text_list(source_obligation_candidate_ids) or (
            _handoff_source_obligation_ids(
                parent_contract=parent_contract,
                planner_state=self.state.search_planner_proposal_state,
                revision_state=self.state.search_planner_revision_state,
            )
        )
        clean_requirement_ids = _preserve_text_list(search_requirement_ids) or (
            _handoff_search_requirement_ids(
                planner_state=self.state.search_planner_proposal_state,
                revision_state=self.state.search_planner_revision_state,
            )
        )
        parent_revision_ref = revision_ref_from_revision_state(
            self.state.search_planner_revision_state
        )
        parent_scout_ref = scout_ref_from_scout_report_state(
            self.state.scout_disambiguation_report_state
        )
        if parent_revision_ref and (
            _safe_mapping(parent_revision_ref.get("parent_search_planner_proposal_ref"))
            != parent_planner_ref
        ):
            raise RunKernelTransitionError(
                "SearchExecutor handoff requires revision bound to current planner/QMR"
            )
        clean_hint_ids = _preserve_text_list(scout_direction_hint_ids)
        if not clean_hint_ids and parent_revision_ref:
            clean_hint_ids = _preserve_text_list(
                self.state.search_planner_revision_state.get(
                    "consumed_scout_hint_ids"
                )
            )
        if clean_hint_ids:
            if not parent_revision_ref:
                raise RunKernelTransitionError(
                    "SearchExecutor handoff cannot consume Scout hints without revision"
                )
            if not parent_scout_ref:
                raise RunKernelTransitionError(
                    "SearchExecutor handoff cannot consume Scout hints without Scout report"
                )
            known_hint_ids = _scout_hint_ids_from_report(
                self.state.scout_disambiguation_report_state
            )
            missing_hint_ids = [
                item for item in clean_hint_ids if item not in known_hint_ids
            ]
            if missing_hint_ids:
                raise RunKernelTransitionError(
                    "SearchExecutor handoff consumes unknown Scout hints: "
                    + ", ".join(missing_hint_ids)
                )
            if _safe_mapping(
                parent_revision_ref.get("parent_scout_disambiguation_report_ref")
            ) != parent_scout_ref:
                raise RunKernelTransitionError(
                    "SearchExecutor handoff requires revision bound to current Scout report"
                )
        merged_inputs = {
            **dict(inputs or {}),
            "run_id": self.state.run_id,
            "request_id": request_id or self.state.request_id,
            "contract_parent_kind": clean_parent_kind,
            "parent_current_contract_version": current_ref.get(
                "contract_version"
            ),
            "parent_current_contract_digest": current_ref.get("contract_digest"),
            "parent_initial_contract_version": initial_ref.get(
                "contract_version"
            ),
            "parent_initial_contract_digest": initial_ref.get("contract_digest"),
            "parent_search_planner_proposal_id": parent_planner_ref.get(
                "proposal_id"
            ),
            "parent_search_planner_proposal_digest": parent_planner_ref.get(
                "proposal_digest"
            ),
            "parent_question_meaning_record_id": parent_planner_ref.get(
                "question_meaning_record_id"
            ),
            "parent_question_meaning_record_digest": parent_planner_ref.get(
                "question_meaning_record_digest"
            ),
            "parent_search_planner_revision_id": parent_revision_ref.get(
                "revision_id"
            ),
            "parent_search_planner_revision_digest": parent_revision_ref.get(
                "revision_digest"
            ),
            "parent_scout_disambiguation_report_id": (
                parent_scout_ref.get("report_id") if clean_hint_ids else None
            ),
            "parent_scout_disambiguation_report_digest": (
                parent_scout_ref.get("report_digest") if clean_hint_ids else None
            ),
            "component_ids": clean_component_ids,
            "source_obligation_candidate_ids": clean_source_ids,
            "search_requirement_ids": clean_requirement_ids,
            "scout_direction_hint_ids": clean_hint_ids,
            "handoff_schema_version": SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
            "reason": reason,
        }
        return self.authorize(
            stage=SEARCH_EXECUTOR_HANDOFF_STAGE,
            action_type=ActionType.SEARCH_EXECUTOR_HANDOFF,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED
            ),
        )

    def authorize_live_search_validation(
        self,
        *,
        selected_search_task_ids: Sequence[str],
        provider_authorized: str | None = None,
        provider_call_cap: int = LIVE_SEARCH_VALIDATION_DEFAULT_PROVIDER_CALL_CAP,
        results_per_task_cap: int = (
            LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP
        ),
        parent_current_contract_version: str | None = None,
        parent_current_contract_digest: str | None = None,
        handoff_id: str | None = None,
        handoff_digest: str | None = None,
        raw_provider_payload_retained: bool = False,
        raw_search_response_retained: bool = False,
        no_fetch_read_policy_active: bool = True,
        request_id: str | None = None,
        reason: str = LIVE_SEARCH_VALIDATION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.current_answer_contract:
            raise RunKernelTransitionError(
                "live search validation requires current_answer_contract"
            )
        if not self.state.search_executor_handoff_state:
            raise RunKernelTransitionError(
                "live search validation requires SearchExecutorHandoff"
            )
        current_ref = _live_validation_contract_ref_from_contract(
            self.state.current_answer_contract,
            source="current_answer_contract",
        )
        handoff_ref = _live_validation_handoff_ref_from_handoff_state(
            self.state.search_executor_handoff_state
        )
        if not current_ref:
            raise RunKernelTransitionError(
                "live search validation requires accepted current_answer_contract"
            )
        if not handoff_ref:
            raise RunKernelTransitionError(
                "live search validation requires reduced SearchExecutorHandoff"
            )
        if (
            _safe_mapping(handoff_ref.get("parent_current_contract_ref"))
            != current_ref
        ):
            raise RunKernelTransitionError(
                "live search validation requires handoff bound to current_answer_contract"
            )
        if parent_current_contract_version and (
            parent_current_contract_version != current_ref.get("contract_version")
        ):
            raise RunKernelTransitionError(
                "live search validation parent current contract version is stale"
            )
        if parent_current_contract_digest and (
            parent_current_contract_digest != current_ref.get("contract_digest")
        ):
            raise RunKernelTransitionError(
                "live search validation parent current contract digest is stale"
            )
        if handoff_id and handoff_id != handoff_ref.get("handoff_id"):
            raise RunKernelTransitionError(
                "live search validation handoff_id is stale"
            )
        if handoff_digest and handoff_digest != handoff_ref.get("handoff_digest"):
            raise RunKernelTransitionError(
                "live search validation handoff_digest is stale"
            )

        selected_ids = _preserve_text_list(selected_search_task_ids)
        if not selected_ids:
            raise RunKernelTransitionError(
                "live search validation requires selected_search_task_ids"
            )
        if len(selected_ids) != len(set(selected_ids)):
            raise RunKernelTransitionError(
                "live search validation selected search_task_ids must be unique"
            )
        if len(selected_ids) > LIVE_SEARCH_VALIDATION_MAX_SELECTED_TASKS:
            raise RunKernelTransitionError(
                "live search validation selected task count exceeds PR1 cap"
            )
        known_task_ids = {
            _clean_text(task.get("search_task_id"), limit=260)
            for task in self.state.search_executor_handoff_state.get(
                "search_task_records",
                [],
            )
            if isinstance(task, Mapping)
        }
        missing_task_ids = [
            task_id for task_id in selected_ids if task_id not in known_task_ids
        ]
        if missing_task_ids:
            raise RunKernelTransitionError(
                "live search validation selected task ids are missing from "
                "SearchExecutorHandoff: "
                + ", ".join(missing_task_ids)
            )
        clean_provider = _clean_text(provider_authorized, limit=120)
        if not clean_provider:
            raise RunKernelTransitionError(
                "live search validation requires explicit provider_authorized"
            )
        clean_provider_call_cap = _live_validation_positive_int(
            provider_call_cap,
            "live search validation requires provider_call_cap",
        )
        clean_results_cap = _live_validation_positive_int(
            results_per_task_cap,
            "live search validation requires results_per_task_cap",
        )
        if (
            clean_provider_call_cap
            > LIVE_SEARCH_VALIDATION_DEFAULT_PROVIDER_CALL_CAP
        ):
            raise RunKernelTransitionError(
                "live search validation provider_call_cap exceeds PR1 default"
            )
        if (
            clean_results_cap
            > LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP
        ):
            raise RunKernelTransitionError(
                "live search validation results_per_task_cap exceeds explicit cap"
            )
        if raw_provider_payload_retained is not False:
            raise RunKernelTransitionError(
                "live search validation requires raw_provider_payload_retained false"
            )
        if raw_search_response_retained is not False:
            raise RunKernelTransitionError(
                "live search validation requires raw_search_response_retained false"
            )
        if no_fetch_read_policy_active is not True:
            raise RunKernelTransitionError(
                "live search validation requires no_fetch_read_policy_active true"
            )
        _reject_live_validation_closed_surface_inputs(inputs or {})
        merged_inputs = {
            **dict(inputs or {}),
            "run_id": self.state.run_id,
            "request_id": request_id or self.state.request_id,
            "stage": LIVE_SEARCH_VALIDATION_STAGE,
            "action_type": ActionType.LIVE_SEARCH_VALIDATE.value,
            "expected_observation_type": ObservationType.LIVE_SEARCH_VALIDATED.value,
            "schema_version": LIVE_SEARCH_VALIDATION_SCHEMA_VERSION,
            "parent_current_contract_version": current_ref.get("contract_version"),
            "parent_current_contract_digest": current_ref.get("contract_digest"),
            "handoff_id": handoff_ref.get("handoff_id"),
            "handoff_digest": handoff_ref.get("handoff_digest"),
            "selected_search_task_ids": selected_ids,
            "provider_authorized": clean_provider,
            "provider_call_cap": clean_provider_call_cap,
            "results_per_task_cap": clean_results_cap,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
            "no_fetch_read_policy_active": True,
            "reason": reason,
        }
        return self.authorize(
            stage=LIVE_SEARCH_VALIDATION_STAGE,
            action_type=ActionType.LIVE_SEARCH_VALIDATE,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
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

    def initialize_multicomponent_graph_scheduler(
        self,
        *,
        component_analyst_input_packets: Mapping[str, Mapping[str, Any]],
        requested_synthesis_directive: str,
        configured_provider: str = "OpenAI",
        specialist_capability_registry: Any | None = None,
        specialist_execution_policy: Any | None = None,
    ) -> dict[str, Any]:
        """Initialize the qualifying lane's RunKernel-owned V2/V3 scheduler."""

        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
            derive_multicomponent_transport_profile,
        )
        from core.multicomponent_role_runtime import safe_packet_digest
        from core.specialist_graph_runtime import (
            SpecialistCapabilityRegistry,
            SpecialistExecutionPolicy,
        )

        if self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE):
            raise RunKernelTransitionError("multi-component scheduler already exists")
        contract = _safe_mapping(
            self.state.current_answer_contract or self.state.initial_answer_contract
        )
        component_refs = [
            _safe_mapping(item)
            for item in contract.get("accepted_answer_component_refs") or ()
        ]
        component_by_id = {
            str(item.get("component_id") or ""): item for item in component_refs
        }
        packets = {
            str(key): _safe_mapping(value)
            for key, value in component_analyst_input_packets.items()
        }
        if not component_by_id or set(packets) != set(component_by_id):
            raise RunKernelTransitionError(
                "scheduler initialization requires one exact packet per accepted component"
            )
        ledger_candidate_ids = {
            str(_safe_mapping(item).get("candidate_id") or "")
            for item in self.state.evidence_ledger.to_projection().to_dict().get(
                "candidate_records", ()
            )
            if _safe_mapping(item).get("candidate_id")
        }
        for component_id, packet in packets.items():
            binding = _safe_mapping(packet.get("run_binding"))
            packet_component = _safe_mapping(packet.get("component_ref"))
            evidence = _safe_mapping(packet.get("component_evidence"))
            custody = _safe_mapping(evidence.get("candidate_custody_ref"))
            accepted_component = component_by_id[component_id]
            if (
                binding.get("run_id") != self.state.run_id
                or binding.get("request_id") != self.state.request_id
                or binding.get("accepted_contract_version")
                != contract.get("accepted_contract_version")
                or binding.get("accepted_contract_digest")
                != contract.get("accepted_contract_digest")
                or packet_component.get("component_id") != component_id
                or packet_component.get("component_revision")
                != accepted_component.get("component_revision")
                or packet_component.get("component_digest")
                != accepted_component.get("component_digest")
                or evidence.get("evidence_status") != "available"
                or evidence.get("evidence_ref_id") not in ledger_candidate_ids
                or custody.get("candidate_id") != evidence.get("evidence_ref_id")
            ):
                raise RunKernelTransitionError(
                    "scheduler component packet is not current canonical input"
                )
        directive = _clean_text(requested_synthesis_directive, limit=360)
        metadata = _safe_mapping(contract.get("question_meaning_metadata"))
        if not directive or directive != _clean_text(
            metadata.get("requested_synthesis_directive"), limit=360
        ):
            raise RunKernelTransitionError(
                "scheduler synthesis directive is not current contract authority"
            )
        specialist_injected = (
            specialist_capability_registry is not None
            or specialist_execution_policy is not None
        )
        if specialist_injected and not (
            isinstance(specialist_capability_registry, SpecialistCapabilityRegistry)
            and isinstance(specialist_execution_policy, SpecialistExecutionPolicy)
        ):
            raise RunKernelTransitionError(
                "Specialist scheduler injection requires an exact registry and policy"
            )
        registry_projection = (
            specialist_capability_registry.projection()
            if specialist_injected
            else {}
        )
        policy_projection = (
            specialist_execution_policy.projection()
            if specialist_injected
            else {}
        )
        self.state.multicomponent_scheduler_context = {
            "requested_synthesis_directive": directive,
            "component_analyst_input_packets": deepcopy(packets),
            "recovery_bindings": {},
            "configured_provider_class": derive_multicomponent_transport_profile(
                configured_provider
            )["configured_provider_class"],
            "specialist_scheduler_enabled": specialist_injected,
            "specialist_registry_projection": deepcopy(registry_projection),
            "specialist_execution_policy_projection": deepcopy(policy_projection),
        }
        action = self.authorize(
            stage=MULTICOMPONENT_SCHEDULER_STAGE,
            action_type=ActionType.MULTICOMPONENT_SCHEDULER_INITIALIZE,
            reason="ordinary_multicomponent_scheduler_initialize",
            inputs={
                "component_input_packet_digests": {
                    key: safe_packet_digest(value) for key, value in packets.items()
                },
                "requested_synthesis_directive_digest": safe_packet_digest(
                    {"requested_synthesis_directive": directive}
                ),
                "configured_provider_class": self.state.multicomponent_scheduler_context[
                    "configured_provider_class"
                ],
                "specialist_scheduler_enabled": specialist_injected,
                "specialist_registry_digest": registry_projection.get(
                    "registry_digest"
                ),
                "specialist_execution_policy_digest": policy_projection.get(
                    "execution_policy_digest"
                ),
            },
            expected_observation_type=(
                ObservationType.MULTICOMPONENT_SCHEDULER_INITIALIZED
            ),
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        return deepcopy(self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE])

    def grant_next_multicomponent_work_lease(self) -> dict[str, Any]:
        """Rederive readiness and grant or canonically deny its first item."""

        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
            derive_ready_work,
        )

        ready = derive_ready_work(self.state)
        if not ready:
            raise RunKernelTransitionError("scheduler has no current ready work")
        action = self.authorize(
            stage=(
                f"{MULTICOMPONENT_SCHEDULER_STAGE}:grant:"
                f"{self.state.next_action_sequence}"
            ),
            action_type=ActionType.MULTICOMPONENT_LEASE_GRANT,
            reason="ordinary_multicomponent_next_current_work_lease",
            inputs={"expected_first_ready_work": deepcopy(ready[0])},
            expected_observation_type=ObservationType.MULTICOMPONENT_LEASE_GRANTED,
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        scheduler = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
        )
        return deepcopy(dict((scheduler.get("lease_history") or [{}])[-1]))

    def bind_specialist_need_from_role_artifact(
        self,
        *,
        role_artifact: Mapping[str, Any],
        canonical_target_ref: Mapping[str, Any],
        specialist_capability_registry: Any,
        specialist_execution_policy: Any,
        scrutineer_leaf_target_authorized: bool = False,
    ) -> dict[str, Any]:
        """Bind one optional role proposal without delegating authority to it."""

        from core.component_work_graph_v1 import COMPONENT_WORK_GRAPH_V1_STAGE
        from core.multicomponent_role_runtime import (
            role_artifact_ref,
            validate_multicomponent_role_artifact,
        )
        from core.specialist_graph_runtime import (
            SpecialistCapabilityRegistry,
            SpecialistExecutionPolicy,
            bind_specialist_need_proposal,
        )

        artifact = validate_multicomponent_role_artifact(role_artifact)
        proposal = _safe_mapping(
            _safe_mapping(artifact.get("semantic_output")).get(
                "specialist_need_proposal"
            )
        )
        if not proposal:
            return {}
        if not isinstance(
            specialist_capability_registry, SpecialistCapabilityRegistry
        ) or not isinstance(specialist_execution_policy, SpecialistExecutionPolicy):
            raise RunKernelTransitionError(
                "Specialist proposal binding requires injected registry and policy"
            )
        context = _safe_mapping(self.state.multicomponent_scheduler_context)
        registry_projection = specialist_capability_registry.projection()
        policy_projection = specialist_execution_policy.projection()
        if (
            context.get("specialist_scheduler_enabled") is not True
            or _safe_mapping(context.get("specialist_registry_projection"))
            != registry_projection
            or _safe_mapping(context.get("specialist_execution_policy_projection"))
            != policy_projection
        ):
            raise RunKernelTransitionError(
                "Specialist proposal binding registry/policy is not scheduler authority"
            )
        contract = _safe_mapping(
            self.state.current_answer_contract or self.state.initial_answer_contract
        )
        contract_ref = {
            "run_id": self.state.run_id,
            "request_id": self.state.request_id,
            "accepted_contract_version": contract.get("accepted_contract_version"),
            "accepted_contract_digest": contract.get("accepted_contract_digest"),
        }
        graph = _safe_mapping(
            self.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
        )
        graph_ref = (
            {
                "graph_id": graph.get("graph_id"),
                "graph_revision": graph.get("graph_revision"),
                "graph_digest": graph.get("graph_digest"),
            }
            if graph
            else {}
        )
        bound = bind_specialist_need_proposal(
            run_id=self.state.run_id,
            request_id=self.state.request_id,
            origin_role=str(artifact.get("role") or ""),
            origin_action_ref=_safe_mapping(artifact.get("authorized_action_ref")),
            origin_artifact_ref=role_artifact_ref(artifact),
            proposal=proposal,
            canonical_target_ref=canonical_target_ref,
            accepted_contract_ref=contract_ref,
            graph_ref=graph_ref,
            registry=specialist_capability_registry,
            policy=specialist_execution_policy,
            scrutineer_leaf_target_authorized=scrutineer_leaf_target_authorized,
        )
        action = self.authorize(
            stage=f"specialist_proposal:{bound['proposal_id']}",
            action_type=ActionType.SPECIALIST_PROPOSAL_BIND,
            reason="runkernel_bind_specialist_need_proposal",
            inputs={
                "proposal_id": bound["proposal_id"],
                "proposal_digest": bound["proposal_digest"],
                "origin_action_id": _safe_mapping(
                    artifact.get("authorized_action_ref")
                ).get("action_id"),
                "registry_digest": registry_projection["registry_digest"],
                "execution_policy_digest": policy_projection[
                    "execution_policy_digest"
                ],
            },
            expected_observation_type=ObservationType.SPECIALIST_PROPOSAL_BOUND,
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"bound_specialist_proposal": bound},
            )
        )
        return deepcopy(bound)

    def consume_specialist_handoff_by_dprime(
        self,
        *,
        handoff_id: str,
        dprime_artifact_ref: Mapping[str, Any],
    ) -> dict[str, Any]:
        from core.specialist_graph_runtime import (
            SPECIALIST_WORK_PLANE_STAGE,
            handoff_by_id,
        )

        handoff = handoff_by_id(
            _safe_mapping(
                self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE)
            ),
            handoff_id=handoff_id,
        )
        if not handoff:
            raise RunKernelTransitionError(
                "D-prime consumption requires a retained Specialist handoff"
            )
        action = self.authorize(
            stage=f"specialist_validator_consumption:{handoff_id}",
            action_type=ActionType.SPECIALIST_VALIDATOR_CONSUME,
            reason="relevant_dprime_consume_exact_specialist_need_handoff",
            inputs={
                "handoff_id": handoff_id,
                "handoff_digest": handoff.get("handoff_digest"),
                "dprime_artifact_ref": deepcopy(dict(dprime_artifact_ref)),
            },
            expected_observation_type=ObservationType.SPECIALIST_VALIDATOR_CONSUMED,
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        return deepcopy(self.state.projections[SPECIALIST_WORK_PLANE_STAGE])

    def dispose_exhausted_optional_specialist_proposals(self) -> int:
        """Record each optional accepted need that cannot receive another unit."""

        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
        )
        from core.specialist_graph_runtime import (
            PROPOSAL_ACCEPTED,
            SPECIALIST_WORK_PLANE_STAGE,
        )

        plane = _safe_mapping(
            self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE)
        )
        scheduler = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
        )
        pool = _safe_mapping(scheduler.get("specialist_compatibility_pool"))
        if (
            not plane
            or int(pool.get("specialist_remaining") or 0) != 0
            or int(pool.get("specialist_spent") or 0) < 1
        ):
            return 0
        disposed_ids = {
            _safe_mapping(_safe_mapping(item).get("proposal_ref")).get(
                "proposal_id"
            )
            for item in plane.get("proposal_dispositions") or ()
        }
        active_ids = {
            _safe_mapping(_safe_mapping(item).get("work"))
            .get("specialist_proposal_ref", {})
            .get("proposal_id")
            for item in scheduler.get("lease_history") or ()
            if _safe_mapping(item).get("status")
            in {"granted_reserved", "execution_started_spent"}
        }
        candidates = [
            _safe_mapping(item)
            for item in plane.get("proposals") or ()
            if _safe_mapping(item).get("proposal_authority")
            == PROPOSAL_ACCEPTED
            and _safe_mapping(item).get("posture") == "optional"
            and _safe_mapping(item).get("proposal_id") not in disposed_ids
            and _safe_mapping(item).get("proposal_id") not in active_ids
        ]
        count = 0
        for proposal in candidates:
            action = self.authorize(
                stage=f"specialist_disposition:{proposal['proposal_id']}",
                action_type=ActionType.SPECIALIST_PROPOSAL_DISPOSE,
                reason="optional_specialist_pool_exhausted",
                inputs={
                    "proposal_id": proposal["proposal_id"],
                    "proposal_digest": proposal["proposal_digest"],
                    "nonexecution_reason": "specialist_pool_exhausted",
                },
                expected_observation_type=(
                    ObservationType.SPECIALIST_PROPOSAL_DISPOSED
                ),
            )
            self.reduce(
                Observation.from_action(
                    action,
                    observation_type=action.expected_observation_type,
                    status=RunStageStatus.COMPLETED,
                    payload={},
                )
            )
            count += 1
        return count

    def dispose_failed_specialist_reconstruction(
        self, *, work: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Record one exact cancelled predispatch reconstruction failure."""

        from core.specialist_graph_runtime import SPECIALIST_WORK_PLANE_STAGE

        item = _safe_mapping(work)
        proposal_ref = _safe_mapping(item.get("specialist_proposal_ref"))
        action = self.authorize(
            stage=f"specialist_disposition:{proposal_ref.get('proposal_id')}",
            action_type=ActionType.SPECIALIST_PROPOSAL_DISPOSE,
            reason="specialist_input_reconstruction_failed_predispatch",
            inputs={
                "proposal_id": proposal_ref.get("proposal_id"),
                "proposal_digest": proposal_ref.get("proposal_digest"),
                "work_id": item.get("work_id"),
                "work_digest": item.get("work_digest"),
                "nonexecution_reason": "input_reconstruction_failed",
            },
            expected_observation_type=(
                ObservationType.SPECIALIST_PROPOSAL_DISPOSED
            ),
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        return deepcopy(
            self.state.projections[SPECIALIST_WORK_PLANE_STAGE][
                "proposal_dispositions"
            ][-1]
        )

    def derive_current_multicomponent_ready_work(self) -> list[dict[str, Any]]:
        """Return RunKernel's exact current scheduler readiness projection."""

        from core.multicomponent_graph_scheduling import derive_ready_work

        return deepcopy(derive_ready_work(self.state))

    def grant_next_multicomponent_work_batch(self) -> dict[str, Any]:
        """Rederive and atomically reserve the exact V2 contiguous prefix."""

        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
            derive_ready_batch_work,
            derive_ready_work,
        )

        ready = derive_ready_work(self.state)
        if not ready:
            raise RunKernelTransitionError("scheduler has no current ready work")
        batch_work = derive_ready_batch_work(self.state)
        action = self.authorize(
            stage=(
                f"{MULTICOMPONENT_SCHEDULER_STAGE}:batch-grant:"
                f"{self.state.next_action_sequence}"
            ),
            action_type=ActionType.MULTICOMPONENT_BATCH_GRANT,
            reason="ordinary_multicomponent_next_current_work_batch",
            inputs={
                "expected_first_ready_work": deepcopy(ready[0]),
                "expected_batch_work": deepcopy(batch_work),
            },
            expected_observation_type=ObservationType.MULTICOMPONENT_BATCH_GRANTED,
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        scheduler = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
        )
        return deepcopy(dict((scheduler.get("batch_history") or [{}])[-1]))

    def cancel_multicomponent_work_batch(
        self,
        *,
        batch_id: str,
        reason: str = "predispatch_batch_cancellation",
    ) -> dict[str, Any]:
        """Atomically return every granted reservation in one V2 batch."""

        from core.multicomponent_graph_scheduling import MULTICOMPONENT_SCHEDULER_STAGE

        action = self.authorize(
            stage=(
                f"{MULTICOMPONENT_SCHEDULER_STAGE}:batch-cancel:"
                f"{self.state.next_action_sequence}"
            ),
            action_type=ActionType.MULTICOMPONENT_BATCH_CANCEL,
            reason="ordinary_multicomponent_predispatch_batch_return",
            inputs={"batch_id": batch_id, "cancellation_reason": reason},
            expected_observation_type=ObservationType.MULTICOMPONENT_BATCH_CANCELLED,
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        return deepcopy(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
        )

    @staticmethod
    def _multicomponent_role_action_contract(
        role: str,
    ) -> tuple[ActionType, ObservationType]:
        role_types = {
            "component_analyst": (
                ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
                ObservationType.MULTICOMPONENT_COMPONENT_ANALYST_COMPLETED,
            ),
            "component_dprime": (
                ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
                ObservationType.MULTICOMPONENT_COMPONENT_DPRIME_COMPLETED,
            ),
            "cross_component_analyst": (
                ActionType.MULTICOMPONENT_CROSS_ANALYST_EXECUTE,
                ObservationType.MULTICOMPONENT_CROSS_ANALYST_COMPLETED,
            ),
            "synthesis_dprime": (
                ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE,
                ObservationType.MULTICOMPONENT_SYNTHESIS_DPRIME_COMPLETED,
            ),
            "scrutineer": (
                ActionType.MULTICOMPONENT_SCRUTINEER_EXECUTE,
                ObservationType.MULTICOMPONENT_SCRUTINEER_COMPLETED,
            ),
            "specialist_capability": (
                ActionType.SPECIALIST_CAPABILITY_EXECUTE,
                ObservationType.SPECIALIST_CAPABILITY_COMPLETED,
            ),
        }
        try:
            return role_types[role]
        except KeyError as exc:
            raise RunKernelTransitionError(
                "unknown multi-component semantic role"
            ) from exc

    def _build_multicomponent_private_child_descriptor(
        self,
        *,
        batch: Mapping[str, Any],
        lease: Mapping[str, Any],
        batch_index: int,
    ) -> dict[str, Any]:
        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION,
        )
        from core.multicomponent_role_runtime import safe_packet_digest

        work = _safe_mapping(lease.get("work"))
        action_type, observation_type = self._multicomponent_role_action_contract(
            str(work.get("role") or "")
        )
        descriptor_core = {
            "schema_version": MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SCHEMA_VERSION,
            "batch_id": batch.get("batch_id"),
            "batch_digest": batch.get("batch_digest"),
            "batch_index": batch_index,
            "work_id": work.get("work_id"),
            "work_digest": work.get("work_digest"),
            "lease_id": lease.get("lease_id"),
            "lease_digest": lease.get("lease_digest"),
            "role": work.get("role"),
            "action_type": action_type.value,
            "expected_observation_type": observation_type.value,
            "logical_evaluation_key": work.get("logical_evaluation_key"),
            "input_packet_digest": work.get("input_packet_digest"),
            "output_schema_variant": work.get("output_schema_variant"),
            "safe_target_ref": {
                "target_kind": work.get("target_kind"),
                "component_id": work.get("component_id"),
                "synthesis_key": work.get("synthesis_key"),
                "node_ref": deepcopy(work.get("node_ref")),
            },
            "authority_refs": {
                "accepted_contract_ref": deepcopy(work.get("accepted_contract_ref")),
                "graph_ref": deepcopy(work.get("graph_ref")),
                "recovery_authorization_ref": deepcopy(
                    work.get("recovery_authorization_ref")
                ),
                "contract_amendment_admission_ref": deepcopy(
                    work.get("contract_amendment_admission_ref")
                ),
                "contract_amendment_application_ref": deepcopy(
                    work.get("contract_amendment_application_ref")
                ),
                "selective_closure_ref": deepcopy(work.get("selective_closure_ref")),
            },
            "expected_action_stage_seed": (
                f"specialist_capability:{work.get('logical_evaluation_key')}"
                if work.get("role") == "specialist_capability"
                else (
                    f"multicomponent_role:{work.get('role')}:"
                    f"{work.get('logical_evaluation_key')}"
                )
            ),
        }
        return {
            **descriptor_core,
            "descriptor_digest": safe_packet_digest(descriptor_core),
        }

    def build_multicomponent_private_child_descriptor_set(
        self,
        *,
        batch_id: str,
        packet_digests: Sequence[str],
    ) -> dict[str, Any]:
        """Build a complete transient descriptor set without canonical mutation."""

        from core.multicomponent_graph_scheduling import (
            LEASE_GRANTED,
            MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SET_SCHEMA_VERSION,
            MULTICOMPONENT_ROLE_CALL_LIMITS,
            MULTICOMPONENT_SCHEDULER_STAGE,
            validate_scheduler_state,
            work_is_current,
        )
        from core.multicomponent_role_runtime import safe_packet_digest

        scheduler = validate_scheduler_state(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
        )
        batch = next(
            (
                deepcopy(dict(item))
                for item in scheduler.get("batch_history") or ()
                if dict(item).get("batch_id") == batch_id
            ),
            {},
        )
        if batch.get("status") != LEASE_GRANTED:
            raise RunKernelTransitionError("scheduler batch is not granted")
        lease_refs = [
            deepcopy(dict(item)) for item in batch.get("ordered_lease_refs") or ()
        ]
        leases = [
            next(
                deepcopy(dict(item))
                for item in scheduler.get("lease_history") or ()
                if dict(item).get("lease_id") == ref.get("lease_id")
            )
            for ref in lease_refs
        ]
        if len(leases) != len(packet_digests) or any(
            lease.get("status") != LEASE_GRANTED for lease in leases
        ):
            raise RunKernelTransitionError(
                "private descriptor preparation requires every granted lease"
            )
        prior_counts: dict[str, int] = {}
        batch_counts: dict[str, int] = {}
        seen_keys: set[tuple[str, str]] = set()
        descriptors: list[dict[str, Any]] = []
        for batch_index, (lease, packet_digest) in enumerate(
            zip(leases, packet_digests, strict=True)
        ):
            work = deepcopy(dict(lease.get("work") or {}))
            role = str(work.get("role") or "")
            action_type, _observation_type = self._multicomponent_role_action_contract(role)
            key = str(work.get("logical_evaluation_key") or "")
            if (
                packet_digest != work.get("input_packet_digest")
                or not work_is_current(self.state, work)
                or (role, key) in seen_keys
            ):
                raise RunKernelTransitionError(
                    "private descriptor packet or logical binding is not current"
                )
            seen_keys.add((role, key))
            if role not in prior_counts:
                prior = [
                    item
                    for item in self.state.issued_actions.values()
                    if item.action_type is action_type
                ]
                if any(
                    item.inputs.get("logical_evaluation_key") == key for item in prior
                ):
                    raise RunKernelTransitionError(
                        "multi-component role logical evaluation key is duplicate"
                    )
                prior_counts[role] = len(prior)
            batch_counts[role] = batch_counts.get(role, 0) + 1
            if (
                role != "specialist_capability"
                and prior_counts[role] + batch_counts[role]
                > MULTICOMPONENT_ROLE_CALL_LIMITS[role]
            ):
                raise RunKernelTransitionError(
                    "multi-component batch exceeds the shared role cap"
                )
            descriptors.append(
                self._build_multicomponent_private_child_descriptor(
                    batch=batch,
                    lease=lease,
                    batch_index=batch_index,
                )
            )
        descriptor_set_core = {
            "schema_version": MULTICOMPONENT_CHILD_ACTION_DESCRIPTOR_SET_SCHEMA_VERSION,
            "batch_id": batch.get("batch_id"),
            "batch_digest": batch.get("batch_digest"),
            "ordered_descriptors": descriptors,
        }
        return {
            **descriptor_set_core,
            "descriptor_set_digest": safe_packet_digest(descriptor_set_core),
        }

    def _materialize_multicomponent_child_action(
        self,
        *,
        descriptor: Mapping[str, Any],
        lease: Mapping[str, Any],
        dispatch_action_ref: Mapping[str, Any],
        sequence: int,
    ) -> AuthorizedAction:
        work = deepcopy(dict(lease.get("work") or {}))
        role = str(work.get("role") or "")
        action_type, observation_type = self._multicomponent_role_action_contract(role)
        stage = str(descriptor.get("expected_action_stage_seed") or "")
        action_id = f"{self.state.run_id}:action:{sequence}:{action_type.value}"
        specialist_work_node = deepcopy(work.get("specialist_work_node"))
        if role == "specialist_capability":
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
            )
            from core.specialist_graph_runtime import (
                bind_specialist_work_authority,
            )

            pool = _safe_mapping(
                _safe_mapping(
                    self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
                ).get("specialist_compatibility_pool")
            )
            specialist_work_node = bind_specialist_work_authority(
                _safe_mapping(specialist_work_node),
                authorization_action_ref={
                    "action_id": action_id,
                    "stage": stage,
                    "sequence": sequence,
                    "observation_type": observation_type.value,
                },
                grant_action_ref=_safe_mapping(lease.get("grant_action_ref")),
                dispatch_action_ref=dispatch_action_ref,
                lease_ref={
                    "lease_id": lease.get("lease_id"),
                    "lease_digest": lease.get("lease_digest"),
                    "batch_id": lease.get("batch_id"),
                    "batch_digest": lease.get("batch_digest"),
                },
                specialist_budget_ref={
                    "specialist_work_item_limit": pool.get(
                        "specialist_work_item_limit"
                    ),
                    "specialist_total": pool.get("specialist_total"),
                },
            )
        return AuthorizedAction(
            action_id=action_id,
            run_id=self.state.run_id,
            stage=stage,
            action_type=action_type,
            reason=(
                "ordinary_multicomponent_registered_deterministic_specialist_execution"
                if role == "specialist_capability"
                else "ordinary_multicomponent_semantic_role_execution"
            ),
            inputs={
                "role": role,
                "input_packet_digest": work.get("input_packet_digest"),
                "logical_evaluation_key": work.get("logical_evaluation_key"),
                "supported_query_class": (
                    "ordinary-bounded-multicomponent-factual-synthesis-v1"
                ),
                "batch_id": descriptor.get("batch_id"),
                "batch_digest": descriptor.get("batch_digest"),
                "batch_index": descriptor.get("batch_index"),
                "descriptor_digest": descriptor.get("descriptor_digest"),
                "lease_id": lease.get("lease_id"),
                "lease_digest": lease.get("lease_digest"),
                "work_id": work.get("work_id"),
                "work_digest": work.get("work_digest"),
                "grant_action_ref": deepcopy(lease.get("grant_action_ref")),
                "dispatch_action_ref": deepcopy(dict(dispatch_action_ref)),
                "accepted_contract_ref": deepcopy(work.get("accepted_contract_ref")),
                "graph_ref": deepcopy(work.get("graph_ref")),
                "target_kind": work.get("target_kind"),
                "component_id": work.get("component_id"),
                "synthesis_key": work.get("synthesis_key"),
                "node_ref": deepcopy(work.get("node_ref")),
                "recovery_authorization_ref": deepcopy(
                    work.get("recovery_authorization_ref")
                ),
                "contract_amendment_admission_ref": deepcopy(
                    work.get("contract_amendment_admission_ref")
                ),
                "contract_amendment_application_ref": deepcopy(
                    work.get("contract_amendment_application_ref")
                ),
                "selective_closure_ref": deepcopy(work.get("selective_closure_ref")),
                "scheduler_revision_at_grant": lease.get(
                    "scheduler_revision_at_grant"
                ),
                "output_schema_variant": work.get("output_schema_variant"),
                "work_kind": work.get("work_kind"),
                "resource_class": work.get("resource_class"),
                "executor_class": work.get("executor_class"),
                "capability_id": work.get("capability_id"),
                "capability_version": work.get("capability_version"),
                "capability_descriptor_digest": work.get(
                    "capability_descriptor_digest"
                ),
                "specialist_proposal_ref": deepcopy(
                    work.get("specialist_proposal_ref")
                ),
                "specialist_work_node": specialist_work_node,
            },
            expected_observation_type=observation_type,
            sequence=sequence,
        )

    def commit_multicomponent_batch_dispatch(
        self,
        *,
        batch_id: str,
        packet_digests: Sequence[str],
    ) -> tuple[AuthorizedAction, ...]:
        """Atomically commit dispatch and publish all ordered child actions."""

        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
            validate_scheduler_state,
        )

        try:
            descriptor_set = self.build_multicomponent_private_child_descriptor_set(
                batch_id=batch_id,
                packet_digests=packet_digests,
            )
            scheduler = validate_scheduler_state(
                self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
            )
            batch = next(
                deepcopy(dict(item))
                for item in scheduler.get("batch_history") or ()
                if dict(item).get("batch_id") == batch_id
            )
            leases_by_id = {
                str(dict(item).get("lease_id") or ""): deepcopy(dict(item))
                for item in scheduler.get("lease_history") or ()
            }
            dispatch_sequence = self.state.next_action_sequence
            dispatch_stage = (
                f"{MULTICOMPONENT_SCHEDULER_STAGE}:batch-dispatch:"
                f"{dispatch_sequence}"
            )
            dispatch_action_id = (
                f"{self.state.run_id}:action:{dispatch_sequence}:"
                f"{ActionType.MULTICOMPONENT_BATCH_DISPATCH.value}"
            )
            dispatch_action_ref = {
                "action_id": dispatch_action_id,
                "stage": dispatch_stage,
                "sequence": dispatch_sequence,
                "observation_type": (
                    ObservationType.MULTICOMPONENT_BATCH_DISPATCHED.value
                ),
            }
            private_actions = tuple(
                self._materialize_multicomponent_child_action(
                    descriptor=descriptor,
                    lease=leases_by_id[str(descriptor.get("lease_id") or "")],
                    dispatch_action_ref=dispatch_action_ref,
                    sequence=dispatch_sequence + batch_index + 1,
                )
                for batch_index, descriptor in enumerate(
                    descriptor_set["ordered_descriptors"]
                )
            )
        except Exception:
            self.cancel_multicomponent_work_batch(
                batch_id=batch_id,
                reason="private_child_descriptor_preparation_failed",
            )
            raise
        dispatch_action = self.authorize(
            stage=dispatch_stage,
            action_type=ActionType.MULTICOMPONENT_BATCH_DISPATCH,
            reason="ordinary_multicomponent_atomic_batch_pretransport_commitment",
            inputs={
                "batch_id": batch.get("batch_id"),
                "batch_digest": batch.get("batch_digest"),
                "descriptor_set_digest": descriptor_set.get("descriptor_set_digest"),
            },
            expected_observation_type=ObservationType.MULTICOMPONENT_BATCH_DISPATCHED,
        )
        if dispatch_action.action_id != dispatch_action_id:
            raise RunKernelTransitionError("batch dispatch action sequence changed")
        self._pending_multicomponent_batch_dispatch = {
            "dispatch_action_id": dispatch_action.action_id,
            "descriptor_set": descriptor_set,
            "private_actions": private_actions,
            "packet_digests": tuple(packet_digests),
        }
        try:
            self.reduce(
                Observation.from_action(
                    dispatch_action,
                    observation_type=dispatch_action.expected_observation_type,
                    status=RunStageStatus.COMPLETED,
                    payload={},
                )
            )
        finally:
            self.__dict__.pop("_pending_multicomponent_batch_dispatch", None)
        scheduler = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
        )
        committed = next(
            _safe_mapping(item)
            for item in scheduler.get("batch_history") or ()
            if _safe_mapping(item).get("batch_id") == batch_id
        )
        if committed.get("status") != "dispatch_committed":
            raise RunKernelTransitionError("batch dispatch failed before child publication")
        return private_actions

    def prepare_multicomponent_role_dispatch(
        self,
        *,
        lease_id: str,
        role: str,
        input_packet_digest: str,
        logical_evaluation_key: str,
        output_schema_variant: str | None = None,
    ) -> AuthorizedAction:
        """Issue the role action and reduce its exact pretransport spend."""

        from core.multicomponent_graph_scheduling import (
            LEASE_GRANTED,
            MULTICOMPONENT_SCHEDULER_STAGE,
            validate_scheduler_state,
        )

        scheduler = validate_scheduler_state(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
        )
        lease = next(
            (
                _safe_mapping(item)
                for item in scheduler.get("lease_history") or ()
                if _safe_mapping(item).get("lease_id") == lease_id
            ),
            {},
        )
        work = _safe_mapping(lease.get("work"))
        if lease.get("status") != LEASE_GRANTED:
            raise RunKernelTransitionError("scheduler lease is not granted")
        if (
            work.get("role") != role
            or work.get("input_packet_digest") != input_packet_digest
            or work.get("logical_evaluation_key") != logical_evaluation_key
            or work.get("output_schema_variant") != output_schema_variant
        ):
            raise RunKernelTransitionError(
                "requested semantic dispatch does not equal scheduler-selected work"
            )
        dispatch_action = self.authorize(
            stage=(
                f"{MULTICOMPONENT_SCHEDULER_STAGE}:dispatch:"
                f"{self.state.next_action_sequence}"
            ),
            action_type=ActionType.MULTICOMPONENT_LEASE_DISPATCH,
            reason="ordinary_multicomponent_canonical_pretransport_commitment",
            inputs={
                "lease_id": lease.get("lease_id"),
                "lease_digest": lease.get("lease_digest"),
                "work_id": work.get("work_id"),
                "work_digest": work.get("work_digest"),
            },
            expected_observation_type=(
                ObservationType.MULTICOMPONENT_LEASE_DISPATCHED
            ),
        )
        role_action = self.authorize_multicomponent_role_call(
            role=role,
            input_packet_digest=input_packet_digest,
            logical_evaluation_key=logical_evaluation_key,
            lease_id=lease_id,
            dispatch_action_id=dispatch_action.action_id,
            output_schema_variant=output_schema_variant,
        )
        role_action_ref = {
            "action_id": role_action.action_id,
            "stage": role_action.stage,
            "sequence": role_action.sequence,
            "observation_type": role_action.expected_observation_type.value,
            "role": role_action.inputs.get("role"),
            "logical_evaluation_key": role_action.inputs.get(
                "logical_evaluation_key"
            ),
            "input_packet_digest": role_action.inputs.get("input_packet_digest"),
            "lease_id": role_action.inputs.get("lease_id"),
            "lease_digest": role_action.inputs.get("lease_digest"),
            "work_id": role_action.inputs.get("work_id"),
            "work_digest": role_action.inputs.get("work_digest"),
        }
        self.reduce(
            Observation.from_action(
                dispatch_action,
                observation_type=dispatch_action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"role_action_ref": role_action_ref},
            )
        )
        return role_action

    def cancel_multicomponent_work_lease(
        self, *, lease_id: str, reason: str = "predispatch_cancellation"
    ) -> dict[str, Any]:
        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
        )

        action = self.authorize(
            stage=(
                f"{MULTICOMPONENT_SCHEDULER_STAGE}:cancel:"
                f"{self.state.next_action_sequence}"
            ),
            action_type=ActionType.MULTICOMPONENT_LEASE_CANCEL,
            reason="ordinary_multicomponent_predispatch_reservation_return",
            inputs={"lease_id": lease_id, "cancellation_reason": reason},
            expected_observation_type=ObservationType.MULTICOMPONENT_LEASE_CANCELLED,
        )
        self.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={},
            )
        )
        return deepcopy(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
        )

    def _scheduler_after_canonical_authority_transition(
        self,
        *,
        transition: str,
        projection_update: tuple[str, Mapping[str, Any]] | None = None,
        current_answer_contract: Mapping[str, Any] | None = None,
        scheduler_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
            _settle_for_canonical_authority_transition,
        )

        if not self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE):
            return None
        projections = dict(self.state.projections)
        if projection_update is not None:
            stage, projection = projection_update
            projections[stage] = deepcopy(dict(projection))
        candidate_state = SimpleNamespace(
            run_id=self.state.run_id,
            request_id=self.state.request_id,
            projections=projections,
            initial_answer_contract=self.state.initial_answer_contract,
            current_answer_contract=(
                dict(current_answer_contract)
                if current_answer_contract is not None
                else self.state.current_answer_contract
            ),
            multicomponent_scheduler_context=(
                dict(scheduler_context)
                if scheduler_context is not None
                else self.state.multicomponent_scheduler_context
            ),
        )
        return _settle_for_canonical_authority_transition(
            state=candidate_state,
            transition=transition,
        )

    def _pending_multicomponent_authority_supersession(
        self, action: AuthorizedAction
    ) -> dict[str, Any]:
        from core.multicomponent_graph_scheduling import (
            LEASE_EXECUTION_STARTED,
            MULTICOMPONENT_SCHEDULER_STAGE,
            validate_scheduler_state,
        )

        if action.action_type not in {
            ActionType.CONTRACT_AMENDMENT_APPLY,
            ActionType.MULTICOMPONENT_GRAPH_REDUCE,
        }:
            return {}
        scheduler_raw = self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
        if not scheduler_raw:
            return {}
        scheduler = validate_scheduler_state(scheduler_raw)
        active = [
            _safe_mapping(item)
            for item in scheduler.get("lease_history") or ()
            if _safe_mapping(item).get("status") == LEASE_EXECUTION_STARTED
        ]
        if not active or action.sequence != (
            self.state.next_observation_sequence + len(active)
        ):
            return {}
        pending_leases: list[dict[str, Any]] = []
        for offset, lease in enumerate(active):
            role_action_id = str(
                _safe_mapping(lease.get("role_action_ref")).get("action_id") or ""
            )
            role_action = self.state.issued_actions.get(role_action_id)
            if (
                role_action is None
                or role_action.sequence != self.state.next_observation_sequence + offset
                or role_action.action_id in self.state.reduced_action_ids
            ):
                return {}
            pending_leases.append(
                {
                    "lease_id": lease.get("lease_id"),
                    "role_action_id": role_action_id,
                }
            )
        return {
            "pending_leases": pending_leases,
        }

    def _commit_multicomponent_authority_supersession(
        self,
        *,
        pending: Mapping[str, Any],
        scheduler: Mapping[str, Any] | None,
    ) -> None:
        from core.multicomponent_graph_scheduling import LEASE_STALE

        if not pending:
            return
        candidate = _safe_mapping(scheduler)
        resolved: list[tuple[dict[str, Any], AuthorizedAction]] = []
        for pending_lease in pending.get("pending_leases") or ():
            lease = next(
                (
                    _safe_mapping(item)
                    for item in candidate.get("lease_history") or ()
                    if _safe_mapping(item).get("lease_id")
                    == _safe_mapping(pending_lease).get("lease_id")
                ),
                {},
            )
            role_action = self.state.issued_actions.get(
                str(_safe_mapping(pending_lease).get("role_action_id") or "")
            )
            if lease.get("status") != LEASE_STALE or role_action is None:
                raise RunKernelTransitionError(
                    "unrelated authority transition cannot supersede active semantic work"
                )
            resolved.append((lease, role_action))
        for lease, role_action in resolved:
            failure_kind = "canonical_authority_changed_before_role_observation"
            synthetic = Observation.from_action(
                role_action,
                observation_type=role_action.expected_observation_type,
                status=RunStageStatus.FAILED,
                payload={
                    "lease_settlement": LEASE_STALE,
                    "failure_kind": failure_kind,
                },
            )
            self.state.reduced_action_ids.add(role_action.action_id)
            self.state.action_statuses[role_action.action_id] = RunStageStatus.FAILED
            self.state.stage_statuses[role_action.stage] = RunStageStatus.FAILED
            self.state.projections[role_action.stage] = {
                "schema_version": "multicomponent_semantic_role_failure_v1",
                "owner": "RunKernel.MulticomponentGraphScheduler",
                "canonical_state": True,
                "role": role_action.inputs.get("role"),
                "logical_evaluation_key": role_action.inputs.get(
                    "logical_evaluation_key"
                ),
                "work_id": role_action.inputs.get("work_id"),
                "lease_id": role_action.inputs.get("lease_id"),
                "settlement": LEASE_STALE,
                "failure_kind": failure_kind,
                "semantic_artifact_admitted": False,
                "raw_model_response_retained": False,
                "raw_provider_payload_retained": False,
            }
            self.state.observations.append(synthetic)
            self.state.next_observation_sequence += 1

    def _commit_deferred_authority_action(
        self,
        *,
        action: AuthorizedAction,
        observation: Observation,
        pending: Mapping[str, Any],
    ) -> None:
        if not pending:
            return
        self.state.reduced_action_ids.add(action.action_id)
        self.state.action_statuses[action.action_id] = observation.status
        self.state.stage_statuses[action.stage] = observation.status

    def register_multicomponent_recovery_scheduler_context(
        self,
        *,
        component_id: str,
        analyst_input_packet: Mapping[str, Any],
        recovery_authorization_ref: Mapping[str, Any],
        contract_amendment_admission_ref: Mapping[str, Any],
        contract_amendment_application_ref: Mapping[str, Any],
    ) -> None:
        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
        )

        context = _safe_mapping(self.state.multicomponent_scheduler_context)
        if not context or not self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE):
            raise RunKernelTransitionError("recovery requires active scheduler context")
        packet = _safe_mapping(analyst_input_packet)
        binding = _safe_mapping(packet.get("run_binding"))
        component = _safe_mapping(packet.get("component_ref"))
        contract = _safe_mapping(self.state.current_answer_contract)
        accepted = next(
            (
                _safe_mapping(item)
                for item in contract.get("accepted_answer_component_refs") or ()
                if _safe_mapping(item).get("component_id") == component_id
            ),
            {},
        )
        evidence = _safe_mapping(packet.get("component_evidence"))
        custody = _safe_mapping(evidence.get("candidate_custody_ref"))
        ledger_candidate_ids = {
            str(_safe_mapping(item).get("candidate_id") or "")
            for item in self.state.evidence_ledger.to_projection().to_dict().get(
                "candidate_records", ()
            )
            if _safe_mapping(item).get("candidate_id")
        }
        if (
            not accepted
            or binding.get("run_id") != self.state.run_id
            or binding.get("request_id") != self.state.request_id
            or binding.get("accepted_contract_digest")
            != contract.get("accepted_contract_digest")
            or component.get("component_id") != component_id
            or component.get("component_digest") != accepted.get("component_digest")
            or evidence.get("evidence_status") != "available"
            or evidence.get("evidence_ref_id") not in ledger_candidate_ids
            or custody.get("candidate_id") != evidence.get("evidence_ref_id")
        ):
            raise RunKernelTransitionError(
                "recovery scheduler context is not current contract authority"
            )
        authorization = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE)
        )
        amendment_admission = _safe_mapping(
            self.state.contract_amendment_admission_projection
        )
        amendment_application = _safe_mapping(
            self.state.contract_amendment_application_projection
        )
        expected_recovery_authorization_ref = {
            "authorization_id": authorization.get("authorization_id"),
            "authorization_digest": authorization.get("authorization_digest"),
        }
        expected_contract_amendment_admission_ref = {
            "amendment_record_id": amendment_admission.get("amendment_record_id"),
            "amendment_record_digest": amendment_admission.get(
                "amendment_record_digest"
            ),
            "authorized_action_id": amendment_admission.get("authorized_action_id"),
            "admission_digest": amendment_admission.get("admission_digest"),
        }
        expected_contract_amendment_application_ref = {
            "amendment_record_id": amendment_application.get("amendment_record_id"),
            "authorized_action_id": amendment_application.get(
                "authorized_action_id"
            ),
            "application_digest": amendment_application.get("application_digest"),
        }
        if (
            not expected_recovery_authorization_ref["authorization_id"]
            or not expected_recovery_authorization_ref["authorization_digest"]
            or not expected_contract_amendment_admission_ref["admission_digest"]
            or not expected_contract_amendment_application_ref["application_digest"]
            or _safe_mapping(recovery_authorization_ref)
            != expected_recovery_authorization_ref
            or _safe_mapping(contract_amendment_admission_ref)
            != expected_contract_amendment_admission_ref
            or _safe_mapping(contract_amendment_application_ref)
            != expected_contract_amendment_application_ref
        ):
            raise RunKernelTransitionError(
                "recovery scheduler context refs must match canonical "
                "RunKernel projections"
            )
        packets = _safe_mapping(context.get("component_analyst_input_packets"))
        recoveries = _safe_mapping(context.get("recovery_bindings"))
        proposed_packet = deepcopy(packet)
        proposed_recovery = {
            "recovery_authorization_ref": deepcopy(
                expected_recovery_authorization_ref
            ),
            "contract_amendment_admission_ref": deepcopy(
                expected_contract_amendment_admission_ref
            ),
            "contract_amendment_application_ref": deepcopy(
                expected_contract_amendment_application_ref
            ),
        }
        if component_id in recoveries:
            if (
                _safe_mapping(packets.get(component_id)) == proposed_packet
                and _safe_mapping(recoveries.get(component_id)) == proposed_recovery
            ):
                return
            raise RunKernelTransitionError(
                "recovery scheduler context rejects changed duplicate "
                "component registration"
            )
        packets[component_id] = proposed_packet
        recoveries[component_id] = proposed_recovery
        context["component_analyst_input_packets"] = packets
        context["recovery_bindings"] = recoveries
        scheduler = self._scheduler_after_canonical_authority_transition(
            transition="recovery_scheduler_context_registered",
            scheduler_context=context,
        )
        self.state.multicomponent_scheduler_context = context
        if scheduler is not None:
            self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = scheduler

    def complete_multicomponent_graph_scheduler(self) -> dict[str, Any]:
        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
            complete_scheduler,
        )

        self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = complete_scheduler(
            self.state
        )
        return deepcopy(self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE])

    def multicomponent_work_lease_is_current(self, lease_id: str) -> bool:
        from core.multicomponent_graph_scheduling import (
            MULTICOMPONENT_SCHEDULER_STAGE,
            validate_scheduler_state,
            work_is_current,
        )

        scheduler = validate_scheduler_state(
            self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
        )
        lease = next(
            (
                deepcopy(dict(item))
                for item in scheduler.get("lease_history") or ()
                if dict(item).get("lease_id") == lease_id
            ),
            {},
        )
        return bool(
            lease
            and work_is_current(self.state, deepcopy(dict(lease.get("work") or {})))
        )

    def authorize_multicomponent_role_call(
        self,
        *,
        role: str,
        input_packet_digest: str,
        logical_evaluation_key: str,
        lease_id: str | None = None,
        dispatch_action_id: str | None = None,
        output_schema_variant: str | None = None,
    ) -> AuthorizedAction:
        """Authorize one exact semantic-role evaluation for the V1 lane."""

        from core.multicomponent_graph_scheduling import (
            LEASE_GRANTED,
            MULTICOMPONENT_ROLE_CALL_LIMITS,
            MULTICOMPONENT_SCHEDULER_STAGE,
            validate_scheduler_state,
        )
        from core.multicomponent_role_runtime import ROLE_SYSTEM_PROMPTS

        role_name = _clean_text(role, limit=80)
        input_digest = _clean_text(input_packet_digest, limit=128)
        evaluation_key = _clean_text(logical_evaluation_key, limit=180)
        if role_name not in ROLE_SYSTEM_PROMPTS:
            raise RunKernelTransitionError("unknown multi-component semantic role")
        if not input_digest or not evaluation_key:
            raise RunKernelTransitionError(
                "multi-component role execution requires exact input and logical bindings"
            )
        role_types = {
            "component_analyst": (
                ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
                ObservationType.MULTICOMPONENT_COMPONENT_ANALYST_COMPLETED,
            ),
            "component_dprime": (
                ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
                ObservationType.MULTICOMPONENT_COMPONENT_DPRIME_COMPLETED,
            ),
            "cross_component_analyst": (
                ActionType.MULTICOMPONENT_CROSS_ANALYST_EXECUTE,
                ObservationType.MULTICOMPONENT_CROSS_ANALYST_COMPLETED,
            ),
            "synthesis_dprime": (
                ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE,
                ObservationType.MULTICOMPONENT_SYNTHESIS_DPRIME_COMPLETED,
            ),
            "scrutineer": (
                ActionType.MULTICOMPONENT_SCRUTINEER_EXECUTE,
                ObservationType.MULTICOMPONENT_SCRUTINEER_COMPLETED,
            ),
        }
        action_type, observation_type = role_types[role_name]
        prior_role_actions = [
            prior
            for prior in self.state.issued_actions.values()
            if prior.action_type is action_type
        ]
        if any(
            prior.inputs.get("logical_evaluation_key") == evaluation_key
            for prior in prior_role_actions
        ):
            raise RunKernelTransitionError(
                "multi-component role logical evaluation key is duplicate"
            )
        if len(prior_role_actions) >= MULTICOMPONENT_ROLE_CALL_LIMITS[role_name]:
            raise RunKernelTransitionError(
                "multi-component role call exceeds the shared compatibility mapping Phase 1 cap"
            )
        scheduler_raw = self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE, {})
        lease_inputs: dict[str, Any] = {}
        if scheduler_raw:
            scheduler = validate_scheduler_state(scheduler_raw)
            lease = next(
                (
                    _safe_mapping(item)
                    for item in scheduler.get("lease_history") or ()
                    if _safe_mapping(item).get("lease_id") == lease_id
                ),
                {},
            )
            work = _safe_mapping(lease.get("work"))
            dispatch = self.state.issued_actions.get(str(dispatch_action_id or ""))
            if (
                lease.get("status") != LEASE_GRANTED
                or work.get("role") != role_name
                or work.get("input_packet_digest") != input_digest
                or work.get("logical_evaluation_key") != evaluation_key
                or work.get("output_schema_variant") != output_schema_variant
                or dispatch is None
                or dispatch.action_type is not ActionType.MULTICOMPONENT_LEASE_DISPATCH
                or dispatch.inputs.get("lease_id") != lease.get("lease_id")
                or dispatch.inputs.get("work_id") != work.get("work_id")
            ):
                raise RunKernelTransitionError(
                    "scheduler-active role call requires its exact granted lease"
                )
            lease_inputs = {
                "lease_id": lease.get("lease_id"),
                "lease_digest": lease.get("lease_digest"),
                "work_id": work.get("work_id"),
                "work_digest": work.get("work_digest"),
                "grant_action_ref": deepcopy(lease.get("grant_action_ref")),
                "dispatch_action_ref": {
                    "action_id": dispatch.action_id,
                    "stage": dispatch.stage,
                    "sequence": dispatch.sequence,
                    "observation_type": dispatch.expected_observation_type.value,
                },
                "accepted_contract_ref": deepcopy(work.get("accepted_contract_ref")),
                "graph_ref": deepcopy(work.get("graph_ref")),
                "target_kind": work.get("target_kind"),
                "component_id": work.get("component_id"),
                "synthesis_key": work.get("synthesis_key"),
                "node_ref": deepcopy(work.get("node_ref")),
                "recovery_authorization_ref": deepcopy(
                    work.get("recovery_authorization_ref")
                ),
                "contract_amendment_admission_ref": deepcopy(
                    work.get("contract_amendment_admission_ref")
                ),
                "contract_amendment_application_ref": deepcopy(
                    work.get("contract_amendment_application_ref")
                ),
                "selective_closure_ref": deepcopy(
                    work.get("selective_closure_ref")
                ),
                "scheduler_revision_at_grant": lease.get(
                    "scheduler_revision_at_grant"
                ),
                "output_schema_variant": output_schema_variant,
            }
        elif lease_id or dispatch_action_id:
            raise RunKernelTransitionError(
                "caller-authored lease lineage is forbidden without scheduler state"
            )
        return self.authorize(
            stage=f"multicomponent_role:{role_name}:{evaluation_key}",
            action_type=action_type,
            reason="ordinary_multicomponent_semantic_role_execution",
            inputs={
                "role": role_name,
                "input_packet_digest": input_digest,
                "logical_evaluation_key": evaluation_key,
                "supported_query_class": (
                    "ordinary-bounded-multicomponent-factual-synthesis-v1"
                ),
                **lease_inputs,
            },
            expected_observation_type=observation_type,
        )

    def authorize_multicomponent_component_admission(
        self,
        *,
        component_id: str,
        analyst_artifact_digest: str,
        dprime_artifact_digest: str,
    ) -> AuthorizedAction:
        if not self.state.initial_answer_contract_projection:
            raise RunKernelTransitionError(
                "multi-component admission requires an accepted answer contract"
            )
        component = _clean_text(component_id, limit=180)
        analyst_digest = _clean_text(analyst_artifact_digest, limit=128)
        dprime_digest = _clean_text(dprime_artifact_digest, limit=128)
        if not component or not analyst_digest or not dprime_digest:
            raise RunKernelTransitionError(
                "multi-component admission requires component and role bindings"
            )
        accepted_contract = (
            self.state.current_answer_contract
            or self.state.initial_answer_contract
        )
        return self.authorize(
            stage="multicomponent_component_admission",
            action_type=ActionType.MULTICOMPONENT_COMPONENT_ADMISSION_REDUCE,
            reason="component_analyst_then_dprime_admission",
            inputs={
                "component_id": component,
                "analyst_artifact_digest": analyst_digest,
                "dprime_artifact_digest": dprime_digest,
                "accepted_contract_digest": accepted_contract.get(
                    "accepted_contract_digest"
                ),
            },
            expected_observation_type=(
                ObservationType.MULTICOMPONENT_COMPONENT_ADMISSION_REDUCED
            ),
        )

    def authorize_multicomponent_graph_reduction(
        self,
        *,
        operation: str,
        prior_graph_digest: str | None,
        synthesis_key: str | None = None,
        role_evaluation_key: str | None = None,
    ) -> AuthorizedAction:
        operation_name = _clean_text(operation, limit=80)
        if operation_name not in {
            "structure",
            "synthesis_validation",
            "scrutiny",
            "synthesis_admission",
            "accounting",
            "finalize",
            "graph_amendment",
            "resynthesis_structure",
            "selective_invalidation",
            "selective_resynthesis_structure",
            "specialist_remediation",
        }:
            raise RunKernelTransitionError("unknown Graph V1 reduction operation")
        current_graph = _safe_mapping(
            self.state.projections.get("multicomponent_component_work_graph_v1")
        )
        current_digest = current_graph.get("graph_digest")
        if operation_name == "structure":
            if current_graph:
                raise RunKernelTransitionError("Graph V1 is already structured")
            if prior_graph_digest:
                raise RunKernelTransitionError(
                    "initial Graph V1 structure cannot claim a prior graph"
                )
        elif not current_graph or prior_graph_digest != current_digest:
            raise RunKernelTransitionError(
                "Graph V1 reduction requires the current canonical graph digest"
            )
        action_inputs = {
            "operation": operation_name,
            "prior_graph_digest": prior_graph_digest,
            "synthesis_key": _clean_text(synthesis_key, limit=80),
            "role_evaluation_key": _clean_text(
                role_evaluation_key, limit=180
            ),
        }
        if operation_name == "selective_resynthesis_structure":
            from core.component_work_graph_v1 import (
                MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
                validate_selective_recomputation_closure,
            )

            closure = validate_selective_recomputation_closure(
                _safe_mapping(
                    self.state.projections.get(
                        MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE
                    )
                )
            )
            if (
                current_graph.get("dependency_posture")
                != "requires_selective_resynthesis"
                or _safe_mapping(current_graph.get("selective_closure_ref"))
                != {
                    "closure_id": closure.get("closure_id"),
                    "closure_digest": closure.get("closure_digest"),
                }
            ):
                raise RunKernelTransitionError(
                    "selective resynthesis requires the closure-bound transition graph"
                )
            action_inputs.update(
                {
                    "closure_id": closure.get("closure_id"),
                    "closure_digest": closure.get("closure_digest"),
                }
            )
        return self.authorize(
            stage="multicomponent_component_work_graph_v1",
            action_type=ActionType.MULTICOMPONENT_GRAPH_REDUCE,
            reason=f"ordinary_multicomponent_graph_{operation_name}",
            inputs=action_inputs,
            expected_observation_type=ObservationType.MULTICOMPONENT_GRAPH_REDUCED,
        )

    def authorize_multicomponent_selective_recomputation_closure(
        self,
    ) -> AuthorizedAction:
        """Authorize closure derivation against the exact pre-transition graph."""

        from core.component_work_graph_v1 import (
            COMPONENT_WORK_GRAPH_V1_STAGE,
            validate_component_work_graph_v1,
        )
        from core.multicomponent_component_admission import (
            MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
        )

        graph = validate_component_work_graph_v1(
            _safe_mapping(self.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
        )
        authorization = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE)
        )
        if (
            authorization.get("graph_id") != graph.get("graph_id")
            or authorization.get("graph_revision") != graph.get("graph_revision")
            or authorization.get("graph_digest") != graph.get("graph_digest")
            or authorization.get("authorization_digest") is None
        ):
            raise RunKernelTransitionError(
                "selective closure requires the authorization-bound graph snapshot"
            )
        contract = _safe_mapping(self.state.current_answer_contract)
        amendment_admission = _safe_mapping(
            self.state.contract_amendment_admission_projection
        )
        amendment_application = _safe_mapping(
            self.state.contract_amendment_application_projection
        )
        component_projection = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE)
        )
        prior_component_ids = {
            item.get("component_id")
            for item in graph.get("component_nodes") or ()
            if isinstance(item, Mapping)
        }
        recovered_refs = [
            _safe_mapping(item)
            for item in component_projection.get("component_admission_refs") or ()
            if isinstance(item, Mapping)
            and item.get("component_id") not in prior_component_ids
            and item.get("accepted_contract_digest")
            == contract.get("accepted_contract_digest")
        ]
        if (
            not contract
            or not amendment_admission.get("admission_digest")
            or not amendment_application.get("application_digest")
            or len(recovered_refs) != 1
            or recovered_refs[0].get("admission_status")
            not in {"admitted", "admitted_with_caveats"}
        ):
            raise RunKernelTransitionError(
                "selective closure requires current amendment and recovered admission"
            )
        if any(
            item.action_type is ActionType.MULTICOMPONENT_GRAPH_REDUCE
            and item.inputs.get("operation") == "selective_closure"
            for item in self.state.issued_actions.values()
        ):
            raise RunKernelTransitionError(
                "selective closure is already authorized"
            )
        return self.authorize(
            stage=MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
            action_type=ActionType.MULTICOMPONENT_GRAPH_REDUCE,
            reason="ordinary_multicomponent_selective_closure",
            inputs={
                "operation": "selective_closure",
                "source_graph_ref": {
                    "graph_id": graph.get("graph_id"),
                    "graph_revision": graph.get("graph_revision"),
                    "graph_digest": graph.get("graph_digest"),
                },
                "recovery_authorization_ref": {
                    "authorization_id": authorization.get("authorization_id"),
                    "authorization_digest": authorization.get("authorization_digest"),
                },
                "current_contract_ref": {
                    "owner": contract.get("owner"),
                    "canonical_state": contract.get("canonical_state"),
                    "run_id": self.state.run_id,
                    "request_id": self.state.request_id,
                    "accepted_contract_version": contract.get(
                        "accepted_contract_version"
                    ),
                    "accepted_contract_digest": contract.get(
                        "accepted_contract_digest"
                    ),
                    "parent_question_meaning_record_id": contract.get(
                        "parent_question_meaning_record_id"
                    ),
                    "parent_question_meaning_record_digest": contract.get(
                        "parent_question_meaning_record_digest"
                    ),
                    "accepted_answer_component_count": contract.get(
                        "accepted_answer_component_count"
                    )
                    or len(contract.get("accepted_answer_component_refs", [])),
                },
                "contract_amendment_admission_ref": {
                    "amendment_record_id": amendment_admission.get(
                        "amendment_record_id"
                    ),
                    "amendment_record_digest": amendment_admission.get(
                        "amendment_record_digest"
                    ),
                    "authorized_action_id": amendment_admission.get(
                        "authorized_action_id"
                    ),
                    "admission_digest": amendment_admission.get("admission_digest"),
                },
                "contract_amendment_application_ref": {
                    "amendment_record_id": amendment_application.get(
                        "amendment_record_id"
                    ),
                    "authorized_action_id": amendment_application.get(
                        "authorized_action_id"
                    ),
                    "application_digest": amendment_application.get(
                        "application_digest"
                    ),
                },
                "recovered_component_admission_ref": recovered_refs[0],
                "run_id": self.state.run_id,
                "request_id": self.state.request_id,
            },
            expected_observation_type=ObservationType.MULTICOMPONENT_GRAPH_REDUCED,
        )

    def authorize_multicomponent_selective_invalidation(self) -> AuthorizedAction:
        """Authorize the one atomic affected-stale and carry-forward transition."""

        from core.component_work_graph_v1 import (
            COMPONENT_WORK_GRAPH_V1_STAGE,
            MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
            validate_component_work_graph_v1,
            validate_selective_recomputation_closure,
        )

        graph = validate_component_work_graph_v1(
            _safe_mapping(self.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE))
        )
        closure = validate_selective_recomputation_closure(
            _safe_mapping(
                self.state.projections.get(MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE)
            )
        )
        source_ref = _safe_mapping(closure.get("source_graph_ref"))
        if source_ref != {
            "graph_id": graph.get("graph_id"),
            "graph_revision": graph.get("graph_revision"),
            "graph_digest": graph.get("graph_digest"),
        }:
            raise RunKernelTransitionError(
                "selective invalidation requires the unchanged closure source graph"
            )
        authorization = _safe_mapping(
            self.state.projections.get(MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE)
        )
        contract = _safe_mapping(self.state.current_answer_contract)
        if (
            _safe_mapping(closure.get("recovery_authorization_ref"))
            != {
                "authorization_id": authorization.get("authorization_id"),
                "authorization_digest": authorization.get("authorization_digest"),
            }
            or _safe_mapping(closure.get("current_contract_ref")).get(
                "accepted_contract_digest"
            )
            != contract.get("accepted_contract_digest")
        ):
            raise RunKernelTransitionError(
                "selective invalidation closure authority became stale"
            )
        if any(
            item.action_type is ActionType.MULTICOMPONENT_GRAPH_REDUCE
            and item.inputs.get("operation") == "selective_invalidation"
            for item in self.state.issued_actions.values()
        ):
            raise RunKernelTransitionError(
                "selective invalidation is already authorized"
            )
        return self.authorize(
            stage=COMPONENT_WORK_GRAPH_V1_STAGE,
            action_type=ActionType.MULTICOMPONENT_GRAPH_REDUCE,
            reason="ordinary_multicomponent_graph_selective_invalidation",
            inputs={
                "operation": "selective_invalidation",
                "prior_graph_digest": graph.get("graph_digest"),
                "source_graph_ref": source_ref,
                "closure_id": closure.get("closure_id"),
                "closure_digest": closure.get("closure_digest"),
                "recovery_authorization_id": authorization.get("authorization_id"),
                "recovery_authorization_digest": authorization.get(
                    "authorization_digest"
                ),
                "current_contract_version": contract.get(
                    "accepted_contract_version"
                ),
                "current_contract_digest": contract.get(
                    "accepted_contract_digest"
                ),
                "contract_amendment_admission_ref": _safe_mapping(
                    closure.get("contract_amendment_admission_ref")
                ),
                "contract_amendment_application_ref": _safe_mapping(
                    closure.get("contract_amendment_application_ref")
                ),
                "recovered_component_admission_ref": _safe_mapping(
                    closure.get("recovered_component_admission_ref")
                ),
                "target_graph_id": graph.get("graph_id"),
                "target_graph_revision": int(graph.get("graph_revision") or 0) + 1,
                "run_id": self.state.run_id,
                "request_id": self.state.request_id,
            },
            expected_observation_type=ObservationType.MULTICOMPONENT_GRAPH_REDUCED,
        )

    def authorize_multicomponent_missing_component_recovery(
        self,
        *,
        proposal_key: str,
    ) -> AuthorizedAction:
        """Authorize the one bounded Scrutineer-originated recovery round."""

        from core.component_work_graph_v1 import (
            COMPONENT_WORK_GRAPH_V1_STAGE,
            MAX_COMPONENT_NODES,
            validate_component_work_graph_v1,
        )
        from core.multicomponent_role_runtime import (
            ROLE_SCRUTINEER,
            role_artifact_ref,
            safe_packet_digest,
            validate_multicomponent_role_artifact,
        )

        key = _clean_text(proposal_key, limit=80)
        if not key:
            raise RunKernelTransitionError(
                "multi-component recovery requires a proposal key"
            )
        graph = validate_component_work_graph_v1(
            _safe_mapping(
                self.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
            )
        )
        if graph.get("run_id") != self.state.run_id or graph.get(
            "request_id"
        ) != self.state.request_id:
            raise RunKernelTransitionError(
                "multi-component recovery graph is cross-run"
            )
        active_contract = (
            self.state.current_answer_contract
            or self.state.initial_answer_contract
        )
        contract_ref = _safe_mapping(graph.get("accepted_contract_ref"))
        if (
            not active_contract
            or contract_ref.get("accepted_contract_version")
            != active_contract.get("accepted_contract_version")
            or contract_ref.get("accepted_contract_digest")
            != active_contract.get("accepted_contract_digest")
        ):
            raise RunKernelTransitionError(
                "multi-component recovery requires the current AnswerContract binding"
            )
        if len(graph.get("component_nodes") or ()) >= MAX_COMPONENT_NODES:
            raise RunKernelTransitionError(
                "multi-component recovery exceeds the component cap"
            )
        prior_recovery_actions = [
            item
            for item in self.state.issued_actions.values()
            if item.action_type is ActionType.MULTICOMPONENT_RECOVERY_AUTHORIZE
        ]
        if prior_recovery_actions:
            raise RunKernelTransitionError(
                "second multi-component recovery round is not authorized"
            )
        if self.state.contract_amendment_application_history:
            raise RunKernelTransitionError(
                "multi-component recovery amendment budget is exhausted"
            )
        if int(graph.get("automatic_recovery_rounds") or 0) != 0 or int(
            graph.get("graph_amendment_rounds") or 0
        ) != 0:
            raise RunKernelTransitionError(
                "multi-component recovery graph budget is exhausted"
            )

        scrutineer_ref = _safe_mapping(graph.get("scrutineer_ref"))
        action_ref = _safe_mapping(
            scrutineer_ref.get("authorized_action_ref")
        )
        completed_stage = _clean_text(action_ref.get("stage"), limit=240)
        completed = _safe_mapping(
            self.state.projections.get(completed_stage or "")
        )
        completed_action = self.state.issued_actions.get(
            str(action_ref.get("action_id") or "")
        )
        if (
            completed_action is None
            or completed_action.action_type
            is not ActionType.MULTICOMPONENT_SCRUTINEER_EXECUTE
            or completed_action.stage != completed_stage
            or completed_action.action_id not in self.state.reduced_action_ids
        ):
            raise RunKernelTransitionError(
                "multi-component recovery requires completed Scrutineer action history"
            )
        try:
            completed = validate_multicomponent_role_artifact(
                completed,
                expected_role=ROLE_SCRUTINEER,
            )
        except Exception as exc:
            raise RunKernelTransitionError(
                "multi-component recovery requires the exact completed Scrutineer artifact"
            ) from exc
        if role_artifact_ref(completed) != scrutineer_ref:
            raise RunKernelTransitionError(
                "multi-component recovery Scrutineer artifact is not canonical"
            )
        proposals = [
            _safe_mapping(item)
            for item in _safe_mapping(
                completed.get("semantic_output")
            ).get("missing_component_proposals", ())
            if isinstance(item, Mapping)
        ]
        matching = [item for item in proposals if item.get("proposal_key") == key]
        if len(proposals) != 1 or len(matching) != 1:
            raise RunKernelTransitionError(
                "multi-component recovery requires exactly one canonical proposal"
            )
        proposal = matching[0]
        scope_posture = proposal.get("scope_posture")
        if scope_posture not in {
            "required_to_fulfill_existing_accepted_user_obligation",
            "new_or_broadened_user_intent",
        }:
            raise RunKernelTransitionError(
                "multi-component recovery proposal scope posture is invalid"
            )
        search_authorized = scope_posture == (
            "required_to_fulfill_existing_accepted_user_obligation"
        )
        target_pair = (proposal.get("target_kind"), proposal.get("target_key"))
        matching_challenges = [
            _safe_mapping(item)
            for item in graph.get("challenge_refs") or ()
            if (item.get("target_kind"), item.get("target_key")) == target_pair
            and _safe_mapping(item.get("scrutineer_ref")) == scrutineer_ref
            and item.get("challenge_status") in {"challenged", "blocked"}
        ]
        if len(matching_challenges) != 1 or target_pair[0] != "synthesis":
            raise RunKernelTransitionError(
                "multi-component recovery requires the resolved current synthesis target"
            )
        directive = _clean_text(
            graph.get("requested_synthesis_directive"), limit=360
        )
        relationship = _clean_text(
            proposal.get("relationship_to_accepted_synthesis_directive"),
            limit=800,
        )
        if not directive or not relationship:
            raise RunKernelTransitionError(
                "multi-component recovery proposal lacks accepted directive binding"
            )
        proposal_digest = safe_packet_digest(proposal)
        proposal_id = (
            f"missing-component-proposal:{self.state.run_id}:"
            f"{proposal_digest[:16]}"
        )
        return self.authorize(
            stage=MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE,
            action_type=ActionType.MULTICOMPONENT_RECOVERY_AUTHORIZE,
            reason="scrutineer_missing_component_recovery_authorization",
            inputs={
                "proposal_id": proposal_id,
                "proposal_key": key,
                "proposal_digest": proposal_digest,
                "proposal": proposal,
                "scrutineer_artifact_id": completed.get("artifact_id"),
                "scrutineer_artifact_digest": completed.get("artifact_digest"),
                "scrutineer_action_id": action_ref.get("action_id"),
                "target_kind": target_pair[0],
                "target_key": target_pair[1],
                "resolved_target": matching_challenges[0].get(
                    "resolved_target"
                ),
                "graph_id": graph.get("graph_id"),
                "graph_revision": graph.get("graph_revision"),
                "graph_digest": graph.get("graph_digest"),
                "accepted_contract_version": active_contract.get(
                    "accepted_contract_version"
                ),
                "accepted_contract_digest": active_contract.get(
                    "accepted_contract_digest"
                ),
                "automatic_amendment_authority_class": (
                    "required_to_fulfill_existing_accepted_user_obligation"
                    if search_authorized
                    else None
                ),
                "recovery_scope_posture": scope_posture,
                "search_authorized": search_authorized,
                "component_count_before_recovery": len(
                    graph.get("component_nodes") or ()
                ),
                "maximum_component_count": MAX_COMPONENT_NODES,
                "recovery_round": 1,
                "amendment_round": 1,
                "graph_amendment_round": 1,
                "component_research_reentry_round": 1,
                "selective_recomputation_round": 1,
                "whole_graph_resynthesis_round": 0,
            },
            expected_observation_type=(
                ObservationType.MULTICOMPONENT_RECOVERY_AUTHORIZED
            ),
        )

    def authorize_multicomponent_recovery_outcome(
        self,
        *,
        disposition: str,
        observed_provider_identities: Sequence[str] = (),
        blocker_reason: str | None = None,
    ) -> AuthorizedAction:
        """Authorize one canonical terminal outcome for the bounded recovery."""

        clean_disposition = _clean_text(disposition, limit=80)
        if clean_disposition not in _MULTICOMPONENT_RECOVERY_OUTCOME_DISPOSITIONS:
            raise RunKernelTransitionError(
                "multi-component recovery outcome disposition is invalid"
            )
        prior = [
            item
            for item in self.state.issued_actions.values()
            if item.action_type
            is ActionType.MULTICOMPONENT_RECOVERY_OUTCOME_REDUCE
        ]
        if prior:
            raise RunKernelTransitionError(
                "multi-component recovery outcome is already authorized"
            )
        authorization = _safe_mapping(
            self.state.projections.get(
                MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
            )
        )
        if (
            authorization.get("owner")
            != "RunKernel.MulticomponentRecoveryAuthorization"
            or authorization.get("canonical_state") is not True
            or authorization.get("run_id") != self.state.run_id
            or authorization.get("request_id") != self.state.request_id
        ):
            raise RunKernelTransitionError(
                "multi-component recovery outcome requires canonical authorization"
            )
        providers = list(
            dict.fromkeys(
                item
                for item in (
                    _clean_text(value, limit=80)
                    for value in observed_provider_identities
                )
                if item
            )
        )
        if any(
            provider not in _MULTICOMPONENT_RECOVERY_ORDINARY_PROVIDERS
            for provider in providers
        ):
            raise RunKernelTransitionError(
                "multi-component recovery outcome provider is not an ordinary provider"
            )
        requires_confirmation = (
            clean_disposition == "blocked_requires_user_confirmation"
        )
        if requires_confirmation:
            if authorization.get("search_authorized") is not False or providers:
                raise RunKernelTransitionError(
                    "confirmation-blocked recovery cannot record provider execution"
                )
        else:
            live_state = _safe_mapping(self.state.live_search_validation_state)
            observed_provider = _clean_text(
                live_state.get("provider_used"), limit=80
            )
            if (
                authorization.get("search_authorized") is not True
                or not self.state.search_planner_proposal_state
                or not self.state.search_executor_handoff_state
                or not live_state
                or not observed_provider
                or observed_provider
                not in _MULTICOMPONENT_RECOVERY_ORDINARY_PROVIDERS
                or (providers and observed_provider not in providers)
            ):
                raise RunKernelTransitionError(
                    "recovery outcome requires one canonical ordinary acquisition attempt"
                )
            # The adapter may report diagnostics, but executed-provider authority
            # is rederived from canonical live-search state.
            providers = [observed_provider]
        blocker = _clean_text(blocker_reason, limit=300)
        if clean_disposition == "acquired" and blocker:
            raise RunKernelTransitionError(
                "acquired recovery outcome cannot carry a blocker"
            )
        if clean_disposition != "acquired" and not blocker:
            raise RunKernelTransitionError(
                "blocked recovery outcome requires a bounded blocker reason"
            )
        return self.authorize(
            stage=MULTICOMPONENT_RECOVERY_OUTCOME_STAGE,
            action_type=ActionType.MULTICOMPONENT_RECOVERY_OUTCOME_REDUCE,
            reason="multicomponent_recovery_terminal_outcome",
            inputs={
                "disposition": clean_disposition,
                "observed_provider_identities": providers,
                "blocker_reason": blocker,
                "recovery_authorization_id": authorization.get(
                    "authorization_id"
                ),
                "recovery_authorization_digest": authorization.get(
                    "authorization_digest"
                ),
            },
            expected_observation_type=(
                ObservationType.MULTICOMPONENT_RECOVERY_OUTCOME_REDUCED
            ),
        )

    def authorize_dprime_current_answer_contract_authority(
        self,
        *,
        expected_contract_version: str,
        expected_contract_digest: str,
        answer_component_id: str,
        source_obligation_candidate_ids: Sequence[str],
        fetch_read_content_packet_id: str,
        fetch_read_content_packet_digest: str,
        request_id: str | None = None,
        reason: str = DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        """Authorize the narrow D-prime accepted/current contract surface."""

        clean_source_ids = [
            item
            for item in (
                _clean_text(value, limit=200)
                for value in source_obligation_candidate_ids
            )
            if item
        ]
        for label, value in (
            ("expected_contract_version", expected_contract_version),
            ("expected_contract_digest", expected_contract_digest),
            ("answer_component_id", answer_component_id),
            ("fetch_read_content_packet_id", fetch_read_content_packet_id),
            ("fetch_read_content_packet_digest", fetch_read_content_packet_digest),
        ):
            if not _clean_text(value, limit=260):
                raise RunKernelTransitionError(
                    "D-prime contract authority requires " f"{label} binding"
                )
        if not clean_source_ids:
            raise RunKernelTransitionError(
                "D-prime contract authority requires source-obligation lineage"
            )
        merged_inputs = {
            "expected_contract_version": expected_contract_version,
            "expected_contract_digest": expected_contract_digest,
            "answer_component_id": answer_component_id,
            "source_obligation_candidate_ids": clean_source_ids,
            "fetch_read_content_packet_id": fetch_read_content_packet_id,
            "fetch_read_content_packet_digest": fetch_read_content_packet_digest,
            "request_id": request_id or self.state.request_id,
            "component_coverage_bound": False,
            "source_obligation_satisfied": False,
            "citation_eligibility_claimed": False,
            "product_correctness_claimed": False,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY_STAGE,
            action_type=ActionType.DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORIZED
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

    def authorize_dprime_source_obligation_authority(
        self,
        *,
        source_obligation_authority_id: str,
        source_obligation_authority_digest: str,
        coverage_record_id: str,
        coverage_record_digest: str,
        coverage_reduction_digest: str,
        answer_component_id: str,
        source_obligation_candidate_ids: Sequence[str],
        semantic_observation_id: str,
        semantic_observation_digest: str,
        content_ref_id: str,
        evidence_ref_id: str,
        request_id: str | None = None,
        reason: str = DPRIME_SOURCE_OBLIGATION_AUTHORITY_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        """Authorize D-prime source-obligation authority after coverage binds."""

        if not self.state.component_coverage_projection:
            raise RunKernelTransitionError(
                "D-prime source-obligation authority requires bound ComponentCoverage"
            )
        if self.state.dprime_source_obligation_authority_projection:
            raise RunKernelTransitionError(
                "D-prime source-obligation authority is already consumed"
            )
        _require_dprime_downstream_closed(
            state=self.state,
            context="D-prime source-obligation authority",
        )
        clean_source_ids = _preserve_text_list(source_obligation_candidate_ids)
        if not clean_source_ids:
            raise RunKernelTransitionError(
                "D-prime source-obligation authority requires source ids"
            )
        coverage = self.state.component_coverage_projection
        expected_pairs = (
            ("coverage_record_id", coverage_record_id, coverage.get("coverage_record_id")),
            (
                "coverage_record_digest",
                coverage_record_digest,
                coverage.get("coverage_record_digest"),
            ),
            (
                "coverage_reduction_digest",
                coverage_reduction_digest,
                coverage.get("coverage_reduction_digest"),
            ),
            (
                "answer_component_id",
                answer_component_id,
                coverage.get("answer_component_id"),
            ),
        )
        for label, value, expected in expected_pairs:
            if not _clean_text(value, limit=260):
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority requires "
                    f"{label} binding"
                )
            if expected and value != expected:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority "
                    f"{label} does not match bound ComponentCoverage"
                )
        for label, value in (
            ("source_obligation_authority_id", source_obligation_authority_id),
            (
                "source_obligation_authority_digest",
                source_obligation_authority_digest,
            ),
            ("semantic_observation_id", semantic_observation_id),
            ("semantic_observation_digest", semantic_observation_digest),
            ("content_ref_id", content_ref_id),
            ("evidence_ref_id", evidence_ref_id),
        ):
            if not _clean_text(value, limit=260):
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority requires "
                    f"{label} binding"
                )
        merged_inputs = {
            "source_obligation_authority_id": source_obligation_authority_id,
            "source_obligation_authority_digest": source_obligation_authority_digest,
            "coverage_record_id": coverage_record_id,
            "coverage_record_digest": coverage_record_digest,
            "coverage_reduction_digest": coverage_reduction_digest,
            "answer_component_id": answer_component_id,
            "source_obligation_candidate_ids": clean_source_ids,
            "semantic_observation_id": semantic_observation_id,
            "semantic_observation_digest": semantic_observation_digest,
            "content_ref_id": content_ref_id,
            "evidence_ref_id": evidence_ref_id,
            "request_id": request_id or self.state.request_id,
            "component_coverage_consumed": True,
            "component_coverage_only_treated_as_pass": False,
            "retained_ids_alone_are_authority": False,
            "citation_eligibility_authority_consumed": False,
            "citation_rendering_created": False,
            "sufficiency_readiness_created": False,
            "final_answer_packet_created": False,
            "author_answer_created": False,
            "product_correctness_claimed": False,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=DPRIME_SOURCE_OBLIGATION_AUTHORITY_STAGE,
            action_type=ActionType.DPRIME_SOURCE_OBLIGATION_AUTHORITY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.DPRIME_SOURCE_OBLIGATION_AUTHORITY_CONSUMED
            ),
        )

    def authorize_dprime_citation_source_handoff_authority(
        self,
        *,
        citation_source_handoff_id: str,
        citation_source_handoff_digest: str,
        source_obligation_authority_id: str,
        source_obligation_authority_digest: str,
        coverage_record_id: str,
        coverage_record_digest: str,
        citation_eligible_source_ids: Sequence[str],
        request_id: str | None = None,
        reason: str = DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        """Authorize D-prime citation-source handoff after source authority."""

        if not self.state.dprime_source_obligation_authority_projection:
            raise RunKernelTransitionError(
                "D-prime citation-source handoff requires source-obligation authority"
            )
        if self.state.dprime_citation_source_handoff_projection:
            raise RunKernelTransitionError(
                "D-prime citation-source handoff authority is already consumed"
            )
        _require_dprime_downstream_closed(
            state=self.state,
            context="D-prime citation-source handoff authority",
        )
        source_authority = self.state.dprime_source_obligation_authority_projection
        coverage = self.state.component_coverage_projection
        clean_source_ids = _preserve_text_list(citation_eligible_source_ids)
        if not clean_source_ids:
            raise RunKernelTransitionError(
                "D-prime citation-source handoff requires source identities"
            )
        expected_pairs = (
            (
                "source_obligation_authority_id",
                source_obligation_authority_id,
                source_authority.get("source_obligation_authority_id"),
            ),
            (
                "source_obligation_authority_digest",
                source_obligation_authority_digest,
                source_authority.get("source_obligation_authority_digest"),
            ),
            ("coverage_record_id", coverage_record_id, coverage.get("coverage_record_id")),
            (
                "coverage_record_digest",
                coverage_record_digest,
                coverage.get("coverage_record_digest"),
            ),
        )
        for label, value, expected in expected_pairs:
            if not _clean_text(value, limit=260):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff requires "
                    f"{label} binding"
                )
            if expected and value != expected:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff "
                    f"{label} does not match prior authority"
                )
        for label, value in (
            ("citation_source_handoff_id", citation_source_handoff_id),
            ("citation_source_handoff_digest", citation_source_handoff_digest),
        ):
            if not _clean_text(value, limit=260):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff requires "
                    f"{label} binding"
                )
        merged_inputs = {
            "citation_source_handoff_id": citation_source_handoff_id,
            "citation_source_handoff_digest": citation_source_handoff_digest,
            "source_obligation_authority_id": source_obligation_authority_id,
            "source_obligation_authority_digest": source_obligation_authority_digest,
            "coverage_record_id": coverage_record_id,
            "coverage_record_digest": coverage_record_digest,
            "citation_eligible_source_ids": clean_source_ids,
            "request_id": request_id or self.state.request_id,
            "source_obligation_authority_consumed": True,
            "citation_eligibility_authority_consumed": True,
            "citation_source_handoff_consumed": True,
            "citation_rendering_created": False,
            "citations_rendered": False,
            "sufficiency_readiness_created": False,
            "final_answer_packet_created": False,
            "author_answer_created": False,
            "product_correctness_claimed": False,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_STAGE,
            action_type=ActionType.DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_CONSUMED
            ),
        )

    def authorize_dprime_citation_source_display(
        self,
        *,
        display_id: str,
        display_digest: str,
        citation_source_handoff_id: str,
        citation_source_handoff_digest: str,
        author_prose_id: str,
        author_prose_digest: str,
        final_answer_packet_digest: str,
        request_id: str | None = None,
        reason: str = DPRIME_CITATION_SOURCE_DISPLAY_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        """Authorize D-prime source display after FAP and AuthorProse consume."""

        if not self.state.dprime_citation_source_handoff_projection:
            raise RunKernelTransitionError(
                "D-prime source display requires citation-source handoff authority"
            )
        if not self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "D-prime source display requires hardened FinalAnswerPacket"
            )
        if not self.state.author_prose_projection:
            raise RunKernelTransitionError(
                "D-prime source display requires AuthorProse output"
            )
        handoff = self.state.dprime_citation_source_handoff_projection
        author = self.state.author_prose_projection
        fap = self.state.final_answer_authority_projection
        expected_pairs = (
            (
                "citation_source_handoff_id",
                citation_source_handoff_id,
                handoff.get("citation_source_handoff_id"),
            ),
            (
                "citation_source_handoff_digest",
                citation_source_handoff_digest,
                handoff.get("citation_source_handoff_digest"),
            ),
            ("author_prose_id", author_prose_id, author.get("author_prose_id")),
            (
                "author_prose_digest",
                author_prose_digest,
                author.get("author_prose_digest"),
            ),
        )
        for label, value, expected in expected_pairs:
            if not _clean_text(value, limit=260):
                raise RunKernelTransitionError(
                    "D-prime source display requires " f"{label} binding"
                )
            if expected and value != expected:
                raise RunKernelTransitionError(
                    "D-prime source display "
                    f"{label} does not match prior authority"
                )
        packet_digest = (
            fap.get("packet_digest")
            or fap.get("no_packet_digest")
            or fap.get("fap_digest")
        )
        if not _clean_text(final_answer_packet_digest, limit=260):
            raise RunKernelTransitionError(
                "D-prime source display requires final_answer_packet_digest binding"
            )
        if packet_digest and final_answer_packet_digest != packet_digest:
            raise RunKernelTransitionError(
                "D-prime source display final_answer_packet_digest mismatch"
            )
        for label, value in (
            ("display_id", display_id),
            ("display_digest", display_digest),
        ):
            if not _clean_text(value, limit=260):
                raise RunKernelTransitionError(
                    "D-prime source display requires " f"{label} binding"
                )
        merged_inputs = {
            "display_id": display_id,
            "display_digest": display_digest,
            "citation_source_handoff_id": citation_source_handoff_id,
            "citation_source_handoff_digest": citation_source_handoff_digest,
            "author_prose_id": author_prose_id,
            "author_prose_digest": author_prose_digest,
            "final_answer_packet_digest": final_answer_packet_digest,
            "request_id": request_id or self.state.request_id,
            "citation_source_handoff_consumed": True,
            "final_answer_packet_consumed": True,
            "author_answer_consumed": True,
            "product_correctness_claimed": False,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=DPRIME_CITATION_SOURCE_DISPLAY_STAGE,
            action_type=ActionType.DPRIME_CITATION_SOURCE_DISPLAY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=(
                ObservationType.DPRIME_CITATION_SOURCE_DISPLAY_CREATED
            ),
        )

    def authorize_single_relation_source_obligation_recovery(
        self,
        *,
        reason: str = (
            "single_relation_source_obligation_recovery_authorization"
        ),
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        """Authorize the post-D-prime source-obligation contract reducer."""

        return self.authorize(
            stage=SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE,
            action_type=(
                ActionType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE
            ),
            reason=reason,
            inputs=inputs,
            expected_observation_type=(
                ObservationType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED
            ),
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

    def _require_multicomponent_recovery_amendment_authority(
        self,
        inputs: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        supplied = _safe_mapping(inputs)
        authority_class = _clean_text(
            supplied.get("automatic_amendment_authority_class"), limit=160
        )
        if not authority_class:
            return {}
        if authority_class != (
            "required_to_fulfill_existing_accepted_user_obligation"
        ):
            raise RunKernelTransitionError(
                "unknown automatic AnswerContract amendment authority class"
            )
        authorization = _safe_mapping(
            self.state.projections.get(
                MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
            )
        )
        if (
            authorization.get("owner")
            != "RunKernel.MulticomponentRecoveryAuthorization"
            or authorization.get("canonical_state") is not True
            or authorization.get("run_id") != self.state.run_id
            or authorization.get("request_id") != self.state.request_id
            or authorization.get("automatic_amendment_authority_class")
            != authority_class
        ):
            raise RunKernelTransitionError(
                "automatic AnswerContract amendment requires canonical recovery authorization"
            )
        required_matches = {
            "recovery_authorization_id": authorization.get("authorization_id"),
            "recovery_authorization_digest": authorization.get(
                "authorization_digest"
            ),
            "recovery_proposal_id": authorization.get("proposal_id"),
            "recovery_proposal_digest": authorization.get("proposal_digest"),
        }
        if any(
            supplied.get(key) != value or not value
            for key, value in required_matches.items()
        ):
            raise RunKernelTransitionError(
                "automatic AnswerContract amendment recovery binding mismatch"
            )
        return authorization

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
        self._require_multicomponent_recovery_amendment_authority(inputs)
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

    def authorize_contract_amendment_application(
        self,
        *,
        amendment_record_id: str,
        amendment_record_digest: str,
        admission_digest: str,
        parent_contract_digest: str | None = None,
        parent_contract_version: str | None = None,
        request_id: str | None = None,
        reason: str = CONTRACT_AMENDMENT_APPLICATION_REASON,
        inputs: Mapping[str, Any] | None = None,
    ) -> AuthorizedAction:
        if not self.state.initial_answer_contract_projection:
            raise RunKernelTransitionError(
                "contract amendment application requires an accepted "
                "initial answer contract"
            )
        if not self.state.contract_amendment_admission_history:
            raise RunKernelTransitionError(
                "contract amendment application requires a canonical "
                "admitted amendment"
            )
        parent = self.state.current_answer_contract or self.state.initial_answer_contract
        resolved_parent_digest = (
            parent_contract_digest or parent.get("accepted_contract_digest")
        )
        resolved_parent_version = (
            parent_contract_version or parent.get("accepted_contract_version")
        )
        for label, value in (
            ("amendment_record_id", amendment_record_id),
            ("amendment_record_digest", amendment_record_digest),
            ("admission_digest", admission_digest),
            ("parent_contract_digest", resolved_parent_digest),
            ("parent_contract_version", resolved_parent_version),
        ):
            if not _clean_text(value, limit=200):
                raise RunKernelTransitionError(
                    "contract amendment application requires " f"{label} binding"
                )
        self._require_multicomponent_recovery_amendment_authority(inputs)
        merged_inputs = {
            "amendment_record_id": amendment_record_id,
            "amendment_record_digest": amendment_record_digest,
            "admission_digest": admission_digest,
            "parent_contract_digest": resolved_parent_digest,
            "parent_contract_version": resolved_parent_version,
            "request_id": request_id or self.state.request_id,
            **dict(inputs or {}),
        }
        return self.authorize(
            stage=CONTRACT_AMENDMENT_APPLICATION_STAGE,
            action_type=ActionType.CONTRACT_AMENDMENT_APPLY,
            reason=reason,
            inputs=merged_inputs,
            expected_observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
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

    def build_answer_contract_authority_map_projection(
        self,
        *,
        component_executor_contract_projection: Mapping[str, Any] | None = None,
        component_plan_projection: Mapping[str, Any] | None = None,
        search_work_plan_projection: Mapping[str, Any] | None = None,
        query_plan_work_shadow_projection: Mapping[str, Any] | None = None,
        blocked_final_answer_packet_summary: Mapping[str, Any] | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        """Build the passive AnswerContractAuthorityMap from RunKernel state."""

        from core.answer_contract_authority_map import (
            build_answer_contract_authority_map,
        )

        projection = build_answer_contract_authority_map(
            component_executor_contract_projection=(
                component_executor_contract_projection
            ),
            component_plan_projection=component_plan_projection,
            search_work_plan_projection=(
                search_work_plan_projection or self.state.search_work_plan
            ),
            query_plan_work_shadow_projection=query_plan_work_shadow_projection,
            evidence_ledger_projection=(
                self.state.evidence_ledger.to_projection().to_dict()
            ),
            semantic_observation_projection=(
                self.state.semantic_observation_admission_projection
            ),
            component_coverage_projection=self.state.component_coverage_projection,
            search_judgment_projection=self.state.search_judgment_projection,
            sufficiency_judgment_projection=(
                self.state.sufficiency_judgment_projection
            ),
            final_answer_packet_projection=self.state.final_answer_packet,
            final_answer_authority_projection=(
                self.state.final_answer_authority_projection
            ),
            blocked_final_answer_packet_summary=blocked_final_answer_packet_summary,
        ).to_projection()
        if store:
            self.state.projections[ANSWER_CONTRACT_AUTHORITY_MAP_STAGE] = deepcopy(
                projection
            )
        return projection

    def build_offline_search_executor_bridge_projection(
        self,
        *,
        answer_contract_authority_map_projection: Mapping[str, Any] | None = None,
        component_executor_contract_projection: Mapping[str, Any] | None = None,
        component_search_plan_projection: Mapping[str, Any] | None = None,
        component_plan_projection: Mapping[str, Any] | None = None,
        search_work_plan_projection: Mapping[str, Any] | None = None,
        query_plan_work_shadow_projection: Mapping[str, Any] | None = None,
        offline_candidate_observations: Sequence[Mapping[str, Any]] | None = None,
        offline_candidate_fixtures: Sequence[Mapping[str, Any]] | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        """Build and store the offline SearchExecutor bridge projection."""

        from core.offline_search_executor_bridge import (
            build_offline_search_executor_bridge_projection,
        )

        bridge = build_offline_search_executor_bridge_projection(
            answer_contract_authority_map_projection=(
                answer_contract_authority_map_projection
                or self.state.projections.get(ANSWER_CONTRACT_AUTHORITY_MAP_STAGE)
            ),
            component_executor_contract_projection=(
                component_executor_contract_projection
            ),
            component_search_plan_projection=component_search_plan_projection,
            component_plan_projection=component_plan_projection,
            search_work_plan_projection=(
                search_work_plan_projection
                or self.state.search_work_plan_projection
                or self.state.search_work_plan
            ),
            query_plan_work_shadow_projection=query_plan_work_shadow_projection,
            offline_candidate_observations=offline_candidate_observations,
            offline_candidate_fixtures=offline_candidate_fixtures,
        ).to_projection()
        if store:
            self.state.offline_search_executor_bridge_projection = deepcopy(bridge)
            self.state.offline_search_executor_bridge_history.append(
                deepcopy(bridge)
            )
            self.state.projections[OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE] = deepcopy(
                bridge
            )
        return bridge

    def record_component_scoped_source_custody_from_offline_search_executor_bridge(
        self,
        *,
        bridge_projection: Mapping[str, Any] | None = None,
        observation_id: str = "component-scoped-source-custody:offline-bridge",
        store: bool = True,
    ) -> dict[str, Any]:
        """Consume the offline bridge into EvidenceLedger-owned component custody."""

        bridge_input = (
            bridge_projection
            or self.state.offline_search_executor_bridge_projection
            or self.state.projections.get(OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE)
        )
        bridge = dict(bridge_input) if isinstance(bridge_input, Mapping) else {}
        if not bridge:
            raise RunKernelTransitionError(
                "component-scoped source custody requires an offline "
                "SearchExecutor bridge projection"
            )
        projection = (
            self.state.evidence_ledger.record_component_scoped_source_custody_from_offline_search_executor_bridge(
                bridge,
                observation_id=observation_id,
            )
        )
        if store:
            self.state.component_scoped_source_custody_projection = deepcopy(
                projection
            )
            self.state.component_scoped_source_custody_history.append(
                deepcopy(projection)
            )
            self.state.projections[COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE] = (
                deepcopy(projection)
            )
            self.state.projections[EVIDENCE_LEDGER_STAGE] = (
                self.state.evidence_ledger.to_projection().to_dict()
            )
        return projection

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
        graph = _safe_mapping(
            self.state.projections.get(
                "multicomponent_component_work_graph_v1"
            )
        )
        if graph:
            scheduler = _safe_mapping(
                self.state.projections.get("multicomponent_graph_scheduler")
            )
            scheduler_required_work_blocked = scheduler.get("status") in {
                "blocked_exhausted",
                "blocked_required_work_failed",
            }
            if (
                graph.get("graph_status") == "synthesis_validation_required"
                and not scheduler_required_work_blocked
            ):
                raise RunKernelTransitionError(
                    "ordinary Sufficiency requires finalized Graph V1 state"
                )
            supplied_digest = _safe_mapping(inputs).get(
                "multicomponent_graph_digest"
            )
            if supplied_digest != graph.get("graph_digest"):
                raise RunKernelTransitionError(
                    "ordinary Sufficiency requires the current Graph V1 digest"
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
        graph = _safe_mapping(
            self.state.projections.get(
                "multicomponent_component_work_graph_v1"
            )
        )
        if graph:
            sufficiency = _safe_mapping(self.state.sufficiency_judgment_projection)
            consumption = _safe_mapping(
                sufficiency.get("multicomponent_graph_consumption")
            )
            if (
                not sufficiency
                or consumption.get("graph_digest") != graph.get("graph_digest")
                or consumption.get("ordinary_sufficiency_decision_created")
                is not True
            ):
                raise RunKernelTransitionError(
                    "FinalAnswerPacket requires ordinary Sufficiency consumption of current Graph V1"
                )
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

    def authorize_followup_search(
        self,
        *,
        followup_search_intent_packet: Mapping[str, Any],
        mode: str = "Balanced",
        proposal_ids: Sequence[str] = (),
        logical_depth: int = 1,
        unresolved_blocker_ids: Sequence[str] = (),
        new_evidence_expected: bool = True,
        extra_recovery_authorized: bool = False,
        reason: str = FOLLOWUP_SEARCH_AUTHORIZATION_REASON,
    ) -> AuthorizedAction:
        try:
            inputs = build_followup_search_authorization_action_inputs(
                run_id=self.state.run_id,
                request_id=self.state.request_id,
                followup_search_intent_packet=followup_search_intent_packet,
                current_answer_contract=self.state.current_answer_contract,
                existing_authorization_projection=self.state.projections.get(
                    FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
                    {},
                ),
                mode=mode,
                proposal_ids=proposal_ids,
                logical_depth=logical_depth,
                unresolved_blocker_ids=unresolved_blocker_ids,
                new_evidence_expected=new_evidence_expected,
                extra_recovery_authorized=extra_recovery_authorized,
            )
        except FollowupSearchAuthorizationRuntimeError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
            action_type=ActionType.FOLLOWUP_SEARCH_AUTHORIZE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.FOLLOWUP_SEARCH_AUTHORIZED,
        )

    def authorize_scrutineer_review(
        self,
        *,
        scrutineer_review_record: Mapping[str, Any],
        reason: str = SCRUTINEER_REVIEW_REASON,
    ) -> AuthorizedAction:
        try:
            inputs = build_scrutineer_review_action_inputs(
                run_id=self.state.run_id,
                request_id=self.state.request_id,
                scrutineer_review_record=scrutineer_review_record,
            )
        except ScrutineerReviewRuntimeError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=SCRUTINEER_REVIEW_STAGE,
            action_type=ActionType.SCRUTINEER_REVIEW_REDUCE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.SCRUTINEER_REVIEW_REDUCED,
        )

    def authorize_specialist_source_bound_calculation(
        self,
        *,
        specialist_source_bound_calculation_record: Mapping[str, Any],
        reason: str = SPECIALIST_SOURCE_BOUND_CALCULATION_REASON,
    ) -> AuthorizedAction:
        try:
            inputs = build_specialist_source_bound_calculation_action_inputs(
                run_id=self.state.run_id,
                request_id=self.state.request_id,
                specialist_source_bound_calculation_record=(
                    specialist_source_bound_calculation_record
                ),
            )
        except SpecialistSourceBoundCalculationRuntimeError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE,
            action_type=ActionType.SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=(
                ObservationType.SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCED
            ),
        )

    def authorize_sufficiency_readiness(
        self,
        *,
        mode: str = "Balanced",
        reason: str = SUFFICIENCY_READINESS_REASON,
    ) -> AuthorizedAction:
        try:
            inputs = build_sufficiency_readiness_action_inputs(
                run_id=self.state.run_id,
                request_id=self.state.request_id,
                mode=mode,
                current_answer_contract=(
                    self.state.current_answer_contract
                    or self.state.initial_answer_contract
                ),
                component_coverage_projection=self.state.component_coverage_projection,
                component_coverage_history=self.state.component_coverage_history,
                semantic_observation_admission_projection=(
                    self.state.semantic_observation_admission_projection
                ),
                semantic_observation_admission_history=(
                    self.state.semantic_observation_admission_history
                ),
                scrutineer_review_projection=self.state.scrutineer_review_projection,
                scrutineer_review_history=self.state.scrutineer_review_history,
                specialist_source_bound_calculation_projection=(
                    self.state.specialist_source_bound_calculation_projection
                ),
                specialist_source_bound_calculation_history=(
                    self.state.specialist_source_bound_calculation_history
                ),
                followup_search_authorization_projection=self.state.projections.get(
                    FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
                    {},
                ),
            )
        except SufficiencyReadinessRuntimeError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=SUFFICIENCY_READINESS_STAGE,
            action_type=ActionType.SUFFICIENCY_READINESS_DECIDE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.SUFFICIENCY_READINESS_DECIDED,
        )

    def authorize_final_answer_packet_hardening(
        self,
        *,
        reason: str = FINAL_ANSWER_PACKET_HARDENING_REASON,
    ) -> AuthorizedAction:
        if not self.state.sufficiency_readiness_state:
            raise RunKernelTransitionError(
                "hardened FinalAnswerPacket requires sufficiency_readiness_state"
            )
        if not self.state.sufficiency_readiness_projection:
            raise RunKernelTransitionError(
                "hardened FinalAnswerPacket requires sufficiency_readiness_projection"
            )
        try:
            inputs = build_final_answer_packet_hardening_action_inputs(
                run_id=self.state.run_id,
                request_id=self.state.request_id,
                sufficiency_readiness_state=self.state.sufficiency_readiness_state,
                sufficiency_readiness_projection=(
                    self.state.sufficiency_readiness_projection
                ),
                sufficiency_readiness_history=self.state.sufficiency_readiness_history,
            )
        except FinalAnswerPacketHardeningRuntimeError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=FINAL_ANSWER_PACKET_STAGE,
            action_type=ActionType.FINAL_ANSWER_PACKET_HARDEN,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.FINAL_ANSWER_PACKET_HARDENED,
        )

    def authorize_author_prose_finalization(
        self,
        *,
        policy: Mapping[str, Any] | None = None,
        reason: str = AUTHOR_PROSE_FINALIZATION_REASON,
    ) -> AuthorizedAction:
        if not self.state.final_answer_authority_projection:
            raise RunKernelTransitionError(
                "Author prose finalization requires final_answer_authority_projection"
            )
        try:
            inputs = build_author_prose_finalization_action_inputs(
                run_id=self.state.run_id,
                request_id=self.state.request_id,
                final_answer_packet_state=self.state.final_answer_packet,
                final_answer_authority_projection=(
                    self.state.final_answer_authority_projection
                ),
                policy=policy,
            )
        except AuthorProseFinalizationRuntimeError as exc:
            raise RunKernelTransitionError(str(exc)) from exc
        return self.authorize(
            stage=AUTHOR_PROSE_FINALIZATION_STAGE,
            action_type=ActionType.AUTHOR_PROSE_FINALIZE,
            reason=reason,
            inputs=inputs,
            expected_observation_type=ObservationType.AUTHOR_PROSE_FINALIZED,
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
        authority_supersession = (
            self._pending_multicomponent_authority_supersession(action)
        )
        if (
            observation.sequence != self.state.next_observation_sequence
            and not authority_supersession
        ):
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

        if action.action_type in {
            ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
            ActionType.MULTICOMPONENT_CROSS_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE,
            ActionType.MULTICOMPONENT_SCRUTINEER_EXECUTE,
        } and action.inputs.get("lease_id"):
            from core.multicomponent_graph_scheduling import (
                validate_role_lease_settlement,
            )

            validate_role_lease_settlement(
                state=self.state,
                action_id=action.action_id,
                action_inputs=action.inputs,
                observation_failed=observation.status is RunStageStatus.FAILED,
                observation_payload=observation.payload,
            )

        if not authority_supersession:
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
        elif action.action_type is ActionType.SEARCH_PLANNER_PRODUCE:
            try:
                proposal_state = build_search_planner_proposal_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=_safe_mapping(observation.payload),
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    current_parent_initial_contract=self.state.initial_answer_contract,
                    current_parent_current_contract=self.state.current_answer_contract,
                    existing_proposal_history=(
                        self.state.search_planner_proposal_history
                    ),
                )
                proposal_projection = build_search_planner_proposal_projection(
                    proposal_state=proposal_state
                )
            except SearchPlannerRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.search_planner_proposal_state = proposal_state
            self.state.search_planner_proposal_projection = proposal_projection
            self.state.search_planner_proposal_history.append(
                deepcopy(proposal_projection)
            )
            self.state.projections[action.stage] = deepcopy(proposal_projection)
        elif action.action_type is ActionType.SCOUT_DISAMBIGUATE:
            try:
                scout_state = build_scout_disambiguation_report_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=_safe_mapping(observation.payload),
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    current_search_planner_proposal_state=(
                        self.state.search_planner_proposal_state
                    ),
                    current_parent_initial_contract=(
                        self.state.initial_answer_contract
                    ),
                    current_parent_current_contract=(
                        self.state.current_answer_contract
                    ),
                    existing_report_history=(
                        self.state.scout_disambiguation_report_history
                    ),
                )
                scout_projection = build_scout_disambiguation_report_projection(
                    report_state=scout_state
                )
            except ScoutDisambiguationRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.scout_disambiguation_report_state = scout_state
            self.state.scout_disambiguation_report_projection = scout_projection
            self.state.scout_disambiguation_report_history.append(
                deepcopy(scout_projection)
            )
            self.state.projections[action.stage] = deepcopy(scout_projection)
        elif action.action_type is ActionType.SEARCH_PLANNER_REVISE:
            try:
                revision_state = build_search_planner_revision_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    current_search_planner_proposal_state=(
                        self.state.search_planner_proposal_state
                    ),
                    current_scout_disambiguation_report_state=(
                        self.state.scout_disambiguation_report_state
                    ),
                    current_parent_initial_contract=(
                        self.state.initial_answer_contract
                    ),
                    current_parent_current_contract=(
                        self.state.current_answer_contract
                    ),
                    existing_revision_history=(
                        self.state.search_planner_revision_history
                    ),
                )
                revision_projection = build_search_planner_revision_projection(
                    revision_state=revision_state
                )
            except SearchPlannerRevisionRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.search_planner_revision_state = revision_state
            self.state.search_planner_revision_projection = revision_projection
            self.state.search_planner_revision_history.append(
                deepcopy(revision_projection)
            )
            self.state.projections[action.stage] = deepcopy(revision_projection)
        elif action.action_type is ActionType.SEARCH_EXECUTOR_HANDOFF:
            try:
                handoff_state = build_search_executor_handoff_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    current_search_planner_proposal_state=(
                        self.state.search_planner_proposal_state
                    ),
                    current_search_planner_revision_state=(
                        self.state.search_planner_revision_state
                    ),
                    current_scout_disambiguation_report_state=(
                        self.state.scout_disambiguation_report_state
                    ),
                    current_parent_initial_contract=(
                        self.state.initial_answer_contract
                    ),
                    current_parent_current_contract=(
                        self.state.current_answer_contract
                    ),
                    existing_handoff_history=(
                        self.state.search_executor_handoff_history
                    ),
                )
                handoff_projection = build_search_executor_handoff_projection(
                    handoff_state=handoff_state
                )
            except SearchExecutorHandoffRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.search_executor_handoff_state = handoff_state
            self.state.search_executor_handoff_projection = handoff_projection
            self.state.search_executor_handoff_history.append(
                deepcopy(handoff_projection)
            )
            self.state.projections[action.stage] = deepcopy(handoff_projection)
        elif action.action_type is ActionType.LIVE_SEARCH_VALIDATE:
            try:
                validation_state = build_live_search_validation_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    current_parent_current_contract=(
                        self.state.current_answer_contract
                    ),
                    current_search_executor_handoff_state=(
                        self.state.search_executor_handoff_state
                    ),
                    existing_validation_history=(
                        self.state.live_search_validation_history
                    ),
                )
                validation_projection = build_live_search_validation_projection(
                    validation_state=validation_state
                )
            except LiveSearchValidationRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.live_search_validation_state = validation_state
            self.state.live_search_validation_projection = validation_projection
            self.state.live_search_validation_history.append(
                deepcopy(validation_projection)
            )
            self.state.projections[action.stage] = deepcopy(validation_projection)
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
        elif (
            action.action_type
            is ActionType.DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY
        ):
            if self.state.initial_answer_contract or self.state.current_answer_contract:
                raise RunKernelTransitionError(
                    "D-prime contract authority requires empty answer-contract state"
                )
            contract_payload = _safe_mapping(
                observation.payload.get("answer_contract_authority")
            )
            if not contract_payload:
                raise RunKernelTransitionError(
                    "D-prime contract authority observation requires "
                    "answer_contract_authority payload"
                )
            expected_version = _clean_text(
                action.inputs.get("expected_contract_version"),
                limit=200,
            )
            expected_digest = _clean_text(
                action.inputs.get("expected_contract_digest"),
                limit=128,
            )
            if (
                _clean_text(contract_payload.get("accepted_contract_version"))
                != expected_version
                or _clean_text(
                    contract_payload.get("accepted_contract_digest"),
                    limit=128,
                )
                != expected_digest
            ):
                raise RunKernelTransitionError(
                    "D-prime contract authority digest/version mismatch"
                )
            if contract_payload.get("run_id") != self.state.run_id:
                raise RunKernelTransitionError(
                    "D-prime contract authority run_id mismatch"
                )
            if contract_payload.get("request_id") != self.state.request_id:
                raise RunKernelTransitionError(
                    "D-prime contract authority request_id mismatch"
                )
            component_id = _clean_text(action.inputs.get("answer_component_id"))
            action_source_ids = {
                _clean_text(item)
                for item in action.inputs.get("source_obligation_candidate_ids", [])
            }
            action_source_ids.discard(None)
            component_refs = [
                _safe_mapping(item)
                for item in contract_payload.get("accepted_answer_component_refs", [])
                if isinstance(item, Mapping)
            ]
            matching_component = next(
                (
                    item
                    for item in component_refs
                    if item.get("component_id") == component_id
                ),
                {},
            )
            if not matching_component:
                raise RunKernelTransitionError(
                    "D-prime contract authority component binding missing"
                )
            payload_source_ids = {
                _clean_text(item)
                for item in matching_component.get(
                    "source_obligation_candidate_ids",
                    [],
                )
            }
            payload_source_ids.discard(None)
            if not action_source_ids or not action_source_ids.issubset(
                payload_source_ids
            ):
                raise RunKernelTransitionError(
                    "D-prime contract authority source-obligation lineage mismatch"
                )
            lineage = _safe_mapping(contract_payload.get("lineage"))
            if lineage.get("retained_refs_are_authority") is True:
                raise RunKernelTransitionError(
                    "retained D-prime refs cannot be answer-contract authority"
                )
            accepted_contract = deepcopy(dict(contract_payload))
            accepted_contract["owner"] = "RunKernel.DPrimeAnswerContractAuthority"
            accepted_contract["canonical_state"] = True
            accepted_contract["trace_only"] = False
            accepted_contract["storage_only"] = False
            accepted_contract["authorized_action_id"] = action.action_id
            current_contract = deepcopy(accepted_contract)
            current_contract["owner"] = "RunKernel.CurrentAnswerContract"
            current_contract["trace_key"] = "current_answer_contract"
            current_contract["current_answer_contract_created"] = True
            current_contract["lineage"] = {
                **_safe_mapping(current_contract.get("lineage")),
                "created_by": "RunKernel.DPrimeAnswerContractAuthority",
                "created_from": [
                    "ordinary_dprime_product_status",
                    "retained_source_fetch_read_lineage",
                    "component_source_obligation_lineage",
                ],
                "reducer_action_id": action.action_id,
                "retained_refs_are_lineage_only": True,
            }
            accepted_projection = {
                "owner": "RunKernel.DPrimeAnswerContractAuthority",
                "schema_version": accepted_contract.get("schema_version"),
                "canonical_state": True,
                "trace_only": False,
                "storage_only": False,
                "run_id": self.state.run_id,
                "request_id": self.state.request_id,
                "authorized_action_id": action.action_id,
                "accepted_contract_version": expected_version,
                "accepted_contract_digest": expected_digest,
                "parent_question_meaning_record_id": accepted_contract.get(
                    "parent_question_meaning_record_id"
                ),
                "parent_question_meaning_record_digest": accepted_contract.get(
                    "parent_question_meaning_record_digest"
                ),
                "accepted_answer_component_refs": deepcopy(component_refs),
                "accepted_answer_component_count": len(component_refs),
                "lineage": deepcopy(_safe_mapping(accepted_contract.get("lineage"))),
                "coverage_created": False,
                "semantic_observation_admitted": False,
                "sufficiency_decided": False,
                "final_answer_packet_created": False,
                "author_input_created": False,
                "citation_behavior_changed": False,
                "provider_search_behavior_changed": False,
                "runtime_behavior_changed": False,
                "live_validation_not_run": True,
            }
            current_projection = build_current_answer_contract_projection(
                current_answer_contract=current_contract
            )
            self.state.initial_answer_contract = accepted_contract
            self.state.initial_answer_contract_projection = accepted_projection
            self.state.initial_answer_contract_history.append(
                deepcopy(accepted_projection)
            )
            self.state.current_answer_contract = current_contract
            self.state.current_answer_contract_projection = current_projection
            self.state.current_answer_contract_history.append(
                deepcopy(current_projection)
            )
            self.state.projections[
                INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE
            ] = deepcopy(accepted_projection)
            self.state.projections[
                DPRIME_CURRENT_ANSWER_CONTRACT_AUTHORITY_STAGE
            ] = deepcopy(current_projection)
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
        elif action.action_type is ActionType.DPRIME_SOURCE_OBLIGATION_AUTHORITY:
            if self.state.dprime_source_obligation_authority_projection:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority is already consumed"
                )
            _require_dprime_downstream_closed(
                state=self.state,
                context="D-prime source-obligation authority",
            )
            source_state = _safe_mapping(
                observation.payload.get("dprime_source_obligation_authority")
            )
            if not source_state:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority observation requires "
                    "authority payload"
                )
            if source_state.get("owner") != "RunKernel.DPrimeSourceObligationAuthority":
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority requires RunKernel owner"
                )
            if source_state.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority requires canonical state"
                )
            if source_state.get("trace_only") is not False:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority must not be trace-only"
                )
            if source_state.get("storage_only") is not False:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority must not be storage-only"
                )
            if source_state.get("run_id") != self.state.run_id:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority run_id mismatch"
                )
            if source_state.get("request_id") != self.state.request_id:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority request_id mismatch"
                )
            if source_state.get("source_obligation_authority_id") != action.inputs.get(
                "source_obligation_authority_id"
            ):
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority id mismatch"
                )
            if source_state.get(
                "source_obligation_authority_digest"
            ) != action.inputs.get("source_obligation_authority_digest"):
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority digest mismatch"
                )
            if source_state.get("authority_consumed") is not True:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority must be consumed"
                )
            if source_state.get("source_obligation_status") != "satisfied":
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority requires satisfied status"
                )
            if source_state.get("component_coverage_only_treated_as_pass") is not False:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority cannot treat "
                    "ComponentCoverage alone as PASS"
                )
            if source_state.get("retained_ids_alone_are_authority") is not False:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority cannot treat retained "
                    "ids alone as authority"
                )
            _require_false_fields(
                source_state,
                (
                    "citation_eligibility_authority_consumed",
                    "citation_rendering_created",
                    "sufficiency_readiness_created",
                    "final_answer_packet_created",
                    "author_answer_created",
                    "product_correctness_claimed",
                ),
                context="D-prime source-obligation authority",
            )
            coverage_ref = _safe_mapping(source_state.get("component_coverage_ref"))
            coverage = self.state.component_coverage_projection
            for label in (
                "coverage_record_id",
                "coverage_record_digest",
                "coverage_reduction_digest",
            ):
                if coverage_ref.get(label) != coverage.get(label):
                    raise RunKernelTransitionError(
                        "D-prime source-obligation authority ComponentCoverage "
                        f"{label} mismatch"
                    )
            action_source_ids = _preserve_text_list(
                action.inputs.get("source_obligation_candidate_ids") or []
            )
            state_source_ids = _preserve_text_list(
                source_state.get("source_obligation_candidate_ids") or []
            )
            if not action_source_ids or action_source_ids != state_source_ids:
                raise RunKernelTransitionError(
                    "D-prime source-obligation authority source ids mismatch"
                )
            source_projection = _dprime_source_obligation_authority_projection(
                source_state
            )
            self.state.dprime_source_obligation_authority_state = source_state
            self.state.dprime_source_obligation_authority_projection = (
                source_projection
            )
            self.state.dprime_source_obligation_authority_history.append(
                deepcopy(source_projection)
            )
            self.state.projections[action.stage] = deepcopy(source_projection)
        elif action.action_type is ActionType.DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY:
            if self.state.dprime_citation_source_handoff_projection:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff authority is already consumed"
                )
            _require_dprime_downstream_closed(
                state=self.state,
                context="D-prime citation-source handoff authority",
            )
            handoff_state = _safe_mapping(
                observation.payload.get("dprime_citation_source_handoff_authority")
            )
            if not handoff_state:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff observation requires "
                    "handoff payload"
                )
            if handoff_state.get("owner") != (
                "RunKernel.DPrimeCitationSourceHandoffAuthority"
            ):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff requires RunKernel owner"
                )
            if handoff_state.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff requires canonical state"
                )
            if handoff_state.get("trace_only") is not False:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff must not be trace-only"
                )
            if handoff_state.get("storage_only") is not False:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff must not be storage-only"
                )
            if handoff_state.get("run_id") != self.state.run_id:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff run_id mismatch"
                )
            if handoff_state.get("request_id") != self.state.request_id:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff request_id mismatch"
                )
            if handoff_state.get("citation_source_handoff_id") != action.inputs.get(
                "citation_source_handoff_id"
            ):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff id mismatch"
                )
            if handoff_state.get("citation_source_handoff_digest") != action.inputs.get(
                "citation_source_handoff_digest"
            ):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff digest mismatch"
                )
            for required_flag in (
                "authority_consumed",
                "source_obligation_authority_consumed",
                "citation_eligibility_authority_consumed",
                "citation_source_handoff_consumed",
            ):
                if handoff_state.get(required_flag) is not True:
                    raise RunKernelTransitionError(
                        "D-prime citation-source handoff must set "
                        f"{required_flag}=True"
                    )
            _require_false_fields(
                handoff_state,
                (
                    "citation_rendering_created",
                    "citations_rendered",
                    "citation_formatter_invoked",
                    "ordered_product_source_output_created",
                    "sufficiency_readiness_created",
                    "final_answer_packet_created",
                    "author_answer_created",
                    "author_input_created",
                    "product_correctness_claimed",
                ),
                context="D-prime citation-source handoff authority",
            )
            source_ref = _safe_mapping(
                handoff_state.get("source_obligation_authority_ref")
            )
            source_projection = self.state.dprime_source_obligation_authority_projection
            if source_ref.get("source_obligation_authority_id") != (
                source_projection.get("source_obligation_authority_id")
            ):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff source authority id mismatch"
                )
            if source_ref.get("source_obligation_authority_digest") != (
                source_projection.get("source_obligation_authority_digest")
            ):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff source authority digest mismatch"
                )
            if not handoff_state.get("citation_source_records"):
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff requires source records"
                )
            action_source_ids = _preserve_text_list(
                action.inputs.get("citation_eligible_source_ids") or []
            )
            state_source_ids = _preserve_text_list(
                handoff_state.get("citation_eligible_source_ids") or []
            )
            if not action_source_ids or action_source_ids != state_source_ids:
                raise RunKernelTransitionError(
                    "D-prime citation-source handoff source ids mismatch"
                )
            handoff_projection = _dprime_citation_source_handoff_projection(
                handoff_state
            )
            self.state.dprime_citation_source_handoff_state = handoff_state
            self.state.dprime_citation_source_handoff_projection = (
                handoff_projection
            )
            self.state.dprime_citation_source_handoff_history.append(
                deepcopy(handoff_projection)
            )
            self.state.projections[action.stage] = deepcopy(handoff_projection)
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
            recovery_authority = (
                self._require_multicomponent_recovery_amendment_authority(
                    action.inputs
                )
            )
            recovery_posture = (
                "required_to_fulfill_existing_accepted_user_obligation"
            )
            if (
                amendment_projection.get("user_confirmation_posture")
                == recovery_posture
            ) != bool(recovery_authority):
                raise RunKernelTransitionError(
                    "automatic recovery amendment posture requires exact recovery authority"
                )
            if recovery_authority:
                operations = [
                    _safe_mapping(item)
                    for item in amendment_projection.get("operations") or ()
                ]
                trigger_refs = _safe_mapping(
                    amendment_projection.get("trigger_refs")
                )
                if (
                    len(operations) != 1
                    or operations[0].get("operation_kind") != "add_component"
                    or amendment_projection.get("disposition")
                    != "eligible_for_future_acceptance"
                    or amendment_projection.get("user_confirmation_posture")
                    != (
                        "required_to_fulfill_existing_accepted_user_obligation"
                    )
                    or amendment_projection.get("weakening_posture") != "none"
                    or recovery_authority.get("proposal_id")
                    not in (trigger_refs.get("gap_refs") or ())
                ):
                    raise RunKernelTransitionError(
                        "automatic recovery amendment exceeds its narrow authority class"
                    )
            self.state.contract_amendment_admission_state = amendment_state
            self.state.contract_amendment_admission_projection = amendment_projection
            self.state.contract_amendment_admission_history.append(
                deepcopy(amendment_projection)
            )
            self.state.projections[action.stage] = deepcopy(amendment_projection)
        elif action.action_type is ActionType.CONTRACT_AMENDMENT_APPLY:
            if not self.state.initial_answer_contract_projection:
                raise RunKernelTransitionError(
                    "contract amendment application requires an accepted "
                    "initial answer contract"
                )
            if not self.state.contract_amendment_admission_history:
                raise RunKernelTransitionError(
                    "contract amendment application requires a canonical "
                    "admitted amendment"
                )
            amendment_record_id = _clean_text(
                action.inputs.get("amendment_record_id")
            )
            amendment_record_digest = _clean_text(
                action.inputs.get("amendment_record_digest"),
                limit=128,
            )
            admission_digest = _clean_text(
                action.inputs.get("admission_digest"),
                limit=128,
            )
            admitted_amendment = {}
            for item in reversed(self.state.contract_amendment_admission_history):
                candidate = _safe_mapping(item)
                if (
                    _clean_text(candidate.get("amendment_record_id"))
                    == amendment_record_id
                    and _clean_text(
                        candidate.get("amendment_record_digest"),
                        limit=128,
                    )
                    == amendment_record_digest
                    and _clean_text(candidate.get("admission_digest"), limit=128)
                    == admission_digest
                ):
                    admitted_amendment = candidate
                    break
            if not admitted_amendment:
                raise RunKernelTransitionError(
                    "contract amendment application could not find the "
                    "canonical admitted amendment"
                )
            recovery_authority = (
                self._require_multicomponent_recovery_amendment_authority(
                    action.inputs
                )
            )
            recovery_posture = (
                "required_to_fulfill_existing_accepted_user_obligation"
            )
            if (
                admitted_amendment.get("user_confirmation_posture")
                == recovery_posture
            ) != bool(recovery_authority):
                raise RunKernelTransitionError(
                    "automatic recovery amendment application requires exact recovery authority"
                )
            if recovery_authority and (
                admitted_amendment.get("user_confirmation_posture")
                != "required_to_fulfill_existing_accepted_user_obligation"
                or admitted_amendment.get("disposition")
                != "eligible_for_future_acceptance"
            ):
                raise RunKernelTransitionError(
                    "automatic recovery amendment admission lost its authority class"
                )
            parent_contract = (
                self.state.current_answer_contract
                or self.state.initial_answer_contract
            )
            try:
                application_state = build_contract_amendment_application_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    admitted_amendment=admitted_amendment,
                    parent_contract=parent_contract,
                    initial_contract=self.state.initial_answer_contract,
                    component_coverage_history=self.state.component_coverage_history,
                    evidence_ledger_projection=(
                        self.state.evidence_ledger.to_projection().to_dict()
                    ),
                    application_history=(
                        self.state.contract_amendment_application_history
                    ),
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                )
                application_projection = (
                    build_contract_amendment_application_projection(
                        application_state=application_state
                    )
                )
            except ContractAmendmentApplicationError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            current_contract = _safe_mapping(
                application_state.get("current_answer_contract")
            )
            current_projection = _safe_mapping(
                application_projection.get("current_answer_contract_projection")
            )
            scheduler = self._scheduler_after_canonical_authority_transition(
                transition="contract_amendment_applied",
                current_answer_contract=current_contract,
            )
            self._commit_multicomponent_authority_supersession(
                pending=authority_supersession,
                scheduler=scheduler,
            )
            self._commit_deferred_authority_action(
                action=action,
                observation=observation,
                pending=authority_supersession,
            )
            self.state.contract_amendment_application_state = application_state
            self.state.contract_amendment_application_projection = (
                application_projection
            )
            self.state.contract_amendment_application_history.append(
                deepcopy(application_projection)
            )
            self.state.current_answer_contract = current_contract
            self.state.current_answer_contract_projection = current_projection
            self.state.current_answer_contract_history.append(
                deepcopy(current_projection)
            )
            self.state.projections[action.stage] = deepcopy(application_projection)
            if scheduler is not None:
                self.state.projections["multicomponent_graph_scheduler"] = scheduler
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
        elif action.action_type is ActionType.FINAL_ANSWER_PACKET_HARDEN:
            try:
                fap_state = build_hardened_final_answer_packet_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    sufficiency_readiness_state=(
                        self.state.sufficiency_readiness_state
                    ),
                    sufficiency_readiness_projection=(
                        self.state.sufficiency_readiness_projection
                    ),
                    sufficiency_readiness_history=(
                        self.state.sufficiency_readiness_history
                    ),
                )
                fap_projection = build_hardened_final_answer_packet_projection(
                    fap_state=fap_state,
                    existing_final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                )
            except FinalAnswerPacketHardeningRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            if fap_projection.get("packet_created") is True:
                self.state.final_answer_packet = fap_state
            else:
                self.state.final_answer_packet = {}
            self.state.final_answer_authority_projection = fap_projection
            self.state.final_answer_packet_history.append(deepcopy(fap_projection))
            self.state.projections[FINAL_ANSWER_PACKET_STAGE] = deepcopy(
                fap_projection
            )
        elif action.action_type is ActionType.AUTHOR_PROSE_FINALIZE:
            try:
                author_prose_state = build_author_prose_finalization_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    final_answer_packet_state=self.state.final_answer_packet,
                    final_answer_authority_projection=(
                        self.state.final_answer_authority_projection
                    ),
                )
                author_prose_projection = build_author_prose_finalization_projection(
                    author_prose_state=author_prose_state,
                    existing_author_prose_projection=(
                        self.state.author_prose_projection
                    ),
                )
            except AuthorProseFinalizationRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.author_prose_state = author_prose_state
            self.state.author_prose_projection = author_prose_projection
            self.state.author_prose_history.append(deepcopy(author_prose_projection))
            self.state.projections[AUTHOR_PROSE_FINALIZATION_STAGE] = deepcopy(
                author_prose_projection
            )
        elif action.action_type is ActionType.DPRIME_CITATION_SOURCE_DISPLAY:
            display = _safe_mapping(
                observation.payload.get("dprime_citation_source_display")
            )
            if not display:
                raise RunKernelTransitionError(
                    "D-prime source display observation requires display payload"
                )
            if display.get("owner") != "RunKernel.DPrimeCitationSourceDisplay":
                raise RunKernelTransitionError(
                    "D-prime source display requires RunKernel owner"
                )
            if display.get("canonical_state") is not True:
                raise RunKernelTransitionError(
                    "D-prime source display requires canonical state"
                )
            if display.get("trace_only") is not False:
                raise RunKernelTransitionError(
                    "D-prime source display must not be trace-only"
                )
            if display.get("storage_only") is not False:
                raise RunKernelTransitionError(
                    "D-prime source display must not be storage-only"
                )
            if display.get("run_id") != self.state.run_id:
                raise RunKernelTransitionError(
                    "D-prime source display run_id mismatch"
                )
            if display.get("request_id") != self.state.request_id:
                raise RunKernelTransitionError(
                    "D-prime source display request_id mismatch"
                )
            for label in (
                "display_id",
                "display_digest",
                "citation_source_handoff_id",
                "citation_source_handoff_digest",
                "author_prose_id",
                "author_prose_digest",
                "final_answer_packet_digest",
            ):
                if display.get(label) != action.inputs.get(label):
                    raise RunKernelTransitionError(
                        "D-prime source display "
                        f"{label} does not match authorized action"
                    )
            handoff = self.state.dprime_citation_source_handoff_projection
            if display.get("citation_source_handoff_id") != handoff.get(
                "citation_source_handoff_id"
            ):
                raise RunKernelTransitionError(
                    "D-prime source display handoff id mismatch"
                )
            if display.get("citation_source_handoff_digest") != handoff.get(
                "citation_source_handoff_digest"
            ):
                raise RunKernelTransitionError(
                    "D-prime source display handoff digest mismatch"
                )
            author = self.state.author_prose_projection
            if display.get("author_prose_id") != author.get("author_prose_id"):
                raise RunKernelTransitionError(
                    "D-prime source display AuthorProse id mismatch"
                )
            if display.get("author_prose_digest") != author.get("author_prose_digest"):
                raise RunKernelTransitionError(
                    "D-prime source display AuthorProse digest mismatch"
                )
            fap = self.state.final_answer_authority_projection
            expected_packet_digest = (
                fap.get("packet_digest")
                or fap.get("no_packet_digest")
                or fap.get("fap_digest")
            )
            if display.get("final_answer_packet_digest") != expected_packet_digest:
                raise RunKernelTransitionError(
                    "D-prime source display FinalAnswerPacket digest mismatch"
                )
            for required_flag in (
                "citation_source_handoff_consumed",
                "final_answer_packet_consumed",
                "author_answer_consumed",
                "citation_source_display_created",
            ):
                if display.get(required_flag) is not True:
                    raise RunKernelTransitionError(
                        "D-prime source display must set "
                        f"{required_flag}=True"
                    )
            if not display.get("citation_source_entries"):
                raise RunKernelTransitionError(
                    "D-prime source display requires source entries"
                )
            _require_false_fields(
                display,
                (
                    "product_correctness_claimed",
                    "author_answer_is_product_correctness",
                    "model_called",
                    "provider_called",
                    "live_provider_called",
                    "search_executed",
                    "fetch_read_executed",
                    "retrieval_executed",
                    "raw_prompt_retained",
                    "raw_model_response_retained",
                    "raw_provider_payload_retained",
                    "raw_source_text_retained",
                    "bounded_source_text_retained",
                    "db_rows_retained",
                    "cache_rows_retained",
                    "private_logs_retained",
                ),
                context="D-prime source display",
            )
            self.state.projections[action.stage] = deepcopy(display)
        elif (
            action.action_type
            is ActionType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZE
        ):
            reduction_inputs = {
                **_safe_mapping(action.inputs),
                **_safe_mapping(observation.payload),
            }
            authorization = (
                build_single_relation_source_obligation_recovery_authorization(
                    relation_plan=_safe_mapping(
                        reduction_inputs.get("relation_plan")
                    ),
                    acquisition_plan=_safe_mapping(
                        reduction_inputs.get("acquisition_plan")
                    ),
                    selected_candidate_diagnostic=_safe_mapping(
                        reduction_inputs.get("selected_candidate_diagnostic")
                    ),
                    candidate_diagnostics=tuple(
                        _safe_mapping(item)
                        for item in (
                            reduction_inputs.get("candidate_diagnostics") or ()
                        )
                    ),
                    dprime_status=_safe_mapping(
                        reduction_inputs.get("dprime_status")
                    ),
                    provider_acquisition_attempt_counts=_safe_mapping(
                        reduction_inputs.get("provider_acquisition_attempt_counts")
                    ),
                    evidence_admission_ref=_safe_mapping(
                        reduction_inputs.get("evidence_admission_ref")
                    ),
                    recovery_attempt_ref=_safe_mapping(
                        reduction_inputs.get("recovery_attempt_ref")
                    ),
                    recovery_attempt_counts=_safe_mapping(
                        reduction_inputs.get("recovery_attempt_counts")
                    ),
                    recovery_confirmation_authorized=bool(
                        reduction_inputs.get("recovery_confirmation_authorized")
                    ),
                )
            )
            authorization_projection = authorization.to_dict()
            contract_projection = _safe_mapping(
                authorization_projection.get("current_answer_contract_projection")
            )
            contract_state = _safe_mapping(
                authorization_projection.get("updated_contract_state")
            )
            if not contract_projection or not contract_state:
                raise RunKernelTransitionError(
                    "single-relation source-obligation recovery authorization "
                    "requires contract projection and updated state"
                )
            run_kernel_ref = {
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "observation_id": observation.observation_id,
                "observation_type": observation.observation_type.value,
                "stage": action.stage,
                "run_id": self.state.run_id,
                "request_id": self.state.request_id,
                "sequence": action.sequence,
            }
            authorization_projection.update(
                {
                    "run_kernel_reduced": True,
                    "run_kernel_action_ref": dict(run_kernel_ref),
                    "run_kernel_observation_ref": dict(run_kernel_ref),
                    "run_state_projection_key": action.stage,
                }
            )
            authorization_projection["current_answer_contract_projection"] = {
                **contract_projection,
                "run_kernel_reduced": True,
                "run_state_projection_key": action.stage,
                "run_kernel_action_ref": dict(run_kernel_ref),
                "run_kernel_observation_ref": dict(run_kernel_ref),
            }
            authorization_projection["updated_contract_state"] = {
                **contract_state,
                "run_kernel_reduced": True,
                "run_state_projection_key": action.stage,
                "run_kernel_action_ref": dict(run_kernel_ref),
                "run_kernel_observation_ref": dict(run_kernel_ref),
            }
            self.state.projections[action.stage] = deepcopy(
                authorization_projection
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
            graph = _safe_mapping(
                self.state.projections.get(
                    "multicomponent_component_work_graph_v1"
                )
            )
            if graph:
                sufficiency_inputs = _safe_mapping(
                    self.state.sufficiency_judgment_projection.get(
                        "final_packet_inputs"
                    )
                )
                if (
                    packet_projection.get("direct_component_entries", [])
                    != sufficiency_inputs.get("direct_component_entries", [])
                    or packet_projection.get("admitted_synthesis_entries", [])
                    != sufficiency_inputs.get("admitted_synthesis_entries", [])
                    or packet_projection.get("multicomponent_graph_readiness")
                    != sufficiency_inputs.get("multicomponent_graph_readiness")
                    or packet_projection.get("multicomponent_limitations", [])
                    != sufficiency_inputs.get("multicomponent_limitations", [])
                ):
                    raise RunKernelTransitionError(
                        "FinalAnswerPacket multi-component content must come from ordinary Sufficiency"
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
                "direct_component_entry_count": len(
                    packet_projection.get("direct_component_entries", []) or []
                ),
                "admitted_synthesis_entry_count": len(
                    packet_projection.get("admitted_synthesis_entries", []) or []
                ),
                "multicomponent_graph_readiness": packet_projection.get(
                    "multicomponent_graph_readiness"
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
        elif action.action_type is ActionType.FOLLOWUP_SEARCH_AUTHORIZE:
            try:
                authorization_state = build_followup_search_authorization_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    existing_authorization_projection=self.state.projections.get(
                        FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
                        {},
                    ),
                )
                authorization_projection = (
                    build_followup_search_authorization_projection(
                        authorization_state=authorization_state
                    )
                )
            except FollowupSearchAuthorizationRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.projections[action.stage] = deepcopy(
                authorization_projection
            )
        elif action.action_type is ActionType.SCRUTINEER_REVIEW_REDUCE:
            try:
                scrutineer_state = build_scrutineer_review_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    existing_review_projection=self.state.scrutineer_review_projection,
                )
                scrutineer_projection = build_scrutineer_review_projection(
                    scrutineer_review_state=scrutineer_state
                )
            except ScrutineerReviewRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.scrutineer_review_state = scrutineer_state
            self.state.scrutineer_review_projection = scrutineer_projection
            self.state.scrutineer_review_history.append(
                deepcopy(scrutineer_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                scrutineer_projection
            )
        elif action.action_type is (
            ActionType.SPECIALIST_SOURCE_BOUND_CALCULATION_REDUCE
        ):
            try:
                specialist_state = build_specialist_source_bound_calculation_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    existing_calculation_projection=(
                        self.state.specialist_source_bound_calculation_projection
                    ),
                )
                specialist_projection = (
                    build_specialist_source_bound_calculation_projection(
                        calculation_state=specialist_state
                    )
                )
            except SpecialistSourceBoundCalculationRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.specialist_source_bound_calculation_state = specialist_state
            self.state.specialist_source_bound_calculation_projection = (
                specialist_projection
            )
            self.state.specialist_source_bound_calculation_history.append(
                deepcopy(specialist_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                specialist_projection
            )
        elif action.action_type is ActionType.SUFFICIENCY_READINESS_DECIDE:
            try:
                readiness_state = build_sufficiency_readiness_state(
                    action_id=action.action_id,
                    action_inputs=action.inputs,
                    observation_payload=observation.payload,
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    current_answer_contract=(
                        self.state.current_answer_contract
                        or self.state.initial_answer_contract
                    ),
                    component_coverage_projection=(
                        self.state.component_coverage_projection
                    ),
                    component_coverage_history=self.state.component_coverage_history,
                    semantic_observation_admission_projection=(
                        self.state.semantic_observation_admission_projection
                    ),
                    semantic_observation_admission_history=(
                        self.state.semantic_observation_admission_history
                    ),
                    scrutineer_review_projection=(
                        self.state.scrutineer_review_projection
                    ),
                    scrutineer_review_history=self.state.scrutineer_review_history,
                    specialist_source_bound_calculation_projection=(
                        self.state.specialist_source_bound_calculation_projection
                    ),
                    specialist_source_bound_calculation_history=(
                        self.state.specialist_source_bound_calculation_history
                    ),
                    followup_search_authorization_projection=(
                        self.state.projections.get(
                            FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
                            {},
                        )
                    ),
                    existing_readiness_projection=(
                        self.state.sufficiency_readiness_projection
                    ),
                )
                readiness_projection = build_sufficiency_readiness_projection(
                    readiness_state=readiness_state
                )
            except SufficiencyReadinessRuntimeError as exc:
                raise RunKernelTransitionError(str(exc)) from exc
            self.state.sufficiency_readiness_state = readiness_state
            self.state.sufficiency_readiness_projection = readiness_projection
            self.state.sufficiency_readiness_history.append(
                deepcopy(readiness_projection)
            )
            self.state.projections[action.stage] = deepcopy(
                readiness_projection
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
        elif action.action_type is ActionType.MULTICOMPONENT_RECOVERY_AUTHORIZE:
            from core.component_work_graph_v1 import (
                COMPONENT_WORK_GRAPH_V1_STAGE,
            )
            from core.multicomponent_role_runtime import safe_packet_digest

            current_graph = _safe_mapping(
                self.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
            )
            if (
                current_graph.get("graph_id") != action.inputs.get("graph_id")
                or current_graph.get("graph_revision")
                != action.inputs.get("graph_revision")
                or current_graph.get("graph_digest")
                != action.inputs.get("graph_digest")
            ):
                raise RunKernelTransitionError(
                    "multi-component recovery authorization became stale"
                )
            active_contract = (
                self.state.current_answer_contract
                or self.state.initial_answer_contract
            )
            if (
                active_contract.get("accepted_contract_version")
                != action.inputs.get("accepted_contract_version")
                or active_contract.get("accepted_contract_digest")
                != action.inputs.get("accepted_contract_digest")
            ):
                raise RunKernelTransitionError(
                    "multi-component recovery AnswerContract binding became stale"
                )
            recovery_actions = [
                item
                for item in self.state.issued_actions.values()
                if item.action_type
                is ActionType.MULTICOMPONENT_RECOVERY_AUTHORIZE
            ]
            if recovery_actions != [action]:
                raise RunKernelTransitionError(
                    "multi-component recovery authorization history is not singular"
                )
            recovery_observation_count = 1 + sum(
                1
                for item in self.state.observations
                if self.state.issued_actions.get(item.action_id)
                and self.state.issued_actions[item.action_id].action_type
                is ActionType.MULTICOMPONENT_RECOVERY_AUTHORIZE
            )
            projection_core = {
                "schema_version": (
                    "multicomponent_missing_component_recovery_authorization_v1"
                ),
                "owner": "RunKernel.MulticomponentRecoveryAuthorization",
                "canonical_state": True,
                "run_id": self.state.run_id,
                "request_id": self.state.request_id,
                "authorization_id": (
                    f"multicomponent-recovery:{action.action_id}"
                ),
                "authorized_action_id": action.action_id,
                "proposal_id": action.inputs.get("proposal_id"),
                "proposal_key": action.inputs.get("proposal_key"),
                "proposal_digest": action.inputs.get("proposal_digest"),
                "proposal": _safe_mapping(action.inputs.get("proposal")),
                "scrutineer_artifact_id": action.inputs.get(
                    "scrutineer_artifact_id"
                ),
                "scrutineer_artifact_digest": action.inputs.get(
                    "scrutineer_artifact_digest"
                ),
                "scrutineer_action_id": action.inputs.get(
                    "scrutineer_action_id"
                ),
                "target_kind": action.inputs.get("target_kind"),
                "target_key": action.inputs.get("target_key"),
                "resolved_target": _safe_mapping(
                    action.inputs.get("resolved_target")
                ),
                "graph_id": action.inputs.get("graph_id"),
                "graph_revision": action.inputs.get("graph_revision"),
                "graph_digest": action.inputs.get("graph_digest"),
                "accepted_contract_version": action.inputs.get(
                    "accepted_contract_version"
                ),
                "accepted_contract_digest": action.inputs.get(
                    "accepted_contract_digest"
                ),
                "automatic_amendment_authority_class": action.inputs.get(
                    "automatic_amendment_authority_class"
                ),
                "recovery_scope_posture": action.inputs.get(
                    "recovery_scope_posture"
                ),
                "component_count_before_recovery": action.inputs.get(
                    "component_count_before_recovery"
                ),
                "maximum_component_count": action.inputs.get(
                    "maximum_component_count"
                ),
                "recovery_authorization_action_count": len(recovery_actions),
                "recovery_authorization_observation_count": (
                    recovery_observation_count
                ),
                "contract_amendment_application_action_count": sum(
                    item.action_type is ActionType.CONTRACT_AMENDMENT_APPLY
                    for item in self.state.issued_actions.values()
                ),
                "graph_amendment_action_count": sum(
                    item.action_type is ActionType.MULTICOMPONENT_GRAPH_REDUCE
                    and item.inputs.get("operation") == "graph_amendment"
                    for item in self.state.issued_actions.values()
                ),
                "recovery_round": action.inputs.get("recovery_round"),
                "amendment_round": action.inputs.get("amendment_round"),
                "graph_amendment_round": action.inputs.get(
                    "graph_amendment_round"
                ),
                "component_research_reentry_round": action.inputs.get(
                    "component_research_reentry_round"
                ),
                "whole_graph_resynthesis_round": action.inputs.get(
                    "whole_graph_resynthesis_round"
                ),
                "selective_recomputation_round": action.inputs.get(
                    "selective_recomputation_round"
                ),
                "search_authorized": action.inputs.get("search_authorized")
                is True,
                "provider_selected": False,
                "component_admitted": False,
                "contract_amendment_applied": False,
            }
            projection = {
                **projection_core,
                "authorization_digest": safe_packet_digest(projection_core),
            }
            self.state.projections[action.stage] = projection
        elif (
            action.action_type
            is ActionType.MULTICOMPONENT_RECOVERY_OUTCOME_REDUCE
        ):
            from core.component_work_graph_v1 import (
                COMPONENT_WORK_GRAPH_V1_STAGE,
                GRAPH_STATUS_READY,
                GRAPH_STATUS_READY_WITH_CAVEATS,
                MULTICOMPONENT_CARRY_FORWARD_STAGE,
                MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
                validate_component_work_graph_v1,
            )
            from core.multicomponent_component_admission import (
                MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
            )
            from core.multicomponent_role_runtime import safe_packet_digest
            from core.search_executor_handoff_runtime import (
                handoff_ref_from_handoff_state,
                planner_ref_from_search_planner_state,
            )
            from core.search_result_candidate_packet import (
                build_search_result_candidate_packet_from_live_validation_state,
                search_result_candidate_packet_ref_from_packet,
                validate_search_result_candidate_packet,
            )

            if observation.payload:
                raise RunKernelTransitionError(
                    "recovery outcome observation cannot supply authority fields"
                )
            authorization = _safe_mapping(
                self.state.projections.get(
                    MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
                )
            )
            if (
                authorization.get("authorization_id")
                != action.inputs.get("recovery_authorization_id")
                or authorization.get("authorization_digest")
                != action.inputs.get("recovery_authorization_digest")
                or authorization.get("run_id") != self.state.run_id
                or authorization.get("request_id") != self.state.request_id
            ):
                raise RunKernelTransitionError(
                    "recovery outcome authorization binding became stale"
                )
            disposition = str(action.inputs.get("disposition") or "")
            providers = list(
                action.inputs.get("observed_provider_identities") or ()
            )
            active_contract = _safe_mapping(
                self.state.current_answer_contract
                or self.state.initial_answer_contract
            )
            graph = validate_component_work_graph_v1(
                _safe_mapping(
                    self.state.projections.get(
                        COMPONENT_WORK_GRAPH_V1_STAGE
                    )
                )
            )
            graph_contract = _safe_mapping(graph.get("accepted_contract_ref"))
            amendment_admission = _safe_mapping(
                self.state.contract_amendment_admission_projection
            )
            amendment_application = _safe_mapping(
                self.state.contract_amendment_application_projection
            )
            planner_ref = planner_ref_from_search_planner_state(
                self.state.search_planner_proposal_state
            )
            handoff_ref = handoff_ref_from_handoff_state(
                self.state.search_executor_handoff_state
            )
            live_state = _safe_mapping(self.state.live_search_validation_state)
            selected_task_refs = [
                {
                    "search_task_id": item.get("search_task_id"),
                    "query_intent_id": item.get("query_intent_id"),
                    "component_id": item.get("component_id"),
                    "source_obligation_candidate_ids": list(
                        item.get("source_obligation_candidate_ids") or ()
                    ),
                }
                for item in self.state.search_executor_handoff_state.get(
                    "search_task_records", ()
                )
                if isinstance(item, Mapping)
                and item.get("search_task_id")
                in set(live_state.get("selected_search_task_ids") or ())
            ]
            candidate_packet_ref: dict[str, Any] = {}
            if live_state:
                candidate_packet = validate_search_result_candidate_packet(
                    build_search_result_candidate_packet_from_live_validation_state(
                        live_state
                    )
                )
                candidate_packet_ref = (
                    search_result_candidate_packet_ref_from_packet(
                        candidate_packet
                    )
                )
                if live_state.get("provider_used") not in providers:
                    raise RunKernelTransitionError(
                        "recovery outcome lost actual ordinary provider identity"
                    )
            authorization_action = self.state.issued_actions.get(
                str(authorization.get("authorized_action_id") or "")
            )
            authorization_sequence = (
                authorization_action.sequence
                if authorization_action is not None
                else -1
            )
            recovery_ledger_actions = [
                item
                for item in self.state.issued_actions.values()
                if item.action_type is ActionType.EVIDENCE_LEDGER_REDUCE
                and item.action_id in self.state.reduced_action_ids
                and item.sequence > authorization_sequence
            ]
            fetch_actions = [
                item
                for item in recovery_ledger_actions
                if item.inputs.get("fetch_read_content_packet_id")
            ]
            fetch_action = fetch_actions[-1] if fetch_actions else None
            fetch_packet_ref = (
                {
                    "packet_id": fetch_action.inputs.get(
                        "fetch_read_content_packet_id"
                    ),
                    "packet_digest": fetch_action.inputs.get(
                        "fetch_read_content_packet_digest"
                    ),
                }
                if fetch_action is not None
                else {}
            )
            ledger_action = (
                recovery_ledger_actions[-1]
                if recovery_ledger_actions
                else None
            )
            ledger_observation = next(
                (
                    item
                    for item in reversed(self.state.observations)
                    if ledger_action is not None
                    and item.action_id == ledger_action.action_id
                ),
                None,
            )
            ledger_ref = (
                {
                    "action_id": ledger_action.action_id,
                    "observation_id": (
                        ledger_observation.observation_id
                        if ledger_observation is not None
                        else None
                    ),
                }
                if ledger_action is not None
                else {}
            )
            component_id = (
                f"component:recovered:"
                f"{str(authorization.get('proposal_digest') or '')[:16]}"
            )
            component_projection = _safe_mapping(
                self.state.projections.get(
                    MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
                )
            )
            matching_admissions = [
                _safe_mapping(item)
                for item in component_projection.get(
                    "component_admission_refs", ()
                )
                if isinstance(item, Mapping)
                and item.get("component_id") == component_id
            ]
            component_admission_ref = (
                matching_admissions[-1] if matching_admissions else {}
            )
            candidate_count = int(live_state.get("candidate_count") or 0)
            graph_ready = graph.get("graph_status") in {
                GRAPH_STATUS_READY,
                GRAPH_STATUS_READY_WITH_CAVEATS,
            }
            admitted = component_admission_ref.get("admission_status") in {
                "admitted",
                "admitted_with_caveats",
            }
            selective_closure = _safe_mapping(
                self.state.projections.get(MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE)
            )
            carry_forward = _safe_mapping(
                self.state.projections.get(MULTICOMPONENT_CARRY_FORWARD_STAGE)
            )
            if disposition == "blocked_requires_user_confirmation":
                if (
                    authorization.get("search_authorized") is not False
                    or planner_ref
                    or handoff_ref
                    or live_state
                    or amendment_application
                ):
                    raise RunKernelTransitionError(
                        "confirmation-blocked recovery outcome has execution state"
                    )
            elif disposition == "blocked_no_candidates":
                if (
                    candidate_count != 0
                    or component_admission_ref
                    or fetch_packet_ref
                    or ledger_ref
                ):
                    raise RunKernelTransitionError(
                        "no-candidate recovery outcome conflicts with canonical state"
                    )
            elif disposition == "blocked_no_readable_evidence":
                if (
                    candidate_count <= 0
                    or component_admission_ref
                    or not fetch_packet_ref
                    or not ledger_ref
                ):
                    raise RunKernelTransitionError(
                        "no-readable recovery outcome conflicts with canonical state"
                    )
            elif disposition == "blocked_component_admission":
                if not component_admission_ref or admitted:
                    raise RunKernelTransitionError(
                        "component-blocked recovery outcome conflicts with admission"
                    )
            elif disposition == "blocked_resynthesis":
                if not admitted or graph_ready:
                    raise RunKernelTransitionError(
                        "resynthesis-blocked recovery outcome conflicts with graph"
                    )
            elif disposition == "acquired":
                if not admitted or not graph_ready:
                    raise RunKernelTransitionError(
                        "acquired recovery outcome requires admitted component and ready graph"
                    )
                if (
                    int(graph.get("selective_recomputation_rounds") or 0) != 1
                    or int(graph.get("whole_graph_resynthesis_rounds") or 0) != 0
                    or _safe_mapping(graph.get("selective_closure_ref"))
                    != {
                        "closure_id": selective_closure.get("closure_id"),
                        "closure_digest": selective_closure.get("closure_digest"),
                    }
                    or _safe_mapping(carry_forward.get("final_graph_ref")).get(
                        "graph_id"
                    )
                    != graph.get("graph_id")
                    or int(
                        _safe_mapping(carry_forward.get("final_graph_ref")).get(
                            "graph_revision"
                        )
                        or 0
                    )
                    >= int(graph.get("graph_revision") or 0)
                    or not _safe_mapping(carry_forward.get("final_graph_ref")).get(
                        "graph_digest"
                    )
                    or int(carry_forward.get("carry_forward_count") or 0)
                    != int(graph.get("carry_forward_count") or 0)
                ):
                    raise RunKernelTransitionError(
                        "acquired recovery outcome lacks exact selective recomputation authority"
                    )
            pre_recovery_synthesis_suppressed = bool(
                graph.get("pre_recovery_synthesis_authority_invalidated")
                or graph.get("graph_output_suppressed")
                or not graph_ready
                or graph_contract.get("accepted_contract_digest")
                != active_contract.get("accepted_contract_digest")
            )
            if not pre_recovery_synthesis_suppressed:
                raise RunKernelTransitionError(
                    "recovery outcome requires pre-recovery synthesis suppression"
                )
            outcome_actions = [
                item
                for item in self.state.issued_actions.values()
                if item.action_type
                is ActionType.MULTICOMPONENT_RECOVERY_OUTCOME_REDUCE
            ]
            if outcome_actions != [action]:
                raise RunKernelTransitionError(
                    "recovery outcome action history is not singular"
                )
            projection_core = {
                "schema_version": "multicomponent_recovery_outcome_v1",
                "owner": "RunKernel.MulticomponentRecoveryOutcome",
                "canonical_state": True,
                "trace_only": False,
                "final_answer_authority": True,
                "run_id": self.state.run_id,
                "request_id": self.state.request_id,
                "outcome_id": f"multicomponent-recovery-outcome:{action.action_id}",
                "authorized_action_id": action.action_id,
                "recovery_disposition": disposition,
                "bounded_blocker_reason": action.inputs.get("blocker_reason"),
                "recovery_authorization_id": authorization.get(
                    "authorization_id"
                ),
                "recovery_authorization_digest": authorization.get(
                    "authorization_digest"
                ),
                "proposal_id": authorization.get("proposal_id"),
                "proposal_digest": authorization.get("proposal_digest"),
                "scrutineer_artifact_id": authorization.get(
                    "scrutineer_artifact_id"
                ),
                "scrutineer_artifact_digest": authorization.get(
                    "scrutineer_artifact_digest"
                ),
                "current_answer_contract_version": active_contract.get(
                    "accepted_contract_version"
                ),
                "current_answer_contract_digest": active_contract.get(
                    "accepted_contract_digest"
                ),
                "graph_id": graph.get("graph_id"),
                "graph_revision": graph.get("graph_revision"),
                "graph_digest": graph.get("graph_digest"),
                "graph_answer_contract_version": graph_contract.get(
                    "accepted_contract_version"
                ),
                "graph_answer_contract_digest": graph_contract.get(
                    "accepted_contract_digest"
                ),
                "ordinary_acquisition_attempt_count": (
                    0
                    if disposition
                    == "blocked_requires_user_confirmation"
                    else 1
                ),
                "observed_provider_identities": providers,
                "pre_recovery_synthesis_suppressed": (
                    pre_recovery_synthesis_suppressed
                ),
                "direct_semantic_producer_used": False,
                "runtime_parallelism": False,
                "recovery_outcome_action_count": len(outcome_actions),
                "recovery_outcome_observation_count": 1,
            }
            if selective_closure:
                projection_core.update(
                    {
                        "selective_recomputation_rounds": int(
                            graph.get("selective_recomputation_rounds") or 0
                        ),
                        "whole_graph_resynthesis_rounds": int(
                            graph.get("whole_graph_resynthesis_rounds") or 0
                        ),
                        "affected_synthesis_count": int(
                            graph.get("affected_synthesis_count") or 0
                        ),
                        "preserved_synthesis_count": int(
                            graph.get("preserved_synthesis_count") or 0
                        ),
                        "recomputed_synthesis_count": int(
                            graph.get("recomputed_synthesis_count") or 0
                        ),
                        "carry_forward_count": int(
                            graph.get("carry_forward_count") or 0
                        ),
                        "selective_closure_ref": {
                            "closure_id": selective_closure.get("closure_id"),
                            "closure_digest": selective_closure.get(
                                "closure_digest"
                            ),
                        },
                        "fresh_affected_synthesis_refs": [
                            {
                                "node_kind": item.get("node_kind"),
                                "node_id": item.get("node_id"),
                                "node_revision": item.get("node_revision"),
                                "node_digest": item.get("node_digest"),
                                "synthesis_key": item.get("synthesis_key"),
                                "status": item.get("status"),
                                "current": item.get("current") is True,
                                "stale": item.get("stale") is True,
                            }
                            for item in graph.get("synthesis_nodes") or ()
                            if item.get("synthesis_key")
                            in set(
                                selective_closure.get(
                                    "affected_synthesis_keys", ()
                                )
                            )
                        ],
                        "fresh_full_case_scrutineer_ref": _safe_mapping(
                            graph.get("scrutineer_ref")
                        ),
                        "logical_role_accounting": _safe_mapping(
                            graph.get("logical_accounting")
                        ),
                        "physical_role_call_accounting": _safe_mapping(
                            graph.get("physical_call_accounting")
                        ),
                    }
                )
            if carry_forward:
                projection_core["carry_forward_projection_ref"] = {
                    "carry_forward_projection_digest": carry_forward.get(
                        "carry_forward_projection_digest"
                    ),
                    "runkernel_carry_forward_action_ref": _safe_mapping(
                        carry_forward.get("runkernel_carry_forward_action_ref")
                    ),
                    "final_graph_ref": _safe_mapping(
                        carry_forward.get("final_graph_ref")
                    ),
                    "carry_forward_count": carry_forward.get(
                        "carry_forward_count"
                    ),
                }
            if amendment_admission:
                projection_core.update(
                    {
                        "amendment_record_id": amendment_admission.get(
                            "amendment_record_id"
                        ),
                        "amendment_record_digest": amendment_admission.get(
                            "amendment_record_digest"
                        ),
                        "amendment_admission_action_id": amendment_admission.get(
                            "authorized_action_id"
                        ),
                        "amendment_admission_digest": amendment_admission.get(
                            "admission_digest"
                        ),
                    }
                )
            if amendment_application:
                projection_core.update(
                    {
                        "amendment_application_action_id": (
                            amendment_application.get("authorized_action_id")
                        ),
                        "amendment_application_digest": (
                            amendment_application.get("application_digest")
                        ),
                        "recovered_component_id": component_id,
                    }
                )
            if planner_ref:
                projection_core["ordinary_search_planner_ref"] = planner_ref
            if handoff_ref:
                projection_core[
                    "ordinary_search_executor_handoff_ref"
                ] = handoff_ref
            if selected_task_refs:
                projection_core["selected_search_task_refs"] = selected_task_refs
            if candidate_packet_ref:
                projection_core[
                    "search_result_candidate_packet_ref"
                ] = candidate_packet_ref
            if fetch_packet_ref:
                projection_core["fetch_read_content_packet_ref"] = fetch_packet_ref
            if ledger_ref:
                projection_core["evidence_ledger_reduction_ref"] = ledger_ref
            if component_admission_ref:
                projection_core["component_admission_ref"] = component_admission_ref
            outcome_projection = {
                **projection_core,
                "outcome_digest": safe_packet_digest(projection_core),
            }
            self.state.projections[action.stage] = outcome_projection
            self.state.projections[f"{action.stage}_history"] = {
                "schema_version": "multicomponent_recovery_outcome_history_v1",
                "owner": "RunKernel.MulticomponentRecoveryOutcome",
                "canonical_state": True,
                "trace_only": False,
                "outcome_count": 1,
                "outcomes": [deepcopy(outcome_projection)],
            }
        elif action.action_type is ActionType.SPECIALIST_PROPOSAL_BIND:
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
                block_required_specialist_proposal,
            )
            from core.specialist_graph_runtime import (
                AVAILABILITY_CAPABILITY,
                AVAILABILITY_POLICY,
                AVAILABILITY_TARGET,
                PROPOSAL_ACCEPTED,
                PROPOSAL_DENIED_POLICY,
                PROPOSAL_REJECTED,
                PROPOSAL_UNSUPPORTED_TARGET,
                SPECIALIST_WORK_PLANE_STAGE,
                append_bound_proposal,
                append_specialist_disposition,
                validate_bound_specialist_proposal,
            )

            proposal = validate_bound_specialist_proposal(
                _safe_mapping(observation.payload.get("bound_specialist_proposal"))
            )
            origin_action_id = str(action.inputs.get("origin_action_id") or "")
            if (
                action.inputs.get("proposal_id") != proposal.get("proposal_id")
                or action.inputs.get("proposal_digest")
                != proposal.get("proposal_digest")
                or _safe_mapping(proposal.get("origin_action_ref")).get(
                    "action_id"
                )
                != origin_action_id
                or origin_action_id not in self.state.reduced_action_ids
                or action.inputs.get("registry_digest")
                != proposal.get("registry_digest")
                or action.inputs.get("execution_policy_digest")
                != proposal.get("execution_policy_digest")
            ):
                raise RunKernelTransitionError(
                    "Specialist proposal binding lacks exact current authority"
                )
            plane = append_bound_proposal(
                _safe_mapping(
                    self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE)
                ),
                proposal,
            )
            self.state.projections[SPECIALIST_WORK_PLANE_STAGE] = plane
            self.state.projections[action.stage] = deepcopy(proposal)
            if proposal.get("proposal_authority") != PROPOSAL_ACCEPTED:
                disposition_contract = {
                    PROPOSAL_DENIED_POLICY: (
                        AVAILABILITY_POLICY,
                        "denied_by_policy",
                    ),
                    PROPOSAL_REJECTED: (
                        AVAILABILITY_CAPABILITY,
                        "unknown_or_incompatible_capability",
                    ),
                    PROPOSAL_UNSUPPORTED_TARGET: (
                        AVAILABILITY_TARGET,
                        "unsupported_target",
                    ),
                }
                availability, reason = disposition_contract[
                    str(proposal.get("proposal_authority") or "")
                ]
                plane = append_specialist_disposition(
                    plane,
                    proposal=proposal,
                    availability_posture=availability,
                    nonexecution_reason=reason,
                )
                self.state.projections[SPECIALIST_WORK_PLANE_STAGE] = plane
            if (
                proposal.get("posture") == "required"
                and proposal.get("proposal_authority") != PROPOSAL_ACCEPTED
            ):
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    block_required_specialist_proposal(
                        state=self.state,
                        proposal=proposal,
                    )
                )
        elif action.action_type is ActionType.SPECIALIST_PROPOSAL_DISPOSE:
            from core.multicomponent_graph_scheduling import (
                LEASE_CANCELLED,
                MULTICOMPONENT_SCHEDULER_STAGE,
                WORK_KIND_SPECIALIST_CAPABILITY,
                block_required_specialist_reconstruction_failure,
            )
            from core.specialist_graph_runtime import (
                AVAILABILITY_BUDGET,
                AVAILABILITY_FAILED,
                PROPOSAL_ACCEPTED,
                SPECIALIST_WORK_PLANE_STAGE,
                append_specialist_disposition,
                validate_bound_specialist_proposal,
            )

            plane = _safe_mapping(
                self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE)
            )
            proposal_id = str(action.inputs.get("proposal_id") or "")
            proposal = next(
                (
                    validate_bound_specialist_proposal(_safe_mapping(item))
                    for item in plane.get("proposals") or ()
                    if _safe_mapping(item).get("proposal_id") == proposal_id
                ),
                {},
            )
            scheduler = _safe_mapping(
                self.state.projections.get(MULTICOMPONENT_SCHEDULER_STAGE)
            )
            pool = _safe_mapping(
                scheduler.get("specialist_compatibility_pool")
            )
            nonexecution_reason = str(
                action.inputs.get("nonexecution_reason") or ""
            )
            active_proposal_ids = {
                _safe_mapping(_safe_mapping(item).get("work"))
                .get("specialist_proposal_ref", {})
                .get("proposal_id")
                for item in scheduler.get("lease_history") or ()
                if _safe_mapping(item).get("status")
                in {"granted_reserved", "execution_started_spent"}
                and _safe_mapping(_safe_mapping(item).get("work")).get(
                    "work_kind"
                )
                == WORK_KIND_SPECIALIST_CAPABILITY
            }
            common_invalid = (
                not proposal
                or proposal.get("proposal_digest")
                != action.inputs.get("proposal_digest")
                or proposal.get("proposal_authority") != PROPOSAL_ACCEPTED
                or proposal_id in active_proposal_ids
            )
            blocked_scheduler: dict[str, Any] = {}
            if nonexecution_reason == "specialist_pool_exhausted":
                invalid = (
                    common_invalid
                    or proposal.get("posture") != "optional"
                    or int(pool.get("specialist_remaining") or 0) != 0
                    or int(pool.get("specialist_spent") or 0) < 1
                )
                availability = AVAILABILITY_BUDGET
            elif nonexecution_reason == "input_reconstruction_failed":
                cancelled = [
                    _safe_mapping(item)
                    for item in scheduler.get("lease_history") or ()
                    if _safe_mapping(item).get("status") == LEASE_CANCELLED
                    and _safe_mapping(item).get("settlement_reason")
                    == "exact_batch_packet_reconstruction_failed"
                    and _safe_mapping(_safe_mapping(item).get("work")).get(
                        "work_id"
                    )
                    == action.inputs.get("work_id")
                    and _safe_mapping(_safe_mapping(item).get("work")).get(
                        "work_digest"
                    )
                    == action.inputs.get("work_digest")
                    and _safe_mapping(
                        _safe_mapping(item).get("work")
                    ).get("specialist_proposal_ref", {}).get("proposal_id")
                    == proposal_id
                ]
                invalid = (
                    common_invalid
                    or proposal.get("posture") not in {"optional", "required"}
                    or len(cancelled) != 1
                )
                availability = AVAILABILITY_FAILED
                if not invalid and proposal.get("posture") == "required":
                    blocked_scheduler = (
                        block_required_specialist_reconstruction_failure(
                            state=self.state,
                            proposal=proposal,
                            work_ref=action.inputs,
                        )
                    )
            else:
                invalid = True
                availability = ""
            if invalid:
                raise RunKernelTransitionError(
                    "Specialist nonexecution disposition lacks exact authority"
                )
            self.state.projections[SPECIALIST_WORK_PLANE_STAGE] = (
                append_specialist_disposition(
                    plane,
                    proposal=proposal,
                    availability_posture=availability,
                    nonexecution_reason=nonexecution_reason,
                )
            )
            if blocked_scheduler:
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    blocked_scheduler
                )
            self.state.projections[action.stage] = deepcopy(
                self.state.projections[SPECIALIST_WORK_PLANE_STAGE][
                    "proposal_dispositions"
                ][-1]
            )
        elif action.action_type is ActionType.SPECIALIST_CAPABILITY_EXECUTE:
            from core.multicomponent_graph_scheduling import (
                LEASE_BLOCKED,
                LEASE_COMPLETED,
                LEASE_CONTESTED,
                LEASE_FAILED,
                LEASE_STALE,
                MULTICOMPONENT_SCHEDULER_STAGE,
                settle_specialist_lease,
            )
            from core.specialist_graph_runtime import (
                EXECUTION_BLOCKED,
                EXECUTION_COMPLETED,
                EXECUTION_CONTESTED,
                EXECUTION_FAILED,
                EXECUTION_STALE,
                SPECIALIST_WORK_PLANE_STAGE,
                append_specialist_result,
                validate_specialist_result_artifact,
                validate_specialist_work_node,
            )

            work_node = validate_specialist_work_node(
                _safe_mapping(action.inputs.get("specialist_work_node"))
            )
            result = validate_specialist_result_artifact(
                _safe_mapping(observation.payload.get("specialist_result_artifact"))
            )
            action_ref = _safe_mapping(result.get("authorization_action_ref"))
            lease_ref = _safe_mapping(result.get("lease_ref"))
            if (
                action_ref.get("action_id") != action.action_id
                or _safe_mapping(result.get("work_ref")).get("node_digest")
                != work_node.get("node_digest")
                or lease_ref.get("lease_id") != action.inputs.get("lease_id")
                or lease_ref.get("lease_digest") != action.inputs.get("lease_digest")
                or result.get("capability_id") != action.inputs.get("capability_id")
                or result.get("capability_version")
                != action.inputs.get("capability_version")
            ):
                raise RunKernelTransitionError(
                    "Specialist result does not match authorized work and lease"
                )
            posture = str(result.get("execution_posture") or "")
            settlements = {
                EXECUTION_COMPLETED: LEASE_COMPLETED,
                EXECUTION_FAILED: LEASE_FAILED,
                EXECUTION_BLOCKED: LEASE_BLOCKED,
                EXECUTION_CONTESTED: LEASE_CONTESTED,
                EXECUTION_STALE: LEASE_STALE,
            }
            if posture not in settlements:
                raise RunKernelTransitionError(
                    "Specialist result names an unsupported execution posture"
                )
            self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                settle_specialist_lease(
                    state=self.state,
                    action_inputs=dict(action.inputs),
                    settlement=settlements[posture],
                )
            )
            self.state.projections[SPECIALIST_WORK_PLANE_STAGE] = (
                append_specialist_result(
                    _safe_mapping(
                        self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE)
                    ),
                    work_node=work_node,
                    result=result,
                )
            )
            self.state.projections[action.stage] = deepcopy(result)
        elif action.action_type is ActionType.SPECIALIST_VALIDATOR_CONSUME:
            from core.component_work_graph_v1 import (
                COMPONENT_WORK_GRAPH_V1_STAGE,
                synthesis_dprime_input_packet,
                validate_component_work_graph_v1,
            )
            from core.multicomponent_component_admission import (
                component_dprime_input_packet,
            )
            from core.multicomponent_role_runtime import (
                ROLE_COMPONENT_ANALYST,
                ROLE_COMPONENT_DPRIME,
                ROLE_SYNTHESIS_DPRIME,
                role_artifact_ref,
                safe_packet_digest,
                validate_multicomponent_role_artifact,
            )
            from core.specialist_graph_runtime import (
                SPECIALIST_WORK_PLANE_STAGE,
                VALIDATOR_PENDING,
                handoff_by_id,
                mark_validator_consumption,
            )

            plane = _safe_mapping(
                self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE)
            )
            handoff_id = str(action.inputs.get("handoff_id") or "")
            handoff = handoff_by_id(plane, handoff_id=handoff_id)
            if (
                not handoff
                or handoff.get("handoff_digest")
                != action.inputs.get("handoff_digest")
                or handoff.get("validator_consumption") != VALIDATOR_PENDING
            ):
                raise RunKernelTransitionError(
                    "Specialist handoff consumption identity is stale or terminal"
                )
            dprime_ref = _safe_mapping(
                action.inputs.get("dprime_artifact_ref")
            )
            dprime_action_id = str(
                _safe_mapping(dprime_ref.get("authorized_action_ref")).get(
                    "action_id"
                )
                or ""
            )
            dprime_action = self.state.issued_actions.get(dprime_action_id)
            target = _safe_mapping(handoff.get("canonical_target_ref"))
            target_kind = str(target.get("target_kind") or "")
            expected_role = {
                "component": ROLE_COMPONENT_DPRIME,
                "synthesis": ROLE_SYNTHESIS_DPRIME,
            }.get(target_kind)
            expected_action_type = {
                "component": ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
                "synthesis": ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE,
            }.get(target_kind)
            if (
                dprime_action is None
                or dprime_action.action_id not in self.state.reduced_action_ids
                or dprime_action.action_type is not expected_action_type
                or dprime_action.inputs.get("role") != expected_role
                or dprime_action.inputs.get("target_kind") != target_kind
            ):
                raise RunKernelTransitionError(
                    "Specialist handoff requires the exact relevant completed D-prime"
                )
            completed = validate_multicomponent_role_artifact(
                _safe_mapping(self.state.projections.get(dprime_action.stage)),
                expected_role=str(expected_role or ""),
            )
            if role_artifact_ref(completed) != dprime_ref:
                raise RunKernelTransitionError(
                    "Specialist handoff D-prime artifact reference is forged or unrelated"
                )
            target_key = str(target.get("target_key") or "")
            node_ref = _safe_mapping(dprime_action.inputs.get("node_ref"))
            if target_kind == "component":
                accepted = _safe_mapping(
                    self.state.current_answer_contract
                    or self.state.initial_answer_contract
                )
                component_ref = next(
                    (
                        _safe_mapping(item)
                        for item in accepted.get(
                            "accepted_answer_component_refs"
                        )
                        or ()
                        if _safe_mapping(item).get("component_id")
                        == target_key
                    ),
                    {},
                )
                analyst = validate_multicomponent_role_artifact(
                    _safe_mapping(
                        self.state.projections.get(
                            f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{target_key}"
                        )
                    ),
                    expected_role=ROLE_COMPONENT_ANALYST,
                )
                analyst_input = _safe_mapping(
                    _safe_mapping(self.state.multicomponent_scheduler_context)
                    .get("component_analyst_input_packets", {})
                    .get(target_key)
                )
                if (
                    dprime_action.inputs.get("component_id") != target_key
                    or component_ref.get("component_revision")
                    != target.get("target_revision")
                    or component_ref.get("component_digest")
                    != target.get("target_digest")
                    or node_ref.get("component_revision")
                    != target.get("target_revision")
                    or node_ref.get("component_digest")
                    != target.get("target_digest")
                ):
                    raise RunKernelTransitionError(
                        "Specialist component handoff target is no longer exact"
                    )
                packet = component_dprime_input_packet(
                    analyst_artifact=analyst,
                    analyst_input_packet=analyst_input,
                    specialist_need_handoff=handoff,
                )
                route = "component_dprime"
            else:
                graph = validate_component_work_graph_v1(
                    _safe_mapping(
                        self.state.projections.get(
                            COMPONENT_WORK_GRAPH_V1_STAGE
                        )
                    )
                )
                synthesis_node = next(
                    (
                        _safe_mapping(item)
                        for item in graph.get("synthesis_nodes") or ()
                        if _safe_mapping(item).get("synthesis_key")
                        == target_key
                    ),
                    {},
                )
                graph_ref = _safe_mapping(
                    dprime_action.inputs.get("graph_ref")
                )
                scrutineer_successor = (
                    handoff.get("origin_role") == "scrutineer"
                )
                target_revision_matches = (
                    int(synthesis_node.get("node_revision") or 0)
                    > int(target.get("target_revision") or 0)
                    and _safe_mapping(
                        synthesis_node.get("specialist_result_ref")
                    )
                    == _safe_mapping(
                        _safe_mapping(handoff.get("result")).get("result_ref")
                    )
                    if scrutineer_successor
                    else synthesis_node.get("node_revision")
                    == target.get("target_revision")
                )
                if (
                    dprime_action.inputs.get("synthesis_key") != target_key
                    or not target_revision_matches
                    or node_ref.get("node_revision")
                    != synthesis_node.get("node_revision")
                    or node_ref.get("node_digest")
                    != synthesis_node.get("node_digest")
                    or graph_ref.get("graph_revision")
                    != graph.get("graph_revision")
                    or graph_ref.get("graph_digest")
                    != graph.get("graph_digest")
                ):
                    raise RunKernelTransitionError(
                        "Specialist synthesis handoff target is no longer exact"
                    )
                packet = synthesis_dprime_input_packet(
                    graph,
                    synthesis_key=target_key,
                    specialist_need_handoff=handoff,
                )
                route = "synthesis_dprime"
            if safe_packet_digest(packet) != dprime_action.inputs.get(
                "input_packet_digest"
            ) or completed.get(
                "input_packet_digest"
            ) != dprime_action.inputs.get("input_packet_digest"):
                raise RunKernelTransitionError(
                    "Specialist handoff was not consumed by the exact reconstructed D-prime input"
                )
            validation_status = str(
                _safe_mapping(completed.get("semantic_output")).get(
                    "validation_status"
                )
                or ""
            )
            self.state.projections[SPECIALIST_WORK_PLANE_STAGE] = (
                mark_validator_consumption(
                    plane,
                    handoff_id=handoff_id,
                    route=route,
                    validation_status=validation_status,
                    dprime_artifact_ref=dprime_ref,
                )
            )
            self.state.projections[action.stage] = {
                "handoff_id": handoff_id,
                "handoff_digest": action.inputs.get("handoff_digest"),
                "route": route,
                "dprime_artifact_ref": deepcopy(dprime_ref),
            }
        elif action.action_type is ActionType.MULTICOMPONENT_SCHEDULER_INITIALIZE:
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
                initialize_scheduler_v2_state,
                initialize_scheduler_v3_state,
            )
            from core.multicomponent_role_runtime import safe_packet_digest
            from core.specialist_graph_runtime import (
                SPECIALIST_WORK_PLANE_STAGE,
                initialize_specialist_work_plane_from_projections,
            )

            context = _safe_mapping(self.state.multicomponent_scheduler_context)
            packets = _safe_mapping(context.get("component_analyst_input_packets"))
            expected_digests = {
                key: safe_packet_digest(_safe_mapping(value))
                for key, value in packets.items()
            }
            directive = str(context.get("requested_synthesis_directive") or "")
            specialist_enabled = context.get("specialist_scheduler_enabled") is True
            registry_projection = _safe_mapping(
                context.get("specialist_registry_projection")
            )
            policy_projection = _safe_mapping(
                context.get("specialist_execution_policy_projection")
            )
            if (
                action.inputs.get("component_input_packet_digests")
                != expected_digests
                or action.inputs.get("requested_synthesis_directive_digest")
                != safe_packet_digest({"requested_synthesis_directive": directive})
                or action.inputs.get("configured_provider_class")
                != context.get("configured_provider_class")
                or action.inputs.get("specialist_scheduler_enabled")
                is not specialist_enabled
                or action.inputs.get("specialist_registry_digest")
                != registry_projection.get("registry_digest")
                or action.inputs.get("specialist_execution_policy_digest")
                != policy_projection.get("execution_policy_digest")
            ):
                raise RunKernelTransitionError(
                    "scheduler initialization action does not bind private canonical context"
                )
            if specialist_enabled:
                self.state.projections[SPECIALIST_WORK_PLANE_STAGE] = (
                    initialize_specialist_work_plane_from_projections(
                        registry_projection=registry_projection,
                        policy_projection=policy_projection,
                    )
                )
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    initialize_scheduler_v3_state(
                        run_id=self.state.run_id,
                        request_id=self.state.request_id,
                        configured_provider=context.get("configured_provider_class"),
                        specialist_work_item_limit=int(
                            policy_projection.get("specialist_work_item_limit") or 0
                        ),
                        specialist_registry_digest=str(
                            registry_projection.get("registry_digest") or ""
                        ),
                        specialist_execution_policy_digest=str(
                            policy_projection.get("execution_policy_digest") or ""
                        ),
                    )
                )
            else:
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    initialize_scheduler_v2_state(
                    run_id=self.state.run_id,
                    request_id=self.state.request_id,
                    configured_provider=context.get("configured_provider_class"),
                    )
                )
        elif action.action_type is ActionType.MULTICOMPONENT_BATCH_GRANT:
            from core.multicomponent_graph_scheduling import (
                LEASE_DENIED_EXHAUSTED,
                MULTICOMPONENT_SCHEDULER_STAGE,
                WORK_KIND_SPECIALIST_CAPABILITY,
                derive_ready_batch_work,
                derive_ready_work,
                grant_next_batch,
            )

            ready = derive_ready_work(self.state)
            batch_work = derive_ready_batch_work(self.state)
            if (
                not ready
                or _safe_mapping(action.inputs.get("expected_first_ready_work"))
                != ready[0]
                or [
                    _safe_mapping(item)
                    for item in action.inputs.get("expected_batch_work") or ()
                ]
                != batch_work
            ):
                raise RunKernelTransitionError(
                    "batch grant action does not name the exact current prefix"
                )
            scheduler, _batch = grant_next_batch(
                state=self.state,
                action_ref={
                    "action_id": action.action_id,
                    "stage": action.stage,
                    "sequence": action.sequence,
                    "observation_type": action.expected_observation_type.value,
                },
            )
            self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = scheduler
            if (
                _batch.get("status") == LEASE_DENIED_EXHAUSTED
                and _safe_mapping(ready[0]).get("work_kind")
                == WORK_KIND_SPECIALIST_CAPABILITY
            ):
                from core.specialist_graph_runtime import (
                    AVAILABILITY_BUDGET,
                    SPECIALIST_WORK_PLANE_STAGE,
                    append_specialist_disposition,
                )

                plane = _safe_mapping(
                    self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE)
                )
                proposal_id = _safe_mapping(
                    _safe_mapping(ready[0]).get("specialist_proposal_ref")
                ).get("proposal_id")
                proposal = next(
                    (
                        _safe_mapping(item)
                        for item in plane.get("proposals") or ()
                        if _safe_mapping(item).get("proposal_id")
                        == proposal_id
                    ),
                    {},
                )
                self.state.projections[SPECIALIST_WORK_PLANE_STAGE] = (
                    append_specialist_disposition(
                        plane,
                        proposal=proposal,
                        availability_posture=AVAILABILITY_BUDGET,
                        nonexecution_reason="specialist_pool_exhausted",
                    )
                )
        elif action.action_type is ActionType.MULTICOMPONENT_BATCH_DISPATCH:
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
                cancel_batch,
                dispatch_batch,
            )

            pending_raw = getattr(
                self, "_pending_multicomponent_batch_dispatch", {}
            )
            pending = dict(pending_raw) if isinstance(pending_raw, Mapping) else {}
            dispatch_action_ref = {
                "action_id": action.action_id,
                "stage": action.stage,
                "sequence": action.sequence,
                "observation_type": action.expected_observation_type.value,
            }
            try:
                descriptor_set = _safe_mapping(pending.get("descriptor_set"))
                private_actions = tuple(pending.get("private_actions") or ())
                packet_digests = tuple(pending.get("packet_digests") or ())
                if (
                    pending.get("dispatch_action_id") != action.action_id
                    or descriptor_set
                    != self.build_multicomponent_private_child_descriptor_set(
                        batch_id=str(action.inputs.get("batch_id") or ""),
                        packet_digests=packet_digests,
                    )
                    or action.inputs.get("descriptor_set_digest")
                    != descriptor_set.get("descriptor_set_digest")
                    or not private_actions
                    or [item.sequence for item in private_actions]
                    != list(
                        range(
                            self.state.next_action_sequence,
                            self.state.next_action_sequence + len(private_actions),
                        )
                    )
                    or any(
                        item.action_id in self.state.issued_actions
                        for item in private_actions
                    )
                ):
                    raise RunKernelTransitionError(
                        "batch dispatch private child set is not exact"
                    )
                child_action_refs = [
                    {
                        "action_id": item.action_id,
                        "stage": item.stage,
                        "sequence": item.sequence,
                        "observation_type": item.expected_observation_type.value,
                        "batch_index": item.inputs.get("batch_index"),
                        "role": item.inputs.get("role"),
                        "logical_evaluation_key": item.inputs.get(
                            "logical_evaluation_key"
                        ),
                        "input_packet_digest": item.inputs.get(
                            "input_packet_digest"
                        ),
                        "lease_id": item.inputs.get("lease_id"),
                        "lease_digest": item.inputs.get("lease_digest"),
                        "work_id": item.inputs.get("work_id"),
                        "work_digest": item.inputs.get("work_digest"),
                    }
                    for item in private_actions
                ]
                candidate_scheduler = dispatch_batch(
                    state=self.state,
                    batch_id=str(action.inputs.get("batch_id") or ""),
                    dispatch_action_ref=dispatch_action_ref,
                    descriptor_set=descriptor_set,
                    child_action_refs=child_action_refs,
                )
            except Exception as exc:
                candidate_scheduler = cancel_batch(
                    state=self.state,
                    batch_id=str(action.inputs.get("batch_id") or ""),
                    action_ref=dispatch_action_ref,
                    reason="batch_dispatch_precommit_validation_failed",
                )
                observation = Observation.from_action(
                    action,
                    observation_type=action.expected_observation_type,
                    status=RunStageStatus.FAILED,
                    payload={
                        "failure_kind": "batch_dispatch_precommit_validation_failed",
                        "child_actions_published": False,
                        "logical_keys_consumed": False,
                        "failure_type": type(exc).__name__,
                    },
                )
                self.state.action_statuses[action.action_id] = RunStageStatus.FAILED
                self.state.stage_statuses[action.stage] = RunStageStatus.FAILED
                self.state.projections[action.stage] = {
                    "schema_version": "multicomponent_batch_dispatch_precommit_failure_v1",
                    "owner": "RunKernel.MulticomponentGraphScheduler",
                    "canonical_state": True,
                    "batch_id": action.inputs.get("batch_id"),
                    "batch_digest": action.inputs.get("batch_digest"),
                    "failure_kind": "batch_dispatch_precommit_validation_failed",
                    "child_actions_published": False,
                    "logical_keys_consumed": False,
                    "raw_private_material_retained": False,
                }
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    candidate_scheduler
                )
            else:
                self.state.issued_actions.update(
                    {item.action_id: item for item in private_actions}
                )
                self.state.action_statuses.update(
                    {
                        item.action_id: RunStageStatus.AUTHORIZED
                        for item in private_actions
                    }
                )
                for item in private_actions:
                    self.state.stage_statuses[item.stage] = RunStageStatus.AUTHORIZED
                self.state.next_action_sequence += len(private_actions)
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    candidate_scheduler
                )
        elif action.action_type is ActionType.MULTICOMPONENT_BATCH_CANCEL:
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
                cancel_batch,
            )

            self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = cancel_batch(
                state=self.state,
                batch_id=str(action.inputs.get("batch_id") or ""),
                action_ref={
                    "action_id": action.action_id,
                    "stage": action.stage,
                    "sequence": action.sequence,
                    "observation_type": action.expected_observation_type.value,
                },
                reason=str(
                    action.inputs.get("cancellation_reason")
                    or "predispatch_batch_cancellation"
                ),
            )
        elif action.action_type is ActionType.MULTICOMPONENT_LEASE_GRANT:
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
                derive_ready_work,
                grant_next_lease,
            )

            ready = derive_ready_work(self.state)
            if (
                not ready
                or _safe_mapping(action.inputs.get("expected_first_ready_work"))
                != ready[0]
            ):
                raise RunKernelTransitionError(
                    "lease grant action does not name the exact first current work"
                )
            scheduler, _lease = grant_next_lease(
                state=self.state,
                action_ref={
                    "action_id": action.action_id,
                    "stage": action.stage,
                    "sequence": action.sequence,
                    "observation_type": action.expected_observation_type.value,
                },
            )
            self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = scheduler
        elif action.action_type is ActionType.MULTICOMPONENT_LEASE_DISPATCH:
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
                dispatch_lease,
            )

            role_action_ref = _safe_mapping(
                observation.payload.get("role_action_ref")
            )
            role_action = self.state.issued_actions.get(
                str(role_action_ref.get("action_id") or "")
            )
            if (
                role_action is None
                or role_action.inputs.get("dispatch_action_ref", {}).get("action_id")
                != action.action_id
            ):
                raise RunKernelTransitionError(
                    "dispatch commitment requires the exact issued role action"
                )
            self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = dispatch_lease(
                state=self.state,
                lease_id=str(action.inputs.get("lease_id") or ""),
                dispatch_action_ref={
                    "action_id": action.action_id,
                    "stage": action.stage,
                    "sequence": action.sequence,
                    "observation_type": action.expected_observation_type.value,
                },
                role_action_ref=role_action_ref,
            )
        elif action.action_type is ActionType.MULTICOMPONENT_LEASE_CANCEL:
            from core.multicomponent_graph_scheduling import (
                MULTICOMPONENT_SCHEDULER_STAGE,
                cancel_lease,
            )

            self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = cancel_lease(
                state=self.state,
                lease_id=str(action.inputs.get("lease_id") or ""),
                reason=str(
                    action.inputs.get("cancellation_reason")
                    or "predispatch_cancellation"
                ),
            )
        elif action.action_type in {
            ActionType.MULTICOMPONENT_COMPONENT_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_COMPONENT_DPRIME_EXECUTE,
            ActionType.MULTICOMPONENT_CROSS_ANALYST_EXECUTE,
            ActionType.MULTICOMPONENT_SYNTHESIS_DPRIME_EXECUTE,
            ActionType.MULTICOMPONENT_SCRUTINEER_EXECUTE,
        }:
            from core.multicomponent_graph_scheduling import (
                LEASE_COMPLETED,
                LEASE_FAILED,
                LEASE_STALE,
                MULTICOMPONENT_SCHEDULER_STAGE,
                settle_role_lease,
            )
            from core.multicomponent_role_runtime import (
                validate_multicomponent_role_artifact,
            )

            scheduler_active = bool(action.inputs.get("lease_id"))
            if observation.status is RunStageStatus.FAILED:
                if not scheduler_active:
                    raise RunKernelTransitionError(
                        "unscheduled semantic role failure cannot claim lease settlement"
                    )
                settlement = str(
                    observation.payload.get("lease_settlement") or LEASE_FAILED
                )
                if settlement not in {LEASE_FAILED, LEASE_STALE}:
                    raise RunKernelTransitionError(
                        "semantic role failure settlement is invalid"
                    )
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    settle_role_lease(
                        state=self.state,
                        action_inputs={
                            **dict(action.inputs),
                            "failure_kind": _clean_text(
                                observation.payload.get("failure_kind"), limit=100
                            ),
                            "transport_submitted": observation.payload.get(
                                "transport_submitted"
                            )
                            is True,
                            "transport_started": observation.payload.get(
                                "transport_started"
                            )
                            is True,
                            "transport_completed": observation.payload.get(
                                "transport_completed"
                            )
                            is True,
                            "provider_request_attempt_count": max(
                                0,
                                min(
                                    1,
                                    int(
                                        observation.payload.get(
                                            "provider_request_attempt_count"
                                        )
                                        or 0
                                    ),
                                ),
                            ),
                            "observed_batch_max_in_flight": int(
                                observation.payload.get(
                                    "observed_batch_max_in_flight"
                                )
                                or 0
                            ),
                        },
                        settlement=settlement,
                    )
                )
                self.state.projections[action.stage] = {
                    "schema_version": "multicomponent_semantic_role_failure_v1",
                    "owner": "RunKernel.MulticomponentGraphScheduler",
                    "canonical_state": True,
                    "role": action.inputs.get("role"),
                    "logical_evaluation_key": action.inputs.get(
                        "logical_evaluation_key"
                    ),
                    "work_id": action.inputs.get("work_id"),
                    "lease_id": action.inputs.get("lease_id"),
                    "settlement": settlement,
                    "failure_kind": _clean_text(
                        observation.payload.get("failure_kind"), limit=100
                    ),
                    "semantic_artifact_admitted": False,
                    "raw_model_response_retained": False,
                    "raw_provider_payload_retained": False,
                }
                artifact = {}
            else:
                artifact = validate_multicomponent_role_artifact(
                    _safe_mapping(observation.payload.get("semantic_role_artifact")),
                    expected_role=str(action.inputs.get("role") or ""),
                )
            if artifact and artifact.get("run_id") != self.state.run_id:
                raise RunKernelTransitionError(
                    "multi-component semantic role cross-run observation"
                )
            if artifact and artifact.get("request_id") != self.state.request_id:
                raise RunKernelTransitionError(
                    "multi-component semantic role request binding mismatch"
                )
            if artifact and artifact.get("input_packet_digest") != action.inputs.get(
                "input_packet_digest"
            ):
                raise RunKernelTransitionError(
                    "multi-component semantic role input binding mismatch"
                )
            if artifact and artifact.get("logical_evaluation_key") != action.inputs.get(
                "logical_evaluation_key"
            ):
                raise RunKernelTransitionError(
                    "multi-component semantic role logical evaluation key mismatch"
                )
            action_ref = _safe_mapping(artifact.get("authorized_action_ref"))
            if artifact and action_ref.get("action_id") != action.action_id:
                raise RunKernelTransitionError(
                    "multi-component semantic role action binding mismatch"
                )
            if artifact and scheduler_active:
                for key in (
                    "batch_id",
                    "batch_digest",
                    "batch_index",
                    "descriptor_digest",
                    "lease_id",
                    "lease_digest",
                    "work_id",
                    "work_digest",
                    "grant_action_ref",
                    "dispatch_action_ref",
                    "accepted_contract_ref",
                    "graph_ref",
                    "target_kind",
                    "component_id",
                    "synthesis_key",
                    "node_ref",
                    "recovery_authorization_ref",
                    "contract_amendment_admission_ref",
                    "contract_amendment_application_ref",
                    "selective_closure_ref",
                    "scheduler_revision_at_grant",
                    "output_schema_variant",
                ):
                    if artifact.get(key) != action.inputs.get(key):
                        raise RunKernelTransitionError(
                            "semantic artifact and lease lineage disagree"
                        )
                self.state.projections[MULTICOMPONENT_SCHEDULER_STAGE] = (
                    settle_role_lease(
                        state=self.state,
                        action_inputs={
                            **dict(action.inputs),
                            "transport_submitted": observation.payload.get(
                                "transport_submitted"
                            )
                            is True,
                            "transport_started": observation.payload.get(
                                "transport_started"
                            )
                            is True,
                            "transport_completed": observation.payload.get(
                                "transport_completed"
                            )
                            is True,
                            "provider_request_attempt_count": max(
                                0,
                                min(
                                    1,
                                    int(
                                        observation.payload.get(
                                            "provider_request_attempt_count"
                                        )
                                        or 0
                                    ),
                                ),
                            ),
                            "observed_batch_max_in_flight": int(
                                observation.payload.get(
                                    "observed_batch_max_in_flight"
                                )
                                or 0
                            ),
                        },
                        settlement=LEASE_COMPLETED,
                    )
                )
            if artifact:
                self.state.projections[action.stage] = deepcopy(artifact)
        elif action.action_type is ActionType.MULTICOMPONENT_COMPONENT_ADMISSION_REDUCE:
            from core.multicomponent_component_admission import (
                MULTICOMPONENT_COMPONENT_ADMISSION_OWNER,
            )
            from core.multicomponent_role_runtime import safe_packet_digest

            aggregate = _safe_mapping(
                observation.payload.get("component_admission_projection")
            )
            component_ref = _safe_mapping(
                observation.payload.get("component_admission_ref")
            )
            accepted_contract = _safe_mapping(
                self.state.current_answer_contract
                or self.state.initial_answer_contract
            )
            accepted_contract_digest = accepted_contract.get(
                "accepted_contract_digest"
            )
            accepted_contract_version = accepted_contract.get(
                "accepted_contract_version"
            )
            if (
                aggregate.get("owner") != MULTICOMPONENT_COMPONENT_ADMISSION_OWNER
                or aggregate.get("canonical_state") is not True
                or aggregate.get("run_id") != self.state.run_id
                or aggregate.get("request_id") != self.state.request_id
                or aggregate.get("accepted_contract_digest")
                != accepted_contract_digest
                or aggregate.get("accepted_contract_version")
                != accepted_contract_version
                or component_ref.get("run_id") != self.state.run_id
                or component_ref.get("request_id") != self.state.request_id
                or component_ref.get("accepted_contract_digest")
                != accepted_contract_digest
                or component_ref.get("accepted_contract_version")
                != accepted_contract_version
                or action.inputs.get("accepted_contract_digest")
                != accepted_contract_digest
            ):
                raise RunKernelTransitionError(
                    "multi-component admission requires canonical RunKernel projection"
                )
            if (
                component_ref.get("component_id") != action.inputs.get("component_id")
                or _safe_mapping(component_ref.get("analyst_finding_ref")).get(
                    "artifact_digest"
                )
                != action.inputs.get("analyst_artifact_digest")
                or _safe_mapping(component_ref.get("dprime_validation_ref")).get(
                    "artifact_digest"
                )
                != action.inputs.get("dprime_artifact_digest")
            ):
                raise RunKernelTransitionError(
                    "multi-component admission role/component binding mismatch"
                )
            from core.multicomponent_role_runtime import (
                ROLE_COMPONENT_ANALYST,
                ROLE_COMPONENT_DPRIME,
                role_artifact_ref,
                validate_multicomponent_role_artifact,
            )

            component_id = str(component_ref.get("component_id") or "")
            completed_analyst = _safe_mapping(
                self.state.projections.get(
                    f"multicomponent_role:{ROLE_COMPONENT_ANALYST}:{component_id}"
                )
            )
            completed_dprime = _safe_mapping(
                self.state.projections.get(
                    f"multicomponent_role:{ROLE_COMPONENT_DPRIME}:{component_id}"
                )
            )
            try:
                completed_analyst = validate_multicomponent_role_artifact(
                    completed_analyst,
                    expected_role=ROLE_COMPONENT_ANALYST,
                )
                completed_dprime = validate_multicomponent_role_artifact(
                    completed_dprime,
                    expected_role=ROLE_COMPONENT_DPRIME,
                )
            except Exception as exc:
                raise RunKernelTransitionError(
                    "multi-component admission requires completed RunKernel role artifacts"
                ) from exc
            if (
                completed_analyst.get("logical_evaluation_key") != component_id
                or completed_dprime.get("logical_evaluation_key") != component_id
                or role_artifact_ref(completed_analyst)
                != _safe_mapping(component_ref.get("analyst_finding_ref"))
                or role_artifact_ref(completed_dprime)
                != _safe_mapping(component_ref.get("dprime_validation_ref"))
                or completed_analyst.get("artifact_digest")
                != action.inputs.get("analyst_artifact_digest")
                or completed_dprime.get("artifact_digest")
                != action.inputs.get("dprime_artifact_digest")
            ):
                raise RunKernelTransitionError(
                    "multi-component admission role provenance does not match completed history"
                )
            admitted_claim = _safe_mapping(component_ref.get("admitted_claim_ref"))
            if component_ref.get("admission_status") in {
                "admitted",
                "admitted_with_caveats",
            }:
                nominated_claim = _safe_mapping(
                    completed_analyst.get("semantic_output")
                ).get("claim_text")
                if (
                    not nominated_claim
                    or admitted_claim.get("claim_text") != nominated_claim
                ):
                    raise RunKernelTransitionError(
                        "multi-component admission claim must equal Analyst-nominated claim"
                    )
            refs = [
                _safe_mapping(item)
                for item in aggregate.get("component_admission_refs") or ()
            ]
            prior_aggregate = _safe_mapping(self.state.projections.get(action.stage))
            prior_refs = [
                _safe_mapping(item)
                for item in prior_aggregate.get("component_admission_refs") or ()
            ]
            aggregate_core = dict(aggregate)
            declared_projection_digest = aggregate_core.pop(
                "projection_digest",
                None,
            )
            if (
                component_ref.get("owner")
                != MULTICOMPONENT_COMPONENT_ADMISSION_OWNER
                or component_ref.get("canonical_state") is not True
                or component_ref.get("action_id") != action.action_id
                or aggregate.get("latest_action_id") != action.action_id
                or refs[:-1] != prior_refs
                or not refs
                or refs[-1] != component_ref
                or int(aggregate.get("component_count") or 0) != len(refs)
                or declared_projection_digest != safe_packet_digest(aggregate_core)
            ):
                raise RunKernelTransitionError(
                    "multi-component admission aggregate/action is not canonical append-only state"
                )
            admission_state = _safe_mapping(
                observation.payload.get("semantic_observation_admission_state")
            )
            admission_projection = _safe_mapping(
                observation.payload.get("semantic_observation_admission_projection")
            )
            coverage_state = _safe_mapping(
                observation.payload.get("component_coverage_state")
            )
            coverage_projection = _safe_mapping(
                observation.payload.get("component_coverage_projection")
            )
            admitted = component_ref.get("admission_status") in {
                "admitted",
                "admitted_with_caveats",
            }
            if admitted and not all(
                (admission_state, admission_projection, coverage_state, coverage_projection)
            ):
                raise RunKernelTransitionError(
                    "admitted multi-component state requires semantic and coverage reductions"
                )
            if not admitted and any(
                (admission_state, admission_projection, coverage_state, coverage_projection)
            ):
                raise RunKernelTransitionError(
                    "blocked multi-component state cannot manufacture canonical semantics"
                )
            if admitted:
                if (
                    admission_projection.get("answer_component_id")
                    != component_ref.get("component_id")
                    or coverage_projection.get("answer_component_id")
                    != component_ref.get("component_id")
                ):
                    raise RunKernelTransitionError(
                        "multi-component semantic/coverage component mismatch"
                    )
                self.state.semantic_observation_admission_state = admission_state
                self.state.semantic_observation_admission_projection = (
                    admission_projection
                )
                self.state.semantic_observation_admission_history.append(
                    deepcopy(admission_projection)
                )
                self.state.component_coverage_state = coverage_state
                self.state.component_coverage_projection = coverage_projection
                self.state.component_coverage_history.append(
                    deepcopy(coverage_projection)
                )
                self.state.projections[SEMANTIC_OBSERVATION_ADMISSION_STAGE] = (
                    deepcopy(admission_projection)
                )
                self.state.projections[COMPONENT_COVERAGE_REDUCTION_STAGE] = (
                    deepcopy(coverage_projection)
                )
            self.state.projections[action.stage] = deepcopy(aggregate)
        elif action.action_type is ActionType.MULTICOMPONENT_GRAPH_REDUCE:
            from core.component_work_graph_v1 import (
                COMPONENT_WORK_GRAPH_V1_OWNER,
                COMPONENT_WORK_GRAPH_V1_STAGE,
                MULTICOMPONENT_CARRY_FORWARD_STAGE,
                MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE,
                build_synthesis_carry_forward_projection,
                component_work_graph_v1_from_cross_component_artifact,
                component_work_graph_v1_resynthesis_from_cross_component_artifact,
                component_work_graph_v1_selective_resynthesis_from_cross_artifact,
                derive_multicomponent_role_call_accounting,
                derive_selective_recomputation_closure,
                expected_graph_after_transition,
                graph_with_recovered_component,
                graph_with_selective_invalidation,
                validate_component_work_graph_v1,
                validate_selective_recomputation_closure,
            )
            from core.component_work_node import (
                component_work_node_v1_from_admitted_component,
            )
            from core.multicomponent_component_admission import (
                MULTICOMPONENT_COMPONENT_ADMISSION_OWNER,
                MULTICOMPONENT_COMPONENT_ADMISSION_STAGE,
            )
            from core.multicomponent_role_runtime import (
                ROLE_CROSS_COMPONENT_ANALYST,
                ROLE_SCRUTINEER,
                ROLE_SYNTHESIS_DPRIME,
                role_artifact_ref,
                safe_packet_digest,
            )

            def current_component_packets_for_graph_reproof(
                *,
                component_nodes: Sequence[Mapping[str, Any]],
                requested_synthesis_directive: str,
            ) -> dict[str, Any]:
                raw_context = self.state.multicomponent_scheduler_context
                if not isinstance(raw_context, Mapping):
                    raise RunKernelTransitionError(
                        "Graph V1 structure reproof requires current component Analyst packets"
                    )
                context = _safe_mapping(raw_context)
                raw_packets = raw_context.get("component_analyst_input_packets")
                packets = _safe_mapping(
                    raw_packets if isinstance(raw_packets, Mapping) else None
                )
                component_ids = {
                    str(_safe_mapping(item).get("component_id") or "")
                    for item in component_nodes
                }
                if (
                    not packets
                    or not component_ids
                    or set(packets) != component_ids
                    or any(
                        not isinstance(value, Mapping)
                        for value in (
                            raw_packets.values()
                            if isinstance(raw_packets, Mapping)
                            else ()
                        )
                    )
                    or _clean_text(
                        context.get("requested_synthesis_directive"), limit=360
                    )
                    != _clean_text(requested_synthesis_directive, limit=360)
                ):
                    raise RunKernelTransitionError(
                        "Graph V1 structure reproof requires current component Analyst packets"
                    )
                scheduler = _safe_mapping(
                    self.state.projections.get("multicomponent_graph_scheduler")
                )
                if scheduler:
                    expected_packet_digests: dict[str, Any] = {}
                    recovery_transitions = [
                        _safe_mapping(item)
                        for item in scheduler.get("transition_history") or ()
                        if _safe_mapping(item).get("transition")
                        == "recovery_scheduler_context_registered"
                    ]
                    if recovery_transitions:
                        expected_packet_digests = _safe_mapping(
                            _safe_mapping(recovery_transitions[-1]).get(
                                "authority_ref"
                            )
                        ).get("component_input_packet_digests", {})
                    else:
                        initialization_actions = [
                            issued
                            for issued in self.state.issued_actions.values()
                            if issued.action_type
                            is ActionType.MULTICOMPONENT_SCHEDULER_INITIALIZE
                        ]
                        if len(initialization_actions) == 1:
                            expected_packet_digests = _safe_mapping(
                                initialization_actions[0].inputs
                            ).get("component_input_packet_digests", {})
                    current_packet_digests = {
                        str(key): safe_packet_digest(_safe_mapping(value))
                        for key, value in packets.items()
                    }
                    if (
                        not isinstance(expected_packet_digests, Mapping)
                        or current_packet_digests
                        != dict(expected_packet_digests)
                    ):
                        raise RunKernelTransitionError(
                            "Graph V1 structure reproof component packets do not match scheduler authority"
                        )
                return deepcopy(packets)

            operation = action.inputs.get("operation")
            if operation == "selective_closure":
                candidate = validate_selective_recomputation_closure(
                    _safe_mapping(
                        observation.payload.get("selective_recomputation_closure")
                    )
                )
                source_graph = validate_component_work_graph_v1(
                    _safe_mapping(
                        self.state.projections.get(COMPONENT_WORK_GRAPH_V1_STAGE)
                    )
                )
                authorization = _safe_mapping(
                    self.state.projections.get(
                        MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
                    )
                )
                contract = _safe_mapping(self.state.current_answer_contract)
                amendment_admission = _safe_mapping(
                    self.state.contract_amendment_admission_projection
                )
                amendment_application = _safe_mapping(
                    self.state.contract_amendment_application_projection
                )
                component_projection = _safe_mapping(
                    self.state.projections.get(
                        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
                    )
                )
                expected_refs = {
                    "source_graph_ref": {
                        "graph_id": source_graph.get("graph_id"),
                        "graph_revision": source_graph.get("graph_revision"),
                        "graph_digest": source_graph.get("graph_digest"),
                    },
                    "recovery_authorization_ref": {
                        "authorization_id": authorization.get("authorization_id"),
                        "authorization_digest": authorization.get(
                            "authorization_digest"
                        ),
                    },
                    "current_contract_ref": action.inputs.get(
                        "current_contract_ref"
                    ),
                    "contract_amendment_admission_ref": action.inputs.get(
                        "contract_amendment_admission_ref"
                    ),
                    "contract_amendment_application_ref": action.inputs.get(
                        "contract_amendment_application_ref"
                    ),
                    "recovered_component_admission_ref": action.inputs.get(
                        "recovered_component_admission_ref"
                    ),
                }
                if (
                    expected_refs["source_graph_ref"]
                    != _safe_mapping(action.inputs.get("source_graph_ref"))
                    or action.inputs.get("run_id") != self.state.run_id
                    or action.inputs.get("request_id") != self.state.request_id
                    or expected_refs["current_contract_ref"]
                    != {
                        "owner": contract.get("owner"),
                        "canonical_state": contract.get("canonical_state"),
                        "run_id": self.state.run_id,
                        "request_id": self.state.request_id,
                        "accepted_contract_version": contract.get(
                            "accepted_contract_version"
                        ),
                        "accepted_contract_digest": contract.get(
                            "accepted_contract_digest"
                        ),
                        "parent_question_meaning_record_id": contract.get(
                            "parent_question_meaning_record_id"
                        ),
                        "parent_question_meaning_record_digest": contract.get(
                            "parent_question_meaning_record_digest"
                        ),
                        "accepted_answer_component_count": contract.get(
                            "accepted_answer_component_count"
                        )
                        or len(contract.get("accepted_answer_component_refs", [])),
                    }
                    or expected_refs["contract_amendment_admission_ref"]
                    != {
                        "amendment_record_id": amendment_admission.get(
                            "amendment_record_id"
                        ),
                        "amendment_record_digest": amendment_admission.get(
                            "amendment_record_digest"
                        ),
                        "authorized_action_id": amendment_admission.get(
                            "authorized_action_id"
                        ),
                        "admission_digest": amendment_admission.get(
                            "admission_digest"
                        ),
                    }
                    or expected_refs["contract_amendment_application_ref"]
                    != {
                        "amendment_record_id": amendment_application.get(
                            "amendment_record_id"
                        ),
                        "authorized_action_id": amendment_application.get(
                            "authorized_action_id"
                        ),
                        "application_digest": amendment_application.get(
                            "application_digest"
                        ),
                    }
                    or expected_refs["recovered_component_admission_ref"]
                    not in [
                        _safe_mapping(item)
                        for item in component_projection.get(
                            "component_admission_refs", ()
                        )
                        if isinstance(item, Mapping)
                    ]
                ):
                    raise RunKernelTransitionError(
                        "selective closure action authority became stale"
                    )
                expected = derive_selective_recomputation_closure(
                    source_graph,
                    recovery_authorization_ref=authorization,
                    current_contract_ref=_safe_mapping(
                        expected_refs["current_contract_ref"]
                    ),
                    contract_amendment_admission_ref=_safe_mapping(
                        expected_refs["contract_amendment_admission_ref"]
                    ),
                    contract_amendment_application_ref=_safe_mapping(
                        expected_refs["contract_amendment_application_ref"]
                    ),
                    recovered_component_admission_ref=_safe_mapping(
                        expected_refs["recovered_component_admission_ref"]
                    ),
                )
                if candidate != expected:
                    raise RunKernelTransitionError(
                        "selective closure candidate does not equal RunKernel derivation"
                    )
                scheduler = self._scheduler_after_canonical_authority_transition(
                    transition="selective_closure_installed",
                    projection_update=(action.stage, expected),
                )
                self._commit_multicomponent_authority_supersession(
                    pending=authority_supersession,
                    scheduler=scheduler,
                )
                self._commit_deferred_authority_action(
                    action=action,
                    observation=observation,
                    pending=authority_supersession,
                )
                self.state.projections[action.stage] = deepcopy(expected)
                if scheduler is not None:
                    self.state.projections[
                        "multicomponent_graph_scheduler"
                    ] = scheduler
                self.state.projections[f"{action.stage}_history"] = {
                    "schema_version": (
                        "multicomponent_selective_recomputation_closure_history_v1"
                    ),
                    "owner": expected["owner"],
                    "canonical_state": True,
                    "closure_count": 1,
                    "closures": [deepcopy(expected)],
                }
                self.state.observations.append(observation)
                self.state.next_observation_sequence += 1
                return self.state

            graph = validate_component_work_graph_v1(
                _safe_mapping(observation.payload.get("component_work_graph_v1"))
            )
            if (
                graph.get("owner") != COMPONENT_WORK_GRAPH_V1_OWNER
                or graph.get("canonical_state") is not True
                or graph.get("run_id") != self.state.run_id
            ):
                raise RunKernelTransitionError(
                    "Graph V1 reduction requires canonical RunKernel-owned state"
                )
            action_ref = _safe_mapping(graph.get("runkernel_graph_action_ref"))
            if action_ref.get("action_id") != action.action_id:
                raise RunKernelTransitionError("Graph V1 action binding mismatch")
            current_graph = _safe_mapping(self.state.projections.get(action.stage))
            synthesis_key = action.inputs.get("synthesis_key")
            role_evaluation_key = action.inputs.get("role_evaluation_key")
            role_artifact = None
            logical_accounting = None
            physical_call_accounting = None
            structure_graph = None
            transition_graph = None
            specialist_need_handoff = None
            specialist_result_artifact = None
            if operation == "structure":
                if current_graph or int(graph.get("graph_revision") or 0) != 1:
                    raise RunKernelTransitionError(
                        "Graph V1 structure must create revision one exactly once"
                    )
                component_admission = _safe_mapping(
                    self.state.projections.get(
                        MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
                    )
                )
                accepted_contract = _safe_mapping(
                    self.state.initial_answer_contract
                )
                contract_ref = _safe_mapping(graph.get("accepted_contract_ref"))
                expected_contract_fields = {
                    "owner": accepted_contract.get("owner"),
                    "canonical_state": accepted_contract.get("canonical_state"),
                    "run_id": self.state.run_id,
                    "request_id": self.state.request_id,
                    "accepted_contract_version": accepted_contract.get(
                        "accepted_contract_version"
                    ),
                    "accepted_contract_digest": accepted_contract.get(
                        "accepted_contract_digest"
                    ),
                }
                current_cross_artifact = _safe_mapping(
                    self.state.projections.get(
                        f"multicomponent_role:{ROLE_CROSS_COMPONENT_ANALYST}:graph-v1"
                    )
                )
                expected_cross_ref = (
                    role_artifact_ref(current_cross_artifact)
                    if current_cross_artifact
                    else {}
                )
                accepted_components = {
                    _safe_mapping(item).get("component_id"): _safe_mapping(item)
                    for item in self.state.initial_answer_contract.get(
                        "accepted_answer_component_refs",
                        [],
                    )
                }
                admission_refs = [
                    _safe_mapping(item)
                    for item in component_admission.get(
                        "component_admission_refs",
                        [],
                    )
                ]
                admission_by_component = {
                    item.get("component_id"): item for item in admission_refs
                }
                try:
                    expected_component_nodes = [
                        component_work_node_v1_from_admitted_component(
                            run_id=self.state.run_id,
                            request_id=self.state.request_id,
                            accepted_component_ref=accepted_component,
                            component_admission_ref=admission_by_component[
                                component_id
                            ],
                        )
                        for component_id, accepted_component in accepted_components.items()
                    ]
                    if not expected_component_nodes:
                        raise RunKernelTransitionError(
                            "Graph V1 structure must exactly consume current RunKernel component admission"
                        )
                    component_packets = current_component_packets_for_graph_reproof(
                        component_nodes=expected_component_nodes,
                        requested_synthesis_directive=str(
                            graph.get("requested_synthesis_directive") or ""
                        ),
                    )
                    structure_graph = (
                        component_work_graph_v1_from_cross_component_artifact(
                            run_id=self.state.run_id,
                            request_id=self.state.request_id,
                            accepted_contract_ref=contract_ref,
                            requested_synthesis_directive=str(
                                graph.get("requested_synthesis_directive") or ""
                            ),
                            component_nodes=expected_component_nodes,
                            cross_component_artifact=current_cross_artifact,
                            component_analyst_input_packets=component_packets,
                            additional_scrutineer_trigger_reasons=tuple(
                                reason
                                for reason in graph.get("scrutineer_trigger_reasons")
                                or ()
                                if reason
                                in {
                                    "deep_mode",
                                    "high_stakes_quantitative_posture",
                                }
                            ),
                        )
                    )
                except RunKernelTransitionError:
                    raise
                except (KeyError, ValueError) as exc:
                    raise RunKernelTransitionError(
                        "Graph V1 structure must exactly consume current RunKernel component admission"
                    ) from exc
                if (
                    component_admission.get("owner")
                    != MULTICOMPONENT_COMPONENT_ADMISSION_OWNER
                    or component_admission.get("canonical_state") is not True
                    or component_admission.get("run_id") != self.state.run_id
                    or component_admission.get("request_id")
                    != self.state.request_id
                    or component_admission.get("accepted_contract_digest")
                    != accepted_contract.get("accepted_contract_digest")
                    or component_admission.get("accepted_contract_version")
                    != accepted_contract.get("accepted_contract_version")
                    or any(
                        contract_ref.get(key) != value
                        for key, value in expected_contract_fields.items()
                    )
                    or not expected_cross_ref
                    or any(
                        _safe_mapping(node.get("proposal_ref")).get(
                            "cross_component_analyst_ref"
                        )
                        != expected_cross_ref
                        for node in graph.get("synthesis_nodes") or ()
                    )
                    or expected_component_nodes != graph.get("component_nodes")
                ):
                    raise RunKernelTransitionError(
                        "Graph V1 structure must exactly consume current RunKernel component admission"
                    )
            else:
                if (
                    not current_graph
                    or graph.get("previous_graph_digest")
                    != current_graph.get("graph_digest")
                    or int(graph.get("graph_revision") or 0)
                    != int(current_graph.get("graph_revision") or 0) + 1
                    or graph.get("graph_id") != current_graph.get("graph_id")
                ):
                    raise RunKernelTransitionError(
                        "Graph V1 reducer received a stale or non-sequential transition"
                    )
                if operation == "synthesis_validation":
                    role_artifact = _safe_mapping(
                        self.state.projections.get(
                            "multicomponent_role:"
                            f"{ROLE_SYNTHESIS_DPRIME}:"
                            f"{role_evaluation_key or synthesis_key}"
                        )
                    )
                    if not role_artifact:
                        raise RunKernelTransitionError(
                            "Graph V1 synthesis validation lacks completed D-prime artifact"
                        )
                    from core.specialist_graph_runtime import (
                        SPECIALIST_WORK_PLANE_STAGE,
                        handoff_for_target,
                    )

                    specialist_plane = self.state.projections.get(
                        SPECIALIST_WORK_PLANE_STAGE
                    )
                    if specialist_plane:
                        specialist_need_handoff = (
                            handoff_for_target(
                                specialist_plane,
                                target_kind="synthesis",
                                target_key=str(synthesis_key or ""),
                                include_consumed=True,
                            )
                            or None
                        )
                elif operation == "scrutiny":
                    role_artifact = _safe_mapping(
                        self.state.projections.get(
                            "multicomponent_role:"
                            f"{ROLE_SCRUTINEER}:"
                            f"{role_evaluation_key or 'full-case'}"
                        )
                    )
                    if not role_artifact:
                        raise RunKernelTransitionError(
                            "Graph V1 scrutiny lacks completed Scrutineer artifact"
                        )
                elif operation == "specialist_remediation":
                    from core.component_work_graph_v1 import (
                        graph_with_specialist_leaf_remediation,
                    )
                    from core.specialist_graph_runtime import (
                        SPECIALIST_WORK_PLANE_STAGE,
                        result_for_target,
                    )

                    specialist_result = result_for_target(
                        self.state.projections.get(SPECIALIST_WORK_PLANE_STAGE, {}),
                        target_kind="synthesis",
                        target_key=str(synthesis_key or ""),
                    )
                    if (
                        not specialist_result
                        or _safe_mapping(specialist_result.get("graph_ref")).get(
                            "graph_digest"
                        )
                        != current_graph.get("graph_digest")
                    ):
                        raise RunKernelTransitionError(
                            "Specialist remediation lacks an exact current result"
                        )
                    transition_graph = graph_with_specialist_leaf_remediation(
                        current_graph,
                        specialist_result_artifact=specialist_result,
                    )
                elif operation == "accounting":
                    try:
                        logical_accounting, physical_call_accounting = (
                            derive_multicomponent_role_call_accounting(
                                self.state.projections,
                                issued_actions=self.state.issued_actions,
                            )
                        )
                    except ValueError as exc:
                        raise RunKernelTransitionError(str(exc)) from exc
                elif operation == "selective_invalidation":
                    closure = validate_selective_recomputation_closure(
                        _safe_mapping(
                            self.state.projections.get(
                                MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE
                            )
                        )
                    )
                    if (
                        action.inputs.get("closure_id") != closure.get("closure_id")
                        or action.inputs.get("closure_digest")
                        != closure.get("closure_digest")
                        or _safe_mapping(closure.get("source_graph_ref"))
                        != {
                            "graph_id": current_graph.get("graph_id"),
                            "graph_revision": current_graph.get("graph_revision"),
                            "graph_digest": current_graph.get("graph_digest"),
                        }
                    ):
                        raise RunKernelTransitionError(
                            "selective invalidation closure binding became stale"
                        )
                    accepted_contract = _safe_mapping(
                        self.state.current_answer_contract
                    )
                    current_component_ids = {
                        item.get("component_id")
                        for item in current_graph.get("component_nodes") or ()
                        if isinstance(item, Mapping)
                    }
                    added_components = [
                        _safe_mapping(item)
                        for item in accepted_contract.get(
                            "accepted_answer_component_refs", []
                        )
                        if isinstance(item, Mapping)
                        and item.get("component_id") not in current_component_ids
                    ]
                    component_admission = _safe_mapping(
                        self.state.projections.get(
                            MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
                        )
                    )
                    expected_admission_ref = _safe_mapping(
                        closure.get("recovered_component_admission_ref")
                    )
                    matching_admissions = [
                        _safe_mapping(item)
                        for item in component_admission.get(
                            "component_admission_refs", []
                        )
                        if isinstance(item, Mapping)
                        and _safe_mapping(item) == expected_admission_ref
                    ]
                    if len(added_components) != 1 or len(matching_admissions) != 1:
                        raise RunKernelTransitionError(
                            "selective invalidation requires the exact recovered component"
                        )
                    recovered_node = component_work_node_v1_from_admitted_component(
                        run_id=self.state.run_id,
                        request_id=self.state.request_id,
                        accepted_component_ref=added_components[0],
                        component_admission_ref=matching_admissions[0],
                    )
                    contract_ref = {
                        "owner": accepted_contract.get("owner"),
                        "canonical_state": accepted_contract.get("canonical_state"),
                        "run_id": self.state.run_id,
                        "request_id": self.state.request_id,
                        "accepted_contract_version": accepted_contract.get(
                            "accepted_contract_version"
                        ),
                        "accepted_contract_digest": accepted_contract.get(
                            "accepted_contract_digest"
                        ),
                        "parent_question_meaning_record_id": accepted_contract.get(
                            "parent_question_meaning_record_id"
                        ),
                        "parent_question_meaning_record_digest": accepted_contract.get(
                            "parent_question_meaning_record_digest"
                        ),
                        "accepted_answer_component_count": accepted_contract.get(
                            "accepted_answer_component_count"
                        )
                        or len(
                            accepted_contract.get(
                                "accepted_answer_component_refs", []
                            )
                        ),
                    }
                    recovery_ref = _safe_mapping(
                        self.state.projections.get(
                            MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
                        )
                    )
                    application_ref = _safe_mapping(
                        closure.get("contract_amendment_application_ref")
                    )
                    amendment_admission_ref = _safe_mapping(
                        closure.get("contract_amendment_admission_ref")
                    )
                    transition_graph = graph_with_selective_invalidation(
                        current_graph,
                        closure=closure,
                        recovered_component_node=recovered_node,
                        current_contract_ref=contract_ref,
                        recovery_authorization_ref=recovery_ref,
                        contract_amendment_admission_ref=amendment_admission_ref,
                        amendment_application_ref=application_ref,
                        carry_forward_action_ref=action_ref,
                    )
                elif operation == "graph_amendment":
                    accepted_contract = _safe_mapping(
                        self.state.current_answer_contract
                    )
                    if not accepted_contract:
                        raise RunKernelTransitionError(
                            "Graph V1 amendment requires current AnswerContract"
                        )
                    current_component_ids = {
                        item.get("component_id")
                        for item in current_graph.get("component_nodes") or ()
                        if isinstance(item, Mapping)
                    }
                    added_components = [
                        _safe_mapping(item)
                        for item in accepted_contract.get(
                            "accepted_answer_component_refs", []
                        )
                        if isinstance(item, Mapping)
                        and item.get("component_id") not in current_component_ids
                    ]
                    component_admission = _safe_mapping(
                        self.state.projections.get(
                            MULTICOMPONENT_COMPONENT_ADMISSION_STAGE
                        )
                    )
                    if len(added_components) != 1:
                        raise RunKernelTransitionError(
                            "Graph V1 amendment requires exactly one added component"
                        )
                    added_component = added_components[0]
                    matching_admissions = [
                        _safe_mapping(item)
                        for item in component_admission.get(
                            "component_admission_refs", []
                        )
                        if isinstance(item, Mapping)
                        and item.get("component_id")
                        == added_component.get("component_id")
                        and item.get("accepted_contract_digest")
                        == accepted_contract.get("accepted_contract_digest")
                    ]
                    if len(matching_admissions) != 1:
                        raise RunKernelTransitionError(
                            "Graph V1 amendment requires exact recovered component admission"
                        )
                    recovered_node = component_work_node_v1_from_admitted_component(
                        run_id=self.state.run_id,
                        request_id=self.state.request_id,
                        accepted_component_ref=added_component,
                        component_admission_ref=matching_admissions[0],
                    )
                    contract_ref = {
                        "owner": accepted_contract.get("owner"),
                        "canonical_state": accepted_contract.get("canonical_state"),
                        "run_id": self.state.run_id,
                        "request_id": self.state.request_id,
                        "accepted_contract_version": accepted_contract.get(
                            "accepted_contract_version"
                        ),
                        "accepted_contract_digest": accepted_contract.get(
                            "accepted_contract_digest"
                        ),
                        "parent_question_meaning_record_id": accepted_contract.get(
                            "parent_question_meaning_record_id"
                        ),
                        "parent_question_meaning_record_digest": accepted_contract.get(
                            "parent_question_meaning_record_digest"
                        ),
                        "accepted_answer_component_count": accepted_contract.get(
                            "accepted_answer_component_count"
                        )
                        or len(
                            accepted_contract.get(
                                "accepted_answer_component_refs", []
                            )
                        ),
                    }
                    recovery_ref = _safe_mapping(
                        self.state.projections.get(
                            MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE
                        )
                    )
                    application = _safe_mapping(
                        self.state.contract_amendment_application_projection
                    )
                    application_ref = {
                        "owner": application.get("owner"),
                        "application_digest": application.get(
                            "application_digest"
                        ),
                        "authorized_action_id": application.get(
                            "authorized_action_id"
                        ),
                        "amendment_record_id": application.get(
                            "amendment_record_id"
                        ),
                    }
                    transition_graph = graph_with_recovered_component(
                        current_graph,
                        recovered_component_node=recovered_node,
                        current_contract_ref=contract_ref,
                        recovery_authorization_ref=recovery_ref,
                        amendment_application_ref=application_ref,
                    )
                elif operation == "resynthesis_structure":
                    evaluation_key = _clean_text(
                        role_evaluation_key, limit=180
                    )
                    if not evaluation_key:
                        raise RunKernelTransitionError(
                            "Graph V1 resynthesis requires revision-specific role key"
                        )
                    role_artifact = _safe_mapping(
                        self.state.projections.get(
                            "multicomponent_role:"
                            f"{ROLE_CROSS_COMPONENT_ANALYST}:{evaluation_key}"
                        )
                    )
                    if not role_artifact:
                        raise RunKernelTransitionError(
                            "Graph V1 resynthesis lacks completed Cross-Component Analyst"
                        )
                    try:
                        component_packets = (
                            current_component_packets_for_graph_reproof(
                                component_nodes=current_graph.get(
                                    "component_nodes", []
                                ),
                                requested_synthesis_directive=str(
                                    current_graph.get(
                                        "requested_synthesis_directive"
                                    )
                                    or ""
                                ),
                            )
                        )
                        transition_graph = component_work_graph_v1_resynthesis_from_cross_component_artifact(
                            current_graph,
                            accepted_contract_ref=_safe_mapping(
                                current_graph.get("accepted_contract_ref")
                            ),
                            cross_component_artifact=role_artifact,
                            component_analyst_input_packets=component_packets,
                        )
                    except RunKernelTransitionError:
                        raise
                    except ValueError as exc:
                        raise RunKernelTransitionError(
                            "Graph V1 resynthesis requires exact current Cross input"
                        ) from exc
                elif operation == "selective_resynthesis_structure":
                    evaluation_key = _clean_text(role_evaluation_key, limit=180)
                    closure = validate_selective_recomputation_closure(
                        _safe_mapping(
                            self.state.projections.get(
                                MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE
                            )
                        )
                    )
                    if (
                        not evaluation_key
                        or action.inputs.get("closure_id")
                        != closure.get("closure_id")
                        or action.inputs.get("closure_digest")
                        != closure.get("closure_digest")
                    ):
                        raise RunKernelTransitionError(
                            "selective resynthesis action lacks exact closure binding"
                        )
                    role_artifact = _safe_mapping(
                        self.state.projections.get(
                            "multicomponent_role:"
                            f"{ROLE_CROSS_COMPONENT_ANALYST}:{evaluation_key}"
                        )
                    )
                    if not role_artifact:
                        raise RunKernelTransitionError(
                            "selective resynthesis lacks completed selective Cross artifact"
                        )
                    transition_graph = (
                        component_work_graph_v1_selective_resynthesis_from_cross_artifact(
                            current_graph,
                            closure=closure,
                            cross_component_artifact=role_artifact,
                        )
                    )
            try:
                expected_graph = expected_graph_after_transition(
                    current_graph or None,
                    operation=str(operation or ""),
                    action_ref=action_ref,
                    synthesis_key=synthesis_key,
                    role_artifact=role_artifact,
                    logical_accounting=logical_accounting,
                    physical_call_accounting=physical_call_accounting,
                    structure_graph=structure_graph,
                    transition_graph=transition_graph,
                    specialist_need_handoff=specialist_need_handoff,
                    specialist_result_artifact=specialist_result_artifact,
                )
            except ValueError as exc:
                raise RunKernelTransitionError(
                    f"Graph V1 could not rederive exact {operation} transition"
                ) from exc
            if expected_graph != graph:
                raise RunKernelTransitionError(
                    "Graph V1 candidate does not equal the exact rederived transition"
                )
            scheduler = self._scheduler_after_canonical_authority_transition(
                transition="component_work_graph_reduced",
                projection_update=(action.stage, graph),
            )
            self._commit_multicomponent_authority_supersession(
                pending=authority_supersession,
                scheduler=scheduler,
            )
            self._commit_deferred_authority_action(
                action=action,
                observation=observation,
                pending=authority_supersession,
            )
            self.state.projections[action.stage] = deepcopy(graph)
            if scheduler is not None:
                self.state.projections["multicomponent_graph_scheduler"] = scheduler
            if operation == "selective_invalidation":
                carry_projection = build_synthesis_carry_forward_projection(
                    prior_graph=current_graph,
                    final_graph=graph,
                    closure=closure,
                    carry_forward_action_ref=action_ref,
                )
                self.state.projections[MULTICOMPONENT_CARRY_FORWARD_STAGE] = (
                    deepcopy(carry_projection)
                )
                self.state.projections[
                    f"{MULTICOMPONENT_CARRY_FORWARD_STAGE}_history"
                ] = {
                    "schema_version": (
                        "multicomponent_synthesis_carry_forward_history_v1"
                    ),
                    "owner": carry_projection["owner"],
                    "canonical_state": True,
                    "carry_forward_projection_count": 1,
                    "carry_forward_projections": [deepcopy(carry_projection)],
                }
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


def _preserve_text_list(value: Any) -> list[str]:
    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        return []
    out: list[str] = []
    for item in value:
        text = _clean_text(item, limit=180)
        if text and text not in out:
            out.append(text)
    return out


def _live_validation_positive_int(value: Any, message: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RunKernelTransitionError(message) from exc
    if parsed <= 0:
        raise RunKernelTransitionError(message)
    return parsed


def _reject_live_validation_closed_surface_inputs(
    inputs: Mapping[str, Any],
) -> None:
    closed_keys = {
        "author_input",
        "author_input_created",
        "citation_eligible",
        "citation_requested",
        "evidence_ledger_admission",
        "evidence_ledger_admitted",
        "fetch_read_executed",
        "fetch_read_requested",
        "final_answer_packet",
        "final_answer_packet_created",
        "partial_answer_ready",
        "product_correctness_claimed",
        "raw_provider_payload",
        "raw_search_response",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
    for key, value in _safe_mapping(inputs).items():
        normalized = str(key).casefold()
        if normalized in closed_keys and value not in (None, False, {}, []):
            raise RunKernelTransitionError(
                "live search validation cannot request closed surface: "
                + str(key)
            )


def _scout_hint_ids_from_report(report: Mapping[str, Any]) -> set[str]:
    hint_ids: set[str] = set()
    for key in (
        "scout_result_hints",
        "likely_official_target_hints",
        "currentness_hints",
    ):
        for item in report.get(key, []) or []:
            if not isinstance(item, Mapping):
                continue
            hint_id = _clean_text(item.get("hint_id"), limit=180)
            if hint_id:
                hint_ids.add(hint_id)
    for item in report.get("candidate_interpretations", []) or []:
        if not isinstance(item, Mapping):
            continue
        for hint_id in _preserve_text_list(item.get("supporting_hint_ids")):
            hint_ids.add(hint_id)
    return hint_ids


def _handoff_component_ids(contract: Mapping[str, Any]) -> list[str]:
    component_ids: list[str] = []
    for item in contract.get("accepted_answer_component_refs", []) or []:
        mapping = _safe_mapping(item)
        component_id = _clean_text(mapping.get("component_id"), limit=180)
        if component_id and component_id not in component_ids:
            component_ids.append(component_id)
    return component_ids


def _handoff_source_obligation_ids(
    *,
    parent_contract: Mapping[str, Any],
    planner_state: Mapping[str, Any],
    revision_state: Mapping[str, Any],
) -> list[str]:
    source_ids: list[str] = []
    for item in parent_contract.get("accepted_answer_component_refs", []) or []:
        mapping = _safe_mapping(item)
        for candidate_id in _preserve_text_list(
            mapping.get("source_obligation_candidate_ids")
        ):
            if candidate_id not in source_ids:
                source_ids.append(candidate_id)
        for candidate_id in _preserve_text_list(
            mapping.get("source_obligation_candidate_refs")
        ):
            if candidate_id not in source_ids:
                source_ids.append(candidate_id)
    planner = _safe_mapping(planner_state)
    qmr = _safe_mapping(planner.get("question_meaning_record"))
    for item in qmr.get("answer_components", []) or []:
        mapping = _safe_mapping(item)
        for candidate_id in _preserve_text_list(
            mapping.get("source_obligation_candidate_ids")
        ):
            if candidate_id not in source_ids:
                source_ids.append(candidate_id)
    for item in planner.get("component_search_requirements", []) or []:
        mapping = _safe_mapping(item)
        for candidate_id in _preserve_text_list(
            mapping.get("source_obligation_candidate_ids")
        ):
            if candidate_id not in source_ids:
                source_ids.append(candidate_id)
    revision = _safe_mapping(revision_state)
    for key in (
        "component_search_requirement_updates",
        "source_obligation_focus_updates",
        "revised_source_obligation_candidates",
    ):
        for item in revision.get(key, []) or []:
            mapping = _safe_mapping(item)
            candidate_id = _clean_text(
                mapping.get("candidate_id") or mapping.get("source_obligation_id"),
                limit=180,
            )
            if candidate_id and candidate_id not in source_ids:
                source_ids.append(candidate_id)
            for listed_id in _preserve_text_list(
                mapping.get("source_obligation_candidate_ids")
            ):
                if listed_id not in source_ids:
                    source_ids.append(listed_id)
    return source_ids


def _handoff_search_requirement_ids(
    *,
    planner_state: Mapping[str, Any],
    revision_state: Mapping[str, Any],
) -> list[str]:
    requirement_ids: list[str] = []
    for source in (
        _safe_mapping(planner_state).get("component_search_requirements"),
        _safe_mapping(revision_state).get("component_search_requirement_updates"),
    ):
        for item in source or []:
            mapping = _safe_mapping(item)
            requirement_id = _clean_text(
                mapping.get("requirement_id")
                or mapping.get("search_requirement_id"),
                limit=180,
            )
            if requirement_id and requirement_id not in requirement_ids:
                requirement_ids.append(requirement_id)
    return requirement_ids


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


def _require_dprime_downstream_closed(*, state: RunState, context: str) -> None:
    if (
        state.sufficiency_readiness_state
        or state.sufficiency_readiness_projection
        or state.sufficiency_readiness_history
    ):
        raise RunKernelTransitionError(f"{context} must not follow SufficiencyReadiness")
    if state.final_answer_packet or state.final_answer_packet_history:
        raise RunKernelTransitionError(f"{context} must not create or consume FAP")
    if (
        state.author_observation
        or state.final_answer_outcome
        or state.author_prose_state
        or state.author_prose_projection
        or state.author_prose_history
    ):
        raise RunKernelTransitionError(f"{context} must keep Author/answer closed")
    if state.final_answer_authority_projection:
        raise RunKernelTransitionError(
            f"{context} must not follow final answer authority"
        )


def _require_false_fields(
    value: Mapping[str, Any],
    fields: Sequence[str],
    *,
    context: str,
) -> None:
    for field_name in fields:
        if value.get(field_name) is not False:
            raise RunKernelTransitionError(f"{context} must keep {field_name}=False")


def _dprime_source_obligation_authority_projection(
    source_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": source_state.get("owner"),
        "schema_version": source_state.get("schema_version"),
        "runtime_surface": source_state.get("runtime_surface"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": source_state.get("run_id"),
        "request_id": source_state.get("request_id"),
        "source_obligation_authority_id": source_state.get(
            "source_obligation_authority_id"
        ),
        "source_obligation_authority_digest": source_state.get(
            "source_obligation_authority_digest"
        ),
        "source_obligation_authority_status": source_state.get(
            "source_obligation_authority_status"
        ),
        "source_obligation_status": source_state.get("source_obligation_status"),
        "status": source_state.get("status"),
        "blocker": None,
        "authority_consumed": True,
        "satisfaction_claimed": bool(source_state.get("satisfaction_claimed")),
        "satisfaction_authority_backed_by": source_state.get(
            "satisfaction_authority_backed_by"
        ),
        "retained_ids_consumed_as_lineage": bool(
            source_state.get("retained_ids_consumed_as_lineage")
        ),
        "retained_ids_alone_are_authority": False,
        "component_coverage_only_treated_as_pass": False,
        "source_obligation_candidate_ids": list(
            source_state.get("source_obligation_candidate_ids") or []
        ),
        "satisfied_source_obligation_ids": list(
            source_state.get("satisfied_source_obligation_ids") or []
        ),
        "component_coverage_ref": _safe_mapping(
            source_state.get("component_coverage_ref")
        ),
        "semantic_observation_ref": _safe_mapping(
            source_state.get("semantic_observation_ref")
        ),
        "content_ref": _safe_mapping(source_state.get("content_ref")),
        "lineage": _safe_mapping(source_state.get("lineage")),
        "citation_eligibility_authority_consumed": False,
        "citation_rendering_created": False,
        "sufficiency_readiness_created": False,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "product_correctness_claimed": False,
        "live_validation_not_run": True,
    }


def _dprime_citation_source_handoff_projection(
    handoff_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "owner": handoff_state.get("owner"),
        "schema_version": handoff_state.get("schema_version"),
        "runtime_surface": handoff_state.get("runtime_surface"),
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": handoff_state.get("run_id"),
        "request_id": handoff_state.get("request_id"),
        "citation_source_handoff_id": handoff_state.get(
            "citation_source_handoff_id"
        ),
        "citation_source_handoff_digest": handoff_state.get(
            "citation_source_handoff_digest"
        ),
        "citation_eligibility_authority_status": handoff_state.get(
            "citation_eligibility_authority_status"
        ),
        "citation_source_handoff_status": handoff_state.get(
            "citation_source_handoff_status"
        ),
        "status": handoff_state.get("status"),
        "blocker": None,
        "authority_consumed": True,
        "citation_eligibility_authority_consumed": True,
        "citation_source_handoff_consumed": True,
        "source_obligation_authority_consumed": True,
        "source_obligation_authority_ref": _safe_mapping(
            handoff_state.get("source_obligation_authority_ref")
        ),
        "component_coverage_ref": _safe_mapping(
            handoff_state.get("component_coverage_ref")
        ),
        "citation_eligible_source_ids": list(
            handoff_state.get("citation_eligible_source_ids") or []
        ),
        "citation_source_records": [
            _safe_mapping(record)
            for record in handoff_state.get("citation_source_records") or []
            if isinstance(record, Mapping)
        ],
        "citation_rendering_created": False,
        "citations_rendered": False,
        "citation_formatter_invoked": False,
        "ordered_product_source_output_created": False,
        "sufficiency_readiness_created": False,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "author_input_created": False,
        "product_correctness_claimed": False,
        "live_validation_not_run": True,
        "reasons": list(handoff_state.get("reasons") or []),
    }


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
        "component_readiness": judgment_projection.get("component_readiness", {}),
        "multicomponent_graph_consumption": judgment_projection.get(
            "multicomponent_graph_consumption",
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
    "AUTHOR_PROSE_FINALIZATION_STAGE",
    "FINAL_ANSWER_PACKET_STAGE",
    "FOLLOWUP_AUTHORIZATION_STAGE",
    "FOLLOWUP_SEARCH_AUTHORIZATION_STAGE",
    "SCRUTINEER_REVIEW_STAGE",
    "SPECIALIST_SOURCE_BOUND_CALCULATION_STAGE",
    "SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE",
    "SUFFICIENCY_READINESS_STAGE",
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
    "ANSWER_CONTRACT_AUTHORITY_MAP_STAGE",
    "OFFLINE_SEARCH_EXECUTOR_BRIDGE_STAGE",
    "COMPONENT_SCOPED_SOURCE_CUSTODY_STAGE",
    "MAIN_RETRIEVAL_STAGE",
    "MULTICOMPONENT_RECOVERY_AUTHORIZATION_STAGE",
    "MULTICOMPONENT_RECOVERY_OUTCOME_STAGE",
    "MULTICOMPONENT_SELECTIVE_CLOSURE_STAGE",
    "EVIDENCE_LEDGER_STAGE",
    "SEARCH_JUDGMENT_STAGE",
    "SEARCH_WORK_PLAN_CONSTRUCTION_STAGE",
    "DPRIME_CITATION_SOURCE_DISPLAY_STAGE",
    "DPRIME_CITATION_SOURCE_HANDOFF_AUTHORITY_STAGE",
    "DPRIME_SOURCE_OBLIGATION_AUTHORITY_STAGE",
    "SUFFICIENCY_JUDGMENT_STAGE",
    "RUN_CONTRACT_STAGE",
    "QUERY_PRODUCTION_STAGE",
    "QUERY_PLAN_ADMISSION_STAGE",
    "RETRIEVAL_STOP_CHECKPOINT_STAGE",
    "ROUTE_REQUEST_STAGE",
    "RUN_KERNEL_TRACE_KEY",
    "SEARCH_PLANNER_PRODUCTION_STAGE",
    "SEARCH_PLANNER_REVISION_STAGE",
    "SEARCH_EXECUTOR_HANDOFF_STAGE",
    "LIVE_SEARCH_VALIDATION_STAGE",
    "SCOUT_DISAMBIGUATION_STAGE",
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
