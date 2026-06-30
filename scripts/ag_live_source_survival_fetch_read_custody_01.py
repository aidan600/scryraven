from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.evidence_ledger_lifecycle import (  # noqa: E402
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.fetch_read_content_reference import (  # noqa: E402
    FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS,
    build_fetch_read_content_packet_from_candidate_packet,
    fetch_read_content_packet_ref_from_packet,
    validate_fetch_read_content_packet,
)
from core.run_kernel import RunKernel  # noqa: E402
from core.search_result_candidate_packet import (  # noqa: E402
    validate_search_result_candidate_packet,
)

PHASE = "AG-LIVE-SOURCE-SURVIVAL-FETCH-READ-CUSTODY-01"
MODE = "PROOF"
USABLE_ANSWER_VERDICT_TARGET = "NO-BUT-JUSTIFIED"
PROOF_CLASS = "live_component_proof"
PRODUCT_FACING_PROGRESS_TYPE = (
    "live component source-survival validation with explicit live license"
)
PRODUCT_PATH_AFFECTED = (
    "standalone local validation harness only; installed product behavior is unchanged"
)
ACTUAL_CONSUMER_SEAM = (
    "SearchResultCandidatePacket -> FetchReadContentPacket / "
    "SanitizedContentReference -> EvidenceLedger candidate/content custody"
)
PRIOR_PHASE = "AG-LIMITED-LIVE-SEARCH-CANDIDATE-01"
DEFAULT_PRIOR_OUTPUT_DIR = ROOT / "output" / "ag_limited_live_search_candidate_01"
DEFAULT_CANDIDATE_PACKET = DEFAULT_PRIOR_OUTPUT_DIR / "search_result_candidate_packet.json"
DEFAULT_VALIDATION_PACKET = DEFAULT_PRIOR_OUTPUT_DIR / "validation_packet.json"
DEFAULT_SANITIZED_PROVIDER_RESULTS = (
    DEFAULT_PRIOR_OUTPUT_DIR / "sanitized_provider_results.json"
)
DEFAULT_OUTPUT_DIR = ROOT / "output" / "ag_live_source_survival_fetch_read_custody_01"

REQUEST_PACKET_NAME = "request_packet.json"
REQUEST_MARKDOWN_NAME = "request_packet.md"
SOURCE_PACKET_NAME = "source_survival_packet.json"
SOURCE_MARKDOWN_NAME = "source_survival_packet.md"
FETCH_READ_PACKET_NAME = "fetch_read_content_packet.json"
CONTENT_REFERENCE_NAME = "sanitized_content_reference.json"
LEDGER_PROJECTION_NAME = "evidence_ledger_projection.json"

SELECTED_RANK = 1
REQUIRED_DOMAIN = "travel.state.gov"
MAX_FETCH_READ_CALLS = 1
MAX_REDIRECTS = 2
MAX_FETCHED_BYTES = 1_048_576
MAX_REVIEW_SANITIZED_TEXT_CHARS = 8_000
MAX_LEDGER_ADMISSIONS = 1
MODEL_CALLS = 0
PROVIDER_CALLS = 0
BROKER_CALLS = 0
RETRIEVAL_CALLS = 0

SOURCE_SURVIVAL_RESULTS = frozenset(
    {
        "source_survival_pass",
        "source_survival_partial",
        "source_survival_fail",
        "validation_not_run_operator_blocked",
        "validation_inconclusive",
    }
)

MANDATORY_NEXT_BUILD_CHECKPOINT = (
    "live evidence-relative semantic support over the fetched content if source "
    "survival / fetch-read / EvidenceLedger candidate-content custody passes; "
    "otherwise targeted REPAIR of the first broken fetch/read/custody seam"
)

OPENED_SURFACES = [
    "one public HTTPS fetch/read for the selected rank-1 travel.state.gov URL",
    "bounded sanitized readable-content extraction",
    "FetchReadContentPacket / SanitizedContentReference for the selected candidate",
    "EvidenceLedger candidate/content custody for bounded sanitized content",
    "review packets under output/ag_live_source_survival_fetch_read_custody_01/",
]

CLOSED_SURFACES = [
    "provider search / broker / Serper",
    "model calls",
    "broad retrieval",
    "PDF handling",
    "multi-source fetch",
    "JavaScript rendering",
    "login/cookie flows",
    "SemanticObservation",
    "ComponentCoverage",
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "AuthorProse",
    "citation eligibility or rendering",
    "source-obligation satisfaction",
    "answer text",
    "product correctness",
]

EXPLICIT_NON_PROOFS = [
    "semantic support from fetched content",
    "ComponentCoverage",
    "SufficiencyReadiness",
    "FinalAnswerPacket authority",
    "Author or AuthorProse behavior",
    "citation eligibility",
    "citation rendering",
    "source-obligation satisfaction",
    "answer text",
    "answer correctness or product correctness",
    "product-quality prose",
]

_SAFE_FALSE_KEYS = frozenset(
    {
        "raw_html_retained",
        "raw_response_headers_retained",
        "raw_cookies_retained",
        "raw_page_content_retained",
        "raw_page_text_retained",
        "raw_headers_retained",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
        "citation_eligible",
        "citation_created",
        "source_obligation_satisfied",
        "semantic_support_created",
        "semantic_observation_created",
        "component_coverage_created",
        "sufficiency_decided",
        "final_answer_packet_created",
        "author_input_created",
        "partial_answer_ready",
        "product_correctness_claimed",
    }
)

_FORBIDDEN_RAW_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "auth_header",
        "auth_headers",
        "authorization",
        "authorization_header",
        "body",
        "cache",
        "cache_row",
        "cookie",
        "cookies",
        "db",
        "db_cache_row",
        "db_cache_rows",
        "db_row",
        "env",
        "full_prompt",
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
        "raw_cookies",
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
        "raw_response_headers",
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

_FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "analyst_material",
        "analyst_report",
        "answer",
        "answer_material",
        "answer_text",
        "author",
        "author_input",
        "author_material",
        "citation",
        "citation_record",
        "citation_records",
        "citation_source",
        "citation_sources",
        "citations",
        "component_coverage",
        "component_satisfaction",
        "coverage",
        "evidence_relative_support",
        "fap",
        "fap_material",
        "final_answer",
        "final_answer_packet",
        "semantic_observation",
        "semantic_support",
        "source_obligation_claim",
        "source_obligation_satisfaction",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)

