"""Default-off live dogfood entrypoint for the fixed MVP query.

This module repairs the narrow bridge from one licensed brokered provider
search to retained sanitized artifacts consumed by the existing MVP live status
path. It does not broaden query planning, provider routing, model routing, or
product correctness claims.
"""

from __future__ import annotations

import json
import os
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
from core.live_ordinary_candidate_handoff_runtime import (
    execute_ordinary_live_candidate_handoff,
)
from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
)
from core.mvp_supported_query_class_boundary import (
    build_mvp_supported_query_class_boundary_status,
    validate_mvp_supported_query_class_boundary_status,
)
from core.product_model_route_config import (
    CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
)
from core.run_kernel import RunKernel
from core.search_result_candidate_packet import validate_search_result_candidate_packet
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
from proplex.mvp_friend_shareable_output import (
    DEFAULT_MVP_LIVE_OUTPUT_DIR,
    DEFAULT_MVP_QUERY,
    MVP_COMPONENT_ID,
    MVP_SOURCE_OBLIGATION_ID,
    MvpFriendOutputResult,
    build_mvp_live_dogfood_status_output,
    build_mvp_live_dogfood_status_output_from_semantic_status,
    format_mvp_friend_output,
)
from proplex.mvp_friend_shareable_output import (
    EXPLICIT_NON_PROOFS as MVP_STATUS_NON_PROOFS,
)

PHASE_NAME = "MVP-LIVE-DPRIME-REVIEW-ENTRYPOINT-01"
MODE = "REPAIR"
PASS_DECISION = "PASS"
CONFIRM_LIVE_DOGFOOD_FLAG = "--confirm-live-dogfood"

BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED = "BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED"
BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED = (
    "BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED"
)
BLOCKED_MVP_LIVE_TEST_OR_CI_GUARD = "BLOCKED_MVP_LIVE_TEST_OR_CI_GUARD"
BLOCKED_MVP_LIVE_GENERIC_BROKER_UNAVAILABLE = (
    "BLOCKED_MVP_LIVE_GENERIC_BROKER_UNAVAILABLE"
)
BLOCKED_MVP_LIVE_PROVIDER_PROXY_HELPER_MISSING = (
    "BLOCKED_MVP_LIVE_PROVIDER_PROXY_HELPER_MISSING"
)
BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING = (
    "BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING"
)
BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING = (
    "BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING"
)
BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING = (
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING"
)
BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE = (
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE"
)
BLOCKED_MVP_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED = (
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED"
)
BLOCKED_MVP_LIVE_DPRIME_REVIEW_OUTPUT_INVALID = (
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_OUTPUT_INVALID"
)
BLOCKED_MVP_LIVE_MODEL_ROUTE_SECRET_BOUNDARY = (
    "BLOCKED_MVP_LIVE_MODEL_ROUTE_SECRET_BOUNDARY"
)
BLOCKED_MVP_LIVE_PRODUCT_PATH_NOT_CONSUMED = (
    "BLOCKED_MVP_LIVE_PRODUCT_PATH_NOT_CONSUMED"
)
BLOCKED_MVP_LIVE_OUTPUT_HYGIENE = "BLOCKED_MVP_LIVE_OUTPUT_HYGIENE"
BLOCKED_MVP_LIVE_CAP_EXHAUSTED = "BLOCKED_MVP_LIVE_CAP_EXHAUSTED"

DEFAULT_PROVIDER = "serper"
DEFAULT_OPERATION = "search.query"
EXPECTED_SEARCH_SCHEMA_VERSION = "2"
EXPECTED_SEARCH_PROOF_KIND = "scryraven_search_query_proof_v2"
EXPECTED_SEARCH_COST_CEILING_USD = "0.05"
DEFAULT_BROKER_URL = "http://127.0.0.1:8765/run"
SANITIZED_PROVIDER_PROXY_RESPONSE_NAME = "sanitized-provider-proxy-response.json"
LIVE_DOGFOOD_PACKET_NAME = "live_dogfood_packet.json"

MAX_SEARCH_TASKS = 2
MAX_PROVIDER_SEARCH_CALLS = 1
MAX_PROVIDER_RESULTS = 5
MAX_FETCH_READ_ATTEMPTS = 3
MAX_EVIDENCE_LEDGER_ADMISSIONS = 3
MAX_DPRIME_MODEL_REVIEW_CALLS = 1
MAX_FOLLOWUP_LOOPS = 0
MAX_FETCHED_BYTES = 1_048_576
MAX_REDIRECTS = 2

MVP_SEARCH_REQUIREMENT_ID = "searchreq:mvp-live-dogfood-passport-fee"
TARGET_COMPONENT_TEXT = "adult U.S. passport book renewal fee by mail"
TARGET_COMPONENT_CLAIM_UNDER_TEST = (
    "current adult U.S. passport book renewal fee by mail"
)
TARGET_ANCHOR_GROUPS = (
    ("adult", "age 16", "16 and older"),
    ("passport",),
    ("book",),
    ("renew", "renewal"),
    ("mail",),
    ("fee",),
)

