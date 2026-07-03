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
import subprocess
import sys
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
)
from core.fetch_read_content_reference import (
    FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
    BoundedTextSelection,
    build_fetch_read_content_packet_from_candidate_packet,
    select_bounded_answer_bearing_text,
    validate_fetch_read_content_packet,
)
from core.generic_query_to_relation_planning import (
    GenericQueryRelationPlanningError,
    build_generic_query_relation_plan,
)
from core.mvp_supported_query_class_boundary import MVP_SUPPORTED_QUERY_CLASS_ID
from core.product_model_route_config import (
    CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
    MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
)
from core.search_result_candidate_packet import (
    SearchResultCandidatePacket,
    SearchResultCandidateRecord,
    validate_search_result_candidate_packet,
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

PHASE_NAME = "GENERIC-SINGLE-RELATION-LIVE-DOGFOOD-01"
SCHEMA_VERSION = "generic_single_relation_live_dogfood_v1"
MODE = "BUILD"
PASS_DECISION = "PASS"
CONFIRM_LIVE_DOGFOOD_FLAG = "--confirm-live-dogfood"

BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_TEST_OR_CI_GUARD = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_TEST_OR_CI_GUARD"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRIVATE_BROKER_UNAVAILABLE = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRIVATE_BROKER_UNAVAILABLE"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PROVIDER_PROXY_HELPER_MISSING = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PROVIDER_PROXY_HELPER_MISSING"
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
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_EXHAUSTED"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_ENFORCEMENT = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CAP_ENFORCEMENT"
)
BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE = (
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE"
)

DEFAULT_PROVIDER = "serper"
DEFAULT_OPERATION = "search"
DEFAULT_BROKER_URL = "http://127.0.0.1:8765/run"
DEFAULT_PRIVATE_BROKER_PATH = (
    Path.home() / "ScryRavenLiveBroker" / "scryraven_live_broker.py"
)
DEFAULT_PRIVATE_BROKER_ENV_FILE = Path.home() / "ScryRavenLiveBroker" / ".env"
DEFAULT_OUTPUT_DIR = Path("output") / "mvp_single_relation_live_dogfood_01"
SANITIZED_PROVIDER_PROXY_RESPONSE_NAME = "sanitized-provider-proxy-response.json"
LIVE_DOGFOOD_PACKET_NAME = "single_relation_live_dogfood_packet.json"