_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "admitted_to_evidence_ledger",
        "admitted_source",
        "analyst_report_created",
        "answer_ready",
        "author_input_created",
        "citation_created",
        "citation_eligible",
        "citation_rendered",
        "component_coverage_created",
        "component_satisfaction_created",
        "content_citation_eligible",
        "evidence_admitted",
        "final_answer_packet_created",
        "final_answer_ready",
        "partial_answer_ready",
        "product_correctness_claimed",
        "readiness_decided",
        "semantic_observation_created",
        "semantic_support_created",
        "source_obligation_satisfied",
        "source_obligation_support_created",
        "sufficiency_decided",
    }
)


class SourceSurvivalError(ValueError):
    """Raised when the source-survival harness must fail closed."""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        failure_layer: str | None = None,
    ) -> None:
        super().__init__(message or code)
        self.code = code
        self.failure_layer = failure_layer


@dataclass(frozen=True, slots=True)
class PriorCandidateSelection:
    candidate_packet: dict[str, Any]
    validation_packet: dict[str, Any]
    selected_candidate: dict[str, Any]
    prior_refs: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FetchReadResult:
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
    redirects_sanitized: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    retrieved_or_observed_at: str = ""


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
            raise SourceSurvivalError(
                "max_redirects_exceeded",
                "selected URL exceeded the redirect cap",
                failure_layer="url_fetch_read",
            )
        self.redirects.append(
            {
                "from_domain": _domain_from_url(req.full_url),
                "to_domain": _domain_from_url(newurl),
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
        return _clean_token(" ".join(self.title_parts), limit=300)


def prepare_request(
    *,
    candidate_packet_path: str | Path = DEFAULT_CANDIDATE_PACKET,
    validation_packet_path: str | Path = DEFAULT_VALIDATION_PACKET,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Write request/review prep without opening the public URL."""

    selection = load_prior_candidate_selection(
        candidate_packet_path=candidate_packet_path,
        validation_packet_path=validation_packet_path,
    )
    target = _phase_output_dir(output_dir)
    packet = _base_packet(
        selection=selection,
        fetch_read_calls_attempted=0,
        fetch_read_calls_completed=0,
        selected_source_survived="validation_not_run_operator_blocked",
        likely_failure_layer="operator_pending_fetch_read_confirmation",
        final_url=None,
        final_domain=None,
        http_status_class=None,
        content_type=None,
        fetched_byte_count=0,
        sanitized_readable_text=None,
        fetch_read_packet=None,
        sanitized_content_reference=None,
        evidence_ledger_projection=None,
        output_dir=target,
    )
    packet.update(
        {
            "packet_kind": "source_survival_request_packet",
            "request_generation_fetch_read_free": True,
            "fetch_read_custody_requires_confirm_fetch_read": True,
            "operator_command": _operator_command(
                candidate_packet_path=candidate_packet_path,
                validation_packet_path=validation_packet_path,
                output_dir=target,
            ),
            "expected_output_paths": {
                "request_packet": _rel(target / REQUEST_PACKET_NAME),
                "request_markdown": _rel(target / REQUEST_MARKDOWN_NAME),
                "source_survival_packet": _rel(target / SOURCE_PACKET_NAME),
                "source_survival_markdown": _rel(target / SOURCE_MARKDOWN_NAME),
                "fetch_read_content_packet": _rel(target / FETCH_READ_PACKET_NAME),
                "sanitized_content_reference": _rel(target / CONTENT_REFERENCE_NAME),
                "evidence_ledger_projection": _rel(target / LEDGER_PROJECTION_NAME),
            },
        }
    )
    validate_source_survival_packet(packet)
    _write_json(target / REQUEST_PACKET_NAME, packet)
    (target / REQUEST_MARKDOWN_NAME).write_text(
        _request_markdown(packet),
        encoding="utf-8",
    )
    return packet


def fetch_read_custody(
    *,
    candidate_packet_path: str | Path = DEFAULT_CANDIDATE_PACKET,
    validation_packet_path: str | Path = DEFAULT_VALIDATION_PACKET,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    confirm_fetch_read: bool = False,
    fetcher: Callable[[str], FetchReadResult] | None = None,
) -> dict[str, Any]:
    """Perform the one licensed public URL fetch/read and custody reduction."""

    if not confirm_fetch_read:
        raise SourceSurvivalError(
            "confirm_fetch_read_required",
            "fetch-read-custody requires --confirm-fetch-read",
            failure_layer="operator_confirmation",
        )
    selection = load_prior_candidate_selection(
        candidate_packet_path=candidate_packet_path,
        validation_packet_path=validation_packet_path,
    )
    target = _phase_output_dir(output_dir)
    selected = selection.selected_candidate
    fetch = fetcher or _fetch_public_url_once
    fetch_read_calls_attempted = 1
    fetch_read_calls_completed = 0
    fetch_result: FetchReadResult | None = None
    fetch_read_packet: dict[str, Any] | None = None
    reference: dict[str, Any] | None = None
    ledger_projection: dict[str, Any] | None = None
    survived = "source_survival_fail"
    failure_layer: str | None = "url_fetch_read"
    failure_reason: str | None = None

    try:
        fetch_result = fetch(str(selected["url"]))
        fetch_read_calls_completed = 1
        _validate_fetch_result(fetch_result, selected=selected)
        bounded_text = _bounded_current_path_text(fetch_result.sanitized_text)
        material = _sanitized_fetch_read_material(
            selection=selection,
            fetch_result=fetch_result,
            bounded_text=bounded_text,
        )
        fetch_read_packet = build_fetch_read_content_packet_from_candidate_packet(
            selection.candidate_packet,
            [material],
            selected_candidate_ids=[selected["candidate_id"]],
        )
        fetch_read_packet = validate_fetch_read_content_packet(fetch_read_packet)
        reference = dict(fetch_read_packet["reference_records"][0])
        run_kernel = RunKernel.start(
            run_id=str(selection.candidate_packet["run_id"]),
            request_id=str(selection.candidate_packet["request_id"]),
            request={
                "phase": PHASE,
                "mode": MODE,
                "proof_class": PROOF_CLASS,
                "query_text_retained": False,
                "provider_calls": PROVIDER_CALLS,
                "broker_calls": BROKER_CALLS,
                "model_calls": MODEL_CALLS,
                "fetch_read_calls": MAX_FETCH_READ_CALLS,
            },
        )
        ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
            run_kernel=run_kernel,
            fetch_read_content_packet=fetch_read_packet,
            observation_id=(
                f"{selection.candidate_packet['run_id']}:"
                "evidence-ledger:ag-live-source-survival-fetch-read-custody-01"
            ),
        )
        survived = _survival_verdict(
            fetch_result=fetch_result,
            fetch_read_packet=fetch_read_packet,
            ledger_projection=ledger_projection,
        )
        failure_layer = None if survived == "source_survival_pass" else "custody"
    except SourceSurvivalError as exc:
        failure_reason = str(exc)
        failure_layer = exc.failure_layer or "url_fetch_read"
        survived = "source_survival_fail"

    packet = _base_packet(
        selection=selection,
        fetch_read_calls_attempted=fetch_read_calls_attempted,
        fetch_read_calls_completed=fetch_read_calls_completed,
        selected_source_survived=survived,
        likely_failure_layer=failure_layer,
        final_url=fetch_result.final_url if fetch_result else None,
        final_domain=fetch_result.final_domain if fetch_result else None,
        http_status_class=fetch_result.status_class if fetch_result else None,
        content_type=fetch_result.content_type if fetch_result else None,
        fetched_byte_count=fetch_result.fetched_byte_count if fetch_result else 0,
        sanitized_readable_text=(
            _bounded_current_path_text(fetch_result.sanitized_text)
            if fetch_result
            else None
        ),
        fetch_read_packet=fetch_read_packet,
        sanitized_content_reference=reference,
        evidence_ledger_projection=ledger_projection,
        output_dir=target,
    )
    packet.update(
        {
            "packet_kind": "source_survival_packet",
            "fetch_read_failure_reason": failure_reason,
            "redirect_count": fetch_result.redirect_count if fetch_result else 0,
            "redirect_chain_digest": (
                fetch_result.redirect_chain_digest if fetch_result else None
            ),
            "redirects_sanitized": (
                list(fetch_result.redirects_sanitized) if fetch_result else []
            ),
        }
    )
    validate_source_survival_packet(packet)
    if fetch_read_packet:
        _write_json(target / FETCH_READ_PACKET_NAME, fetch_read_packet)
    if reference:
        _write_json(target / CONTENT_REFERENCE_NAME, reference)
    if ledger_projection:
        _write_json(target / LEDGER_PROJECTION_NAME, ledger_projection)
    _write_json(target / SOURCE_PACKET_NAME, packet)
    (target / SOURCE_MARKDOWN_NAME).write_text(
        _source_markdown(packet),
        encoding="utf-8",
    )
    return packet


def load_prior_candidate_selection(
    *,
    candidate_packet_path: str | Path,
    validation_packet_path: str | Path,
) -> PriorCandidateSelection:
    candidate_path = _prior_output_path(candidate_packet_path)
    validation_path = _prior_output_path(validation_packet_path)
    try:
        candidate_packet = validate_search_result_candidate_packet(
            _read_json(candidate_path)
        )
        validation_packet = _read_json(validation_path)
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        raise SourceSurvivalError(
            "prior_candidate_packet_missing_or_mismatched",
            "prior_candidate_packet_missing_or_mismatched",
            failure_layer="prior_candidate_packet",
        ) from exc

    selected = _rank_one_candidate(candidate_packet)
    summary = _rank_one_validation_summary(validation_packet)
    if (
        selected.get("domain") != REQUIRED_DOMAIN
        or selected.get("result_rank") != SELECTED_RANK
        or summary.get("domain") != REQUIRED_DOMAIN
        or summary.get("rank") != SELECTED_RANK
        or summary.get("url") != selected.get("url")
        or validation_packet.get("likely_acquisition_result")
        != "candidate_acquisition_pass"
        or validation_packet.get("search_result_candidate_packet_status")
        != "built_and_validated"
    ):
        raise SourceSurvivalError(
            "prior_candidate_packet_missing_or_mismatched",
            "prior_candidate_packet_missing_or_mismatched",
            failure_layer="prior_candidate_packet",
        )

    prior_refs = {
        "prior_phase": PRIOR_PHASE,
        "candidate_packet_path": _rel(candidate_path),
        "candidate_packet_digest": _file_digest(candidate_path),
        "validation_packet_path": _rel(validation_path),
        "validation_packet_digest": _file_digest(validation_path),
        "sanitized_provider_results_path": _rel(DEFAULT_SANITIZED_PROVIDER_RESULTS),
        "sanitized_provider_results_digest": (
            _file_digest(DEFAULT_SANITIZED_PROVIDER_RESULTS)
            if DEFAULT_SANITIZED_PROVIDER_RESULTS.exists()
            else None
        ),
        "search_result_candidate_packet_ref": {
            "packet_id": candidate_packet.get("packet_id"),
            "packet_digest": candidate_packet.get("packet_digest"),
            "candidate_count": candidate_packet.get("candidate_count"),
            "schema_version": candidate_packet.get("schema_version"),
        },
        "validation_packet_result": validation_packet.get(
            "likely_acquisition_result"
        ),
    }
    return PriorCandidateSelection(
        candidate_packet=candidate_packet,
        validation_packet=validation_packet,
        selected_candidate=dict(selected),
        prior_refs=_json_safe(prior_refs),
    )


def validate_source_survival_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(packet)
    if safe.get("phase") != PHASE:
        raise SourceSurvivalError("source_survival_packet_phase_mismatch")
    if safe.get("mode") != MODE:
        raise SourceSurvivalError("source_survival_packet_mode_mismatch")
    result = safe.get("selected_source_survived")
    if result not in SOURCE_SURVIVAL_RESULTS:
        raise SourceSurvivalError("source_survival_packet_result_mismatch")
    _reject_forbidden_packet_material(safe)
    for key in (
        "raw_html_retained",
        "raw_response_headers_retained",
        "raw_cookies_retained",
    ):
        if safe.get(key) is not False:
            raise SourceSurvivalError(f"{key}_must_be_false")
    if safe.get("fetch_read_calls_attempted", 0) > MAX_FETCH_READ_CALLS:
        raise SourceSurvivalError("fetch_read_call_cap_exceeded")
    if safe.get("evidence_ledger_candidate_content_custody_count", 0) > (
        MAX_LEDGER_ADMISSIONS
    ):
        raise SourceSurvivalError("evidence_ledger_custody_cap_exceeded")
    if safe.get("semantic_observation_admissions") != 0:
        raise SourceSurvivalError("semantic_observation_surface_opened")
    if safe.get("component_coverage_reductions") != 0:
        raise SourceSurvivalError("component_coverage_surface_opened")
    if safe.get("citation_eligibility_decisions") != 0:
        raise SourceSurvivalError("citation_eligibility_surface_opened")
    if safe.get("source_obligation_satisfaction_decisions") != 0:
        raise SourceSurvivalError("source_obligation_surface_opened")
    if safe.get("sufficiency_fap_author_authorprose_from_live_evidence") != 0:
        raise SourceSurvivalError("answer_author_surface_opened")
    excerpt = safe.get("bounded_excerpt")
    if excerpt is not None and len(str(excerpt)) > MAX_REVIEW_SANITIZED_TEXT_CHARS:
        raise SourceSurvivalError("bounded_excerpt_exceeds_phase_cap")
    return safe


def _fetch_public_url_once(url: str) -> FetchReadResult:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != REQUIRED_DOMAIN:
        raise SourceSurvivalError(
            "selected_url_outside_allowed_domain",
            "selected URL must be the rank-1 travel.state.gov HTTPS URL",
            failure_layer="selected_candidate",
        )
    redirect_handler = _RedirectLimiter()
    opener = build_opener(redirect_handler)
    request = Request(
        url,
        headers={
            "User-Agent": (
                "ScryRaven AG-LIVE-SOURCE-SURVIVAL-FETCH-READ-CUSTODY-01"
            )
        },
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
        raise SourceSurvivalError(
            "selected_url_fetch_failed",
            f"HTTP status class {_status_class(exc.code)}",
            failure_layer="url_fetch_read",
        ) from exc
    except (OSError, URLError) as exc:
        raise SourceSurvivalError(
            "selected_url_fetch_failed",
            "selected URL could not be fetched in one public fetch/read call",
            failure_layer="url_fetch_read",
        ) from exc

    if len(body) > MAX_FETCHED_BYTES:
        raise SourceSurvivalError(
            "fetched_byte_cap_exceeded",
            "fetched response exceeds the 1 MB cap",
            failure_layer="url_fetch_read",
        )
    final_domain = _domain_from_url(final_url)
    if not _allowed_final_domain(final_domain):
        raise SourceSurvivalError(
            "final_url_outside_allowed_domain",
            "final URL left the allowed official state.gov boundary",
            failure_layer="url_fetch_read",
        )
    if content_type in {"application/pdf"} or final_url.lower().endswith(".pdf"):
        raise SourceSurvivalError(
            "pdf_handling_closed",
            "selected URL requires PDF handling, which is closed",
            failure_layer="content_type",
        )
    if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
        raise SourceSurvivalError(
            "unsupported_content_type",
            "selected URL response is not readable text/html or text/plain",
            failure_layer="content_type",
        )
    sanitized_text, content_title = _extract_readable_text(
        body,
        content_type=content_type,
        charset=charset,
    )
    if not sanitized_text:
        raise SourceSurvivalError(
            "no_readable_text",
            "selected URL did not produce bounded readable text",
            failure_layer="sanitized_readable_content",
        )
    redirects = list(redirect_handler.redirects)
    return FetchReadResult(
        attempted_url=url,
        final_url=final_url,
        final_domain=final_domain,
        status_code=status_code,
        status_class=_status_class(status_code),
        content_type=content_type,
        fetched_byte_count=len(body),
        sanitized_text=sanitized_text,
        content_title=content_title,
        redirect_count=len(redirects),
        redirect_chain_digest=_digest_json(redirects) if redirects else None,
        redirects_sanitized=redirects,
        retrieved_or_observed_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
    )


def _validate_fetch_result(
    fetch_result: FetchReadResult,
    *,
    selected: Mapping[str, Any],
) -> None:
    if fetch_result.attempted_url != selected.get("url"):
        raise SourceSurvivalError(
            "fetch_attempt_url_mismatch",
            "fetch/read attempted URL differs from selected candidate URL",
            failure_layer="url_fetch_read",
        )
    if fetch_result.final_domain != selected.get("domain"):
        if not _allowed_final_domain(fetch_result.final_domain):
            raise SourceSurvivalError(
                "final_url_outside_allowed_domain",
                "final URL left the allowed official domain boundary",
                failure_layer="url_fetch_read",
            )
    if fetch_result.redirect_count > MAX_REDIRECTS:
        raise SourceSurvivalError(
            "max_redirects_exceeded",
            "selected URL exceeded the redirect cap",
            failure_layer="url_fetch_read",
        )
    if fetch_result.fetched_byte_count > MAX_FETCHED_BYTES:
        raise SourceSurvivalError(
            "fetched_byte_cap_exceeded",
            "fetched response exceeds the 1 MB cap",
            failure_layer="url_fetch_read",
        )
    if not fetch_result.sanitized_text:
        raise SourceSurvivalError(
            "no_readable_text",
            "selected URL did not produce readable sanitized content",
            failure_layer="sanitized_readable_content",
        )


def _sanitized_fetch_read_material(
    *,
    selection: PriorCandidateSelection,
    fetch_result: FetchReadResult,
    bounded_text: str,
) -> dict[str, Any]:
    candidate = selection.selected_candidate
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "run_id": selection.candidate_packet["run_id"],
        "request_id": selection.candidate_packet["request_id"],
        "current_answer_contract_digest": selection.candidate_packet[
            "current_answer_contract_digest"
        ],
        "search_executor_handoff_digest": selection.candidate_packet[
            "search_executor_handoff_digest"
        ],
        "search_result_candidate_packet_id": selection.candidate_packet["packet_id"],
        "search_result_candidate_packet_digest": selection.candidate_packet[
            "packet_digest"
        ],
        "fetch_read_status": "readable",
        "attempted_url": candidate["url"],
        "resolved_url": fetch_result.final_url,
        "final_url": fetch_result.final_url,
        "resolved_domain": fetch_result.final_domain,
        "content_type": fetch_result.content_type,
        "retrieved_or_observed_at": fetch_result.retrieved_or_observed_at,
        "published_or_observed_date": candidate.get("published_or_observed_date"),
        "content_title": fetch_result.content_title or candidate.get("title"),
        "content_length": fetch_result.fetched_byte_count,
        "redirect_chain_digest": fetch_result.redirect_chain_digest,
        "redirect_count": fetch_result.redirect_count,
        "bounded_text": bounded_text,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(bounded_text),
        "raw_page_content_retained": False,
        "raw_page_text_retained": False,
        "raw_headers_retained": False,
        "raw_prompt_retained": False,
    }


def _base_packet(
    *,
    selection: PriorCandidateSelection,
    fetch_read_calls_attempted: int,
    fetch_read_calls_completed: int,
    selected_source_survived: str,
    likely_failure_layer: str | None,
    final_url: str | None,
    final_domain: str | None,
    http_status_class: str | None,
    content_type: str | None,
    fetched_byte_count: int,
    sanitized_readable_text: str | None,
    fetch_read_packet: Mapping[str, Any] | None,
    sanitized_content_reference: Mapping[str, Any] | None,
    evidence_ledger_projection: Mapping[str, Any] | None,
    output_dir: Path,
) -> dict[str, Any]:
    selected = selection.selected_candidate
    excerpt = _bounded_review_excerpt(sanitized_readable_text)
    content_digest = _digest_json({"bounded_text": excerpt}) if excerpt else None
    ledger_summary = _ledger_summary(evidence_ledger_projection)
    return _without_empty(
        {
            "phase": PHASE,
            "mode": MODE,
            "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
            "proof_class": PROOF_CLASS,
            "product_facing_progress_type": PRODUCT_FACING_PROGRESS_TYPE,
            "product_path_affected": PRODUCT_PATH_AFFECTED,
            "actual_app_delta": (
                "No installed product behavior changes; the local harness can "
                "test whether the rank-1 live candidate survives public "
                "fetch/read into existing bounded content and custody reducers."
            ),
            "runtime_consumer": (
                "existing FetchReadContentPacket builder/validator and "
                "EvidenceLedger candidate/content custody reducer"
            ),
            "actual_consumer_seam": ACTUAL_CONSUMER_SEAM,
            "user_facing_reviewable_output_delta": (
                "JSON/Markdown source-survival packets under "
                f"{_rel(output_dir)}"
            ),
            "non_product_exception_leash": (
                "This Proof phase is limited to source survival, fetch/read, "
                "and candidate/content custody because semantic support, "
                "coverage, readiness, citations, FAP, Author, answer text, "
                "and product correctness remain closed."
            ),
            "prior_phase_refs_and_digests": selection.prior_refs,
            "selected_candidate": {
                "candidate_id": selected.get("candidate_id"),
                "candidate_digest": selected.get("candidate_digest"),
                "record_digest": selected.get("record_digest"),
                "rank": selected.get("result_rank"),
                "title": selected.get("title"),
                "domain": selected.get("domain"),
                "url": selected.get("url"),
            },
            "live_budget": {
                "max_scry_raven_validation_runs": 1,
                "provider_search_calls": PROVIDER_CALLS,
                "broker_calls": BROKER_CALLS,
                "model_calls": MODEL_CALLS,
                "url_fetch_read_calls": MAX_FETCH_READ_CALLS,
                "max_redirects": MAX_REDIRECTS,
                "allowed_final_host": REQUIRED_DOMAIN,
                "max_fetched_bytes": MAX_FETCHED_BYTES,
                "max_sanitized_readable_text_retained_in_packet": (
                    MAX_REVIEW_SANITIZED_TEXT_CHARS
                ),
                "current_path_fetch_read_content_max_bounded_text_chars": (
                    FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS
                ),
                "evidence_ledger_candidate_content_custody_admissions": (
                    MAX_LEDGER_ADMISSIONS
                ),
                "retries": 0,
            },
            "fetch_read_calls_attempted": fetch_read_calls_attempted,
            "fetch_read_calls_completed": fetch_read_calls_completed,
            "final_url": final_url,
            "final_domain": final_domain,
            "http_status_class": http_status_class,
            "content_type": content_type,
            "fetched_byte_count": fetched_byte_count,
            "raw_html_retained": False,
            "raw_response_headers_retained": False,
            "raw_cookies_retained": False,
            "sanitized_readable_content_char_count": len(excerpt or ""),
            "sanitized_readable_content_digest": content_digest,
            "bounded_excerpt": excerpt,
            "bounded_excerpt_posture": {
                "review_debug_only": True,
                "not_answer_material": True,
                "not_citation_text": True,
                "not_semantic_support": True,
                "not_source_obligation_satisfaction": True,
            },
            "fetch_read_content_packet_ref": (
                fetch_read_content_packet_ref_from_packet(fetch_read_packet)
                if fetch_read_packet
                else {}
            ),
            "sanitized_content_reference_ref": (
                _content_reference_ref(sanitized_content_reference)
                if sanitized_content_reference
                else {}
            ),
            "evidence_ledger_candidate_content_custody_ref": ledger_summary.get(
                "ref"
            ),
            "evidence_ledger_candidate_content_custody_projection_summary": (
                ledger_summary
            ),
            "evidence_ledger_candidate_content_custody_count": ledger_summary.get(
                "custody_record_count",
                0,
            ),
            "selected_source_survived": selected_source_survived,
            "likely_failure_layer_if_not_pass": likely_failure_layer,
            "opened_surfaces": list(OPENED_SURFACES),
            "closed_surfaces": list(CLOSED_SURFACES),
            "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
            "budget_exhausted": fetch_read_calls_attempted >= MAX_FETCH_READ_CALLS,
            "budget_status": {
                "url_fetch_read_budget_exhausted": (
                    fetch_read_calls_attempted >= MAX_FETCH_READ_CALLS
                ),
                "provider_search_budget_exhausted": False,
                "broker_budget_exhausted": False,
                "model_budget_exhausted": False,
                "evidence_ledger_custody_budget_exhausted": (
                    ledger_summary.get("custody_record_count", 0)
                    >= MAX_LEDGER_ADMISSIONS
                ),
            },
            "semantic_observation_admissions": 0,
            "component_coverage_reductions": 0,
            "citation_eligibility_decisions": 0,
            "source_obligation_satisfaction_decisions": 0,
            "sufficiency_fap_author_authorprose_from_live_evidence": 0,
            "existing_machinery_reused": [
                "SearchResultCandidatePacket validator",
                "FetchReadContentPacket / SanitizedContentReference builder and validator",
                "EvidenceLedger candidate/content custody reducer",
                "RunKernel EvidenceLedger reduction authorization",
            ],
            "new_machinery_introduced": [
                "scripts/ag_live_source_survival_fetch_read_custody_01.py",
                "tests/test_ag_live_source_survival_fetch_read_custody_01.py",
                "docs/architecture/AG_LIVE_SOURCE_SURVIVAL_FETCH_READ_CUSTODY_01.md",
            ],
            "why_not_reinventing_existing_surface": (
                "The harness supplies only the bounded public fetch/read "
                "material needed by existing current-path reducers; it does "
                "not create a parallel content packet or custody authority."
            ),
            "old_path_treatment": (
                "Old Author/FAP/sufficiency/follow-up/pipeline/offline bridge "
                "surfaces remain closed, legacy, passive, or historical."
            ),
            "human_reviewable_product_output": (
                "structural proof packet only; no answer text or product prose"
            ),
            "live_validation_status": (
                "one public URL fetch/read licensed for fetch-read-custody only"
                if fetch_read_calls_attempted
                else "not run; operator confirmation pending"
            ),
            "mandatory_next_build_product_checkpoint": (
                MANDATORY_NEXT_BUILD_CHECKPOINT
            ),
        }
    )


def _survival_verdict(
    *,
    fetch_result: FetchReadResult,
    fetch_read_packet: Mapping[str, Any],
    ledger_projection: Mapping[str, Any],
) -> str:
    custody = _ledger_summary(ledger_projection)
    if (
        fetch_result.final_domain == REQUIRED_DOMAIN
        and fetch_result.sanitized_text
        and fetch_read_packet.get("reference_count") == 1
        and custody.get("readable_record_count") == 1
        and custody.get("custody_record_count") == 1
    ):
        return "source_survival_pass"
    if fetch_read_packet.get("reference_count") == 1 or custody.get(
        "custody_record_count"
    ):
        return "source_survival_partial"
    return "source_survival_fail"


def _ledger_summary(projection: Mapping[str, Any] | None) -> dict[str, Any]:
    if not projection:
        return {
            "ref": {},
            "custody_record_count": 0,
            "readable_record_count": 0,
            "candidate_content_custody_visible": False,
        }
    ledger = _safe_mapping(projection)
    custody = _safe_mapping(ledger.get("fetch_read_candidate_custody"))
    records = _safe_list(custody.get("fetch_read_candidate_custody_records"))
    first = _safe_mapping(records[0]) if records else {}
    ref = _without_empty(
        {
            "ledger_owner": ledger.get("owner"),
            "ledger_schema_version": ledger.get("schema_version"),
            "trace_key": custody.get("trace_key"),
            "custody_record_id": first.get("reference_id"),
            "custody_record_digest": first.get("reference_digest"),
            "fetch_read_content_packet_id": first.get(
                "fetch_read_content_packet_id"
            ),
            "fetch_read_content_packet_digest": first.get(
                "fetch_read_content_packet_digest"
            ),
        }
    )
    return {
        "ref": ref,
        "schema_version": custody.get("schema_version"),
        "owner": custody.get("owner"),
        "candidate_content_custody_visible": custody.get(
            "candidate_content_custody_visible",
            False,
        ),
        "custody_record_count": custody.get("custody_record_count", 0),
        "readable_record_count": custody.get("readable_record_count", 0),
        "unreadable_record_count": custody.get("unreadable_record_count", 0),
        "candidate_content_custody_is_semantic_support": custody.get(
            "candidate_content_custody_is_semantic_support",
            False,
        ),
        "citation_eligible": custody.get("citation_eligible", False),
        "source_obligation_satisfied": custody.get(
            "source_obligation_satisfied",
            False,
        ),
        "component_coverage_created": custody.get(
            "component_coverage_created",
            False,
        ),
        "sufficiency_decided": custody.get("sufficiency_decided", False),
        "final_answer_packet_created": custody.get(
            "final_answer_packet_created",
            False,
        ),
        "author_input_created": custody.get("author_input_created", False),
        "bounded_content_payload_retained": _safe_mapping(
            custody.get("behavior_boundary_flags")
        ).get("bounded_content_payload_retained", False),
    }


def _content_reference_ref(reference: Mapping[str, Any] | None) -> dict[str, Any]:
    safe = _safe_mapping(reference)
    return _without_empty(
        {
            "reference_id": safe.get("reference_id"),
            "reference_digest": safe.get("reference_digest"),
            "candidate_id": safe.get("candidate_id"),
            "candidate_digest": safe.get("candidate_digest"),
            "fetch_read_status": safe.get("fetch_read_status"),
            "bounded_text_char_count": safe.get("bounded_character_count"),
            "bounded_text_digest": safe.get("excerpt_digest"),
            "not_semantic_support": safe.get("not_semantic_support"),
            "not_citation_eligible": safe.get("not_citation_eligible"),
        }
    )


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


def _bounded_current_path_text(text: str) -> str:
    collapsed = _collapse_text(text)
    if len(collapsed) > FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS:
        return collapsed[:FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS].rstrip()
    return collapsed


def _bounded_review_excerpt(text: str | None) -> str | None:
    if not text:
        return None
    collapsed = _collapse_text(text)
    limit = min(MAX_REVIEW_SANITIZED_TEXT_CHARS, FETCH_READ_CONTENT_MAX_BOUNDED_TEXT_CHARS)
    return collapsed[:limit].rstrip()


def _rank_one_candidate(packet: Mapping[str, Any]) -> dict[str, Any]:
    records = [
        dict(record)
        for record in _safe_list(packet.get("candidate_records"))
        if isinstance(record, Mapping) and record.get("result_rank") == SELECTED_RANK
    ]
    if len(records) != 1:
        raise SourceSurvivalError(
            "prior_candidate_packet_missing_or_mismatched",
            "prior_candidate_packet_missing_or_mismatched",
            failure_layer="prior_candidate_packet",
        )
    return records[0]


def _rank_one_validation_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    summaries = _safe_list(packet.get("sanitized_provider_result_summaries"))
    for summary in summaries:
        if isinstance(summary, Mapping) and summary.get("rank") == SELECTED_RANK:
            return dict(summary)
    raise SourceSurvivalError(
        "prior_candidate_packet_missing_or_mismatched",
        "prior_candidate_packet_missing_or_mismatched",
        failure_layer="prior_candidate_packet",
    )


def _operator_command(
    *,
    candidate_packet_path: str | Path,
    validation_packet_path: str | Path,
    output_dir: Path,
) -> str:
    return "\n".join(
        [
            "py scripts\\ag_live_source_survival_fetch_read_custody_01.py fetch-read-custody `",
            f"  --candidate-packet {_rel(candidate_packet_path)} `",
            f"  --validation-packet {_rel(validation_packet_path)} `",
            f"  --output-dir {_rel(output_dir)} `",
            "  --confirm-fetch-read",
        ]
    )


def _request_markdown(packet: Mapping[str, Any]) -> str:
    selected = packet["selected_candidate"]
    non_proofs = "\n".join(f"- {item}" for item in packet["explicit_non_proofs"])
    return (
        f"# {PHASE} Request Packet\n\n"
        f"Mode: `{packet['mode']}`\n\n"
        f"Usable-answer verdict target: `{packet['usable_answer_verdict_target']}`\n\n"
        f"Selected candidate: rank `{selected['rank']}` / `{selected['domain']}`\n\n"
        f"URL: `{selected['url']}`\n\n"
        "This request packet performs no fetch/read. The live command requires "
        "`--confirm-fetch-read` and may make exactly one public URL fetch/read.\n\n"
        "## Operator Command\n\n"
        "```powershell\n"
        f"{packet['operator_command']}\n"
        "```\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n"
    )


def _source_markdown(packet: Mapping[str, Any]) -> str:
    selected = packet["selected_candidate"]
    non_proofs = "\n".join(f"- {item}" for item in packet["explicit_non_proofs"])
    return (
        f"# {PHASE} Source Survival Packet\n\n"
        f"Mode: `{packet['mode']}`\n\n"
        f"Selected candidate: rank `{selected['rank']}` / `{selected['domain']}`\n\n"
        f"URL: `{selected['url']}`\n\n"
        "Fetch/read calls attempted/completed: "
        f"`{packet['fetch_read_calls_attempted']}` / "
        f"`{packet['fetch_read_calls_completed']}`\n\n"
        f"Source survival verdict: `{packet['selected_source_survived']}`\n\n"
        f"Failure layer: `{packet.get('likely_failure_layer_if_not_pass')}`\n\n"
        "## Custody\n\n"
        "FetchReadContentPacket: "
        f"`{packet.get('fetch_read_content_packet_ref', {}).get('packet_id')}`\n\n"
        "EvidenceLedger custody records: "
        f"`{packet.get('evidence_ledger_candidate_content_custody_count', 0)}`\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n\n"
        "Mandatory next Build/product checkpoint: "
        f"`{packet['mandatory_next_build_product_checkpoint']}`\n"
    )


def _phase_output_dir(path: str | Path) -> Path:
    resolved = _resolve_under(path, DEFAULT_OUTPUT_DIR, "output-dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _phase_output_path(path: str | Path) -> Path:
    return _resolve_under(path, DEFAULT_OUTPUT_DIR, "output path")


def _prior_output_path(path: str | Path) -> Path:
    return _resolve_under(path, DEFAULT_PRIOR_OUTPUT_DIR, "prior output path")


def _resolve_under(path: str | Path, root: Path, label: str) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    resolved = raw.resolve()
    allowed = root.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise SourceSurvivalError(
            "path_outside_phase_scope",
            f"{label} must stay under {_rel(allowed)}",
            failure_layer="path_scope",
        ) from exc
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, Mapping):
        raise SourceSurvivalError("json_packet_must_be_object")
    return dict(decoded)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    resolved = _phase_output_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reject_forbidden_packet_material(value: Any) -> None:
    keys = _collect_keys(value)
    raw_keys = sorted(
        key
        for key in keys
        if key not in _SAFE_FALSE_KEYS
        and (key.startswith("raw_") or key in _FORBIDDEN_RAW_KEYS)
    )
    if raw_keys:
        raise SourceSurvivalError(
            "source_survival_packet_contains_raw_or_private_fields",
            ", ".join(raw_keys),
        )
    authority = sorted(keys & _FORBIDDEN_AUTHORITY_KEYS)
    if authority:
        raise SourceSurvivalError(
            "source_survival_packet_contains_closed_authority_fields",
            ", ".join(authority),
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise SourceSurvivalError(
            "source_survival_packet_opens_closed_surfaces",
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


def _allowed_final_domain(domain: str | None) -> bool:
    if not domain:
        return False
    normalized = domain.casefold()
    return (
        normalized == REQUIRED_DOMAIN
        or normalized == "state.gov"
        or normalized.endswith(".state.gov")
    )


def _domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).netloc.casefold() or None


def _collapse_text(text: Any) -> str:
    decoded = unescape(str(text or ""))
    decoded = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", decoded)
    return " ".join(decoded.split())


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    text = _collapse_text(value)
    return text[:limit] if text else None


def _file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _digest_json(value: Any) -> str:
    encoded = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    safe = _json_safe(dict(value))
    return dict(safe) if isinstance(safe, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    safe = _json_safe(list(value))
    return list(safe) if isinstance(safe, list) else []


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
        if value is not None and value != [] and value != {}
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


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
            "Prepare and run AG-LIVE source-survival fetch/read custody packets. "
            "Only fetch-read-custody with --confirm-fetch-read may make the one "
            "licensed public URL fetch/read call."
        )
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    prepare = subparsers.add_parser("prepare-request")
    prepare.add_argument("--candidate-packet", default=str(DEFAULT_CANDIDATE_PACKET))
    prepare.add_argument("--validation-packet", default=str(DEFAULT_VALIDATION_PACKET))
    prepare.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    fetch = subparsers.add_parser("fetch-read-custody")
    fetch.add_argument("--candidate-packet", default=str(DEFAULT_CANDIDATE_PACKET))
    fetch.add_argument("--validation-packet", default=str(DEFAULT_VALIDATION_PACKET))
    fetch.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    fetch.add_argument("--confirm-fetch-read", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.operation == "prepare-request":
            packet = prepare_request(
                candidate_packet_path=args.candidate_packet,
                validation_packet_path=args.validation_packet,
                output_dir=args.output_dir,
            )
        else:
            packet = fetch_read_custody(
                candidate_packet_path=args.candidate_packet,
                validation_packet_path=args.validation_packet,
                output_dir=args.output_dir,
                confirm_fetch_read=args.confirm_fetch_read,
            )
    except SourceSurvivalError as exc:
        print(exc.code, file=sys.stderr)
        return 2
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(
            f"refusing AG-LIVE source-survival operation: {exc}",
            file=sys.stderr,
        )
        return 2

    summary = {
        "phase": PHASE,
        "operation": args.operation,
        "output_dir": str(Path(args.output_dir)),
        "selected_source_survived": packet.get("selected_source_survived"),
        "fetch_read_calls_attempted": packet.get("fetch_read_calls_attempted"),
        "fetch_read_calls_completed": packet.get("fetch_read_calls_completed"),
        "selected_url": packet.get("selected_candidate", {}).get("url"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