RAW_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
}
EXPLICIT_NON_PROOFS = (
    "product correctness",
    "arbitrary query planning",
    "supported query-class expansion",
    "independent external source checking",
    "provider/model routing changes",
    "Economist routing",
    "Specialist routing",
    "new Scrutineer remediation",
    "old Author execution",
)
_ALLOWED_PROVIDER_ENVELOPE_KEYS = frozenset(
    {
        "schema_version",
        "proof_kind",
        "provider",
        "operation",
        "status",
        "result_count",
        "results",
        "physical_attempt_count",
        "provider_elapsed_milliseconds_total",
        "caller_authorized_cost_ceiling_usd",
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
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
        "provider",
        "operation",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
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
        "serper_api_key",
        "serper_payload",
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
        "raw_private_retention",
        "raw_prompt_retention",
        "raw_prompt_retained",
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
        "raw_search_response_retained",
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
        "raw_private",
        "raw_prompt",
        "raw_provider",
        "secret",
        "sk-",
    }
)


class MvpLiveDogfoodRunError(ValueError):
    """Raised when the live dogfood run must fail closed."""

    def __init__(
        self,
        blocker: str,
        detail: str,
        *,
        caps_exhausted: bool = False,
    ) -> None:
        super().__init__(detail)
        self.blocker = blocker
        self.detail = detail
        self.caps_exhausted = caps_exhausted


@dataclass(frozen=True, slots=True)
class ProviderProxyRunRequest:
    repo_root: Path
    output_path: Path
    query: str
    provider: str = DEFAULT_PROVIDER
    operation: str = DEFAULT_OPERATION
    max_results: int = MAX_PROVIDER_RESULTS
    broker_url: str = DEFAULT_BROKER_URL
    env_file_paths: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderProxyRunResult:
    return_code: int
    output_path: Path
    provider_calls_attempted: int
    provider_calls_completed: int


@dataclass(frozen=True, slots=True)
class LiveDogfoodFetchReadResult:
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


ProviderProxyRunner = Callable[[ProviderProxyRunRequest], ProviderProxyRunResult]
FetchReadRunner = Callable[[str], LiveDogfoodFetchReadResult]


def build_mvp_live_dogfood_run_output(
    *,
    query: str = DEFAULT_MVP_QUERY,
    repo_root: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    confirm_live_dogfood: bool = False,
    confirm_live_dprime_review: bool = False,
    broker_url: str = DEFAULT_BROKER_URL,
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
    """Run the fixed live dogfood flow and consume the existing status path."""

    root = Path(repo_root).resolve()
    normalized_query = _normalize_query(query)
    run_id = _run_id(run_id)
    run_dir = _run_output_dir(
        root,
        output_dir or DEFAULT_MVP_LIVE_OUTPUT_DIR,
        run_id,
    )
    retained_root = run_dir / "retained_status_repo"
    provider_output_path = run_dir / SANITIZED_PROVIDER_PROXY_RESPONSE_NAME
    packet_path = run_dir / LIVE_DOGFOOD_PACKET_NAME
    counts = _empty_counts()

    try:
        if not confirm_live_dogfood:
            raise MvpLiveDogfoodRunError(
                BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED,
                f"{CONFIRM_LIVE_DOGFOOD_FLAG} is required for live dogfood.",
            )
        if normalized_query != DEFAULT_MVP_QUERY:
            raise MvpLiveDogfoodRunError(
                BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED,
                "Only the fixed licensed live dogfood query is supported.",
            )
        _guard_dprime_review_route(
            confirm_live_dprime_review=confirm_live_dprime_review,
            dprime_model_review_callable=dprime_model_review_callable,
            dprime_one_shot_model_review_adapter=dprime_one_shot_model_review_adapter,
            environ=environ,
        )
        if provider_proxy_runner is None and _pytest_or_ci_guard(environ):
            raise MvpLiveDogfoodRunError(
                BLOCKED_MVP_LIVE_TEST_OR_CI_GUARD,
                "Default live provider runner is disabled under pytest/CI.",
            )

        proxy_runner = provider_proxy_runner or run_provider_proxy_helper_once
        proxy_result = proxy_runner(
            ProviderProxyRunRequest(
                repo_root=root,
                output_path=provider_output_path,
                query=normalized_query,
                broker_url=broker_url,
                env_file_paths=_env_file_paths(env_file_paths),
            )
        )
        counts["provider_calls_attempted"] = proxy_result.provider_calls_attempted
        counts["provider_calls_completed"] = proxy_result.provider_calls_completed
        if proxy_result.return_code != 0:
            raise MvpLiveDogfoodRunError(
                BLOCKED_MVP_LIVE_GENERIC_BROKER_UNAVAILABLE,
                "tracked broker/operator provider call did not complete.",
            )

        provider_payload = _load_sanitized_provider_output(proxy_result.output_path)
        results = _provider_results(provider_payload)
        counts["provider_results_returned"] = len(results)
        _write_search_artifacts(
            retained_root=retained_root,
            provider_payload=provider_payload,
            candidate_packet=_candidate_packet_from_provider_results(
                query=normalized_query,
                run_id=run_id,
                results=results,
                provider_calls_attempted=counts["provider_calls_attempted"],
                provider_calls_completed=counts["provider_calls_completed"],
            ),
        )
        counts["search_tasks_attempted"] = 1
        counts["search_tasks_completed"] = 1

        fetch_packet, fetch_counts = _write_fetch_read_artifacts(
            retained_root=retained_root,
            fetch_read_runner=fetch_read_runner or fetch_public_url_once,
        )
        counts.update(fetch_counts)
        if fetch_packet is not None:
            counts["fetch_read_packet_created"] = 1

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
                query=normalized_query,
                repo_root=retained_root,
                smart_provider=smart_provider,
                smart_model=smart_model,
                **dprime_kwargs,
            )
            status_result = build_mvp_live_dogfood_status_output_from_semantic_status(
                semantic_status=semantic_status,
                repo_root=root,
                retained_artifact_root=retained_root,
                output_dir=output_dir or DEFAULT_MVP_LIVE_OUTPUT_DIR,
                run_id=run_id,
                command_harness_used=_command_harness(confirm_live_dprime_review),
                provider_broker_posture=(
                    "generic_broker_sanitized_provider_execution_to_"
                    "retained_artifacts_"
                    "with_explicit_dprime_review"
                ),
            )
        else:
            status_result = build_mvp_live_dogfood_status_output(
                query=normalized_query,
                repo_root=root,
                retained_artifact_root=retained_root,
                output_dir=output_dir or DEFAULT_MVP_LIVE_OUTPUT_DIR,
                run_id=run_id,
            )
        packet = _packet_from_status(
            status_result=status_result,
            query=normalized_query,
            run_id=run_id,
            retained_root=retained_root,
            counts=counts,
            provider_broker_posture=(
                "generic_broker_sanitized_provider_execution_to_retained_artifacts"
                "_with_explicit_dprime_review"
                if confirm_live_dprime_review
                else (
                    "generic_broker_sanitized_provider_execution_to_"
                    "retained_artifacts"
                )
            ),
            consumed_status=True,
            model_review_licensed=confirm_live_dprime_review,
        )
    except MvpLiveDogfoodRunError as exc:
        packet = _blocked_packet(
            blocker=exc.blocker,
            detail=exc.detail,
            query=normalized_query,
            run_id=run_id,
            retained_root=retained_root if retained_root.exists() else None,
            counts=counts,
            consumed_status=False,
            caps_exhausted=exc.caps_exhausted,
            confirm_live_dprime_review=confirm_live_dprime_review,
            model_review_licensed=False,
        )

    validate_mvp_live_dogfood_packet(packet)
    _write_json(packet_path, packet)
    output = format_mvp_friend_output(
        packet,
        packet_path=packet_path,
        output_title="ScryRaven MVP live dogfood run",
        output_kind="live dogfood run",
    )
    return MvpFriendOutputResult(
        decision=str(packet["decision"]),
        output=output,
        packet=packet,
        packet_path=packet_path,
        retained_artifact_root=retained_root if retained_root.exists() else None,
    )