MAX_LIVE_RUNS = 1
MAX_QUERY_PLANS_CONSUMED = 1
MAX_PROVIDER_SEARCH_CALLS = 1
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
FETCH_READ_UNKNOWN = "unknown"
FETCH_READ_CAP_EXHAUSTED = "FETCH_READ_CAP_EXHAUSTED"
FETCH_READ_STOPPED_AFTER_SUCCESS = "READABLE_CONTENT_OBTAINED"
FETCH_READ_CANDIDATE_SELECTION_POLICY_ID = (
    "generic_single_relation_live_fetch_read_acquisition_priority_v1"
)
FETCH_READ_CANDIDATE_SELECTION_SCOPE = "local_fetch_read_acquisition_only"

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
)
_ALLOWED_PROVIDER_ENVELOPE_KEYS = frozenset(
    {
        "request_kind",
        "provider",
        "operation",
        "result_count",
        "results",
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
_PRIVATE_VALUE_MARKERS = frozenset(
    {
        "api_key",
        "authorization:",
        "bearer ",
        "private_sentinel",
        "provider_payload",
        "raw_prompt",
        "raw_provider",
        "secret",
        "sk-",
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


@dataclass(frozen=True, slots=True)
class GenericProviderProxyRunRequest:
    repo_root: Path
    output_path: Path
    query: str
    provider: str = DEFAULT_PROVIDER
    operation: str = DEFAULT_OPERATION
    max_results: int = MAX_PROVIDER_RESULTS
    broker_url: str = DEFAULT_BROKER_URL
    private_broker_path: Path = DEFAULT_PRIVATE_BROKER_PATH
    env_file_paths: tuple[Path, ...] = (DEFAULT_PRIVATE_BROKER_ENV_FILE,)


@dataclass(frozen=True, slots=True)
class GenericProviderProxyRunResult:
    return_code: int
    output_path: Path
    provider_calls_attempted: int
    provider_calls_completed: int


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


ProviderProxyRunner = Callable[
    [GenericProviderProxyRunRequest],
    GenericProviderProxyRunResult,
]
FetchReadRunner = Callable[[str], GenericLiveFetchReadResult]


def build_generic_single_relation_live_dogfood_run_output(
    *,
    query: str,
    repo_root: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    confirm_live_dogfood: bool = False,
    confirm_live_dprime_review: bool = False,
    broker_url: str = DEFAULT_BROKER_URL,
    private_broker_path: str | Path = DEFAULT_PRIVATE_BROKER_PATH,
    env_file_paths: Sequence[str | Path] | None = None,
    provider_proxy_runner: ProviderProxyRunner | None = None,
    fetch_read_runner: FetchReadRunner | None = None,
    smart_provider: str | None = None,
    smart_model: str | None = None,
    dprime_model_review_license: Mapping[str, Any] | None = None,
    dprime_model_review_callable: Callable[..., Any] | None = None,
    dprime_one_shot_provider_boundary: Mapping[str, Any] | None = None,
    dprime_one_shot_model_review_adapter: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> MvpFriendOutputResult:
    """Run one planned generic relation through bounded live dogfood."""

    root = Path(repo_root).resolve()
    run_id = _run_id(run_id)
    run_dir = _run_output_dir(root, output_dir or DEFAULT_OUTPUT_DIR, run_id)
    retained_root = run_dir / "retained_status_repo"
    provider_output_path = run_dir / SANITIZED_PROVIDER_PROXY_RESPONSE_NAME
    packet_path = run_dir / LIVE_DOGFOOD_PACKET_NAME
    counts = _empty_counts()
    relation_plan: dict[str, Any] | None = None
    semantic_payload: Mapping[str, Any] = {}

    try:
        relation_plan = build_generic_query_relation_plan(query)
        counts["query_plans_consumed"] = 1
        _guard_plan_for_live_acquisition(relation_plan)
        if not confirm_live_dogfood:
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_CONFIRMATION_REQUIRED,
                (
                    f"{CONFIRM_LIVE_DOGFOOD_FLAG} is required before live "
                    "provider/search/fetch/read contact."
                ),
            )
        _guard_dprime_review_route(
            confirm_live_dprime_review=confirm_live_dprime_review,
            dprime_model_review_callable=dprime_model_review_callable,
            dprime_one_shot_model_review_adapter=(
                dprime_one_shot_model_review_adapter
            ),
            environ=environ,
        )
        if provider_proxy_runner is None and _pytest_or_ci_guard(environ):
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_TEST_OR_CI_GUARD,
                "Default live provider runner is disabled under pytest/CI.",
            )

        search_query_seed = _search_query_seed(relation_plan)
        proxy_runner = provider_proxy_runner or run_provider_proxy_helper_once
        proxy_result = proxy_runner(
            GenericProviderProxyRunRequest(
                repo_root=root,
                output_path=provider_output_path,
                query=search_query_seed,
                broker_url=broker_url,
                private_broker_path=Path(private_broker_path),
                env_file_paths=_env_file_paths(env_file_paths),
            )
        )
        counts["provider_calls_attempted"] = proxy_result.provider_calls_attempted
        counts["provider_calls_completed"] = proxy_result.provider_calls_completed
        _enforce_caps(counts)
        if proxy_result.return_code != 0:
            raise GenericSingleRelationLiveDogfoodRunError(
                BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRIVATE_BROKER_UNAVAILABLE,
                "private broker/operator provider call did not complete.",
            )

        provider_payload = _load_sanitized_provider_output(proxy_result.output_path)
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
            provider_results=results,
            fetch_read_runner=fetch_read_runner or fetch_public_url_once,
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
        packet = _packet_from_semantic_status(
            relation_plan=relation_plan,
            run_id=run_id,
            retained_root=retained_root,
            counts=counts,
            semantic_payload=semantic_payload,
            status_decision=str(semantic_status.decision),
            confirm_live_dprime_review=confirm_live_dprime_review,
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
            caps_exhausted=False,
            confirm_live_dprime_review=confirm_live_dprime_review,
            semantic_payload={},
            hard_exclusion_category=exc.hard_exclusion_category,
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
            caps_exhausted=exc.caps_exhausted,
            confirm_live_dprime_review=confirm_live_dprime_review,
            semantic_payload=semantic_payload,
            hard_exclusion_category=None,
        )

    validate_generic_single_relation_live_dogfood_packet(packet)
    _write_json(packet_path, packet)
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


def run_provider_proxy_helper_once(
    request: GenericProviderProxyRunRequest,
) -> GenericProviderProxyRunResult:
    """Invoke the generic one-run provider-proxy helper without printing secrets."""

    helper = request.repo_root / "scripts" / "run_provider_proxy_broker_once.py"
    if not helper.is_file():
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PROVIDER_PROXY_HELPER_MISSING,
            "provider-proxy helper script is missing.",
        )
    command = [
        sys.executable,
        str(helper),
        "--provider",
        request.provider,
        "--operation",
        request.operation,
        "--query",
        request.query,
        "--max-results",
        str(request.max_results),
        "--output",
        str(request.output_path),
        "--broker-url",
        request.broker_url,
        "--private-broker-path",
        str(request.private_broker_path),
        "--confirm-provider-call",
    ]
    for env_file in request.env_file_paths:
        command.extend(["--env-file", str(env_file)])
    completed = subprocess.run(
        command,
        cwd=request.repo_root,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return GenericProviderProxyRunResult(
        return_code=completed.returncode,
        output_path=request.output_path,
        provider_calls_attempted=1,
        provider_calls_completed=1 if completed.returncode == 0 else 0,
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
    request = Request(
        url,
        headers={
            "User-Agent": (
                "ScryRaven generic single-relation live dogfood "
                "(sanitized bounded readability check)"
            ),
        },
        method="GET",
    )
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
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            f"fetch/read HTTP error status class {status_class}.",
            fetch_status_class=status_class,
            fetch_content_type=content_type,
            fetch_readable_content_type=_readable_content_type_value(content_type),
            fetch_readable_text_obtained=False,
            fetch_failure_category=_failure_category_for_status_class(status_class),
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
    for key, expected in RAW_FALSE_FLAGS.items():
        if safe.get(key) is not expected:
            _blocked_output_hygiene(f"generic live packet must keep {key}=false.")
    for key, expected in CLOSED_FALSE_FLAGS.items():
        if safe.get(key) is not expected:
            _blocked_output_hygiene(f"generic live packet must keep {key}=false.")
    if _bounded_int(safe.get("live_runs_attempted")) > MAX_LIVE_RUNS:
        _blocked_cap("live run cap exceeded.")
    if _bounded_int(safe.get("query_plans_consumed")) > MAX_QUERY_PLANS_CONSUMED:
        _blocked_cap("query plan consumption cap exceeded.")
    if _bounded_int(safe.get("provider_calls_attempted")) > MAX_PROVIDER_SEARCH_CALLS:
        _blocked_cap("provider/search call cap exceeded.")
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
            "fetch_read_attempts",
            "fetch_read_completed",
            "dprime_model_review_calls_attempted",
            "dprime_model_review_calls_completed",
        ):
            if _bounded_int(safe.get(count_key)) != 0:
                _blocked_output_hygiene("unsupported query made live/model calls.")
    if safe.get("answer_text_present") is True and safe.get("decision") != PASS_DECISION:
        _blocked_output_hygiene("blocked packet must not expose answer text.")
    _validate_fetch_read_observability(safe)
    _reject_forbidden_material(safe, context="generic live dogfood packet")
    return safe


def _validate_fetch_read_observability(packet: Mapping[str, Any]) -> None:
    for key in (
        "candidate_diagnostics_observability_only",
        "provider_snippets_used_as_evidence",
        "candidate_diagnostics_satisfy_source_obligations",
        "fetch_read_failure_metadata_citation_eligible",
        "fetch_read_failure_metadata_satisfies_source_obligations",
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
    ):
        expected = key == "candidate_diagnostics_observability_only"
        if packet.get(key) is not expected:
            _blocked_output_hygiene(f"generic live packet {key} posture invalid.")
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
        "candidate_diagnostic_satisfies_source_obligation",
        "fetch_read_failure_metadata_citation_eligible",
    ):
        if diagnostic.get(key) is not False:
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
    ):
        if diagnostic.get(key) is not False:
            _blocked_output_hygiene(f"candidate diagnostic requires {key}=false.")
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
    ):
        if diagnostic.get(key) is not False:
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
    ):
        if diagnostic.get(key) is not False:
            _blocked_output_hygiene(f"fetch/read diagnostic requires {key}=false.")
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

    sources = _source_display_entries(packet)
    relation_status = _safe_mapping(packet.get("dprime_relation_intake_ref")).get(
        "status",
        "not reached",
    )
    lines = [
        "ScryRaven generic single-relation live dogfood run",
        f"Question: {_clean_text(packet.get('query'), limit=500)}",
        f"Decision: {packet.get('decision')}",
        "",
        "Plan",
        f"- Relation plan consumed: {_bool_text(packet.get('relation_plan_consumed'))}",
        f"- Relation plan id: {packet.get('relation_plan_id') or 'not created'}",
        f"- Component: {packet.get('component_text') or 'not created'}",
        f"- Search seed used: {packet.get('search_query_seed_used') or 'not used'}",
        "",
        "Answer",
        _clean_text(packet.get("answer_or_blocker_text"), limit=1_400)
        or "No answer text is available.",
        "",
        "Sources",
    ]
    if sources:
        lines.extend(f"- {entry}" for entry in sources)
    else:
        lines.append("- No source display is available yet.")
    lines.extend(
        [
            "",
            "Status",
            f"- Provider calls: {packet.get('provider_calls_attempted')}/"
            f"{packet.get('provider_calls_completed')}",
            f"- Fetch/read: {packet.get('fetch_read_attempts')}/"
            f"{packet.get('fetch_read_completed')}",
            f"- EvidenceLedger admissions: {packet.get('evidence_ledger_admissions')}",
            f"- D-prime relation intake: {relation_status}",
            f"- D-prime/model calls: {packet.get('dprime_model_review_calls_attempted')}/"
            f"{packet.get('dprime_model_review_calls_completed')}",
            "",
            "Caveats",
            "- Product correctness claimed: false.",
            "- Friend-level/general MVP claimed: false.",
            "- FAP/Author opened: false.",
            "- Multi-component planning opened: false.",
            "- Raw/private retained: false.",
            "- Fake-provider offline PASS is not live validation PASS.",
            f"- Review packet: {_display_path(packet_path)}",
        ]
    )
    return "\n".join(lines)


