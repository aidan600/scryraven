"""Default-off generic single-relation live dogfood entrypoint.

This module consumes the relation plan from
``core.generic_query_to_relation_planning`` before any live acquisition. The live
search seed, component refs, source-obligation refs, and D-prime intake posture
all come from that plan. It deliberately does not reuse the fixed passport
dogfood query gate, anchors, or domain assumptions.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from core.analyst_workbench_runtime import (
    ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION,
    ANALYST_WORKBENCH_SCHEMA_VERSION,
    CANDIDATE_EVIDENCE_TRIAGE_SCHEMA_VERSION,
    WORKBENCH_DPRIME_DOSSIER_SCHEMA_VERSION,
    WORKBENCH_REDUCTION_PROJECTION_SCHEMA_VERSION,
    AnalystWorkbenchError,
    build_current_source_record_analyst_workbench,
    empty_current_source_record_analyst_workbench_bundle,
    validate_current_source_record_analyst_workbench_bundle,
)
from core.dprime_product_smart_one_shot_transport import (
    build_dprime_product_smart_model_review_adapter,
    build_dprime_product_smart_model_review_license,
    build_dprime_product_smart_model_review_provider_boundary,
)
from core.dprime_support_proposal_schema import (
    BLOCKED_APPROVED_MODEL_UNAVAILABLE,
    BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED,
    BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID,
    BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE,
    BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE,
    BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT,
    DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED,
)
from core.fetch_read_content_reference import (
    FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
    BoundedTextSelection,
    FetchReadContentReferenceError,
    build_fetch_read_content_packet_from_candidate_packet,
    select_bounded_answer_bearing_text,
    validate_fetch_read_content_packet,
)
from core.generic_product_provider_acquisition import (
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE,
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE,
    PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS,
    ProductProviderAcquisitionRequest,
    ProductProviderAcquisitionResult,
    ProductProviderAcquisitionRunner,
    build_generic_product_provider_acquisition_runner,
    redact_provider_extracted_source_text,
)
from core.generic_query_to_relation_planning import (
    GenericQueryRelationPlanningError,
    build_generic_query_relation_plan,
)
from core.model_assisted_single_relation_planning import (
    BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE,
    MODEL_ASSISTED_PLANNING_MODEL_TASK,
    MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE,
    PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
    PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY,
    build_model_assisted_single_relation_planning_packet,
)
from core.mvp_supported_query_class_boundary import MVP_SUPPORTED_QUERY_CLASS_ID
from core.product_model_route_config import (
    CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
    CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
    MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
    MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
)
from core.run_kernel import (
    SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_result_candidate_packet import (
    SearchResultCandidatePacket,
    SearchResultCandidateRecord,
    validate_search_result_candidate_packet,
)
from core.single_relation_source_obligation_recovery_authorization import (
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED,
    BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED,
    DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED,
    candidate_answer_bearing_by_safe_diagnostics,
    candidate_official_source_of_record_looking_by_safe_diagnostics,
    selected_candidate_ref_from_diagnostic,
)
from proplex.live_acquisition_readability_status import (
    FETCH_READ_ARTIFACT_DIR,
    FETCH_READ_CONTENT_PACKET_NAME,
    LIVE_SOURCE_SURVIVAL_SUMMARY_NAME,
    SANITIZED_PROVIDER_RESULTS_NAME,
    SEARCH_ARTIFACT_DIR,
    SEARCH_CANDIDATE_PACKET_NAME,
    SEARCH_RESULT_CANDIDATE_PACKET_NAME,
)
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from proplex.mvp_friend_shareable_output import MvpFriendOutputResult

PHASE_NAME = "GENERIC-SINGLE-RELATION-ANSWER-SOURCE-GATEWAY-01"
SCHEMA_VERSION = "generic_single_relation_live_dogfood_v1"
MODE = "BUILD"
PASS_DECISION = "PASS"
CONFIRM_LIVE_DOGFOOD_FLAG = "--confirm-live-dogfood"
DOGFOOD_ENTRYPOINT_SURFACE = "mvp_single_relation_live_dogfood"
DOGFOOD_ENTRYPOINT_KIND = "diagnostic_dogfood_cli"
DOGFOOD_SUPPORTED_QUERY_CLASS = "generic-single-relation-live-dogfood-v1"
PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE = (
    "mvp_current_source_of_record_single_fact"
)
PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND = "product_supported_query_cli"
PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS = (
    "mvp-current-source-of-record-single-fact-v1"
)

BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_CREDENTIAL_UNAVAILABLE = (
    BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_CREDENTIAL_UNAVAILABLE
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CONTRACT_MISSING = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CONTRACT_MISSING"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_OUTPUT_INVALID = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_OUTPUT_INVALID"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PATH_NOT_CONSUMED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PATH_NOT_CONSUMED"
)
BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_STATE_MISSING = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_STATE_MISSING"
)
BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_DPRIME_NOT_PASSING = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_DPRIME_NOT_PASSING"
)
BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_SOURCE_DISPLAY_BLOCKED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_SOURCE_DISPLAY_BLOCKED"
)
BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD = (
    "BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD"
)
BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED"
)
BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED"
)
BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING = (
    "BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING"
)
BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE = (
    "BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE"
)
BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED = (
    "BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE"
)
PROVIDER_EXTRACTED_CONTENT_CUSTODY_ADMISSION_BLOCKED = (
    "PROVIDER_EXTRACTED_CONTENT_CUSTODY_ADMISSION_BLOCKED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_ENFORCEMENT = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_ENFORCEMENT"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE"
)
DEFAULT_PROVIDER = "tavily"
DEFAULT_EXTRACTION_PROVIDER = "tavily"
DEFAULT_SCOUT_PROVIDER = "serper"
DEFAULT_OPERATION = "search"
CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG = (
    "--confirm-live-source-challenge-recovery"
)
DEFAULT_OUTPUT_DIR = Path("output") / "mvp_single_relation_live_dogfood_01"
PRODUCT_SINGLE_FACT_OUTPUT_ROOT = Path("output")
SANITIZED_PRODUCT_PROVIDER_ACQUISITION_RESPONSE_NAME = (
    "sanitized-product-provider-acquisition-response.json"
)
SANITIZED_SCOUT_PRODUCT_PROVIDER_ACQUISITION_RESPONSE_NAME = (
    "sanitized-scout-product-provider-acquisition-response.json"
)
LIVE_DOGFOOD_PACKET_NAME = "single_relation_live_dogfood_packet.json"
CURRENT_SOURCE_RECORD_SINGLE_FACT_REVIEW_REPORT_JSON_NAME = (
    "current_source_record_single_fact_review_report.json"
)
CURRENT_SOURCE_RECORD_SINGLE_FACT_REVIEW_REPORT_MD_NAME = (
    "current_source_record_single_fact_review_report.md"
)
SOURCE_READINESS_GATEWAY_SCHEMA_VERSION = "generic_single_relation_source_readiness_gateway_v1"
DPRIME_AUTHORITY_INTEGRATION_SCHEMA_VERSION = (
    "generic_single_relation_dprime_authority_integration_v1"
)
SOURCE_CITATION_DISPLAY_BOUNDARY_SCHEMA_VERSION = (
    "generic_single_relation_source_citation_display_boundary_v1"
)
WORKBENCH_GAP_REENTRY_REF_SCHEMA_VERSION = "workbench_gap_reentry_ref_v1"
DPRIME_AUTHORITY_INTEGRATION_NEXT_PHASE = (
    "GENERIC-DOGFOOD-DPRIME-AUTHORITY-ADAPTER-01"
)
SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE = (
    "GENERIC-SINGLE-RELATION-QUICK-SUFFICIENCY-READINESS-01"
)
ANSWER_PATH_NEXT_PRODUCT_CHECKPOINT = "TIGHTLY-SCOPED-LIMITED-LIVE-VALIDATION"
EXISTING_DPRIME_ANSWER_PATH_BLOCKERS = frozenset(
    {
        "BLOCKED_DPRIME_SUFFICIENCY_READINESS_AUTHORITY_MISSING",
        "BLOCKED_DPRIME_FAP_AUTHORITY_MISSING",
        "BLOCKED_DPRIME_AUTHOR_OUTPUT_AUTHORITY_MISSING",
        "BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING",
        "BLOCKED_DPRIME_ANSWER_PATH_SUPPORT_BUNDLE_INCOMPLETE",
    }
)
EXISTING_DPRIME_DOWNSTREAM_AUTHORITY_MODULE_REFS = (
    "core.dprime_runkernel_admission_runtime",
    "core.dprime_ordinary_contract_authority_runtime",
    "core.dprime_semantic_observation_materialization_runtime",
    "core.dprime_evidence_support_bundle_runtime",
    "core.dprime_source_obligation_citation_authority_runtime",
    "core.dprime_single_lane_answer_path_runtime",
    "core.runkernel_followup_search_reentry_ordinary_search_runtime",
    "core.dprime_multi_source_analyst_scrutiny_runtime",
)

MAX_LIVE_RUNS = 1
MAX_QUERY_PLANS_CONSUMED = 1
MAX_INITIAL_FAST_MODEL_PLANNING_CALLS = 1
MAX_RECOVERY_FAST_MODEL_PLANNING_CALLS = 1
MAX_FAST_MODEL_PLANNING_CALLS = (
    MAX_INITIAL_FAST_MODEL_PLANNING_CALLS
    + MAX_RECOVERY_FAST_MODEL_PLANNING_CALLS
)
MAX_PROVIDER_SEARCH_CALLS = 1
MAX_SOURCE_CHALLENGE_RECOVERY_PROVIDER_CALLS = 1
MAX_SERPER_SCOUT_CALLS = 1
MAX_PROVIDER_RESULTS = 5
MAX_FETCH_READ_ATTEMPTS = 3
MAX_EVIDENCE_LEDGER_ADMISSIONS = 3
MAX_DPRIME_MODEL_REVIEW_CALLS = 1
MAX_FOLLOWUP_LOOPS = 0
MAX_FAP_CALLS = 0
MAX_AUTHOR_CALLS = 0
MAX_INDEPENDENT_SOURCE_CHECKS = 0
MAX_FETCHED_BYTES = 1_048_576
MAX_REDIRECTS = 2
FETCH_READ_PUBLIC_WEB_REQUEST_PROFILE_ID = (
    "generic_public_web_fetch_read_request_hygiene_v1"
)
FETCH_READ_PUBLIC_WEB_REQUEST_POSTURE = (
    "stable_product_user_agent_accept_accept_language"
)
FETCH_READ_PUBLIC_WEB_USER_AGENT = (
    "ScryRaven/1.0 "
    "(+https://github.com/aidan600/scryraven; generic-public-web-readability-check)"
)

FETCH_READ_FAILURE_MISSING_URL = "MISSING_URL"
FETCH_READ_FAILURE_INVALID_URL = "INVALID_URL"
FETCH_READ_FAILURE_HTTP_4XX = "HTTP_4XX"
FETCH_READ_FAILURE_HTTP_5XX = "HTTP_5XX"
FETCH_READ_FAILURE_UNSUPPORTED_CONTENT_TYPE = "UNSUPPORTED_CONTENT_TYPE"
FETCH_READ_FAILURE_NO_READABLE_TEXT = "NO_READABLE_TEXT"
FETCH_READ_FAILURE_EXCEPTION = "FETCH_READ_EXCEPTION"
FETCH_READ_FAILURE_UNKNOWN = "UNKNOWN"
FETCH_READ_FAILURE_CATEGORIES = frozenset(
    {
        FETCH_READ_FAILURE_MISSING_URL,
        FETCH_READ_FAILURE_INVALID_URL,
        FETCH_READ_FAILURE_HTTP_4XX,
        FETCH_READ_FAILURE_HTTP_5XX,
        FETCH_READ_FAILURE_UNSUPPORTED_CONTENT_TYPE,
        FETCH_READ_FAILURE_NO_READABLE_TEXT,
        FETCH_READ_FAILURE_EXCEPTION,
        FETCH_READ_FAILURE_UNKNOWN,
    }
)
FETCH_READ_READABLE_CONTENT_TYPES = frozenset(
    {"text/html", "text/plain", "application/xhtml+xml"}
)
OFFICIAL_ARTIFACT_READ_SUPPORT_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "text/csv",
        "text/tab-separated-values",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)
FETCH_READ_UNKNOWN = "unknown"
FETCH_READ_CAP_EXHAUSTED = "FETCH_READ_CAP_EXHAUSTED"
FETCH_READ_STOPPED_AFTER_SUCCESS = "READABLE_CONTENT_OBTAINED"
FETCH_READ_CANDIDATE_SELECTION_POLICY_ID = (
    "generic_single_relation_live_fetch_read_acquisition_priority_v1"
)
FETCH_READ_CANDIDATE_SELECTION_SCOPE = "local_fetch_read_acquisition_only"
ACQUISITION_PLANNER_SCHEMA_VERSION = (
    "generic_single_relation_live_acquisition_planner_v1"
)
ACQUISITION_PLANNER_KIND = (
    "deterministic_artifact_single_relation_acquisition_planner"
)
SOURCE_ACQUISITION_MODE_PROVIDER_EXTRACTED = "provider_extracted_source_content"
SOURCE_ACQUISITION_MODE_DIRECT_FETCH_FALLBACK = "direct_public_web_fetch_fallback"
SOURCE_ACQUISITION_MODE_NONE = "none"
PROVIDER_EXTRACTED_CONTENT_TYPE = "text/html"
OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE = "readable_bounded_sanitized_text"
OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_UNREADABLE = "unreadable_read_support_needed"
OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_FETCH_RUNNER = (
    "existing_fetch_read_runner_sanitized_text"
)
OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_PROVIDER_EXTRACTED = (
    "provider_extracted_sanitized_text"
)
ANSWER_BEARING_CANDIDATE_WINDOW_NOT_ESTABLISHED = (
    "answer_bearing_candidate_window_not_established"
)
ANSWER_BEARING_CANDIDATE_WINDOW_BEST_EFFORT = (
    "answer_bearing_candidate_window_best_effort"
)
ANSWER_BEARING_CANDIDATE_WINDOW_ESTABLISHED = (
    "answer_bearing_candidate_window_established"
)
ANSWER_BEARING_CANDIDATE_WINDOW_NOT_SELECTED = (
    "ANSWER_BEARING_CANDIDATE_WINDOW_NOT_SELECTED"
)
SOURCE_CHALLENGE_RECOVERY_ARTIFACT_DIR = "source_challenge_recovery"
_CANDIDATE_PRIORITY_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "by",
        "charge",
        "com",
        "cost",
        "current",
        "currently",
        "determine",
        "fee",
        "fees",
        "filing",
        "find",
        "form",
        "for",
        "from",
        "gov",
        "html",
        "http",
        "https",
        "in",
        "is",
        "latest",
        "material",
        "net",
        "of",
        "official",
        "or",
        "org",
        "paper",
        "record",
        "requirement",
        "requirements",
        "source",
        "states",
        "that",
        "the",
        "to",
        "www",
    }
)
_CANDIDATE_DERIVATIVE_MARKERS = frozenset(
    {
        "advocacy",
        "blog",
        "campaign",
        "center",
        "clinic",
        "explainer",
        "foundation",
        "guide",
        "institute",
        "legal",
        "news",
        "project",
        "wiki",
    }
)

RAW_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_source_content_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
CLOSED_FALSE_FLAGS = {
    "product_correctness_claimed": False,
    "friend_level_mvp_claimed": False,
    "general_supported_query_mvp_claimed": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "source_authority_finalized": False,
    "final_answer_packet_created": False,
    "author_prose_created": False,
    "citation_source_display_created": False,
    "citation_rendering_invoked": False,
    "multi_component_planning_opened": False,
    "runkernel_dag_scheduling_opened": False,
    "budget_leases_opened": False,
    "fap_opened": False,
    "author_opened": False,
    "fap_author_opened": False,
    "source_class_adapters_opened": False,
    "social_review_analysis_opened": False,
    "followup_loops_opened": False,
}
EXPLICIT_NON_PROOFS = (
    "not product correctness",
    "not arbitrary query answering",
    "not general supported-query MVP readiness",
    "not friend-level MVP readiness",
    "not multi-component planning",
    "not RunKernel DAG scheduling or budget leases",
    "not source-class adapter implementation",
    "not social/review aggregation",
    "not FAP or Author execution",
    "not source-obligation satisfaction by this packet alone",
    "not citation eligibility",
    "not source-authority finality",
    "not final answer prose generation",
)
SOURCE_READINESS_GATEWAY_NON_CLAIMS = {
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "source_authority_finalized": False,
    "final_answer_packet_created": False,
    "author_prose_created": False,
    "product_correctness_claimed": False,
}
SOURCE_CITATION_DISPLAY_BOUNDARY_NON_CLAIMS = {
    "sufficiency_readiness_created": False,
    "final_answer_prose_created": False,
    "final_answer_packet_created": False,
    "author_answer_created": False,
    "author_invoked": False,
    "citation_rendering_invoked": False,
    "final_citation_rendering_created": False,
    "product_correctness_claimed": False,
}
_ALLOWED_PROVIDER_ENVELOPE_KEYS = frozenset(
    {
        "request_kind",
        "provider",
        "provider_role",
        "acquisition_provider_role",
        "operation",
        "result_count",
        "results",
        "domain_constraints",
        "include_domains",
        "exclude_domains",
        "source_of_record_domain_constraints",
        "domain_constraints_acquisition_only",
        "domain_constraints_create_source_authority",
        "domain_constraints_satisfy_source_obligation",
        "domain_constraints_citation_eligible",
        "domain_constraints_claim_correctness",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
_ALLOWED_PROVIDER_RESULT_KEYS = frozenset(
    {
        "title",
        "url",
        "link",
        "domain",
        "snippet",
        "date",
        "published_or_observed_date",
        "rank",
        "result_rank",
        "call_index",
        "provider_call_index",
        "provider_extracted_text",
        "provider_extracted_text_sanitized",
        "provider_extracted_text_bounded",
        "provider_extracted_text_char_count",
        "provider_extracted_text_digest",
        "provider_extracted_source_text_digest",
        "provider_extracted_content_type",
        "provider_extracted_at",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "bounded_text",
        "cache",
        "cache_row",
        "cookie",
        "db",
        "db_row",
        "env",
        "full_trace",
        "header",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "private_logs",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_headers",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_page_content",
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
        "token",
        "unbounded_content",
        "unbounded_page_text",
        "unbounded_text",
    }
)
_ALLOWED_RAW_FALSE_KEYS = frozenset(
    {
        "raw_headers_retained",
        "raw_model_response_retention",
        "raw_model_response_retained",
        "raw_page_content_retained",
        "raw_page_text_retained",
        "raw_private_retention_flags",
        "raw_private_retention",
        "raw_prompt_retention",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "raw_source_content_retained",
        "raw_source_text_retained",
    }
)
PRIVATE_LOOKING_VALUE_REDACTION = "private_looking_value_not_retained"
PRIVATE_LOOKING_DETAIL_REDACTION = "private-looking detail redacted"
_PUBLIC_CREDENTIAL_NAME_REFERENCES = frozenset(
    {
        "SERPER_API_KEY",
        "TAVILY_API_KEY",
    }
)


class GenericSingleRelationLiveDogfoodRunError(ValueError):
    """Raised when the generic live dogfood path must fail closed."""

    def __init__(
        self,
        blocker: str,
        detail: str,
        *,
        caps_exhausted: bool = False,
        fetch_status_class: str | None = None,
        fetch_content_type: str | None = None,
        fetch_readable_content_type: bool | str | None = None,
        fetch_readable_text_obtained: bool | None = None,
        fetch_failure_category: str | None = None,
        fetch_final_url: str | None = None,
        fetch_status_code: int | None = None,
        fetch_redirect_count: int | None = None,
        fetch_redirect_chain_digest: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail
        self.caps_exhausted = caps_exhausted
        self.fetch_status_class = fetch_status_class
        self.fetch_content_type = fetch_content_type
        self.fetch_readable_content_type = fetch_readable_content_type
        self.fetch_readable_text_obtained = fetch_readable_text_obtained
        self.fetch_failure_category = fetch_failure_category
        self.fetch_final_url = fetch_final_url
        self.fetch_status_code = fetch_status_code
        self.fetch_redirect_count = fetch_redirect_count
        self.fetch_redirect_chain_digest = fetch_redirect_chain_digest


@dataclass(frozen=True, slots=True)
class GenericProviderProxyRunRequest:
    repo_root: Path
    output_path: Path
    query: str
    provider: str = DEFAULT_PROVIDER
    acquisition_provider_role: str = "extraction_provider"
    operation: str = DEFAULT_OPERATION
    max_results: int = MAX_PROVIDER_RESULTS
    domain_constraints: tuple[str, ...] = ()
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    source_of_record_domain_constraints: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GenericProviderProxyRunResult:
    return_code: int
    output_path: Path
    provider_calls_attempted: int
    provider_calls_completed: int
    blocker: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class GenericLiveFetchReadResult:
    attempted_url: str
    final_url: str
    final_domain: str
    status_code: int | None
    status_class: str | None
    content_type: str | None
    fetched_byte_count: int
    sanitized_text: str
    content_title: str | None = None
    redirect_count: int = 0
    redirect_chain_digest: str | None = None
    retrieved_or_observed_at: str = ""
    official_artifact_read_support: bool = False
    official_artifact_read_support_source: str | None = None


@dataclass(frozen=True, slots=True)
class _CandidateWindowEvaluation:
    candidate: Mapping[str, Any]
    provider_result: Mapping[str, Any]
    selection: BoundedTextSelection
    score: tuple[int, ...]
    diagnostic: dict[str, Any]


ProviderProxyRunner = Callable[
    [GenericProviderProxyRunRequest],
    GenericProviderProxyRunResult,
]
FetchReadRunner = Callable[[str], GenericLiveFetchReadResult]


def _select_generic_provider_acquisition_runner(
    *,
    legacy_injected_provider_runner: ProviderProxyRunner | None,
    product_provider_acquisition_runner: ProductProviderAcquisitionRunner | None,
    counts: dict[str, Any],
) -> ProviderProxyRunner | None:
    if legacy_injected_provider_runner is not None:
        counts["product_provider_acquisition_adapter_used"] = 0
        return legacy_injected_provider_runner
    product_runner = (
        product_provider_acquisition_runner
        or build_generic_product_provider_acquisition_runner()
    )
    counts["product_provider_acquisition_adapter_used"] = 1
    return _provider_runner_from_product_acquisition_runner(product_runner)


def _provider_runner_from_product_acquisition_runner(
    product_provider_acquisition_runner: ProductProviderAcquisitionRunner,
) -> ProviderProxyRunner:
    def runner(request: GenericProviderProxyRunRequest) -> GenericProviderProxyRunResult:
        result = product_provider_acquisition_runner(
            ProductProviderAcquisitionRequest(
                repo_root=request.repo_root,
                output_path=request.output_path,
                query=request.query,
                provider=request.provider,
                acquisition_provider_role=request.acquisition_provider_role,
                operation=request.operation,
                max_results=request.max_results,
                domain_constraints=tuple(request.domain_constraints),
                include_domains=tuple(request.include_domains),
                exclude_domains=tuple(request.exclude_domains),
                source_of_record_domain_constraints=tuple(
                    request.source_of_record_domain_constraints
                ),
            )
        )
        return _generic_result_from_product_acquisition_result(result)

    return runner


def _generic_result_from_product_acquisition_result(
    result: ProductProviderAcquisitionResult,
) -> GenericProviderProxyRunResult:
    return GenericProviderProxyRunResult(
        return_code=result.return_code,
        output_path=result.output_path,
        provider_calls_attempted=result.provider_calls_attempted,
        provider_calls_completed=result.provider_calls_completed,
        blocker=result.blocker,
        detail=result.detail,
    )


def build_generic_single_relation_live_dogfood_run_output(
    *,
    query: str,
    repo_root: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    confirm_live_dogfood: bool = False,
    confirm_live_dprime_review: bool = False,
    confirm_live_source_challenge_recovery: bool = False,
    entrypoint_surface: str = DOGFOOD_ENTRYPOINT_SURFACE,
    entrypoint_kind: str = DOGFOOD_ENTRYPOINT_KIND,
    diagnostic_dogfood_alias: bool = True,
    supported_query_class: str = DOGFOOD_SUPPORTED_QUERY_CLASS,
    product_provider_acquisition_runner: ProductProviderAcquisitionRunner | None = None,
    provider_proxy_runner: ProviderProxyRunner | None = None,
    fetch_read_runner: FetchReadRunner | None = None,
    smart_provider: str | None = None,
    smart_model: str | None = None,
    fast_provider: str | None = None,
    fast_model: str | None = None,
    fast_model_local_url: str | None = None,
    fast_model_planner_callable: Callable[..., Any] | None = None,
    fast_model_planner_clean_json_response: Callable[[str], str] | None = None,
    fast_model_planner_strict_route_ref: Mapping[str, Any] | None = None,
    require_model_assisted_planning: bool = False,
    dprime_model_review_license: Mapping[str, Any] | None = None,
    dprime_model_review_callable: Callable[..., Any] | None = None,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None = None,
    dprime_one_shot_model_review_adapter: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> MvpFriendOutputResult:
    """Run one planned generic relation through bounded live dogfood."""

    entrypoint_metadata = _entrypoint_metadata(
        entrypoint_surface=entrypoint_surface,
        entrypoint_kind=entrypoint_kind,
        diagnostic_dogfood_alias=diagnostic_dogfood_alias,
        supported_query_class=supported_query_class,
    )
    root = Path(repo_root).resolve()
    run_id = _run_id(run_id)
    run_dir = _run_output_dir(
        root,
        output_dir or DEFAULT_OUTPUT_DIR,
        run_id,
        entrypoint_metadata=entrypoint_metadata,
    )
    retained_root = run_dir / "retained_status_repo"
    provider_output_path = run_dir / SANITIZED_PRODUCT_PROVIDER_ACQUISITION_RESPONSE_NAME
    packet_path = run_dir / LIVE_DOGFOOD_PACKET_NAME
    review_report_json_path = (
        run_dir / CURRENT_SOURCE_RECORD_SINGLE_FACT_REVIEW_REPORT_JSON_NAME
    )
    review_report_md_path = (
        run_dir / CURRENT_SOURCE_RECORD_SINGLE_FACT_REVIEW_REPORT_MD_NAME
    )
    counts = _empty_counts()
    relation_plan: dict[str, Any] | None = None
    semantic_payload: Mapping[str, Any] = {}
    acquisition_plan: dict[str, Any] | None = None
    disambiguation_record: dict[str, Any] | None = None
    source_obligation_run_kernel = RunKernel.start(
        run_id=run_id,
        request_id=f"{run_id}:single_relation_source_obligation_recovery",
        request={"surface": "mvp_single_relation_live_dogfood_run"},
    )
    source_obligation_authorization: dict[str, Any] | None = None
    source_challenge_recovery: dict[str, Any] | None = None
    initial_model_planning_packet: dict[str, Any] | None = None
    recovery_model_planning_packet: dict[str, Any] | None = None
    product_single_fact_answer_path_enabled = (
        entrypoint_metadata["entrypoint_kind"] == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
        and entrypoint_metadata["supported_query_class"]
        == PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS
    )
    planning_strict_route_ref = _model_assisted_planning_route_ref(
        strict_model_route_ref=fast_model_planner_strict_route_ref,
        fast_provider=fast_provider,
        fast_model=fast_model,
        fast_model_local_url=fast_model_local_url,
        require_model_assisted_planning=require_model_assisted_planning,
        planner_callable=fast_model_planner_callable,
    )

    try:
        relation_plan = build_generic_query_relation_plan(query)
        counts["query_plans_consumed"] = 1
        _guard_plan_for_live_acquisition(relation_plan)
        initial_model_planning_packet = _build_model_assisted_planning_packet(
            planning_context_kind=PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
            context_state=_initial_model_planning_context(relation_plan),
            planner_callable=fast_model_planner_callable,
            strict_model_route_ref=planning_strict_route_ref,
            clean_json_response=fast_model_planner_clean_json_response,
            require_model_assisted_planning=require_model_assisted_planning,
        )
        _record_model_assisted_planning_counts(
            counts,
            initial_model_planning_packet,
            prefix="initial",
        )
        _enforce_caps(counts)
        if _model_assisted_planning_strict_route_blocked(
            initial_model_planning_packet,
            require_model_assisted_planning=require_model_assisted_planning,
        ):
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE,
                (
                    "Strict reusable FastModel planning route is unavailable; "
                    "live model-assisted planning cannot be exercised under the "
                    "phase one-call budget."
                ),
            )
        if _model_assisted_planning_required_blocked(
            initial_model_planning_packet,
            require_model_assisted_planning=require_model_assisted_planning,
        ):
            initial_blocker = _safe_mapping(initial_model_planning_packet)
            raise GenericSingleRelationLiveDogfoodRunError(
                _clean_text(initial_blocker.get("blocker"), limit=220)
                or BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
                _clean_text(initial_blocker.get("blocker_detail"), limit=900)
                or "Model-assisted planning failed closed before acquisition.",
            )
        if _model_assisted_planning_multi_component_closed(
            initial_model_planning_packet
        ):
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
                (
                    "FastModel planning safely identified likely multi-component "
                    "structure, and multi-component execution remains closed."
                ),
            )
        acquisition_plan = _build_fast_acquisition_plan(
            relation_plan,
            model_planning_packet=initial_model_planning_packet,
        )
        counts["fast_planner_calls_attempted"] = 1
        if not confirm_live_dogfood:
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED,
                (
                    f"{entrypoint_metadata['confirmation_flag']} is required before live "
                    "provider/search/fetch/read contact."
                ),
            )
        provider_runner = _select_generic_provider_acquisition_runner(
            legacy_injected_provider_runner=provider_proxy_runner,
            product_provider_acquisition_runner=product_provider_acquisition_runner,
            counts=counts,
        )
        if provider_runner is None:
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE,
                "Generic single-relation live dogfood has no product provider route.",
            )
        _guard_dprime_review_route(
            confirm_live_dprime_review=confirm_live_dprime_review,
            dprime_model_review_callable=dprime_model_review_callable,
            dprime_one_shot_model_review_adapter=(
                dprime_one_shot_model_review_adapter
            ),
            environ=environ,
        )

        if acquisition_plan["disambiguation_required"]:
            scout_output_path = (
                run_dir / SANITIZED_SCOUT_PRODUCT_PROVIDER_ACQUISITION_RESPONSE_NAME
            )
            scout_result = provider_runner(
                GenericProviderProxyRunRequest(
                    repo_root=root,
                    output_path=scout_output_path,
                    query=str(acquisition_plan["disambiguation_query"]),
                    provider=DEFAULT_SCOUT_PROVIDER,
                    operation=DEFAULT_OPERATION,
                )
            )
            counts["serper_scout_calls_attempted"] = (
                scout_result.provider_calls_attempted
            )
            counts["serper_scout_calls_completed"] = (
                scout_result.provider_calls_completed
            )
            _enforce_caps(counts)
            if scout_result.return_code != 0:
                raise GenericSingleRelationLiveDogfoodRunError(
                    _provider_result_blocker(
                        scout_result,
                        default=BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE,
                    ),
                    _provider_result_detail(
                        scout_result,
                        default=(
                            "Serper scout/disambiguation product provider "
                            "acquisition did not complete."
                        ),
                    ),
                )
            scout_payload = _load_sanitized_provider_output(scout_result.output_path)
            disambiguation_record = _disambiguation_record_from_scout_payload(
                scout_payload,
                acquisition_plan=acquisition_plan,
            )
            acquisition_plan = _revised_acquisition_plan_after_disambiguation(
                acquisition_plan,
                disambiguation_record=disambiguation_record,
            )

        search_query_seed = str(acquisition_plan["acquisition_query"])
        extraction_provider = str(acquisition_plan["extraction_provider"])
        provider_result = provider_runner(
            GenericProviderProxyRunRequest(
                repo_root=root,
                output_path=provider_output_path,
                query=search_query_seed,
                provider=extraction_provider,
                operation=str(acquisition_plan["provider_operation"]),
            )
        )
        counts["provider_calls_attempted"] = provider_result.provider_calls_attempted
        counts["provider_calls_completed"] = provider_result.provider_calls_completed
        counts["extraction_provider_calls_attempted"] = (
            provider_result.provider_calls_attempted
        )
        counts["extraction_provider_calls_completed"] = (
            provider_result.provider_calls_completed
        )
        _enforce_caps(counts)
        if provider_result.return_code != 0:
            raise GenericSingleRelationLiveDogfoodRunError(
                _provider_result_blocker(
                    provider_result,
                    default=BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE,
                ),
                _provider_result_detail(
                    provider_result,
                    default=(
                        "extraction-capable product provider acquisition did "
                        "not complete."
                    ),
                ),
            )

        provider_payload = _load_sanitized_provider_output(provider_result.output_path)
        results = _provider_results(provider_payload)
        counts["provider_results_returned"] = len(results)
        _enforce_caps(counts)
        candidate_packet = _candidate_packet_from_provider_results(
            relation_plan=relation_plan,
            run_id=run_id,
            results=results,
            provider_calls_attempted=counts["provider_calls_attempted"],
            provider_calls_completed=counts["provider_calls_completed"],
            search_query_seed=search_query_seed,
            extraction_provider=extraction_provider,
        )
        _write_search_artifacts(
            retained_root=retained_root,
            provider_payload=provider_payload,
            candidate_packet=candidate_packet,
        )
        counts["search_tasks_attempted"] = 1
        counts["search_tasks_completed"] = 1

        fetch_packet, fetch_counts = _write_fetch_read_artifacts(
            retained_root=retained_root,
            relation_plan=relation_plan,
            acquisition_plan=acquisition_plan,
            provider_results=results,
            fetch_read_runner=fetch_read_runner or fetch_public_url_once,
            retain_failed_fetch_read_packet=product_single_fact_answer_path_enabled,
        )
        counts.update(fetch_counts)
        if fetch_packet is None:
            fetch_blocker = (
                _clean_text(fetch_counts.get("fetch_read_blocker"), limit=220)
                or BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING
            )
            fetch_detail = _clean_text(
                fetch_counts.get("fetch_read_blocker_detail"),
                limit=900,
            ) or "bounded fetch/read did not produce a retained readable handoff."
            raise GenericSingleRelationLiveDogfoodRunError(
                fetch_blocker,
                fetch_detail,
            )
        counts["fetch_read_packet_created"] = 1
        _enforce_caps(counts)
        analyst_workbench_bundle = build_current_source_record_analyst_workbench(
            relation_plan=relation_plan,
            acquisition_plan=acquisition_plan,
            candidate_diagnostics=_safe_sequence(
                counts.get("fetch_read_candidate_diagnostics")
            ),
            answer_bearing_candidate_window_diagnostics=_safe_sequence(
                counts.get("answer_bearing_candidate_window_diagnostics")
            ),
            provider_results=results,
            fetch_read_content_packet=fetch_packet,
            entrypoint_kind=entrypoint_metadata["entrypoint_kind"],
        )
        _record_analyst_workbench_counts(counts, analyst_workbench_bundle)

        source_obligation_authorization = (
            _build_source_obligation_recovery_authorization(
                run_kernel=source_obligation_run_kernel,
                relation_plan=relation_plan,
                acquisition_plan=acquisition_plan,
                counts=counts,
                dprime_status=None,
                recovery_confirmation_authorized=(
                    confirm_live_source_challenge_recovery
                ),
            )
        )
        dprime_kwargs: dict[str, Any] = {}
        if confirm_live_dprime_review:
            dprime_kwargs = _dprime_review_kwargs(
                smart_provider=smart_provider,
                smart_model=smart_model,
                dprime_model_review_license=dprime_model_review_license,
                dprime_model_review_callable=dprime_model_review_callable,
                dprime_one_shot_provider_boundary=dprime_one_shot_provider_boundary,
                dprime_one_shot_model_review_adapter=(
                    dprime_one_shot_model_review_adapter
                ),
            )
        semantic_status = build_live_semantic_coverage_status(
            query=str(relation_plan["sanitized_query"]),
            repo_root=retained_root,
            smart_provider=smart_provider,
            smart_model=smart_model,
            dprime_downstream_authority_enabled=False,
            dprime_source_citation_authority_enabled=True,
            dprime_single_lane_answer_path_enabled=(
                product_single_fact_answer_path_enabled
            ),
            dprime_run_kernel_admission_decision_status=(
                source_obligation_authorization.get(
                    "run_kernel_support_admission_decision_status"
                )
                or DPRIME_RUN_KERNEL_ADMISSION_DECISION_ADMITTED
            ),
            workbench_dprime_dossier=_safe_mapping(
                analyst_workbench_bundle.get("workbench_dprime_dossier")
            ),
            **dprime_kwargs,
        )
        semantic_payload = _safe_mapping(semantic_status.payload)
        counts["evidence_ledger_admissions"] = _evidence_admission_count(
            semantic_payload
        )
        counts["dprime_model_review_calls_attempted"] = _dprime_call_count(
            semantic_payload
        )
        counts["dprime_model_review_calls_completed"] = (
            _dprime_calls_completed(semantic_payload)
        )
        counts["followup_loop_count"] = _followup_loop_count(semantic_payload)
        _enforce_caps(counts)
        source_obligation_authorization = (
            _build_source_obligation_recovery_authorization(
                run_kernel=source_obligation_run_kernel,
                relation_plan=relation_plan,
                acquisition_plan=acquisition_plan,
                counts=counts,
                dprime_status=_safe_mapping(semantic_payload.get("dprime_status")),
                semantic_payload=semantic_payload,
                recovery_confirmation_authorized=(
                    confirm_live_source_challenge_recovery
                ),
            )
        )
        packet = _packet_from_semantic_status(
            relation_plan=relation_plan,
            run_id=run_id,
            retained_root=retained_root,
            counts=counts,
            acquisition_plan=acquisition_plan,
            disambiguation_record=disambiguation_record,
            semantic_payload=semantic_payload,
            status_decision=str(semantic_status.decision),
            confirm_live_dprime_review=confirm_live_dprime_review,
            confirm_live_source_challenge_recovery=(
                confirm_live_source_challenge_recovery
            ),
            source_obligation_recovery_authorization=(
                source_obligation_authorization
            ),
            source_challenge_recovery=None,
            initial_model_planning_packet=initial_model_planning_packet,
            recovery_model_planning_packet=recovery_model_planning_packet,
            require_model_assisted_planning=require_model_assisted_planning,
            entrypoint_metadata=entrypoint_metadata,
        )
        if source_obligation_authorization.get("recovery_required") is True:
            recovery_model_planning_packet = _build_model_assisted_planning_packet(
                planning_context_kind=PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY,
                context_state=_recovery_model_planning_context(
                    relation_plan=relation_plan,
                    acquisition_plan=acquisition_plan,
                    counts=counts,
                    semantic_payload=semantic_payload,
                    source_obligation_authorization=source_obligation_authorization,
                ),
                planner_callable=fast_model_planner_callable,
                strict_model_route_ref=planning_strict_route_ref,
                clean_json_response=fast_model_planner_clean_json_response,
                require_model_assisted_planning=require_model_assisted_planning,
            )
            _record_model_assisted_planning_counts(
                counts,
                recovery_model_planning_packet,
                prefix="recovery",
            )
            _enforce_caps(counts)
            if _model_assisted_planning_required_blocked(
                recovery_model_planning_packet,
                require_model_assisted_planning=require_model_assisted_planning,
            ):
                recovery_blocker = _safe_mapping(recovery_model_planning_packet)
                raise GenericSingleRelationLiveDogfoodRunError(
                    _clean_text(recovery_blocker.get("blocker"), limit=220)
                    or BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
                    _clean_text(recovery_blocker.get("blocker_detail"), limit=900)
                    or "Recovery model-assisted planning failed closed.",
                )
            source_challenge_recovery = _run_source_challenge_recovery(
                root=root,
                run_dir=run_dir,
                retained_root=retained_root,
                run_id=run_id,
                relation_plan=relation_plan,
                acquisition_plan=acquisition_plan,
                first_stage_counts=counts,
                first_stage_semantic_payload=semantic_payload,
                source_obligation_recovery_authorization=(
                    source_obligation_authorization
                ),
                recovery_model_planning_packet=recovery_model_planning_packet,
                provider_runner=provider_runner,
                fetch_read_runner=fetch_read_runner or fetch_public_url_once,
                confirm_live_source_challenge_recovery=(
                    confirm_live_source_challenge_recovery
                ),
            )
            counts.update(
                _source_challenge_recovery_counts(source_challenge_recovery)
            )
            _enforce_caps(counts)
            source_obligation_authorization = (
                _build_source_obligation_recovery_authorization(
                    run_kernel=source_obligation_run_kernel,
                    relation_plan=relation_plan,
                    acquisition_plan=acquisition_plan,
                    counts=counts,
                    dprime_status=_safe_mapping(
                        semantic_payload.get("dprime_status")
                    ),
                    semantic_payload=semantic_payload,
                    source_challenge_recovery=source_challenge_recovery,
                    recovery_confirmation_authorized=(
                        confirm_live_source_challenge_recovery
                    ),
                )
            )
            packet = _packet_from_semantic_status(
                relation_plan=relation_plan,
                run_id=run_id,
                retained_root=retained_root,
                counts=counts,
                acquisition_plan=acquisition_plan,
                disambiguation_record=disambiguation_record,
                semantic_payload=semantic_payload,
                status_decision=str(semantic_status.decision),
                confirm_live_dprime_review=confirm_live_dprime_review,
                confirm_live_source_challenge_recovery=(
                    confirm_live_source_challenge_recovery
                ),
                source_obligation_recovery_authorization=(
                    source_obligation_authorization
                ),
                source_challenge_recovery=source_challenge_recovery,
                initial_model_planning_packet=initial_model_planning_packet,
                recovery_model_planning_packet=recovery_model_planning_packet,
                require_model_assisted_planning=require_model_assisted_planning,
                entrypoint_metadata=entrypoint_metadata,
            )
    except GenericQueryRelationPlanningError as exc:
        packet = _blocked_packet(
            blocker=exc.blocker_code,
            detail=exc.detail,
            query_retained=False,
            relation_plan=None,
            run_id=run_id,
            retained_root=None,
            counts=counts,
            acquisition_plan=acquisition_plan,
            disambiguation_record=disambiguation_record,
            caps_exhausted=False,
            confirm_live_dprime_review=confirm_live_dprime_review,
            confirm_live_source_challenge_recovery=(
                confirm_live_source_challenge_recovery
            ),
            source_obligation_recovery_authorization=(
                source_obligation_authorization
            ),
            source_challenge_recovery=source_challenge_recovery,
            semantic_payload={},
            hard_exclusion_category=exc.hard_exclusion_category,
            initial_model_planning_packet=initial_model_planning_packet,
            recovery_model_planning_packet=recovery_model_planning_packet,
            require_model_assisted_planning=require_model_assisted_planning,
            entrypoint_metadata=entrypoint_metadata,
        )
    except GenericSingleRelationLiveDogfoodRunError as exc:
        packet = _blocked_packet(
            blocker=exc.blocker,
            detail=exc.detail,
            query_retained=relation_plan is not None,
            relation_plan=relation_plan,
            run_id=run_id,
            retained_root=retained_root if retained_root.exists() else None,
            counts=counts,
            acquisition_plan=acquisition_plan,
            disambiguation_record=disambiguation_record,
            caps_exhausted=exc.caps_exhausted,
            confirm_live_dprime_review=confirm_live_dprime_review,
            confirm_live_source_challenge_recovery=(
                confirm_live_source_challenge_recovery
            ),
            source_obligation_recovery_authorization=(
                source_obligation_authorization
            ),
            source_challenge_recovery=source_challenge_recovery,
            semantic_payload=semantic_payload,
            hard_exclusion_category=None,
            initial_model_planning_packet=initial_model_planning_packet,
            recovery_model_planning_packet=recovery_model_planning_packet,
            require_model_assisted_planning=require_model_assisted_planning,
            entrypoint_metadata=entrypoint_metadata,
        )

    if entrypoint_metadata["entrypoint_kind"] == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND:
        packet["review_report_json_path"] = _display_path(review_report_json_path)
        packet["review_report_markdown_path"] = _display_path(review_report_md_path)
    validate_generic_single_relation_live_dogfood_packet(packet)
    _write_json(packet_path, packet)
    if entrypoint_metadata["entrypoint_kind"] == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND:
        _write_current_source_record_single_fact_review_report(
            packet=packet,
            json_path=review_report_json_path,
            markdown_path=review_report_md_path,
        )
    output = format_generic_single_relation_live_dogfood_output(
        packet,
        packet_path=packet_path,
    )
    return MvpFriendOutputResult(
        decision=str(packet["decision"]),
        output=output,
        packet=packet,
        packet_path=packet_path,
        retained_artifact_root=retained_root if retained_root.exists() else None,
    )


def fetch_public_url_once(url: str) -> GenericLiveFetchReadResult:
    """Fetch one public URL and retain only bounded sanitized readable text."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read requires an http(s) URL.",
            fetch_status_class=FETCH_READ_UNKNOWN,
            fetch_content_type=FETCH_READ_UNKNOWN,
            fetch_readable_content_type=FETCH_READ_UNKNOWN,
            fetch_readable_text_obtained=False,
            fetch_failure_category=FETCH_READ_FAILURE_INVALID_URL,
        )
    redirect_handler = _RedirectLimiter()
    opener = build_opener(redirect_handler)
    request = _public_web_fetch_read_request(url)
    try:
        with opener.open(request, timeout=20) as response:
            body = response.read(MAX_FETCHED_BYTES + 1)
            final_url = response.geturl()
            status_code = getattr(response, "status", None)
            content_type_header = response.headers.get("content-type", "")
    except HTTPError as exc:
        status_class = _status_class(exc.code)
        content_type_header = exc.headers.get("content-type", "") if exc.headers else ""
        content_type = (
            _content_type_or_unknown(content_type_header)
            if content_type_header
            else FETCH_READ_UNKNOWN
        )
        final_url = _http_error_final_url(exc) or url
        redirect_chain_digest = (
            _digest_json(redirect_handler.redirects)
            if redirect_handler.redirects
            else None
        )
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            f"fetch/read HTTP error status class {status_class}.",
            fetch_status_class=status_class,
            fetch_content_type=content_type,
            fetch_readable_content_type=_readable_content_type_value(content_type),
            fetch_readable_text_obtained=False,
            fetch_failure_category=_failure_category_for_status_class(status_class),
            fetch_final_url=final_url,
            fetch_status_code=exc.code,
            fetch_redirect_count=len(redirect_handler.redirects),
            fetch_redirect_chain_digest=redirect_chain_digest,
        ) from None
    except URLError as exc:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            f"fetch/read URL error: {_clean_text(exc.reason, limit=120) or 'unavailable'}.",
            fetch_status_class=FETCH_READ_UNKNOWN,
            fetch_content_type=FETCH_READ_UNKNOWN,
            fetch_readable_content_type=FETCH_READ_UNKNOWN,
            fetch_readable_text_obtained=False,
            fetch_failure_category=FETCH_READ_FAILURE_EXCEPTION,
        ) from None
    if len(body) > MAX_FETCHED_BYTES:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED,
            "fetch/read byte cap exhausted.",
            caps_exhausted=True,
        )
    content_type, charset = _content_type_and_charset(content_type_header)
    if content_type not in FETCH_READ_READABLE_CONTENT_TYPES:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read did not receive a readable text/html or text/plain response.",
            fetch_status_class=_status_class(status_code),
            fetch_content_type=content_type,
            fetch_readable_content_type=False,
            fetch_readable_text_obtained=False,
            fetch_failure_category=FETCH_READ_FAILURE_UNSUPPORTED_CONTENT_TYPE,
        )
    readable_text, content_title = _extract_readable_text(
        body,
        content_type=content_type,
        charset=charset,
    )
    if not readable_text:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read produced no sanitized readable text.",
            fetch_status_class=_status_class(status_code),
            fetch_content_type=content_type,
            fetch_readable_content_type=True,
            fetch_readable_text_obtained=False,
            fetch_failure_category=FETCH_READ_FAILURE_NO_READABLE_TEXT,
        )
    final_domain = urlparse(final_url).netloc.lower()
    return GenericLiveFetchReadResult(
        attempted_url=url,
        final_url=final_url,
        final_domain=final_domain,
        status_code=status_code,
        status_class=_status_class(status_code),
        content_type=content_type,
        fetched_byte_count=len(body),
        sanitized_text=readable_text,
        content_title=content_title,
        redirect_count=len(redirect_handler.redirects),
        redirect_chain_digest=(
            _digest_json(redirect_handler.redirects)
            if redirect_handler.redirects
            else None
        ),
        retrieved_or_observed_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
    )


def _public_web_fetch_read_request(url: str) -> Request:
    return Request(
        url,
        headers=_public_web_fetch_read_request_headers(),
        method="GET",
    )


def _public_web_fetch_read_request_headers() -> dict[str, str]:
    return {
        "User-Agent": FETCH_READ_PUBLIC_WEB_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
    }


def _http_error_final_url(exc: HTTPError) -> str | None:
    try:
        value = exc.geturl()
    except (AttributeError, ValueError):
        value = getattr(exc, "url", None)
    return _clean_text(value, limit=700)


def validate_generic_single_relation_live_dogfood_packet(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the generic live dogfood packet without opening closed surfaces."""

    safe = _safe_mapping(packet)
    if safe.get("schema_version") != SCHEMA_VERSION:
        _blocked_output_hygiene("generic live packet schema mismatch.")
    if safe.get("phase_name") != PHASE_NAME:
        _blocked_output_hygiene("generic live packet phase mismatch.")
    if safe.get("mode") != MODE:
        _blocked_output_hygiene("generic live packet mode mismatch.")
    _validate_entrypoint_metadata(safe)
    product_entrypoint = safe.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    product_answer_pass = product_entrypoint and safe.get("decision") == PASS_DECISION
    product_answer_path_consumed = product_entrypoint and (
        safe.get("fap_author_opened") is True
    )
    product_answer_open_flags = {
        "final_answer_packet_created",
        "author_prose_created",
        "citation_source_display_created",
        "fap_opened",
        "author_opened",
        "fap_author_opened",
    }
    for key, expected in RAW_FALSE_FLAGS.items():
        if safe.get(key) is not expected:
            _blocked_output_hygiene(f"generic live packet must keep {key}=false.")
    for key, expected in CLOSED_FALSE_FLAGS.items():
        if product_answer_path_consumed and key in product_answer_open_flags:
            if safe.get(key) is not True:
                _blocked_output_hygiene(
                    f"product answer-path packet must set {key}=true."
                )
            continue
        if safe.get(key) is not expected:
            _blocked_output_hygiene(f"generic live packet must keep {key}=false.")
    if safe.get("model_assisted_planning_raw_private_retention_false") is not True:
        _blocked_output_hygiene(
            "model-assisted planning raw/private retention guard failed."
        )
    if safe.get("model_assisted_planning_closed_surfaces_preserved") is not True:
        _blocked_output_hygiene(
            "model-assisted planning closed-surface guard failed."
        )
    if _bounded_int(safe.get("live_runs_attempted")) > MAX_LIVE_RUNS:
        _blocked_cap("live run cap exceeded.")
    if _bounded_int(safe.get("query_plans_consumed")) > MAX_QUERY_PLANS_CONSUMED:
        _blocked_cap("query plan consumption cap exceeded.")
    if _bounded_int(safe.get("initial_model_assisted_planning_calls_attempted")) > (
        MAX_INITIAL_FAST_MODEL_PLANNING_CALLS
    ):
        _blocked_cap("initial FastModel planning call cap exceeded.")
    if _bounded_int(safe.get("recovery_model_assisted_planning_calls_attempted")) > (
        MAX_RECOVERY_FAST_MODEL_PLANNING_CALLS
    ):
        _blocked_cap("recovery FastModel planning call cap exceeded.")
    if _bounded_int(safe.get("fast_planner_model_calls_attempted")) > (
        MAX_FAST_MODEL_PLANNING_CALLS
    ):
        _blocked_cap("FastModel planning call cap exceeded.")
    if _bounded_int(safe.get("provider_calls_attempted")) > MAX_PROVIDER_SEARCH_CALLS:
        _blocked_cap("provider/search call cap exceeded.")
    if _bounded_int(safe.get("extraction_provider_calls_attempted")) > (
        MAX_PROVIDER_SEARCH_CALLS
    ):
        _blocked_cap("extraction provider/search call cap exceeded.")
    if _bounded_int(safe.get("source_challenge_recovery_provider_calls_attempted")) > (
        MAX_SOURCE_CHALLENGE_RECOVERY_PROVIDER_CALLS
    ):
        _blocked_cap("source-challenge recovery provider/search call cap exceeded.")
    if _bounded_int(safe.get("serper_scout_calls_attempted")) > MAX_SERPER_SCOUT_CALLS:
        _blocked_cap("Serper scout call cap exceeded.")
    if _bounded_int(safe.get("provider_results_returned")) > MAX_PROVIDER_RESULTS:
        _blocked_cap("provider result cap exceeded.")
    if _bounded_int(safe.get("fetch_read_attempts")) > MAX_FETCH_READ_ATTEMPTS:
        _blocked_cap("fetch/read attempt cap exceeded.")
    if _bounded_int(safe.get("evidence_ledger_admissions")) > (
        MAX_EVIDENCE_LEDGER_ADMISSIONS
    ):
        _blocked_cap("EvidenceLedger admission cap exceeded.")
    if _bounded_int(safe.get("dprime_model_review_calls_attempted")) > (
        MAX_DPRIME_MODEL_REVIEW_CALLS
    ):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED,
            "D-prime model-review cap exceeded.",
            caps_exhausted=True,
        )
    if _bounded_int(safe.get("followup_loop_count")) > MAX_FOLLOWUP_LOOPS:
        _blocked_cap("follow-up loop cap exceeded.")
    if safe.get("relation_plan_consumed") is True:
        if safe.get("supported_query_class_id") != MVP_SUPPORTED_QUERY_CLASS_ID:
            _blocked_output_hygiene("supported query class id missing.")
        if not _clean_text(safe.get("relation_plan_id"), limit=320):
            _blocked_output_hygiene("relation plan id missing.")
        if not _clean_text(safe.get("component_id"), limit=320):
            _blocked_output_hygiene("component id missing.")
        if not _clean_text(safe.get("source_obligation_id"), limit=320):
            _blocked_output_hygiene("source-obligation id missing.")
        if not _clean_text(safe.get("search_requirement_id"), limit=320):
            _blocked_output_hygiene("search requirement id missing.")
        dprime = _safe_mapping(safe.get("relation_plan_dprime_relation_intake_candidate"))
        if dprime.get("relation_plan_id") != safe.get("relation_plan_id"):
            _blocked_output_hygiene("D-prime relation-intake candidate is not plan-bound.")
        if dprime.get("component_id") != safe.get("component_id"):
            _blocked_output_hygiene("D-prime relation-intake component mismatch.")
    else:
        if safe.get("query") != "unsupported query (not retained)":
            _blocked_output_hygiene("unsupported query text retained.")
        if safe.get("unsupported_query_retained") is not False:
            _blocked_output_hygiene("unsupported query retention flag invalid.")
        for count_key in (
            "provider_calls_attempted",
            "provider_calls_completed",
            "extraction_provider_calls_attempted",
            "extraction_provider_calls_completed",
            "serper_scout_calls_attempted",
            "serper_scout_calls_completed",
            "fast_planner_model_calls_attempted",
            "fast_planner_model_calls_completed",
            "initial_model_assisted_planning_calls_attempted",
            "initial_model_assisted_planning_calls_completed",
            "recovery_model_assisted_planning_calls_attempted",
            "recovery_model_assisted_planning_calls_completed",
            "fetch_read_attempts",
            "fetch_read_completed",
            "dprime_model_review_calls_attempted",
            "dprime_model_review_calls_completed",
        ):
            if _bounded_int(safe.get(count_key)) != 0:
                _blocked_output_hygiene("unsupported query made live/model calls.")
    if not product_entrypoint:
        if safe.get("answer_text_present") is True:
            _blocked_output_hygiene("generic live packet must not expose answer text.")
        if _clean_text(safe.get("product_answer_text"), limit=20):
            _blocked_output_hygiene(
                "generic live packet must not expose product answer text."
            )
        if _safe_sequence(safe.get("source_display_entries")):
            _blocked_output_hygiene(
                "generic live packet must not create source display entries."
            )
    elif product_answer_pass:
        if not _clean_text(safe.get("product_answer_text"), limit=4_000):
            _blocked_output_hygiene("product PASS requires product answer text.")
        lineage = _safe_mapping(
            safe.get("selected_current_value_to_fap_claim_lineage")
        )
        if lineage.get("contract_accountable") is not True:
            _blocked_output_hygiene("product PASS requires contract-accountable claim lineage.")
    _validate_source_readiness_gateway(safe)
    _validate_dprime_authority_integration(safe)
    _validate_source_citation_display_boundary(safe)
    _validate_fetch_read_observability(safe)
    _validate_analyst_workbench_surface(safe)
    _validate_workbench_gap_reentry_ref(safe)
    _reject_forbidden_material(safe, context="generic live dogfood packet")
    return safe


def _validate_source_readiness_gateway(packet: Mapping[str, Any]) -> None:
    gateway = _safe_mapping(packet.get("source_readiness_gateway"))
    if not gateway:
        _blocked_output_hygiene("source/readiness gateway section missing.")
    if gateway.get("schema_version") != SOURCE_READINESS_GATEWAY_SCHEMA_VERSION:
        _blocked_output_hygiene("source/readiness gateway schema mismatch.")
    if gateway.get("raw_private_retention_flags") != RAW_FALSE_FLAGS:
        _blocked_output_hygiene("source/readiness gateway raw/private posture invalid.")
    non_claims = _safe_mapping(gateway.get("explicit_non_claims"))
    if non_claims != SOURCE_READINESS_GATEWAY_NON_CLAIMS:
        _blocked_output_hygiene("source/readiness gateway non-claims invalid.")
    for key, expected in SOURCE_READINESS_GATEWAY_NON_CLAIMS.items():
        if gateway.get(key) is not None and gateway.get(key) is not expected:
            _blocked_output_hygiene(
                f"source/readiness gateway must keep {key}=false."
            )
    for key in (
        "final_answer_prose_created",
        "source_display_entries_created",
        "source_obligation_satisfaction_used_for_display",
        "citation_eligibility_used_for_display",
        "product_correctness_claimed",
    ):
        if gateway.get(key) is not False:
            _blocked_output_hygiene(f"source/readiness gateway {key} invalid.")
    status = gateway.get("status")
    if status not in {"ready", "blocked", "not_reached"}:
        _blocked_output_hygiene("source/readiness gateway status invalid.")
    if packet.get("decision") == PASS_DECISION:
        if status != "ready":
            _blocked_output_hygiene("PASS packet requires a ready source/readiness gateway.")
        if not _clean_text(gateway.get("selected_current_value_text"), limit=700):
            _blocked_output_hygiene("ready gateway requires selected current value text.")
        source = _safe_mapping(gateway.get("selected_source_ref"))
        if not _clean_text(source.get("url"), limit=700):
            _blocked_output_hygiene("ready gateway requires selected source URL.")
        window = _safe_mapping(gateway.get("selected_window_ref"))
        if not _clean_text(window.get("selected_window_digest"), limit=128):
            _blocked_output_hygiene("ready gateway requires selected window digest.")
    elif status == "ready":
        integration = _safe_mapping(
            packet.get("single_relation_dprime_authority_integration")
        )
        if not (
            (
                packet.get("decision")
                == BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD
                and integration.get("status") == "blocked"
            )
            or (
                packet.get("decision")
                == BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED
                and integration.get("status") == "consumed"
            )
            or (
                packet.get("decision")
                in {
                    BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED,
                    BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING,
                    BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE,
                    *EXISTING_DPRIME_ANSWER_PATH_BLOCKERS,
                }
                and integration.get("status") == "consumed"
            )
        ) or integration.get("gateway_treated_as_authority") is not False:
            _blocked_output_hygiene("blocked packet must not carry ready gateway status.")


def _validate_consumed_dprime_authority_integration(
    integration: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> None:
    allowed_decisions = {
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED,
        BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED,
        BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING,
        BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE,
        PASS_DECISION,
        *EXISTING_DPRIME_ANSWER_PATH_BLOCKERS,
    }
    if integration.get("blocker_code") not in allowed_decisions:
        _blocked_output_hygiene("consumed D-prime stop point blocker invalid.")
    if packet.get("decision") not in allowed_decisions:
        _blocked_output_hygiene("consumed D-prime stop point must own decision.")
    if integration.get("existing_dprime_authority_reused") is not True:
        _blocked_output_hygiene("consumed stop point must reuse existing authority.")
    if integration.get("dprime_source_citation_authority_enabled") is not True:
        _blocked_output_hygiene("source/citation stop point was not requested.")
    product_entrypoint = packet.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    if product_entrypoint:
        if integration.get("dprime_single_lane_answer_path_enabled") is not True:
            _blocked_output_hygiene("product entrypoint did not request answer path.")
        if (
            integration.get("generic_dogfood_single_lane_answer_path_kept_disabled")
            is not False
        ):
            _blocked_output_hygiene("product entrypoint marked answer path disabled.")
    else:
        if integration.get("dprime_single_lane_answer_path_enabled") is not False:
            _blocked_output_hygiene("single-lane answer path must remain disabled.")
        if (
            integration.get("generic_dogfood_single_lane_answer_path_kept_disabled")
            is not True
        ):
            _blocked_output_hygiene("generic dogfood opened the answer path.")
    if integration.get("source_obligation_authority_consumed") is not True:
        _blocked_output_hygiene("source-obligation authority was not consumed.")
    if integration.get("citation_source_handoff_authority_consumed") is not True:
        _blocked_output_hygiene("citation-source handoff authority was not consumed.")
    if integration.get("single_relation_source_obligation_ready") is not True:
        _blocked_output_hygiene("source-obligation readiness alias invalid.")
    if integration.get("single_relation_citation_handoff_ready") is not True:
        _blocked_output_hygiene("citation handoff readiness alias invalid.")
    if integration.get("source_readiness_gateway_is_authority") is not False:
        _blocked_output_hygiene("source/readiness gateway became authority.")
    if (
        integration.get("source_citation_authority_refs_are_dprime_runtime_refs")
        is not True
    ):
        _blocked_output_hygiene("source/citation authority refs are not D-prime refs.")
    source_ref = _safe_mapping(integration.get("source_obligation_authority_ref"))
    citation_ref = _safe_mapping(
        integration.get("citation_source_handoff_authority_ref")
    )
    if source_ref.get("owner") != "RunKernel.DPrimeSourceObligationAuthority":
        _blocked_output_hygiene("source-obligation authority owner invalid.")
    if citation_ref.get("owner") != "RunKernel.DPrimeCitationSourceHandoffAuthority":
        _blocked_output_hygiene("citation-source handoff authority owner invalid.")
    if source_ref.get("authority_consumed") is not True:
        _blocked_output_hygiene("source-obligation authority ref not consumed.")
    if citation_ref.get("citation_source_handoff_consumed") is not True:
        _blocked_output_hygiene("citation handoff authority ref not consumed.")
    if (
        packet.get("single_relation_source_obligation_ready") is not True
        or packet.get("single_relation_citation_handoff_ready") is not True
    ):
        _blocked_output_hygiene("packet readiness aliases did not reflect authority.")
    for key in (
        "source_obligation_satisfied",
        "citation_eligible",
        "source_authority_finalized",
        "product_correctness_claimed",
    ):
        if integration.get(key) is not False:
            _blocked_output_hygiene(f"D-prime stop point {key} invalid.")
    answer_path_created_keys = (
        "final_answer_packet_created",
        "author_prose_created",
        "author_answer_created",
        "citation_source_display_created",
        "final_answer_prose_created",
        "fap_invoked",
        "author_invoked",
    )
    product_answer_path_consumed = product_entrypoint and (
        packet.get("fap_author_opened") is True
    )
    if product_answer_path_consumed:
        for key in answer_path_created_keys:
            if integration.get(key) is not True:
                _blocked_output_hygiene(f"product D-prime answer path {key} invalid.")
    else:
        for key in answer_path_created_keys:
            if integration.get(key) is not False:
                _blocked_output_hygiene(f"D-prime stop point {key} invalid.")
    if integration.get("citation_rendering_invoked") is not False:
        _blocked_output_hygiene("generic citation rendering must remain closed.")


def _validate_entrypoint_metadata(packet: Mapping[str, Any]) -> None:
    flag = packet.get("command_flag")
    confirmation_flag = packet.get("confirmation_flag")
    surface = packet.get("entrypoint_surface")
    kind = packet.get("entrypoint_kind")
    alias = packet.get("diagnostic_dogfood_alias")
    supported_query_class = packet.get("supported_query_class")
    if kind == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND:
        if flag != MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG:
            _blocked_output_hygiene("product entrypoint command flag mismatch.")
        if confirmation_flag != CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG:
            _blocked_output_hygiene("product entrypoint confirmation flag mismatch.")
        if surface != PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE:
            _blocked_output_hygiene("product entrypoint surface mismatch.")
        if alias is not False:
            _blocked_output_hygiene("product entrypoint cannot be dogfood alias.")
        if supported_query_class != PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS:
            _blocked_output_hygiene("product entrypoint query class mismatch.")
        return
    if kind != DOGFOOD_ENTRYPOINT_KIND:
        _blocked_output_hygiene("generic live entrypoint kind invalid.")
    if flag != MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG:
        _blocked_output_hygiene("dogfood entrypoint command flag mismatch.")
    if confirmation_flag != CONFIRM_LIVE_DOGFOOD_FLAG:
        _blocked_output_hygiene("dogfood entrypoint confirmation flag mismatch.")
    if surface != DOGFOOD_ENTRYPOINT_SURFACE:
        _blocked_output_hygiene("dogfood entrypoint surface mismatch.")
    if alias is not True:
        _blocked_output_hygiene("dogfood entrypoint alias flag mismatch.")
    if supported_query_class != DOGFOOD_SUPPORTED_QUERY_CLASS:
        _blocked_output_hygiene("dogfood entrypoint query class mismatch.")


def _validate_dprime_authority_integration(packet: Mapping[str, Any]) -> None:
    integration = _safe_mapping(
        packet.get("single_relation_dprime_authority_integration")
    )
    product_entrypoint = packet.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    if not integration:
        _blocked_output_hygiene("D-prime authority integration section missing.")
    if integration.get("schema_version") != DPRIME_AUTHORITY_INTEGRATION_SCHEMA_VERSION:
        _blocked_output_hygiene("D-prime authority integration schema mismatch.")
    if integration.get("status") not in {"blocked", "not_reached", "consumed"}:
        _blocked_output_hygiene("D-prime authority integration status invalid.")
    if integration.get("existing_dprime_authority_referenced") is not True:
        _blocked_output_hygiene("existing D-prime authority reference missing.")
    if (
        integration.get("existing_dprime_source_obligation_citation_authority_exists")
        is not True
    ):
        _blocked_output_hygiene("existing D-prime source/citation authority not named.")
    if (
        integration.get("status") == "consumed"
        and integration.get("existing_dprime_authority_reused") is not True
    ):
        _blocked_output_hygiene("generic dogfood did not claim authority reuse.")
    if (
        integration.get("status") != "consumed"
        and integration.get("existing_dprime_authority_reused") is not False
    ):
        _blocked_output_hygiene("generic dogfood must not claim authority reuse yet.")
    if integration.get("gateway_treated_as_authority") is not False:
        _blocked_output_hygiene("gateway must not be treated as authority.")
    if integration.get("dprime_support_slice_treated_as_readiness") is not False:
        _blocked_output_hygiene("D-prime support slice must not satisfy readiness.")
    if integration.get("dprime_downstream_authority_enabled") is not False:
        _blocked_output_hygiene("generic dogfood must keep downstream D-prime disabled.")
    product_answer_path_consumed = product_entrypoint and (
        packet.get("fap_author_opened") is True
    )
    false_unless_consumed = (
        "single_relation_source_obligation_ready",
        "single_relation_citation_handoff_ready",
        "downstream_dprime_authority_invoked",
    )
    for key in (
        "source_obligation_satisfied",
        "citation_eligible",
        "source_authority_finalized",
        "product_correctness_claimed",
    ):
        if integration.get(key) is not False:
            _blocked_output_hygiene(f"D-prime authority integration {key} invalid.")
    for key in (
        "final_answer_packet_created",
        "author_prose_created",
        "author_answer_created",
        "citation_source_display_created",
        "final_answer_prose_created",
        "fap_invoked",
        "author_invoked",
        "citation_rendering_invoked",
    ):
        if (
            not product_answer_path_consumed
            and integration.get(key) is not False
        ):
            _blocked_output_hygiene(f"D-prime authority integration {key} invalid.")
    if integration.get("status") != "consumed":
        for key in false_unless_consumed:
            if integration.get(key) is not False:
                _blocked_output_hygiene(
                    f"D-prime authority integration {key} invalid."
                )
    if (
        packet.get("source_obligation_citation_readiness_status")
        != integration.get("status")
    ):
        _blocked_output_hygiene("readiness status alias mismatch.")
    if (
        packet.get("source_obligation_citation_readiness_blocker")
        != integration.get("blocker_code")
    ):
        _blocked_output_hygiene("readiness blocker alias mismatch.")
    if packet.get("dprime_source_citation_stoppoint_status") != integration.get(
        "dprime_source_citation_stoppoint_status"
    ):
        _blocked_output_hygiene("source/citation stop-point status alias mismatch.")
    if packet.get("dprime_source_citation_stoppoint_blocker") != integration.get(
        "dprime_source_citation_stoppoint_blocker"
    ):
        _blocked_output_hygiene("source/citation stop-point blocker alias mismatch.")
    if packet.get("source_obligation_authority_consumed") is not (
        integration.get("source_obligation_authority_consumed") is True
    ):
        _blocked_output_hygiene("source-obligation consumed alias mismatch.")
    if packet.get("citation_source_handoff_authority_consumed") is not (
        integration.get("citation_source_handoff_authority_consumed") is True
    ):
        _blocked_output_hygiene("citation-source handoff consumed alias mismatch.")
    if integration.get("status") == "blocked":
        if (
            integration.get("blocker_code")
            != BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD
        ):
            _blocked_output_hygiene("D-prime authority integration blocker invalid.")
        if (
            packet.get("decision")
            != BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD
        ):
            _blocked_output_hygiene("blocked authority integration must own decision.")
        if integration.get("gateway_display_present") is not True:
            _blocked_output_hygiene("blocked authority integration requires gateway display.")
        if integration.get("dprime_support_slice_present") is not True:
            _blocked_output_hygiene("blocked authority integration requires D-prime slice.")
    elif integration.get("status") == "consumed":
        _validate_consumed_dprime_authority_integration(integration, packet)
    elif packet.get("decision") == PASS_DECISION:
        _blocked_output_hygiene("PASS requires D-prime authority integration readiness.")


def _validate_source_citation_display_boundary(packet: Mapping[str, Any]) -> None:
    boundary = _safe_mapping(packet.get("source_citation_display_boundary"))
    if not boundary:
        _blocked_output_hygiene("source/citation display boundary section missing.")
    if boundary.get("schema_version") != SOURCE_CITATION_DISPLAY_BOUNDARY_SCHEMA_VERSION:
        _blocked_output_hygiene("source/citation display boundary schema mismatch.")
    if boundary.get("status") not in {"created", "not_reached"}:
        _blocked_output_hygiene("source/citation display boundary status invalid.")
    if boundary.get("raw_private_retention_flags") != RAW_FALSE_FLAGS:
        _blocked_output_hygiene("source/citation display boundary raw/private posture invalid.")
    if (
        _safe_mapping(boundary.get("explicit_non_claims"))
        != SOURCE_CITATION_DISPLAY_BOUNDARY_NON_CLAIMS
    ):
        _blocked_output_hygiene("source/citation display boundary non-claims invalid.")
    for key, expected in SOURCE_CITATION_DISPLAY_BOUNDARY_NON_CLAIMS.items():
        if boundary.get(key) is not expected:
            _blocked_output_hygiene(
                f"source/citation display boundary must keep {key}=false."
            )
    entries = [
        _safe_mapping(item)
        for item in _safe_sequence(boundary.get("source_citation_display_entries"))
    ]
    if packet.get("source_citation_display_boundary_status") != boundary.get("status"):
        _blocked_output_hygiene("source/citation display boundary status alias mismatch.")
    if packet.get("source_citation_display_boundary_blocker") != boundary.get(
        "blocker_code"
    ):
        _blocked_output_hygiene("source/citation display boundary blocker alias mismatch.")
    if list(_safe_sequence(packet.get("source_citation_display_entries"))) != entries:
        _blocked_output_hygiene("source/citation display entries alias mismatch.")
    if packet.get("source_citation_display_entries_created") is not (
        boundary.get("source_citation_display_entries_created") is True
    ):
        _blocked_output_hygiene("source/citation display entries-created alias mismatch.")
    if packet.get("source_citation_display_derived_from_gateway_only") is not False:
        _blocked_output_hygiene("source/citation display cannot be gateway-only.")
    if packet.get("final_citation_rendering_created") is not False:
        _blocked_output_hygiene("final citation rendering must remain closed.")
    if boundary.get("status") == "created":
        _validate_created_source_citation_display_boundary(boundary, packet, entries)
    else:
        if entries:
            _blocked_output_hygiene("not-reached display boundary carried entries.")
        if boundary.get("source_citation_display_entries_created") is not False:
            _blocked_output_hygiene("not-reached display boundary claimed entries.")
        if boundary.get("derived_from_gateway_only") is not False:
            _blocked_output_hygiene("not-reached display boundary became gateway-only.")


def _validate_created_source_citation_display_boundary(
    boundary: Mapping[str, Any],
    packet: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
) -> None:
    allowed_decisions = {
        BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED,
        BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING,
        BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE,
        PASS_DECISION,
        *EXISTING_DPRIME_ANSWER_PATH_BLOCKERS,
    }
    if packet.get("decision") not in allowed_decisions:
        _blocked_output_hygiene(
            "created display boundary must move to an answer-path decision."
        )
    if boundary.get("blocker_code") not in allowed_decisions:
        _blocked_output_hygiene("created display boundary blocker invalid.")
    if boundary.get("authority_source") not in {
        "core.dprime_source_obligation_citation_authority_runtime",
        "core.dprime_single_lane_answer_path_runtime",
    }:
        _blocked_output_hygiene("display boundary authority source invalid.")
    if boundary.get("derived_from_dprime_authority") is not True:
        _blocked_output_hygiene("display boundary is not D-prime authority-backed.")
    if boundary.get("derived_from_gateway_only") is not False:
        _blocked_output_hygiene("display boundary was derived from gateway-only state.")
    if boundary.get("gateway_treated_as_authority") is not False:
        _blocked_output_hygiene("display boundary treated gateway as authority.")
    if boundary.get("source_obligation_authority_consumed") is not True:
        _blocked_output_hygiene("display boundary lacks source-obligation authority.")
    if boundary.get("citation_source_handoff_authority_consumed") is not True:
        _blocked_output_hygiene("display boundary lacks citation-source handoff authority.")
    if boundary.get("source_obligation_authority_ref_owner") != (
        "RunKernel.DPrimeSourceObligationAuthority"
    ):
        _blocked_output_hygiene("display boundary source authority owner invalid.")
    if boundary.get("citation_source_handoff_authority_ref_owner") != (
        "RunKernel.DPrimeCitationSourceHandoffAuthority"
    ):
        _blocked_output_hygiene("display boundary citation handoff owner invalid.")
    if boundary.get("source_citation_authority_refs_are_dprime_runtime_refs") is not True:
        _blocked_output_hygiene("display boundary refs are not D-prime runtime refs.")
    source_ref = _safe_mapping(boundary.get("source_obligation_authority_ref"))
    citation_ref = _safe_mapping(boundary.get("citation_source_handoff_authority_ref"))
    if source_ref.get("authority_consumed") is not True:
        _blocked_output_hygiene("display boundary source authority ref not consumed.")
    if citation_ref.get("citation_source_handoff_consumed") is not True:
        _blocked_output_hygiene("display boundary citation handoff ref not consumed.")
    if not entries:
        _blocked_output_hygiene("created display boundary requires entries.")
    for entry in entries:
        if entry.get("derived_from_dprime_authority") is not True:
            _blocked_output_hygiene("display entry is not D-prime authority-backed.")
        if entry.get("derived_from_gateway_only") is not False:
            _blocked_output_hygiene("display entry derived from gateway-only state.")
        for key in (
            "citation_rendering_created",
            "final_answer_prose_created",
            "product_correctness_claimed",
        ):
            if entry.get(key) is not False:
                _blocked_output_hygiene(f"display entry {key} invalid.")
        if not _clean_text(entry.get("citation_source_handoff_digest"), limit=128):
            _blocked_output_hygiene("display entry lacks citation handoff digest.")
        if not _clean_text(entry.get("source_obligation_authority_digest"), limit=128):
            _blocked_output_hygiene("display entry lacks source authority digest.")
        if not (
            _clean_text(entry.get("source_url"), limit=700)
            or _clean_text(entry.get("source_domain"), limit=160)
            or _clean_text(entry.get("source_id"), limit=320)
        ):
            _blocked_output_hygiene("display entry lacks safe source identity.")


def _validate_fetch_read_observability(packet: Mapping[str, Any]) -> None:
    for key in (
        "candidate_diagnostics_observability_only",
        "provider_snippets_used_as_evidence",
        "candidate_diagnostics_satisfy_source_obligations",
        "fetch_read_failure_metadata_citation_eligible",
        "fetch_read_failure_metadata_satisfies_source_obligations",
        "official_pdf_table_read_support_raw_content_retained",
        "official_pdf_table_read_support_creates_source_authority",
        "official_pdf_table_read_support_satisfies_source_obligation",
        "official_pdf_table_read_support_citation_eligible",
        "official_pdf_table_read_support_claims_correctness",
        "official_pdf_table_read_support_adds_dependency",
        "official_pdf_table_read_support_uses_ocr",
        "official_pdf_table_read_support_uses_browser_automation",
        "pdf_content_type_support_opened",
        "pdf_parsing_opened",
        "candidate_ranking_policy_changed",
        "candidate_selection_uses_provider_snippet",
        "candidate_selection_created_source_authority",
        "candidate_selection_satisfies_source_obligation",
        "candidate_selection_citation_eligible",
        "candidate_selection_claims_correctness",
        "candidate_selection_global_ranking_policy_created",
        "candidate_selection_source_authority_policy_created",
        "candidate_selection_approved_domain_list_created",
        "candidate_selection_retrieval_filtering_layer_created",
        "http_source_survival_access_control_bypass_opened",
        "http_source_survival_login_session_handling_opened",
        "http_source_survival_captcha_handling_opened",
        "http_source_survival_javascript_browser_automation_opened",
        "http_source_survival_proxy_rotation_opened",
        "http_source_survival_referer_spoofing_opened",
        "http_source_survival_domain_specific_header_hacks_opened",
        "http_source_survival_domain_specific_url_fallback_opened",
        "http_source_survival_canonical_url_transformation_opened",
    ):
        expected = key == "candidate_diagnostics_observability_only"
        if packet.get(key) is not expected:
            _blocked_output_hygiene(f"generic live packet {key} posture invalid.")
    if packet.get("provider_query_generation_changed") not in {True, False}:
        _blocked_output_hygiene(
            "generic live packet provider_query_generation_changed invalid."
        )
    if packet.get("provider_routing_changed") not in {True, False}:
        _blocked_output_hygiene("generic live packet provider_routing_changed invalid.")
    if packet.get("official_pdf_table_read_support_adapter") != (
        "existing_fetch_read_content_packet"
    ):
        _blocked_output_hygiene("official artifact read-support adapter invalid.")
    if not isinstance(
        packet.get("official_pdf_table_read_support_status_summary"),
        Mapping,
    ):
        _blocked_output_hygiene("official artifact read-support summary invalid.")
    for key in (
        "official_http_source_survival_blocker_available",
        "http_source_survival_request_hygiene_added",
        "fetch_read_cap_preserved",
    ):
        if packet.get(key) is not True:
            _blocked_output_hygiene(f"generic live packet {key} posture invalid.")
    if packet.get("fetch_read_cap_value") != MAX_FETCH_READ_ATTEMPTS:
        _blocked_output_hygiene("fetch/read cap value invalid.")
    if packet.get("fetch_read_public_web_request_profile_id") != (
        FETCH_READ_PUBLIC_WEB_REQUEST_PROFILE_ID
    ):
        _blocked_output_hygiene("fetch/read public web request profile invalid.")
    if packet.get("fetch_read_public_web_request_posture") != (
        FETCH_READ_PUBLIC_WEB_REQUEST_POSTURE
    ):
        _blocked_output_hygiene("fetch/read public web request posture invalid.")
    if packet.get("http_source_survival_scope") != (
        "ordinary_public_web_fetch_read_hygiene"
    ):
        _blocked_output_hygiene("HTTP source survival scope invalid.")
    if packet.get("official_http_source_survival_blocker_active") not in {
        True,
        False,
    }:
        _blocked_output_hygiene("official HTTP source survival blocker flag invalid.")
    if (
        packet.get("official_http_source_survival_blocker_active") is True
        and packet.get("fetch_read_blocker")
        != BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX
    ):
        _blocked_output_hygiene(
            "official HTTP source survival blocker flag mismatched."
        )
    if packet.get("candidate_selection_policy_id") != (
        FETCH_READ_CANDIDATE_SELECTION_POLICY_ID
    ):
        _blocked_output_hygiene("candidate selection policy id missing.")
    if packet.get("candidate_selection_policy_scope") != (
        FETCH_READ_CANDIDATE_SELECTION_SCOPE
    ):
        _blocked_output_hygiene("candidate selection policy scope invalid.")
    if packet.get("candidate_selection_policy_uses_sanitized_metadata_only") is not True:
        _blocked_output_hygiene(
            "candidate selection must use sanitized metadata only."
        )
    if packet.get("candidate_selection_is_acquisition_only") is not True:
        _blocked_output_hygiene("candidate selection acquisition-only flag missing.")
    candidate_diagnostics = [
        _safe_mapping(item)
        for item in _safe_sequence(packet.get("fetch_read_candidate_diagnostics"))
    ]
    attempt_diagnostics = [
        _safe_mapping(item)
        for item in _safe_sequence(packet.get("fetch_read_attempt_diagnostics"))
    ]
    if len(attempt_diagnostics) != _bounded_int(packet.get("fetch_read_attempts")):
        _blocked_output_hygiene("fetch/read attempt diagnostics count mismatch.")
    if (
        attempt_diagnostics
        and _bounded_int(packet.get("fetch_read_completed")) == 0
        and packet.get("decision")
        == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING
    ):
        _blocked_output_hygiene(
            "attempted fetch/read failures must not collapse to entrypoint missing."
        )
    for diagnostic in candidate_diagnostics:
        _validate_candidate_diagnostic(diagnostic)
    seen_attempts: set[tuple[str, int]] = set()
    for diagnostic in attempt_diagnostics:
        candidate_id = _clean_text(diagnostic.get("candidate_id"), limit=320)
        attempt_index = _bounded_int(diagnostic.get("attempt_index"))
        if not candidate_id or attempt_index <= 0:
            _blocked_output_hygiene("fetch/read attempt diagnostic identity missing.")
        key = (candidate_id, attempt_index)
        if key in seen_attempts:
            _blocked_output_hygiene("duplicate fetch/read attempt diagnostic.")
        seen_attempts.add(key)
        _validate_attempt_diagnostic(diagnostic)


def _validate_analyst_workbench_surface(packet: Mapping[str, Any]) -> None:
    bundle = {
        "candidate_evidence_triage_packet": _safe_mapping(
            packet.get("candidate_evidence_triage_packet")
        ),
        "analyst_workbench_packet": _safe_mapping(
            packet.get("analyst_workbench_packet")
        ),
        "analysis_gap_search_proposal": _safe_mapping(
            packet.get("analysis_gap_search_proposal")
        ),
        "workbench_dprime_dossier": _safe_mapping(
            packet.get("workbench_dprime_dossier")
        ),
        "workbench_reduction_projection": _safe_mapping(
            packet.get("workbench_reduction_projection")
        ),
        "candidate_evidence_triage_ref": _safe_mapping(
            packet.get("candidate_evidence_triage_ref")
        ),
        "analyst_workbench_ref": _safe_mapping(packet.get("analyst_workbench_ref")),
        "analysis_gap_search_proposal_ref": _safe_mapping(
            packet.get("analysis_gap_search_proposal_ref")
        ),
        "workbench_dprime_dossier_ref": _safe_mapping(
            packet.get("workbench_dprime_dossier_ref")
        ),
        "workbench_reduction_projection_ref": _safe_mapping(
            packet.get("workbench_reduction_projection_ref")
        ),
    }
    try:
        validate_current_source_record_analyst_workbench_bundle(bundle)
    except AnalystWorkbenchError as exc:
        _blocked_output_hygiene(f"Analyst Workbench bundle invalid: {exc}")
    triage = bundle["candidate_evidence_triage_packet"]
    workbench = bundle["analyst_workbench_packet"]
    gap = bundle["analysis_gap_search_proposal"]
    dossier = bundle["workbench_dprime_dossier"]
    projection = bundle["workbench_reduction_projection"]
    for section_name, section, schema_version in (
        (
            "candidate_evidence_triage_packet",
            triage,
            CANDIDATE_EVIDENCE_TRIAGE_SCHEMA_VERSION,
        ),
        ("analyst_workbench_packet", workbench, ANALYST_WORKBENCH_SCHEMA_VERSION),
        (
            "analysis_gap_search_proposal",
            gap,
            ANALYSIS_GAP_SEARCH_PROPOSAL_SCHEMA_VERSION,
        ),
        (
            "workbench_dprime_dossier",
            dossier,
            WORKBENCH_DPRIME_DOSSIER_SCHEMA_VERSION,
        ),
    ):
        if not section:
            if _bounded_int(packet.get("fetch_read_packet_created")):
                _blocked_output_hygiene(f"{section_name} missing after fetch/read.")
            continue
        if section.get("schema_version") != schema_version:
            _blocked_output_hygiene(f"{section_name} schema mismatch.")
        if section.get("ordinary_product_path_consumed") is not True:
            _blocked_output_hygiene(f"{section_name} not product-consumed.")
        _validate_workbench_non_authority_posture(section, section_name)
    if projection.get("schema_version") != WORKBENCH_REDUCTION_PROJECTION_SCHEMA_VERSION:
        _blocked_output_hygiene("Workbench reduction projection schema mismatch.")
    if projection.get("owner") != "AnalystWorkbenchRuntime":
        _blocked_output_hygiene("Workbench reduction projection owner mismatch.")
    if projection.get("run_kernel_reduced") is not False:
        _blocked_output_hygiene("Workbench projection claimed RunKernel reduction.")
    if projection.get("run_kernel_reduction_pending") is not True:
        _blocked_output_hygiene("Workbench projection pending flag invalid.")
    if projection.get("proposed_for_runkernel_reduction") is not True:
        _blocked_output_hygiene("Workbench projection proposal flag invalid.")
    _validate_workbench_non_authority_posture(
        projection,
        "workbench_reduction_projection",
    )
    if _bounded_int(packet.get("fetch_read_packet_created")):
        if packet.get("optional_evidence_triage_implemented") is not True:
            _blocked_output_hygiene("Analyst Workbench triage was not implemented.")
        for key in (
            "candidate_evidence_triage_consumed_by_product_path",
            "analyst_workbench_consumed_by_product_path",
            "workbench_dprime_dossier_consumed_by_product_path",
        ):
            if packet.get(key) is not True:
                _blocked_output_hygiene(f"Analyst Workbench {key} invalid.")
        if projection.get("ordinary_product_path_consumed") is not True:
            _blocked_output_hygiene("Workbench reduction projection not consumed.")
    if _bounded_int(packet.get("dprime_model_review_calls_attempted")) and (
        _semantic_payload_supports_workbench_dossier(packet)
    ):
        if packet.get("workbench_dprime_dossier_consumed_by_dprime") is not True:
            _blocked_output_hygiene("D-prime did not consume Workbench dossier ref.")
        _validate_workbench_dprime_input_ref(packet)


def _semantic_payload_supports_workbench_dossier(packet: Mapping[str, Any]) -> bool:
    semantic = _safe_mapping(packet.get("semantic_status_payload"))
    dprime = _safe_mapping(semantic.get("dprime_status"))
    input_ref = _safe_mapping(dprime.get("input_packet_ref"))
    return bool(
        "workbench_dprime_dossier_ref" in semantic
        or "workbench_dprime_dossier_consumed_by_product_status" in semantic
        or "workbench_dprime_dossier_ref" in input_ref
    )


def _validate_workbench_dprime_input_ref(packet: Mapping[str, Any]) -> None:
    expected = _safe_mapping(packet.get("workbench_dprime_dossier_ref"))
    expected_digest = _clean_text(expected.get("dossier_digest"), limit=128)
    semantic = _safe_mapping(packet.get("semantic_status_payload"))
    dprime = _safe_mapping(semantic.get("dprime_status"))
    input_ref = _safe_mapping(dprime.get("input_packet_ref"))
    consumed = _safe_mapping(input_ref.get("workbench_dprime_dossier_ref"))
    if not expected_digest or consumed.get("dossier_digest") != expected_digest:
        _blocked_output_hygiene("D-prime Workbench dossier ref mismatch.")


def _validate_workbench_gap_reentry_ref(packet: Mapping[str, Any]) -> None:
    ref = _safe_mapping(packet.get("workbench_gap_reentry_ref"))
    if not ref:
        _blocked_output_hygiene("Workbench gap re-entry ref missing.")
    if ref.get("schema_version") != WORKBENCH_GAP_REENTRY_REF_SCHEMA_VERSION:
        _blocked_output_hygiene("Workbench gap re-entry ref schema mismatch.")
    status = ref.get("workbench_gap_reentry_status")
    if status not in {
        "not_required",
        "followup_not_licensed",
        "runkernel_authorized_not_executed",
    }:
        _blocked_output_hygiene("Workbench gap re-entry status invalid.")
    if packet.get("workbench_gap_reentry_status") != status:
        _blocked_output_hygiene("Workbench gap re-entry status alias mismatch.")
    authorization_ref = _safe_mapping(ref.get("runkernel_followup_authorization_ref"))
    authorization_created = ref.get("runkernel_followup_authorization_created") is True
    if authorization_created != bool(authorization_ref):
        _blocked_output_hygiene("Workbench gap re-entry authorization binding invalid.")
    if not authorization_created and ref.get("proposal_or_blocker_ref_only") is not True:
        _blocked_output_hygiene("Workbench gap re-entry proposal/blocker label invalid.")
    if (
        authorization_created
        and ref.get("runkernel_authorization_object_source")
        != "core.runkernel_followup_search_reentry_ordinary_search_runtime"
    ):
        _blocked_output_hygiene("Workbench gap re-entry authorization source invalid.")
    if ref.get("followup_execution_licensed") is not False:
        _blocked_output_hygiene("Workbench gap re-entry opened follow-up execution.")
    if ref.get("new_search_subsystem_created") is not False:
        _blocked_output_hygiene("Workbench gap re-entry created a new search subsystem.")
    for key in (
        "provider_called",
        "live_search_called",
        "fetch_read_executed",
        "dprime_dispatch_owner",
        "workbench_dispatch_owner",
        "evidence_admitted",
        "source_obligation_satisfied",
        "citation_eligible",
        "source_authority_finalized",
        "final_answer_packet_created",
        "author_prose_created",
        "product_correctness_claimed",
    ):
        if ref.get(key) is not False:
            _blocked_output_hygiene(f"Workbench gap re-entry {key} invalid.")
    if _safe_mapping(ref.get("raw_private_retention_flags")) != RAW_FALSE_FLAGS:
        _blocked_output_hygiene("Workbench gap re-entry raw/private flags invalid.")
    if packet.get("followup_execution_licensed") is not False:
        _blocked_output_hygiene("follow-up execution license alias invalid.")
    if packet.get("new_search_subsystem_created_for_gap_reentry") is not False:
        _blocked_output_hygiene("new search subsystem alias invalid.")


def _validate_workbench_non_authority_posture(
    section: Mapping[str, Any],
    section_name: str,
) -> None:
    for item in _iter_mapping_values(section):
        for key in (
            "evidence_admitted",
            "source_obligation_satisfied",
            "citation_eligible",
            "source_authority_finalized",
            "final_answer_packet_created",
            "author_answer_created",
            "product_correctness_claimed",
        ):
            if key in item and item.get(key) is not False:
                _blocked_output_hygiene(f"{section_name} authority flag invalid.")
        if "proposal_only" in item and item.get("proposal_only") is not True:
            _blocked_output_hygiene(f"{section_name} proposal-only flag invalid.")
        raw_flags = _safe_mapping(item.get("raw_private_retention_flags"))
        if raw_flags and raw_flags != RAW_FALSE_FLAGS:
            _blocked_output_hygiene(f"{section_name} raw/private flags invalid.")
        for key in RAW_FALSE_FLAGS:
            if key in item and item.get(key) is not False:
                _blocked_output_hygiene(f"{section_name} raw/private flag invalid.")


def _iter_mapping_values(value: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        safe = _safe_mapping(value)
        items.append(safe)
        for item in safe.values():
            items.extend(_iter_mapping_values(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            items.extend(_iter_mapping_values(item))
    return items


def _validate_candidate_diagnostic(diagnostic: Mapping[str, Any]) -> None:
    if not _clean_text(diagnostic.get("candidate_id"), limit=320):
        _blocked_output_hygiene("candidate diagnostic requires candidate_id.")
    if diagnostic.get("diagnostic_posture") != "observability_only":
        _blocked_output_hygiene("candidate diagnostic posture invalid.")
    for key in (
        "not_evidence",
        "not_citation_eligible",
        "not_source_obligation_satisfaction",
    ):
        if diagnostic.get(key) is not True:
            _blocked_output_hygiene(f"candidate diagnostic requires {key}=true.")
    for key in (
        "provider_snippet_used_as_evidence",
        "provider_snippet_used_as_extracted_source_text",
        "candidate_diagnostic_satisfies_source_obligation",
        "fetch_read_failure_metadata_citation_eligible",
        "official_artifact_read_support_raw_content_retained",
        "official_artifact_read_support_creates_source_authority",
        "official_artifact_read_support_satisfies_source_obligation",
        "official_artifact_read_support_citation_eligible",
        "official_artifact_read_support_claims_correctness",
        "pdf_parsing_opened",
        "ocr_opened",
        "browser_automation_opened",
        "heavy_document_parser_dependency_added",
    ):
        if key in diagnostic and diagnostic.get(key) is not False:
            _blocked_output_hygiene(f"candidate diagnostic requires {key}=false.")
    if diagnostic.get("attempted") not in {True, False}:
        _blocked_output_hygiene("candidate diagnostic attempted flag invalid.")
    if diagnostic.get("selected_for_fetch_read") not in {True, False}:
        _blocked_output_hygiene(
            "candidate diagnostic selected_for_fetch_read flag invalid."
        )
    if diagnostic.get("candidate_selection_policy_id") != (
        FETCH_READ_CANDIDATE_SELECTION_POLICY_ID
    ):
        _blocked_output_hygiene("candidate diagnostic policy id invalid.")
    if diagnostic.get("candidate_selection_is_acquisition_only") is not True:
        _blocked_output_hygiene("candidate diagnostic acquisition flag invalid.")
    for key in (
        "candidate_selection_created_source_authority",
        "candidate_selection_satisfies_source_obligation",
        "candidate_selection_citation_eligible",
        "candidate_selection_claims_correctness",
        "source_survival_diagnostic_creates_source_authority",
        "source_survival_diagnostic_satisfies_source_obligation",
        "source_survival_diagnostic_citation_eligible",
    ):
        if diagnostic.get(key) is not False:
            _blocked_output_hygiene(f"candidate diagnostic requires {key}=false.")
    if diagnostic.get("source_survival_diagnostic_only") is not True:
        _blocked_output_hygiene("candidate source survival diagnostic posture invalid.")
    if diagnostic.get("source_survival_scope") != (
        "ordinary_public_web_fetch_read_hygiene"
    ):
        _blocked_output_hygiene("candidate source survival scope invalid.")
    if diagnostic.get("source_survival_candidate_signal") not in {
        "source_of_record_looking",
        "official_looking",
        "ordinary_public_web",
    }:
        _blocked_output_hygiene("candidate source survival signal invalid.")
    if diagnostic.get("official_or_source_record_looking_http_candidate") not in {
        True,
        False,
    }:
        _blocked_output_hygiene("candidate source survival official flag invalid.")
    if _bounded_int(diagnostic.get("fetch_read_priority_rank")) <= 0:
        _blocked_output_hygiene("candidate diagnostic priority rank invalid.")
    _validate_candidate_selection_features(
        _safe_mapping(diagnostic.get("candidate_selection_features")),
        expected_priority_rank=_bounded_int(diagnostic.get("fetch_read_priority_rank")),
    )
    url_source = _clean_text(diagnostic.get("url_source"), limit=20)
    if url_source not in {"url", "link", "missing"}:
        _blocked_output_hygiene("candidate diagnostic url_source invalid.")
    if diagnostic.get("url_valid") not in {True, False}:
        _blocked_output_hygiene("candidate diagnostic url_valid flag invalid.")
    if diagnostic.get("url_valid") is True and not _is_valid_http_url(
        diagnostic.get("url")
    ):
        _blocked_output_hygiene("candidate diagnostic url_valid mismatch.")
    failure_category = diagnostic.get("failure_category")
    if (
        failure_category is not None
        and _clean_text(failure_category, limit=80)
        not in FETCH_READ_FAILURE_CATEGORIES
    ):
        _blocked_output_hygiene("candidate diagnostic failure category invalid.")
    if _safe_mapping(diagnostic.get("raw_private_retention_flags")) != RAW_FALSE_FLAGS:
        _blocked_output_hygiene("candidate diagnostic raw/private retention invalid.")


def _validate_candidate_selection_features(
    features: Mapping[str, Any],
    *,
    expected_priority_rank: int,
) -> None:
    if features.get("feature_posture") != "discovery_metadata_only":
        _blocked_output_hygiene("candidate selection feature posture invalid.")
    for key in (
        "official_domain_signal",
        "source_of_record_domain_signal",
        "query_entity_domain_overlap",
        "title_or_path_token_overlap",
        "public_agency_domain_signal",
        "derivative_domain_signal",
        "pdf_url_or_title_signal",
        "table_url_or_title_signal",
    ):
        if features.get(key) not in {True, False}:
            _blocked_output_hygiene(f"candidate selection feature {key} invalid.")
    for key in (
        "features_used_as_evidence",
        "features_create_source_authority",
        "features_satisfy_source_obligation",
        "features_make_candidate_citation_eligible",
        "features_claim_correctness",
    ):
        if features.get(key) is not False:
            _blocked_output_hygiene(f"candidate selection feature requires {key}=false.")
    if _bounded_int(features.get("provider_rank")) <= 0:
        _blocked_output_hygiene("candidate selection feature provider rank invalid.")
    if (
        _bounded_int(features.get("final_fetch_read_priority_rank"))
        != expected_priority_rank
    ):
        _blocked_output_hygiene("candidate selection feature priority rank mismatch.")


def _validate_attempt_diagnostic(diagnostic: Mapping[str, Any]) -> None:
    if diagnostic.get("diagnostic_posture") != "observability_only":
        _blocked_output_hygiene("fetch/read attempt diagnostic posture invalid.")
    for key in (
        "not_evidence",
        "not_citation_eligible",
        "not_source_obligation_satisfaction",
    ):
        if diagnostic.get(key) is not True:
            _blocked_output_hygiene(f"fetch/read diagnostic requires {key}=true.")
    for key in (
        "candidate_diagnostics_satisfy_source_obligations",
        "fetch_read_failure_metadata_citation_eligible",
        "official_artifact_read_support_raw_content_retained",
        "official_artifact_read_support_creates_source_authority",
        "official_artifact_read_support_satisfies_source_obligation",
        "official_artifact_read_support_citation_eligible",
        "official_artifact_read_support_claims_correctness",
        "pdf_parsing_opened",
        "ocr_opened",
        "browser_automation_opened",
        "heavy_document_parser_dependency_added",
    ):
        if key in diagnostic and diagnostic.get(key) is not False:
            _blocked_output_hygiene(f"fetch/read diagnostic requires {key}=false.")
    if not _normalized_status_class(diagnostic.get("http_status_class")):
        _blocked_output_hygiene("fetch/read diagnostic status class invalid.")
    if diagnostic.get("candidate_selection_policy_id") != (
        FETCH_READ_CANDIDATE_SELECTION_POLICY_ID
    ):
        _blocked_output_hygiene("fetch/read diagnostic policy id invalid.")
    if diagnostic.get("candidate_selection_is_acquisition_only") is not True:
        _blocked_output_hygiene("fetch/read diagnostic acquisition flag invalid.")
    for key in (
        "candidate_selection_created_source_authority",
        "candidate_selection_satisfies_source_obligation",
        "candidate_selection_citation_eligible",
        "candidate_selection_claims_correctness",
        "source_survival_diagnostic_creates_source_authority",
        "source_survival_diagnostic_satisfies_source_obligation",
        "source_survival_diagnostic_citation_eligible",
    ):
        if diagnostic.get(key) is not False:
            _blocked_output_hygiene(f"fetch/read diagnostic requires {key}=false.")
    if diagnostic.get("source_survival_diagnostic_only") is not True:
        _blocked_output_hygiene("fetch/read source survival diagnostic posture invalid.")
    if diagnostic.get("source_survival_scope") != (
        "ordinary_public_web_fetch_read_hygiene"
    ):
        _blocked_output_hygiene("fetch/read source survival scope invalid.")
    if diagnostic.get("source_survival_candidate_signal") not in {
        "source_of_record_looking",
        "official_looking",
        "ordinary_public_web",
    }:
        _blocked_output_hygiene("fetch/read source survival signal invalid.")
    if diagnostic.get("official_or_source_record_looking_http_candidate") not in {
        True,
        False,
    }:
        _blocked_output_hygiene("fetch/read source survival official flag invalid.")
    if diagnostic.get("fetch_read_request_profile_id") != (
        FETCH_READ_PUBLIC_WEB_REQUEST_PROFILE_ID
    ):
        _blocked_output_hygiene("fetch/read request profile invalid.")
    if diagnostic.get("fetch_read_request_posture") != (
        FETCH_READ_PUBLIC_WEB_REQUEST_POSTURE
    ) and diagnostic.get("fetch_read_request_posture") != (
        "provider_extracted_source_content_no_direct_fetch"
    ):
        _blocked_output_hygiene("fetch/read request posture invalid.")
    final_url = _clean_text(diagnostic.get("final_url"), limit=700)
    if final_url and not _is_valid_http_url(final_url):
        _blocked_output_hygiene("fetch/read final URL invalid.")
    status_code = diagnostic.get("http_status_code")
    if status_code is not None:
        parsed_status = _bounded_int(status_code)
        if not 100 <= parsed_status <= 599:
            _blocked_output_hygiene("fetch/read HTTP status code invalid.")
    if _bounded_int(diagnostic.get("redirect_count")) > MAX_REDIRECTS:
        _blocked_output_hygiene("fetch/read redirect count invalid.")
    if _bounded_int(diagnostic.get("fetch_read_priority_rank")) <= 0:
        _blocked_output_hygiene("fetch/read diagnostic priority rank invalid.")
    _validate_candidate_selection_features(
        _safe_mapping(diagnostic.get("candidate_selection_features")),
        expected_priority_rank=_bounded_int(diagnostic.get("fetch_read_priority_rank")),
    )
    _content_type_or_unknown(diagnostic.get("content_type"))
    if diagnostic.get("readable_content_type") not in {True, False, FETCH_READ_UNKNOWN}:
        _blocked_output_hygiene("fetch/read diagnostic readable content flag invalid.")
    if diagnostic.get("readable_text_obtained") not in {True, False}:
        _blocked_output_hygiene("fetch/read diagnostic readable text flag invalid.")
    failure_category = diagnostic.get("failure_category")
    if diagnostic.get("readable_text_obtained") is True:
        if failure_category is not None:
            _blocked_output_hygiene(
                "successful fetch/read diagnostic must not carry failure category."
            )
    elif _clean_text(failure_category, limit=80) not in FETCH_READ_FAILURE_CATEGORIES:
        _blocked_output_hygiene("fetch/read diagnostic failure category invalid.")
    if _safe_mapping(diagnostic.get("raw_private_retention_flags")) != RAW_FALSE_FLAGS:
        _blocked_output_hygiene("fetch/read diagnostic raw/private retention invalid.")


def format_generic_single_relation_live_dogfood_output(
    packet: Mapping[str, Any],
    *,
    packet_path: Path,
) -> str:
    """Render a compact CLI view for one generic relation dogfood run."""

    if packet.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND:
        return _format_product_single_fact_output(packet, packet_path=packet_path)

    sources = _source_display_entries(packet)
    boundary_sources = _source_citation_display_boundary_entries(packet)
    gateway = _safe_mapping(packet.get("source_readiness_gateway"))
    gateway_source = _safe_mapping(gateway.get("selected_source_ref"))
    gateway_window = _safe_mapping(gateway.get("selected_window_ref"))
    gateway_non_claims = _safe_mapping(gateway.get("explicit_non_claims"))
    dprime_integration = _safe_mapping(
        packet.get("single_relation_dprime_authority_integration")
    )
    display_boundary = _safe_mapping(packet.get("source_citation_display_boundary"))
    answer_path_pass = (
        packet.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
        and packet.get("decision") == PASS_DECISION
        and packet.get("fap_author_opened") is True
    )
    relation_status = _safe_mapping(packet.get("dprime_relation_intake_ref")).get(
        "status",
        "not reached",
    )
    header = (
        "ScryRaven current source-of-record single-fact run"
        if packet.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
        else "ScryRaven generic single-relation live dogfood run"
    )
    lines = [
        header,
        f"Question: {_clean_text(packet.get('query'), limit=500)}",
        f"Decision: {packet.get('decision')}",
        f"Next product checkpoint: {packet.get('next_product_path_checkpoint') or 'not named'}",
        "",
        "Entrypoint",
        f"- Surface: {packet.get('entrypoint_surface') or 'not named'}",
        f"- Kind: {packet.get('entrypoint_kind') or 'not named'}",
        "- Diagnostic dogfood alias: "
        f"{_bool_text(packet.get('diagnostic_dogfood_alias'))}",
        f"- Supported query class: {packet.get('supported_query_class') or 'not named'}",
        "",
        "Plan",
        f"- Relation plan consumed: {_bool_text(packet.get('relation_plan_consumed'))}",
        f"- Relation plan id: {packet.get('relation_plan_id') or 'not created'}",
        f"- Component: {packet.get('component_text') or 'not created'}",
        f"- Search seed used: {packet.get('search_query_seed_used') or 'not used'}",
        "",
        "Source/readiness gateway",
        f"- Status: {gateway.get('status') or 'not reached'}",
        f"- Blocker: {gateway.get('blocker_code') or 'none'}",
        "- Selected current value status: "
        f"{gateway.get('selected_current_value_display_status') or 'not displayed'}",
        "- Selected current value: "
        f"{gateway.get('selected_current_value_text') or 'not displayed'}",
        "- Selected source: "
        f"{gateway_source.get('title') or 'not available'} "
        f"({gateway_source.get('domain') or 'unknown domain'})",
        f"- Selected source URL: {gateway_source.get('url') or 'not available'}",
        f"- Selected window digest: {gateway_window.get('selected_window_digest') or 'not available'}",
        "- Source obligation satisfied: "
        f"{_bool_text(gateway_non_claims.get('source_obligation_satisfied'))}",
        "- Citation eligible: "
        f"{_bool_text(gateway_non_claims.get('citation_eligible'))}",
        "- Source authority finalized: "
        f"{_bool_text(gateway_non_claims.get('source_authority_finalized'))}",
        "",
        "D-prime authority integration",
        f"- Status: {dprime_integration.get('status') or 'not reached'}",
        f"- Blocker: {dprime_integration.get('blocker_code') or 'none'}",
        "- Existing source/citation authority exists: "
        f"{_bool_text(dprime_integration.get('existing_dprime_source_obligation_citation_authority_exists'))}",
        "- Downstream D-prime authority enabled: "
        f"{_bool_text(dprime_integration.get('dprime_downstream_authority_enabled'))}",
        "- Source/citation authority enabled: "
        f"{_bool_text(dprime_integration.get('dprime_source_citation_authority_enabled'))}",
        "- Single-lane answer path enabled: "
        f"{_bool_text(dprime_integration.get('dprime_single_lane_answer_path_enabled'))}",
        "- Source/citation stop point: "
        f"{dprime_integration.get('dprime_source_citation_stoppoint_status') or 'not reached'}",
        "- D-prime pass + gateway display sufficient for readiness: false.",
        "- Gateway treated as authority: "
        f"{_bool_text(dprime_integration.get('gateway_treated_as_authority'))}",
        "- Source-obligation authority consumed: "
        f"{_bool_text(dprime_integration.get('source_obligation_authority_consumed'))}",
        "- Citation-source handoff authority consumed: "
        f"{_bool_text(dprime_integration.get('citation_source_handoff_authority_consumed'))}",
        "- Source-obligation ready: "
        f"{_bool_text(dprime_integration.get('single_relation_source_obligation_ready'))}",
        "- Citation handoff ready: "
        f"{_bool_text(dprime_integration.get('single_relation_citation_handoff_ready'))}",
        f"- Next phase: {dprime_integration.get('next_phase') or 'not named'}",
        "",
        "Source/citation display boundary",
        f"- Status: {display_boundary.get('status') or 'not reached'}",
        f"- Blocker: {display_boundary.get('blocker_code') or 'none'}",
        "- Authority source: "
        f"{display_boundary.get('authority_source') or 'not available'}",
        "- Derived from D-prime authority: "
        f"{_bool_text(display_boundary.get('derived_from_dprime_authority'))}",
        "- Derived from gateway-only state: "
        f"{_bool_text(display_boundary.get('derived_from_gateway_only'))}",
        "- Entries created: "
        f"{_bool_text(display_boundary.get('source_citation_display_entries_created'))}",
        (
            "- FAP/Author consumed through existing D-prime path: true."
            if answer_path_pass
            else "- Boundary-only FAP created: false."
        ),
        (
            "- Product correctness claimed: false."
            if answer_path_pass
            else "- Boundary-only Author invoked: false."
        ),
        "- Final citation rendering created: false.",
    ]
    if boundary_sources:
        lines.extend(f"- {entry}" for entry in boundary_sources)
    else:
        lines.append("- No source/citation boundary entries are available yet.")
    lines.extend(
        [
            "",
        "Answer",
        "- Final answer prose created: "
        f"{_bool_text(packet.get('author_answer_created'))}.",
        "- FinalAnswerPacket created: "
        f"{_bool_text(packet.get('final_answer_packet_created'))}.",
        "- Product answer text: "
        f"{packet.get('product_answer_text') or 'not created'}.",
        _clean_text(packet.get("answer_or_blocker_text"), limit=1_400)
        or "No gateway status is available.",
        "",
        "Sources",
        ]
    )
    if sources:
        lines.extend(f"- {entry}" for entry in sources)
    else:
        lines.append("- No source display is available yet.")
    lines.extend(
        [
            "",
            "Status",
            f"- Fast planner: {packet.get('fast_planner_kind') or 'not used'}",
            "- Model-assisted planning status: "
            f"{packet.get('model_assisted_planning_reduced_status') or 'not used'}",
            "- FastModel planning calls: "
            f"{packet.get('fast_planner_model_calls_attempted')}/"
            f"{packet.get('fast_planner_model_calls_completed')}",
            f"- Planner marked ambiguity: {_bool_text(packet.get('planner_marked_ambiguity'))}",
            f"- Serper scout calls: {packet.get('serper_scout_calls_attempted')}/"
            f"{packet.get('serper_scout_calls_completed')}",
            f"- Extraction provider: {packet.get('extraction_provider') or 'not used'}",
            "- Provider-extracted content obtained: "
            f"{_bool_text(packet.get('provider_extracted_content_obtained'))}",
            f"- Provider calls: {packet.get('provider_calls_attempted')}/"
            f"{packet.get('provider_calls_completed')}",
            "- Source-challenge recovery: "
            f"{packet.get('source_challenge_recovery_status') or 'not_triggered'} "
            f"({packet.get('source_challenge_recovery_provider_calls_attempted')}/"
            f"{packet.get('source_challenge_recovery_provider_calls_completed')} calls)",
            f"- Direct fetch/read fallback attempts: {packet.get('direct_fetch_read_attempts')}",
            f"- Readable content handoff: {packet.get('fetch_read_completed')}",
            "- Fetch/read status classes: "
            f"{_summary_text(packet.get('fetch_read_status_class_summary'))}",
            "- Fetch/read content types: "
            f"{_summary_text(packet.get('fetch_read_content_type_summary'))}",
            "- Fetch/read failure categories: "
            f"{_summary_text(packet.get('fetch_read_failure_category_summary'))}",
            "- Official HTTP source-survival blocker active: "
            f"{_bool_text(packet.get('official_http_source_survival_blocker_active'))}",
            f"- EvidenceLedger admissions: {packet.get('evidence_ledger_admissions')}",
            f"- D-prime relation intake: {relation_status}",
            f"- D-prime/model calls: {packet.get('dprime_model_review_calls_attempted')}/"
            f"{packet.get('dprime_model_review_calls_completed')}",
            "",
            "Caveats",
            "- Product correctness claimed: false.",
            "- Friend-level/general MVP claimed: false.",
            "- FAP/Author consumed through existing D-prime path: "
            f"{_bool_text(packet.get('fap_author_opened'))}.",
            "- Multi-component planning opened: false.",
            "- Raw/private retained: false.",
            "- Fake-provider offline PASS is not live validation PASS.",
            f"- Review packet: {_display_path(packet_path)}",
        ]
    )
    return "\n".join(lines)


def _format_product_single_fact_output(
    packet: Mapping[str, Any],
    *,
    packet_path: Path,
) -> str:
    answer_text = _clean_text(packet.get("product_answer_text"), limit=4_000)
    if not answer_text:
        answer_text = _product_single_fact_blocker_text(packet)
    lines = [
        "Answer:",
        answer_text or "Blocked before answer: unavailable.",
        "",
        "Sources:",
    ]
    source_entries = _product_single_fact_source_entries(packet)
    if source_entries:
        for index, source in enumerate(source_entries, start=1):
            label = _clean_text(source.get("label"), limit=80) or f"D{index}"
            if not label.startswith("["):
                label = f"[D{index}]"
            title = (
                _clean_text(source.get("source_title"), limit=220)
                or _clean_text(source.get("title"), limit=220)
                or _clean_text(source.get("display_text"), limit=400)
                or "Source"
            )
            url = _clean_text(
                source.get("source_url") or source.get("url"),
                limit=700,
            )
            lines.append(f"{label} {title}")
            if url:
                lines.append(url)
    else:
        lines.append("No source display is available.")
    lines.extend(
        [
            "",
            "Status:",
            f"- Decision: {packet.get('decision')}",
            f"- Planner calls: {packet.get('query_plans_consumed')}/1",
            (
                f"- Provider: {packet.get('extraction_provider') or 'not used'}, "
                f"{packet.get('provider_calls_completed')}/"
                f"{packet.get('provider_calls_attempted')}"
            ),
            "- Provider-extracted content: "
            f"{_bool_text(packet.get('provider_extracted_content_obtained'))}",
            f"- EvidenceLedger admissions: {packet.get('evidence_ledger_admissions')}",
            f"- D-prime/model calls: {packet.get('dprime_model_review_calls_attempted')}/"
            f"{packet.get('dprime_model_review_calls_completed')}",
            "- Raw/private retained: false",
            "- Review report: "
            f"{_product_report_display_path(packet)}",
        ]
    )
    return "\n".join(lines)


def _product_single_fact_blocker_text(packet: Mapping[str, Any]) -> str:
    reentry = _safe_mapping(packet.get("workbench_gap_reentry_ref"))
    if reentry.get("workbench_gap_reentry_status") == "followup_not_licensed":
        if reentry.get("workbench_gap_kind") == "unreadable_high_value_candidate":
            return (
                "Blocked before answer: official source read support is needed. "
                "A high-value official artifact was found, but bounded PDF/table "
                "text support is not available in this run."
            )
        if reentry.get("runkernel_followup_authorization_created") is True:
            return (
                "Blocked before answer: official strict support follow-up is needed. "
                "The Workbench/D-prime gap was converted into a RunKernel follow-up "
                "authorization, but live follow-up execution is not licensed."
            )
        return (
            "Blocked before answer: official strict support follow-up is needed. "
            "The Workbench/D-prime gap remains proposal-only; live follow-up "
            "execution is not licensed."
        )
    gap = _safe_mapping(packet.get("analysis_gap_search_proposal"))
    gap_status = _clean_text(gap.get("gap_status"), limit=80)
    gap_kind = _clean_text(gap.get("gap_kind"), limit=120)
    gap_reason = _clean_text(gap.get("gap_reason"), limit=300)
    if gap_status == "proposed" and gap_kind in {
        "strict_support_missing",
        "overclaim_risk",
        "unreadable_high_value_candidate",
    }:
        reason = gap_reason or "contextual material is insufficient."
        return f"Blocked before answer: official strict support needed. {reason}"
    detail = _clean_text(packet.get("blocker_detail"), limit=900)
    return f"Blocked before answer: {packet.get('decision')}. {detail}".strip()


def _workbench_gap_reentry_ref(
    *,
    gap_proposal: Mapping[str, Any],
    gap_ref: Mapping[str, Any],
    semantic_payload: Mapping[str, Any],
) -> dict[str, Any]:
    gap = _safe_mapping(gap_proposal)
    semantic = _safe_mapping(semantic_payload)
    followup = _safe_mapping(semantic.get("dprime_followup_search_reentry_ref"))
    dprime_gap = _dprime_gap_posture_ref(semantic)
    workbench_gap_required = gap.get("gap_status") == "proposed"
    dprime_gap_required = bool(dprime_gap)
    gap_required = workbench_gap_required or dprime_gap_required
    authorization_ref = _safe_mapping(followup.get("followup_search_authorization_ref"))
    authorization_created = bool(authorization_ref)
    if not gap_required:
        status = "not_required"
        execution_status = "not_required"
        ordinary_status = "not_required"
    elif authorization_created:
        status = "runkernel_authorized_not_executed"
        execution_status = "not_executed_live_followup_not_licensed"
        ordinary_status = _clean_text(
            followup.get("ordinary_search_executor_handoff_status"),
            limit=120,
        ) or "ordinary_search_reentry_intent_created"
    else:
        status = "followup_not_licensed"
        execution_status = "not_executed_followup_not_licensed"
        ordinary_status = "intended_not_executed"
    gap_sources: list[str] = []
    if workbench_gap_required:
        gap_sources.append("workbench")
    if dprime_gap_required:
        gap_sources.append("dprime")
    ref = {
        "schema_version": WORKBENCH_GAP_REENTRY_REF_SCHEMA_VERSION,
        "phase_name": PHASE_NAME,
        "mode": MODE,
        "surface": "current_source_record_workbench_dprime_gap_reentry",
        "workbench_gap_reentry_status": status,
        "gap_sources": gap_sources,
        "workbench_gap_proposal_ref": _safe_mapping(gap_ref),
        "workbench_gap_status": gap.get("gap_status"),
        "workbench_gap_kind": gap.get("gap_kind"),
        "dprime_gap_ref": dprime_gap,
        "followup_search_intent_ref": _safe_mapping(
            followup.get("followup_search_intent_packet_ref")
        ),
        "runkernel_followup_authorization_ref": authorization_ref,
        "runkernel_followup_authorization_status": (
            "authorized"
            if authorization_created
            else "not_created_followup_not_licensed"
            if gap_required
            else "not_required"
        ),
        "runkernel_followup_authorization_created": authorization_created,
        "runkernel_authorization_object_source": (
            "core.runkernel_followup_search_reentry_ordinary_search_runtime"
            if authorization_created
            else "not_created"
        ),
        "local_product_path_projection": True,
        "proposal_or_blocker_ref_only": not authorization_created,
        "ordinary_search_reentry_intent_status": ordinary_status,
        "ordinary_search_path_reused": bool(gap_required or authorization_created),
        "new_search_subsystem_created": False,
        "followup_execution_status": execution_status,
        "followup_execution_licensed": False,
        "provider_called": bool(followup.get("provider_called")),
        "live_search_called": bool(followup.get("live_search_called")),
        "fetch_read_executed": bool(followup.get("fetch_read_executed")),
        "dprime_dispatch_owner": bool(followup.get("dprime_dispatch_owner")),
        "workbench_dispatch_owner": False,
        "evidence_admitted": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
        "source_authority_finalized": False,
        "final_answer_packet_created": False,
        "author_prose_created": False,
        "product_correctness_claimed": False,
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "forbidden_interpretation": (
            "A local Workbench/D-prime gap re-entry ref is not a "
            "RunKernel follow-up authorization unless the "
            "runkernel_followup_authorization_ref is present."
        ),
    }
    ref = {key: value for key, value in ref.items() if value not in (None, "")}
    ref["ref_digest"] = _digest_json(ref)
    return ref


def _dprime_gap_posture_ref(semantic_payload: Mapping[str, Any]) -> dict[str, Any]:
    dprime = _safe_mapping(_safe_mapping(semantic_payload).get("dprime_status"))
    if not dprime:
        return {}
    relation = _clean_text(dprime.get("support_relation"), limit=160)
    assessment_status = _clean_text(dprime.get("assessment_status"), limit=160)
    proposal_status = _clean_text(
        dprime.get("proposal_validation_status"),
        limit=160,
    )
    gap_relations = {
        "absent",
        "scope_mismatch",
        "currentness_mismatch",
        "contradicts",
        "missing_qualifier",
        "weak_or_overclaim_risk",
        "abstained",
    }
    gap_statuses = {
        "non-support",
        "challenge-recommended",
        "abstained",
        "invalid",
    }
    gap_required = (
        relation in gap_relations
        or assessment_status in gap_statuses
        or (
            bool(relation)
            and relation != "directly_supports"
            and proposal_status != "DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED"
        )
    )
    if not gap_required:
        return {}
    return _without_empty(
        {
            "status": "gap_posture_detected",
            "assessment_status": assessment_status,
            "support_relation": relation,
            "proposal_validation_status": proposal_status,
            "blocker_detail": _clean_text(dprime.get("blocker_detail"), limit=500),
            "assessment_ref": _safe_mapping(dprime.get("assessment_ref")),
            "dprime_dispatch_owner": False,
        }
    )


def _product_report_display_path(packet: Mapping[str, Any]) -> str:
    path = _clean_text(packet.get("review_report_markdown_path"), limit=900)
    if not path:
        return "not written"
    if (
        "dogfood" in path.casefold()
        or "single_relation_live_dogfood_packet" in path.casefold()
        or "mvp_single_relation_live_dogfood_01" in path.casefold()
    ):
        return CURRENT_SOURCE_RECORD_SINGLE_FACT_REVIEW_REPORT_MD_NAME
    return path


def _product_single_fact_source_entries(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries = [
        _safe_mapping(entry)
        for entry in _safe_sequence(packet.get("source_display_entries"))
        if isinstance(entry, Mapping)
    ]
    if entries:
        return entries
    return [
        _safe_mapping(entry)
        for entry in _safe_sequence(packet.get("source_citation_display_entries"))
        if isinstance(entry, Mapping)
    ]


def _write_current_source_record_single_fact_review_report(
    *,
    packet: Mapping[str, Any],
    json_path: Path,
    markdown_path: Path,
) -> None:
    report = _build_current_source_record_single_fact_review_report(packet)
    _write_json(json_path, report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        _format_current_source_record_single_fact_review_report(report),
        encoding="utf-8",
    )


def _build_current_source_record_single_fact_review_report(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    safe = _safe_mapping(packet)
    gateway = _safe_mapping(safe.get("source_readiness_gateway"))
    lineage = _safe_mapping(safe.get("selected_current_value_to_fap_claim_lineage"))
    contract_projection = _safe_mapping(
        safe.get("single_relation_answer_contract_projection")
    )
    answer_path_ref = _safe_mapping(safe.get("dprime_answer_path_ref"))
    integration = _safe_mapping(safe.get("single_relation_dprime_authority_integration"))
    boundary = _safe_mapping(safe.get("source_citation_display_boundary"))
    semantic = _safe_mapping(safe.get("semantic_status_payload"))
    dprime = _safe_mapping(semantic.get("dprime_status"))
    analyst_workbench = _current_source_record_workbench_report_section(safe)
    gap_reentry = _current_source_record_gap_reentry_report_section(safe)
    live_product_run_executed = bool(safe.get("live_runs_attempted"))
    report = {
        "report_kind": "current_source_record_single_fact_review_report",
        "schema_version": "current_source_record_single_fact_review_report_v1",
        "phase_name": PHASE_NAME,
        "mode": MODE,
        "decision": safe.get("decision"),
        "blocker_code": safe.get("blocker_code"),
        "blocker_detail": safe.get("blocker_detail"),
        "answer_contract_lifecycle": {
            "initial_answer_contract_present": "unknown",
            "current_answer_contract_present": bool(contract_projection),
            "current_answer_contract_status": (
                "present" if contract_projection else "unknown"
            ),
            "current_answer_contract_id": contract_projection.get(
                "projection_kind"
            ),
            "current_answer_contract_digest": contract_projection.get(
                "projection_digest"
            ),
            "projection_kind": contract_projection.get("projection_kind"),
            "projection_digest": contract_projection.get("projection_digest"),
            "contract_owner": contract_projection.get("contract_owner"),
            "component_ref": _safe_mapping(contract_projection.get("component_ref")),
            "active_components": [
                _safe_mapping(contract_projection.get("component_ref"))
            ]
            if _safe_mapping(contract_projection.get("component_ref"))
            else [],
            "source_obligation_ref": _safe_mapping(
                contract_projection.get("source_obligation_ref")
            ),
            "active_source_obligations": [
                _safe_mapping(contract_projection.get("source_obligation_ref"))
            ]
            if _safe_mapping(contract_projection.get("source_obligation_ref"))
            else [],
            "active_fetch_read_obligations": [
                _safe_mapping(contract_projection.get("acquisition_plan_ref"))
            ]
            if _safe_mapping(contract_projection.get("acquisition_plan_ref"))
            else [],
            "active_caveats": [],
            "prohibited_upgrades": [],
            "amendment_candidates": {
                "proposed": "unknown",
                "admitted": "unknown",
                "applied": "unknown",
            },
            "search_executor_handoff_consumed_current_answer_contract": bool(
                safe.get("acquisition_plan_consumed_by_product_path")
            ),
            "updated_contract_state_ref": _without_empty(
                {
                    "state_kind": _safe_mapping(
                        safe.get("single_relation_answer_contract_state")
                    ).get("state_kind"),
                    "state_digest": _safe_mapping(
                        safe.get("single_relation_answer_contract_state")
                    ).get("state_digest"),
                    "support_admission_allowed": _safe_mapping(
                        safe.get("single_relation_answer_contract_state")
                    ).get("support_admission_allowed"),
                    "answer_display_allowed": _safe_mapping(
                        safe.get("single_relation_answer_contract_state")
                    ).get("answer_display_allowed"),
                    "source_display_allowed": _safe_mapping(
                        safe.get("single_relation_answer_contract_state")
                    ).get("source_display_allowed"),
                }
            ),
            "accepted_current_answer_contract_authority_ref": _safe_mapping(
                lineage.get("accepted_current_answer_contract_authority_ref")
            ),
            "selected_claim_bound_to_current_answer_contract": lineage.get(
                "contract_accountable"
            )
            is True,
            "selected_value_bound_to_current_answer_contract_component_source_obligation": (
                lineage.get("contract_accountable") is True
            ),
            "lineage_checks": _safe_mapping(lineage.get("checks")),
            "lineage_missing": list(_safe_sequence(lineage.get("missing"))),
        },
        "claim_propagation_lifecycle": {
            "selected_current_value": gateway.get("selected_current_value_text"),
            "selected_current_value_present": bool(
                gateway.get("selected_current_value_text")
            ),
            "selected_source_ref": _safe_mapping(gateway.get("selected_source_ref")),
            "selected_source_present": bool(
                _safe_mapping(gateway.get("selected_source_ref")).get("url")
            ),
            "selected_window_ref": _safe_mapping(gateway.get("selected_window_ref")),
            "selected_value_bound_to_contract": lineage.get("contract_accountable")
            is True,
            "selected_value_bound_to_current_answer_contract_component_source_obligation": (
                lineage.get("contract_accountable") is True
            ),
            "semantic_observation_ref": _safe_mapping(
                lineage.get("semantic_observation_ref")
            )
            or _safe_mapping(answer_path_ref.get("semantic_observation_ref")),
            "component_coverage_ref": _safe_mapping(
                lineage.get("component_coverage_ref")
            )
            or _safe_mapping(answer_path_ref.get("component_coverage_ref")),
            "sufficiency_readiness_ref": _safe_mapping(
                lineage.get("sufficiency_readiness_ref")
            )
            or _safe_mapping(answer_path_ref.get("sufficiency_readiness_ref")),
            "fap_safe_claim_ref": _safe_mapping(lineage.get("fap_safe_claim_ref"))
            or _safe_mapping(answer_path_ref.get("fap_safe_claim_ref")),
            "author_safe_claim_ref": _safe_mapping(
                lineage.get("author_safe_claim_ref")
            )
            or _safe_mapping(answer_path_ref.get("author_safe_claim_ref")),
            "selected_value_entered_admitted_semantic_support": bool(
                _safe_mapping(lineage.get("semantic_observation_ref")).get(
                    "observation_digest"
                )
                or _safe_mapping(answer_path_ref.get("semantic_observation_ref")).get(
                    "observation_digest"
                )
            ),
            "selected_value_entered_component_coverage": bool(
                _safe_mapping(lineage.get("component_coverage_ref")).get(
                    "coverage_record_digest"
                )
                or _safe_mapping(answer_path_ref.get("component_coverage_ref")).get(
                    "coverage_record_digest"
                )
            ),
            "selected_value_entered_sufficiency_readiness": bool(
                _safe_mapping(lineage.get("sufficiency_readiness_ref")).get(
                    "readiness_digest"
                )
                or _safe_mapping(answer_path_ref.get("sufficiency_readiness_ref")).get(
                    "readiness_digest"
                )
            ),
            "selected_value_entered_fap_safe_claim_text": bool(
                safe.get("safe_answer_claim_text")
            ),
            "selected_value_entered_author_answer_text": bool(
                safe.get("answer_path_author_text_present")
                and safe.get("safe_answer_claim_text")
                and (
                    safe.get("safe_answer_claim_text")
                    in (safe.get("author_answer_text") or "")
                )
            ),
            "fap_safe_claim_text": safe.get("safe_answer_claim_text"),
            "author_answer_text_present": safe.get("answer_path_author_text_present")
            is True,
            "product_answer_text_present": safe.get("answer_text_present") is True,
            "authority_path": safe.get("product_claim_text_authority_path")
            or lineage.get("authority_path"),
            "unknown_stage_explanations": [],
        },
        "stage_lifecycle": {
            "planner": {
                "relation_plan_consumed": safe.get("relation_plan_consumed"),
                "relation_plan_id": safe.get("relation_plan_id"),
                "query_plans_consumed": safe.get("query_plans_consumed"),
                "acquisition_query": safe.get("acquisition_query"),
            },
            "provider_and_fetch": {
                "extraction_provider": safe.get("extraction_provider"),
                "provider_calls_attempted": safe.get("provider_calls_attempted"),
                "provider_calls_completed": safe.get("provider_calls_completed"),
                "provider_extracted_content_obtained": safe.get(
                    "provider_extracted_content_obtained"
                ),
                "fetch_read_attempts": safe.get("fetch_read_attempts"),
                "fetch_read_completed": safe.get("fetch_read_completed"),
            },
            "evidence_and_dprime": {
                "evidence_ledger_admissions": safe.get("evidence_ledger_admissions"),
                "dprime_relation_intake_ref": _safe_mapping(
                    safe.get("dprime_relation_intake_ref")
                ),
                "dprime_status": _without_empty(
                    {
                        "assessment_status": dprime.get("assessment_status"),
                        "support_relation": dprime.get("support_relation"),
                        "semantic_observation_admission_status": dprime.get(
                            "semantic_observation_admission_status"
                        ),
                        "objects_created": _safe_mapping(dprime.get("objects_created")),
                    }
                ),
            },
            "source_obligation_and_display": {
                "source_obligation_authority_consumed": safe.get(
                    "source_obligation_authority_consumed"
                ),
                "citation_source_handoff_authority_consumed": safe.get(
                    "citation_source_handoff_authority_consumed"
                ),
                "integration_status": integration.get("status"),
                "display_boundary_status": boundary.get("status"),
                "source_display_entry_count": len(
                    _safe_sequence(safe.get("source_citation_display_entries"))
                ),
            },
            "answer_path": {
                "sufficiency_readiness_status": answer_path_ref.get(
                    "sufficiency_readiness_status"
                ),
                "final_answer_packet_status": answer_path_ref.get(
                    "final_answer_packet_status"
                ),
                "author_answer_status": answer_path_ref.get(
                    "author_answer_status"
                ),
                "citation_source_display_status": answer_path_ref.get(
                    "citation_source_display_status"
                ),
                "safe_claim_available": bool(safe.get("safe_answer_claim_text")),
            },
            "retention": {
                "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
                "live_product_run_executed": live_product_run_executed,
                "live_validation_correctness_claimed": False,
                "product_correctness_claimed": False,
            },
        },
        "analyst_workbench": analyst_workbench,
        "gap_reentry": gap_reentry,
        "non_claims": {
            "live_product_run_executed": live_product_run_executed,
            "live_validation_correctness_claimed": False,
            "product_correctness_claimed": False,
            "source_obligation_satisfied_by_cli": False,
            "final_citation_rendering_created": False,
            "raw_private_retained": False,
        },
    }
    return _json_safe(report)


def _current_source_record_workbench_report_section(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    triage = _safe_mapping(packet.get("candidate_evidence_triage_packet"))
    workbench = _safe_mapping(packet.get("analyst_workbench_packet"))
    gap = _safe_mapping(packet.get("analysis_gap_search_proposal"))
    dossier = _safe_mapping(packet.get("workbench_dprime_dossier"))
    projection = _safe_mapping(packet.get("workbench_reduction_projection"))
    return {
        "schema_version": "analyst_workbench_review_section_v1",
        "product_path_consumed": bool(
            packet.get("analyst_workbench_consumed_by_product_path")
        ),
        "candidate_evidence_triage_ref": _safe_mapping(
            packet.get("candidate_evidence_triage_ref")
        ),
        "analyst_workbench_ref": _safe_mapping(packet.get("analyst_workbench_ref")),
        "analysis_gap_search_proposal_ref": _safe_mapping(
            packet.get("analysis_gap_search_proposal_ref")
        ),
        "workbench_dprime_dossier_ref": _safe_mapping(
            packet.get("workbench_dprime_dossier_ref")
        ),
        "workbench_dprime_dossier_consumed_by_dprime": bool(
            packet.get("workbench_dprime_dossier_consumed_by_dprime")
        ),
        "workbench_reduction_projection_ref": _safe_mapping(
            packet.get("workbench_reduction_projection_ref")
        ),
        "workbench_reduction_projection_status": projection.get("status"),
        "run_kernel_reduced": projection.get("run_kernel_reduced") is True,
        "run_kernel_reduction_pending": (
            projection.get("run_kernel_reduction_pending") is True
        ),
        "proposed_for_runkernel_reduction": (
            projection.get("proposed_for_runkernel_reduction") is True
        ),
        "top_candidate_ref": _safe_mapping(triage.get("top_candidate_ref")),
        "selected_candidate_ref": _safe_mapping(triage.get("selected_candidate_ref")),
        "dprime_review_candidate_ref": _safe_mapping(
            triage.get("dprime_review_candidate_ref")
        )
        or _safe_mapping(dossier.get("dprime_review_candidate_ref")),
        "strict_answer_support_candidate_refs": [
            _safe_mapping(item)
            for item in _safe_sequence(
                triage.get("strict_answer_support_candidate_refs")
            )
        ],
        "contextual_candidate_refs": [
            _safe_mapping(item)
            for item in _safe_sequence(triage.get("contextual_candidate_refs"))
        ],
        "overclaim_risk_candidate_refs": [
            _safe_mapping(item)
            for item in _safe_sequence(triage.get("overclaim_risk_candidate_refs"))
        ],
        "evidence_role_proposal_refs": [
            _safe_mapping(item)
            for item in _safe_sequence(workbench.get("evidence_role_proposal_refs"))
        ],
        "analyst_finding_proposal_refs": [
            _safe_mapping(item)
            for item in _safe_sequence(workbench.get("analyst_finding_proposal_refs"))
        ],
        "specialist_lane": _safe_mapping(workbench.get("specialist_lane_placeholder")),
        "economist_lane": _safe_mapping(workbench.get("economist_lane_placeholder")),
        "scrutineer_lane": _safe_mapping(workbench.get("scrutineer_lane_placeholder")),
        "analysis_gap_search_proposal": _without_empty(
            {
                "gap_status": gap.get("gap_status"),
                "gap_kind": gap.get("gap_kind"),
                "gap_reason": gap.get("gap_reason"),
                "live_followup_required": gap.get("live_followup_required"),
                "live_followup_licensed": gap.get("live_followup_licensed"),
                "proposed_runkernel_reduction_status": gap.get(
                    "proposed_runkernel_reduction_status"
                ),
            }
        ),
        "display_candidate_ref_status": workbench.get("display_candidate_ref_status"),
        "non_authority_flags": {
            "proposal_only": workbench.get("proposal_only") is True
            or projection.get("proposal_only") is True,
            "evidence_admitted": False,
            "source_obligation_satisfied": False,
            "citation_eligible": False,
            "source_authority_finalized": False,
            "product_correctness_claimed": False,
        },
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "source_text_retained": False,
    }


def _current_source_record_gap_reentry_report_section(
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    ref = _safe_mapping(packet.get("workbench_gap_reentry_ref"))
    return {
        "schema_version": "current_source_record_gap_reentry_section_v1",
        "workbench_gap_reentry_ref": ref,
        "workbench_gap_reentry_status": ref.get("workbench_gap_reentry_status"),
        "workbench_gap_proposal_ref": _safe_mapping(
            ref.get("workbench_gap_proposal_ref")
        ),
        "dprime_gap_ref": _safe_mapping(ref.get("dprime_gap_ref")),
        "followup_search_intent_ref": _safe_mapping(
            ref.get("followup_search_intent_ref")
        ),
        "runkernel_followup_authorization_ref": _safe_mapping(
            ref.get("runkernel_followup_authorization_ref")
        ),
        "runkernel_followup_authorization_status": ref.get(
            "runkernel_followup_authorization_status"
        ),
        "ordinary_search_path_reused": ref.get("ordinary_search_path_reused") is True,
        "ordinary_search_reentry_intent_status": ref.get(
            "ordinary_search_reentry_intent_status"
        ),
        "followup_execution_licensed": ref.get("followup_execution_licensed") is True,
        "followup_execution_status": ref.get("followup_execution_status"),
        "provider_called": ref.get("provider_called") is True,
        "live_search_called": ref.get("live_search_called") is True,
        "fetch_read_executed": ref.get("fetch_read_executed") is True,
        "dprime_dispatch_owner": ref.get("dprime_dispatch_owner") is True,
        "workbench_dispatch_owner": ref.get("workbench_dispatch_owner") is True,
        "new_search_subsystem_created": ref.get("new_search_subsystem_created") is True,
        "evidence_claimed": ref.get("evidence_admitted") is True,
        "source_obligation_satisfied": ref.get("source_obligation_satisfied") is True,
        "citation_eligible": ref.get("citation_eligible") is True,
        "source_authority_finalized": ref.get("source_authority_finalized") is True,
        "fap_or_author_created": bool(
            ref.get("final_answer_packet_created") or ref.get("author_prose_created")
        ),
        "product_correctness_claimed": ref.get("product_correctness_claimed") is True,
        "honest_authority_language": (
            "This local gap re-entry section is proposal/blocker status unless "
            "runkernel_followup_authorization_ref is present."
        ),
    }


def _format_current_source_record_single_fact_review_report(
    report: Mapping[str, Any],
) -> str:
    safe = _safe_mapping(report)
    contract = _safe_mapping(safe.get("answer_contract_lifecycle"))
    propagation = _safe_mapping(safe.get("claim_propagation_lifecycle"))
    stages = _safe_mapping(safe.get("stage_lifecycle"))
    answer_path = _safe_mapping(stages.get("answer_path"))
    analyst_workbench = _safe_mapping(safe.get("analyst_workbench"))
    gap_reentry = _safe_mapping(safe.get("gap_reentry"))
    gap = _safe_mapping(analyst_workbench.get("analysis_gap_search_proposal"))
    scrutineer = _safe_mapping(analyst_workbench.get("scrutineer_lane"))
    specialist = _safe_mapping(analyst_workbench.get("specialist_lane"))
    economist = _safe_mapping(analyst_workbench.get("economist_lane"))
    non_claims = _safe_mapping(safe.get("non_claims"))
    lines = [
        "# Current Source Record Single-Fact Review Report",
        "",
        f"- Decision: {safe.get('decision')}",
        f"- Blocker: {safe.get('blocker_code') or 'none'}",
        "- Selected claim bound to current answer contract: "
        f"{_bool_text(contract.get('selected_claim_bound_to_current_answer_contract'))}",
        f"- Selected current value: {propagation.get('selected_current_value') or 'not present'}",
        f"- FAP safe claim text present: {_bool_text(bool(propagation.get('fap_safe_claim_text')))}",
        f"- Product answer text present: {_bool_text(propagation.get('product_answer_text_present'))}",
        "",
        "## Contract Lifecycle",
        f"- Projection kind: {contract.get('projection_kind') or 'not present'}",
        f"- Projection digest: {contract.get('projection_digest') or 'not present'}",
        f"- Component: {_safe_mapping(contract.get('component_ref')).get('component_id') or 'not present'}",
        "- Source obligation: "
        f"{_safe_mapping(contract.get('source_obligation_ref')).get('source_obligation_id') or 'not present'}",
        f"- Missing lineage checks: {', '.join(_safe_sequence(contract.get('lineage_missing'))) or 'none'}",
        "",
        "## Claim Propagation",
        f"- SemanticObservation: {_safe_mapping(propagation.get('semantic_observation_ref')).get('observation_digest') or 'not present'}",
        f"- ComponentCoverage: {_safe_mapping(propagation.get('component_coverage_ref')).get('coverage_record_digest') or 'not present'}",
        f"- SufficiencyReadiness: {_safe_mapping(propagation.get('sufficiency_readiness_ref')).get('readiness_digest') or 'not present'}",
        f"- FAP safe claim: {_bool_text(bool(propagation.get('fap_safe_claim_ref')))}",
        f"- Author safe claim: {_bool_text(bool(propagation.get('author_safe_claim_ref')))}",
        "",
        "## Analyst Workbench",
        "- Product path consumed: "
        f"{_bool_text(analyst_workbench.get('product_path_consumed'))}",
        "- Candidate triage: "
        f"{_safe_mapping(analyst_workbench.get('candidate_evidence_triage_ref')).get('packet_digest') or 'not present'}",
        "- D-prime dossier consumed: "
        f"{_bool_text(analyst_workbench.get('workbench_dprime_dossier_consumed_by_dprime'))}",
        "- Workbench reduction projection: "
        f"{analyst_workbench.get('workbench_reduction_projection_status') or 'not reached'}",
        "- RunKernel reduction pending: "
        f"{_bool_text(analyst_workbench.get('run_kernel_reduction_pending'))}",
        f"- Scrutineer lane: {scrutineer.get('status') or 'not reached'}",
        f"- Specialist lane: {specialist.get('status') or 'not reached'}",
        f"- Economist lane: {economist.get('status') or 'not reached'}",
        "- Gap proposal: "
        f"{gap.get('gap_status') or 'not present'} / {gap.get('gap_kind') or 'none'}",
        "- Strict candidates: "
        f"{len(_safe_sequence(analyst_workbench.get('strict_answer_support_candidate_refs')))}",
        "- Contextual candidates: "
        f"{len(_safe_sequence(analyst_workbench.get('contextual_candidate_refs')))}",
        "- Overclaim-risk candidates: "
        f"{len(_safe_sequence(analyst_workbench.get('overclaim_risk_candidate_refs')))}",
        "- Workbench authority: proposal-only",
        "",
        "## Gap Re-entry",
        f"- Status: {gap_reentry.get('workbench_gap_reentry_status') or 'not reached'}",
        "- Workbench gap proposal: "
        f"{_safe_mapping(gap_reentry.get('workbench_gap_proposal_ref')).get('proposal_digest') or 'not present'}",
        "- D-prime gap posture: "
        f"{_safe_mapping(gap_reentry.get('dprime_gap_ref')).get('support_relation') or 'not present'}",
        "- Follow-up intent ref: "
        f"{_safe_mapping(gap_reentry.get('followup_search_intent_ref')).get('packet_digest') or 'not created'}",
        "- RunKernel authorization reducer status: "
        f"{gap_reentry.get('runkernel_followup_authorization_status') or 'not reached'}",
        "- Reducer-produced authorization ref: "
        f"{_safe_mapping(gap_reentry.get('runkernel_followup_authorization_ref')).get('authorization_digest') or 'not created'}",
        "- Ordinary search path reused/intended: "
        f"{_bool_text(gap_reentry.get('ordinary_search_path_reused'))}",
        "- Follow-up execution licensed: "
        f"{_bool_text(gap_reentry.get('followup_execution_licensed'))}",
        "- Follow-up execution status: "
        f"{gap_reentry.get('followup_execution_status') or 'not reached'}",
        "- Provider/search/fetch-read executed: "
        f"{_bool_text(gap_reentry.get('provider_called'))}/"
        f"{_bool_text(gap_reentry.get('live_search_called'))}/"
        f"{_bool_text(gap_reentry.get('fetch_read_executed'))}",
        "- D-prime dispatched search directly: "
        f"{_bool_text(gap_reentry.get('dprime_dispatch_owner'))}",
        "- Workbench dispatched search directly: "
        f"{_bool_text(gap_reentry.get('workbench_dispatch_owner'))}",
        "- New search subsystem created: "
        f"{_bool_text(gap_reentry.get('new_search_subsystem_created'))}",
        "- Evidence/source-obligation/citation/FAP/Author/correctness claimed: "
        f"{_bool_text(gap_reentry.get('evidence_claimed'))}/"
        f"{_bool_text(gap_reentry.get('source_obligation_satisfied'))}/"
        f"{_bool_text(gap_reentry.get('citation_eligible'))}/"
        f"{_bool_text(gap_reentry.get('fap_or_author_created'))}/"
        f"{_bool_text(gap_reentry.get('product_correctness_claimed'))}",
        "",
        "## Answer Path",
        f"- SufficiencyReadiness status: {answer_path.get('sufficiency_readiness_status') or 'not reached'}",
        f"- FinalAnswerPacket status: {answer_path.get('final_answer_packet_status') or 'not reached'}",
        f"- Author status: {answer_path.get('author_answer_status') or 'not reached'}",
        f"- Source display status: {answer_path.get('citation_source_display_status') or 'not reached'}",
        "",
        "## Non-Claims",
        "- Live product run executed: "
        f"{_bool_text(non_claims.get('live_product_run_executed'))}",
        "- Live validation correctness claimed: "
        f"{_bool_text(non_claims.get('live_validation_correctness_claimed'))}",
        "- Product correctness claimed: "
        f"{_bool_text(non_claims.get('product_correctness_claimed'))}",
        "- Raw/private retained: false",
    ]
    return "\n".join(lines) + "\n"


def _packet_from_semantic_status(
    *,
    relation_plan: Mapping[str, Any],
    run_id: str,
    retained_root: Path,
    counts: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    disambiguation_record: Mapping[str, Any] | None,
    semantic_payload: Mapping[str, Any],
    status_decision: str,
    confirm_live_dprime_review: bool,
    confirm_live_source_challenge_recovery: bool,
    source_obligation_recovery_authorization: Mapping[str, Any] | None,
    source_challenge_recovery: Mapping[str, Any] | None,
    initial_model_planning_packet: Mapping[str, Any] | None,
    recovery_model_planning_packet: Mapping[str, Any] | None,
    require_model_assisted_planning: bool,
    entrypoint_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    decision = _mapped_live_decision(
        status_decision,
        model_review_licensed=confirm_live_dprime_review,
    )
    recovery_decision = _source_challenge_recovery_decision(
        source_challenge_recovery,
        fallback_decision=decision,
    )
    decision = recovery_decision
    blocker_detail = _mapped_blocker_detail(
        decision=decision,
        status_decision=status_decision,
        original_detail=_clean_text(semantic_payload.get("blocker_detail"), limit=900)
        or "",
        model_review_licensed=confirm_live_dprime_review,
    )
    packet = _base_packet(
        relation_plan=relation_plan,
        query_retained=True,
        run_id=run_id,
        retained_root=retained_root,
        counts=counts,
        acquisition_plan=acquisition_plan,
        disambiguation_record=disambiguation_record,
        confirm_live_dprime_review=confirm_live_dprime_review,
        confirm_live_source_challenge_recovery=confirm_live_source_challenge_recovery,
        source_obligation_recovery_authorization=(
            source_obligation_recovery_authorization
        ),
        source_challenge_recovery=source_challenge_recovery,
        initial_model_planning_packet=initial_model_planning_packet,
        recovery_model_planning_packet=recovery_model_planning_packet,
        require_model_assisted_planning=require_model_assisted_planning,
        caps_exhausted=False,
        semantic_payload=semantic_payload,
        entrypoint_metadata=entrypoint_metadata,
    )
    blocker_detail = _source_challenge_recovery_detail(
        source_challenge_recovery,
        fallback_detail=blocker_detail,
    )
    source_readiness_gateway = _source_readiness_gateway_from_packet(
        packet,
        semantic_payload=semantic_payload,
    )
    dprime_authority_integration = _dprime_authority_integration_from_gateway(
        source_readiness_gateway=source_readiness_gateway,
        semantic_payload=semantic_payload,
    )
    source_citation_display_boundary = (
        _source_citation_display_boundary_from_authority(
            source_readiness_gateway=source_readiness_gateway,
            dprime_authority_integration=dprime_authority_integration,
            semantic_payload=semantic_payload,
        )
    )
    answer_path_ref = _dprime_answer_path_ref(semantic_payload)
    answer_path_decision = _dprime_answer_path_decision(answer_path_ref)
    answer_path_passed = answer_path_decision == PASS_DECISION
    product_entrypoint = (
        entrypoint_metadata.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    )
    answer_path_safe_claim_text = _clean_text(
        answer_path_ref.get("safe_answer_claim_text"),
        limit=4_000,
    )
    claim_lineage = _current_source_record_contract_claim_lineage(
        packet=packet,
        source_readiness_gateway=source_readiness_gateway,
        answer_path_ref=answer_path_ref,
        semantic_payload=semantic_payload,
    )
    product_answer_text = (
        answer_path_safe_claim_text
        if product_entrypoint and answer_path_passed
        else ""
    )
    if dprime_authority_integration.get("status") == "blocked":
        decision = BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD
        blocker_detail = _clean_text(
            dprime_authority_integration.get("blocker_detail"),
            limit=900,
        ) or (
            "Existing D-prime source-obligation/citation authority cannot be "
            "safely consumed by generic dogfood yet."
        )
    elif product_entrypoint and answer_path_passed and not answer_path_safe_claim_text:
        decision = BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING
        blocker_detail = (
            "The product answer path consumed the existing D-prime stages, but "
            "the selected current value did not reach a FAP safe-claim field."
        )
        product_answer_text = ""
    elif (
        product_entrypoint
        and answer_path_passed
        and claim_lineage.get("contract_accountable") is not True
    ):
        decision = BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE
        blocker_detail = (
            _clean_text(claim_lineage.get("blocker_detail"), limit=900)
            or "The selected answer claim could not be shown as bound to the "
            "current answer contract component and source obligation."
        )
        product_answer_text = ""
    elif answer_path_passed:
        decision = PASS_DECISION
        blocker_detail = None
    elif answer_path_decision in EXISTING_DPRIME_ANSWER_PATH_BLOCKERS:
        decision = answer_path_decision
        blocker_detail = (
            _clean_text(answer_path_ref.get("blocker_detail"), limit=900)
            or "Existing D-prime single-lane answer path stopped at a named surface."
        )
    elif (
        product_entrypoint
        and packet.get("workbench_gap_reentry_status") == "followup_not_licensed"
    ):
        decision = BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED
        if (
            _safe_mapping(packet.get("workbench_gap_reentry_ref")).get(
                "workbench_gap_kind"
            )
            == "unreadable_high_value_candidate"
        ):
            blocker_detail = (
                "Official source read support is needed. A high-value official "
                "artifact was found, but bounded PDF/table text support is not "
                "available in this run."
            )
        else:
            blocker_detail = (
                "Official strict support follow-up is needed; the Workbench/D-prime "
                "gap remains proposal-only because live follow-up execution is not "
                "licensed."
            )
    elif source_citation_display_boundary.get("status") == "created":
        decision = BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED
        blocker_detail = _clean_text(
            source_citation_display_boundary.get("blocker_detail"),
            limit=900,
        ) or (
            "Generic dogfood displayed consumed D-prime source/citation handoff "
            "material and stops before SufficiencyReadiness, FAP, Author, "
            "final citation rendering, and product correctness."
        )
    elif source_readiness_gateway.get("status") == "ready":
        decision = PASS_DECISION
        blocker_detail = None
    elif source_readiness_gateway.get("dprime_pass_evaluated") is True:
        decision = (
            _clean_text(source_readiness_gateway.get("blocker_code"), limit=220)
            or BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_STATE_MISSING
        )
        blocker_detail = _clean_text(
            source_readiness_gateway.get("blocker_detail"),
            limit=900,
        ) or "Source/readiness gateway required current-path state is missing."
    packet.update(
        {
            "decision": decision,
            "status_decision": status_decision,
            "blocker_code": None if decision == PASS_DECISION else decision,
            "blocker_detail": None if decision == PASS_DECISION else blocker_detail,
            "source_readiness_gateway": source_readiness_gateway,
            "source_readiness_gateway_status": source_readiness_gateway.get("status"),
            "source_readiness_gateway_blocker": source_readiness_gateway.get(
                "blocker_code"
            ),
            "single_relation_dprime_authority_integration": (
                dprime_authority_integration
            ),
            "dprime_authority_integration": dprime_authority_integration,
            "single_relation_dprime_authority_integration_status": (
                dprime_authority_integration.get("status")
            ),
            "single_relation_dprime_authority_integration_blocker": (
                dprime_authority_integration.get("blocker_code")
            ),
            "source_obligation_citation_readiness_status": (
                dprime_authority_integration.get("status")
            ),
            "source_obligation_citation_readiness_blocker": (
                dprime_authority_integration.get("blocker_code")
            ),
            "source_citation_display_boundary": source_citation_display_boundary,
            "source_citation_display_boundary_status": (
                source_citation_display_boundary.get("status")
            ),
            "source_citation_display_boundary_blocker": (
                source_citation_display_boundary.get("blocker_code")
            ),
            "source_citation_display_entries": list(
                _safe_sequence(
                    source_citation_display_boundary.get(
                        "source_citation_display_entries"
                    )
                )
            ),
            "source_citation_display_entries_created": (
                source_citation_display_boundary.get(
                    "source_citation_display_entries_created"
                )
                is True
            ),
            "source_citation_display_authority_source": (
                source_citation_display_boundary.get("authority_source")
            ),
            "source_citation_display_derived_from_dprime_authority": (
                source_citation_display_boundary.get(
                    "derived_from_dprime_authority"
                )
                is True
            ),
            "source_citation_display_derived_from_gateway_only": (
                source_citation_display_boundary.get(
                    "derived_from_gateway_only"
                )
                is True
            ),
            "next_product_path_checkpoint": (
                ANSWER_PATH_NEXT_PRODUCT_CHECKPOINT
                if answer_path_passed
                else answer_path_ref.get("next_blocked_surface")
                if answer_path_decision in EXISTING_DPRIME_ANSWER_PATH_BLOCKERS
                else source_citation_display_boundary.get(
                    "next_product_path_checkpoint"
                )
                or dprime_authority_integration.get("next_product_path_checkpoint")
            ),
            "final_citation_rendering_created": False,
            "dprime_source_citation_stoppoint_status": (
                dprime_authority_integration.get(
                    "dprime_source_citation_stoppoint_status"
                )
            ),
            "dprime_source_citation_stoppoint_blocker": (
                dprime_authority_integration.get(
                    "dprime_source_citation_stoppoint_blocker"
                )
            ),
            "source_obligation_authority_consumed": (
                dprime_authority_integration.get(
                    "source_obligation_authority_consumed"
                )
                is True
            ),
            "citation_source_handoff_authority_consumed": (
                dprime_authority_integration.get(
                    "citation_source_handoff_authority_consumed"
                )
                is True
            ),
            "single_relation_source_obligation_ready": (
                dprime_authority_integration.get(
                    "single_relation_source_obligation_ready"
                )
                is True
            ),
            "single_relation_citation_handoff_ready": (
                dprime_authority_integration.get(
                    "single_relation_citation_handoff_ready"
                )
                is True
            ),
            "dprime_pass_and_gateway_ready_rejected_as_readiness_authority": (
                dprime_authority_integration.get(
                    "gateway_ready_and_dprime_pass_insufficient_for_"
                    "source_obligation_citation_readiness"
                )
            ),
            "selected_current_value_display_status": (
                source_readiness_gateway.get("selected_current_value_display_status")
            ),
            "selected_current_value_text_present": bool(
                source_readiness_gateway.get("selected_current_value_text")
            ),
            "selected_current_value_to_fap_claim_lineage": claim_lineage,
            "product_claim_text_source": answer_path_ref.get("claim_text_source"),
            "product_claim_text_source_ref": answer_path_ref.get(
                "claim_text_source_ref"
            ),
            "product_claim_text_authority_path": answer_path_ref.get(
                "claim_text_authority_path"
            ),
            "safe_answer_claim_text": answer_path_safe_claim_text,
            "author_answer_text": _clean_text(
                answer_path_ref.get("answer_text"),
                limit=4_000,
            ),
            "answer_path_author_text_present": bool(
                _clean_text(answer_path_ref.get("answer_text"), limit=4_000)
            ),
            "answer_or_blocker_text": (
                (
                    product_answer_text
                    if product_entrypoint and product_answer_text
                    else "Existing D-prime single-lane answer path consumed "
                    "SufficiencyReadiness, hardened FinalAnswerPacket, "
                    "AuthorProse, and D-prime citation/source display. "
                    "Product correctness is not claimed."
                )
                if decision == PASS_DECISION and answer_path_passed
                else _source_readiness_gateway_summary(source_readiness_gateway)
                if decision == PASS_DECISION
                else f"Blocked before answer: {decision}. {blocker_detail}".strip()
            ),
            "product_answer_text": product_answer_text or "",
            "answer_text_present": bool(
                product_entrypoint and decision == PASS_DECISION and product_answer_text
            ),
            "source_display_entries": (
                list(
                    _safe_sequence(
                        source_citation_display_boundary.get(
                            "source_citation_display_entries"
                        )
                    )
                )
                if product_entrypoint and decision == PASS_DECISION and product_answer_text
                else []
            ),
            "dprime_answer_path_ref": answer_path_ref,
            "dprime_single_lane_answer_path_status": (
                answer_path_ref.get("status") or "not reached"
            ),
            "answer_path_existing_blocker": (
                answer_path_ref.get("blocker")
                if answer_path_decision in EXISTING_DPRIME_ANSWER_PATH_BLOCKERS
                else None
            ),
            "answer_path_next_blocked_surface": answer_path_ref.get(
                "next_blocked_surface"
            ),
            "final_answer_packet_created": answer_path_passed,
            "author_prose_created": answer_path_passed,
            "author_answer_created": answer_path_passed,
            "citation_source_display_created": answer_path_passed,
            "fap_opened": answer_path_passed,
            "author_opened": answer_path_passed,
            "fap_author_opened": answer_path_passed,
            "decision_made_by_the_run": (
                "existing_dprime_single_lane_answer_path_consumed"
                if decision == PASS_DECISION and answer_path_passed
                else
                "existing_dprime_single_lane_answer_path_blocker_recorded"
                if decision in EXISTING_DPRIME_ANSWER_PATH_BLOCKERS
                else
                "product_safe_claim_adapter_missing"
                if decision == BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING
                else
                "product_current_source_record_contract_lineage_missing"
                if decision == BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE
                else
                "current_source_record_followup_not_licensed"
                if decision == BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED
                else
                "generic_single_relation_dprime_authority_integration_blocked"
                if decision
                == BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD
                else
                "generic_single_relation_source_citation_display_boundary_emitted"
                if decision
                == BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED
                else
                "generic_single_relation_dprime_source_citation_stoppoint_consumed"
                if decision
                == BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED
                else
                "generic_single_relation_source_readiness_gateway_emitted"
                if decision == PASS_DECISION
                else "generic_single_relation_live_dogfood_named_blocker_recorded"
            ),
        }
    )
    packet["failure_attribution_bucket"] = _failure_attribution_bucket(packet)
    return packet


def _dprime_answer_path_ref(semantic_payload: Mapping[str, Any]) -> dict[str, Any]:
    return _safe_mapping(_safe_mapping(semantic_payload).get("dprime_answer_path_ref"))


def _dprime_answer_path_decision(answer_path_ref: Mapping[str, Any]) -> str | None:
    ref = _safe_mapping(answer_path_ref)
    if ref.get("status") == "consumed":
        return PASS_DECISION
    blocker = _clean_text(ref.get("blocker"), limit=220)
    if blocker in EXISTING_DPRIME_ANSWER_PATH_BLOCKERS:
        return blocker
    return None


def _current_source_record_contract_claim_lineage(
    *,
    packet: Mapping[str, Any],
    source_readiness_gateway: Mapping[str, Any],
    answer_path_ref: Mapping[str, Any],
    semantic_payload: Mapping[str, Any],
) -> dict[str, Any]:
    gateway = _safe_mapping(source_readiness_gateway)
    answer_path = _safe_mapping(answer_path_ref)
    semantic = _safe_mapping(semantic_payload)
    dprime = _safe_mapping(semantic.get("dprime_status"))
    contract_projection = _safe_mapping(
        packet.get("single_relation_answer_contract_projection")
    )
    contract_component = _safe_mapping(contract_projection.get("component_ref"))
    contract_source_obligation = _safe_mapping(
        contract_projection.get("source_obligation_ref")
    )
    authority_ref = _safe_mapping(
        semantic.get("accepted_current_answer_contract_authority_ref")
    ) or _safe_mapping(dprime.get("accepted_current_answer_contract_authority_ref"))
    selected_source = _safe_mapping(gateway.get("selected_source_ref"))
    selected_value = _clean_text(gateway.get("selected_current_value_text"), limit=1_000)
    safe_claim = _clean_text(answer_path.get("safe_answer_claim_text"), limit=1_000)
    plan_component_id = _clean_text(packet.get("component_id"), limit=320)
    plan_source_obligation_id = _clean_text(packet.get("source_obligation_id"), limit=320)
    bound_component_id = _clean_text(
        answer_path.get("bound_contract_component_id"),
        limit=320,
    )
    bound_source_obligation_id = _clean_text(
        answer_path.get("bound_contract_source_obligation_id"),
        limit=320,
    )
    source_ids = _lineage_source_obligation_ids(contract_source_obligation)
    checks = {
        "selected_current_value_present": bool(selected_value),
        "safe_fap_claim_present": bool(safe_claim),
        "selected_value_matches_safe_claim": bool(
            selected_value and safe_claim and selected_value == safe_claim
        ),
        "selected_source_present": bool(
            _clean_text(selected_source.get("url"), limit=700)
        ),
        "contract_projection_present": bool(contract_projection),
        "acquisition_consumed_current_answer_contract": bool(
            packet.get("acquisition_plan_consumed_by_product_path")
        ),
        "contract_component_matches": bool(
            plan_component_id
            and contract_component.get("component_id") == plan_component_id
            and bound_component_id == plan_component_id
        ),
        "contract_source_obligation_matches": bool(
            plan_source_obligation_id
            and (
                contract_source_obligation.get("source_obligation_id")
                == plan_source_obligation_id
                or plan_source_obligation_id in source_ids
            )
            and (
                bound_source_obligation_id == plan_source_obligation_id
                or bound_source_obligation_id in source_ids
            )
        ),
        "answer_contract_authority_ref_present": bool(
            authority_ref.get("current_contract_digest")
            or authority_ref.get("accepted_contract_digest")
        ),
        "semantic_observation_ref_present": bool(
            _safe_mapping(answer_path.get("semantic_observation_ref")).get(
                "observation_digest"
            )
        ),
        "component_coverage_ref_present": bool(
            _safe_mapping(answer_path.get("component_coverage_ref")).get(
                "coverage_record_digest"
            )
        ),
        "sufficiency_readiness_ref_present": bool(
            _safe_mapping(answer_path.get("sufficiency_readiness_ref")).get(
                "readiness_digest"
            )
        ),
        "fap_safe_claim_ref_present": bool(
            _safe_mapping(answer_path.get("fap_safe_claim_ref")).get(
                "safe_answer_claim_text"
            )
            or _safe_mapping(answer_path.get("fap_safe_claim_ref")).get(
                "packet_digest"
            )
        ),
        "author_safe_claim_ref_present": bool(
            _safe_mapping(answer_path.get("author_safe_claim_ref")).get(
                "safe_answer_claim_text"
            )
            or _safe_mapping(answer_path.get("author_safe_claim_ref")).get(
                "author_prose_digest"
            )
        ),
    }
    missing = [key for key, passed in checks.items() if not passed]
    return _json_safe(
        _without_empty(
            {
                "contract_accountable": not missing,
                "checks": checks,
                "missing": missing,
                "blocker_detail": (
                    "Current-source record answer claim lineage missing: "
                    + ", ".join(missing)
                    + "."
                    if missing
                    else None
                ),
                "selected_current_value": selected_value,
                "safe_answer_claim_text": safe_claim,
                "selected_source_ref": {
                    "title": selected_source.get("title"),
                    "url": selected_source.get("url"),
                    "domain": selected_source.get("domain"),
                    "candidate_id": selected_source.get("candidate_id"),
                },
                "bound_contract_component_id": bound_component_id,
                "bound_contract_source_obligation_id": bound_source_obligation_id,
                "contract_projection_ref": {
                    "projection_kind": contract_projection.get("projection_kind"),
                    "projection_digest": contract_projection.get(
                        "projection_digest"
                    ),
                    "contract_owner": contract_projection.get("contract_owner"),
                    "component_id": contract_component.get("component_id"),
                    "source_obligation_id": contract_source_obligation.get(
                        "source_obligation_id"
                    ),
                },
                "accepted_current_answer_contract_authority_ref": authority_ref,
                "semantic_observation_ref": _safe_mapping(
                    answer_path.get("semantic_observation_ref")
                ),
                "component_coverage_ref": _safe_mapping(
                    answer_path.get("component_coverage_ref")
                ),
                "sufficiency_readiness_ref": _safe_mapping(
                    answer_path.get("sufficiency_readiness_ref")
                ),
                "fap_safe_claim_ref": _safe_mapping(
                    answer_path.get("fap_safe_claim_ref")
                ),
                "author_safe_claim_ref": _safe_mapping(
                    answer_path.get("author_safe_claim_ref")
                ),
                "authority_path": answer_path.get("claim_text_authority_path"),
            }
        )
    )


def _lineage_source_obligation_ids(source_obligation: Mapping[str, Any]) -> set[str]:
    ids = {
        _clean_text(source_obligation.get("source_obligation_id"), limit=320),
        _clean_text(source_obligation.get("obligation_id"), limit=320),
    }
    for item in _safe_sequence(source_obligation.get("source_obligation_candidate_ids")):
        text = _clean_text(item, limit=320)
        if text:
            ids.add(text)
    return {item for item in ids if item}


def _blocked_packet(
    *,
    blocker: str,
    detail: str,
    query_retained: bool,
    relation_plan: Mapping[str, Any] | None,
    run_id: str,
    retained_root: Path | None,
    counts: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    disambiguation_record: Mapping[str, Any] | None,
    caps_exhausted: bool,
    confirm_live_dprime_review: bool,
    confirm_live_source_challenge_recovery: bool,
    source_obligation_recovery_authorization: Mapping[str, Any] | None,
    source_challenge_recovery: Mapping[str, Any] | None,
    semantic_payload: Mapping[str, Any],
    hard_exclusion_category: str | None,
    initial_model_planning_packet: Mapping[str, Any] | None,
    recovery_model_planning_packet: Mapping[str, Any] | None,
    require_model_assisted_planning: bool,
    entrypoint_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    source_readiness_gateway = _source_readiness_gateway_not_reached(
        blocker=blocker,
        detail=detail,
    )
    dprime_authority_integration = _dprime_authority_integration_not_reached(
        blocker=blocker,
        detail=detail,
        source_readiness_gateway=source_readiness_gateway,
    )
    packet = _base_packet(
        relation_plan=relation_plan,
        query_retained=query_retained,
        run_id=run_id,
        retained_root=retained_root,
        counts=counts,
        acquisition_plan=acquisition_plan,
        disambiguation_record=disambiguation_record,
        confirm_live_dprime_review=confirm_live_dprime_review,
        confirm_live_source_challenge_recovery=confirm_live_source_challenge_recovery,
        source_obligation_recovery_authorization=(
            source_obligation_recovery_authorization
        ),
        source_challenge_recovery=source_challenge_recovery,
        initial_model_planning_packet=initial_model_planning_packet,
        recovery_model_planning_packet=recovery_model_planning_packet,
        require_model_assisted_planning=require_model_assisted_planning,
        caps_exhausted=caps_exhausted,
        semantic_payload=semantic_payload,
        entrypoint_metadata=entrypoint_metadata,
    )
    packet.update(
        {
            "decision": blocker,
            "status_decision": blocker,
            "blocker_code": blocker,
            "blocker_detail": detail,
            "hard_exclusion_category": hard_exclusion_category,
            "answer_or_blocker_text": f"Blocked before answer: {blocker}. {detail}",
            "product_answer_text": "",
            "answer_text_present": False,
            "source_display_entries": [],
            "source_readiness_gateway": source_readiness_gateway,
            "source_readiness_gateway_status": "not_reached",
            "source_readiness_gateway_blocker": blocker,
            "single_relation_dprime_authority_integration": (
                dprime_authority_integration
            ),
            "dprime_authority_integration": dprime_authority_integration,
            "single_relation_dprime_authority_integration_status": "not_reached",
            "single_relation_dprime_authority_integration_blocker": blocker,
            "source_obligation_citation_readiness_status": "not_reached",
            "source_obligation_citation_readiness_blocker": blocker,
            "source_citation_display_boundary": (
                _source_citation_display_boundary_not_reached(
                    blocker=blocker,
                    detail=detail,
                )
            ),
            "source_citation_display_boundary_status": "not_reached",
            "source_citation_display_boundary_blocker": blocker,
            "source_citation_display_entries": [],
            "source_citation_display_entries_created": False,
            "source_citation_display_authority_source": None,
            "source_citation_display_derived_from_dprime_authority": False,
            "source_citation_display_derived_from_gateway_only": False,
            "next_product_path_checkpoint": (
                dprime_authority_integration.get("next_product_path_checkpoint")
            ),
            "final_citation_rendering_created": False,
            "dprime_source_citation_stoppoint_status": "not_reached",
            "dprime_source_citation_stoppoint_blocker": blocker,
            "source_obligation_authority_consumed": False,
            "citation_source_handoff_authority_consumed": False,
            "single_relation_source_obligation_ready": False,
            "single_relation_citation_handoff_ready": False,
            "dprime_pass_and_gateway_ready_rejected_as_readiness_authority": False,
            "selected_current_value_display_status": "not_displayed",
            "selected_current_value_text_present": False,
            "decision_made_by_the_run": (
                "generic_single_relation_live_dogfood_blocker_recorded"
            ),
        }
    )
    packet["failure_attribution_bucket"] = _failure_attribution_bucket(packet)
    return packet


def _source_readiness_gateway_from_packet(
    packet: Mapping[str, Any],
    *,
    semantic_payload: Mapping[str, Any],
) -> dict[str, Any]:
    semantic = _safe_mapping(semantic_payload)
    dprime = _safe_mapping(semantic.get("dprime_status"))
    admission_ref = _safe_mapping(semantic.get("source_evidence_admission_ref"))
    selected_candidate = _selected_gateway_candidate(packet)
    selected_window = _selected_window_ref_from_dprime(dprime)
    source_ref = _selected_source_ref(
        packet=packet,
        relation_ref=_safe_mapping(semantic.get("dprime_relation_intake_ref")),
        selected_candidate=selected_candidate,
        admission_ref=admission_ref,
    )
    value_ref = _selected_current_value_ref(packet=packet, dprime=dprime)
    dprime_ref = _gateway_dprime_ref(dprime)
    contract_state = _safe_mapping(packet.get("single_relation_answer_contract_state"))
    dprime_pass_ready = _dprime_pass_ready_for_gateway(dprime)
    blocker, detail = _source_readiness_gateway_blocker(
        packet=packet,
        dprime_pass_ready=dprime_pass_ready,
        selected_candidate=selected_candidate,
        selected_window=selected_window,
        source_ref=source_ref,
        value_ref=value_ref,
        contract_state=contract_state,
    )
    status = "ready" if blocker is None else (
        "blocked" if dprime_pass_ready else "not_reached"
    )
    gateway = {
        "schema_version": SOURCE_READINESS_GATEWAY_SCHEMA_VERSION,
        "status": status,
        "gateway_owner": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "source_readiness_gateway"
        ),
        "runtime_consumer": packet.get("runtime_consumer"),
        "ordinary_product_path_consumed": True,
        "dprime_pass_evaluated": dprime_pass_ready,
        "blocker_code": blocker,
        "blocker_detail": detail,
        "query_ref": {
            "relation_plan_id": packet.get("relation_plan_id"),
            "component_id": packet.get("component_id"),
            "source_obligation_id": packet.get("source_obligation_id"),
            "search_requirement_id": packet.get("search_requirement_id"),
        },
        "selected_current_value_display_status": (
            "displayed_from_current_path_admitted_dprime_state"
            if status == "ready"
            else "blocked_current_path_state_missing"
            if dprime_pass_ready
            else "not_displayed"
        ),
        "selected_current_value_text": (
            value_ref.get("selected_current_value_text")
            if status == "ready"
            else None
        ),
        "selected_current_value_ref": value_ref,
        "selected_source_ref": source_ref,
        "selected_window_ref": selected_window,
        "custody_readability_ref": {
            "source_evidence_admission_ref": admission_ref,
            "fetch_read_completed": packet.get("fetch_read_completed"),
            "fetch_read_packet_created": packet.get("fetch_read_packet_created"),
            "source_acquisition_mode": packet.get("source_acquisition_mode"),
            "answer_bearing_candidate_window_status": packet.get(
                "answer_bearing_candidate_window_status"
            ),
        },
        "dprime_ref": dprime_ref,
        "model_assisted_planning_ref": {
            "provider": packet.get("model_assisted_planning_provider_used"),
            "model": packet.get("model_assisted_planning_model_used"),
            "endpoint": packet.get("model_assisted_planning_endpoint_used"),
            "call_count": packet.get("fast_planner_model_calls_attempted"),
            "status": packet.get("model_assisted_planning_reduced_status"),
        },
        "source_obligation_contract_ref": {
            "source_display_allowed": contract_state.get("source_display_allowed"),
            "answer_display_allowed": contract_state.get("answer_display_allowed"),
            "support_admission_allowed": contract_state.get(
                "support_admission_allowed"
            ),
            "blocker_status": contract_state.get("blocker_status"),
        },
        "explicit_non_claims": dict(SOURCE_READINESS_GATEWAY_NON_CLAIMS),
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "final_answer_prose_created": False,
        "source_display_entries_created": False,
        "source_obligation_satisfaction_used_for_display": False,
        "citation_eligibility_used_for_display": False,
        "product_correctness_claimed": False,
    }
    return _json_safe(gateway)


def _source_readiness_gateway_not_reached(
    *,
    blocker: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_READINESS_GATEWAY_SCHEMA_VERSION,
        "status": "not_reached",
        "gateway_owner": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "source_readiness_gateway"
        ),
        "runtime_consumer": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "build_generic_single_relation_live_dogfood_run_output"
        ),
        "ordinary_product_path_consumed": True,
        "dprime_pass_evaluated": False,
        "blocker_code": blocker,
        "blocker_detail": detail,
        "selected_current_value_display_status": "not_displayed",
        "selected_current_value_text": None,
        "selected_current_value_ref": {},
        "selected_source_ref": {},
        "selected_window_ref": {},
        "custody_readability_ref": {},
        "dprime_ref": {},
        "model_assisted_planning_ref": {},
        "source_obligation_contract_ref": {},
        "explicit_non_claims": dict(SOURCE_READINESS_GATEWAY_NON_CLAIMS),
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "final_answer_prose_created": False,
        "source_display_entries_created": False,
        "source_obligation_satisfaction_used_for_display": False,
        "citation_eligibility_used_for_display": False,
        "product_correctness_claimed": False,
    }


def _dprime_authority_integration_from_gateway(
    *,
    source_readiness_gateway: Mapping[str, Any],
    semantic_payload: Mapping[str, Any],
) -> dict[str, Any]:
    gateway = _safe_mapping(source_readiness_gateway)
    semantic = _safe_mapping(semantic_payload)
    dprime = _safe_mapping(semantic.get("dprime_status"))
    dprime_objects = _safe_mapping(dprime.get("objects_created"))
    source_authority_ref = _safe_mapping(
        semantic.get("source_obligation_authority_ref")
    )
    citation_handoff_ref = _safe_mapping(
        semantic.get("citation_eligibility_authority_ref")
    )
    answer_path_ref = _dprime_answer_path_ref(semantic)
    answer_path_decision = _dprime_answer_path_decision(answer_path_ref)
    answer_path_passed = answer_path_decision == PASS_DECISION
    answer_path_blocked = answer_path_decision in EXISTING_DPRIME_ANSWER_PATH_BLOCKERS
    gateway_ready = gateway.get("status") == "ready"
    dprime_pass_slice_present = _dprime_pass_ready_for_gateway(dprime)
    source_obligation_consumed = (
        dprime.get("source_obligation_authority_consumed") is True
        and source_authority_ref.get("authority_consumed") is True
        and source_authority_ref.get("status") == "consumed"
    )
    citation_handoff_consumed = (
        dprime.get("citation_eligibility_or_source_handoff_authority_consumed")
        is True
        and citation_handoff_ref.get("authority_consumed") is True
        and citation_handoff_ref.get("citation_source_handoff_consumed") is True
        and citation_handoff_ref.get("status") == "consumed"
    )
    source_citation_consumed = (
        gateway_ready
        and dprime_pass_slice_present
        and source_obligation_consumed
        and citation_handoff_consumed
    )
    reached = gateway_ready and dprime_pass_slice_present and not source_citation_consumed
    blocker_code = (
        PASS_DECISION
        if answer_path_passed
        else answer_path_decision
        if answer_path_blocked
        else
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED
        if source_citation_consumed
        else
        BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD
        if reached
        else _clean_text(gateway.get("blocker_code"), limit=220)
        or BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_STATE_MISSING
    )
    blocker_detail = (
        "Existing D-prime single-lane answer path consumed SufficiencyReadiness, "
        "hardened FinalAnswerPacket, AuthorProse, and D-prime source display."
        if answer_path_passed
        else _clean_text(answer_path_ref.get("blocker_detail"), limit=900)
        or "Existing D-prime single-lane answer path stopped at a named surface."
        if answer_path_blocked
        else
        "Existing D-prime source-obligation authority and citation-source "
        "handoff authority were consumed through the ordinary status path. "
        "Generic dogfood stops here because source/citation display, "
        "SufficiencyReadiness, FAP, Author, final citation rendering, and "
        "product correctness are closed in this phase."
        if source_citation_consumed
        else
        "Existing D-prime source-obligation/citation authority is present, "
        "but generic single-relation dogfood currently keeps "
        "dprime_downstream_authority_enabled=False. D-prime support-slice PASS "
        "plus #434 gateway display is insufficient for source-obligation or "
        "citation handoff readiness, and enabling the current downstream "
        "single-lane path would also open SufficiencyReadiness, FAP, Author, "
        "and citation/source display surfaces."
        if reached
        else _clean_text(gateway.get("blocker_detail"), limit=900)
        or "D-prime authority integration was not reached."
    )
    downstream_enabled = semantic.get("dprime_downstream_authority_enabled") is True
    downstream_objects_created = any(
        dprime_objects.get(key) is True
        for key in (
            "component_coverage",
            "final_answer_packet",
            "author_answer",
            "citation_source_display",
        )
    )
    status = "consumed" if source_citation_consumed else "blocked" if reached else "not_reached"
    next_checkpoint = (
        ANSWER_PATH_NEXT_PRODUCT_CHECKPOINT
        if answer_path_passed
        else answer_path_ref.get("next_blocked_surface")
        if answer_path_blocked
        else
        SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE
        if source_citation_consumed
        else DPRIME_AUTHORITY_INTEGRATION_NEXT_PHASE
    )
    return _json_safe(
        {
            "schema_version": DPRIME_AUTHORITY_INTEGRATION_SCHEMA_VERSION,
            "status": status,
            "blocker_code": blocker_code,
            "blocker_detail": blocker_detail,
            "integration_owner": (
                "proplex.mvp_single_relation_live_dogfood_run."
                "single_relation_dprime_authority_integration_blocker"
            ),
            "runtime_consumer": (
                "proplex.mvp_single_relation_live_dogfood_run."
                "build_generic_single_relation_live_dogfood_run_output"
            ),
            "ordinary_product_path_consumed": True,
            "existing_dprime_authority_referenced": True,
            "existing_dprime_authority_reused": source_citation_consumed,
            "existing_dprime_authority_modules": list(
                EXISTING_DPRIME_DOWNSTREAM_AUTHORITY_MODULE_REFS
            ),
            "existing_dprime_source_obligation_citation_authority_exists": True,
            "existing_dprime_source_obligation_citation_authority_module": (
                "core.dprime_source_obligation_citation_authority_runtime"
            ),
            "existing_single_lane_answer_path_module": (
                "core.dprime_single_lane_answer_path_runtime"
            ),
            "existing_dprime_authority_integration_blocked": reached,
            "dprime_downstream_authority_enabled": downstream_enabled,
            "dprime_source_citation_authority_enabled": (
                semantic.get("dprime_source_citation_authority_enabled") is True
            ),
            "dprime_single_lane_answer_path_enabled": (
                semantic.get("dprime_single_lane_answer_path_enabled") is True
            ),
            "generic_dogfood_downstream_authority_kept_disabled": (
                downstream_enabled is False
            ),
            "generic_dogfood_single_lane_answer_path_kept_disabled": (
                semantic.get("dprime_single_lane_answer_path_enabled") is not True
            ),
            "dprime_support_slice_present": dprime_pass_slice_present,
            "gateway_display_present": gateway_ready,
            "gateway_treated_as_authority": False,
            "dprime_support_slice_treated_as_readiness": False,
            "gateway_ready_and_dprime_pass_insufficient_for_"
            "source_obligation_citation_readiness": reached,
            "downstream_dprime_authority_invoked": (
                source_citation_consumed or downstream_enabled or downstream_objects_created
            ),
            "dprime_source_citation_authority_invoked": source_citation_consumed,
            "source_obligation_authority_consumed": source_obligation_consumed,
            "citation_source_handoff_authority_consumed": citation_handoff_consumed,
            "dprime_source_citation_stoppoint_status": (
                semantic.get("dprime_source_citation_stoppoint_status")
                or ("consumed" if source_citation_consumed else "not_reached")
            ),
            "dprime_source_citation_stoppoint_blocker": (
                semantic.get("dprime_source_citation_stoppoint_blocker")
                or blocker_code
            ),
            "dprime_single_lane_answer_path_status": (
                answer_path_ref.get("status") or "not reached"
            ),
            "dprime_single_lane_answer_path_blocker": (
                answer_path_ref.get("blocker") if answer_path_blocked else None
            ),
            "dprime_single_lane_answer_path_next_blocked_surface": (
                answer_path_ref.get("next_blocked_surface")
            ),
            "source_obligation_authority_ref": dict(source_authority_ref),
            "citation_source_handoff_authority_ref": dict(citation_handoff_ref),
            "source_obligation_authority_ref_owner": source_authority_ref.get(
                "owner"
            ),
            "citation_source_handoff_authority_ref_owner": citation_handoff_ref.get(
                "owner"
            ),
            "source_citation_authority_refs_are_dprime_runtime_refs": (
                source_authority_ref.get("runtime_surface")
                == "core.dprime_source_obligation_citation_authority_runtime"
                and citation_handoff_ref.get("runtime_surface")
                == "core.dprime_source_obligation_citation_authority_runtime"
            ),
            "source_readiness_gateway_is_authority": False,
            "component_coverage_created": dprime_objects.get("component_coverage")
            is True,
            "semantic_observation_created": dprime_objects.get("semantic_observation")
            is True,
            "source_obligation_satisfied": False,
            "citation_eligible": False,
            "source_authority_finalized": False,
            "single_relation_source_obligation_ready": source_obligation_consumed,
            "single_relation_citation_handoff_ready": citation_handoff_consumed,
            "final_answer_packet_created": answer_path_passed,
            "author_prose_created": answer_path_passed,
            "author_answer_created": answer_path_passed,
            "citation_source_display_created": answer_path_passed,
            "final_answer_prose_created": answer_path_passed,
            "fap_invoked": answer_path_passed,
            "author_invoked": answer_path_passed,
            "citation_rendering_invoked": False,
            "product_correctness_claimed": False,
            "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
            "next_phase": next_checkpoint,
            "next_product_path_checkpoint": next_checkpoint,
        }
    )


def _dprime_authority_integration_not_reached(
    *,
    blocker: str,
    detail: str,
    source_readiness_gateway: Mapping[str, Any],
) -> dict[str, Any]:
    return _json_safe(
        {
            "schema_version": DPRIME_AUTHORITY_INTEGRATION_SCHEMA_VERSION,
            "status": "not_reached",
            "blocker_code": blocker,
            "blocker_detail": detail,
            "integration_owner": (
                "proplex.mvp_single_relation_live_dogfood_run."
                "single_relation_dprime_authority_integration_blocker"
            ),
            "runtime_consumer": (
                "proplex.mvp_single_relation_live_dogfood_run."
                "build_generic_single_relation_live_dogfood_run_output"
            ),
            "ordinary_product_path_consumed": True,
            "existing_dprime_authority_referenced": True,
            "existing_dprime_authority_reused": False,
            "existing_dprime_authority_modules": list(
                EXISTING_DPRIME_DOWNSTREAM_AUTHORITY_MODULE_REFS
            ),
            "existing_dprime_source_obligation_citation_authority_exists": True,
            "existing_dprime_source_obligation_citation_authority_module": (
                "core.dprime_source_obligation_citation_authority_runtime"
            ),
            "existing_single_lane_answer_path_module": (
                "core.dprime_single_lane_answer_path_runtime"
            ),
            "existing_dprime_authority_integration_blocked": False,
            "dprime_downstream_authority_enabled": False,
            "dprime_source_citation_authority_enabled": False,
            "dprime_single_lane_answer_path_enabled": False,
            "generic_dogfood_downstream_authority_kept_disabled": True,
            "generic_dogfood_single_lane_answer_path_kept_disabled": True,
            "dprime_support_slice_present": False,
            "gateway_display_present": (
                _safe_mapping(source_readiness_gateway).get("status") == "ready"
            ),
            "gateway_treated_as_authority": False,
            "dprime_support_slice_treated_as_readiness": False,
            "gateway_ready_and_dprime_pass_insufficient_for_"
            "source_obligation_citation_readiness": False,
            "downstream_dprime_authority_invoked": False,
            "dprime_source_citation_authority_invoked": False,
            "source_obligation_authority_consumed": False,
            "citation_source_handoff_authority_consumed": False,
            "dprime_source_citation_stoppoint_status": "not_reached",
            "dprime_source_citation_stoppoint_blocker": blocker,
            "source_obligation_authority_ref": {},
            "citation_source_handoff_authority_ref": {},
            "source_obligation_authority_ref_owner": None,
            "citation_source_handoff_authority_ref_owner": None,
            "source_citation_authority_refs_are_dprime_runtime_refs": False,
            "source_readiness_gateway_is_authority": False,
            "component_coverage_created": False,
            "semantic_observation_created": False,
            "source_obligation_satisfied": False,
            "citation_eligible": False,
            "source_authority_finalized": False,
            "single_relation_source_obligation_ready": False,
            "single_relation_citation_handoff_ready": False,
            "final_answer_packet_created": False,
            "author_prose_created": False,
            "author_answer_created": False,
            "citation_source_display_created": False,
            "final_answer_prose_created": False,
            "fap_invoked": False,
            "author_invoked": False,
            "citation_rendering_invoked": False,
            "product_correctness_claimed": False,
            "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
            "next_phase": DPRIME_AUTHORITY_INTEGRATION_NEXT_PHASE,
            "next_product_path_checkpoint": DPRIME_AUTHORITY_INTEGRATION_NEXT_PHASE,
        }
    )


def _source_citation_display_boundary_from_authority(
    *,
    source_readiness_gateway: Mapping[str, Any],
    dprime_authority_integration: Mapping[str, Any],
    semantic_payload: Mapping[str, Any],
) -> dict[str, Any]:
    gateway = _safe_mapping(source_readiness_gateway)
    integration = _safe_mapping(dprime_authority_integration)
    semantic = _safe_mapping(semantic_payload)
    source_ref = _safe_mapping(integration.get("source_obligation_authority_ref"))
    citation_ref = _safe_mapping(
        integration.get("citation_source_handoff_authority_ref")
    )
    source_window = _safe_mapping(gateway.get("selected_window_ref"))
    authority_backed = _source_citation_display_authority_backed(
        integration=integration,
        source_ref=source_ref,
        citation_ref=citation_ref,
    )
    answer_path_ref = _dprime_answer_path_ref(semantic)
    if _dprime_answer_path_decision(answer_path_ref) == PASS_DECISION:
        return _source_citation_display_boundary_from_answer_path(
            source_readiness_gateway=gateway,
            dprime_authority_integration=integration,
            answer_path_ref=answer_path_ref,
            source_obligation_authority_ref=source_ref,
            citation_handoff_ref=citation_ref,
        )
    if not authority_backed:
        blocker = (
            _clean_text(integration.get("blocker_code"), limit=220)
            or _clean_text(gateway.get("blocker_code"), limit=220)
            or BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED
        )
        detail = (
            _clean_text(integration.get("blocker_detail"), limit=900)
            or _clean_text(gateway.get("blocker_detail"), limit=900)
            or "Source/citation display boundary requires consumed D-prime authority refs."
        )
        return _source_citation_display_boundary_not_reached(
            blocker=blocker,
            detail=detail,
        )

    entries = [
        _source_citation_display_boundary_entry(
            record=record,
            index=index,
            selected_value_text=gateway.get("selected_current_value_text"),
            selected_window=source_window,
            source_obligation_authority_ref=source_ref,
            citation_handoff_ref=citation_ref,
        )
        for index, record in enumerate(
            _safe_sequence(citation_ref.get("citation_source_records")),
            start=1,
        )
        if isinstance(record, Mapping)
    ]
    if not entries:
        return _source_citation_display_boundary_not_reached(
            blocker=BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED,
            detail=(
                "D-prime citation-source handoff authority was consumed but "
                "provided no safe source records for the generic display boundary."
            ),
        )

    boundary = {
        "schema_version": SOURCE_CITATION_DISPLAY_BOUNDARY_SCHEMA_VERSION,
        "status": "created",
        "blocker_code": BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED,
        "blocker_detail": (
            "Source/citation display boundary was created from consumed D-prime "
            "source-obligation and citation-source handoff authority. "
            "Generic dogfood stops next because SufficiencyReadiness, FAP, "
            "Author, final citation rendering, and product correctness remain "
            "closed in this phase."
        ),
        "boundary_owner": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "source_citation_display_boundary"
        ),
        "runtime_consumer": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "build_generic_single_relation_live_dogfood_run_output"
        ),
        "ordinary_product_path_consumed": True,
        "authority_source": (
            "core.dprime_source_obligation_citation_authority_runtime"
        ),
        "source_citation_display_entries": entries,
        "source_citation_display_entries_created": True,
        "entry_count": len(entries),
        "derived_from_dprime_authority": True,
        "derived_from_gateway_only": False,
        "gateway_treated_as_authority": False,
        "source_obligation_authority_consumed": True,
        "citation_source_handoff_authority_consumed": True,
        "source_obligation_authority_ref_owner": source_ref.get("owner"),
        "citation_source_handoff_authority_ref_owner": citation_ref.get("owner"),
        "source_citation_authority_refs_are_dprime_runtime_refs": True,
        "source_obligation_authority_ref": _source_obligation_boundary_ref(source_ref),
        "citation_source_handoff_authority_ref": _citation_handoff_boundary_ref(
            citation_ref
        ),
        "source_readiness_gateway_ref": {
            "status": gateway.get("status"),
            "selected_current_value_display_status": gateway.get(
                "selected_current_value_display_status"
            ),
            "selected_source_ref": gateway.get("selected_source_ref"),
            "selected_window_digest": source_window.get("selected_window_digest"),
            "selected_window_char_count": source_window.get(
                "selected_window_char_count"
            ),
        },
        "dprime_source_citation_stoppoint_status": integration.get(
            "dprime_source_citation_stoppoint_status"
        ),
        "dprime_source_citation_stoppoint_blocker": integration.get(
            "dprime_source_citation_stoppoint_blocker"
        ),
        "semantic_status_decision": semantic.get("decision"),
        "explicit_non_claims": dict(SOURCE_CITATION_DISPLAY_BOUNDARY_NON_CLAIMS),
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "sufficiency_readiness_created": False,
        "final_answer_prose_created": False,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "author_invoked": False,
        "citation_rendering_invoked": False,
        "final_citation_rendering_created": False,
        "product_correctness_claimed": False,
        "nonclaim_labels": [
            "display boundary only",
            "not final answer prose",
            "not final citation rendering",
            "not product correctness",
        ],
        "next_product_path_checkpoint": SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE,
    }
    boundary["boundary_digest"] = _digest_json(
        {
            "schema_version": boundary["schema_version"],
            "authority_source": boundary["authority_source"],
            "entries": entries,
            "source_obligation_authority_digest": source_ref.get(
                "source_obligation_authority_digest"
            ),
            "citation_source_handoff_digest": citation_ref.get(
                "citation_source_handoff_digest"
            ),
        }
    )
    return _json_safe(boundary)


def _source_citation_display_boundary_from_answer_path(
    *,
    source_readiness_gateway: Mapping[str, Any],
    dprime_authority_integration: Mapping[str, Any],
    answer_path_ref: Mapping[str, Any],
    source_obligation_authority_ref: Mapping[str, Any],
    citation_handoff_ref: Mapping[str, Any],
) -> dict[str, Any]:
    gateway = _safe_mapping(source_readiness_gateway)
    integration = _safe_mapping(dprime_authority_integration)
    answer_path = _safe_mapping(answer_path_ref)
    display = _safe_mapping(answer_path.get("citation_source_display"))
    source_ref = _safe_mapping(source_obligation_authority_ref)
    citation_ref = _safe_mapping(citation_handoff_ref)
    source_window = _safe_mapping(gateway.get("selected_window_ref"))
    entries = [
        _source_citation_display_boundary_answer_path_entry(
            record=record,
            index=index,
            selected_value_text=gateway.get("selected_current_value_text"),
            selected_window=source_window,
            source_obligation_authority_ref=source_ref,
            citation_handoff_ref=citation_ref,
        )
        for index, record in enumerate(
            _safe_sequence(display.get("citation_source_entries")),
            start=1,
        )
        if isinstance(record, Mapping)
    ]
    if not entries:
        return _source_citation_display_boundary_not_reached(
            blocker="BLOCKED_DPRIME_CITATION_RENDERING_AUTHORITY_MISSING",
            detail=(
                "D-prime answer path was consumed, but its source display did "
                "not expose safe display entries."
            ),
        )
    boundary = {
        "schema_version": SOURCE_CITATION_DISPLAY_BOUNDARY_SCHEMA_VERSION,
        "status": "created",
        "blocker_code": PASS_DECISION,
        "blocker_detail": None,
        "boundary_owner": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "source_citation_display_boundary"
        ),
        "runtime_consumer": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "build_generic_single_relation_live_dogfood_run_output"
        ),
        "ordinary_product_path_consumed": True,
        "authority_source": "core.dprime_single_lane_answer_path_runtime",
        "source_citation_display_entries": entries,
        "source_citation_display_entries_created": True,
        "entry_count": len(entries),
        "derived_from_dprime_authority": True,
        "derived_from_gateway_only": False,
        "gateway_treated_as_authority": False,
        "source_obligation_authority_consumed": True,
        "citation_source_handoff_authority_consumed": True,
        "source_obligation_authority_ref_owner": source_ref.get("owner"),
        "citation_source_handoff_authority_ref_owner": citation_ref.get("owner"),
        "source_citation_authority_refs_are_dprime_runtime_refs": True,
        "source_obligation_authority_ref": _source_obligation_boundary_ref(source_ref),
        "citation_source_handoff_authority_ref": _citation_handoff_boundary_ref(
            citation_ref
        ),
        "source_readiness_gateway_ref": {
            "status": gateway.get("status"),
            "selected_current_value_display_status": gateway.get(
                "selected_current_value_display_status"
            ),
            "selected_source_ref": gateway.get("selected_source_ref"),
            "selected_window_digest": source_window.get("selected_window_digest"),
            "selected_window_char_count": source_window.get(
                "selected_window_char_count"
            ),
        },
        "dprime_answer_path_ref": {
            "status": answer_path.get("status"),
            "sufficiency_readiness_status": answer_path.get(
                "sufficiency_readiness_status"
            ),
            "final_answer_packet_status": answer_path.get(
                "final_answer_packet_status"
            ),
            "author_answer_status": answer_path.get("author_answer_status"),
            "citation_source_display_status": answer_path.get(
                "citation_source_display_status"
            ),
        },
        "dprime_source_citation_stoppoint_status": integration.get(
            "dprime_source_citation_stoppoint_status"
        ),
        "dprime_source_citation_stoppoint_blocker": integration.get(
            "dprime_source_citation_stoppoint_blocker"
        ),
        "semantic_status_decision": PASS_DECISION,
        "explicit_non_claims": dict(SOURCE_CITATION_DISPLAY_BOUNDARY_NON_CLAIMS),
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "sufficiency_readiness_created": False,
        "final_answer_prose_created": False,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "author_invoked": False,
        "citation_rendering_invoked": False,
        "final_citation_rendering_created": False,
        "product_correctness_claimed": False,
        "nonclaim_labels": [
            "D-prime answer-path source display projection",
            "not product correctness",
        ],
        "next_product_path_checkpoint": ANSWER_PATH_NEXT_PRODUCT_CHECKPOINT,
    }
    boundary["boundary_digest"] = _digest_json(
        {
            "schema_version": boundary["schema_version"],
            "authority_source": boundary["authority_source"],
            "entries": entries,
            "display_digest": display.get("display_digest"),
        }
    )
    return _json_safe(boundary)


def _source_citation_display_boundary_not_reached(
    *,
    blocker: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_CITATION_DISPLAY_BOUNDARY_SCHEMA_VERSION,
        "status": "not_reached",
        "blocker_code": blocker,
        "blocker_detail": detail,
        "boundary_owner": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "source_citation_display_boundary"
        ),
        "runtime_consumer": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "build_generic_single_relation_live_dogfood_run_output"
        ),
        "ordinary_product_path_consumed": True,
        "authority_source": None,
        "source_citation_display_entries": [],
        "source_citation_display_entries_created": False,
        "entry_count": 0,
        "derived_from_dprime_authority": False,
        "derived_from_gateway_only": False,
        "gateway_treated_as_authority": False,
        "source_obligation_authority_consumed": False,
        "citation_source_handoff_authority_consumed": False,
        "source_obligation_authority_ref": {},
        "citation_source_handoff_authority_ref": {},
        "source_readiness_gateway_ref": {},
        "explicit_non_claims": dict(SOURCE_CITATION_DISPLAY_BOUNDARY_NON_CLAIMS),
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "sufficiency_readiness_created": False,
        "final_answer_prose_created": False,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "author_invoked": False,
        "citation_rendering_invoked": False,
        "final_citation_rendering_created": False,
        "product_correctness_claimed": False,
    }


def _source_citation_display_authority_backed(
    *,
    integration: Mapping[str, Any],
    source_ref: Mapping[str, Any],
    citation_ref: Mapping[str, Any],
) -> bool:
    return (
        integration.get("status") == "consumed"
        and integration.get("gateway_treated_as_authority") is False
        and integration.get("source_obligation_authority_consumed") is True
        and integration.get("citation_source_handoff_authority_consumed") is True
        and source_ref.get("owner") == "RunKernel.DPrimeSourceObligationAuthority"
        and citation_ref.get("owner") == "RunKernel.DPrimeCitationSourceHandoffAuthority"
        and source_ref.get("runtime_surface")
        == "core.dprime_source_obligation_citation_authority_runtime"
        and citation_ref.get("runtime_surface")
        == "core.dprime_source_obligation_citation_authority_runtime"
        and source_ref.get("authority_consumed") is True
        and citation_ref.get("citation_source_handoff_consumed") is True
        and citation_ref.get("authority_consumed") is True
    )


def _source_citation_display_boundary_entry(
    *,
    record: Mapping[str, Any],
    index: int,
    selected_value_text: Any,
    selected_window: Mapping[str, Any],
    source_obligation_authority_ref: Mapping[str, Any],
    citation_handoff_ref: Mapping[str, Any],
) -> dict[str, Any]:
    source = _safe_mapping(record)
    title = _clean_text(source.get("title"), limit=220)
    domain = _clean_domain(source.get("domain"))
    url = _clean_text(source.get("url"), limit=700)
    source_id = _clean_text(source.get("source_id"), limit=320)
    label = f"D-prime source {index}"
    display_name = title or domain or source_id or label
    display_text = (
        f"{label}: {display_name} ({domain or 'unknown domain'})"
        if not url
        else f"{label}: {display_name} - {url}"
    )
    return _without_empty(
        {
            "label": label,
            "display_text": display_text,
            "source_title": title,
            "source_url": url,
            "source_domain": domain,
            "source_id": source_id,
            "source_obligation_id": _clean_text(
                source.get("source_obligation_id"),
                limit=320,
            ),
            "evidence_id": _clean_text(source.get("evidence_id"), limit=320),
            "content_ref_id": _clean_text(source.get("content_ref_id"), limit=320),
            "source_digest": _clean_text(source.get("source_digest"), limit=128),
            "selected_current_value_display_text": _clean_text(
                selected_value_text,
                limit=700,
            ),
            "selected_window_digest": _clean_text(
                selected_window.get("selected_window_digest"),
                limit=128,
            ),
            "selected_window_char_count": _bounded_int(
                selected_window.get("selected_window_char_count")
            ),
            "source_obligation_authority_id": _clean_text(
                source_obligation_authority_ref.get("source_obligation_authority_id"),
                limit=320,
            ),
            "source_obligation_authority_digest": _clean_text(
                source_obligation_authority_ref.get(
                    "source_obligation_authority_digest"
                ),
                limit=128,
            ),
            "citation_source_handoff_id": _clean_text(
                citation_handoff_ref.get("citation_source_handoff_id"),
                limit=320,
            ),
            "citation_source_handoff_digest": _clean_text(
                citation_handoff_ref.get("citation_source_handoff_digest"),
                limit=128,
            ),
            "source_citation_handoff_status": _clean_text(
                citation_handoff_ref.get("citation_source_handoff_status"),
                limit=80,
            ),
            "derived_from_dprime_authority": True,
            "derived_from_gateway_only": False,
            "citation_rendering_created": False,
            "final_answer_prose_created": False,
            "product_correctness_claimed": False,
            "caveat_labels": [
                "display boundary only",
                "not final citation rendering",
                "not product correctness",
            ],
        }
    )


def _source_citation_display_boundary_answer_path_entry(
    *,
    record: Mapping[str, Any],
    index: int,
    selected_value_text: Any,
    selected_window: Mapping[str, Any],
    source_obligation_authority_ref: Mapping[str, Any],
    citation_handoff_ref: Mapping[str, Any],
) -> dict[str, Any]:
    source = _safe_mapping(record)
    title = _clean_text(source.get("title"), limit=220)
    domain = _clean_domain(source.get("domain"))
    url = _clean_text(source.get("url"), limit=700)
    source_id = _clean_text(source.get("source_id"), limit=320)
    display_text = _clean_text(source.get("display_text"), limit=900)
    if not display_text:
        label = f"D-prime source {index}"
        display_name = title or domain or source_id or label
        display_text = (
            f"{label}: {display_name} ({domain or 'unknown domain'})"
            if not url
            else f"{label}: {display_name} - {url}"
        )
    return _without_empty(
        {
            "label": _clean_text(source.get("label"), limit=80)
            or f"D-prime source {index}",
            "display_text": display_text,
            "source_title": title,
            "source_url": url,
            "source_domain": domain,
            "source_id": source_id,
            "source_obligation_id": _clean_text(
                source.get("source_obligation_id"),
                limit=320,
            ),
            "evidence_id": _clean_text(source.get("evidence_id"), limit=320),
            "content_ref_id": _clean_text(source.get("content_ref_id"), limit=320),
            "source_digest": _clean_text(source.get("source_digest"), limit=128),
            "selected_current_value_display_text": _clean_text(
                selected_value_text,
                limit=700,
            ),
            "selected_window_digest": _clean_text(
                selected_window.get("selected_window_digest"),
                limit=128,
            ),
            "selected_window_char_count": _bounded_int(
                selected_window.get("selected_window_char_count")
            ),
            "source_obligation_authority_id": _clean_text(
                source_obligation_authority_ref.get("source_obligation_authority_id"),
                limit=320,
            ),
            "source_obligation_authority_digest": _clean_text(
                source_obligation_authority_ref.get(
                    "source_obligation_authority_digest"
                ),
                limit=128,
            ),
            "citation_source_handoff_id": _clean_text(
                citation_handoff_ref.get("citation_source_handoff_id"),
                limit=320,
            ),
            "citation_source_handoff_digest": _clean_text(
                citation_handoff_ref.get("citation_source_handoff_digest"),
                limit=128,
            ),
            "source_citation_handoff_status": _clean_text(
                citation_handoff_ref.get("citation_source_handoff_status"),
                limit=80,
            ),
            "derived_from_dprime_authority": True,
            "derived_from_gateway_only": False,
            "dprime_citation_source_display_created": True,
            "citation_rendering_created": False,
            "final_answer_prose_created": False,
            "product_correctness_claimed": False,
            "caveat_labels": [
                "D-prime answer-path source display",
                "not product correctness",
            ],
        }
    )


def _source_obligation_boundary_ref(source_ref: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "owner": source_ref.get("owner"),
            "runtime_surface": source_ref.get("runtime_surface"),
            "source_obligation_authority_id": source_ref.get(
                "source_obligation_authority_id"
            ),
            "source_obligation_authority_digest": source_ref.get(
                "source_obligation_authority_digest"
            ),
            "status": source_ref.get("status"),
            "authority_consumed": source_ref.get("authority_consumed"),
            "source_obligation_status": source_ref.get("source_obligation_status"),
        }
    )


def _citation_handoff_boundary_ref(citation_ref: Mapping[str, Any]) -> dict[str, Any]:
    return _without_empty(
        {
            "owner": citation_ref.get("owner"),
            "runtime_surface": citation_ref.get("runtime_surface"),
            "citation_source_handoff_id": citation_ref.get(
                "citation_source_handoff_id"
            ),
            "citation_source_handoff_digest": citation_ref.get(
                "citation_source_handoff_digest"
            ),
            "status": citation_ref.get("status"),
            "authority_consumed": citation_ref.get("authority_consumed"),
            "citation_source_handoff_consumed": citation_ref.get(
                "citation_source_handoff_consumed"
            ),
            "citation_source_handoff_status": citation_ref.get(
                "citation_source_handoff_status"
            ),
            "citation_eligible_source_ids": list(
                _safe_sequence(citation_ref.get("citation_eligible_source_ids"))
            ),
        }
    )


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {}, ())
    }


def _source_readiness_gateway_summary(gateway: Mapping[str, Any]) -> str:
    source = _safe_mapping(gateway.get("selected_source_ref"))
    value = _clean_text(gateway.get("selected_current_value_text"), limit=700)
    return (
        "Source/readiness gateway ready; selected current value text is "
        f"{value or 'not displayed'}; selected source is "
        f"{source.get('title') or 'not available'} "
        f"({source.get('domain') or 'unknown domain'}). Final answer prose, "
        "citation eligibility, source-obligation satisfaction, source-authority "
        "finality, FAP, Author, and product correctness remain unclaimed."
    )


def _source_readiness_gateway_blocker(
    *,
    packet: Mapping[str, Any],
    dprime_pass_ready: bool,
    selected_candidate: Mapping[str, Any],
    selected_window: Mapping[str, Any],
    source_ref: Mapping[str, Any],
    value_ref: Mapping[str, Any],
    contract_state: Mapping[str, Any],
) -> tuple[str | None, str | None]:
    if not dprime_pass_ready:
        return (
            BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_DPRIME_NOT_PASSING,
            "D-prime admitted support state is not present for gateway display.",
        )
    if (
        packet.get("source_obligation_recovery_answer_display_blocked") is True
        or packet.get("source_obligation_recovery_source_display_blocked") is True
        or contract_state.get("answer_display_allowed") is False
        or contract_state.get("source_display_allowed") is False
    ):
        return (
            BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_SOURCE_DISPLAY_BLOCKED,
            "Source-obligation recovery contract state blocks answer/source display.",
        )
    missing = []
    if not value_ref.get("selected_current_value_text"):
        missing.append("selected_current_value_text")
    if not source_ref.get("url") or not source_ref.get("domain"):
        missing.append("selected_source_ref")
    if not source_ref.get("candidate_id") and not selected_candidate.get("candidate_id"):
        missing.append("selected_candidate_ref")
    if not selected_window.get("selected_window_digest"):
        missing.append("selected_window_digest")
    if not selected_window.get("evidence_window_ref"):
        missing.append("evidence_window_ref")
    if missing:
        return (
            BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_STATE_MISSING,
            "Source/readiness gateway missing current-path state: "
            + ", ".join(missing)
            + ".",
        )
    return None, None


def _dprime_pass_ready_for_gateway(dprime: Mapping[str, Any]) -> bool:
    objects = _safe_mapping(dprime.get("objects_created"))
    return (
        dprime.get("assessment_status") == "assessed"
        and dprime.get("support_relation") == "directly_supports"
        and dprime.get("proposal_validation_status")
        == DPRIME_SUPPORT_PROPOSAL_VALIDATION_PASSED
        and dprime.get("run_kernel_admission_decision_status") == "admitted"
        and (
            dprime.get("semantic_observation_admission_status") == "materialized"
            or objects.get("semantic_observation") is True
        )
    )


def _selected_gateway_candidate(packet: Mapping[str, Any]) -> dict[str, Any]:
    for item in _safe_sequence(packet.get("answer_bearing_candidate_window_diagnostics")):
        safe = _safe_mapping(item)
        if safe.get("answer_bearing_candidate_window_selected") is True:
            return safe
    for item in _safe_sequence(packet.get("fetch_read_candidate_diagnostics")):
        safe = _safe_mapping(item)
        if (
            safe.get("answer_bearing_candidate_window_selected") is True
            or safe.get("selected_for_fetch_read") is True
            or safe.get("attempted") is True
        ):
            return safe
    authorization = _safe_mapping(packet.get("source_obligation_recovery_authorization"))
    return _safe_mapping(authorization.get("selected_candidate_ref"))


def _selected_window_ref_from_dprime(dprime: Mapping[str, Any]) -> dict[str, Any]:
    input_ref = _safe_mapping(dprime.get("input_packet_ref"))
    diagnostic = _safe_mapping(input_ref.get("selected_window_diagnostic_ref"))
    evidence_window = _safe_mapping(input_ref.get("evidence_window_ref"))
    return {
        "selected_window_digest": _clean_text(
            diagnostic.get("selected_window_digest"),
            limit=128,
        )
        or _clean_text(diagnostic.get("bounded_content_digest"), limit=128)
        or _clean_text(evidence_window.get("window_digest"), limit=128)
        or _clean_text(evidence_window.get("bounded_content_digest"), limit=128),
        "selected_window_char_count": _bounded_int(
            diagnostic.get("selected_window_char_count")
            or diagnostic.get("bounded_character_count")
            or evidence_window.get("window_char_count")
            or evidence_window.get("bounded_character_count")
        ),
        "provider_extracted_source_text_digest": _clean_text(
            diagnostic.get("provider_extracted_source_text_digest"),
            limit=128,
        ),
        "source_text_digest_distinct_from_selected_window_digest": (
            diagnostic.get("source_text_digest_distinct_from_selected_window_digest")
            is True
        ),
        "value_token_observed": diagnostic.get("value_token_observed") is True,
        "value_token_kind_counts": _safe_mapping(
            diagnostic.get("value_token_kind_counts")
        ),
        "anchor_match_status": _clean_text(
            diagnostic.get("anchor_match_status"),
            limit=120,
        ),
        "diagnostic_ref": _without_window_text(diagnostic),
        "evidence_window_ref": _without_window_text(evidence_window),
    }


def _selected_source_ref(
    *,
    packet: Mapping[str, Any],
    relation_ref: Mapping[str, Any],
    selected_candidate: Mapping[str, Any],
    admission_ref: Mapping[str, Any],
) -> dict[str, Any]:
    title = (
        _clean_text(selected_candidate.get("title"), limit=220)
        or _clean_text(relation_ref.get("source_title"), limit=220)
    )
    url = (
        _clean_text(selected_candidate.get("url"), limit=700)
        or _clean_text(relation_ref.get("source_url"), limit=700)
    )
    domain = (
        _clean_domain(selected_candidate.get("domain"))
        or _clean_domain(relation_ref.get("source_domain"))
    )
    return {
        "title": title,
        "url": url,
        "domain": domain,
        "provider": packet.get("extraction_provider"),
        "candidate_id": _clean_text(
            relation_ref.get("candidate_id")
            or selected_candidate.get("candidate_id")
            or admission_ref.get("candidate_id"),
            limit=320,
        ),
        "candidate_digest": _clean_text(
            relation_ref.get("candidate_digest")
            or selected_candidate.get("candidate_digest")
            or admission_ref.get("candidate_digest"),
            limit=128,
        ),
        "result_rank": _bounded_int(selected_candidate.get("result_rank")),
        "source_ref_kind": "current_path_selected_candidate_source_ref",
    }


def _selected_current_value_ref(
    *,
    packet: Mapping[str, Any],
    dprime: Mapping[str, Any],
) -> dict[str, Any]:
    assessment = _safe_mapping(dprime.get("assessment_material_ref"))
    claim = _safe_mapping(assessment.get("answer_component_claim"))
    claim_text = _clean_text(claim.get("claim"), limit=700)
    component_id = _clean_text(claim.get("component_id"), limit=320)
    component_matches = bool(component_id and component_id == packet.get("component_id"))
    if not component_matches:
        claim_text = None
    semantic_ref = _safe_mapping(dprime.get("semantic_observation_ref"))
    return {
        "selected_current_value_text": claim_text,
        "value_source": (
            "dprime_assessment_material_ref.answer_component_claim.claim"
            if claim_text
            else None
        ),
        "component_id": component_id,
        "component_matches_relation_plan": component_matches,
        "assessment_id": _clean_text(assessment.get("assessment_id"), limit=320),
        "assessment_digest": _clean_text(assessment.get("assessment_digest"), limit=128),
        "semantic_observation_ref": {
            "observation_id": semantic_ref.get("observation_id"),
            "observation_digest": semantic_ref.get("observation_digest"),
            "owner": semantic_ref.get("owner"),
        },
        "not_final_answer_prose": True,
        "not_model_knowledge_generation": True,
    }


def _gateway_dprime_ref(dprime: Mapping[str, Any]) -> dict[str, Any]:
    objects = _safe_mapping(dprime.get("objects_created"))
    return {
        "assessment_status": dprime.get("assessment_status"),
        "support_relation": dprime.get("support_relation"),
        "proposal_validation_status": dprime.get("proposal_validation_status"),
        "run_kernel_admission_decision_status": dprime.get(
            "run_kernel_admission_decision_status"
        ),
        "semantic_observation_admission_status": dprime.get(
            "semantic_observation_admission_status"
        ),
        "semantic_observation_created": objects.get("semantic_observation") is True,
        "component_coverage_created": objects.get("component_coverage") is True,
        "final_answer_packet_created": False,
        "author_answer_created": False,
        "citation_source_display_created": False,
        "model_review_status": dprime.get("model_review_status"),
        "model_review_call_count": dprime.get("model_review_call_count"),
    }


def _without_window_text(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in _safe_mapping(value).items()
        if _normalize_key(key)
        not in {
            "window_text",
            "bounded_text",
            "source_text",
            "raw_text",
            "raw_source_text",
            "full_text",
        }
    }


def _provider_acquisition_route_posture(counts: Mapping[str, Any]) -> str:
    if _bounded_int(counts.get("product_provider_acquisition_adapter_used")):
        if _bounded_int(counts.get("provider_calls_completed")):
            return (
                "product_provider_acquisition_adapter_sanitized_results_to_"
                "plan_derived_retained_artifacts"
            )
        if _bounded_int(counts.get("provider_calls_attempted")):
            return "product_provider_acquisition_adapter_failed_closed"
        return "product_provider_acquisition_adapter_selected_before_provider_search"
    if _bounded_int(counts.get("provider_calls_attempted")):
        return (
            "injected_provider_runner_sanitized_results_to_plan_"
            "derived_retained_artifacts"
        )
    return "blocked_before_provider_search"


def _failure_attribution_bucket(packet: Mapping[str, Any]) -> str:
    decision = _clean_text(packet.get("decision"), limit=220) or ""
    if decision == PASS_DECISION:
        return "not_blocked"
    if decision in {
        BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING,
        BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE,
    }:
        return "current_source_record_answer_contract_lineage"
    if decision == BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE:
        return "fast_model_planner_strict_route_unavailable"
    if decision in {
        BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE,
        "blocked_model_output_invalid",
    } or _safe_mapping(packet.get("model_assisted_planning_packet")).get("blocker"):
        return "fast_model_planner_invalid_or_closed"
    if decision in {
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_CREDENTIAL_UNAVAILABLE,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE,
    }:
        return "provider_acquisition"
    if (
        _bounded_int(packet.get("provider_calls_attempted")) > 0
        and _bounded_int(packet.get("provider_results_returned")) == 0
    ):
        return "provider_acquisition"
    if decision in {
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX,
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL,
    }:
        return "selector_or_window"
    if decision in {
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CONTRACT_MISSING,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED,
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_OUTPUT_INVALID,
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED,
    }:
        return "dprime"
    if packet.get("source_obligation_recovery_required") is True:
        return "runkernel_source_obligation_gate"
    if decision in {
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_STATE_MISSING,
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_DPRIME_NOT_PASSING,
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_READINESS_GATEWAY_SOURCE_DISPLAY_BLOCKED,
    }:
        return "source_readiness_gateway"
    if decision == BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD:
        return "dprime_authority_integration"
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CITATION_DISPLAY_NOT_LICENSED:
        return "source_citation_display_boundary"
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_QUICK_SUFFICIENCY_NOT_LICENSED:
        return "source_citation_display_boundary"
    if decision in EXISTING_DPRIME_ANSWER_PATH_BLOCKERS:
        return "dprime_answer_path"
    if _bounded_int(packet.get("evidence_ledger_admissions")) > 0:
        return "runkernel_or_downstream_gate"
    return "blocked_before_acquisition"


def _build_source_obligation_recovery_authorization(
    *,
    run_kernel: RunKernel,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    counts: Mapping[str, Any],
    dprime_status: Mapping[str, Any] | None,
    semantic_payload: Mapping[str, Any] | None = None,
    source_challenge_recovery: Mapping[str, Any] | None = None,
    recovery_confirmation_authorized: bool = False,
) -> dict[str, Any]:
    semantic = _safe_mapping(semantic_payload)
    recovery = _safe_mapping(source_challenge_recovery)
    recovery_result = _safe_mapping(recovery.get("source_challenge_recovery_result"))
    reduction_payload = {
        "relation_plan": _safe_mapping(relation_plan),
        "acquisition_plan": _safe_mapping(acquisition_plan),
        "selected_candidate_diagnostic": (
            _selected_source_challenge_candidate_diagnostic(counts)
        ),
        "candidate_diagnostics": [
            _safe_mapping(item)
            for item in _safe_sequence(counts.get("fetch_read_candidate_diagnostics"))
        ],
        "dprime_status": _safe_mapping(dprime_status),
        "provider_acquisition_attempt_counts": {
            "provider_calls_attempted": counts.get("provider_calls_attempted", 0),
            "provider_calls_completed": counts.get("provider_calls_completed", 0),
            "provider_results_returned": counts.get("provider_results_returned", 0),
            "extraction_provider_calls_attempted": counts.get(
                "extraction_provider_calls_attempted",
                0,
            ),
            "extraction_provider_calls_completed": counts.get(
                "extraction_provider_calls_completed",
                0,
            ),
        },
        "evidence_admission_ref": _safe_mapping(
            semantic.get("source_evidence_admission_ref")
        ),
        "recovery_attempt_ref": {
            "status": recovery.get("status"),
            "blocker": recovery.get("blocker"),
            "detail": recovery.get("detail"),
            "source_challenge_recovery_plan_created": bool(
                recovery.get("source_challenge_recovery_plan")
            ),
        }
        if recovery
        else {},
        "recovery_attempt_counts": recovery_result,
        "recovery_confirmation_authorized": recovery_confirmation_authorized,
        "closed_surface_request_flags": {
            "source_authority_adjudication_requested": False,
            "source_obligation_satisfaction_requested": False,
            "citation_eligibility_requested": False,
            "fap_requested": False,
            "author_requested": False,
            "product_correctness_requested": False,
        },
    }
    action = run_kernel.authorize_single_relation_source_obligation_recovery(
        inputs=reduction_payload
    )
    observation = Observation.from_action(
        action,
        observation_type=(
            ObservationType.SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZED
        ),
        status=RunStageStatus.COMPLETED,
        payload=reduction_payload,
    )
    run_kernel.reduce(observation)
    return _safe_mapping(
        run_kernel.state.projections.get(
            SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_AUTHORIZATION_STAGE
        )
    )


def _source_obligation_authorization_dict(
    authorization: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return _safe_mapping(authorization)


def _run_source_challenge_recovery(
    *,
    root: Path,
    run_dir: Path,
    retained_root: Path,
    run_id: str,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any],
    first_stage_counts: Mapping[str, Any],
    first_stage_semantic_payload: Mapping[str, Any],
    source_obligation_recovery_authorization: Mapping[str, Any],
    recovery_model_planning_packet: Mapping[str, Any] | None,
    provider_runner: ProviderProxyRunner,
    fetch_read_runner: FetchReadRunner,
    confirm_live_source_challenge_recovery: bool,
) -> dict[str, Any]:
    del fetch_read_runner, first_stage_counts, first_stage_semantic_payload
    authorization = _source_obligation_authorization_dict(
        source_obligation_recovery_authorization
    )
    plan = _recovery_plan_with_model_assisted_hints(
        _safe_mapping(authorization.get("source_challenge_recovery_plan")),
        recovery_model_planning_packet=recovery_model_planning_packet,
    )
    if not plan:
        return {
            "trigger_eligible": False,
            "status": "not_triggered",
            "blocker": None,
            "detail": "source-obligation recovery authorization did not require recovery.",
            "source_challenge_recovery_plan": {},
            "source_challenge_recovery_authorization": authorization,
            "source_challenge_recovery_result": {
                "provider_calls_attempted": 0,
                "provider_calls_completed": 0,
                "official_answer_bearing_material_acquired": False,
                "support_created": False,
                "source_authority_adjudicated": False,
                "source_obligation_satisfied": False,
                "answer_created": False,
            },
        }
    if not confirm_live_source_challenge_recovery:
        return {
            "trigger_eligible": True,
            "status": "not_executed_confirmation_required",
            "blocker": (
                authorization.get("authorization_blocker")
                or BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED
            ),
            "detail": (
                f"{CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG} is required "
                "before an additional source-challenge recovery acquisition."
            ),
            "source_challenge_recovery_plan": plan,
            "source_challenge_recovery_authorization": authorization,
            "source_challenge_recovery_result": {
                "provider_calls_attempted": 0,
                "provider_calls_completed": 0,
                "official_answer_bearing_material_acquired": False,
                "support_created": False,
                "source_authority_adjudicated": False,
                "source_obligation_satisfied": False,
                "answer_created": False,
            },
        }

    output_path = run_dir / "sanitized-source-challenge-recovery-provider-response.json"
    provider_result = provider_runner(
        GenericProviderProxyRunRequest(
            repo_root=root,
            output_path=output_path,
            query=str(plan["recovery_query"]),
            provider=str(plan["provider"]),
            acquisition_provider_role=str(plan["provider_role"]),
            operation=str(plan["provider_operation"]),
            max_results=_bounded_int(plan.get("max_results"), default=MAX_PROVIDER_RESULTS),
            domain_constraints=tuple(
                str(item) for item in _safe_sequence(plan.get("domain_constraints"))
            ),
            include_domains=tuple(
                str(item) for item in _safe_sequence(plan.get("include_domains"))
            ),
            source_of_record_domain_constraints=tuple(
                str(item)
                for item in _safe_sequence(
                    plan.get("source_of_record_domain_constraints")
                )
            ),
        )
    )
    if provider_result.return_code != 0:
        blocker = _provider_result_blocker(
            provider_result,
            default=BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE,
        )
        return {
            "trigger_eligible": True,
            "status": "provider_acquisition_failed_closed",
            "blocker": blocker,
            "detail": _provider_result_detail(
                provider_result,
                default="source-challenge recovery provider acquisition failed closed.",
            ),
            "source_challenge_recovery_plan": plan,
            "source_challenge_recovery_authorization": authorization,
            "source_challenge_recovery_result": {
                "provider_calls_attempted": provider_result.provider_calls_attempted,
                "provider_calls_completed": provider_result.provider_calls_completed,
                "provider_results_returned": 0,
                "official_answer_bearing_material_acquired": False,
                "support_created": False,
                "source_authority_adjudicated": False,
                "source_obligation_satisfied": False,
                "answer_created": False,
            },
        }

    provider_payload = _load_sanitized_provider_output(provider_result.output_path)
    results = _provider_results(provider_payload)
    recovery_root = retained_root / SOURCE_CHALLENGE_RECOVERY_ARTIFACT_DIR
    recovery_run_id = f"{_clean_run_id(run_id)}-source-challenge-recovery"
    candidate_packet = _candidate_packet_from_provider_results(
        relation_plan=relation_plan,
        run_id=recovery_run_id,
        results=results,
        provider_calls_attempted=provider_result.provider_calls_attempted,
        provider_calls_completed=provider_result.provider_calls_completed,
        search_query_seed=str(plan["recovery_query"]),
        extraction_provider=str(plan["provider"]),
    )
    _write_search_artifacts(
        retained_root=recovery_root,
        provider_payload=provider_payload,
        candidate_packet=candidate_packet,
    )
    if not any(_provider_extracted_text(item) for item in results):
        return _source_challenge_recovery_no_material_result(
            plan=plan,
            authorization=authorization,
            provider_result=provider_result,
            provider_results_returned=len(results),
            detail=(
                "source-challenge recovery returned no provider-extracted "
                "content for existing candidate/window selection."
            ),
        )

    fetch_packet, fetch_counts = _write_fetch_read_artifacts(
        retained_root=recovery_root,
        relation_plan=relation_plan,
        acquisition_plan=acquisition_plan,
        provider_results=results,
        fetch_read_runner=_source_challenge_recovery_fetch_read_closed,
    )
    selected = _selected_source_challenge_candidate_diagnostic(fetch_counts)
    material_acquired = bool(
        fetch_packet
        and selected
        and candidate_answer_bearing_by_safe_diagnostics(selected)
        and candidate_official_source_of_record_looking_by_safe_diagnostics(
            selected
        )
    )
    recovery_result = {
        "provider_calls_attempted": provider_result.provider_calls_attempted,
        "provider_calls_completed": provider_result.provider_calls_completed,
        "provider_results_returned": len(results),
        "fetch_read_packet_created": bool(fetch_packet),
        "recovery_artifact_root": _display_path(recovery_root),
        "candidate_window_status": fetch_counts.get(
            "answer_bearing_candidate_window_status"
        ),
        "candidate_window_diagnostics": list(
            _safe_sequence(fetch_counts.get("answer_bearing_candidate_window_diagnostics"))
        ),
        "selected_candidate_ref": _source_challenge_selected_candidate_ref(selected),
        "official_answer_bearing_material_acquired": material_acquired,
        "official_source_of_record_looking_candidate_selected": bool(
            selected
            and candidate_official_source_of_record_looking_by_safe_diagnostics(
                selected
            )
        ),
        "support_created": False,
        "dprime_rereview_licensed": False,
        "source_authority_adjudicated": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
        "answer_created": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    if material_acquired:
        return {
            "trigger_eligible": True,
            "status": "official_answer_bearing_recovery_material_acquired",
            "blocker": (
                BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED
            ),
            "detail": (
                "Official/source-of-record-looking answer-bearing recovery "
                "material was acquired by safe diagnostics; second D-prime "
                "review, support, source authority, source-obligation "
                "satisfaction, citation eligibility, FAP, and Author remain closed."
            ),
            "source_challenge_recovery_plan": plan,
            "source_challenge_recovery_authorization": authorization,
            "source_challenge_recovery_result": recovery_result,
        }
    return {
        "trigger_eligible": True,
        "status": "no_official_answer_bearing_material",
        "blocker": (
            BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL
        ),
        "detail": (
            "Source-challenge recovery did not select official/source-of-record-looking "
            "answer-bearing material by safe diagnostics."
        ),
        "source_challenge_recovery_plan": plan,
        "source_challenge_recovery_authorization": authorization,
        "source_challenge_recovery_result": recovery_result,
    }


def _source_challenge_recovery_no_material_result(
    *,
    plan: Mapping[str, Any],
    authorization: Mapping[str, Any],
    provider_result: GenericProviderProxyRunResult,
    provider_results_returned: int,
    detail: str,
) -> dict[str, Any]:
    return {
        "trigger_eligible": True,
        "status": "no_official_answer_bearing_material",
        "blocker": (
            BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL
        ),
        "detail": detail,
        "source_challenge_recovery_plan": dict(plan),
        "source_challenge_recovery_authorization": dict(authorization),
        "source_challenge_recovery_result": {
            "provider_calls_attempted": provider_result.provider_calls_attempted,
            "provider_calls_completed": provider_result.provider_calls_completed,
            "provider_results_returned": provider_results_returned,
            "official_answer_bearing_material_acquired": False,
            "support_created": False,
            "source_authority_adjudicated": False,
            "source_obligation_satisfied": False,
            "citation_eligible": False,
            "answer_created": False,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        },
    }


def _source_challenge_recovery_fetch_read_closed(
    _url: str,
) -> GenericLiveFetchReadResult:
    raise GenericSingleRelationLiveDogfoodRunError(
        BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL,
        "source-challenge recovery uses provider-extracted content only in this phase.",
    )


def _selected_source_challenge_candidate_diagnostic(
    counts: Mapping[str, Any],
) -> dict[str, Any]:
    for item in _safe_sequence(counts.get("fetch_read_candidate_diagnostics")):
        diagnostic = _safe_mapping(item)
        if diagnostic.get("answer_bearing_candidate_window_selected") is True:
            return diagnostic
    return {}


def _source_challenge_selected_candidate_ref(
    diagnostic: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return selected_candidate_ref_from_diagnostic(diagnostic)


def _source_challenge_recovery_counts(
    recovery: Mapping[str, Any] | None,
) -> dict[str, Any]:
    safe = _safe_mapping(recovery)
    result = _safe_mapping(safe.get("source_challenge_recovery_result"))
    return {
        "source_challenge_recovery_provider_calls_attempted": _bounded_int(
            result.get("provider_calls_attempted")
        ),
        "source_challenge_recovery_provider_calls_completed": _bounded_int(
            result.get("provider_calls_completed")
        ),
        "source_challenge_recovery_provider_results_returned": _bounded_int(
            result.get("provider_results_returned")
        ),
    }


def _source_challenge_recovery_decision(
    recovery: Mapping[str, Any] | None,
    *,
    fallback_decision: str,
) -> str:
    safe = _safe_mapping(recovery)
    status = safe.get("status")
    if status in {
        "not_executed_confirmation_required",
        "official_answer_bearing_recovery_material_acquired",
        "no_official_answer_bearing_material",
        "provider_acquisition_failed_closed",
    }:
        blocker = _clean_text(safe.get("blocker"), limit=220)
        return blocker or fallback_decision
    return fallback_decision


def _source_challenge_recovery_detail(
    recovery: Mapping[str, Any] | None,
    *,
    fallback_detail: str,
) -> str:
    safe = _safe_mapping(recovery)
    if safe.get("status") in {
        "not_executed_confirmation_required",
        "official_answer_bearing_recovery_material_acquired",
        "no_official_answer_bearing_material",
        "provider_acquisition_failed_closed",
    }:
        return _clean_text(safe.get("detail"), limit=900) or fallback_detail
    return fallback_detail


def _acquisition_plan_diagnostics(
    acquisition_plan: Mapping[str, Any],
    *,
    counts: Mapping[str, Any],
) -> dict[str, Any]:
    acquisition = _safe_mapping(acquisition_plan)
    if not acquisition:
        return {
            "available": False,
            "raw_private_retention": False,
        }
    answer_anchors = list(
        _safe_sequence(acquisition.get("answer_bearing_anchor_terms"))
    )
    value_kinds = list(
        _safe_sequence(acquisition.get("expected_value_token_kinds"))
    )
    artifact_terms = list(_safe_sequence(acquisition.get("artifact_source_terms")))
    return {
        "available": True,
        "schema_version": acquisition.get("schema_version"),
        "planner_type": acquisition.get("planner_type") or "deterministic",
        "planner_kind": acquisition.get("planner_kind"),
        "fast_model_planner_used": acquisition.get("fast_model_planner_used")
        is True,
        "fast_model_route_used": acquisition.get("fast_model_route_used") is True,
        "ambiguity_required": acquisition.get("ambiguity_required") is True
        or acquisition.get("disambiguation_required") is True,
        "ambiguity_status": acquisition.get("ambiguity_status"),
        "acquisition_query": acquisition.get("acquisition_query"),
        "answer_bearing_anchor_count": len(answer_anchors),
        "expected_value_token_kinds": value_kinds,
        "artifact_source_terms_used": artifact_terms,
        "selected_window_guidance_produced": bool(
            counts.get("selected_window_guidance_produced", 0)
            or acquisition.get("selected_window_guidance")
        ),
        "selected_window_guidance_consumed": bool(
            counts.get("selected_window_guidance_consumed", 0)
        ),
        "selected_window_guidance_blocked": bool(
            counts.get("selected_window_guidance_blocked", 0)
        ),
        "selected_window_anchor_guidance_consumed": bool(
            counts.get("selected_window_anchor_guidance_consumed", 0)
        ),
        "selected_window_value_token_guidance_consumed": bool(
            counts.get("selected_window_value_token_guidance_consumed", 0)
        ),
        "selected_window_value_token_guidance_blocked": bool(
            counts.get("selected_window_value_token_guidance_blocked", 0)
        ),
        "selected_window_value_token_guidance_blocker": _clean_text(
            counts.get("selected_window_value_token_guidance_blocker"),
            limit=220,
        ),
        "selected_window_guidance_blocker": _clean_text(
            counts.get("selected_window_guidance_blocker"),
            limit=220,
        ),
        "raw_private_retention": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "closed_surface_flags": dict(
            _safe_mapping(acquisition.get("closed_surface_flags"))
        ),
    }


def _base_packet(
    *,
    relation_plan: Mapping[str, Any] | None,
    query_retained: bool,
    run_id: str,
    retained_root: Path | None,
    counts: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    disambiguation_record: Mapping[str, Any] | None,
    confirm_live_dprime_review: bool,
    confirm_live_source_challenge_recovery: bool,
    source_obligation_recovery_authorization: Mapping[str, Any] | None,
    source_challenge_recovery: Mapping[str, Any] | None,
    initial_model_planning_packet: Mapping[str, Any] | None,
    recovery_model_planning_packet: Mapping[str, Any] | None,
    require_model_assisted_planning: bool,
    caps_exhausted: bool,
    semantic_payload: Mapping[str, Any],
    entrypoint_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    plan = _safe_mapping(relation_plan)
    acquisition = _safe_mapping(acquisition_plan)
    disambiguation = _safe_mapping(disambiguation_record)
    requirement = _safe_mapping(plan.get("source_authority_posture_requirement"))
    search_requirement = _first_mapping(plan.get("search_requirements"))
    source_obligation = _first_mapping(plan.get("source_obligations"))
    dprime_candidate = _safe_mapping(plan.get("dprime_relation_intake_candidate"))
    future_node = _safe_mapping(plan.get("future_component_work_node_candidate"))
    semantic = _safe_mapping(semantic_payload)
    source_obligation_authorization = (
        _source_obligation_authorization_dict(
            source_obligation_recovery_authorization
        )
    )
    initial_model_planning = _safe_mapping(initial_model_planning_packet)
    recovery_model_planning = _safe_mapping(recovery_model_planning_packet)
    model_route_ref = _model_assisted_planning_route_diagnostic_ref(
        initial_model_planning,
        recovery_model_planning,
    )
    model_route_result_ref = _model_assisted_planning_route_result_diagnostic_ref(
        initial_model_planning,
        recovery_model_planning,
    )
    recovery = _safe_mapping(source_challenge_recovery)
    recovery_plan = _safe_mapping(recovery.get("source_challenge_recovery_plan"))
    recovery_result = _safe_mapping(
        recovery.get("source_challenge_recovery_result")
    )
    relation_ref = _safe_mapping(semantic.get("dprime_relation_intake_ref"))
    query_text = (
        _clean_text(plan.get("sanitized_query"), limit=500)
        if query_retained and plan
        else "unsupported query (not retained)"
    )
    entrypoint = _entrypoint_metadata_from_mapping(entrypoint_metadata)
    workbench_bundle = _analyst_workbench_bundle_from_counts(counts)
    triage_packet = _safe_mapping(
        workbench_bundle.get("candidate_evidence_triage_packet")
    )
    workbench_packet = _safe_mapping(workbench_bundle.get("analyst_workbench_packet"))
    gap_proposal = _safe_mapping(workbench_bundle.get("analysis_gap_search_proposal"))
    dprime_dossier = _safe_mapping(workbench_bundle.get("workbench_dprime_dossier"))
    projection = _safe_mapping(workbench_bundle.get("workbench_reduction_projection"))
    triage_ref = _safe_mapping(workbench_bundle.get("candidate_evidence_triage_ref"))
    workbench_ref = _safe_mapping(workbench_bundle.get("analyst_workbench_ref"))
    gap_ref = _safe_mapping(workbench_bundle.get("analysis_gap_search_proposal_ref"))
    dprime_dossier_ref = _safe_mapping(
        workbench_bundle.get("workbench_dprime_dossier_ref")
    )
    projection_ref = _safe_mapping(
        workbench_bundle.get("workbench_reduction_projection_ref")
    )
    workbench_dprime_consumed = _workbench_dossier_consumed_by_dprime(
        semantic,
        dprime_dossier_ref=dprime_dossier_ref,
    )
    workbench_gap_reentry = _workbench_gap_reentry_ref(
        gap_proposal=gap_proposal,
        gap_ref=gap_ref,
        semantic_payload=semantic,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_name": PHASE_NAME,
        "mode": MODE,
        "ordinary_entrypoint": "python -m proplex",
        "command_flag": entrypoint["command_flag"],
        "status_flag": entrypoint["command_flag"],
        "confirmation_flag": entrypoint["confirmation_flag"],
        "entrypoint_surface": entrypoint["entrypoint_surface"],
        "entrypoint_kind": entrypoint["entrypoint_kind"],
        "diagnostic_dogfood_alias": entrypoint["diagnostic_dogfood_alias"],
        "supported_query_class": entrypoint["supported_query_class"],
        "command_harness_used": _command_harness(
            command_flag=entrypoint["command_flag"],
            confirmation_flag=entrypoint["confirmation_flag"],
            confirm_live_dprime_review=confirm_live_dprime_review,
            confirm_live_source_challenge_recovery=(
                confirm_live_source_challenge_recovery
            ),
        ),
        "source_challenge_recovery_confirmed": bool(
            confirm_live_source_challenge_recovery
        ),
        "query": query_text,
        "query_retained": bool(query_retained and plan),
        "unsupported_query_retained": False,
        "run_id": run_id,
        "packet_id": f"generic-single-relation-live-dogfood-packet:{run_id}",
        "runtime_consumer": (
            "proplex.mvp_single_relation_live_dogfood_run."
            "build_generic_single_relation_live_dogfood_run_output"
        ),
        "ordinary_product_path_consumed": bool(
            semantic.get("generic_relation_intake_consumed_by_product_status")
        ),
        "generic_live_status_consumed_retained_artifacts": bool(semantic),
        "relation_plan_consumed": bool(plan),
        "relation_plan_id": plan.get("plan_id"),
        "relation_plan_packet_id": plan.get("packet_id"),
        "relation_plan_packet_digest": plan.get("packet_digest"),
        "supported_query_class_id": plan.get("supported_query_class_id")
        or MVP_SUPPORTED_QUERY_CLASS_ID,
        "supported_query_class_boundary": _safe_mapping(
            plan.get("supported_query_class_boundary")
        ),
        "source_authority_posture_contract_ref": plan.get(
            "source_authority_posture_contract_ref"
        ),
        "source_authority_posture_requirement_ref": requirement.get(
            "requirement_id"
        ),
        "source_authority_posture_requirement": requirement,
        "actual_source_authority_posture_created": (
            _actual_source_authority_posture_created(semantic)
        ),
        "planner_type": plan.get("planner_type"),
        "fast_planner_added": bool(acquisition),
        "fast_planner_used": bool(acquisition),
        "fast_planner_kind": acquisition.get("planner_kind"),
        "fast_planner_route": acquisition.get("planner_route"),
        "fast_planner_model_route_used": acquisition.get("fast_model_route_used")
        is True,
        "fast_planner_model_calls_attempted": counts.get(
            "fast_planner_model_calls_attempted",
            0,
        ),
        "fast_planner_model_calls_completed": counts.get(
            "fast_planner_model_calls_completed",
            0,
        ),
        "fast_planner_calls_attempted": counts.get(
            "fast_planner_calls_attempted",
            0,
        ),
        "model_assisted_planning_packet": initial_model_planning,
        "initial_model_assisted_planning_packet": initial_model_planning,
        "recovery_model_assisted_planning_packet": recovery_model_planning,
        "model_assisted_planning_required": bool(require_model_assisted_planning),
        "model_assisted_planning_strict_model_route_valid": (
            initial_model_planning.get("strict_model_route_valid") is True
            or recovery_model_planning.get("strict_model_route_valid") is True
        ),
        "model_assisted_planning_strict_model_route_blockers": list(
            _safe_sequence(
                initial_model_planning.get("strict_model_route_blockers")
                or recovery_model_planning.get("strict_model_route_blockers")
            )
        ),
        "model_assisted_planning_configured_fast_provider": model_route_ref.get(
            "configured_fast_provider"
        ),
        "model_assisted_planning_configured_fast_model": model_route_ref.get(
            "configured_fast_model"
        ),
        "model_assisted_planning_configured_endpoint_kind": (
            model_route_ref.get("configured_endpoint_kind")
        ),
        "model_assisted_planning_configured_local_url_present": (
            model_route_ref.get("configured_local_url_present") is True
        ),
        "model_assisted_planning_configured_local_url_posture": (
            model_route_ref.get("configured_local_url_posture")
        ),
        "model_assisted_planning_provider_used": (
            model_route_result_ref.get("provider_used")
        ),
        "model_assisted_planning_model_used": (
            model_route_result_ref.get("model_used")
        ),
        "model_assisted_planning_endpoint_used": (
            model_route_result_ref.get("endpoint_used")
        ),
        "model_assisted_planning_strict_one_shot": (
            model_route_result_ref.get("strict_one_shot") is True
        ),
        "model_assisted_planning_retry_policy": (
            model_route_result_ref.get("retry_policy")
        ),
        "model_assisted_planning_fallback_policy": (
            model_route_result_ref.get("fallback_policy")
        ),
        "model_assisted_planning_provider_switching_allowed": (
            model_route_result_ref.get("provider_switching_allowed") is True
        ),
        "model_assisted_planning_endpoint_switching_allowed": (
            model_route_result_ref.get("endpoint_switching_allowed") is True
        ),
        "model_assisted_planning_context_kinds_exercised": list(
            _safe_sequence(counts.get("model_assisted_planning_context_kinds"))
        ),
        "initial_model_assisted_planning_calls_attempted": counts.get(
            "initial_fast_model_planning_calls_attempted",
            0,
        ),
        "initial_model_assisted_planning_calls_completed": counts.get(
            "initial_fast_model_planning_calls_completed",
            0,
        ),
        "recovery_model_assisted_planning_calls_attempted": counts.get(
            "recovery_fast_model_planning_calls_attempted",
            0,
        ),
        "recovery_model_assisted_planning_calls_completed": counts.get(
            "recovery_fast_model_planning_calls_completed",
            0,
        ),
        "model_assisted_planning_raw_private_retention_false": (
            _model_assisted_planning_raw_private_retention_false(
                initial_model_planning,
                recovery_model_planning,
            )
        ),
        "model_assisted_planning_closed_surfaces_preserved": (
            _model_assisted_planning_closed_surfaces_preserved(
                initial_model_planning,
                recovery_model_planning,
            )
        ),
        "model_assisted_planning_component_count_hypothesis": (
            initial_model_planning.get("component_count_hypothesis")
        ),
        "model_assisted_planning_reduced_status": initial_model_planning.get(
            "reduced_status"
        ),
        "model_assisted_planning_consumed_by_acquisition": bool(
            acquisition.get("model_assisted_planning_consumed")
        ),
        "model_assisted_planning_consumed_by_disambiguation": bool(
            acquisition.get("model_assisted_disambiguation_consumed")
        ),
        "model_assisted_planning_consumed_by_recovery": bool(
            recovery_plan.get("model_assisted_recovery_planning_consumed")
        ),
        "acquisition_query_before_model_assisted_planning": (
            acquisition.get("deterministic_acquisition_query")
        ),
        "acquisition_query_after_model_assisted_planning": acquisition.get(
            "acquisition_query"
        ),
        "official_artifact_hypotheses": list(
            _safe_sequence(acquisition.get("official_artifact_hypotheses"))
        ),
        "planner_marked_ambiguity": acquisition.get("disambiguation_required")
        is True,
        "fast_planner_output": acquisition,
        "component_id": plan.get("component_id"),
        "component_text": plan.get("component_text"),
        "source_obligation_id": plan.get("source_obligation_id"),
        "source_obligation_text": plan.get("source_obligation_text"),
        "source_obligation_ref": source_obligation,
        "search_requirement_id": plan.get("search_requirement_id"),
        "search_requirement_text": plan.get("search_requirement_text"),
        "search_requirement_ref": search_requirement,
        "search_query_seeds": list(_safe_sequence(plan.get("search_query_seeds"))),
        "search_query_seed_used": (
            acquisition.get("acquisition_query") or _search_query_seed(plan)
            if plan
            else None
        ),
        "relation_plan_search_query_seed": _search_query_seed(plan) if plan else None,
        "acquisition_plan_diagnostics": _acquisition_plan_diagnostics(
            acquisition,
            counts=counts,
        ),
        "acquisition_plan_consumed_by_product_path": bool(acquisition),
        "provider_acquisition_query_from_plan": bool(
            acquisition.get("acquisition_query")
        ),
        "acquisition_query": acquisition.get("acquisition_query"),
        "answer_bearing_anchor_count": len(
            _safe_sequence(acquisition.get("answer_bearing_anchor_terms"))
        ),
        "expected_value_token_kinds": list(
            _safe_sequence(acquisition.get("expected_value_token_kinds"))
        ),
        "artifact_source_terms_used": list(
            _safe_sequence(acquisition.get("artifact_source_terms"))
        ),
        "selected_window_guidance_produced": bool(
            counts.get("selected_window_guidance_produced", 0)
            or acquisition.get("selected_window_guidance")
        ),
        "selected_window_guidance_consumed": bool(
            counts.get("selected_window_guidance_consumed", 0)
        ),
        "selected_window_guidance_blocked": bool(
            counts.get("selected_window_guidance_blocked", 0)
        ),
        "selected_window_anchor_guidance_consumed": bool(
            counts.get("selected_window_anchor_guidance_consumed", 0)
        ),
        "selected_window_value_token_guidance_consumed": bool(
            counts.get("selected_window_value_token_guidance_consumed", 0)
        ),
        "selected_window_value_token_guidance_blocked": bool(
            counts.get("selected_window_value_token_guidance_blocked", 0)
        ),
        "selected_window_value_token_guidance_blocker": _clean_text(
            counts.get("selected_window_value_token_guidance_blocker"),
            limit=220,
        ),
        "selected_window_guidance_blocker": _clean_text(
            counts.get("selected_window_guidance_blocker"),
            limit=220,
        ),
        "selected_window_value_token_expectations_reached_diagnostic_path": bool(
            acquisition.get("expected_value_token_kinds")
        ),
        "relation_plan_dprime_relation_intake_candidate": dprime_candidate,
        "dprime_relation_intake_ref": relation_ref,
        "dprime_relation_intake_candidate_consumed_from_plan": bool(
            dprime_candidate
            and relation_ref
            and relation_ref.get("component_id") == plan.get("component_id")
            and relation_ref.get("source_obligation_candidate_ids")
            == [plan.get("source_obligation_id")]
        ),
        "future_component_work_node_candidate": future_node,
        "provider_acquisition_route_posture": (
            _provider_acquisition_route_posture(counts)
        ),
        "run_kernel_local_accounting_authorized_planner": bool(acquisition),
        "run_kernel_local_accounting_authorized_disambiguation": bool(
            disambiguation
        ),
        "run_kernel_local_accounting_authorized_source_acquisition": bool(
            counts.get("extraction_provider_calls_attempted", 0)
        ),
        "run_kernel_dag_scheduling_required": False,
        "disambiguator_added": True,
        "disambiguator_used": bool(disambiguation),
        "disambiguation_record": disambiguation,
        "serper_primary_source_acquisition_removed": True,
        "serper_used_as_primary_source_acquisition": False,
        "serper_output_used_as_evidence": False,
        "serper_output_recorded_as_non_evidence": bool(disambiguation),
        "serper_scout_calls_attempted": counts.get(
            "serper_scout_calls_attempted",
            0,
        ),
        "serper_scout_calls_completed": counts.get(
            "serper_scout_calls_completed",
            0,
        ),
        "serper_scout_reason": (
            acquisition.get("disambiguation_reason")
            if disambiguation
            else "not_attempted_clear_query"
        ),
        "extraction_provider": acquisition.get("extraction_provider")
        or DEFAULT_EXTRACTION_PROVIDER,
        "extraction_provider_used": bool(
            counts.get("extraction_provider_calls_attempted", 0)
        ),
        "extraction_provider_calls_attempted": counts.get(
            "extraction_provider_calls_attempted",
            0,
        ),
        "extraction_provider_calls_completed": counts.get(
            "extraction_provider_calls_completed",
            0,
        ),
        "source_acquisition_mode": counts.get(
            "source_acquisition_mode",
            SOURCE_ACQUISITION_MODE_NONE,
        ),
        "provider_extracted_content_obtained": bool(
            counts.get("provider_extracted_content_handoff_created", 0)
        ),
        "provider_extracted_content_candidate_count": counts.get(
            "provider_extracted_content_candidate_count",
            0,
        ),
        "provider_extracted_content_handoff_created": bool(
            counts.get("provider_extracted_content_handoff_created", 0)
        ),
        "provider_extracted_content_admitted_to_fetch_read_packet": bool(
            counts.get("provider_extracted_content_handoff_created", 0)
        ),
        "provider_extracted_content_admission_blocked": (
            counts.get("fetch_read_blocker")
            == PROVIDER_EXTRACTED_CONTENT_CUSTODY_ADMISSION_BLOCKED
        ),
        "provider_extracted_original_url_bindings_preserved": bool(
            counts.get("provider_extracted_content_handoff_created", 0)
        ),
        "provider_answer_products_used": False,
        "provider_sourced_answer_used": False,
        "provider_snippets_remain_directionality_only": True,
        "direct_url_fetch_primary_happy_path": False,
        "direct_url_fetch_fallback_or_diagnostic_only": True,
        "direct_fetch_read_attempts": counts.get("direct_fetch_read_attempts", 0),
        "optional_evidence_triage_implemented": bool(triage_packet),
        "optional_evidence_triage_deferred_to": None if triage_packet else (
            "CURRENT-SOURCE-RECORD-ANALYST-WORKBENCH-FULL-SLICE-SCAFFOLD-01"
        ),
        "candidate_evidence_triage_packet": triage_packet,
        "candidate_evidence_triage_ref": triage_ref,
        "candidate_evidence_triage_packet_created": counts.get(
            "candidate_evidence_triage_packet_created",
            0,
        ),
        "candidate_evidence_triage_consumed_by_product_path": bool(triage_packet),
        "analyst_workbench_packet": workbench_packet,
        "analyst_workbench_ref": workbench_ref,
        "analyst_workbench_packet_created": counts.get(
            "analyst_workbench_packet_created",
            0,
        ),
        "analyst_workbench_consumed_by_product_path": bool(workbench_packet),
        "analysis_gap_search_proposal": gap_proposal,
        "analysis_gap_search_proposal_ref": gap_ref,
        "analysis_gap_search_proposal_created": counts.get(
            "analysis_gap_search_proposal_created",
            0,
        ),
        "workbench_dprime_dossier": dprime_dossier,
        "workbench_dprime_dossier_ref": dprime_dossier_ref,
        "workbench_dprime_dossier_created": counts.get(
            "workbench_dprime_dossier_created",
            0,
        ),
        "workbench_dprime_dossier_consumed_by_product_path": bool(dprime_dossier),
        "workbench_dprime_dossier_consumed_by_dprime": workbench_dprime_consumed,
        "workbench_reduction_projection": projection,
        "workbench_reduction_projection_ref": projection_ref,
        "workbench_reduction_projection_status": projection.get("status"),
        "workbench_reduction_projection_created": counts.get(
            "workbench_reduction_projection_created",
            0,
        ),
        "workbench_gap_reentry_ref": workbench_gap_reentry,
        "workbench_gap_reentry_status": workbench_gap_reentry.get(
            "workbench_gap_reentry_status"
        ),
        "followup_search_intent_ref": _safe_mapping(
            workbench_gap_reentry.get("followup_search_intent_ref")
        ),
        "runkernel_followup_authorization_ref": _safe_mapping(
            workbench_gap_reentry.get("runkernel_followup_authorization_ref")
        ),
        "runkernel_followup_authorization_status": (
            workbench_gap_reentry.get("runkernel_followup_authorization_status")
        ),
        "followup_execution_status": workbench_gap_reentry.get(
            "followup_execution_status"
        ),
        "followup_execution_licensed": (
            workbench_gap_reentry.get("followup_execution_licensed") is True
        ),
        "ordinary_search_path_reused_for_gap_reentry": (
            workbench_gap_reentry.get("ordinary_search_path_reused") is True
        ),
        "new_search_subsystem_created_for_gap_reentry": (
            workbench_gap_reentry.get("new_search_subsystem_created") is True
        ),
        "live_runs_attempted": (
            1
            if (
                counts.get("provider_calls_attempted", 0)
                or counts.get("serper_scout_calls_attempted", 0)
            )
            else 0
        ),
        "query_plans_consumed": counts.get("query_plans_consumed", 0),
        "provider_calls_attempted": counts.get("provider_calls_attempted", 0),
        "provider_calls_completed": counts.get("provider_calls_completed", 0),
        "source_obligation_recovery_authorization": (
            source_obligation_authorization
        ),
        "single_relation_source_obligation_recovery_authorization": (
            source_obligation_authorization
        ),
        "source_obligation_recovery_authorization_status": (
            source_obligation_authorization.get("authorization_status")
            or "not_created"
        ),
        "source_obligation_recovery_authorization_owner": (
            source_obligation_authorization.get("authorization_owner")
        ),
        "single_relation_answer_contract_projection": (
            source_obligation_authorization.get("current_answer_contract_projection")
            or {}
        ),
        "single_relation_answer_contract_state": (
            source_obligation_authorization.get("updated_contract_state") or {}
        ),
        "answer_contract_reducer_owner": source_obligation_authorization.get(
            "contract_reducer_owner"
        ),
        "answer_contract_reducer_kind": source_obligation_authorization.get(
            "contract_reducer_kind"
        ),
        "source_obligation_recovery_required": bool(
            source_obligation_authorization.get("recovery_required")
        ),
        "source_obligation_recovery_confirmation_required": bool(
            source_obligation_authorization.get("recovery_confirmation_required")
        ),
        "source_obligation_recovery_call_policy_authorized": bool(
            source_obligation_authorization.get("recovery_call_policy_authorized")
        ),
        "source_obligation_recovery_support_admission_blocked": bool(
            source_obligation_authorization.get("support_admission_blocked")
        ),
        "source_obligation_recovery_answer_display_blocked": bool(
            source_obligation_authorization.get("answer_display_blocked")
        ),
        "source_obligation_recovery_source_display_blocked": bool(
            source_obligation_authorization.get("source_display_blocked")
        ),
        "source_obligation_recovery_reason": (
            source_obligation_authorization.get("recovery_reason")
        ),
        "source_obligation_recovery_provider_neutral_domain_constraints": list(
            _safe_sequence(
                source_obligation_authorization.get(
                    "provider_neutral_domain_constraints"
                )
            )
        ),
        "source_obligation_recovery_run_kernel_support_admission_decision_status": (
            source_obligation_authorization.get(
                "run_kernel_support_admission_decision_status"
            )
        ),
        "source_challenge_recovery_trigger_eligible": bool(
            recovery.get("trigger_eligible")
        ),
        "source_challenge_recovery_plan_created": bool(recovery_plan),
        "source_challenge_recovery_plan": recovery_plan,
        "source_challenge_recovery_query_before_model_assisted_planning": (
            recovery_plan.get("recovery_query_before_model_assisted_planning")
        ),
        "source_challenge_recovery_query_after_model_assisted_planning": (
            recovery_plan.get("recovery_query")
        ),
        "source_challenge_recovery_official_artifact_hypotheses": list(
            _safe_sequence(recovery_plan.get("official_artifact_hypotheses"))
        ),
        "source_challenge_recovery_status": recovery.get("status")
        or "not_triggered",
        "source_challenge_recovery_blocker": recovery.get("blocker"),
        "source_challenge_recovery_blocker_detail": recovery.get("detail"),
        "source_challenge_recovery_provider_calls_attempted": counts.get(
            "source_challenge_recovery_provider_calls_attempted",
            0,
        ),
        "source_challenge_recovery_provider_calls_completed": counts.get(
            "source_challenge_recovery_provider_calls_completed",
            0,
        ),
        "source_challenge_recovery_provider_results_returned": counts.get(
            "source_challenge_recovery_provider_results_returned",
            0,
        ),
        "source_challenge_recovery_domain_constraints": list(
            _safe_sequence(recovery_plan.get("domain_constraints"))
        ),
        "source_challenge_recovery_domain_constraints_acquisition_only": True,
        "source_challenge_recovery_domain_constraints_create_source_authority": False,
        "source_challenge_recovery_domain_constraints_satisfy_source_obligation": False,
        "source_challenge_recovery_domain_constraints_citation_eligible": False,
        "source_challenge_recovery_domain_constraints_claim_correctness": False,
        "source_challenge_recovery_material_acquired": bool(
            recovery_result.get("official_answer_bearing_material_acquired")
        ),
        "source_challenge_recovery_official_candidate_selected": bool(
            recovery_result.get("official_source_of_record_looking_candidate_selected")
        ),
        "source_challenge_recovery_result": recovery_result,
        "source_challenge_recovery_support_created": False,
        "source_challenge_recovery_dprime_rereview_licensed": False,
        "source_challenge_recovery_source_authority_adjudicated": False,
        "source_challenge_recovery_source_obligation_satisfied": False,
        "source_challenge_recovery_answer_created": False,
        "search_tasks_attempted": counts.get("search_tasks_attempted", 0),
        "search_tasks_completed": counts.get("search_tasks_completed", 0),
        "provider_results_returned": counts.get("provider_results_returned", 0),
        "fetch_read_attempts": counts.get("fetch_read_attempts", 0),
        "fetch_read_completed": counts.get("fetch_read_completed", 0),
        "fetch_read_blocker": _clean_text(
            counts.get("fetch_read_blocker"),
            limit=220,
        ),
        "fetch_read_blocker_detail": _clean_text(
            counts.get("fetch_read_blocker_detail"),
            limit=900,
        ),
        "fetch_read_status_class_summary": _status_class_summary(
            counts.get("fetch_read_status_classes")
        ),
        "fetch_read_content_type_summary": _content_type_summary(
            counts.get("fetch_read_content_types")
        ),
        "fetch_read_failure_category_summary": _failure_category_summary(
            counts.get("fetch_read_failure_categories")
        ),
        "fetch_read_candidate_diagnostics": list(
            _safe_sequence(counts.get("fetch_read_candidate_diagnostics"))
        ),
        "fetch_read_attempt_diagnostics": list(
            _safe_sequence(counts.get("fetch_read_attempt_diagnostics"))
        ),
        "answer_bearing_candidate_window_status": _clean_text(
            counts.get("answer_bearing_candidate_window_status"),
            limit=120,
        ),
        "answer_bearing_candidate_window_best_effort": bool(
            counts.get("answer_bearing_candidate_window_best_effort")
        ),
        "answer_bearing_candidate_window_not_established": bool(
            counts.get("answer_bearing_candidate_window_not_established")
        ),
        "answer_bearing_candidate_window_diagnostics": list(
            _safe_sequence(counts.get("answer_bearing_candidate_window_diagnostics"))
        ),
        "fetch_read_public_web_request_profile_id": (
            FETCH_READ_PUBLIC_WEB_REQUEST_PROFILE_ID
        ),
        "fetch_read_public_web_request_posture": (
            FETCH_READ_PUBLIC_WEB_REQUEST_POSTURE
        ),
        "official_http_source_survival_blocker_available": True,
        "official_http_source_survival_blocker_active": (
            counts.get("fetch_read_blocker")
            == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX
        ),
        "http_source_survival_scope": "ordinary_public_web_fetch_read_hygiene",
        "http_source_survival_request_hygiene_added": True,
        "http_source_survival_access_control_bypass_opened": False,
        "http_source_survival_login_session_handling_opened": False,
        "http_source_survival_captcha_handling_opened": False,
        "http_source_survival_javascript_browser_automation_opened": False,
        "http_source_survival_proxy_rotation_opened": False,
        "http_source_survival_referer_spoofing_opened": False,
        "http_source_survival_domain_specific_header_hacks_opened": False,
        "http_source_survival_domain_specific_url_fallback_opened": False,
        "http_source_survival_canonical_url_transformation_opened": False,
        "provider_routing_changed": bool(plan),
        "provider_query_generation_changed": bool(
            acquisition.get("acquisition_query")
            and acquisition.get("acquisition_query") != _search_query_seed(plan)
        ),
        "fetch_read_cap_preserved": True,
        "fetch_read_cap_value": MAX_FETCH_READ_ATTEMPTS,
        "candidate_diagnostics_observability_only": True,
        "candidate_diagnostics_satisfy_source_obligations": False,
        "provider_snippets_used_as_evidence": False,
        "fetch_read_failure_metadata_citation_eligible": False,
        "fetch_read_failure_metadata_satisfies_source_obligations": False,
        "official_pdf_table_read_support_adapter": "existing_fetch_read_content_packet",
        "official_pdf_table_read_support_status_summary": (
            _official_artifact_read_support_status_summary(
                counts.get("fetch_read_candidate_diagnostics")
            )
        ),
        "official_pdf_table_artifact_candidate_count": (
            _official_artifact_candidate_count(
                counts.get("fetch_read_candidate_diagnostics")
            )
        ),
        "official_pdf_table_read_support_obtained": (
            _official_artifact_read_support_status_seen(
                counts.get("fetch_read_candidate_diagnostics"),
                OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE,
            )
        ),
        "official_pdf_table_read_support_needed": (
            _official_artifact_read_support_status_seen(
                counts.get("fetch_read_candidate_diagnostics"),
                OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_UNREADABLE,
            )
        ),
        "official_pdf_table_read_support_raw_content_retained": False,
        "official_pdf_table_read_support_creates_source_authority": False,
        "official_pdf_table_read_support_satisfies_source_obligation": False,
        "official_pdf_table_read_support_citation_eligible": False,
        "official_pdf_table_read_support_claims_correctness": False,
        "official_pdf_table_read_support_adds_dependency": False,
        "official_pdf_table_read_support_uses_ocr": False,
        "official_pdf_table_read_support_uses_browser_automation": False,
        "pdf_content_type_support_opened": False,
        "pdf_parsing_opened": False,
        "candidate_ranking_policy_changed": False,
        "candidate_selection_policy_id": FETCH_READ_CANDIDATE_SELECTION_POLICY_ID,
        "candidate_selection_policy_scope": FETCH_READ_CANDIDATE_SELECTION_SCOPE,
        "candidate_selection_policy_uses_sanitized_metadata_only": True,
        "candidate_selection_uses_provider_snippet": False,
        "candidate_selection_is_acquisition_only": True,
        "candidate_selection_created_source_authority": False,
        "candidate_selection_satisfies_source_obligation": False,
        "candidate_selection_citation_eligible": False,
        "candidate_selection_claims_correctness": False,
        "candidate_selection_global_ranking_policy_created": False,
        "candidate_selection_source_authority_policy_created": False,
        "candidate_selection_approved_domain_list_created": False,
        "candidate_selection_retrieval_filtering_layer_created": False,
        "fetch_read_packet_created": counts.get("fetch_read_packet_created", 0),
        "evidence_ledger_admissions": counts.get("evidence_ledger_admissions", 0),
        "dprime_review_licensed": bool(confirm_live_dprime_review),
        "model_review_licensed": bool(confirm_live_dprime_review),
        "dprime_model_review_call_count": counts.get(
            "dprime_model_review_calls_attempted",
            0,
        ),
        "dprime_model_review_calls_attempted": counts.get(
            "dprime_model_review_calls_attempted",
            0,
        ),
        "dprime_model_review_calls_completed": counts.get(
            "dprime_model_review_calls_completed",
            0,
        ),
        "followup_loop_count": counts.get("followup_loop_count", 0),
        "followup_loops": 0,
        "fap_calls": MAX_FAP_CALLS,
        "author_calls": MAX_AUTHOR_CALLS,
        "independent_source_checks_outside_product_path": (
            MAX_INDEPENDENT_SOURCE_CHECKS
        ),
        "caps": _caps_ref(),
        "caps_exhausted": caps_exhausted,
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        **RAW_FALSE_FLAGS,
        **CLOSED_FALSE_FLAGS,
        "semantic_status_payload": _packet_safe_payload(semantic),
        "retained_artifact_root": _display_path(retained_root) if retained_root else None,
        "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
    }


def _guard_plan_for_live_acquisition(plan: Mapping[str, Any]) -> None:
    if plan.get("planning_status") != "planned":
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
            "relation plan was not planned.",
        )
    if _bounded_int(plan.get("component_count")) != 1:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
            "generic live path requires exactly one planned component.",
        )
    if _bounded_int(plan.get("source_obligation_count")) != 1:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
            "generic live path requires exactly one source-obligation ref.",
        )
    if _bounded_int(plan.get("search_requirement_count")) != 1:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
            "generic live path requires exactly one search requirement.",
        )
    if not _safe_sequence(plan.get("search_query_seeds")):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
            "relation plan did not provide a live search query seed.",
        )
    dprime = _safe_mapping(plan.get("dprime_relation_intake_candidate"))
    if dprime.get("relation_plan_id") != plan.get("plan_id"):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
            "relation plan did not provide a plan-bound D-prime intake candidate.",
        )


def _initial_model_planning_context(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "planning_context_kind": PLANNING_CONTEXT_INITIAL_SINGLE_RELATION,
        "normalized_user_question": plan.get("sanitized_query"),
        "relation_plan_id": plan.get("plan_id"),
        "component_id": plan.get("component_id"),
        "component_text": plan.get("component_text"),
        "fact_kind": plan.get("fact_kind"),
        "source_obligation_id": plan.get("source_obligation_id"),
        "source_obligation_text": plan.get("source_obligation_text"),
        "search_requirement_id": plan.get("search_requirement_id"),
        "search_requirement_text": plan.get("search_requirement_text"),
        "search_query_seeds": list(_safe_sequence(plan.get("search_query_seeds"))),
        "supported_query_class_id": plan.get("supported_query_class_id"),
        "deterministic_supported_query_gate_already_passed": True,
        "multi_component_execution_opened": False,
        "evidence_created": False,
        "source_authority_decided": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
        "answer_text_created": False,
    }


def _recovery_model_planning_context(
    *,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any],
    counts: Mapping[str, Any],
    semantic_payload: Mapping[str, Any],
    source_obligation_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    selected = _selected_source_challenge_candidate_diagnostic(counts)
    return {
        "planning_context_kind": PLANNING_CONTEXT_SOURCE_OF_RECORD_RECOVERY,
        "normalized_user_question": relation_plan.get("sanitized_query"),
        "relation_plan_id": relation_plan.get("plan_id"),
        "component_id": relation_plan.get("component_id"),
        "component_text": relation_plan.get("component_text"),
        "fact_kind": relation_plan.get("fact_kind"),
        "source_obligation_id": relation_plan.get("source_obligation_id"),
        "source_obligation_text": relation_plan.get("source_obligation_text"),
        "acquisition_plan": _safe_mapping(acquisition_plan),
        "selected_candidate_diagnostic": _safe_mapping(selected),
        "candidate_diagnostics": [
            _safe_mapping(item)
            for item in _safe_sequence(counts.get("fetch_read_candidate_diagnostics"))
        ],
        "provider_acquisition_attempt_counts": {
            "provider_calls_attempted": counts.get("provider_calls_attempted", 0),
            "provider_calls_completed": counts.get("provider_calls_completed", 0),
            "provider_results_returned": counts.get("provider_results_returned", 0),
        },
        "dprime_status": _safe_mapping(semantic_payload.get("dprime_status")),
        "source_obligation_recovery_authorization": _safe_mapping(
            source_obligation_authorization
        ),
        "run_kernel_authorized_recovery": (
            source_obligation_authorization.get("recovery_required") is True
        ),
        "evidence_created_by_planner": False,
        "source_authority_decided_by_planner": False,
        "source_obligation_satisfied_by_planner": False,
        "citation_eligible_by_planner": False,
        "answer_text_created_by_planner": False,
    }


def _model_assisted_planning_route_ref(
    *,
    strict_model_route_ref: Mapping[str, Any] | None,
    fast_provider: str | None,
    fast_model: str | None,
    fast_model_local_url: str | None,
    require_model_assisted_planning: bool,
    planner_callable: Callable[..., Any] | None,
) -> dict[str, Any] | None:
    if strict_model_route_ref is None:
        if not require_model_assisted_planning and planner_callable is None:
            return None
        return _strict_route_unavailable_candidate_ref(
            fast_provider=fast_provider,
            fast_model=fast_model,
            fast_model_local_url=fast_model_local_url,
        )
    route = dict(strict_model_route_ref)
    route.update(
        _configured_fast_model_route_posture(
            fast_provider=fast_provider,
            fast_model=fast_model,
            fast_model_local_url=fast_model_local_url,
            include_absent=False,
        )
    )
    return _json_safe(route)


def _strict_route_unavailable_candidate_ref(
    *,
    fast_provider: str | None,
    fast_model: str | None,
    fast_model_local_url: str | None,
) -> dict[str, Any]:
    route = {
        "model_task": MODEL_ASSISTED_PLANNING_MODEL_TASK,
        "product_model_role": MODEL_ASSISTED_PLANNING_PRODUCT_MODEL_ROLE,
        "product_route_kind": "strict_one_shot_model_route_unavailable_candidate",
        "max_model_calls": 0,
        "retry_policy": "unavailable",
        "fallback_policy": "unavailable",
        "timeout_policy": "unavailable",
        "provider_switching_allowed": False,
        "endpoint_switching_allowed": False,
        "strict_one_shot": False,
        "call_count": 0,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "provider_payload_retained": False,
    }
    route.update(
        _configured_fast_model_route_posture(
            fast_provider=fast_provider,
            fast_model=fast_model,
            fast_model_local_url=fast_model_local_url,
        )
    )
    return _json_safe(route)


def _configured_fast_model_route_posture(
    *,
    fast_provider: str | None,
    fast_model: str | None,
    fast_model_local_url: str | None,
    include_absent: bool = True,
) -> dict[str, Any]:
    posture: dict[str, Any] = {}
    cleaned_provider = _safe_route_text(fast_provider, limit=80)
    cleaned_model = _safe_route_text(fast_model, limit=120)
    local_url = _clean_text(fast_model_local_url, limit=500)
    if cleaned_provider or include_absent:
        posture["configured_fast_provider"] = cleaned_provider
        endpoint_kind = _configured_endpoint_kind(cleaned_provider)
        if endpoint_kind or include_absent:
            posture["configured_endpoint_kind"] = endpoint_kind
    if cleaned_model or include_absent:
        posture["configured_fast_model"] = cleaned_model
    if local_url or include_absent:
        posture["configured_local_url_present"] = bool(local_url)
        posture["configured_local_url_posture"] = _local_url_posture(local_url)
    return posture


def _configured_endpoint_kind(fast_provider: str | None) -> str | None:
    normalized = _normalize_key(fast_provider)
    if normalized == "openai":
        return "openai_responses_api"
    if normalized in {
        "openrouter",
        "open_router",
        "local",
        "lm_studio",
        "local_lm_studio",
        "local_(lm_studio)",
    }:
        return "chat_completions_compatible"
    return None


def _local_url_posture(local_url: str | None) -> str:
    if not local_url:
        return "not_configured"
    parsed = urlparse(local_url)
    host = (parsed.hostname or "").casefold()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".localhost"):
        return "local_configured_not_retained"
    if parsed.scheme in {"http", "https"} and host:
        return "remote_configured_not_retained"
    return "configured_unvalidated_not_retained"


def _model_assisted_planning_route_diagnostic_ref(
    *packets: Mapping[str, Any],
) -> dict[str, Any]:
    for packet in packets:
        route_ref = _safe_mapping(_safe_mapping(packet).get("strict_model_route_ref"))
        if route_ref:
            return route_ref
    return {}


def _model_assisted_planning_route_result_diagnostic_ref(
    *packets: Mapping[str, Any],
) -> dict[str, Any]:
    for packet in packets:
        route_ref = _safe_mapping(
            _safe_mapping(packet).get("strict_model_route_result_ref")
        )
        if route_ref:
            return route_ref
    return {}


def _build_model_assisted_planning_packet(
    *,
    planning_context_kind: str,
    context_state: Mapping[str, Any],
    planner_callable: Callable[..., Any] | None,
    strict_model_route_ref: Mapping[str, Any] | None,
    clean_json_response: Callable[[str], str] | None,
    require_model_assisted_planning: bool,
) -> dict[str, Any] | None:
    if not require_model_assisted_planning and planner_callable is None:
        return None
    packet = build_model_assisted_single_relation_planning_packet(
        planning_context_kind=planning_context_kind,
        context_state=context_state,
        planner_callable=planner_callable,
        strict_model_route_ref=strict_model_route_ref,
        clean_json_response=clean_json_response,
    )
    _reject_forbidden_material(packet, context="model-assisted planning packet")
    return packet


def _record_model_assisted_planning_counts(
    counts: dict[str, Any],
    packet: Mapping[str, Any] | None,
    *,
    prefix: str,
) -> None:
    safe = _safe_mapping(packet)
    if not safe:
        return
    context_kind = _clean_text(safe.get("planning_context_kind"), limit=120)
    attempted = _bounded_int(safe.get("model_calls_attempted"))
    completed = _bounded_int(safe.get("model_calls_completed"))
    counts["fast_planner_model_calls_attempted"] = (
        _bounded_int(counts.get("fast_planner_model_calls_attempted")) + attempted
    )
    counts["fast_planner_model_calls_completed"] = (
        _bounded_int(counts.get("fast_planner_model_calls_completed")) + completed
    )
    counts[f"{prefix}_fast_model_planning_calls_attempted"] = attempted
    counts[f"{prefix}_fast_model_planning_calls_completed"] = completed
    if context_kind:
        counts["model_assisted_planning_context_kinds"] = (
            _merge_model_assisted_planning_contexts(
                counts.get("model_assisted_planning_context_kinds"),
                (context_kind,),
            )
        )


def _record_analyst_workbench_counts(
    counts: dict[str, Any],
    bundle: Mapping[str, Any],
) -> None:
    try:
        safe = validate_current_source_record_analyst_workbench_bundle(bundle)
    except AnalystWorkbenchError as exc:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            f"Analyst Workbench proposal-only boundary invalid: {exc}",
        ) from exc
    counts["analyst_workbench_bundle"] = safe
    counts["candidate_evidence_triage_packet_created"] = int(
        bool(_safe_mapping(safe.get("candidate_evidence_triage_packet")))
    )
    counts["analyst_workbench_packet_created"] = int(
        bool(_safe_mapping(safe.get("analyst_workbench_packet")))
    )
    counts["analysis_gap_search_proposal_created"] = int(
        bool(_safe_mapping(safe.get("analysis_gap_search_proposal")))
    )
    counts["workbench_dprime_dossier_created"] = int(
        bool(_safe_mapping(safe.get("workbench_dprime_dossier")))
    )
    counts["workbench_reduction_projection_created"] = int(
        bool(_safe_mapping(safe.get("workbench_reduction_projection")))
    )


def _analyst_workbench_bundle_from_counts(
    counts: Mapping[str, Any],
) -> dict[str, Any]:
    bundle = _safe_mapping(counts.get("analyst_workbench_bundle"))
    if bundle:
        try:
            return validate_current_source_record_analyst_workbench_bundle(bundle)
        except AnalystWorkbenchError as exc:
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
                f"Analyst Workbench bundle invalid: {exc}",
            ) from exc
    return empty_current_source_record_analyst_workbench_bundle()


def _workbench_dossier_consumed_by_dprime(
    semantic_payload: Mapping[str, Any],
    *,
    dprime_dossier_ref: Mapping[str, Any],
) -> bool:
    expected_digest = _clean_text(
        dprime_dossier_ref.get("dossier_digest"),
        limit=128,
    )
    if not expected_digest:
        return False
    semantic_ref = _safe_mapping(
        semantic_payload.get("workbench_dprime_dossier_ref")
    )
    dprime = _safe_mapping(semantic_payload.get("dprime_status"))
    input_ref = _safe_mapping(dprime.get("input_packet_ref"))
    input_workbench_ref = _safe_mapping(input_ref.get("workbench_dprime_dossier_ref"))
    return expected_digest in {
        _clean_text(semantic_ref.get("dossier_digest"), limit=128),
        _clean_text(input_workbench_ref.get("dossier_digest"), limit=128),
    }


def _merge_model_assisted_planning_contexts(
    existing: Any,
    new: Any,
) -> tuple[str, ...]:
    return tuple(_unique_clean_terms([*_safe_sequence(existing), *_safe_sequence(new)], limit=4))


def _model_assisted_planning_strict_route_blocked(
    packet: Mapping[str, Any] | None,
    *,
    require_model_assisted_planning: bool,
) -> bool:
    safe = _safe_mapping(packet)
    return bool(
        require_model_assisted_planning
        and (
            not safe
            or safe.get("blocker")
            == BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE
        )
    )


def _model_assisted_planning_required_blocked(
    packet: Mapping[str, Any] | None,
    *,
    require_model_assisted_planning: bool,
) -> bool:
    safe = _safe_mapping(packet)
    return bool(require_model_assisted_planning and safe.get("blocker"))


def _model_assisted_planning_multi_component_closed(
    packet: Mapping[str, Any] | None,
) -> bool:
    safe = _safe_mapping(packet)
    return (
        safe.get("reduced_status")
        == "likely_multi_component_currently_closed"
        or safe.get("component_count_hypothesis") == "likely_multi_component"
    )


def _model_assisted_planning_raw_private_retention_false(
    *packets: Mapping[str, Any],
) -> bool:
    for packet in packets:
        safe = _safe_mapping(packet)
        if not safe:
            continue
        flags = _safe_mapping(safe.get("raw_private_retention_flags"))
        if any(value is not False for value in flags.values()):
            return False
        for key in (
            "raw_prompt_retained",
            "raw_model_response_retained",
            "raw_provider_payload_retained",
            "raw_search_response_retained",
        ):
            if safe.get(key) is not False:
                return False
    return True


def _model_assisted_planning_closed_surfaces_preserved(
    *packets: Mapping[str, Any],
) -> bool:
    for packet in packets:
        safe = _safe_mapping(packet)
        if not safe:
            continue
        flags = _safe_mapping(safe.get("closed_surface_flags"))
        if any(value is not False for value in flags.values()):
            return False
        for key in (
            "planner_output_is_evidence",
            "planner_output_citation_eligible",
            "planner_output_satisfies_source_obligation",
            "planner_output_decides_source_authority",
            "planner_output_creates_answer_text",
            "planner_output_claims_correctness",
        ):
            if safe.get(key) is not False:
                return False
    return True


def _model_planning_text_list(
    packet: Mapping[str, Any],
    key: str,
    *,
    limit: int,
    max_items: int,
) -> list[str]:
    return [
        item
        for item in (
            _clean_text(raw, limit=limit)
            for raw in _safe_sequence(packet.get(key))
        )
        if item
    ][:max_items]


def _model_assisted_acquisition_query(
    *,
    deterministic_query: str,
    model_planning_packet: Mapping[str, Any],
    official_artifact_hypotheses: Sequence[str],
) -> str:
    preferred = _clean_text(
        model_planning_packet.get("preferred_acquisition_query"),
        limit=220,
    )
    if preferred:
        return preferred
    variants = _model_planning_text_list(
        model_planning_packet,
        "acquisition_query_variants",
        limit=220,
        max_items=3,
    )
    if variants:
        return variants[0]
    if official_artifact_hypotheses:
        query = " ".join(
            _unique_clean_terms(
                [deterministic_query, *official_artifact_hypotheses],
                limit=10,
            )
        )
        return _clean_text(query, limit=220) or deterministic_query
    return deterministic_query


def _recovery_plan_with_model_assisted_hints(
    plan: Mapping[str, Any],
    *,
    recovery_model_planning_packet: Mapping[str, Any] | None,
) -> dict[str, Any]:
    safe_plan = _safe_mapping(plan)
    model_planning = _safe_mapping(recovery_model_planning_packet)
    if not safe_plan or not model_planning:
        return safe_plan
    revised = dict(safe_plan)
    original_query = _clean_text(safe_plan.get("recovery_query"), limit=260)
    preferred = _clean_text(
        model_planning.get("preferred_recovery_query"),
        limit=240,
    )
    variants = _model_planning_text_list(
        model_planning,
        "recovery_query_variants",
        limit=240,
        max_items=3,
    )
    revised["recovery_query_before_model_assisted_planning"] = original_query
    if preferred:
        revised["recovery_query"] = preferred
    elif variants:
        revised["recovery_query"] = variants[0]
    revised["model_assisted_recovery_planning_consumed"] = True
    revised["model_assisted_recovery_planning_packet"] = model_planning
    revised["official_artifact_hypotheses"] = _model_planning_text_list(
        model_planning,
        "official_or_source_of_record_artifact_hypotheses",
        limit=180,
        max_items=6,
    )
    revised["recovery_query_variants"] = variants
    revised["planner_output_is_evidence"] = False
    revised["planner_output_citation_eligible"] = False
    revised["planner_output_satisfies_source_obligation"] = False
    revised["planner_output_decides_source_authority"] = False
    revised["planner_output_creates_answer_text"] = False
    revised["planner_output_claims_correctness"] = False
    _reject_forbidden_material(revised, context="model-assisted recovery plan")
    return _json_safe(revised)


def _build_fast_acquisition_plan(
    plan: Mapping[str, Any],
    *,
    model_planning_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    relation_seed = _search_query_seed(plan)
    component_text = _clean_text(plan.get("component_text"), limit=260) or relation_seed
    query_text = _clean_text(plan.get("sanitized_query"), limit=500) or relation_seed
    fact_kind = _clean_text(plan.get("fact_kind"), limit=80) or "current_value"
    model_planning = _safe_mapping(model_planning_packet)
    subject_anchors = _subject_entity_anchors(query_text, component_text)
    form_anchors = _form_document_code_anchors(query_text, component_text)
    fact_anchor = _fact_kind_anchor(component_text, fact_kind)
    timeframe_posture = _timeframe_currentness_posture(query_text, component_text)
    source_artifact_expectation = _source_artifact_expectation(fact_kind)
    artifact_terms = _artifact_source_terms(
        fact_kind=fact_kind,
        form_anchors=form_anchors,
        timeframe_posture=timeframe_posture,
    )
    answer_bearing_anchors = _answer_bearing_anchor_terms(
        subject_anchors=subject_anchors,
        form_anchors=form_anchors,
        fact_anchor=fact_anchor,
        component_text=component_text,
        fact_kind=fact_kind,
    )
    value_token_kinds = _expected_value_token_kinds(fact_kind, component_text)
    deterministic_acquisition_query = _artifact_oriented_acquisition_query(
        subject_anchors=subject_anchors,
        form_anchors=form_anchors,
        fact_anchor=fact_anchor,
        component_text=component_text,
        artifact_terms=artifact_terms,
        timeframe_posture=timeframe_posture,
        fallback=relation_seed,
    )
    official_artifact_hypotheses = _model_planning_text_list(
        model_planning,
        "official_or_source_of_record_artifact_hypotheses",
        limit=180,
        max_items=6,
    )
    likely_official_domains = _model_planning_text_list(
        model_planning,
        "likely_official_domains",
        limit=160,
        max_items=6,
    )
    model_anchor_terms = _model_planning_text_list(
        model_planning,
        "answer_bearing_anchor_terms",
        limit=120,
        max_items=10,
    )
    model_value_token_kinds = _model_planning_text_list(
        model_planning,
        "expected_value_token_kinds",
        limit=40,
        max_items=6,
    )
    answer_bearing_anchors = _unique_clean_terms(
        [*answer_bearing_anchors, *model_anchor_terms],
        limit=10,
    )
    if model_value_token_kinds:
        value_token_kinds = _unique_clean_terms(
            [*value_token_kinds, *model_value_token_kinds],
            limit=6,
        )
    acquisition_query = _model_assisted_acquisition_query(
        deterministic_query=deterministic_acquisition_query,
        model_planning_packet=model_planning,
        official_artifact_hypotheses=official_artifact_hypotheses,
    )
    ambiguity_required, ambiguity_reason = _planner_ambiguity_posture(plan)
    model_disambiguation_required = (
        model_planning.get("disambiguation_status")
        == "ambiguous_needs_disambiguation"
    )
    if model_disambiguation_required:
        ambiguity_required = True
        ambiguity_reason = (
            _clean_text(model_planning.get("disambiguation_reason"), limit=220)
            or "model_assisted_planning_marked_ambiguity"
        )
    payload = {
        "schema_version": ACQUISITION_PLANNER_SCHEMA_VERSION,
        "planner_kind": ACQUISITION_PLANNER_KIND,
        "planner_route": (
            "model_assisted_relation_plan_adapter"
            if model_planning
            else "existing_deterministic_relation_plan_adapter"
        ),
        "planner_type": "model_assisted_reduced" if model_planning else "deterministic",
        "fast_model_route_used": bool(model_planning.get("model_calls_attempted")),
        "fast_model_planner_used": bool(model_planning),
        "fast_model_route_reason": (
            "strict_injected_model_assisted_planning_packet_reduced"
            if model_planning
            else "no strict FastModel planning packet configured"
        ),
        "model_calls_attempted": _bounded_int(
            model_planning.get("model_calls_attempted"),
            default=0,
        ),
        "model_calls_completed": _bounded_int(
            model_planning.get("model_calls_completed"),
            default=0,
        ),
        "model_assisted_planning_packet": model_planning,
        "model_assisted_planning_consumed": bool(model_planning),
        "model_assisted_disambiguation_consumed": bool(
            model_planning and model_disambiguation_required
        ),
        "relation_plan_id": plan.get("plan_id"),
        "component_id": plan.get("component_id"),
        "search_requirement_id": plan.get("search_requirement_id"),
        "source_obligation_id": plan.get("source_obligation_id"),
        "relation_plan_search_query_seed": relation_seed,
        "subject_entity_anchors": subject_anchors,
        "form_document_code_anchors": form_anchors,
        "fact_kind": fact_kind,
        "fact_kind_anchor": fact_anchor,
        "timeframe_currentness_posture": timeframe_posture,
        "source_artifact_expectation": source_artifact_expectation,
        "official_source_of_record_acquisition_intent": True,
        "answer_bearing_anchor_terms": answer_bearing_anchors,
        "expected_value_token_kinds": value_token_kinds,
        "artifact_source_terms": artifact_terms,
        "official_artifact_hypotheses": official_artifact_hypotheses,
        "likely_official_domains": likely_official_domains,
        "acquisition_query": acquisition_query,
        "original_acquisition_query": acquisition_query,
        "deterministic_acquisition_query": deterministic_acquisition_query,
        "query_shaping_reason": (
            "model_assisted_official_artifact_hypotheses_reduced"
            if model_planning
            else "artifact_oriented_source_discovery_from_relation_plan_anchors"
        ),
        "disambiguation_required": ambiguity_required,
        "ambiguity_required": ambiguity_required,
        "disambiguation_reason": ambiguity_reason,
        "ambiguity_status": "required" if ambiguity_required else "clear",
        "disambiguation_query": relation_seed if ambiguity_required else None,
        "scout_query": relation_seed if ambiguity_required else None,
        "extraction_provider": DEFAULT_EXTRACTION_PROVIDER,
        "provider_operation": DEFAULT_OPERATION,
        "max_provider_results": MAX_PROVIDER_RESULTS,
        "max_selected_source_content_candidates": MAX_EVIDENCE_LEDGER_ADMISSIONS,
        "selected_window_guidance": {
            "guidance_kind": "answer_bearing_anchor_and_value_token_expectation",
            "answer_bearing_anchor_terms": answer_bearing_anchors,
            "expected_value_token_kinds": value_token_kinds,
            "existing_selector_consumer": (
                "core.fetch_read_content_reference.select_bounded_answer_bearing_text"
            ),
            "selection_system_parallel_path_created": False,
        },
        "serper_scout_allowed": ambiguity_required,
        "serper_scout_used": False,
        "diagnostics": {
            "safe_diagnostic": True,
            "answer_bearing_anchor_count": len(answer_bearing_anchors),
            "expected_value_token_kinds": value_token_kinds,
            "artifact_source_terms_used": artifact_terms,
            "raw_private_retention": False,
        },
        "closed_surface_flags": {
            "planner_dispatched_provider": False,
            "source_authority_decided": False,
            "evidence_created": False,
            "citation_eligibility_created": False,
            "source_obligation_satisfaction_created": False,
            "answer_text_created": False,
            "dprime_permissiveness_changed": False,
            "multi_component_planning_opened": False,
            "live_fast_model_route_opened": False,
        },
        "source_authority_decided": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
        "correctness_claimed": False,
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    _reject_forbidden_material(payload, context="fast acquisition planner output")
    return _json_safe(payload)


def _planner_ambiguity_posture(plan: Mapping[str, Any]) -> tuple[bool, str]:
    query = (_clean_text(plan.get("sanitized_query"), limit=500) or "").casefold()
    component = (_clean_text(plan.get("component_text"), limit=260) or "").casefold()
    combined = f"{query} {component}"
    vague_markers = (
        " this ",
        " that ",
        " the form",
        " the application",
        " the filing",
        " my ",
        " near me",
        " in my county",
    )
    if any(marker in f" {combined} " for marker in vague_markers):
        return True, "vague_entity_or_form_reference"
    if len(_relation_plan_priority_tokens(plan)) < 2:
        return True, "insufficient_entity_terms_for_source_acquisition"
    return False, "clear_single_relation_query"


def _subject_entity_anchors(query_text: str, component_text: str) -> list[str]:
    text = f"{query_text} {component_text}"
    anchors: list[str] = []
    seen: set[str] = set()
    patterns = (
        r"\b[A-Z][A-Z0-9&.-]{1,}(?:\s+[A-Z][A-Z0-9&.-]{1,})*\b",
        (
            r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s+"
            r"(?:Agency|Authority|Board|Bureau|Commission|County|Department|"
            r"Division|Office|Service)\b"
        ),
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = _clean_text(match.group(0), limit=80)
            if not value or value.casefold() in {"form"}:
                continue
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                anchors.append(value)
    return anchors[:4]


def _form_document_code_anchors(query_text: str, component_text: str) -> list[str]:
    text = f"{query_text} {component_text}"
    anchors: list[str] = []
    seen: set[str] = set()
    patterns = (
        r"\bForm\s+[A-Z]{1,5}-\d+[A-Z]?\b",
        r"\b[A-Z]{1,5}-\d+[A-Z]?\b",
        r"\b\d{4}\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = _clean_text(match.group(0), limit=80)
            if not value:
                continue
            if re.fullmatch(r"\d{4}", value) and not (1900 <= int(value) <= 2100):
                continue
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                anchors.append(value)
    return anchors[:5]


def _fact_kind_anchor(component_text: str, fact_kind: str) -> str:
    lowered = component_text.casefold()
    fact_phrases = {
        "fee": (
            "paper filing fee",
            "filing fee",
            "renewal fee",
            "fee",
        ),
        "current_value": (
            "standard mileage rate",
            "wage base",
            "maximum",
            "limit",
            "rate",
        ),
        "deadline": ("filing deadline", "deadline", "due date"),
        "requirement": ("requirements", "requirement"),
        "status": ("status", "availability"),
    }
    for phrase in fact_phrases.get(fact_kind, (fact_kind,)):
        if phrase in lowered:
            return phrase
    return fact_kind.replace("_", " ")


def _timeframe_currentness_posture(query_text: str, component_text: str) -> str:
    lowered = f"{query_text} {component_text}".casefold()
    if re.search(r"\b(?:19|20)\d{2}\b", lowered):
        return "year_specific_current"
    if any(term in lowered for term in ("current", "currently", "latest", "today", "now")):
        return "current"
    if "official" in lowered:
        return "official_currentness_implied"
    return "currentness_required_by_supported_class"


def _source_artifact_expectation(fact_kind: str) -> str:
    if fact_kind == "fee":
        return "official fee schedule or filing-fee instructions"
    if fact_kind == "deadline":
        return "official deadline schedule or filing instructions"
    if fact_kind == "requirement":
        return "official requirements page or instructions"
    if fact_kind == "status":
        return "official status page or notice"
    return "official rate table, notice, schedule, or source-of-record page"


def _artifact_source_terms(
    *,
    fact_kind: str,
    form_anchors: Sequence[str],
    timeframe_posture: str,
) -> list[str]:
    terms = ["official", "current"]
    if fact_kind == "fee":
        terms.extend(["fee schedule", "filing fees"])
        if form_anchors:
            terms.append("form instructions")
    elif fact_kind == "deadline":
        terms.extend(["deadline", "instructions"])
    elif fact_kind == "requirement":
        terms.extend(["requirements", "instructions"])
    elif fact_kind == "status":
        terms.extend(["status", "notice"])
    else:
        terms.extend(["rate", "notice", "table"])
    if timeframe_posture == "year_specific_current":
        terms.append("effective")
    return _unique_clean_terms(terms, limit=8)


def _answer_bearing_anchor_terms(
    *,
    subject_anchors: Sequence[str],
    form_anchors: Sequence[str],
    fact_anchor: str,
    component_text: str,
    fact_kind: str,
) -> list[str]:
    terms: list[str] = []
    terms.extend(subject_anchors)
    terms.extend(form_anchors)
    if fact_anchor:
        terms.append(fact_anchor)
    lowered = component_text.casefold()
    for phrase in (
        "business use",
        "small claims",
        "paper",
        "filing fee",
        "fee schedule",
        "standard mileage rate",
        "wage base",
    ):
        if phrase in lowered:
            terms.append(phrase)
    if fact_kind == "fee":
        terms.append("fee")
    elif fact_kind == "current_value":
        terms.append("rate")
    return _unique_clean_terms(terms, limit=10)


def _expected_value_token_kinds(fact_kind: str, component_text: str) -> list[str]:
    lowered = component_text.casefold()
    if fact_kind == "fee":
        return ["currency"]
    if "rate" in lowered or "mileage" in lowered:
        return ["currency", "number"]
    if fact_kind == "deadline":
        return ["date_like"]
    if fact_kind == "current_value":
        return ["number"]
    return ["number"]


def _artifact_oriented_acquisition_query(
    *,
    subject_anchors: Sequence[str],
    form_anchors: Sequence[str],
    fact_anchor: str,
    component_text: str,
    artifact_terms: Sequence[str],
    timeframe_posture: str,
    fallback: str,
) -> str:
    parts: list[str] = []
    parts.extend(subject_anchors)
    parts.extend(form_anchors)
    if fact_anchor:
        parts.append(fact_anchor)
    lowered = component_text.casefold()
    for qualifier in ("business use", "small claims", "paper"):
        if qualifier in lowered:
            parts.append(qualifier)
    if timeframe_posture:
        parts.append("current")
    parts.extend(artifact_terms)
    query = " ".join(_unique_clean_terms(parts, limit=14))
    return _clean_text(query or fallback, limit=220) or fallback


def _unique_clean_terms(terms: Sequence[Any], *, limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for term in terms:
        clean = _clean_text(term, limit=120)
        key = clean.casefold() if clean else ""
        if clean and key not in seen:
            seen.add(key)
            out.append(clean)
    return out[:limit]


def _disambiguation_record_from_scout_payload(
    scout_payload: Mapping[str, Any],
    *,
    acquisition_plan: Mapping[str, Any],
) -> dict[str, Any]:
    results = _provider_results(scout_payload)
    observations = []
    for result in results[:MAX_PROVIDER_RESULTS]:
        observations.append(
            {
                "title": _clean_text(result.get("title"), limit=220),
                "url": _clean_text(result.get("url"), limit=700),
                "domain": _clean_domain(result.get("domain")),
                "result_rank": _bounded_int(result.get("result_rank"), default=0),
                "directionality_only": True,
                "not_evidence": True,
                "not_source_custody": True,
                "not_citation_eligible": True,
                "not_source_obligation_satisfaction": True,
            }
        )
    record = {
        "schema_version": "generic_single_relation_disambiguator_record_v1",
        "disambiguator_role": "cheap_scout_directionality",
        "scout_provider": DEFAULT_SCOUT_PROVIDER,
        "scout_query": acquisition_plan.get("disambiguation_query"),
        "scout_result_count": len(observations),
        "observations": observations,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "scout_output_used_as_evidence": False,
        "scout_output_used_as_source_custody": False,
        "scout_output_citation_eligible": False,
        "scout_output_satisfies_source_obligation": False,
        "planner_revision_allowed": True,
    }
    _reject_forbidden_material(record, context="disambiguator scout record")
    return _json_safe(record)


def _revised_acquisition_plan_after_disambiguation(
    acquisition_plan: Mapping[str, Any],
    *,
    disambiguation_record: Mapping[str, Any],
) -> dict[str, Any]:
    revised = dict(acquisition_plan)
    bridge_term = _disambiguation_bridge_term(disambiguation_record)
    if bridge_term:
        revised["acquisition_query"] = _clean_text(
            f"{acquisition_plan.get('original_acquisition_query')} {bridge_term}",
            limit=220,
        )
        revised["planner_revision_source"] = "serper_directionality_bridge_term"
    else:
        revised["planner_revision_source"] = "no_concrete_scout_bridge_term"
    revised["serper_scout_used"] = True
    revised["scout_output_used_as_evidence"] = False
    revised["scout_output_used_as_source_custody"] = False
    revised["scout_output_citation_eligible"] = False
    revised["scout_output_satisfies_source_obligation"] = False
    _reject_forbidden_material(revised, context="revised acquisition planner output")
    return _json_safe(revised)


def _disambiguation_bridge_term(record: Mapping[str, Any]) -> str | None:
    for observation in _safe_sequence(record.get("observations")):
        safe = _safe_mapping(observation)
        title = _clean_text(safe.get("title"), limit=120)
        if title:
            return title
        domain = _clean_domain(safe.get("domain"))
        if domain:
            return domain
    return None


def _candidate_packet_from_provider_results(
    *,
    relation_plan: Mapping[str, Any],
    run_id: str,
    results: Sequence[Mapping[str, Any]],
    provider_calls_attempted: int,
    provider_calls_completed: int,
    search_query_seed: str,
    extraction_provider: str,
) -> dict[str, Any]:
    contract_ref = _contract_ref_from_plan(relation_plan)
    handoff_ref = _handoff_ref_from_plan(relation_plan, contract_ref=contract_ref)
    request_id = f"request:{run_id}"
    validation_ref = {
        "validation_id": f"validation:{run_id}",
        "candidate_count": len(results),
        "relation_plan_id": relation_plan.get("plan_id"),
        "search_query_seed_used": search_query_seed,
        "source_acquisition_provider": extraction_provider,
        "source_acquisition_mode": SOURCE_ACQUISITION_MODE_PROVIDER_EXTRACTED,
        "provider_calls_attempted": provider_calls_attempted,
        "provider_calls_completed": provider_calls_completed,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    records = []
    for result in results:
        if not result.get("url_valid"):
            continue
        url = _required_url(result.get("url"))
        domain = _clean_domain(result.get("domain")) or urlparse(url).netloc.lower()
        rank = _positive_int(result.get("result_rank"), "provider result rank")
        candidate_id, candidate_digest = _provider_result_candidate_identity(
            result,
            relation_plan=relation_plan,
            run_id=run_id,
        )
        records.append(
            SearchResultCandidateRecord(
                run_id=run_id,
                request_id=request_id,
                current_answer_contract_ref=contract_ref,
                search_executor_handoff_ref=handoff_ref,
                search_task_id=str(relation_plan["search_requirement_id"]),
                provider_authorized=extraction_provider,
                provider_used=str(result.get("provider") or extraction_provider),
                provider_call_index=_positive_int(
                    result.get("provider_call_index"),
                    "provider call index",
                ),
                result_rank=rank,
                title=str(result["title"]),
                url=url,
                domain=domain,
                candidate_id=candidate_id,
                candidate_digest=candidate_digest,
                validation_id=str(validation_ref["validation_id"]),
                parent_live_search_validation_ref=validation_ref,
                query_intent_id=f"query-intent:{relation_plan['search_requirement_id']}",
                component_id=str(relation_plan["component_id"]),
                source_obligation_candidate_ids=(
                    str(relation_plan["source_obligation_id"]),
                ),
                snippet=_clean_text(result.get("snippet"), limit=500),
                published_or_observed_date=_clean_text(
                    result.get("published_or_observed_date"),
                    limit=80,
                ),
            ).to_dict()
        )
    packet = SearchResultCandidatePacket(
        run_id=run_id,
        request_id=request_id,
        current_answer_contract_ref=contract_ref,
        search_executor_handoff_ref=handoff_ref,
        candidate_records=records,
        selected_search_task_ids=[str(relation_plan["search_requirement_id"])],
        provider_authorized=extraction_provider,
        provider_used=extraction_provider,
        parent_live_search_validation_ref=validation_ref,
    ).to_dict()
    return validate_search_result_candidate_packet(packet)


def _write_search_artifacts(
    *,
    retained_root: Path,
    provider_payload: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
) -> None:
    search_dir = retained_root / SEARCH_ARTIFACT_DIR
    search_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        search_dir / SANITIZED_PROVIDER_RESULTS_NAME,
        _retained_provider_payload_for_candidate_packet(provider_payload, candidate_packet),
    )
    _write_json(search_dir / SEARCH_CANDIDATE_PACKET_NAME, candidate_packet)
    _write_json(search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME, candidate_packet)


def _retained_provider_payload_for_candidate_packet(
    provider_payload: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_urls = {
        _clean_text(record.get("url"), limit=700)
        for record in _safe_sequence(candidate_packet.get("candidate_records"))
        if isinstance(record, Mapping)
    }
    results = []
    for result in _safe_sequence(provider_payload.get("results")):
        safe = _safe_mapping(result)
        url = _clean_text(safe.get("url"), limit=700)
        if not url or url not in candidate_urls:
            continue
        results.append(
            {
                "title": safe.get("title"),
                "url": url,
                "domain": safe.get("domain"),
                "snippet": safe.get("snippet"),
                "published_or_observed_date": safe.get("published_or_observed_date"),
                "result_rank": safe.get("result_rank"),
                "provider_call_index": safe.get("provider_call_index"),
                "provider_extracted_text_char_count": safe.get(
                    "provider_extracted_text_char_count"
                ),
                "provider_extracted_text_digest": safe.get(
                    "provider_extracted_text_digest"
                ),
                "provider_extracted_source_text_digest": safe.get(
                    "provider_extracted_source_text_digest"
                ),
                "provider_extracted_content_type": safe.get(
                    "provider_extracted_content_type"
                ),
                "provider_extracted_at": safe.get("provider_extracted_at"),
                "raw_provider_payload_retained": False,
                "raw_search_response_retained": False,
            }
        )
    return {
        "request_kind": provider_payload.get("request_kind"),
        "provider": provider_payload.get("provider") or DEFAULT_PROVIDER,
        "operation": provider_payload.get("operation") or DEFAULT_OPERATION,
        "result_count": len(results),
        "results": results,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _write_fetch_read_artifacts(
    *,
    retained_root: Path,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
    provider_results: Sequence[Mapping[str, Any]],
    fetch_read_runner: FetchReadRunner,
    retain_failed_fetch_read_packet: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    search_dir = retained_root / SEARCH_ARTIFACT_DIR
    fetch_dir = retained_root / FETCH_READ_ARTIFACT_DIR
    candidate_packet = validate_search_result_candidate_packet(
        _read_json(search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME)
    )
    candidate_diagnostics = _candidate_diagnostics_from_provider_results(
        provider_results,
        relation_plan=relation_plan,
        run_id=str(candidate_packet["run_id"]),
    )
    candidates = _fetch_candidate_records(candidate_packet, relation_plan=relation_plan)
    if not candidates:
        return None, {
            "source_acquisition_mode": SOURCE_ACQUISITION_MODE_NONE,
            "provider_extracted_content_candidate_count": 0,
            "provider_extracted_content_handoff_created": 0,
            "direct_fetch_read_attempts": 0,
            "fetch_read_attempts": 0,
            "fetch_read_completed": 0,
            "fetch_read_blocker": (
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING
            ),
            "fetch_read_blocker_detail": (
                "no provider result candidate exposed a usable http(s) URL "
                "for bounded fetch/read."
            ),
            "fetch_read_status_classes": (),
            "fetch_read_content_types": (),
            "fetch_read_failure_categories": tuple(
                _candidate_failure_categories(candidate_diagnostics)
            ),
            "fetch_read_candidate_diagnostics": tuple(candidate_diagnostics),
            "fetch_read_attempt_diagnostics": (),
            **_selected_window_guidance_counts(
                acquisition_plan=acquisition_plan,
                selection=None,
                blocked=True,
                blocker="no usable http(s) URL candidate reached selected-window guidance.",
            ),
        }
    provider_results_by_candidate_id = _provider_results_by_candidate_id(
        provider_results,
        relation_plan=relation_plan,
        run_id=str(candidate_packet["run_id"]),
    )
    provider_extracted_candidates = [
        candidate
        for candidate in candidates
        if _provider_extracted_text(
            provider_results_by_candidate_id.get(str(candidate["candidate_id"]), {})
        )
    ]
    if provider_extracted_candidates:
        try:
            evaluations = _provider_extracted_candidate_window_evaluations(
                provider_extracted_candidates,
                provider_results_by_candidate_id=provider_results_by_candidate_id,
                relation_plan=relation_plan,
                acquisition_plan=acquisition_plan,
            )
            selected_evaluation = _select_provider_extracted_candidate_window(
                evaluations
            )
            candidate = selected_evaluation.candidate
            provider_result = selected_evaluation.provider_result
            selection = selected_evaluation.selection
            material = _provider_extracted_fetch_read_material(
                candidate=candidate,
                candidate_packet=candidate_packet,
                provider_result=provider_result,
                selection=selection,
            )
            fetch_packet = validate_fetch_read_content_packet(
                build_fetch_read_content_packet_from_candidate_packet(
                    candidate_packet,
                    [material],
                    selected_candidate_ids=[str(candidate["candidate_id"])],
                )
            )
        except FetchReadContentReferenceError as exc:
            return None, {
                "source_acquisition_mode": SOURCE_ACQUISITION_MODE_PROVIDER_EXTRACTED,
                "provider_extracted_content_candidate_count": len(
                    provider_extracted_candidates
                ),
                "provider_extracted_content_handoff_created": 0,
                "direct_fetch_read_attempts": 0,
                "fetch_read_attempts": 0,
                "fetch_read_completed": 0,
                "fetch_read_blocker": (
                    PROVIDER_EXTRACTED_CONTENT_CUSTODY_ADMISSION_BLOCKED
                ),
                "fetch_read_blocker_detail": str(exc),
                "fetch_read_status_classes": (),
                "fetch_read_content_types": (),
                "fetch_read_failure_categories": tuple(
                    _candidate_failure_categories(candidate_diagnostics)
                ),
                "fetch_read_candidate_diagnostics": tuple(candidate_diagnostics),
                "fetch_read_attempt_diagnostics": (),
                **_selected_window_guidance_counts(
                    acquisition_plan=acquisition_plan,
                    selection=None,
                    blocked=True,
                    blocker=str(exc),
                ),
            }
        fetch_dir.mkdir(parents=True, exist_ok=True)
        _write_json(fetch_dir / FETCH_READ_CONTENT_PACKET_NAME, fetch_packet)
        _write_json(
            fetch_dir / LIVE_SOURCE_SURVIVAL_SUMMARY_NAME,
            _fetch_summary(fetch_packet),
        )
        provider_diagnostic = _provider_extracted_content_diagnostic(
            candidate,
            provider_result=provider_result,
        )
        _apply_candidate_window_diagnostics(
            candidate_diagnostics,
            evaluations=evaluations,
            selected_candidate_id=str(candidate["candidate_id"]),
        )
        _apply_attempt_diagnostic(candidate_diagnostics, provider_diagnostic)
        _mark_unattempted_candidates_skipped_after_success(candidate_diagnostics)
        return fetch_packet, {
            "source_acquisition_mode": SOURCE_ACQUISITION_MODE_PROVIDER_EXTRACTED,
            "provider_extracted_content_candidate_count": len(
                provider_extracted_candidates
            ),
            "provider_extracted_content_handoff_created": 1,
            "direct_fetch_read_attempts": 0,
            "fetch_read_attempts": 0,
            "fetch_read_completed": 1,
            "fetch_read_status_classes": (),
            "fetch_read_content_types": (),
            "fetch_read_failure_categories": tuple(
                _candidate_failure_categories(candidate_diagnostics)
            ),
            "fetch_read_candidate_diagnostics": tuple(candidate_diagnostics),
            "fetch_read_attempt_diagnostics": (),
            "answer_bearing_candidate_window_status": (
                _candidate_window_status(selection)
            ),
            "answer_bearing_candidate_window_best_effort": (
                _candidate_window_status(selection)
                == ANSWER_BEARING_CANDIDATE_WINDOW_BEST_EFFORT
            ),
            "answer_bearing_candidate_window_not_established": (
                _candidate_window_status(selection)
                == ANSWER_BEARING_CANDIDATE_WINDOW_NOT_ESTABLISHED
            ),
            "answer_bearing_candidate_window_diagnostics": (
                _candidate_window_diagnostics(
                    evaluations,
                    selected_candidate_id=str(candidate["candidate_id"]),
                )
            ),
            **_selected_window_guidance_counts(
                acquisition_plan=acquisition_plan,
                selection=selection,
            ),
        }
    fetch_attempts = 0
    last_error: GenericSingleRelationLiveDogfoodRunError | None = None
    attempt_diagnostics: list[dict[str, Any]] = []
    for candidate in candidates:
        if fetch_attempts >= MAX_FETCH_READ_ATTEMPTS:
            _mark_candidate_skipped(
                candidate_diagnostics,
                candidate_id=str(candidate["candidate_id"]),
                skipped_reason=FETCH_READ_CAP_EXHAUSTED,
            )
            continue
        fetch_attempts += 1
        fetch_result: GenericLiveFetchReadResult | None = None
        try:
            fetch_result = fetch_read_runner(str(candidate["url"]))
            _validate_fetch_result(fetch_result, candidate=candidate)
            selection = _bounded_plan_text_selection(
                fetch_result.sanitized_text,
                relation_plan=relation_plan,
                acquisition_plan=acquisition_plan,
            )
            material = _fetch_read_material(
                candidate=candidate,
                candidate_packet=candidate_packet,
                fetch_result=fetch_result,
                selection=selection,
            )
            fetch_packet = validate_fetch_read_content_packet(
                build_fetch_read_content_packet_from_candidate_packet(
                    candidate_packet,
                    [material],
                    selected_candidate_ids=[str(candidate["candidate_id"])],
                )
            )
            fetch_dir.mkdir(parents=True, exist_ok=True)
            _write_json(fetch_dir / FETCH_READ_CONTENT_PACKET_NAME, fetch_packet)
            _write_json(
                fetch_dir / LIVE_SOURCE_SURVIVAL_SUMMARY_NAME,
                _fetch_summary(fetch_packet),
            )
            attempt_diagnostic = _fetch_read_attempt_diagnostic(
                candidate,
                attempt_index=fetch_attempts,
                fetch_result=fetch_result,
                error=None,
                selection=selection,
            )
            attempt_diagnostics.append(attempt_diagnostic)
            _apply_attempt_diagnostic(candidate_diagnostics, attempt_diagnostic)
            _mark_unattempted_candidates_skipped_after_success(candidate_diagnostics)
            return fetch_packet, {
                "source_acquisition_mode": SOURCE_ACQUISITION_MODE_DIRECT_FETCH_FALLBACK,
                "provider_extracted_content_candidate_count": 0,
                "provider_extracted_content_handoff_created": 0,
                "direct_fetch_read_attempts": fetch_attempts,
                "fetch_read_attempts": fetch_attempts,
                "fetch_read_completed": 1,
                "fetch_read_status_classes": tuple(
                    _attempt_status_classes(attempt_diagnostics)
                ),
                "fetch_read_content_types": tuple(
                    _attempt_content_types(attempt_diagnostics)
                ),
                "fetch_read_failure_categories": tuple(
                    _candidate_failure_categories(candidate_diagnostics)
                    + _attempt_failure_categories(attempt_diagnostics)
                ),
                "answer_bearing_candidate_window_status": (
                    _candidate_window_status(selection)
                ),
                "answer_bearing_candidate_window_best_effort": (
                    _candidate_window_status(selection)
                    == ANSWER_BEARING_CANDIDATE_WINDOW_BEST_EFFORT
                ),
                "answer_bearing_candidate_window_not_established": (
                    _candidate_window_status(selection)
                    == ANSWER_BEARING_CANDIDATE_WINDOW_NOT_ESTABLISHED
                ),
                "answer_bearing_candidate_window_diagnostics": (
                    _candidate_window_diagnostics_from_attempt_diagnostics(
                        attempt_diagnostics
                    )
                ),
                "fetch_read_candidate_diagnostics": tuple(candidate_diagnostics),
                "fetch_read_attempt_diagnostics": tuple(attempt_diagnostics),
                **_selected_window_guidance_counts(
                    acquisition_plan=acquisition_plan,
                    selection=selection,
                ),
            }
        except GenericSingleRelationLiveDogfoodRunError as exc:
            last_error = exc
            attempt_diagnostic = _fetch_read_attempt_diagnostic(
                candidate,
                attempt_index=fetch_attempts,
                fetch_result=fetch_result,
                error=exc,
            )
            attempt_diagnostics.append(attempt_diagnostic)
            _apply_attempt_diagnostic(candidate_diagnostics, attempt_diagnostic)
            continue
    if last_error is None:
        last_error = GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "no provider candidate was available for bounded fetch/read.",
        )
    blocker, detail = _fetch_read_blocker_from_attempt_diagnostics(
        attempt_diagnostics,
        last_error=last_error,
    )
    failed_fetch_packet: dict[str, Any] | None = None
    if retain_failed_fetch_read_packet:
        failed_materials = _failed_fetch_read_materials(
            candidate_packet=candidate_packet,
            candidates=candidates,
            attempt_diagnostics=attempt_diagnostics,
        )
        if failed_materials:
            try:
                failed_fetch_packet = validate_fetch_read_content_packet(
                    build_fetch_read_content_packet_from_candidate_packet(
                        candidate_packet,
                        failed_materials,
                        selected_candidate_ids=[
                            str(item["candidate_id"]) for item in failed_materials
                        ],
                    )
                )
                fetch_dir.mkdir(parents=True, exist_ok=True)
                _write_json(
                    fetch_dir / FETCH_READ_CONTENT_PACKET_NAME,
                    failed_fetch_packet,
                )
                _write_json(
                    fetch_dir / LIVE_SOURCE_SURVIVAL_SUMMARY_NAME,
                    _fetch_summary(failed_fetch_packet),
                )
            except FetchReadContentReferenceError:
                failed_fetch_packet = None
    return failed_fetch_packet, {
        "source_acquisition_mode": SOURCE_ACQUISITION_MODE_DIRECT_FETCH_FALLBACK,
        "provider_extracted_content_candidate_count": 0,
        "provider_extracted_content_handoff_created": 0,
        "direct_fetch_read_attempts": fetch_attempts,
        "fetch_read_attempts": fetch_attempts,
        "fetch_read_completed": 0,
        "fetch_read_blocker": blocker,
        "fetch_read_blocker_detail": detail,
        "fetch_read_status_classes": tuple(
            _attempt_status_classes(attempt_diagnostics)
        ),
        "fetch_read_content_types": tuple(_attempt_content_types(attempt_diagnostics)),
        "fetch_read_failure_categories": tuple(
            _candidate_failure_categories(candidate_diagnostics)
            + _attempt_failure_categories(attempt_diagnostics)
        ),
        "fetch_read_candidate_diagnostics": tuple(candidate_diagnostics),
        "fetch_read_attempt_diagnostics": tuple(attempt_diagnostics),
        **_selected_window_guidance_counts(
            acquisition_plan=acquisition_plan,
            selection=None,
            blocked=True,
            blocker=detail,
        ),
    }


def _fetch_candidate_records(
    candidate_packet: Mapping[str, Any],
    *,
    relation_plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    records = [
        _safe_mapping(item)
        for item in candidate_packet.get("candidate_records", [])
        if isinstance(item, Mapping)
    ]
    priorities = _fetch_read_candidate_priorities(records, relation_plan=relation_plan)
    enriched = []
    for record in records:
        candidate_id = _clean_text(record.get("candidate_id"), limit=320)
        priority = priorities.get(candidate_id or "")
        item = dict(record)
        if priority:
            item["fetch_read_priority_rank"] = priority["fetch_read_priority_rank"]
            item["candidate_selection_features"] = priority[
                "candidate_selection_features"
            ]
        enriched.append(item)
    return sorted(
        enriched,
        key=lambda item: (
            _bounded_int(item.get("fetch_read_priority_rank"), default=999),
            _bounded_int(item.get("result_rank"), default=999),
        ),
    )


def _fetch_read_candidate_priorities(
    candidates: Sequence[Mapping[str, Any]],
    *,
    relation_plan: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    ranked: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        safe = _safe_mapping(candidate)
        candidate_id = _clean_text(safe.get("candidate_id"), limit=320)
        if not candidate_id:
            continue
        features = _candidate_selection_features(safe, relation_plan=relation_plan)
        ranked.append(
            (
                _candidate_priority_bucket(safe, features),
                _bounded_int(safe.get("result_rank"), default=999),
                index,
                candidate_id,
                features,
            )
        )
    priorities: dict[str, dict[str, Any]] = {}
    for priority_rank, (_bucket, _provider_rank, _index, candidate_id, features) in (
        enumerate(sorted(ranked), 1)
    ):
        final_features = {
            **features,
            "final_fetch_read_priority_rank": priority_rank,
        }
        priorities[candidate_id] = {
            "fetch_read_priority_rank": priority_rank,
            "candidate_selection_features": final_features,
        }
    return priorities


def _candidate_priority_bucket(
    candidate: Mapping[str, Any],
    features: Mapping[str, Any],
) -> int:
    if not _is_valid_http_url(candidate.get("url")):
        return 6
    agency_or_record_match = (
        features.get("source_of_record_domain_signal") is True
        or (
            features.get("query_entity_domain_overlap") is True
            and features.get("derivative_domain_signal") is False
        )
    )
    if agency_or_record_match:
        return 2 if _official_artifact_feature_signal(features) else 1
    if (
        features.get("official_domain_signal") is True
        or features.get("public_agency_domain_signal") is True
    ):
        return 3
    return 4


def _candidate_selection_features(
    candidate: Mapping[str, Any],
    *,
    relation_plan: Mapping[str, Any],
) -> dict[str, Any]:
    title = _clean_text(candidate.get("title"), limit=220) or ""
    url = _clean_text(candidate.get("url"), limit=700) or ""
    domain = _clean_domain(candidate.get("domain")) or (
        urlparse(url).netloc.lower() if url else ""
    )
    relation_tokens = _relation_plan_priority_tokens(relation_plan)
    domain_tokens = _priority_tokens(domain)
    title_path_tokens = _priority_tokens(
        " ".join((title, urlparse(url).path if url else ""))
    )
    query_entity_domain_overlap = bool(relation_tokens & domain_tokens)
    title_or_path_token_overlap = bool(relation_tokens & title_path_tokens)
    public_agency_domain_signal = _public_agency_domain_signal(domain)
    official_domain_signal = public_agency_domain_signal or "official" in domain_tokens
    source_of_record_domain_signal = (
        query_entity_domain_overlap
        and (official_domain_signal or public_agency_domain_signal)
    )
    derivative_domain_signal = _derivative_domain_signal(
        domain=domain,
        domain_tokens=domain_tokens,
        title_path_tokens=title_path_tokens,
        official_domain_signal=official_domain_signal,
        query_entity_domain_overlap=query_entity_domain_overlap,
    )
    return {
        "feature_posture": "discovery_metadata_only",
        "official_domain_signal": official_domain_signal,
        "source_of_record_domain_signal": source_of_record_domain_signal,
        "query_entity_domain_overlap": query_entity_domain_overlap,
        "title_or_path_token_overlap": title_or_path_token_overlap,
        "public_agency_domain_signal": public_agency_domain_signal,
        "derivative_domain_signal": derivative_domain_signal,
        "pdf_url_or_title_signal": _pdf_url_or_title_signal(title=title, url=url),
        "table_url_or_title_signal": _table_url_or_title_signal(title=title, url=url),
        "provider_rank": _bounded_int(candidate.get("result_rank"), default=0),
        "final_fetch_read_priority_rank": 0,
        "features_used_as_evidence": False,
        "features_create_source_authority": False,
        "features_satisfy_source_obligation": False,
        "features_make_candidate_citation_eligible": False,
        "features_claim_correctness": False,
    }


def _relation_plan_priority_tokens(relation_plan: Mapping[str, Any]) -> set[str]:
    parts: list[str] = []
    for key in (
        "component_text",
        "source_obligation_text",
        "search_requirement_text",
        "claim_under_test",
    ):
        text = _clean_text(relation_plan.get(key), limit=500)
        if text:
            parts.append(text)
    parts.extend(
        str(item)
        for item in _safe_sequence(relation_plan.get("search_query_seeds"))
        if _clean_text(item, limit=220)
    )
    return _priority_tokens(" ".join(parts))


def _priority_tokens(value: str) -> set[str]:
    text = str(value or "").casefold()
    compact = re.sub(r"(?<=[a-z0-9])[-_/](?=[a-z0-9])", "", text)
    tokens = set(re.findall(r"[a-z0-9]+", text))
    tokens.update(re.findall(r"[a-z0-9]+", compact))
    return {
        token
        for token in tokens
        if len(token) >= 3 and token not in _CANDIDATE_PRIORITY_STOPWORDS
    }


def _public_agency_domain_signal(domain: str | None) -> bool:
    clean = (domain or "").casefold().strip(".")
    return clean.endswith(".gov") or ".gov." in clean or clean.endswith(".mil")


def _derivative_domain_signal(
    *,
    domain: str,
    domain_tokens: set[str],
    title_path_tokens: set[str],
    official_domain_signal: bool,
    query_entity_domain_overlap: bool,
) -> bool:
    if official_domain_signal:
        return False
    if domain.casefold().endswith(".org") and not query_entity_domain_overlap:
        return True
    tokens = domain_tokens | title_path_tokens
    return bool(tokens & _CANDIDATE_DERIVATIVE_MARKERS)


def _pdf_url_or_title_signal(*, title: str, url: str) -> bool:
    lowered = f"{title} {urlparse(url).path if url else ''}".casefold()
    return lowered.endswith(".pdf") or ".pdf" in lowered or " pdf" in lowered


def _table_url_or_title_signal(*, title: str, url: str) -> bool:
    lowered = f"{title} {urlparse(url).path if url else ''}".casefold()
    return any(
        marker in lowered
        for marker in (
            ".csv",
            ".tsv",
            ".xls",
            ".xlsx",
            " table",
            " schedule",
            " fee-schedule",
            " fee_schedule",
        )
    )


def _official_artifact_feature_signal(features: Mapping[str, Any]) -> bool:
    return bool(
        features.get("pdf_url_or_title_signal") is True
        or features.get("table_url_or_title_signal") is True
    )


def _official_artifact_type_from_signals(
    *,
    features: Mapping[str, Any] | None = None,
    content_type: str | None = None,
    title: str | None = None,
    url: str | None = None,
) -> str | None:
    safe_features = _safe_mapping(features)
    normalized_content_type = _content_type_or_unknown(content_type)
    pdf_signal = bool(
        safe_features.get("pdf_url_or_title_signal") is True
        or normalized_content_type == "application/pdf"
        or _pdf_url_or_title_signal(title=title or "", url=url or "")
    )
    table_signal = bool(
        safe_features.get("table_url_or_title_signal") is True
        or normalized_content_type
        in {
            "text/csv",
            "text/tab-separated-values",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        or _table_url_or_title_signal(title=title or "", url=url or "")
    )
    if pdf_signal and table_signal:
        return "pdf_table_artifact"
    if pdf_signal:
        return "pdf_artifact"
    if table_signal:
        return "table_artifact"
    return None


def _candidate_diagnostics_from_provider_results(
    provider_results: Sequence[Mapping[str, Any]],
    *,
    relation_plan: Mapping[str, Any],
    run_id: str,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    sorted_results = sorted(
        (_safe_mapping(item) for item in provider_results if isinstance(item, Mapping)),
        key=lambda item: _bounded_int(item.get("result_rank"), default=999),
    )
    priority_inputs: list[dict[str, Any]] = []
    for result in sorted_results:
        candidate_id, _candidate_digest = _provider_result_candidate_identity(
            result,
            relation_plan=relation_plan,
            run_id=run_id,
        )
        priority_inputs.append({**result, "candidate_id": candidate_id})
    priorities = _fetch_read_candidate_priorities(
        priority_inputs,
        relation_plan=relation_plan,
    )
    for result in sorted_results:
        candidate_id, _candidate_digest = _provider_result_candidate_identity(
            result,
            relation_plan=relation_plan,
            run_id=run_id,
        )
        priority = priorities.get(candidate_id, {})
        priority_rank = _bounded_int(priority.get("fetch_read_priority_rank"))
        selection_features = _safe_mapping(priority.get("candidate_selection_features"))
        official_or_source_survival_signal = _official_source_survival_features(
            selection_features
        )
        official_artifact_type = _official_artifact_type_from_signals(
            features=selection_features,
            content_type=result.get("provider_extracted_content_type"),
            title=_clean_text(result.get("title"), limit=220),
            url=_clean_text(result.get("url"), limit=700),
        )
        url = _clean_text(result.get("url"), limit=700)
        url_source = _clean_text(result.get("url_source"), limit=20) or "missing"
        url_valid = _is_valid_http_url(url)
        provider_extracted_text_obtained = bool(_provider_extracted_text(result))
        selected_for_fetch_read = (
            url_valid
            and not provider_extracted_text_obtained
            and 0 < priority_rank <= MAX_FETCH_READ_ATTEMPTS
        )
        skipped_reason = None
        failure_category = None
        if url_valid and not selected_for_fetch_read:
            skipped_reason = FETCH_READ_CAP_EXHAUSTED
        if not url_valid:
            skipped_reason = (
                FETCH_READ_FAILURE_MISSING_URL
                if url_source == "missing" or not url
                else FETCH_READ_FAILURE_INVALID_URL
            )
            failure_category = skipped_reason
        diagnostics.append(
            {
                "candidate_id": candidate_id,
                "provider_call_index": _bounded_int(
                    result.get("provider_call_index"),
                    default=1,
                ),
                "provider_rank": _bounded_int(result.get("result_rank"), default=0),
                "result_rank": _bounded_int(result.get("result_rank"), default=0),
                "fetch_read_priority_rank": priority_rank,
                "candidate_selection_policy_id": (
                    FETCH_READ_CANDIDATE_SELECTION_POLICY_ID
                ),
                "candidate_selection_policy_scope": (
                    FETCH_READ_CANDIDATE_SELECTION_SCOPE
                ),
                "candidate_selection_is_acquisition_only": True,
                "candidate_selection_created_source_authority": False,
                "candidate_selection_satisfies_source_obligation": False,
                "candidate_selection_citation_eligible": False,
                "candidate_selection_claims_correctness": False,
                "candidate_selection_features": selection_features,
                "source_survival_scope": "ordinary_public_web_fetch_read_hygiene",
                "source_survival_candidate_signal": (
                    _source_survival_candidate_signal(selection_features)
                ),
                "official_or_source_record_looking_http_candidate": (
                    official_or_source_survival_signal
                ),
                "official_pdf_or_table_artifact_candidate": bool(
                    official_or_source_survival_signal and official_artifact_type
                ),
                "official_artifact_type": official_artifact_type,
                "official_artifact_read_support_status": None,
                "official_artifact_read_support_source": None,
                "official_artifact_read_support_raw_content_retained": False,
                "provider_snippet_used_as_extracted_source_text": False,
                "source_survival_diagnostic_only": True,
                "source_survival_diagnostic_creates_source_authority": False,
                "source_survival_diagnostic_satisfies_source_obligation": False,
                "source_survival_diagnostic_citation_eligible": False,
                "selected_for_fetch_read": selected_for_fetch_read,
                "provider_extracted_text_obtained": provider_extracted_text_obtained,
                "provider_extracted_text_char_count": _bounded_int(
                    result.get("provider_extracted_text_char_count"),
                    default=len(_provider_extracted_text(result) or ""),
                ),
                "provider_extracted_source_text_digest": (
                    _provider_extracted_source_text_digest(result)
                ),
                "provider_extracted_source_content_can_feed_custody": (
                    provider_extracted_text_obtained
                ),
                "provider_extracted_content_creates_source_authority": False,
                "provider_extracted_content_satisfies_source_obligation": False,
                "provider_extracted_content_citation_eligible": False,
                "provider_extracted_content_claims_correctness": False,
                "attempted": False,
                "skipped_reason": skipped_reason,
                "title": _clean_text(result.get("title"), limit=220),
                "domain": _clean_domain(result.get("domain"))
                or (urlparse(url).netloc.lower() if url else None),
                "url": url,
                "url_source": url_source,
                "url_valid": url_valid,
                "http_status_class": FETCH_READ_UNKNOWN,
                "content_type": FETCH_READ_UNKNOWN,
                "readable_content_type": FETCH_READ_UNKNOWN,
                "readable_text_obtained": False,
                "final_url": None,
                "final_domain": None,
                "http_status_code": None,
                "redirect_count": 0,
                "redirect_chain_digest": None,
                "failure_category": failure_category,
                "diagnostic_posture": "observability_only",
                "not_evidence": True,
                "not_citation_eligible": True,
                "not_source_obligation_satisfaction": True,
                "provider_snippet_used_as_evidence": False,
                "candidate_diagnostic_satisfies_source_obligation": False,
                "fetch_read_failure_metadata_citation_eligible": False,
                "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
            }
        )
    return diagnostics


def _provider_result_candidate_identity(
    result: Mapping[str, Any],
    *,
    relation_plan: Mapping[str, Any],
    run_id: str,
) -> tuple[str, str]:
    rank = _positive_int(result.get("result_rank"), "provider result rank")
    candidate_digest = _digest_json(
        {
            "phase": PHASE_NAME,
            "run_id": run_id,
            "relation_plan_id": relation_plan.get("plan_id"),
            "url": _clean_text(result.get("url"), limit=700),
            "rank": rank,
            "component_id": relation_plan.get("component_id"),
            "source_obligation_id": relation_plan.get("source_obligation_id"),
        }
    )
    return (
        "search-result-candidate:" f"{_clean_run_id(run_id)}:{candidate_digest[:20]}",
        candidate_digest,
    )


def _fetch_read_attempt_diagnostic(
    candidate: Mapping[str, Any],
    *,
    attempt_index: int,
    fetch_result: GenericLiveFetchReadResult | None,
    error: GenericSingleRelationLiveDogfoodRunError | None,
    selection: BoundedTextSelection | None = None,
) -> dict[str, Any]:
    attempted_url = _clean_text(
        fetch_result.attempted_url if fetch_result else candidate.get("url"),
        limit=700,
    )
    status_class = _attempt_status_class(fetch_result=fetch_result, error=error)
    content_type = _attempt_content_type(fetch_result=fetch_result, error=error)
    readable_content_type = _attempt_readable_content_type(
        content_type=content_type,
        error=error,
    )
    readable_text_obtained = bool(
        fetch_result is not None and fetch_result.sanitized_text and error is None
    )
    failure_category = (
        None
        if readable_text_obtained
        else _attempt_failure_category(
            status_class=status_class,
            readable_content_type=readable_content_type,
            error=error,
        )
    )
    final_url = _attempt_final_url(
        attempted_url=attempted_url,
        fetch_result=fetch_result,
        error=error,
    )
    selection_features = _safe_mapping(candidate.get("candidate_selection_features"))
    artifact_payload = _official_artifact_diagnostic_payload(
        candidate=candidate,
        content_type=content_type,
        readable_text_obtained=readable_text_obtained,
        support_source=(
            _clean_text(
                fetch_result.official_artifact_read_support_source
                if fetch_result is not None
                else None,
                limit=120,
            )
            or OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_FETCH_RUNNER
        ),
    )
    window_payload = (
        _selected_fetch_read_window_diagnostic_payload(
            selection,
            content_type=content_type,
        )
        if selection is not None
        else {}
    )
    return {
        "candidate_id": _clean_text(candidate.get("candidate_id"), limit=320),
        "attempt_index": attempt_index,
        "attempted_url": attempted_url,
        "attempted_domain": _clean_domain(candidate.get("domain"))
        or (urlparse(attempted_url).netloc.lower() if attempted_url else None),
        "final_url": final_url,
        "final_domain": urlparse(final_url or "").netloc.lower() if final_url else None,
        "http_status_code": _attempt_status_code(
            fetch_result=fetch_result,
            error=error,
        ),
        "redirect_count": _attempt_redirect_count(
            fetch_result=fetch_result,
            error=error,
        ),
        "redirect_chain_digest": _attempt_redirect_chain_digest(
            fetch_result=fetch_result,
            error=error,
        ),
        "provider_rank": _bounded_int(candidate.get("result_rank"), default=0),
        "result_rank": _bounded_int(candidate.get("result_rank"), default=0),
        "fetch_read_priority_rank": _bounded_int(
            candidate.get("fetch_read_priority_rank"),
            default=0,
        ),
        "fetch_read_request_profile_id": FETCH_READ_PUBLIC_WEB_REQUEST_PROFILE_ID,
        "fetch_read_request_posture": FETCH_READ_PUBLIC_WEB_REQUEST_POSTURE,
        "candidate_selection_policy_id": FETCH_READ_CANDIDATE_SELECTION_POLICY_ID,
        "candidate_selection_policy_scope": FETCH_READ_CANDIDATE_SELECTION_SCOPE,
        "candidate_selection_is_acquisition_only": True,
        "candidate_selection_created_source_authority": False,
        "candidate_selection_satisfies_source_obligation": False,
        "candidate_selection_citation_eligible": False,
        "candidate_selection_claims_correctness": False,
        "candidate_selection_features": selection_features,
        "source_survival_scope": "ordinary_public_web_fetch_read_hygiene",
        "source_survival_candidate_signal": (
            _source_survival_candidate_signal(selection_features)
        ),
        "official_or_source_record_looking_http_candidate": (
            _official_source_survival_features(selection_features)
        ),
        **artifact_payload,
        "source_survival_diagnostic_only": True,
        "source_survival_diagnostic_creates_source_authority": False,
        "source_survival_diagnostic_satisfies_source_obligation": False,
        "source_survival_diagnostic_citation_eligible": False,
        "http_status_class": status_class,
        "content_type": content_type,
        "readable_content_type": readable_content_type,
        "readable_text_obtained": readable_text_obtained,
        **window_payload,
        "failure_category": failure_category,
        "diagnostic_posture": "observability_only",
        "not_evidence": True,
        "not_citation_eligible": True,
        "not_source_obligation_satisfaction": True,
        "candidate_diagnostics_satisfy_source_obligations": False,
        "fetch_read_failure_metadata_citation_eligible": False,
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
    }


def _selected_fetch_read_window_diagnostic_payload(
    selection: BoundedTextSelection,
    *,
    content_type: str,
) -> dict[str, Any]:
    return {
        "answer_bearing_candidate_window_considered": True,
        "answer_bearing_candidate_window_selected": True,
        "answer_bearing_candidate_window_status": _candidate_window_status(selection),
        "selected_window_digest": selection.bounded_text_digest,
        "selected_window_char_count": selection.bounded_text_char_count,
        "bounded_content_digest": selection.bounded_text_digest,
        "bounded_content_char_count": selection.bounded_text_char_count,
        "required_anchor_count": selection.required_anchor_count,
        "matched_anchor_count": selection.matched_anchor_count,
        "missing_anchor_count": len(selection.missing_anchors),
        "anchor_match_status": _anchor_match_status(selection),
        "expected_value_token_kinds": list(selection.expected_value_token_kinds),
        "matched_value_token_kinds": list(selection.matched_value_token_kinds),
        "matched_value_token_kind_count": selection.matched_value_token_kind_count,
        "missing_value_token_kinds": list(selection.missing_value_token_kinds),
        "value_token_guidance_consumed": selection.value_token_guidance_consumed,
        "bounded_window_source": (
            "official_artifact_read_support"
            if content_type in OFFICIAL_ARTIFACT_READ_SUPPORT_CONTENT_TYPES
            else "ordinary_fetch_read_sanitized_text"
        ),
        "window_text_retained_in_diagnostic": False,
        "not_evidence": True,
        "not_semantic_support": True,
        "not_source_authority": True,
        "not_citation_eligible": True,
        "not_source_obligation_satisfaction": True,
        "not_product_correctness": True,
    }


def _apply_attempt_diagnostic(
    candidate_diagnostics: list[dict[str, Any]],
    attempt_diagnostic: Mapping[str, Any],
) -> None:
    candidate_id = _clean_text(attempt_diagnostic.get("candidate_id"), limit=320)
    for diagnostic in candidate_diagnostics:
        if diagnostic.get("candidate_id") != candidate_id:
            continue
        provider_extracted = attempt_diagnostic.get("content_acquisition_mode") == (
            SOURCE_ACQUISITION_MODE_PROVIDER_EXTRACTED
        )
        diagnostic["selected_for_fetch_read"] = not provider_extracted
        diagnostic["provider_extracted_content_selected"] = provider_extracted
        diagnostic["content_acquisition_mode"] = attempt_diagnostic.get(
            "content_acquisition_mode"
        )
        diagnostic["content_acquisition_provider"] = attempt_diagnostic.get(
            "content_acquisition_provider"
        )
        diagnostic["provider_extracted_source_content"] = attempt_diagnostic.get(
            "provider_extracted_source_content"
        )
        diagnostic["attempted"] = True
        diagnostic["skipped_reason"] = None
        diagnostic["http_status_class"] = attempt_diagnostic.get("http_status_class")
        diagnostic["content_type"] = attempt_diagnostic.get("content_type")
        diagnostic["readable_content_type"] = attempt_diagnostic.get(
            "readable_content_type"
        )
        diagnostic["readable_text_obtained"] = attempt_diagnostic.get(
            "readable_text_obtained"
        )
        diagnostic["final_url"] = attempt_diagnostic.get("final_url")
        diagnostic["final_domain"] = attempt_diagnostic.get("final_domain")
        diagnostic["http_status_code"] = attempt_diagnostic.get("http_status_code")
        diagnostic["redirect_count"] = attempt_diagnostic.get("redirect_count")
        diagnostic["redirect_chain_digest"] = attempt_diagnostic.get(
            "redirect_chain_digest"
        )
        diagnostic["failure_category"] = attempt_diagnostic.get("failure_category")
        for key in (
            "official_pdf_or_table_artifact_candidate",
            "official_artifact_type",
            "official_artifact_read_support_status",
            "official_artifact_read_support_source",
            "official_artifact_read_support_raw_content_retained",
            "official_artifact_read_support_creates_source_authority",
            "official_artifact_read_support_satisfies_source_obligation",
            "official_artifact_read_support_citation_eligible",
            "official_artifact_read_support_claims_correctness",
            "pdf_parsing_opened",
            "ocr_opened",
            "browser_automation_opened",
            "heavy_document_parser_dependency_added",
            "answer_bearing_candidate_window_considered",
            "answer_bearing_candidate_window_selected",
            "answer_bearing_candidate_window_status",
            "selected_window_digest",
            "selected_window_char_count",
            "bounded_content_digest",
            "bounded_content_char_count",
            "required_anchor_count",
            "matched_anchor_count",
            "missing_anchor_count",
            "anchor_match_status",
            "expected_value_token_kinds",
            "matched_value_token_kinds",
            "matched_value_token_kind_count",
            "missing_value_token_kinds",
            "value_token_guidance_consumed",
            "bounded_window_source",
            "window_text_retained_in_diagnostic",
            "not_semantic_support",
            "not_source_authority",
            "not_product_correctness",
        ):
            if key in attempt_diagnostic:
                diagnostic[key] = attempt_diagnostic.get(key)
        return


def _mark_candidate_skipped(
    candidate_diagnostics: list[dict[str, Any]],
    *,
    candidate_id: str,
    skipped_reason: str,
) -> None:
    for diagnostic in candidate_diagnostics:
        if diagnostic.get("candidate_id") == candidate_id and not diagnostic.get(
            "attempted"
        ):
            diagnostic["selected_for_fetch_read"] = False
            diagnostic["skipped_reason"] = skipped_reason
            return


def _mark_unattempted_candidates_skipped_after_success(
    candidate_diagnostics: list[dict[str, Any]],
) -> None:
    for diagnostic in candidate_diagnostics:
        if diagnostic.get("selected_for_fetch_read") and not diagnostic.get(
            "attempted"
        ):
            diagnostic["skipped_reason"] = FETCH_READ_STOPPED_AFTER_SUCCESS


def _fetch_read_blocker_from_attempt_diagnostics(
    attempt_diagnostics: Sequence[Mapping[str, Any]],
    *,
    last_error: GenericSingleRelationLiveDogfoodRunError,
) -> tuple[str, str]:
    attempts = [_safe_mapping(item) for item in attempt_diagnostics]
    if attempts and all(
        item.get("failure_category") == FETCH_READ_FAILURE_HTTP_4XX
        for item in attempts
    ):
        if all(_official_source_survival_attempt(item) for item in attempts):
            return (
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX,
                (
                    "all selected official/source-of-record-looking public-web "
                    "fetch/read attempts returned HTTP 4xx; no readable source "
                    "survived under the existing fetch/read cap. See sanitized "
                    "fetch_read_attempt_diagnostics for provider rank, "
                    "fetch/read priority, final URL, status class, and content type."
                ),
            )
        return (
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX,
            "all bounded fetch/read candidate attempts failed with HTTP 4xx status class.",
        )
    if attempts and all(
        item.get("failure_category") == FETCH_READ_FAILURE_UNKNOWN
        and item.get("http_status_class") == FETCH_READ_UNKNOWN
        and item.get("content_type") == FETCH_READ_UNKNOWN
        for item in attempts
    ):
        return (
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT,
            (
                "bounded fetch/read attempts failed without sanitized status, "
                "content-type, or failure-category observability."
            ),
        )
    if attempts:
        return (
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES,
            (
                "bounded fetch/read attempted candidates but no readable text "
                "was retained; see sanitized fetch_read_attempt_diagnostics."
            ),
        )
    return last_error.blocker, last_error.detail


def _attempt_status_class(
    *,
    fetch_result: GenericLiveFetchReadResult | None,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> str:
    if error is not None:
        return (
            _normalized_status_class(error.fetch_status_class)
            or FETCH_READ_UNKNOWN
        )
    if fetch_result is None:
        return FETCH_READ_UNKNOWN
    return (
        _normalized_status_class(fetch_result.status_class)
        or _status_class(fetch_result.status_code)
        or FETCH_READ_UNKNOWN
    )


def _attempt_status_code(
    *,
    fetch_result: GenericLiveFetchReadResult | None,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> int | None:
    if error is not None:
        status = _bounded_int(error.fetch_status_code)
        return status if 100 <= status <= 599 else None
    if fetch_result is None:
        return None
    status = _bounded_int(fetch_result.status_code)
    return status if 100 <= status <= 599 else None


def _attempt_final_url(
    *,
    attempted_url: str | None,
    fetch_result: GenericLiveFetchReadResult | None,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> str | None:
    if fetch_result is not None:
        return _clean_text(fetch_result.final_url, limit=700)
    if error is not None:
        return _clean_text(error.fetch_final_url, limit=700) or attempted_url
    return attempted_url


def _attempt_redirect_count(
    *,
    fetch_result: GenericLiveFetchReadResult | None,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> int:
    if error is not None:
        return _bounded_int(error.fetch_redirect_count)
    if fetch_result is None:
        return 0
    return _bounded_int(fetch_result.redirect_count)


def _attempt_redirect_chain_digest(
    *,
    fetch_result: GenericLiveFetchReadResult | None,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> str | None:
    if error is not None:
        return _clean_text(error.fetch_redirect_chain_digest, limit=120)
    if fetch_result is None:
        return None
    return _clean_text(fetch_result.redirect_chain_digest, limit=120)


def _attempt_content_type(
    *,
    fetch_result: GenericLiveFetchReadResult | None,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> str:
    if error is not None:
        return _content_type_or_unknown(error.fetch_content_type)
    if fetch_result is None:
        return FETCH_READ_UNKNOWN
    return _content_type_or_unknown(fetch_result.content_type)


def _attempt_readable_content_type(
    *,
    content_type: str,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> bool | str:
    if error is not None and error.fetch_readable_content_type is not None:
        value = error.fetch_readable_content_type
        return value if value in {True, False, FETCH_READ_UNKNOWN} else FETCH_READ_UNKNOWN
    return _readable_content_type_value(content_type)


def _attempt_failure_category(
    *,
    status_class: str,
    readable_content_type: bool | str,
    error: GenericSingleRelationLiveDogfoodRunError | None,
) -> str:
    if error is not None and error.fetch_failure_category:
        return _fetch_read_failure_category(error.fetch_failure_category)
    status_failure = _failure_category_for_status_class(status_class)
    if status_failure != FETCH_READ_FAILURE_UNKNOWN:
        return status_failure
    if readable_content_type is False:
        return FETCH_READ_FAILURE_UNSUPPORTED_CONTENT_TYPE
    if error is not None:
        return FETCH_READ_FAILURE_EXCEPTION
    return FETCH_READ_FAILURE_NO_READABLE_TEXT


def _official_source_survival_features(features: Mapping[str, Any]) -> bool:
    return any(
        features.get(key) is True
        for key in (
            "source_of_record_domain_signal",
            "official_domain_signal",
            "public_agency_domain_signal",
        )
    )


def _source_survival_candidate_signal(features: Mapping[str, Any]) -> str:
    if features.get("source_of_record_domain_signal") is True:
        return "source_of_record_looking"
    if (
        features.get("official_domain_signal") is True
        or features.get("public_agency_domain_signal") is True
    ):
        return "official_looking"
    return "ordinary_public_web"


def _official_source_survival_attempt(attempt: Mapping[str, Any]) -> bool:
    if attempt.get("official_or_source_record_looking_http_candidate") is True:
        return True
    return _official_source_survival_features(
        _safe_mapping(attempt.get("candidate_selection_features"))
    )


def _attempt_status_classes(
    attempt_diagnostics: Sequence[Mapping[str, Any]],
) -> list[str]:
    return [
        _normalized_status_class(_safe_mapping(item).get("http_status_class"))
        or FETCH_READ_UNKNOWN
        for item in attempt_diagnostics
    ]


def _attempt_content_types(
    attempt_diagnostics: Sequence[Mapping[str, Any]],
) -> list[str]:
    return [
        _content_type_or_unknown(_safe_mapping(item).get("content_type"))
        for item in attempt_diagnostics
    ]


def _attempt_failure_categories(
    attempt_diagnostics: Sequence[Mapping[str, Any]],
) -> list[str]:
    categories: list[str] = []
    for item in attempt_diagnostics:
        category = _safe_mapping(item).get("failure_category")
        if category:
            categories.append(_fetch_read_failure_category(category))
    return categories


def _candidate_failure_categories(
    candidate_diagnostics: Sequence[Mapping[str, Any]],
) -> list[str]:
    categories: list[str] = []
    for item in candidate_diagnostics:
        category = _safe_mapping(item).get("failure_category")
        if category in {FETCH_READ_FAILURE_MISSING_URL, FETCH_READ_FAILURE_INVALID_URL}:
            categories.append(_fetch_read_failure_category(category))
    return categories


def _provider_results_by_candidate_id(
    provider_results: Sequence[Mapping[str, Any]],
    *,
    relation_plan: Mapping[str, Any],
    run_id: str,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for result in provider_results:
        if not isinstance(result, Mapping):
            continue
        candidate_id, _candidate_digest = _provider_result_candidate_identity(
            result,
            relation_plan=relation_plan,
            run_id=run_id,
        )
        out[candidate_id] = _safe_mapping(result)
    return out


def _provider_extracted_text(provider_result: Mapping[str, Any]) -> str | None:
    text = _clean_provider_extracted_source_text(
        provider_result.get("provider_extracted_text")
    )
    return text or None


def _provider_extracted_source_text_digest(
    provider_result: Mapping[str, Any],
) -> str | None:
    declared = _clean_text(
        provider_result.get("provider_extracted_source_text_digest")
        or provider_result.get("provider_extracted_text_digest"),
        limit=128,
    )
    if declared:
        return declared
    text = _provider_extracted_text(provider_result)
    if not text:
        return None
    return _digest_json({"provider_extracted_text": text})


def _provider_extracted_candidate_window_evaluations(
    provider_extracted_candidates: Sequence[Mapping[str, Any]],
    *,
    provider_results_by_candidate_id: Mapping[str, Mapping[str, Any]],
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None,
) -> list[_CandidateWindowEvaluation]:
    evaluations: list[_CandidateWindowEvaluation] = []
    for candidate in provider_extracted_candidates:
        candidate_id = str(candidate["candidate_id"])
        provider_result = provider_results_by_candidate_id[candidate_id]
        selection = _bounded_plan_text_selection(
            _provider_extracted_text(provider_result) or "",
            relation_plan=relation_plan,
            acquisition_plan=acquisition_plan,
        )
        score = _candidate_window_score(candidate, selection)
        evaluations.append(
            _CandidateWindowEvaluation(
                candidate=candidate,
                provider_result=provider_result,
                selection=selection,
                score=score,
                diagnostic=_candidate_window_diagnostic(
                    candidate,
                    provider_result=provider_result,
                    selection=selection,
                    score=score,
                    selected=False,
                ),
            )
        )
    return evaluations


def _select_provider_extracted_candidate_window(
    evaluations: Sequence[_CandidateWindowEvaluation],
) -> _CandidateWindowEvaluation:
    if not evaluations:
        raise FetchReadContentReferenceError(
            "provider-extracted candidate/window selection had no candidates."
        )
    return max(evaluations, key=lambda item: item.score)


def _candidate_window_score(
    candidate: Mapping[str, Any],
    selection: BoundedTextSelection,
) -> tuple[int, ...]:
    features = _safe_mapping(candidate.get("candidate_selection_features"))
    result_rank = _bounded_int(candidate.get("result_rank"), default=999)
    priority_rank = _bounded_int(candidate.get("fetch_read_priority_rank"), default=999)
    expected_count = len(selection.expected_value_token_kinds)
    matched_value_count = selection.matched_value_token_kind_count
    expected_values_all_matched = int(
        bool(expected_count) and matched_value_count == expected_count
    )
    source_record_tie_breaker = int(
        features.get("source_of_record_domain_signal") is True
    )
    official_tie_breaker = int(
        features.get("official_domain_signal") is True
        or features.get("public_agency_domain_signal") is True
    )
    official_artifact_tie_breaker = int(
        source_record_tie_breaker
        and _official_artifact_feature_signal(features)
    )
    return (
        expected_values_all_matched,
        matched_value_count,
        selection.matched_anchor_count,
        _anchor_match_status_rank(selection),
        -len(selection.missing_anchors),
        official_artifact_tie_breaker,
        source_record_tie_breaker,
        official_tie_breaker,
        -priority_rank,
        -result_rank,
    )


def _anchor_match_status_rank(selection: BoundedTextSelection) -> int:
    if selection.required_anchor_count <= 0:
        return 0
    if selection.matched_anchor_count == selection.required_anchor_count:
        return 3
    if selection.matched_anchor_count > 0:
        return 2
    return 1


def _anchor_match_status(selection: BoundedTextSelection) -> str:
    if selection.required_anchor_count <= 0:
        return "no_anchor_requirements"
    if selection.matched_anchor_count == selection.required_anchor_count:
        return "all_required_anchors_matched"
    if selection.matched_anchor_count == 0:
        return "no_required_anchors_matched"
    return "partial_required_anchor_match"


def _candidate_window_status(selection: BoundedTextSelection) -> str:
    if selection.matched_value_token_kind_count > 0 and selection.matched_anchor_count > 0:
        return ANSWER_BEARING_CANDIDATE_WINDOW_ESTABLISHED
    weak_anchor_coverage = (
        selection.required_anchor_count > 0
        and selection.matched_anchor_count < max(1, selection.required_anchor_count // 2)
    )
    if selection.matched_value_token_kind_count == 0 and weak_anchor_coverage:
        return ANSWER_BEARING_CANDIDATE_WINDOW_NOT_ESTABLISHED
    return ANSWER_BEARING_CANDIDATE_WINDOW_BEST_EFFORT


def _candidate_window_diagnostic(
    candidate: Mapping[str, Any],
    *,
    provider_result: Mapping[str, Any],
    selection: BoundedTextSelection,
    score: Sequence[int],
    selected: bool,
) -> dict[str, Any]:
    provider_text = _provider_extracted_text(provider_result) or ""
    provider_source_digest = _provider_extracted_source_text_digest(provider_result)
    features = _safe_mapping(candidate.get("candidate_selection_features"))
    result_rank = _bounded_int(candidate.get("result_rank"), default=0)
    priority_rank = _bounded_int(candidate.get("fetch_read_priority_rank"), default=0)
    source_record_tie_breaker = (
        features.get("source_of_record_domain_signal") is True
    )
    official_tie_breaker = (
        features.get("official_domain_signal") is True
        or features.get("public_agency_domain_signal") is True
    )
    artifact_type = _official_artifact_type_from_signals(
        features=features,
        content_type=provider_result.get("provider_extracted_content_type"),
        title=_clean_text(candidate.get("title"), limit=220),
        url=_clean_text(candidate.get("url"), limit=700),
    )
    official_artifact_signal = bool(source_record_tie_breaker and artifact_type)
    return {
        "candidate_id": _clean_text(candidate.get("candidate_id"), limit=320),
        "result_rank": result_rank,
        "provider_rank": result_rank,
        "fetch_read_priority_rank": priority_rank,
        "title": _clean_text(candidate.get("title"), limit=220),
        "domain": _clean_domain(candidate.get("domain")),
        "url": _clean_text(candidate.get("url"), limit=700),
        "provider_extracted_source_text_digest": provider_source_digest,
        "provider_extracted_source_text_char_count": len(provider_text),
        "bounded_content_digest": selection.bounded_text_digest,
        "bounded_content_char_count": selection.bounded_text_char_count,
        "selected_window_digest": selection.bounded_text_digest,
        "selected_window_char_count": selection.bounded_text_char_count,
        "source_text_digest_distinct_from_selected_window_digest": (
            bool(provider_source_digest)
            and provider_source_digest != selection.bounded_text_digest
        ),
        "required_anchor_count": selection.required_anchor_count,
        "matched_anchor_count": selection.matched_anchor_count,
        "missing_anchor_count": len(selection.missing_anchors),
        "anchor_match_status": _anchor_match_status(selection),
        "expected_value_token_kinds": list(selection.expected_value_token_kinds),
        "matched_value_token_kinds": list(selection.matched_value_token_kinds),
        "matched_value_token_kind_count": selection.matched_value_token_kind_count,
        "missing_value_token_kinds": list(selection.missing_value_token_kinds),
        "value_token_guidance_consumed": selection.value_token_guidance_consumed,
        "score": list(score),
        "score_components": {
            "expected_value_token_kind_all_matched": bool(
                selection.expected_value_token_kinds
                and selection.matched_value_token_kind_count
                == len(selection.expected_value_token_kinds)
            ),
            "expected_value_token_kind_match_count": (
                selection.matched_value_token_kind_count
            ),
            "matched_anchor_count": selection.matched_anchor_count,
            "anchor_match_status_rank": _anchor_match_status_rank(selection),
            "missing_anchor_count": len(selection.missing_anchors),
            "official_artifact_tie_breaker": official_artifact_signal,
            "source_of_record_looking_tie_breaker": source_record_tie_breaker,
            "official_or_public_agency_tie_breaker": official_tie_breaker,
            "fetch_read_priority_rank_tie_breaker": priority_rank,
            "result_rank_tie_breaker": result_rank,
        },
        "official_pdf_or_table_artifact_candidate": official_artifact_signal,
        "official_artifact_type": artifact_type,
        "official_artifact_read_support_status": (
            OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE
            if official_artifact_signal
            else None
        ),
        "official_artifact_read_support_source": (
            OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_PROVIDER_EXTRACTED
            if official_artifact_signal
            else None
        ),
        "official_artifact_read_support_raw_content_retained": False,
        "selected": selected,
        "candidate_window_selected": selected,
        "answer_bearing_candidate_window_status": _candidate_window_status(selection),
        "diagnostic_posture": "observability_only",
        "not_evidence": True,
        "not_semantic_support": True,
        "not_source_authority": True,
        "not_citation_eligible": True,
        "not_source_obligation_satisfaction": True,
        "not_product_correctness": True,
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
    }


def _apply_candidate_window_diagnostics(
    candidate_diagnostics: list[dict[str, Any]],
    *,
    evaluations: Sequence[_CandidateWindowEvaluation],
    selected_candidate_id: str,
) -> None:
    by_candidate_id = {
        str(evaluation.candidate["candidate_id"]): evaluation
        for evaluation in evaluations
    }
    for diagnostic in candidate_diagnostics:
        candidate_id = _clean_text(diagnostic.get("candidate_id"), limit=320)
        evaluation = by_candidate_id.get(candidate_id or "")
        if evaluation is None:
            continue
        selected = candidate_id == selected_candidate_id
        window_diagnostic = {
            **evaluation.diagnostic,
            "selected": selected,
            "candidate_window_selected": selected,
        }
        diagnostic["answer_bearing_candidate_window_considered"] = True
        diagnostic["answer_bearing_candidate_window_selected"] = selected
        diagnostic["answer_bearing_candidate_window_status"] = (
            window_diagnostic["answer_bearing_candidate_window_status"]
        )
        diagnostic["candidate_window_score"] = window_diagnostic["score"]
        diagnostic["candidate_window_score_components"] = window_diagnostic[
            "score_components"
        ]
        diagnostic["selected_window_digest"] = window_diagnostic[
            "selected_window_digest"
        ]
        diagnostic["selected_window_char_count"] = window_diagnostic[
            "selected_window_char_count"
        ]
        diagnostic["provider_extracted_source_text_digest"] = window_diagnostic[
            "provider_extracted_source_text_digest"
        ]
        diagnostic["provider_extracted_source_text_char_count"] = window_diagnostic[
            "provider_extracted_source_text_char_count"
        ]
        diagnostic[
            "source_text_digest_distinct_from_selected_window_digest"
        ] = window_diagnostic[
            "source_text_digest_distinct_from_selected_window_digest"
        ]
        diagnostic["bounded_content_digest"] = window_diagnostic[
            "bounded_content_digest"
        ]
        diagnostic["bounded_content_char_count"] = window_diagnostic[
            "bounded_content_char_count"
        ]
        diagnostic["required_anchor_count"] = window_diagnostic[
            "required_anchor_count"
        ]
        diagnostic["matched_anchor_count"] = window_diagnostic[
            "matched_anchor_count"
        ]
        diagnostic["missing_anchor_count"] = window_diagnostic[
            "missing_anchor_count"
        ]
        diagnostic["anchor_match_status"] = window_diagnostic["anchor_match_status"]
        diagnostic["expected_value_token_kinds"] = window_diagnostic[
            "expected_value_token_kinds"
        ]
        diagnostic["matched_value_token_kinds"] = window_diagnostic[
            "matched_value_token_kinds"
        ]
        diagnostic["missing_value_token_kinds"] = window_diagnostic[
            "missing_value_token_kinds"
        ]
        diagnostic["value_token_guidance_consumed"] = window_diagnostic[
            "value_token_guidance_consumed"
        ]
        for key in (
            "official_pdf_or_table_artifact_candidate",
            "official_artifact_type",
            "official_artifact_read_support_status",
            "official_artifact_read_support_source",
            "official_artifact_read_support_raw_content_retained",
        ):
            diagnostic[key] = window_diagnostic.get(key)
        if not selected:
            diagnostic["skipped_reason"] = ANSWER_BEARING_CANDIDATE_WINDOW_NOT_SELECTED


def _candidate_window_diagnostics(
    evaluations: Sequence[_CandidateWindowEvaluation],
    *,
    selected_candidate_id: str,
) -> tuple[dict[str, Any], ...]:
    diagnostics: list[dict[str, Any]] = []
    for evaluation in evaluations:
        candidate_id = str(evaluation.candidate["candidate_id"])
        selected = candidate_id == selected_candidate_id
        diagnostics.append(
            {
                **evaluation.diagnostic,
                "selected": selected,
                "candidate_window_selected": selected,
            }
        )
    return tuple(diagnostics)


def _candidate_window_diagnostics_from_attempt_diagnostics(
    attempt_diagnostics: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    diagnostics: list[dict[str, Any]] = []
    for attempt in attempt_diagnostics:
        safe = _safe_mapping(attempt)
        if safe.get("answer_bearing_candidate_window_considered") is not True:
            continue
        diagnostics.append(
            _without_empty(
                {
                    "candidate_id": _clean_text(
                        safe.get("candidate_id"),
                        limit=320,
                    ),
                    "result_rank": _bounded_int(safe.get("result_rank"), default=0),
                    "provider_rank": _bounded_int(
                        safe.get("provider_rank"),
                        default=0,
                    ),
                    "fetch_read_priority_rank": _bounded_int(
                        safe.get("fetch_read_priority_rank"),
                        default=0,
                    ),
                    "title": _clean_text(safe.get("title"), limit=220),
                    "domain": _clean_domain(safe.get("attempted_domain")),
                    "url": _clean_text(safe.get("attempted_url"), limit=700),
                    "bounded_content_digest": _clean_text(
                        safe.get("bounded_content_digest"),
                        limit=128,
                    ),
                    "bounded_content_char_count": _bounded_int(
                        safe.get("bounded_content_char_count")
                    ),
                    "selected_window_digest": _clean_text(
                        safe.get("selected_window_digest"),
                        limit=128,
                    ),
                    "selected_window_char_count": _bounded_int(
                        safe.get("selected_window_char_count")
                    ),
                    "required_anchor_count": _bounded_int(
                        safe.get("required_anchor_count")
                    ),
                    "matched_anchor_count": _bounded_int(
                        safe.get("matched_anchor_count")
                    ),
                    "missing_anchor_count": _bounded_int(
                        safe.get("missing_anchor_count")
                    ),
                    "anchor_match_status": _clean_text(
                        safe.get("anchor_match_status"),
                        limit=80,
                    ),
                    "expected_value_token_kinds": [
                        item
                        for item in (
                            _clean_text(raw, limit=40)
                            for raw in _safe_sequence(
                                safe.get("expected_value_token_kinds")
                            )
                        )
                        if item
                    ],
                    "matched_value_token_kinds": [
                        item
                        for item in (
                            _clean_text(raw, limit=40)
                            for raw in _safe_sequence(
                                safe.get("matched_value_token_kinds")
                            )
                        )
                        if item
                    ],
                    "matched_value_token_kind_count": _bounded_int(
                        safe.get("matched_value_token_kind_count")
                    ),
                    "missing_value_token_kinds": [
                        item
                        for item in (
                            _clean_text(raw, limit=40)
                            for raw in _safe_sequence(
                                safe.get("missing_value_token_kinds")
                            )
                        )
                        if item
                    ],
                    "value_token_guidance_consumed": (
                        safe.get("value_token_guidance_consumed") is True
                    ),
                    "selected": safe.get("answer_bearing_candidate_window_selected")
                    is True,
                    "candidate_window_selected": (
                        safe.get("answer_bearing_candidate_window_selected") is True
                    ),
                    "answer_bearing_candidate_window_status": _clean_text(
                        safe.get("answer_bearing_candidate_window_status"),
                        limit=120,
                    ),
                    "official_pdf_or_table_artifact_candidate": (
                        safe.get("official_pdf_or_table_artifact_candidate") is True
                    ),
                    "official_artifact_type": _clean_text(
                        safe.get("official_artifact_type"),
                        limit=80,
                    ),
                    "official_artifact_read_support_status": _clean_text(
                        safe.get("official_artifact_read_support_status"),
                        limit=120,
                    ),
                    "official_artifact_read_support_source": _clean_text(
                        safe.get("official_artifact_read_support_source"),
                        limit=120,
                    ),
                    "diagnostic_posture": "observability_only",
                    "not_evidence": True,
                    "not_semantic_support": True,
                    "not_source_authority": True,
                    "not_citation_eligible": True,
                    "not_source_obligation_satisfaction": True,
                    "not_product_correctness": True,
                    "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
                }
            )
        )
    return tuple(diagnostics)


def _provider_extracted_fetch_read_material(
    *,
    candidate: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
    provider_result: Mapping[str, Any],
    selection: BoundedTextSelection,
) -> dict[str, Any]:
    bounded_text = selection.bounded_text
    provider_text = _provider_extracted_text(provider_result) or ""
    provider = _clean_text(provider_result.get("provider"), limit=80) or DEFAULT_PROVIDER
    content_type = (
        _content_type_or_unknown(provider_result.get("provider_extracted_content_type"))
        if provider_result.get("provider_extracted_content_type")
        else PROVIDER_EXTRACTED_CONTENT_TYPE
    )
    observed_at = (
        _clean_text(provider_result.get("provider_extracted_at"), limit=80)
        or datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    artifact_payload = _official_artifact_read_support_payload(
        candidate=candidate,
        content_type=content_type,
        readable_text_obtained=bool(bounded_text),
        support_source=OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_PROVIDER_EXTRACTED,
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "run_id": candidate_packet["run_id"],
        "request_id": candidate_packet["request_id"],
        "current_answer_contract_digest": candidate_packet[
            "current_answer_contract_digest"
        ],
        "search_executor_handoff_digest": candidate_packet[
            "search_executor_handoff_digest"
        ],
        "search_result_candidate_packet_id": candidate_packet["packet_id"],
        "search_result_candidate_packet_digest": candidate_packet["packet_digest"],
        "fetch_read_status": "readable",
        "content_acquisition_mode": SOURCE_ACQUISITION_MODE_PROVIDER_EXTRACTED,
        "content_acquisition_provider": provider,
        "provider_extracted_source_content": True,
        "provider_extracted_source_text_digest": (
            _provider_extracted_source_text_digest(provider_result)
        ),
        "provider_extracted_source_text_bounded": True,
        "provider_extracted_source_text_sanitized": True,
        "original_source_url": candidate["url"],
        "original_source_title": candidate.get("title"),
        "original_source_domain": candidate.get("domain"),
        "attempted_url": candidate["url"],
        "resolved_url": candidate["url"],
        "final_url": candidate["url"],
        "resolved_domain": candidate.get("domain"),
        "content_type": content_type,
        "http_status": None,
        "retrieved_or_observed_at": observed_at,
        "published_or_observed_date": candidate.get("published_or_observed_date"),
        "content_title": candidate.get("title"),
        "content_length": len(provider_text),
        "redirect_chain_digest": None,
        "redirect_count": 0,
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(bounded_text),
        "bounded_text_selection": selection.to_metadata(),
        **artifact_payload,
        "raw_page_content_retained": False,
        "raw_page_text_retained": False,
        "raw_headers_retained": False,
        "raw_prompt_retained": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _provider_extracted_content_diagnostic(
    candidate: Mapping[str, Any],
    *,
    provider_result: Mapping[str, Any],
) -> dict[str, Any]:
    selection_features = _safe_mapping(candidate.get("candidate_selection_features"))
    url = _clean_text(candidate.get("url"), limit=700)
    provider = _clean_text(provider_result.get("provider"), limit=80) or DEFAULT_PROVIDER
    content_type = _content_type_or_unknown(
        provider_result.get("provider_extracted_content_type")
        or PROVIDER_EXTRACTED_CONTENT_TYPE
    )
    artifact_payload = _official_artifact_diagnostic_payload(
        candidate=candidate,
        content_type=content_type,
        readable_text_obtained=True,
        support_source=OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_PROVIDER_EXTRACTED,
    )
    return {
        "candidate_id": _clean_text(candidate.get("candidate_id"), limit=320),
        "attempt_index": 0,
        "attempted_url": url,
        "attempted_domain": _clean_domain(candidate.get("domain"))
        or (urlparse(url or "").netloc.lower() if url else None),
        "final_url": url,
        "final_domain": _clean_domain(candidate.get("domain"))
        or (urlparse(url or "").netloc.lower() if url else None),
        "http_status_code": None,
        "redirect_count": 0,
        "redirect_chain_digest": None,
        "provider_rank": _bounded_int(candidate.get("result_rank"), default=0),
        "result_rank": _bounded_int(candidate.get("result_rank"), default=0),
        "fetch_read_priority_rank": _bounded_int(
            candidate.get("fetch_read_priority_rank"),
            default=0,
        ),
        "fetch_read_request_profile_id": FETCH_READ_PUBLIC_WEB_REQUEST_PROFILE_ID,
        "fetch_read_request_posture": "provider_extracted_source_content_no_direct_fetch",
        "content_acquisition_mode": SOURCE_ACQUISITION_MODE_PROVIDER_EXTRACTED,
        "content_acquisition_provider": provider,
        "provider_extracted_source_content": True,
        "provider_extracted_text_char_count": _bounded_int(
            provider_result.get("provider_extracted_text_char_count"),
            default=len(_provider_extracted_text(provider_result) or ""),
        ),
        "provider_extracted_source_text_digest": (
            _provider_extracted_source_text_digest(provider_result)
        ),
        "candidate_selection_policy_id": FETCH_READ_CANDIDATE_SELECTION_POLICY_ID,
        "candidate_selection_policy_scope": FETCH_READ_CANDIDATE_SELECTION_SCOPE,
        "candidate_selection_is_acquisition_only": True,
        "candidate_selection_created_source_authority": False,
        "candidate_selection_satisfies_source_obligation": False,
        "candidate_selection_citation_eligible": False,
        "candidate_selection_claims_correctness": False,
        "candidate_selection_features": selection_features,
        "source_survival_scope": "provider_extracted_source_content",
        "source_survival_candidate_signal": (
            _source_survival_candidate_signal(selection_features)
        ),
        "official_or_source_record_looking_http_candidate": (
            _official_source_survival_features(selection_features)
        ),
        "source_survival_diagnostic_only": True,
        "source_survival_diagnostic_creates_source_authority": False,
        "source_survival_diagnostic_satisfies_source_obligation": False,
        "source_survival_diagnostic_citation_eligible": False,
        "http_status_class": FETCH_READ_UNKNOWN,
        "content_type": content_type,
        "readable_content_type": True,
        "readable_text_obtained": True,
        **artifact_payload,
        "failure_category": None,
        "diagnostic_posture": "observability_only",
        "not_evidence": True,
        "not_citation_eligible": True,
        "not_source_obligation_satisfaction": True,
        "candidate_diagnostics_satisfy_source_obligations": False,
        "fetch_read_failure_metadata_citation_eligible": False,
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
    }


def _official_artifact_read_support_payload(
    *,
    candidate: Mapping[str, Any],
    content_type: str,
    readable_text_obtained: bool,
    support_source: str,
) -> dict[str, Any]:
    features = _safe_mapping(candidate.get("candidate_selection_features"))
    artifact_type = _official_artifact_type_from_signals(
        features=features,
        content_type=content_type,
        title=_clean_text(candidate.get("title"), limit=220),
        url=_clean_text(candidate.get("url"), limit=700),
    )
    if not (
        artifact_type
        and _official_source_survival_features(features)
    ):
        return {}
    status = (
        OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_READABLE
        if readable_text_obtained
        else OFFICIAL_ARTIFACT_READ_SUPPORT_STATUS_UNREADABLE
    )
    return {
        "official_artifact_read_support": True,
        "official_artifact_type": artifact_type,
        "official_artifact_read_support_status": status,
        "official_artifact_read_support_source": support_source,
        "official_artifact_read_support_bounded": bool(readable_text_obtained),
        "official_artifact_read_support_sanitized": bool(readable_text_obtained),
        "official_artifact_read_support_raw_content_retained": False,
        "official_artifact_read_support_creates_source_authority": False,
        "official_artifact_read_support_satisfies_source_obligation": False,
        "official_artifact_read_support_citation_eligible": False,
        "official_artifact_read_support_claims_correctness": False,
        "pdf_parsing_opened": False,
        "ocr_opened": False,
        "browser_automation_opened": False,
        "heavy_document_parser_dependency_added": False,
    }


def _official_artifact_diagnostic_payload(
    *,
    candidate: Mapping[str, Any],
    content_type: str,
    readable_text_obtained: bool,
    support_source: str,
) -> dict[str, Any]:
    payload = _official_artifact_read_support_payload(
        candidate=candidate,
        content_type=content_type,
        readable_text_obtained=readable_text_obtained,
        support_source=support_source,
    )
    if payload:
        return {
            "official_pdf_or_table_artifact_candidate": True,
            "official_artifact_type": payload["official_artifact_type"],
            "official_artifact_read_support_status": payload[
                "official_artifact_read_support_status"
            ],
            "official_artifact_read_support_source": payload[
                "official_artifact_read_support_source"
            ],
            "official_artifact_read_support_raw_content_retained": False,
            "official_artifact_read_support_creates_source_authority": False,
            "official_artifact_read_support_satisfies_source_obligation": False,
            "official_artifact_read_support_citation_eligible": False,
            "official_artifact_read_support_claims_correctness": False,
            "pdf_parsing_opened": False,
            "ocr_opened": False,
            "browser_automation_opened": False,
            "heavy_document_parser_dependency_added": False,
        }
    return {
        "official_pdf_or_table_artifact_candidate": False,
        "official_artifact_type": None,
        "official_artifact_read_support_status": None,
        "official_artifact_read_support_source": None,
        "official_artifact_read_support_raw_content_retained": False,
        "official_artifact_read_support_creates_source_authority": False,
        "official_artifact_read_support_satisfies_source_obligation": False,
        "official_artifact_read_support_citation_eligible": False,
        "official_artifact_read_support_claims_correctness": False,
        "pdf_parsing_opened": False,
        "ocr_opened": False,
        "browser_automation_opened": False,
        "heavy_document_parser_dependency_added": False,
    }


def _fetch_read_material(
    *,
    candidate: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
    fetch_result: GenericLiveFetchReadResult,
    selection: BoundedTextSelection,
) -> dict[str, Any]:
    bounded_text = selection.bounded_text
    content_type = _content_type_or_unknown(fetch_result.content_type)
    artifact_payload = _official_artifact_read_support_payload(
        candidate=candidate,
        content_type=content_type,
        readable_text_obtained=bool(bounded_text),
        support_source=(
            _clean_text(
                fetch_result.official_artifact_read_support_source,
                limit=120,
            )
            or OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_FETCH_RUNNER
        ),
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "run_id": candidate_packet["run_id"],
        "request_id": candidate_packet["request_id"],
        "current_answer_contract_digest": candidate_packet[
            "current_answer_contract_digest"
        ],
        "search_executor_handoff_digest": candidate_packet[
            "search_executor_handoff_digest"
        ],
        "search_result_candidate_packet_id": candidate_packet["packet_id"],
        "search_result_candidate_packet_digest": candidate_packet["packet_digest"],
        "fetch_read_status": "readable",
        "attempted_url": candidate["url"],
        "resolved_url": fetch_result.final_url,
        "final_url": fetch_result.final_url,
        "resolved_domain": fetch_result.final_domain,
        "content_type": content_type,
        "http_status": fetch_result.status_code,
        "retrieved_or_observed_at": (
            fetch_result.retrieved_or_observed_at
            or datetime.now(UTC).replace(microsecond=0).isoformat()
        ),
        "published_or_observed_date": candidate.get("published_or_observed_date"),
        "content_title": fetch_result.content_title or candidate.get("title"),
        "content_length": fetch_result.fetched_byte_count,
        "redirect_chain_digest": fetch_result.redirect_chain_digest,
        "redirect_count": fetch_result.redirect_count,
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(bounded_text),
        "bounded_text_selection": selection.to_metadata(),
        **artifact_payload,
        "raw_page_content_retained": False,
        "raw_page_text_retained": False,
        "raw_headers_retained": False,
        "raw_prompt_retained": False,
    }


def _failed_fetch_read_materials(
    *,
    candidate_packet: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    attempt_diagnostics: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates_by_id = {
        str(candidate.get("candidate_id")): _safe_mapping(candidate)
        for candidate in candidates
        if candidate.get("candidate_id")
    }
    materials: list[dict[str, Any]] = []
    for diagnostic in attempt_diagnostics:
        attempt = _safe_mapping(diagnostic)
        candidate = candidates_by_id.get(str(attempt.get("candidate_id")))
        if not candidate:
            continue
        content_type = _content_type_or_unknown(attempt.get("content_type"))
        artifact_payload = _official_artifact_read_support_payload(
            candidate=candidate,
            content_type=content_type,
            readable_text_obtained=False,
            support_source=OFFICIAL_ARTIFACT_READ_SUPPORT_SOURCE_FETCH_RUNNER,
        )
        materials.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_digest": candidate["candidate_digest"],
                "run_id": candidate_packet["run_id"],
                "request_id": candidate_packet["request_id"],
                "current_answer_contract_digest": candidate_packet[
                    "current_answer_contract_digest"
                ],
                "search_executor_handoff_digest": candidate_packet[
                    "search_executor_handoff_digest"
                ],
                "search_result_candidate_packet_id": candidate_packet["packet_id"],
                "search_result_candidate_packet_digest": candidate_packet[
                    "packet_digest"
                ],
                "fetch_read_status": "failed",
                "attempted_url": attempt.get("attempted_url") or candidate.get("url"),
                "resolved_url": attempt.get("final_url") or candidate.get("url"),
                "final_url": attempt.get("final_url") or candidate.get("url"),
                "resolved_domain": attempt.get("final_domain")
                or candidate.get("domain"),
                "content_type": content_type,
                "http_status": attempt.get("http_status_code"),
                "retrieved_or_observed_at": datetime.now(UTC)
                .replace(microsecond=0)
                .isoformat(),
                "published_or_observed_date": candidate.get(
                    "published_or_observed_date"
                ),
                "content_title": candidate.get("title"),
                "content_length": 0,
                "read_error_code": attempt.get("failure_category")
                or "fetch_read_failed",
                "failure_reason": (
                    "bounded fetch/read failed before readable sanitized text "
                    "was retained"
                ),
                "redirect_chain_digest": attempt.get("redirect_chain_digest"),
                "redirect_count": attempt.get("redirect_count"),
                **artifact_payload,
                "raw_page_content_retained": False,
                "raw_page_text_retained": False,
                "raw_headers_retained": False,
                "raw_prompt_retained": False,
            }
        )
    return materials


def _fetch_summary(fetch_packet: Mapping[str, Any]) -> dict[str, Any]:
    readable_handoff_created = any(
        _safe_mapping(reference).get("fetch_read_status") == "readable"
        for reference in _safe_sequence(fetch_packet.get("reference_records"))
    )
    return {
        "decision": (
            PASS_DECISION
            if readable_handoff_created
            else BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES
        ),
        "readable_content_handoff_created": readable_handoff_created,
        "retention_flags": {
            "headers_retained": False,
            "page_content_retained": False,
            "page_html_retained": False,
            "page_text_retained": False,
            "private_material_retained": False,
            "prompt_retained": False,
            "provider_payload_retained": False,
            "search_response_retained": False,
            "unbounded_page_material_retained": False,
        },
        "closed_downstream_surfaces": {
            "answer_text": False,
            "author_or_authorprose": False,
            "citation_eligibility_or_rendering": False,
            "component_coverage": False,
            "evidence_ledger_admission": False,
            "final_answer_packet": False,
            "product_correctness_claim": False,
            "semantic_observation": False,
            "source_obligation_satisfaction": False,
            "sufficiency_readiness": False,
        },
        "fetch_read_content_packet_ref": {
            "packet_id": fetch_packet["packet_id"],
            "packet_digest": fetch_packet["packet_digest"],
            "reference_count": fetch_packet["reference_count"],
            "schema_version": fetch_packet["schema_version"],
        },
    }


def _validate_fetch_result(
    fetch_result: GenericLiveFetchReadResult,
    *,
    candidate: Mapping[str, Any],
) -> None:
    if fetch_result.attempted_url != candidate.get("url"):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read attempted URL differed from selected candidate URL.",
        )
    parsed = urlparse(fetch_result.final_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read final URL was not http(s).",
        )
    if fetch_result.redirect_count > MAX_REDIRECTS:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED,
            "fetch/read redirect cap exhausted.",
            caps_exhausted=True,
        )
    if fetch_result.fetched_byte_count > MAX_FETCHED_BYTES:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED,
            "fetch/read byte cap exhausted.",
            caps_exhausted=True,
        )
    status_class = _normalized_status_class(fetch_result.status_class) or _status_class(
        fetch_result.status_code
    )
    if status_class and not status_class.startswith("2"):
        failure_category = _failure_category_for_status_class(status_class)
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            f"fetch/read HTTP status class {status_class} did not produce readable content.",
            fetch_status_class=status_class,
            fetch_content_type=_content_type_or_unknown(fetch_result.content_type),
            fetch_readable_content_type=_readable_content_type_value(
                fetch_result.content_type
            ),
            fetch_readable_text_obtained=False,
            fetch_failure_category=failure_category,
            fetch_final_url=fetch_result.final_url,
            fetch_status_code=fetch_result.status_code,
            fetch_redirect_count=fetch_result.redirect_count,
            fetch_redirect_chain_digest=fetch_result.redirect_chain_digest,
        )
    content_type = _content_type_or_unknown(fetch_result.content_type)
    readable_content_type = _readable_content_type_value(content_type)
    if readable_content_type is False:
        if _official_artifact_fixture_read_support_allowed(
            fetch_result,
            candidate=candidate,
            content_type=content_type,
        ):
            if fetch_result.sanitized_text:
                return
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
                (
                    "official PDF/table artifact read support was flagged, but "
                    "no bounded sanitized text was supplied."
                ),
                fetch_status_class=status_class or FETCH_READ_UNKNOWN,
                fetch_content_type=content_type,
                fetch_readable_content_type=False,
                fetch_readable_text_obtained=False,
                fetch_failure_category=FETCH_READ_FAILURE_NO_READABLE_TEXT,
            )
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read did not receive a readable text/html or text/plain response.",
            fetch_status_class=status_class or FETCH_READ_UNKNOWN,
            fetch_content_type=content_type,
            fetch_readable_content_type=False,
            fetch_readable_text_obtained=False,
            fetch_failure_category=FETCH_READ_FAILURE_UNSUPPORTED_CONTENT_TYPE,
        )
    if not fetch_result.sanitized_text:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read did not produce sanitized readable text.",
            fetch_status_class=status_class or FETCH_READ_UNKNOWN,
            fetch_content_type=content_type,
            fetch_readable_content_type=readable_content_type,
            fetch_readable_text_obtained=False,
            fetch_failure_category=FETCH_READ_FAILURE_NO_READABLE_TEXT,
        )


def _official_artifact_fixture_read_support_allowed(
    fetch_result: GenericLiveFetchReadResult,
    *,
    candidate: Mapping[str, Any],
    content_type: str,
) -> bool:
    if fetch_result.official_artifact_read_support is not True:
        return False
    if content_type not in OFFICIAL_ARTIFACT_READ_SUPPORT_CONTENT_TYPES:
        return False
    features = _safe_mapping(candidate.get("candidate_selection_features"))
    return bool(
        _official_source_survival_features(features)
        and _official_artifact_type_from_signals(
            features=features,
            content_type=content_type,
            title=_clean_text(candidate.get("title"), limit=220),
            url=_clean_text(candidate.get("url"), limit=700),
        )
    )


def _bounded_plan_text_selection(
    text: str,
    *,
    relation_plan: Mapping[str, Any],
    acquisition_plan: Mapping[str, Any] | None = None,
) -> BoundedTextSelection:
    return select_bounded_answer_bearing_text(
        text,
        max_chars=FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
        required_or_preferred_anchors=_generic_anchor_groups(
            relation_plan,
            acquisition_plan=acquisition_plan,
        ),
        expected_value_token_kinds=_expected_value_token_kinds_from_plan(
            acquisition_plan
        ),
        component_text=_clean_text(relation_plan.get("component_text"), limit=260),
        claim_under_test=_clean_text(relation_plan.get("claim_under_test"), limit=500),
    )


def _generic_anchor_groups(
    relation_plan: Mapping[str, Any],
    *,
    acquisition_plan: Mapping[str, Any] | None = None,
) -> list[tuple[str, ...]]:
    acquisition = _safe_mapping(acquisition_plan)
    anchor_terms = [
        _clean_text(item, limit=120)
        for item in _safe_sequence(acquisition.get("answer_bearing_anchor_terms"))
    ]
    if any(anchor_terms):
        return [(term,) for term in anchor_terms if term]
    text = " ".join(
        str(item or "")
        for item in (
            relation_plan.get("component_text"),
            relation_plan.get("source_obligation_text"),
        )
    )
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in text.replace("/", " ").replace("-", " ").split():
        token = "".join(ch for ch in raw.casefold() if ch.isalnum())
        if len(token) < 4 or token in {
            "current",
            "official",
            "source",
            "record",
            "that",
            "states",
            "find",
        }:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return [(token,) for token in tokens[:8]]


def _selected_window_guidance_counts(
    *,
    acquisition_plan: Mapping[str, Any] | None,
    selection: BoundedTextSelection | None,
    blocked: bool = False,
    blocker: str | None = None,
) -> dict[str, Any]:
    acquisition = _safe_mapping(acquisition_plan)
    produced = bool(acquisition.get("selected_window_guidance"))
    anchor_consumed = bool(produced and selection is not None)
    expected_value_kinds = _expected_value_token_kinds_from_plan(acquisition)
    value_consumed = bool(
        expected_value_kinds
        and selection is not None
        and selection.value_token_guidance_consumed is True
    )
    value_blocked = bool(expected_value_kinds and (blocked or not value_consumed))
    value_blocker = blocker
    if expected_value_kinds and not value_consumed and not value_blocker:
        value_blocker = (
            "existing bounded-window selector did not consume expected "
            "value-token kinds"
        )
    return {
        "selected_window_guidance_produced": 1 if produced else 0,
        "selected_window_guidance_consumed": 1 if anchor_consumed and value_consumed else 0,
        "selected_window_guidance_blocked": 1 if produced and blocked else 0,
        "selected_window_guidance_blocker": (
            _clean_text(blocker, limit=220) if produced and blocked else None
        ),
        "selected_window_anchor_guidance_consumed": 1 if anchor_consumed else 0,
        "selected_window_value_token_guidance_consumed": 1 if value_consumed else 0,
        "selected_window_value_token_guidance_blocked": 1 if value_blocked else 0,
        "selected_window_value_token_guidance_blocker": (
            _clean_text(value_blocker, limit=220) if value_blocked else None
        ),
    }


def _expected_value_token_kinds_from_plan(
    acquisition_plan: Mapping[str, Any] | None,
) -> list[str]:
    acquisition = _safe_mapping(acquisition_plan)
    return [
        item
        for item in (
            _clean_text(raw, limit=40)
            for raw in _safe_sequence(acquisition.get("expected_value_token_kinds"))
        )
        if item
    ]


def _guard_dprime_review_route(
    *,
    confirm_live_dprime_review: bool,
    dprime_model_review_callable: Callable[..., Any] | None,
    dprime_one_shot_model_review_adapter: Any | None,
    environ: Mapping[str, str] | None,
) -> None:
    if not confirm_live_dprime_review:
        return
    if not _pytest_or_ci_guard(environ):
        return
    if dprime_model_review_callable is not None:
        return
    if dprime_one_shot_model_review_adapter is not None:
        return
    raise GenericSingleRelationLiveDogfoodRunError(
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE,
        (
            "Default live D-prime product model route is disabled under "
            "pytest/CI unless a fake review callable or transport is injected."
        ),
    )


def _dprime_review_kwargs(
    *,
    smart_provider: str | None,
    smart_model: str | None,
    dprime_model_review_license: Mapping[str, Any] | None,
    dprime_model_review_callable: Callable[..., Any] | None,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None,
    dprime_one_shot_model_review_adapter: Any | None,
) -> dict[str, Any]:
    if dprime_model_review_callable is not None:
        return {
            "dprime_model_review_license": (
                dprime_model_review_license or _fake_dprime_review_license()
            ),
            "dprime_model_review_callable": dprime_model_review_callable,
            "dprime_one_shot_provider_boundary": dprime_one_shot_provider_boundary,
            "dprime_one_shot_model_review_adapter": (
                dprime_one_shot_model_review_adapter
            ),
        }
    boundary = (
        dict(dprime_one_shot_provider_boundary)
        if dprime_one_shot_provider_boundary is not None
        else build_dprime_product_smart_model_review_provider_boundary()
    )
    boundary_id = _clean_text(boundary.get("boundary_id"), limit=320)
    if not boundary_id:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE,
            "D-prime product route provider boundary did not expose boundary_id.",
        )
    adapter = dprime_one_shot_model_review_adapter
    if adapter is None:
        adapter = build_dprime_product_smart_model_review_adapter(
            provider_boundary_ref=boundary_id,
            smart_provider=smart_provider or "OpenAI",
            smart_model=smart_model or "gpt-5.4",
        )
    return {
        "dprime_model_review_license": (
            dprime_model_review_license
            or build_dprime_product_smart_model_review_license()
        ),
        "dprime_one_shot_provider_boundary": boundary,
        "dprime_one_shot_model_review_adapter": adapter,
    }


def _fake_dprime_review_license() -> dict[str, Any]:
    return {
        "license_id": "generic-single-relation-live-dogfood-01:fake-test",
        "enabled": True,
        "test_only": True,
        "callable_kind": "fake_test",
        "max_model_review_calls": 1,
        "retry_policy": "forbidden",
        "timeout_policy": "fail_closed",
    }


def _mapped_live_decision(
    status_decision: str,
    *,
    model_review_licensed: bool,
) -> str:
    if status_decision == PASS_DECISION:
        return PASS_DECISION
    if status_decision == "BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED":
        if model_review_licensed:
            return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PATH_NOT_CONSUMED
        return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED
    if status_decision == BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID:
        return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_OUTPUT_INVALID
    if status_decision in {
        BLOCKED_APPROVED_MODEL_UNAVAILABLE,
        BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED,
        BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE,
        BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE,
        BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT,
    }:
        return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE
    if status_decision in {
        "BLOCKED_DPRIME_GENERIC_RELATION_INTAKE_MISSING",
        "BLOCKED_DPRIME_PREFLIGHT_FAILED",
    }:
        return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CONTRACT_MISSING
    if status_decision in {
        "BLOCKED_FETCH_READ_ARTIFACT_MISSING",
        "BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE",
        "BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE",
        "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE",
    }:
        return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING
    if status_decision == "BLOCKED_OUTPUT_HYGIENE":
        return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE
    return status_decision


def _mapped_blocker_detail(
    *,
    decision: str,
    status_decision: str,
    original_detail: str,
    model_review_licensed: bool,
) -> str:
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED:
        return (
            "Live acquisition/readability/custody reached the D-prime relation "
            f"intake posture, but {CONFIRM_LIVE_DPRIME_REVIEW_FLAG} was not "
            "provided; no model call was made."
        )
    safe_original_detail = _redact_private_text(original_detail)
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PATH_NOT_CONSUMED:
        return (
            "The D-prime review was licensed, but the existing product path did "
            f"not produce answer/source-display output; status decision: {status_decision}. "
            f"{safe_original_detail}"
        ).strip()
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE:
        return (
            "The explicit D-prime review route failed closed before producing a "
            f"validated support proposal; status decision: {status_decision}. "
            f"{safe_original_detail}"
        ).strip()
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_OUTPUT_INVALID:
        return (
            "The explicit D-prime review route made one attempt, but the model "
            f"review output was invalid; status decision: {status_decision}. "
            f"{safe_original_detail}"
        ).strip()
    if model_review_licensed and safe_original_detail:
        return safe_original_detail
    return safe_original_detail or f"underlying status decision: {status_decision}."


def _load_sanitized_provider_output(path: Path) -> dict[str, Any]:
    try:
        decoded = _read_json(path)
    except FileNotFoundError as exc:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE,
            "sanitized provider acquisition response was not written.",
        ) from exc
    return _validate_provider_payload(decoded)


def _validate_provider_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = _safe_mapping(payload)
    envelope_guard = {key: item for key, item in raw.items() if key != "results"}
    _reject_forbidden_material(
        envelope_guard,
        context="sanitized provider response",
    )
    unknown = sorted(set(raw) - _ALLOWED_PROVIDER_ENVELOPE_KEYS)
    if unknown:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider response has unsupported fields: "
            + ", ".join(unknown),
        )
    if raw.get("raw_provider_payload_retained") is not False:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider response retained raw provider payload.",
        )
    if raw.get("raw_search_response_retained") is not False:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider response retained raw search response.",
        )
    results = raw.get("results")
    if not isinstance(results, list):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "sanitized provider response results must be a list.",
        )
    if len(results) > MAX_PROVIDER_RESULTS:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED,
            "sanitized provider response exceeded max results cap.",
            caps_exhausted=True,
        )
    if _bounded_int(raw.get("result_count"), default=len(results)) != len(results):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "sanitized provider result_count does not match results length.",
        )
    normalized = [
        _normalize_provider_result(item, index=i) for i, item in enumerate(results, 1)
    ]
    return {
        "request_kind": raw.get("request_kind"),
        "provider": str(raw.get("provider") or DEFAULT_PROVIDER),
        "operation": str(raw.get("operation") or DEFAULT_OPERATION),
        "result_count": len(normalized),
        "results": normalized,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _provider_results(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {**dict(item), "provider": payload.get("provider") or DEFAULT_PROVIDER}
        for item in payload.get("results", [])
        if isinstance(item, Mapping)
    ]


def _normalize_provider_result(value: Any, *, index: int) -> dict[str, Any]:
    raw = _safe_mapping(value)
    provider_extracted_text = _clean_provider_extracted_source_text(
        raw.get("provider_extracted_text")
    )
    result_guard = dict(raw)
    if "provider_extracted_text" in result_guard:
        result_guard["provider_extracted_text"] = provider_extracted_text
    _reject_forbidden_material(result_guard, context="sanitized provider result")
    unknown = sorted(set(raw) - _ALLOWED_PROVIDER_RESULT_KEYS)
    if unknown:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result has unsupported fields: " + ", ".join(unknown),
        )
    if raw.get("raw_provider_payload_retained") is True:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result retained raw provider payload.",
        )
    if raw.get("raw_search_response_retained") is True:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result retained raw search response.",
        )
    url, url_source = _provider_url_and_source(raw)
    url_valid = _is_valid_http_url(url)
    domain = _clean_domain(raw.get("domain")) or (
        urlparse(url).netloc.lower() if url and urlparse(url).netloc else None
    )
    provider_extracted_text_digest = (
        _digest_json({"provider_extracted_text": provider_extracted_text})
        if provider_extracted_text
        else None
    )
    declared_provider_extracted_digests = tuple(
        digest
        for digest in (
            _clean_text(raw.get("provider_extracted_text_digest"), limit=128),
            _clean_text(
                raw.get("provider_extracted_source_text_digest"),
                limit=128,
            ),
        )
        if digest
    )
    for declared_provider_extracted_digest in declared_provider_extracted_digests:
        if declared_provider_extracted_digest != provider_extracted_text_digest:
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
                "sanitized provider result extracted text digest mismatch.",
            )
    declared_provider_extracted_count = _bounded_int(
        raw.get("provider_extracted_text_char_count"),
        default=len(provider_extracted_text or ""),
    )
    if provider_extracted_text and declared_provider_extracted_count != len(
        provider_extracted_text
    ):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result extracted text count mismatch.",
        )
    if provider_extracted_text and (
        raw.get("provider_extracted_text_sanitized") is not True
        or raw.get("provider_extracted_text_bounded") is not True
    ):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result extracted text must be bounded and sanitized.",
        )
    return {
        "title": _required_text(raw.get("title"), "provider result requires title", 220),
        "url": url,
        "url_source": url_source,
        "url_valid": url_valid,
        "domain": domain,
        "snippet": _clean_text(raw.get("snippet"), limit=500),
        "published_or_observed_date": _clean_text(
            raw.get("published_or_observed_date") or raw.get("date"),
            limit=80,
        ),
        "result_rank": _positive_int(raw.get("result_rank") or raw.get("rank") or index),
        "provider_call_index": _positive_int(
            raw.get("provider_call_index") or raw.get("call_index") or 1
        ),
        "provider_extracted_text": provider_extracted_text,
        "provider_extracted_text_sanitized": (
            raw.get("provider_extracted_text_sanitized") is True
            if provider_extracted_text
            else False
        ),
        "provider_extracted_text_bounded": (
            raw.get("provider_extracted_text_bounded") is True
            if provider_extracted_text
            else False
        ),
        "provider_extracted_text_char_count": (
            len(provider_extracted_text) if provider_extracted_text else 0
        ),
        "provider_extracted_text_digest": provider_extracted_text_digest,
        "provider_extracted_source_text_digest": provider_extracted_text_digest,
        "provider_extracted_content_type": _content_type_or_unknown(
            raw.get("provider_extracted_content_type")
            or PROVIDER_EXTRACTED_CONTENT_TYPE
        )
        if provider_extracted_text
        else None,
        "provider_extracted_at": _clean_text(
            raw.get("provider_extracted_at"),
            limit=80,
        ),
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _contract_ref_from_plan(plan: Mapping[str, Any]) -> dict[str, str]:
    digest = _digest_json(
        {
            "phase": PHASE_NAME,
            "relation_plan_id": plan.get("plan_id"),
            "relation_plan_packet_digest": plan.get("packet_digest"),
            "component_id": plan.get("component_id"),
            "source_obligation_id": plan.get("source_obligation_id"),
        }
    )
    return {
        "source": "generic_relation_plan",
        "contract_version": "generic-single-relation-live-dogfood-v1",
        "contract_digest": digest,
    }


def _handoff_ref_from_plan(
    plan: Mapping[str, Any],
    *,
    contract_ref: Mapping[str, Any],
) -> dict[str, Any]:
    digest = _digest_json(
        {
            "phase": PHASE_NAME,
            "relation_plan_id": plan.get("plan_id"),
            "search_requirement_id": plan.get("search_requirement_id"),
            "search_query_seed_used": _search_query_seed(plan),
            "contract_digest": contract_ref.get("contract_digest"),
        }
    )
    return {
        "handoff_id": f"search-executor-handoff:{plan.get('search_requirement_id')}",
        "handoff_digest": digest,
        "schema_version": "generic-single-relation-live-dogfood-handoff-v1",
        "contract_parent_kind": "generic_relation_plan",
        "parent_current_contract_ref": dict(contract_ref),
    }


def _search_query_seed(plan: Mapping[str, Any]) -> str:
    seeds = _safe_sequence(plan.get("search_query_seeds"))
    seed = _clean_text(seeds[0] if seeds else None, limit=220)
    if not seed:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM,
            "relation plan did not provide a live search query seed.",
        )
    return seed


def _evidence_admission_count(payload: Mapping[str, Any]) -> int:
    admission = _safe_mapping(payload.get("source_evidence_admission_ref"))
    return 1 if admission.get("status") == "custody_created" else 0


def _dprime_call_count(payload: Mapping[str, Any]) -> int:
    dprime = _safe_mapping(payload.get("dprime_status"))
    return _bounded_int(dprime.get("model_review_call_count"))


def _dprime_calls_completed(payload: Mapping[str, Any]) -> int:
    dprime = _safe_mapping(payload.get("dprime_status"))
    return 1 if dprime.get("model_review_status") == "completed" else 0


def _followup_loop_count(payload: Mapping[str, Any]) -> int:
    followup = _safe_mapping(payload.get("dprime_followup_search_reentry_ref"))
    status = str(followup.get("status") or "")
    return 1 if status and status != "not reached" else 0


def _source_display_entries(packet: Mapping[str, Any]) -> list[str]:
    return [
        str(entry.get("display_text"))
        for entry in packet.get("source_display_entries") or []
        if isinstance(entry, Mapping) and entry.get("display_text")
    ]


def _source_citation_display_boundary_entries(packet: Mapping[str, Any]) -> list[str]:
    return [
        str(entry.get("display_text"))
        for entry in packet.get("source_citation_display_entries") or []
        if isinstance(entry, Mapping) and entry.get("display_text")
    ]


def _actual_source_authority_posture_created(payload: Mapping[str, Any]) -> bool:
    posture = _safe_mapping(payload.get("source_authority_posture_ref"))
    return posture.get("phase") == "ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01"


def _enforce_caps(counts: Mapping[str, int]) -> None:
    checks = (
        ("query_plans_consumed", MAX_QUERY_PLANS_CONSUMED, "query plan"),
        (
            "initial_fast_model_planning_calls_attempted",
            MAX_INITIAL_FAST_MODEL_PLANNING_CALLS,
            "initial FastModel planning",
        ),
        (
            "recovery_fast_model_planning_calls_attempted",
            MAX_RECOVERY_FAST_MODEL_PLANNING_CALLS,
            "recovery FastModel planning",
        ),
        (
            "fast_planner_model_calls_attempted",
            MAX_FAST_MODEL_PLANNING_CALLS,
            "FastModel planning",
        ),
        (
            "extraction_provider_calls_attempted",
            MAX_PROVIDER_SEARCH_CALLS,
            "extraction provider/search",
        ),
        ("serper_scout_calls_attempted", MAX_SERPER_SCOUT_CALLS, "Serper scout"),
        ("provider_results_returned", MAX_PROVIDER_RESULTS, "provider results"),
        ("fetch_read_attempts", MAX_FETCH_READ_ATTEMPTS, "fetch/read"),
        (
            "evidence_ledger_admissions",
            MAX_EVIDENCE_LEDGER_ADMISSIONS,
            "EvidenceLedger admissions",
        ),
        (
            "dprime_model_review_calls_attempted",
            MAX_DPRIME_MODEL_REVIEW_CALLS,
            "D-prime/model review",
        ),
        (
            "source_challenge_recovery_provider_calls_attempted",
            MAX_SOURCE_CHALLENGE_RECOVERY_PROVIDER_CALLS,
            "source-challenge recovery provider/search",
        ),
        ("followup_loop_count", MAX_FOLLOWUP_LOOPS, "follow-up loop"),
    )
    for key, cap, label in checks:
        if _bounded_int(counts.get(key)) > cap:
            blocker = (
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED
                if key == "dprime_model_review_calls_attempted"
                else BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED
            )
            raise GenericSingleRelationLiveDogfoodRunError(
                blocker,
                f"{label} cap exceeded.",
                caps_exhausted=True,
            )


def _caps_ref() -> dict[str, int]:
    return {
        "max_live_runs": MAX_LIVE_RUNS,
        "max_query_plans_consumed": MAX_QUERY_PLANS_CONSUMED,
        "max_initial_fast_model_planning_calls": (
            MAX_INITIAL_FAST_MODEL_PLANNING_CALLS
        ),
        "max_recovery_fast_model_planning_calls": (
            MAX_RECOVERY_FAST_MODEL_PLANNING_CALLS
        ),
        "max_fast_model_planning_calls": MAX_FAST_MODEL_PLANNING_CALLS,
        "max_provider_search_calls": MAX_PROVIDER_SEARCH_CALLS,
        "max_extraction_provider_calls": MAX_PROVIDER_SEARCH_CALLS,
        "max_source_challenge_recovery_provider_calls": (
            MAX_SOURCE_CHALLENGE_RECOVERY_PROVIDER_CALLS
        ),
        "max_serper_scout_calls": MAX_SERPER_SCOUT_CALLS,
        "max_provider_results": MAX_PROVIDER_RESULTS,
        "max_fetch_read_attempts": MAX_FETCH_READ_ATTEMPTS,
        "max_evidence_ledger_admissions": MAX_EVIDENCE_LEDGER_ADMISSIONS,
        "max_dprime_model_review_calls": MAX_DPRIME_MODEL_REVIEW_CALLS,
        "max_followup_loops": MAX_FOLLOWUP_LOOPS,
        "max_fap_calls": MAX_FAP_CALLS,
        "max_author_calls": MAX_AUTHOR_CALLS,
        "max_independent_source_checks_outside_product_path": (
            MAX_INDEPENDENT_SOURCE_CHECKS
        ),
    }


def _packet_safe_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    safe = _json_safe(_redact_private_values(payload))
    _reject_forbidden_material(safe, context="generic live semantic status payload")
    return _safe_mapping(safe)


def _command_harness(
    *,
    command_flag: str = MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
    confirmation_flag: str = CONFIRM_LIVE_DOGFOOD_FLAG,
    confirm_live_dprime_review: bool,
    confirm_live_source_challenge_recovery: bool,
) -> str:
    command = f"python -m proplex {command_flag} {confirmation_flag}"
    if confirm_live_dprime_review:
        command = f"{command} {CONFIRM_LIVE_DPRIME_REVIEW_FLAG}"
    if confirm_live_source_challenge_recovery:
        command = f"{command} {CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG}"
    return command


def _entrypoint_metadata(
    *,
    entrypoint_surface: str,
    entrypoint_kind: str,
    diagnostic_dogfood_alias: bool,
    supported_query_class: str,
) -> dict[str, Any]:
    if entrypoint_kind == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND:
        return {
            "command_flag": MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
            "confirmation_flag": CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
            "entrypoint_surface": PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
            "entrypoint_kind": PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
            "diagnostic_dogfood_alias": False,
            "supported_query_class": PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
        }
    if (
        entrypoint_surface != DOGFOOD_ENTRYPOINT_SURFACE
        or supported_query_class != DOGFOOD_SUPPORTED_QUERY_CLASS
        or diagnostic_dogfood_alias is not True
    ):
        _blocked_output_hygiene("generic live dogfood entrypoint metadata invalid.")
    return {
        "command_flag": MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
        "confirmation_flag": CONFIRM_LIVE_DOGFOOD_FLAG,
        "entrypoint_surface": DOGFOOD_ENTRYPOINT_SURFACE,
        "entrypoint_kind": DOGFOOD_ENTRYPOINT_KIND,
        "diagnostic_dogfood_alias": True,
        "supported_query_class": DOGFOOD_SUPPORTED_QUERY_CLASS,
    }


def _entrypoint_metadata_from_mapping(metadata: Mapping[str, Any]) -> dict[str, Any]:
    entrypoint = _safe_mapping(metadata)
    return _entrypoint_metadata(
        entrypoint_surface=_clean_text(
            entrypoint.get("entrypoint_surface"),
            limit=120,
        )
        or DOGFOOD_ENTRYPOINT_SURFACE,
        entrypoint_kind=_clean_text(entrypoint.get("entrypoint_kind"), limit=120)
        or DOGFOOD_ENTRYPOINT_KIND,
        diagnostic_dogfood_alias=(
            entrypoint.get("diagnostic_dogfood_alias") is True
        ),
        supported_query_class=_clean_text(
            entrypoint.get("supported_query_class"),
            limit=160,
        )
        or DOGFOOD_SUPPORTED_QUERY_CLASS,
    )


def _run_output_dir(
    root: Path,
    output_dir: str | Path,
    run_id: str,
    *,
    entrypoint_metadata: Mapping[str, Any],
) -> Path:
    raw = Path(output_dir)
    if not raw.is_absolute():
        raw = root / raw
    resolved = raw.resolve()
    product_entrypoint = (
        entrypoint_metadata.get("entrypoint_kind") == PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND
    )
    allowed = (
        root / PRODUCT_SINGLE_FACT_OUTPUT_ROOT
        if product_entrypoint
        else root / DEFAULT_OUTPUT_DIR
    ).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        if product_entrypoint:
            raise ValueError(
                "product-supported current source-of-record single-fact output "
                "must stay under output/"
            ) from exc
        raise ValueError(
            "generic single-relation live dogfood output must stay under "
            "output/mvp_single_relation_live_dogfood_01/"
        ) from exc
    target = resolved / _clean_run_id(run_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _pytest_or_ci_guard(environ: Mapping[str, str] | None) -> bool:
    env = os.environ if environ is None else environ
    return bool(env.get("PYTEST_CURRENT_TEST") or env.get("CI") or env.get("GITHUB_ACTIONS"))


def _empty_counts() -> dict[str, Any]:
    return {
        "query_plans_consumed": 0,
        "fast_planner_calls_attempted": 0,
        "fast_planner_model_calls_attempted": 0,
        "fast_planner_model_calls_completed": 0,
        "initial_fast_model_planning_calls_attempted": 0,
        "initial_fast_model_planning_calls_completed": 0,
        "recovery_fast_model_planning_calls_attempted": 0,
        "recovery_fast_model_planning_calls_completed": 0,
        "model_assisted_planning_context_kinds": (),
        "product_provider_acquisition_adapter_used": 0,
        "serper_scout_calls_attempted": 0,
        "serper_scout_calls_completed": 0,
        "provider_calls_attempted": 0,
        "provider_calls_completed": 0,
        "extraction_provider_calls_attempted": 0,
        "extraction_provider_calls_completed": 0,
        "source_challenge_recovery_provider_calls_attempted": 0,
        "source_challenge_recovery_provider_calls_completed": 0,
        "source_challenge_recovery_provider_results_returned": 0,
        "search_tasks_attempted": 0,
        "search_tasks_completed": 0,
        "provider_results_returned": 0,
        "source_acquisition_mode": SOURCE_ACQUISITION_MODE_NONE,
        "provider_extracted_content_candidate_count": 0,
        "provider_extracted_content_handoff_created": 0,
        "direct_fetch_read_attempts": 0,
        "fetch_read_attempts": 0,
        "fetch_read_completed": 0,
        "fetch_read_blocker": None,
        "fetch_read_blocker_detail": None,
        "fetch_read_status_classes": (),
        "fetch_read_content_types": (),
        "fetch_read_failure_categories": (),
        "fetch_read_candidate_diagnostics": (),
        "fetch_read_attempt_diagnostics": (),
        "fetch_read_packet_created": 0,
        "analyst_workbench_bundle": {},
        "candidate_evidence_triage_packet_created": 0,
        "analyst_workbench_packet_created": 0,
        "analysis_gap_search_proposal_created": 0,
        "workbench_dprime_dossier_created": 0,
        "workbench_reduction_projection_created": 0,
        "evidence_ledger_admissions": 0,
        "dprime_model_review_calls_attempted": 0,
        "dprime_model_review_calls_completed": 0,
        "followup_loop_count": 0,
    }


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, Mapping):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "JSON artifact must be an object.",
        )
    return dict(decoded)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = []
    for key in sorted(keys):
        if key == "raw_private_retention_flags":
            flags = _safe_mapping(_first_normalized_key_value(value, key))
            if not flags or any(item is not False for item in flags.values()):
                forbidden.append(key)
            continue
        if key in _ALLOWED_RAW_FALSE_KEYS:
            if not _all_normalized_key_values_false(value, key):
                forbidden.append(key)
            continue
        if key in _FORBIDDEN_KEYS or key.startswith("raw_"):
            forbidden.append(key)
    if forbidden:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            f"{context} contains raw/private fields: " + ", ".join(forbidden),
        )
    findings = _private_value_findings(value)
    if findings:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            f"{context} contains private-looking values: "
            + "; ".join(_private_value_finding_summaries(findings)),
        )


def _private_value_markers(value: Any) -> set[str]:
    return {finding["marker"] for finding in _private_value_findings(value)}


def _private_value_findings(
    value: Any,
    *,
    path: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            findings.extend(
                _private_value_findings(
                    item,
                    path=(*path, _safe_path_component(key)),
                )
            )
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            findings.extend(
                _private_value_findings(item, path=(*path, f"[{index}]"))
            )
    elif isinstance(value, set | frozenset):
        for index, item in enumerate(sorted(value, key=str)):
            findings.extend(
                _private_value_findings(item, path=(*path, f"[{index}]"))
            )
    elif isinstance(value, str):
        if path and path[-1] == "provider_extracted_text":
            marker = (
                "private_prefix_sk"
                if redact_provider_extracted_source_text(value) != value
                else None
            )
        else:
            marker = _private_value_marker_class(value)
        if marker:
            findings.append(
                {
                    "path": _format_private_value_path(path),
                    "value_type": "str",
                    "marker": marker,
                    "category": "credential_shaped_private_value",
                }
            )
    return findings


def _private_value_finding_summaries(
    findings: Sequence[Mapping[str, str]],
) -> list[str]:
    return [
        (
            "private-looking value detected at "
            f"{finding.get('path') or '<root>'}; "
            f"type={finding.get('value_type') or 'unknown'}; "
            f"marker={finding.get('marker') or 'private_value'}; "
            f"category={finding.get('category') or 'private_value'}"
        )
        for finding in findings[:8]
    ]


def _private_value_marker_class(value: str) -> str | None:
    lowered = _credential_name_safe_value(value).casefold()
    marker_classes = (
        ("sk-", "private_prefix_sk"),
        ("authorization:", "authorization_header"),
        ("bearer ", "bearer_token"),
        ("api_key", "credential_key_name"),
        ("private_sentinel", "private_sentinel_marker"),
        ("provider_payload", "provider_payload_marker"),
        ("raw_prompt", "raw_prompt_marker"),
        ("raw_provider", "raw_provider_marker"),
        ("secret", "secret_keyword"),
    )
    for marker, marker_class in marker_classes:
        if marker in lowered:
            return marker_class
    return None


def _safe_path_component(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "<empty_key>"
    return re.sub(r"[^A-Za-z0-9_]+", "_", text)[:120] or "<key>"


def _format_private_value_path(path: Sequence[str]) -> str:
    if not path:
        return "<root>"
    out = ""
    for part in path:
        if part.startswith("["):
            out = f"{out}{part}" if out else part
        else:
            out = f"{out}.{part}" if out else part
    return out


def _credential_name_safe_value(value: str) -> str:
    text = value
    for name in _PUBLIC_CREDENTIAL_NAME_REFERENCES:
        text = re.sub(rf"\b{re.escape(name)}\b(?!\s*[:=])", "", text)
    return text


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


def _all_normalized_key_values_false(value: Any, normalized_key: str) -> bool:
    values = list(_normalized_key_values(value, normalized_key))
    return bool(values) and all(item is False for item in values)


def _normalized_key_values(value: Any, normalized_key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) == normalized_key:
                found.append(item)
            found.extend(_normalized_key_values(item, normalized_key))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.extend(_normalized_key_values(item, normalized_key))
    return found


def _first_normalized_key_value(value: Any, normalized_key: str) -> Any:
    values = _normalized_key_values(value, normalized_key)
    return values[0] if values else None


def _required_url(value: Any) -> str:
    url = _required_text(value, "provider result requires url", 700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "provider result requires http(s) url.",
        )
    return url


def _provider_url_and_source(raw: Mapping[str, Any]) -> tuple[str | None, str]:
    url = _clean_text(raw.get("url"), limit=700)
    if url:
        return url, "url"
    link = _clean_text(raw.get("link"), limit=700)
    if link:
        return link, "link"
    return None, "missing"


def _is_valid_http_url(value: Any) -> bool:
    url = _clean_text(value, limit=700)
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _required_text(value: Any, message: str, limit: int) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            message,
        )
    return text


def _positive_int(value: Any, message: str = "positive integer required") -> int:
    parsed = _bounded_int(value)
    if parsed <= 0:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            message,
        )
    return parsed


def _blocked_output_hygiene(detail: str) -> None:
    raise GenericSingleRelationLiveDogfoodRunError(
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
        detail,
    )


def _blocked_cap(detail: str) -> None:
    raise GenericSingleRelationLiveDogfoodRunError(
        BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_ENFORCEMENT,
        detail,
        caps_exhausted=True,
    )


def _provider_result_blocker(
    result: GenericProviderProxyRunResult,
    *,
    default: str,
) -> str:
    blocker = _clean_text(result.blocker, limit=220)
    if blocker == BLOCKED_GENERIC_PRODUCT_PROVIDER_ACQUISITION_ROUTE_UNAVAILABLE:
        return BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE
    return blocker or default


def _provider_result_detail(
    result: GenericProviderProxyRunResult,
    *,
    default: str,
) -> str:
    return _safe_detail_text(result.detail, limit=900) or default


def _safe_route_text(value: Any, *, limit: int) -> str | None:
    text = _clean_text(value, limit=limit)
    if not text:
        return None
    return PRIVATE_LOOKING_VALUE_REDACTION if _private_value_markers(text) else text


def _safe_detail_text(value: Any, *, limit: int) -> str | None:
    text = _clean_text(value, limit=limit)
    if not text:
        return None
    return _redact_private_text(text)


def _redact_private_text(value: Any) -> str:
    text = _clean_text(value, limit=900)
    if not text:
        return ""
    return PRIVATE_LOOKING_DETAIL_REDACTION if _private_value_markers(text) else text


def _redact_private_values(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _redact_private_values(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_redact_private_values(item) for item in value]
    if isinstance(value, str):
        return PRIVATE_LOOKING_VALUE_REDACTION if _private_value_markers(value) else value
    return value


class _RedirectLimiter(HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.redirects: list[dict[str, Any]] = []

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        if len(self.redirects) >= MAX_REDIRECTS:
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED,
                "fetch/read redirect cap exhausted.",
                caps_exhausted=True,
            )
        self.redirects.append(
            {
                "from_domain": urlparse(req.full_url).netloc.lower(),
                "to_domain": urlparse(newurl).netloc.lower(),
                "status_class": _status_class(code),
            }
        )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _ReadableTextExtractor(HTMLParser):
    _blocked_tags = {
        "canvas",
        "iframe",
        "noscript",
        "script",
        "style",
        "svg",
        "template",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._blocked_stack: list[str] = []
        self._title_stack = 0
        self.parts: list[str] = []
        self.title_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        normalized = tag.casefold()
        if normalized in self._blocked_tags:
            self._blocked_stack.append(normalized)
        if normalized == "title":
            self._title_stack += 1

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if self._blocked_stack and self._blocked_stack[-1] == normalized:
            self._blocked_stack.pop()
        elif normalized in self._blocked_tags and self._blocked_stack:
            self._blocked_stack.pop()
        if normalized == "title" and self._title_stack:
            self._title_stack -= 1

    def handle_data(self, data: str) -> None:
        text = _collapse_text(data)
        if not text:
            return
        if self._title_stack:
            self.title_parts.append(text)
        if not self._blocked_stack:
            self.parts.append(text)

    @property
    def readable_text(self) -> str:
        return _collapse_text(" ".join(self.parts))

    @property
    def title(self) -> str | None:
        return _clean_text(" ".join(self.title_parts), limit=300)


def _content_type_and_charset(header: str) -> tuple[str, str]:
    parts = [part.strip() for part in str(header or "").split(";") if part.strip()]
    content_type = parts[0].casefold() if parts else "text/html"
    charset = "utf-8"
    for part in parts[1:]:
        if part.casefold().startswith("charset="):
            charset = part.split("=", 1)[1].strip() or "utf-8"
    return content_type, charset


def _content_type_or_unknown(value: Any) -> str:
    return _sanitized_content_type(value) or FETCH_READ_UNKNOWN


def _sanitized_content_type(value: Any) -> str | None:
    text = _clean_text(value, limit=120)
    if not text:
        return None
    content_type = text.split(";", 1)[0].strip().casefold()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789!#$&^_.+-/")
    if not content_type or any(ch not in allowed for ch in content_type):
        return FETCH_READ_UNKNOWN
    if "/" not in content_type:
        return FETCH_READ_UNKNOWN
    return content_type


def _readable_content_type_value(value: Any) -> bool | str:
    content_type = _content_type_or_unknown(value)
    if content_type == FETCH_READ_UNKNOWN:
        return FETCH_READ_UNKNOWN
    return content_type in FETCH_READ_READABLE_CONTENT_TYPES


def _extract_readable_text(
    body: bytes,
    *,
    content_type: str,
    charset: str,
) -> tuple[str, str | None]:
    text = body.decode(charset or "utf-8", errors="replace")
    if content_type == "text/plain":
        return _collapse_text(text), None
    parser = _ReadableTextExtractor()
    parser.feed(text)
    parser.close()
    return parser.readable_text, parser.title


def _first_mapping(value: Any) -> dict[str, Any]:
    seq = _safe_sequence(value)
    return _safe_mapping(seq[0]) if seq else {}


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, parsed)


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "expected scalar text value.",
        )
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _clean_provider_extracted_source_text(value: Any) -> str | None:
    text = _clean_text(value, limit=PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS + 1)
    if text and len(text) > PROVIDER_EXTRACTED_SOURCE_TEXT_MAX_CHARS:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result extracted text exceeds source-text cap.",
        )
    return redact_provider_extracted_source_text(text) if text else None


def _clean_domain(value: Any) -> str | None:
    text = _clean_text(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _collapse_text(value: Any) -> str:
    decoded = unescape(str(value or ""))
    return " ".join(decoded.split())


def _status_class(status_code: int | None) -> str | None:
    if status_code is None:
        return None
    try:
        status = int(status_code)
    except (TypeError, ValueError):
        return None
    if not 100 <= status <= 599:
        return None
    return f"{status // 100}xx"


def _normalized_status_class(value: Any) -> str | None:
    text = _clean_text(value, limit=16)
    if not text:
        return None
    lowered = text.casefold()
    if lowered == FETCH_READ_UNKNOWN:
        return FETCH_READ_UNKNOWN
    if len(lowered) == 3 and lowered[0].isdigit() and lowered[1:] == "xx":
        return lowered
    return None


def _failure_category_for_status_class(status_class: Any) -> str:
    normalized = _normalized_status_class(status_class)
    if normalized == "4xx":
        return FETCH_READ_FAILURE_HTTP_4XX
    if normalized == "5xx":
        return FETCH_READ_FAILURE_HTTP_5XX
    return FETCH_READ_FAILURE_UNKNOWN


def _fetch_read_failure_category(value: Any) -> str:
    text = _clean_text(value, limit=80)
    if text in FETCH_READ_FAILURE_CATEGORIES:
        return text
    return FETCH_READ_FAILURE_UNKNOWN


def _status_class_summary(value: Any) -> dict[str, int]:
    classes = [
        status_class
        for status_class in (
            _normalized_status_class(item) for item in _safe_sequence(value)
        )
        if status_class
    ]
    return {
        status_class: classes.count(status_class)
        for status_class in sorted(set(classes))
    }


def _content_type_summary(value: Any) -> dict[str, int]:
    content_types = [
        content_type
        for content_type in (
            _content_type_or_unknown(item) for item in _safe_sequence(value)
        )
        if content_type
    ]
    return {
        content_type: content_types.count(content_type)
        for content_type in sorted(set(content_types))
    }


def _failure_category_summary(value: Any) -> dict[str, int]:
    categories = [
        category
        for category in (
            _fetch_read_failure_category(item) for item in _safe_sequence(value)
        )
        if category
    ]
    return {
        category: categories.count(category)
        for category in sorted(set(categories))
    }


def _official_artifact_candidate_count(value: Any) -> int:
    return sum(
        1
        for item in _safe_sequence(value)
        if _safe_mapping(item).get("official_pdf_or_table_artifact_candidate") is True
    )


def _official_artifact_read_support_status_summary(value: Any) -> dict[str, int]:
    statuses = [
        status
        for status in (
            _clean_text(
                _safe_mapping(item).get("official_artifact_read_support_status"),
                limit=120,
            )
            for item in _safe_sequence(value)
            if _safe_mapping(item).get("official_pdf_or_table_artifact_candidate")
            is True
        )
        if status
    ]
    return {status: statuses.count(status) for status in sorted(set(statuses))}


def _official_artifact_read_support_status_seen(value: Any, status: str) -> bool:
    return status in _official_artifact_read_support_status_summary(value)


def _bool_text(value: Any) -> str:
    return "true" if value is True else "false" if value is False else "unknown"


def _summary_text(value: Any) -> str:
    summary = _safe_mapping(value)
    if not summary:
        return "none"
    return ", ".join(f"{key}={summary[key]}" for key in sorted(summary))


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _clean_run_id(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-_:" else "-" for ch in value.strip())
    return text[:120] or f"mvp-single-relation-live-{uuid.uuid4().hex[:12]}"


def _run_id(value: str | None) -> str:
    return _clean_run_id(value) if value else f"mvp-single-relation-live-{uuid.uuid4().hex[:12]}"


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_ENFORCEMENT",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_CONTRACT_MISSING",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_NOT_LICENSED",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_OUTPUT_INVALID",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_EXTRACTION_PROVIDER_ROUTE_UNAVAILABLE",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OFFICIAL_HTTP_SOURCE_SURVIVAL_4XX",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_CREDENTIAL_UNAVAILABLE",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PROVIDER_ROUTE_UNAVAILABLE",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PATH_NOT_CONSUMED",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING",
    "BLOCKED_MODEL_ASSISTED_PLANNING_STRICT_MODEL_ROUTE_UNAVAILABLE",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_DPRIME_REREVIEW_NOT_LICENSED",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NOT_CONFIRMED",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_CHALLENGE_RECOVERY_NO_OFFICIAL_ANSWER_BEARING_MATERIAL",
    "BLOCKED_GENERIC_SINGLE_RELATION_SOURCE_OBLIGATION_RECOVERY_NOT_CONFIRMED",
    "BLOCKED_CURRENT_SOURCE_RECORD_FOLLOWUP_NOT_LICENSED",
    "BLOCKED_CURRENT_SOURCE_RECORD_RUN_NOT_CONTRACT_ACCOUNTABLE",
    "BLOCKED_SELECTED_VALUE_TO_FAP_CLAIM_TEXT_ADAPTER_MISSING",
    "BLOCKED_SINGLE_RELATION_DPRIME_AUTHORITY_INTEGRATION_TOO_BROAD",
    "CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG",
    "CONFIRM_LIVE_DOGFOOD_FLAG",
    "CURRENT_SOURCE_RECORD_SINGLE_FACT_REVIEW_REPORT_JSON_NAME",
    "CURRENT_SOURCE_RECORD_SINGLE_FACT_REVIEW_REPORT_MD_NAME",
    "DOGFOOD_ENTRYPOINT_KIND",
    "DOGFOOD_ENTRYPOINT_SURFACE",
    "DOGFOOD_SUPPORTED_QUERY_CLASS",
    "DPRIME_AUTHORITY_INTEGRATION_NEXT_PHASE",
    "DEFAULT_OUTPUT_DIR",
    "GenericLiveFetchReadResult",
    "GenericProviderProxyRunRequest",
    "GenericProviderProxyRunResult",
    "GenericSingleRelationLiveDogfoodRunError",
    "PROVIDER_EXTRACTED_CONTENT_CUSTODY_ADMISSION_BLOCKED",
    "PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND",
    "PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE",
    "PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS",
    "SOURCE_CITATION_DISPLAY_BOUNDARY_NEXT_PHASE",
    "WORKBENCH_GAP_REENTRY_REF_SCHEMA_VERSION",
    "build_generic_single_relation_live_dogfood_run_output",
    "fetch_public_url_once",
    "format_generic_single_relation_live_dogfood_output",
    "validate_generic_single_relation_live_dogfood_packet",
]