def run_provider_proxy_helper_once(
    request: ProviderProxyRunRequest,
) -> ProviderProxyRunResult:
    """Invoke the existing one-run provider-proxy helper without printing secrets."""

    helper = request.repo_root / "scripts" / "run_provider_proxy_broker_once.py"
    if not helper.is_file():
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_PROVIDER_PROXY_HELPER_MISSING,
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
        "--timeout-seconds",
        "30",
        "--retry-cap",
        "0",
        "--cost-ceiling-usd",
        "0.05",
        "--output",
        str(request.output_path),
        "--broker-url",
        request.broker_url,
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
    return ProviderProxyRunResult(
        return_code=completed.returncode,
        output_path=request.output_path,
        provider_calls_attempted=1,
        provider_calls_completed=1 if completed.returncode == 0 else 0,
    )


def fetch_public_url_once(url: str) -> LiveDogfoodFetchReadResult:
    """Fetch one allowed public URL and return bounded sanitized readable text."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or not _allowed_official_domain(parsed.netloc):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read is limited to official state.gov HTTPS candidates.",
        )
    redirect_handler = _RedirectLimiter()
    opener = build_opener(redirect_handler)
    request = Request(
        url,
        headers={"User-Agent": "ScryRaven MVP live dogfood"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=20) as response:
            final_url = response.geturl()
            status_code = getattr(response, "status", None) or response.getcode()
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read(MAX_FETCHED_BYTES + 1)
    except HTTPError as exc:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            f"fetch/read HTTP status class {_status_class(exc.code)}.",
        ) from exc
    except (OSError, URLError) as exc:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "selected URL could not be fetched in one bounded public read.",
        ) from exc
    if len(body) > MAX_FETCHED_BYTES:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_CAP_EXHAUSTED,
            "fetched response exceeded the 1 MB cap.",
            caps_exhausted=True,
        )
    final_domain = urlparse(final_url).netloc.lower()
    if not _allowed_official_domain(final_domain):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "final URL left the allowed official state.gov boundary.",
        )
    if content_type in {"application/pdf"} or final_url.lower().endswith(".pdf"):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "PDF fetch/read is closed for this live dogfood run.",
        )
    if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "selected URL response was not readable text/html or text/plain.",
        )
    sanitized_text, title = _extract_readable_text(
        body,
        content_type=content_type,
        charset=charset,
    )
    if not sanitized_text:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "selected URL did not produce sanitized readable text.",
        )
    redirects = list(redirect_handler.redirects)
    return LiveDogfoodFetchReadResult(
        attempted_url=url,
        final_url=final_url,
        final_domain=final_domain,
        status_code=status_code,
        status_class=_status_class(status_code),
        content_type=content_type,
        fetched_byte_count=len(body),
        sanitized_text=sanitized_text,
        content_title=title,
        redirect_count=len(redirects),
        redirect_chain_digest=_digest_json(redirects) if redirects else None,
        retrieved_or_observed_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
    )


def validate_mvp_live_dogfood_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(packet)
    if safe.get("phase_name") != PHASE_NAME:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "live dogfood packet phase mismatch.",
        )
    if safe.get("mode") != MODE:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "live dogfood packet mode mismatch.",
        )
    for key, expected in RAW_FALSE_FLAGS.items():
        if safe.get(key) is not expected:
            raise MvpLiveDogfoodRunError(
                BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
                f"live dogfood packet must keep {key}=false.",
            )
    if safe.get("product_correctness_claimed") is not False:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "live dogfood packet must not claim product correctness.",
        )
    try:
        validate_mvp_supported_query_class_boundary_status(
            _safe_mapping(safe.get("supported_query_class_boundary"))
        )
    except ValueError as exc:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "live dogfood packet must carry supported-query-class boundary status.",
        ) from exc
    if safe.get("model_review_licensed") not in {True, False}:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "live dogfood packet must record model_review_licensed boolean.",
        )
    if _bounded_int(safe.get("dprime_model_review_calls_attempted")) > (
        MAX_DPRIME_MODEL_REVIEW_CALLS
    ):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED,
            "live dogfood packet exceeded the D-prime model-review call cap.",
            caps_exhausted=True,
        )
    _reject_forbidden_material(safe, context="live dogfood packet")
    return safe


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
    raise MvpLiveDogfoodRunError(
        BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE,
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
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE,
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
        "license_id": "mvp-live-dprime-review-entrypoint-01:fake-test",
        "enabled": True,
        "test_only": True,
        "callable_kind": "fake_test",
        "max_model_review_calls": 1,
        "retry_policy": "forbidden",
        "timeout_policy": "fail_closed",
    }


def _dprime_model_review_calls_completed(packet: Mapping[str, Any]) -> int:
    dprime = _safe_mapping(_safe_mapping(packet.get("status_payload")).get("dprime_status"))
    if not dprime:
        dprime = _safe_mapping(packet.get("dprime_status"))
    return 1 if dprime.get("model_review_status") == "completed" else 0


def _command_harness(confirm_live_dprime_review: bool) -> str:
    command = (
        f"python -m proplex {MVP_LIVE_DOGFOOD_RUN_FLAG} "
        f"{CONFIRM_LIVE_DOGFOOD_FLAG}"
    )
    if confirm_live_dprime_review:
        command = f"{command} {CONFIRM_LIVE_DPRIME_REVIEW_FLAG}"
    return command


def _candidate_packet_from_provider_results(
    *,
    query: str,
    run_id: str,
    results: Sequence[Mapping[str, Any]],
    provider_calls_attempted: int,
    provider_calls_completed: int,
) -> dict[str, Any]:
    kernel = RunKernel.start(
        run_id=run_id,
        request_id=f"request:{run_id}",
        request={
            "phase": PHASE_NAME,
            "mode": MODE,
            "query": query,
            "live_calls_authorized": True,
            "provider_search_call_cap": MAX_PROVIDER_SEARCH_CALLS,
            "fetch_read_attempt_cap": MAX_FETCH_READ_ATTEMPTS,
        },
    )
    result = execute_ordinary_live_candidate_handoff(
        run_kernel=kernel,
        query=query,
        requested_mode="Balanced",
        run_contract_projection={"contract_id": f"run-contract:{run_id}"},
        route_projection={"route_id": "route:mvp-live-dogfood"},
        core_topic="Adult U.S. passport book renewal fee by mail",
        candidate_results={
            "results": [dict(item) for item in results],
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        },
        provider_authorized=DEFAULT_PROVIDER,
        component_id=MVP_COMPONENT_ID,
        source_obligation_id=MVP_SOURCE_OBLIGATION_ID,
        search_requirement_id=MVP_SEARCH_REQUIREMENT_ID,
        planner_purpose="mvp_live_dogfood",
        live_search_validation_execution_mode=(
            LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE
        ),
        broker_invoked=True,
        live_provider_called=True,
        provider_calls_attempted_count=provider_calls_attempted,
        provider_calls_completed_count=provider_calls_completed,
        candidate_authority_source="sanitized_provider_proxy_results",
    )
    if result.candidate_packet is None or result.projection.get("failed_closed"):
        detail = str(result.projection.get("first_failed_seam") or "not_built")
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            f"search candidate packet reduction failed: {detail}",
        )
    return validate_search_result_candidate_packet(result.candidate_packet)


def _write_search_artifacts(
    *,
    retained_root: Path,
    provider_payload: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
) -> None:
    search_dir = retained_root / SEARCH_ARTIFACT_DIR
    search_dir.mkdir(parents=True, exist_ok=True)
    _write_json(search_dir / SANITIZED_PROVIDER_RESULTS_NAME, provider_payload)
    _write_json(search_dir / SEARCH_CANDIDATE_PACKET_NAME, candidate_packet)
    _write_json(search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME, candidate_packet)


def _write_fetch_read_artifacts(
    *,
    retained_root: Path,
    fetch_read_runner: FetchReadRunner,
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    search_dir = retained_root / SEARCH_ARTIFACT_DIR
    fetch_dir = retained_root / FETCH_READ_ARTIFACT_DIR
    candidate_packet = validate_search_result_candidate_packet(
        _read_json(search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME)
    )
    fetch_attempts = 0
    last_error: MvpLiveDogfoodRunError | None = None
    for candidate in _fetch_candidate_records(candidate_packet):
        if fetch_attempts >= MAX_FETCH_READ_ATTEMPTS:
            raise MvpLiveDogfoodRunError(
                BLOCKED_MVP_LIVE_CAP_EXHAUSTED,
                "fetch/read attempt cap exhausted.",
                caps_exhausted=True,
            )
        fetch_attempts += 1
        try:
            fetch_result = fetch_read_runner(str(candidate["url"]))
            _validate_fetch_result(fetch_result, candidate=candidate)
            selection = _bounded_current_path_selection(fetch_result.sanitized_text)
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
            return fetch_packet, {
                "fetch_read_attempts": fetch_attempts,
                "fetch_read_completed": 1,
            }
        except MvpLiveDogfoodRunError as exc:
            last_error = exc
            continue
    if last_error is None:
        last_error = MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "no eligible official state.gov candidate was available for fetch/read.",
        )
    return None, {
        "fetch_read_attempts": fetch_attempts,
        "fetch_read_completed": 0,
        "fetch_read_blocker": last_error.blocker,
    }


def _fetch_candidate_records(candidate_packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = [
        _safe_mapping(item)
        for item in candidate_packet.get("candidate_records", [])
        if isinstance(item, Mapping)
    ]
    official = [
        item
        for item in records
        if _allowed_official_domain(str(item.get("domain") or ""))
    ]
    return sorted(
        official,
        key=lambda item: _bounded_int(item.get("result_rank"), default=999),
    )[:MAX_FETCH_READ_ATTEMPTS]


def _fetch_read_material(
    *,
    candidate: Mapping[str, Any],
    candidate_packet: Mapping[str, Any],
    fetch_result: LiveDogfoodFetchReadResult,
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


def _packet_from_status(
    *,
    status_result: MvpFriendOutputResult,
    query: str,
    run_id: str,
    retained_root: Path,
    counts: Mapping[str, int],
    provider_broker_posture: str,
    consumed_status: bool,
    model_review_licensed: bool,
) -> dict[str, Any]:
    packet = dict(status_result.packet)
    status_decision = str(packet.get("status_decision") or packet.get("decision"))
    decision = _mapped_live_decision(
        status_decision,
        model_review_licensed=model_review_licensed,
    )
    blocker_detail = _mapped_blocker_detail(
        decision=decision,
        status_decision=status_decision,
        original_detail=str(packet.get("blocker_detail") or ""),
        model_review_licensed=model_review_licensed,
    )
    dprime_model_review_call_count = _bounded_int(
        packet.get("dprime_model_review_call_count")
    )
    if dprime_model_review_call_count > MAX_DPRIME_MODEL_REVIEW_CALLS:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED,
            "D-prime model-review call cap exceeded.",
            caps_exhausted=True,
        )
    followup_loop_count = _bounded_int(packet.get("followup_loop_count"))
    if followup_loop_count > MAX_FOLLOWUP_LOOPS:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_CAP_EXHAUSTED,
            "follow-up loop cap exhausted for this phase.",
            caps_exhausted=True,
        )
    packet.update(
        {
            "phase_name": PHASE_NAME,
            "mode": MODE,
            "query": query,
            "run_id": run_id,
            "packet_id": f"mvp-live-dogfood-packet:{run_id}",
            "status_flag": MVP_LIVE_DOGFOOD_RUN_FLAG,
            "command_harness_used": _command_harness(model_review_licensed),
            "provider_broker_posture": provider_broker_posture,
            "mvp_live_status_consumed_retained_artifacts": consumed_status,
            "provider_calls_attempted": counts.get("provider_calls_attempted", 0),
            "provider_calls_completed": counts.get("provider_calls_completed", 0),
            "search_tasks_attempted": counts.get("search_tasks_attempted", 0),
            "search_tasks_completed": counts.get("search_tasks_completed", 0),
            "provider_results_returned": counts.get("provider_results_returned", 0),
            "fetch_read_attempts": counts.get("fetch_read_attempts", 0),
            "fetch_read_completed": counts.get("fetch_read_completed", 0),
            "evidence_ledger_admissions": min(
                _bounded_int(packet.get("evidence_ledger_admissions")),
                MAX_EVIDENCE_LEDGER_ADMISSIONS,
            ),
            "dprime_model_review_call_count": dprime_model_review_call_count,
            "dprime_model_review_calls_attempted": dprime_model_review_call_count,
            "dprime_model_review_calls_completed": (
                _dprime_model_review_calls_completed(packet)
            ),
            "model_review_licensed": model_review_licensed,
            "followup_loop_count": followup_loop_count,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "private_logs_retained": False,
            "product_correctness_claimed": False,
            "caps_exhausted": False,
            "decision_made_by_the_run": (
                "mvp_live_dprime_review_entrypoint_consumed_product_path"
                if model_review_licensed
                else "mvp_live_dogfood_entrypoint_repaired_status_consumed"
            ),
            "decision": decision,
            "status_decision": status_decision,
            "explicit_non_proofs": _explicit_non_proofs(),
            "retained_artifact_root": _display_path(retained_root),
            "blocker_detail": blocker_detail,
        }
    )
    if decision != PASS_DECISION:
        packet["answer_or_blocker_text"] = (
            f"Blocked before answer: {decision}. {blocker_detail}"
        )
        packet["answer_text_present"] = False
    return packet


def _blocked_packet(
    *,
    blocker: str,
    detail: str,
    query: str,
    run_id: str,
    retained_root: Path | None,
    counts: Mapping[str, int],
    consumed_status: bool,
    caps_exhausted: bool,
    confirm_live_dprime_review: bool,
    model_review_licensed: bool,
) -> dict[str, Any]:
    safe_query = query if query == DEFAULT_MVP_QUERY else "unsupported live dogfood query (not retained)"
    packet = {
        "phase_name": PHASE_NAME,
        "mode": MODE,
        "query": safe_query,
        "supported_live_dogfood_query": DEFAULT_MVP_QUERY,
        "run_id": run_id,
        "packet_id": f"mvp-live-dogfood-packet:{run_id}",
        "ordinary_entrypoint": "python -m proplex",
        "status_flag": MVP_LIVE_DOGFOOD_RUN_FLAG,
        "command_harness_used": _command_harness(confirm_live_dprime_review),
        "runtime_consumer": (
            "proplex.mvp_live_dogfood_run.build_mvp_live_dogfood_run_output"
        ),
        "ordinary_product_path_consumed": False,
        "mvp_live_status_consumed_retained_artifacts": consumed_status,
        "provider_broker_posture": "blocked_before_generic_broker_completion",
        "provider_calls_attempted": counts.get("provider_calls_attempted", 0),
        "provider_calls_completed": counts.get("provider_calls_completed", 0),
        "search_tasks_attempted": counts.get("search_tasks_attempted", 0),
        "search_tasks_completed": counts.get("search_tasks_completed", 0),
        "provider_results_returned": counts.get("provider_results_returned", 0),
        "fetch_read_attempts": counts.get("fetch_read_attempts", 0),
        "fetch_read_completed": counts.get("fetch_read_completed", 0),
        "evidence_ledger_admissions": 0,
        "dprime_model_review_call_count": 0,
        "dprime_model_review_calls_attempted": counts.get(
            "dprime_model_review_calls_attempted",
            0,
        ),
        "dprime_model_review_calls_completed": counts.get(
            "dprime_model_review_calls_completed",
            0,
        ),
        "model_review_licensed": model_review_licensed,
        "followup_loop_count": 0,
        "answer_or_blocker_text": f"Blocked before answer: {blocker}. {detail}",
        "product_answer_text": "",
        "answer_text_present": False,
        "source_display_entries": [],
        "scrutineer_status": "not reached",
        "multi_source_status": "not reached",
        "followup_status": "not reached",
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_logs_retained": False,
        "product_correctness_claimed": False,
        "caps_exhausted": caps_exhausted,
        "decision_made_by_the_run": "mvp_live_dogfood_blocker_recorded",
        "decision": blocker,
        "status_decision": blocker,
        "explicit_non_proofs": _explicit_non_proofs(),
        "supported_query_class_boundary": (
            build_mvp_supported_query_class_boundary_status(
                status=(
                    "fixed_dogfood_example_only"
                    if query == DEFAULT_MVP_QUERY
                    else "unsupported_query_blocked_before_boundary_entry"
                ),
                fixed_query_example=query == DEFAULT_MVP_QUERY,
                product_path_slice=(
                    "fixed_live_dogfood_slice"
                    if query == DEFAULT_MVP_QUERY
                    else "fixed_live_dogfood_query_gate"
                ),
                product_path_consumed=False,
            )
        ),
        "retained_artifact_root": _display_path(retained_root) if retained_root else None,
        "blocker_detail": detail,
    }
    if blocker == BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED:
        packet.update(
            {
                "unsupported_query_retained": False,
                "supported_live_dogfood_query": DEFAULT_MVP_QUERY,
            }
        )
    return packet


def _mapped_live_decision(
    status_decision: str,
    *,
    model_review_licensed: bool,
) -> str:
    if status_decision == PASS_DECISION:
        return PASS_DECISION
    if status_decision == "BLOCKED_DPRIME_MODEL_REVIEW_NOT_LICENSED":
        if model_review_licensed:
            return BLOCKED_MVP_LIVE_PRODUCT_PATH_NOT_CONSUMED
        return BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING
    if status_decision == BLOCKED_DPRIME_MODEL_REVIEW_OUTPUT_INVALID:
        return BLOCKED_MVP_LIVE_DPRIME_REVIEW_OUTPUT_INVALID
    if status_decision in {
        BLOCKED_APPROVED_MODEL_UNAVAILABLE,
        BLOCKED_DPRIME_MODEL_REVIEW_CALL_FAILED,
        BLOCKED_OPENAI_CREDENTIAL_UNAVAILABLE,
        BLOCKED_OPENAI_ONE_SHOT_TRANSPORT_UNSAFE,
        BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT,
    }:
        return BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE
    if status_decision in {
        "BLOCKED_FETCH_READ_ARTIFACT_MISSING",
        "BLOCKED_FETCH_READ_ARTIFACT_UNREADABLE",
        "BLOCKED_FETCH_READ_ARTIFACT_RAW_PRIVATE",
        "BLOCKED_FETCH_READ_ARTIFACT_LINEAGE",
    }:
        return BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING
    if status_decision == "BLOCKED_OUTPUT_HYGIENE":
        return BLOCKED_MVP_LIVE_OUTPUT_HYGIENE
    return status_decision


def _mapped_blocker_detail(
    *,
    decision: str,
    status_decision: str,
    original_detail: str,
    model_review_licensed: bool,
) -> str:
    if decision == BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING:
        return (
            "Retained live search and fetch/read artifacts reached the MVP live "
            "status consumer, but the live D-prime model-review route is not "
            "licensed/wired for this command. Pass "
            f"{CONFIRM_LIVE_DPRIME_REVIEW_FLAG} to license one product-route "
            f"D-prime review attempt; underlying status decision: {status_decision}."
        )
    if decision == BLOCKED_MVP_LIVE_PRODUCT_PATH_NOT_CONSUMED:
        return (
            "The D-prime review confirmation was present, but the product status "
            "path still reported the model-review-not-licensed stop; underlying "
            f"status decision: {status_decision}."
        )
    if decision == BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE:
        return (
            "The explicit D-prime review route failed closed before producing a "
            f"validated support proposal; underlying status decision: {status_decision}. "
            f"{original_detail}"
        ).strip()
    if decision == BLOCKED_MVP_LIVE_DPRIME_REVIEW_OUTPUT_INVALID:
        return (
            "The explicit D-prime review route made one attempt, but the model "
            f"review output was invalid; underlying status decision: {status_decision}. "
            f"{original_detail}"
        ).strip()
    if decision == BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING:
        return (
            "Retained live search artifacts reached the MVP status consumer, "
            "but bounded live fetch/read did not produce a readable retained "
            f"handoff; underlying status decision: {status_decision}."
        )
    if model_review_licensed and original_detail:
        return original_detail
    return original_detail or f"underlying status decision: {status_decision}."


def _load_sanitized_provider_output(path: Path) -> dict[str, Any]:
    try:
        decoded = _read_json(path)
    except FileNotFoundError as exc:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_GENERIC_BROKER_UNAVAILABLE,
            "sanitized provider execution proof was not written.",
        ) from exc
    return _validate_provider_payload(decoded)


def _validate_provider_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = _safe_mapping(payload)
    _reject_forbidden_material(raw, context="sanitized provider response")
    unknown = sorted(set(raw) - _ALLOWED_PROVIDER_ENVELOPE_KEYS)
    if unknown:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "sanitized provider response has unsupported fields: "
            + ", ".join(unknown),
        )
    if raw.get("raw_provider_payload_retained") is not False:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "sanitized provider response retained raw provider payload.",
        )
    if raw.get("raw_search_response_retained") is not False:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "sanitized provider response retained raw search response.",
        )
    if (
        raw.get("raw_request_material_retained") is not False
        or raw.get("raw_response_material_retained") is not False
    ):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "sanitized provider response retained raw request/response material.",
        )
    if (
        raw.get("schema_version") != EXPECTED_SEARCH_SCHEMA_VERSION
        or raw.get("proof_kind") != EXPECTED_SEARCH_PROOF_KIND
        or raw.get("provider") != DEFAULT_PROVIDER
        or raw.get("operation") != DEFAULT_OPERATION
        or raw.get("status") != "ok"
        or raw.get("physical_attempt_count") != 1
        or raw.get("caller_authorized_cost_ceiling_usd")
        != EXPECTED_SEARCH_COST_CEILING_USD
    ):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "sanitized provider response proof attestation is invalid.",
        )
    results = raw.get("results")
    if not isinstance(results, list):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "sanitized provider response results must be a list.",
        )
    if len(results) > MAX_PROVIDER_RESULTS:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_CAP_EXHAUSTED,
            "sanitized provider response exceeded max results cap.",
            caps_exhausted=True,
        )
    if _bounded_int(raw.get("result_count"), default=len(results)) != len(results):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "sanitized provider result_count does not match results length.",
        )
    provider_elapsed = raw.get("provider_elapsed_milliseconds_total")
    if (
        not isinstance(provider_elapsed, int)
        or isinstance(provider_elapsed, bool)
        or not 0 <= provider_elapsed <= 2_000_000
    ):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "sanitized provider response elapsed telemetry is invalid.",
        )
    normalized = [_normalize_provider_result(item, index=i) for i, item in enumerate(results, 1)]
    return {
        "schema_version": EXPECTED_SEARCH_SCHEMA_VERSION,
        "proof_kind": EXPECTED_SEARCH_PROOF_KIND,
        "provider": DEFAULT_PROVIDER,
        "operation": DEFAULT_OPERATION,
        "status": "ok",
        "result_count": len(normalized),
        "results": normalized,
        "physical_attempt_count": 1,
        "provider_elapsed_milliseconds_total": provider_elapsed,
        "caller_authorized_cost_ceiling_usd": EXPECTED_SEARCH_COST_CEILING_USD,
        "raw_provider_payload_retained": False,
        "raw_request_material_retained": False,
        "raw_response_material_retained": False,
        "raw_search_response_retained": False,
    }


def _provider_results(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in payload.get("results", []) if isinstance(item, Mapping)]


def _normalize_provider_result(value: Any, *, index: int) -> dict[str, Any]:
    raw = _safe_mapping(value)
    _reject_forbidden_material(raw, context="sanitized provider result")
    unknown = sorted(set(raw) - _ALLOWED_PROVIDER_RESULT_KEYS)
    if unknown:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result has unsupported fields: " + ", ".join(unknown),
        )
    if raw.get("raw_provider_payload_retained") is True:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result retained raw provider payload.",
        )
    if raw.get("raw_search_response_retained") is True:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            "sanitized provider result retained raw search response.",
        )
    if (
        raw.get("provider") != DEFAULT_PROVIDER
        or raw.get("operation") != DEFAULT_OPERATION
    ):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "sanitized provider result route attestation is invalid.",
        )
    url = _required_url(raw.get("url") or raw.get("link"))
    domain = _clean_domain(raw.get("domain")) or urlparse(url).netloc.lower()
    return {
        "title": _required_text(raw.get("title"), "provider result requires title", 220),
        "url": url,
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
    }


def _validate_fetch_result(
    fetch_result: LiveDogfoodFetchReadResult,
    *,
    candidate: Mapping[str, Any],
) -> None:
    if fetch_result.attempted_url != candidate.get("url"):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read attempted URL differed from selected candidate URL.",
        )
    if not _allowed_official_domain(fetch_result.final_domain):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read final domain left the official state.gov boundary.",
        )
    if fetch_result.redirect_count > MAX_REDIRECTS:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_CAP_EXHAUSTED,
            "fetch/read redirect cap exhausted.",
            caps_exhausted=True,
        )
    if fetch_result.fetched_byte_count > MAX_FETCHED_BYTES:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_CAP_EXHAUSTED,
            "fetch/read byte cap exhausted.",
            caps_exhausted=True,
        )
    if not fetch_result.sanitized_text:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING,
            "fetch/read did not produce sanitized readable text.",
        )


def _bounded_current_path_selection(text: str) -> BoundedTextSelection:
    return select_bounded_answer_bearing_text(
        text,
        max_chars=FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
        required_or_preferred_anchors=TARGET_ANCHOR_GROUPS,
        component_text=TARGET_COMPONENT_TEXT,
        claim_under_test=TARGET_COMPONENT_CLAIM_UNDER_TEST,
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
            raise MvpLiveDogfoodRunError(
                BLOCKED_MVP_LIVE_CAP_EXHAUSTED,
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


def _run_output_dir(root: Path, output_dir: str | Path, run_id: str) -> Path:
    raw = Path(output_dir)
    if not raw.is_absolute():
        raw = root / raw
    resolved = raw.resolve()
    allowed = (root / DEFAULT_MVP_LIVE_OUTPUT_DIR).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise ValueError("MVP live dogfood output must stay under output/mvp_live_dogfood_01/") from exc
    target = resolved / _clean_run_id(run_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _env_file_paths(values: Sequence[str | Path] | None) -> tuple[Path, ...]:
    if values is None:
        return ()
    if len(values) > 1:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_GENERIC_BROKER_UNAVAILABLE,
            "tracked broker activation accepts at most one environment file.",
        )
    return tuple(Path(value) for value in values)


def _pytest_or_ci_guard(environ: Mapping[str, str] | None) -> bool:
    env = os.environ if environ is None else environ
    return bool(env.get("PYTEST_CURRENT_TEST") or env.get("CI") or env.get("GITHUB_ACTIONS"))


def _empty_counts() -> dict[str, int]:
    return {
        "provider_calls_attempted": 0,
        "provider_calls_completed": 0,
        "search_tasks_attempted": 0,
        "search_tasks_completed": 0,
        "provider_results_returned": 0,
        "fetch_read_attempts": 0,
        "fetch_read_completed": 0,
        "fetch_read_packet_created": 0,
        "dprime_model_review_calls_attempted": 0,
        "dprime_model_review_calls_completed": 0,
    }


def _explicit_non_proofs() -> list[str]:
    return sorted(set(EXPLICIT_NON_PROOFS) | set(MVP_STATUS_NON_PROOFS))


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, Mapping):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
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
        if key in _ALLOWED_RAW_FALSE_KEYS:
            if not _all_normalized_key_values_false(value, key):
                forbidden.append(key)
            continue
        if key in _FORBIDDEN_KEYS or key.startswith("raw_"):
            forbidden.append(key)
    if forbidden:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
            f"{context} contains raw/private fields: " + ", ".join(forbidden),
        )
    markers = sorted(_private_value_markers(value))
    if markers:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
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


def _required_url(value: Any) -> str:
    url = _required_text(value, "provider result requires url", 700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "provider result requires http(s) url.",
        )
    return url


def _required_text(value: Any, message: str, limit: int) -> str:
    text = _clean_text(value, limit=limit)
    if not text:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            message,
        )
    return text


def _positive_int(value: Any) -> int:
    parsed = _bounded_int(value)
    if parsed <= 0:
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_SEARCH_ARTIFACT_REDUCTION_MISSING,
            "provider result rank/call index must be positive.",
        )
    return parsed


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, parsed)


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _normalize_query(value: Any) -> str:
    return " ".join(str(value or "").split())


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        raise MvpLiveDogfoodRunError(
            BLOCKED_MVP_LIVE_OUTPUT_HYGIENE,
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


def _allowed_official_domain(domain: str | None) -> bool:
    normalized = str(domain or "").casefold().strip("/")
    return (
        normalized == "travel.state.gov"
        or normalized == "state.gov"
        or normalized.endswith(".state.gov")
    )


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


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _clean_run_id(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-_:" else "-" for ch in value.strip())
    return text[:120] or f"mvp-live-dogfood-{uuid.uuid4().hex[:12]}"


def _run_id(value: str | None) -> str:
    return _clean_run_id(value) if value else f"mvp-live-dogfood-{uuid.uuid4().hex[:12]}"


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "BLOCKED_MVP_LIVE_CONFIRMATION_REQUIRED",
    "BLOCKED_MVP_LIVE_DOGFOOD_QUERY_NOT_SUPPORTED",
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_ENTRYPOINT_MISSING",
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_CAP_EXHAUSTED",
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_OUTPUT_INVALID",
    "BLOCKED_MVP_LIVE_DPRIME_REVIEW_ROUTE_UNAVAILABLE",
    "BLOCKED_MVP_LIVE_FETCH_READ_ENTRYPOINT_MISSING",
    "BLOCKED_MVP_LIVE_MODEL_ROUTE_SECRET_BOUNDARY",
    "BLOCKED_MVP_LIVE_GENERIC_BROKER_UNAVAILABLE",
    "BLOCKED_MVP_LIVE_PRODUCT_PATH_NOT_CONSUMED",
    "BLOCKED_MVP_LIVE_TEST_OR_CI_GUARD",
    "CONFIRM_LIVE_DPRIME_REVIEW_FLAG",
    "CONFIRM_LIVE_DOGFOOD_FLAG",
    "MVP_LIVE_DOGFOOD_RUN_FLAG",
    "LiveDogfoodFetchReadResult",
    "MvpLiveDogfoodRunError",
    "ProviderProxyRunRequest",
    "ProviderProxyRunResult",
    "build_mvp_live_dogfood_run_output",
    "fetch_public_url_once",
    "run_provider_proxy_helper_once",
    "validate_mvp_live_dogfood_packet",
]