def _packet_from_semantic_status(
    *,
    relation_plan: Mapping[str, Any],
    run_id: str,
    retained_root: Path,
    counts: Mapping[str, Any],
    semantic_payload: Mapping[str, Any],
    status_decision: str,
    confirm_live_dprime_review: bool,
) -> dict[str, Any]:
    decision = _mapped_live_decision(
        status_decision,
        model_review_licensed=confirm_live_dprime_review,
    )
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
        confirm_live_dprime_review=confirm_live_dprime_review,
        caps_exhausted=False,
        semantic_payload=semantic_payload,
    )
    answer_text = _answer_text_from_semantic_payload(semantic_payload)
    source_entries = _source_entries_from_semantic_payload(semantic_payload)
    packet.update(
        {
            "decision": decision,
            "status_decision": status_decision,
            "blocker_code": None if decision == PASS_DECISION else decision,
            "blocker_detail": None if decision == PASS_DECISION else blocker_detail,
            "answer_or_blocker_text": (
                _friend_answer_from_semantic_payload(semantic_payload)
                if decision == PASS_DECISION
                else f"Blocked before answer: {decision}. {blocker_detail}".strip()
            ),
            "product_answer_text": answer_text if decision == PASS_DECISION else "",
            "answer_text_present": bool(answer_text) and decision == PASS_DECISION,
            "source_display_entries": source_entries if decision == PASS_DECISION else [],
            "decision_made_by_the_run": (
                "generic_single_relation_live_dogfood_answer_or_source_display_consumed"
                if decision == PASS_DECISION
                else "generic_single_relation_live_dogfood_named_blocker_recorded"
            ),
        }
    )
    return packet


def _blocked_packet(
    *,
    blocker: str,
    detail: str,
    query_retained: bool,
    relation_plan: Mapping[str, Any] | None,
    run_id: str,
    retained_root: Path | None,
    counts: Mapping[str, Any],
    caps_exhausted: bool,
    confirm_live_dprime_review: bool,
    semantic_payload: Mapping[str, Any],
    hard_exclusion_category: str | None,
) -> dict[str, Any]:
    packet = _base_packet(
        relation_plan=relation_plan,
        query_retained=query_retained,
        run_id=run_id,
        retained_root=retained_root,
        counts=counts,
        confirm_live_dprime_review=confirm_live_dprime_review,
        caps_exhausted=caps_exhausted,
        semantic_payload=semantic_payload,
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
            "decision_made_by_the_run": (
                "generic_single_relation_live_dogfood_blocker_recorded"
            ),
        }
    )
    return packet


def _base_packet(
    *,
    relation_plan: Mapping[str, Any] | None,
    query_retained: bool,
    run_id: str,
    retained_root: Path | None,
    counts: Mapping[str, Any],
    confirm_live_dprime_review: bool,
    caps_exhausted: bool,
    semantic_payload: Mapping[str, Any],
) -> dict[str, Any]:
    plan = _safe_mapping(relation_plan)
    requirement = _safe_mapping(plan.get("source_authority_posture_requirement"))
    search_requirement = _first_mapping(plan.get("search_requirements"))
    source_obligation = _first_mapping(plan.get("source_obligations"))
    dprime_candidate = _safe_mapping(plan.get("dprime_relation_intake_candidate"))
    future_node = _safe_mapping(plan.get("future_component_work_node_candidate"))
    semantic = _safe_mapping(semantic_payload)
    relation_ref = _safe_mapping(semantic.get("dprime_relation_intake_ref"))
    query_text = (
        _clean_text(plan.get("sanitized_query"), limit=500)
        if query_retained and plan
        else "unsupported query (not retained)"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_name": PHASE_NAME,
        "mode": MODE,
        "ordinary_entrypoint": "python -m proplex",
        "command_flag": MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
        "status_flag": MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
        "command_harness_used": _command_harness(confirm_live_dprime_review),
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
        "component_id": plan.get("component_id"),
        "component_text": plan.get("component_text"),
        "source_obligation_id": plan.get("source_obligation_id"),
        "source_obligation_text": plan.get("source_obligation_text"),
        "source_obligation_ref": source_obligation,
        "search_requirement_id": plan.get("search_requirement_id"),
        "search_requirement_text": plan.get("search_requirement_text"),
        "search_requirement_ref": search_requirement,
        "search_query_seeds": list(_safe_sequence(plan.get("search_query_seeds"))),
        "search_query_seed_used": _search_query_seed(plan) if plan else None,
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
        "provider_broker_posture": (
            "generic_provider_proxy_broker_sanitized_results_to_plan_"
            "derived_retained_artifacts"
            if counts.get("provider_calls_attempted", 0)
            else "blocked_before_provider_search"
        ),
        "live_runs_attempted": 1 if counts.get("provider_calls_attempted", 0) else 0,
        "query_plans_consumed": counts.get("query_plans_consumed", 0),
        "provider_calls_attempted": counts.get("provider_calls_attempted", 0),
        "provider_calls_completed": counts.get("provider_calls_completed", 0),
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
        "candidate_diagnostics_observability_only": True,
        "candidate_diagnostics_satisfy_source_obligations": False,
        "provider_snippets_used_as_evidence": False,
        "fetch_read_failure_metadata_citation_eligible": False,
        "fetch_read_failure_metadata_satisfies_source_obligations": False,
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


def _candidate_packet_from_provider_results(
    *,
    relation_plan: Mapping[str, Any],
    run_id: str,
    results: Sequence[Mapping[str, Any]],
    provider_calls_attempted: int,
    provider_calls_completed: int,
    search_query_seed: str,
) -> dict[str, Any]:
    contract_ref = _contract_ref_from_plan(relation_plan)
    handoff_ref = _handoff_ref_from_plan(relation_plan, contract_ref=contract_ref)
    request_id = f"request:{run_id}"
    validation_ref = {
        "validation_id": f"validation:{run_id}",
        "candidate_count": len(results),
        "relation_plan_id": relation_plan.get("plan_id"),
        "search_query_seed_used": search_query_seed,
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
                provider_authorized=DEFAULT_PROVIDER,
                provider_used=str(result.get("provider") or DEFAULT_PROVIDER),
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
        provider_authorized=DEFAULT_PROVIDER,
        provider_used=DEFAULT_PROVIDER,
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
    provider_results: Sequence[Mapping[str, Any]],
    fetch_read_runner: FetchReadRunner,
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
            )
            attempt_diagnostics.append(attempt_diagnostic)
            _apply_attempt_diagnostic(candidate_diagnostics, attempt_diagnostic)
            _mark_unattempted_candidates_skipped_after_success(candidate_diagnostics)
            return fetch_packet, {
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
                "fetch_read_candidate_diagnostics": tuple(candidate_diagnostics),
                "fetch_read_attempt_diagnostics": tuple(attempt_diagnostics),
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
    return None, {
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
        return 2 if features.get("pdf_url_or_title_signal") is True else 1
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
        url = _clean_text(result.get("url"), limit=700)
        url_source = _clean_text(result.get("url_source"), limit=20) or "missing"
        url_valid = _is_valid_http_url(url)
        selected_for_fetch_read = (
            url_valid and 0 < priority_rank <= MAX_FETCH_READ_ATTEMPTS
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
                "selected_for_fetch_read": selected_for_fetch_read,
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
    return {
        "candidate_id": _clean_text(candidate.get("candidate_id"), limit=320),
        "attempt_index": attempt_index,
        "attempted_url": attempted_url,
        "attempted_domain": _clean_domain(candidate.get("domain"))
        or (urlparse(attempted_url).netloc.lower() if attempted_url else None),
        "provider_rank": _bounded_int(candidate.get("result_rank"), default=0),
        "result_rank": _bounded_int(candidate.get("result_rank"), default=0),
        "fetch_read_priority_rank": _bounded_int(
            candidate.get("fetch_read_priority_rank"),
            default=0,
        ),
        "candidate_selection_policy_id": FETCH_READ_CANDIDATE_SELECTION_POLICY_ID,
        "candidate_selection_policy_scope": FETCH_READ_CANDIDATE_SELECTION_SCOPE,
        "candidate_selection_is_acquisition_only": True,
        "candidate_selection_created_source_authority": False,
        "candidate_selection_satisfies_source_obligation": False,
        "candidate_selection_citation_eligible": False,
        "candidate_selection_claims_correctness": False,
        "candidate_selection_features": _safe_mapping(
            candidate.get("candidate_selection_features")
        ),
        "http_status_class": status_class,
        "content_type": content_type,
        "readable_content_type": readable_content_type,
        "readable_text_obtained": readable_text_obtained,
        "failure_category": failure_category,
        "diagnostic_posture": "observability_only",
        "not_evidence": True,
        "not_citation_eligible": True,
        "not_source_obligation_satisfaction": True,
        "candidate_diagnostics_satisfy_source_obligations": False,
        "fetch_read_failure_metadata_citation_eligible": False,
        "raw_private_retention_flags": dict(RAW_FALSE_FLAGS),
    }


def _apply_attempt_diagnostic(
    candidate_diagnostics: list[dict[str, Any]],
    attempt_diagnostic: Mapping[str, Any],
) -> None:
    candidate_id = _clean_text(attempt_diagnostic.get("candidate_id"), limit=320)
    for diagnostic in candidate_diagnostics:
        if diagnostic.get("candidate_id") != candidate_id:
            continue
        diagnostic["selected_for_fetch_read"] = True
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
        diagnostic["failure_category"] = attempt_diagnostic.get("failure_category")
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


def _fetch_read_material(
    *,
    candidate: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
    fetch_result: GenericLiveFetchReadResult,
    selection: BoundedTextSelection,
) -> dict[str, Any]:
    bounded_text = selection.bounded_text
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
        "content_type": fetch_result.content_type,
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
        "raw_page_content_retained": False,
        "raw_page_text_retained": False,
        "raw_headers_retained": False,
        "raw_prompt_retained": False,
    }


def _fetch_summary(fetch_packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision": PASS_DECISION,
        "readable_content_handoff_created": True,
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
        )
    content_type = _content_type_or_unknown(fetch_result.content_type)
    readable_content_type = _readable_content_type_value(content_type)
    if readable_content_type is False:
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


def _bounded_plan_text_selection(
    text: str,
    *,
    relation_plan: Mapping[str, Any],
) -> BoundedTextSelection:
    return select_bounded_answer_bearing_text(
        text,
        max_chars=FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
        required_or_preferred_anchors=_generic_anchor_groups(relation_plan),
        component_text=_clean_text(relation_plan.get("component_text"), limit=260),
        claim_under_test=_clean_text(relation_plan.get("claim_under_test"), limit=500),
    )


def _generic_anchor_groups(relation_plan: Mapping[str, Any]) -> list[tuple[str, ...]]:
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
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PATH_NOT_CONSUMED:
        return (
            "The D-prime review was licensed, but the existing product path did "
            f"not produce answer/source-display output; status decision: {status_decision}. "
            f"{original_detail}"
        ).strip()
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE:
        return (
            "The explicit D-prime review route failed closed before producing a "
            f"validated support proposal; status decision: {status_decision}. "
            f"{original_detail}"
        ).strip()
    if decision == BLOCKED_GENERIC_SINGLE_RELATION_LIVE_DPRIME_REVIEW_OUTPUT_INVALID:
        return (
            "The explicit D-prime review route made one attempt, but the model "
            f"review output was invalid; status decision: {status_decision}. "
            f"{original_detail}"
        ).strip()
    if model_review_licensed and original_detail:
        return original_detail
    return original_detail or f"underlying status decision: {status_decision}."


def _load_sanitized_provider_output(path: Path) -> dict[str, Any]:
    try:
        decoded = _read_json(path)
    except FileNotFoundError as exc:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRIVATE_BROKER_UNAVAILABLE,
            "sanitized provider proxy response was not written.",
        ) from exc
    return _validate_provider_payload(decoded)


def _validate_provider_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = _safe_mapping(payload)
    _reject_forbidden_material(raw, context="sanitized provider response")
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
    _reject_forbidden_material(raw, context="sanitized provider result")
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


def _answer_text_from_semantic_payload(payload: Mapping[str, Any]) -> str | None:
    answer_path = _safe_mapping(payload.get("dprime_answer_path_ref"))
    return _clean_text(answer_path.get("answer_text"), limit=2_000)


def _friend_answer_from_semantic_payload(payload: Mapping[str, Any]) -> str | None:
    answer_path = _safe_mapping(payload.get("dprime_answer_path_ref"))
    dprime = _safe_mapping(payload.get("dprime_status"))
    material = _safe_mapping(dprime.get("assessment_material_ref"))
    claim = _clean_text(
        _safe_mapping(material.get("answer_component_claim")).get("claim"),
        limit=1_000,
    )
    return claim or _clean_text(answer_path.get("answer_text"), limit=2_000)


def _source_entries_from_semantic_payload(
    payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    answer_path = _safe_mapping(payload.get("dprime_answer_path_ref"))
    display = _safe_mapping(answer_path.get("citation_source_display"))
    entries = []
    for entry in display.get("citation_source_entries") or []:
        safe = _safe_mapping(entry)
        text = _clean_text(safe.get("display_text"), limit=700)
        if text:
            entries.append(
                {
                    "display_text": text,
                    "url": _clean_text(safe.get("url"), limit=700),
                    "domain": _clean_text(safe.get("domain"), limit=260),
                    "product_correctness_claimed": False,
                }
            )
    return entries


def _source_display_entries(packet: Mapping[str, Any]) -> list[str]:
    return [
        str(entry.get("display_text"))
        for entry in packet.get("source_display_entries") or []
        if isinstance(entry, Mapping) and entry.get("display_text")
    ]


def _actual_source_authority_posture_created(payload: Mapping[str, Any]) -> bool:
    posture = _safe_mapping(payload.get("source_authority_posture_ref"))
    return posture.get("phase") == "ANALYST-SOURCE-AUTHORITY-POSTURE-PACKET-01"


def _enforce_caps(counts: Mapping[str, int]) -> None:
    checks = (
        ("query_plans_consumed", MAX_QUERY_PLANS_CONSUMED, "query plan"),
        ("provider_calls_attempted", MAX_PROVIDER_SEARCH_CALLS, "provider/search"),
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
        "max_provider_search_calls": MAX_PROVIDER_SEARCH_CALLS,
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
    safe = _json_safe(payload)
    _reject_forbidden_material(safe, context="generic live semantic status payload")
    return _safe_mapping(safe)


def _command_harness(confirm_live_dprime_review: bool) -> str:
    command = (
        f"python -m proplex {MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG} "
        f"{CONFIRM_LIVE_DOGFOOD_FLAG}"
    )
    if confirm_live_dprime_review:
        command = f"{command} {CONFIRM_LIVE_DPRIME_REVIEW_FLAG}"
    return command


def _run_output_dir(root: Path, output_dir: str | Path, run_id: str) -> Path:
    raw = Path(output_dir)
    if not raw.is_absolute():
        raw = root / raw
    resolved = raw.resolve()
    allowed = (root / DEFAULT_OUTPUT_DIR).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise ValueError(
            "generic single-relation live dogfood output must stay under "
            "output/mvp_single_relation_live_dogfood_01/"
        ) from exc
    target = resolved / _clean_run_id(run_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _env_file_paths(values: Sequence[str | Path] | None) -> tuple[Path, ...]:
    if values is None:
        return (DEFAULT_PRIVATE_BROKER_ENV_FILE,)
    return tuple(Path(value) for value in values)


def _pytest_or_ci_guard(environ: Mapping[str, str] | None) -> bool:
    env = os.environ if environ is None else environ
    return bool(env.get("PYTEST_CURRENT_TEST") or env.get("CI") or env.get("GITHUB_ACTIONS"))


def _empty_counts() -> dict[str, Any]:
    return {
        "query_plans_consumed": 0,
        "provider_calls_attempted": 0,
        "provider_calls_completed": 0,
        "search_tasks_attempted": 0,
        "search_tasks_completed": 0,
        "provider_results_returned": 0,
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
    markers = sorted(_private_value_markers(value))
    if markers:
        raise GenericSingleRelationLiveDogfoodRunError(
            BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE,
            f"{context} contains private-looking values: " + ", ".join(markers),
        )


def _private_value_markers(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            found.update(_private_value_markers(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_private_value_markers(item))
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in _PRIVATE_VALUE_MARKERS:
            if marker in lowered:
                found.add(marker)
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


def _bool_text(value: Any) -> str:
    return "true" if value is True else "false" if value is False else "unknown"


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
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ALL_CANDIDATES_4XX",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_CANDIDATE_CONTRACT_MISSING",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_NO_READABLE_CANDIDATES",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_OBSERVABILITY_INSUFFICIENT",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_OUTPUT_HYGIENE",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PLAN_TO_ACQUISITION_SEAM",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRIVATE_BROKER_UNAVAILABLE",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PRODUCT_PATH_NOT_CONSUMED",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_PROVIDER_PROXY_HELPER_MISSING",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING",
    "BLOCKED_GENERIC_SINGLE_RELATION_LIVE_TEST_OR_CI_GUARD",
    "CONFIRM_LIVE_DOGFOOD_FLAG",
    "DEFAULT_OUTPUT_DIR",
    "GenericLiveFetchReadResult",
    "GenericProviderProxyRunRequest",
    "GenericProviderProxyRunResult",
    "GenericSingleRelationLiveDogfoodRunError",
    "build_generic_single_relation_live_dogfood_run_output",
    "fetch_public_url_once",
    "format_generic_single_relation_live_dogfood_output",
    "run_provider_proxy_helper_once",
    "validate_generic_single_relation_live_dogfood_packet",
]
