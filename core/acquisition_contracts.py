"""Immutable contracts for bounded provider-neutral acquisition execution.

These records carry completed ``core.routing`` decisions into mechanical
adapters.  They describe acquisition material and lineage only; they grant no
evidence, citation, obligation, Sufficiency, FinalAnswerPacket, or Author
authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping
from urllib.parse import urlparse

from core.routing import AcquisitionCapability, ProviderRouteDecision

FOCUS_TEXT_MAX_CHARACTERS = 2_000
SELECTED_URL_MAX_COUNT = 20
READ_RETAINED_CHARACTER_CEILING = 20_000
MAP_RETURNED_URL_CEILING = 100
CRAWL_DEPTH_CEILING = 2
CRAWL_PAGE_CEILING = 10
CRAWL_PAGE_RETAINED_CHARACTER_CEILING = 20_000
CRAWL_AGGREGATE_RETAINED_CHARACTER_CEILING = 100_000
GENERAL_DEEP_QUERY_CEILING = 2
GENERAL_DEEP_RESULTS_PER_QUERY_CEILING = 5


class AcquisitionArtifactKind(str, Enum):
    DISCOVERY_CANDIDATE = "discovery_candidate_material"
    SELECTED_URL_READ = "selected_url_read_material"
    FOCUSED_SELECTED_URL_EXTRACTION = "focused_selected_url_extraction"
    SITE_URL_TOPOLOGY = "site_url_topology"
    BOUNDED_PAGE_COLLECTION = "bounded_page_collection"
    PROVIDER_FAILURE = "typed_provider_failure"
    POLICY_BLOCK = "typed_policy_or_availability_block"


class AcquisitionExecutionStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class AcquisitionContractError(ValueError):
    """Typed validation failure that must block before provider transport."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    """One bounded acquisition job carrying a completed route decision."""

    acquisition_job_id: str
    route_decision: ProviderRouteDecision
    parent_acquisition_job_id: str | None = None
    acquisition_lineage_id: str | None = None
    query_reference: str | None = None
    selected_urls: tuple[str, ...] = ()
    root_url: str | None = None
    render_javascript: bool = False
    queries: tuple[str, ...] = ()
    focus_text: str | None = None
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    include_path_prefix: str | None = None
    exclude_path_prefixes: tuple[str, ...] = ()
    max_results: int = 5
    max_pages: int = 0
    max_depth: int = 0
    max_retained_characters: int = READ_RETAINED_CHARACTER_CEILING
    max_aggregate_retained_characters: int = (
        CRAWL_AGGREGATE_RETAINED_CHARACTER_CEILING
    )
    crawl_job_ordinal: int = 1
    candidate_reference: str | None = None
    obligation_reference: str | None = None

    @property
    def capability(self) -> AcquisitionCapability:
        return self.route_decision.capability

    @property
    def provider(self) -> str | None:
        return self.route_decision.selected_provider

    @property
    def operation(self) -> str | None:
        return self.route_decision.operation

    def to_trace(self) -> dict[str, Any]:
        return _without_empty(
            {
                "acquisition_job_id": self.acquisition_job_id,
                "parent_acquisition_job_id": self.parent_acquisition_job_id,
                "acquisition_lineage_id": self.acquisition_lineage_id,
                "capability": self.capability.value,
                "route_decision": self.route_decision.to_trace(),
                "selected_urls": list(self.selected_urls),
                "root_url": self.root_url,
                "render_javascript": self.render_javascript,
                "query_count": len(self.queries),
                "focus_character_count": len(self.focus_text or ""),
                "include_domains": list(self.include_domains),
                "exclude_domains": list(self.exclude_domains),
                "include_path_prefix": self.include_path_prefix,
                "exclude_path_prefixes": list(self.exclude_path_prefixes),
                "max_results": self.max_results,
                "max_pages": self.max_pages,
                "max_depth": self.max_depth,
                "max_retained_characters": self.max_retained_characters,
                "max_aggregate_retained_characters": (
                    self.max_aggregate_retained_characters
                ),
                "crawl_job_ordinal": self.crawl_job_ordinal,
                "candidate_reference": self.candidate_reference,
                "query_reference": self.query_reference,
                "obligation_reference": self.obligation_reference,
                "provider_synthesis_disabled": True,
                "authority_posture": "acquisition_material_only",
            }
        )


@dataclass(frozen=True, slots=True)
class AcquisitionPageArtifact:
    status: str
    observed_at: str
    requested_url: str | None = None
    attempted_url: str | None = None
    provider_reported_url: str | None = None
    resolved_url: str | None = None
    final_url: str | None = None
    canonical_url: str | None = None
    parent_url: str | None = None
    content_type: str | None = None
    http_status: int | None = None
    title: str | None = None
    retained_text: str | None = None
    retained_character_count: int = 0
    retained_digest: str | None = None
    truncation_posture: str = "not_truncated"

    def to_dict(self, *, include_ephemeral_text: bool = False) -> dict[str, Any]:
        excluded = set() if include_ephemeral_text else {"retained_text"}
        return _without_empty(
            {
                name: getattr(self, name)
                for name in self.__dataclass_fields__
                if name not in excluded
            }
        )


@dataclass(frozen=True, slots=True)
class AcquisitionArtifact:
    kind: AcquisitionArtifactKind
    provider: str
    operation: str
    provider_variant: str
    output_type: str
    acquisition_job_id: str
    status: str
    observed_at: str
    parent_acquisition_job_id: str | None = None
    acquisition_lineage_id: str | None = None
    requested_url: str | None = None
    attempted_url: str | None = None
    provider_reported_url: str | None = None
    resolved_url: str | None = None
    final_url: str | None = None
    canonical_url: str | None = None
    root_url: str | None = None
    parent_url: str | None = None
    candidate_reference: str | None = None
    query_reference: str | None = None
    obligation_reference: str | None = None
    content_type: str | None = None
    http_status: int | None = None
    title: str | None = None
    retained_text: str | None = None
    retained_character_count: int = 0
    retained_digest: str | None = None
    urls: tuple[str, ...] = ()
    pages: tuple[AcquisitionPageArtifact, ...] = ()
    truncation_posture: str = "not_truncated"
    failure_code: str | None = None
    failure_reason: str | None = None
    authority_posture: str = "acquisition_material_only"

    def to_dict(self, *, include_ephemeral_text: bool = False) -> dict[str, Any]:
        payload = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name not in {"kind", "pages", "retained_text"}
        }
        payload.update(
            {
                "kind": self.kind.value,
                "pages": [
                    page.to_dict(include_ephemeral_text=include_ephemeral_text)
                    for page in self.pages
                ],
                "raw_html_retained": False,
                "raw_provider_payload_retained": False,
                "headers_or_cookies_retained": False,
                "evidence_authority_granted": False,
                "citation_authority_granted": False,
                "source_obligation_satisfied": False,
                "sufficiency_decided": False,
                "final_answer_authority_granted": False,
            }
        )
        if include_ephemeral_text and self.retained_text is not None:
            payload["retained_text"] = self.retained_text
        return _without_empty(payload)


@dataclass(frozen=True, slots=True)
class AcquisitionExecutionResult:
    request: AcquisitionRequest
    status: AcquisitionExecutionStatus
    artifacts: tuple[AcquisitionArtifact, ...] = ()
    provider_calls_attempted: int = 0
    provider_calls_completed: int = 0
    block_code: str | None = None
    failure_code: str | None = None
    detail: str | None = None
    transport_posture: str = "zero_transport"

    @property
    def succeeded(self) -> bool:
        return self.status is AcquisitionExecutionStatus.SUCCEEDED

    @property
    def blocked(self) -> bool:
        return self.status is AcquisitionExecutionStatus.BLOCKED

    def to_trace(self) -> dict[str, Any]:
        return _without_empty(
            {
                "request": self.request.to_trace(),
                "status": self.status.value,
                "artifact_count": len(self.artifacts),
                "artifact_refs": [
                    artifact.to_dict(include_ephemeral_text=False)
                    for artifact in self.artifacts
                ],
                "provider_calls_attempted": self.provider_calls_attempted,
                "provider_calls_completed": self.provider_calls_completed,
                "block_code": self.block_code,
                "failure_code": self.failure_code,
                "detail": self.detail,
                "transport_posture": self.transport_posture,
                "provider_failure_fallback_attempted": False,
                "provider_synthesis_disabled": True,
            }
        )


def validate_acquisition_request(request: AcquisitionRequest) -> None:
    """Validate operation bounds without consulting transport state."""

    if not _token(request.acquisition_job_id, limit=200):
        raise AcquisitionContractError(
            "acquisition_job_id_missing",
            "acquisition requests require an acquisition_job_id",
        )
    if not isinstance(request.render_javascript, bool):
        raise AcquisitionContractError(
            "render_javascript_invalid",
            "render_javascript must be an explicit boolean posture",
        )
    decision = request.route_decision
    if decision.blocked or decision.selected_provider is None:
        raise AcquisitionContractError(
            "completed_route_decision_blocked",
            decision.block_reason or "acquisition route is blocked",
        )
    if decision.capability is AcquisitionCapability.PROVIDER_SYNTHESIS:
        raise AcquisitionContractError(
            "provider_synthesis_disabled",
            "provider synthesis cannot be dispatched",
        )

    selected_urls = tuple(_required_url(url, "selected_url_invalid") for url in request.selected_urls)
    if len(selected_urls) > SELECTED_URL_MAX_COUNT:
        raise AcquisitionContractError(
            "selected_url_count_exceeded",
            f"selected URL count exceeds {SELECTED_URL_MAX_COUNT}",
        )

    if request.capability is AcquisitionCapability.READ:
        if len(selected_urls) != 1:
            raise AcquisitionContractError(
                "read_requires_one_selected_url",
                "READ requires exactly one caller-selected URL",
            )
        if not 1 <= int(request.max_retained_characters) <= READ_RETAINED_CHARACTER_CEILING:
            raise AcquisitionContractError(
                "read_retained_character_ceiling_exceeded",
                f"READ retained characters must be within 1..{READ_RETAINED_CHARACTER_CEILING}",
            )
    elif request.capability is AcquisitionCapability.FOCUSED_EXTRACT:
        if not selected_urls:
            raise AcquisitionContractError(
                "focused_extract_requires_selected_urls",
                "FOCUSED_EXTRACT requires caller-selected URLs",
            )
        focus = _text(request.focus_text, limit=FOCUS_TEXT_MAX_CHARACTERS + 1)
        if not focus or len(focus) > FOCUS_TEXT_MAX_CHARACTERS:
            raise AcquisitionContractError(
                "focused_extract_focus_invalid",
                f"FOCUSED_EXTRACT focus must be within 1..{FOCUS_TEXT_MAX_CHARACTERS} characters",
            )
        if not 1 <= int(request.max_retained_characters) <= READ_RETAINED_CHARACTER_CEILING:
            raise AcquisitionContractError(
                "focused_extract_retained_character_ceiling_exceeded",
                f"FOCUSED_EXTRACT retained characters must be within 1..{READ_RETAINED_CHARACTER_CEILING}",
            )
    elif request.capability is AcquisitionCapability.MAP_SITE:
        root = _required_url(request.root_url, "map_root_url_invalid")
        if selected_urls:
            raise AcquisitionContractError(
                "map_selected_urls_forbidden",
                "MAP_SITE accepts a root URL, not selected evidence URLs",
            )
        if not 1 <= int(request.max_results) <= MAP_RETURNED_URL_CEILING:
            raise AcquisitionContractError(
                "map_url_ceiling_exceeded",
                f"MAP_SITE result ceiling is {MAP_RETURNED_URL_CEILING}",
            )
        _validate_allowed_domain(request, root)
    elif request.capability is AcquisitionCapability.CRAWL_SITE:
        root = _required_url(request.root_url, "crawl_root_url_invalid")
        if not 1 <= int(request.max_depth) <= CRAWL_DEPTH_CEILING:
            raise AcquisitionContractError(
                "crawl_depth_ceiling_exceeded",
                f"CRAWL_SITE depth ceiling is {CRAWL_DEPTH_CEILING}",
            )
        if not 1 <= int(request.max_pages) <= CRAWL_PAGE_CEILING:
            raise AcquisitionContractError(
                "crawl_page_ceiling_exceeded",
                f"CRAWL_SITE page ceiling is {CRAWL_PAGE_CEILING}",
            )
        if not 1 <= int(request.max_retained_characters) <= CRAWL_PAGE_RETAINED_CHARACTER_CEILING:
            raise AcquisitionContractError(
                "crawl_page_character_ceiling_exceeded",
                "CRAWL_SITE per-page retained-character ceiling exceeded",
            )
        if not 1 <= int(request.max_aggregate_retained_characters) <= CRAWL_AGGREGATE_RETAINED_CHARACTER_CEILING:
            raise AcquisitionContractError(
                "crawl_aggregate_character_ceiling_exceeded",
                "CRAWL_SITE aggregate retained-character ceiling exceeded",
            )
        if int(request.crawl_job_ordinal) != 1:
            raise AcquisitionContractError(
                "crawl_job_authorization_exhausted",
                "only one crawl job is allowed per acquisition authorization",
            )
        _validate_allowed_domain(request, root)
    elif request.capability is AcquisitionCapability.DISCOVER:
        if not request.queries or len(request.queries) > GENERAL_DEEP_QUERY_CEILING:
            raise AcquisitionContractError(
                "discover_query_count_invalid",
                f"bounded DISCOVER jobs require 1..{GENERAL_DEEP_QUERY_CEILING} queries",
            )
        if decision.variant == "deep":
            authorization = decision.request.general_deep_authorization
            if (
                not decision.request.general_deep_requested
                or authorization is None
                or not authorization.valid
            ):
                raise AcquisitionContractError(
                    "general_deep_authorization_required",
                    "general Linkup Deep requires explicit bounded authorization",
                )
            if len(request.queries) != 1 or request.queries[0] not in authorization.queries:
                raise AcquisitionContractError(
                    "general_deep_query_not_authorized",
                    "each Deep search job must carry one authorized query",
                )
            if (
                request.parent_acquisition_job_id
                != authorization.parent_standard_acquisition_job_id
                or request.acquisition_lineage_id
                != authorization.acquisition_lineage_id
                or request.obligation_reference != authorization.obligation_reference
            ):
                raise AcquisitionContractError(
                    "general_deep_lineage_mismatch",
                    "general Linkup Deep must preserve parent, acquisition, and obligation lineage",
                )
            if not 1 <= int(request.max_results) <= min(
                GENERAL_DEEP_RESULTS_PER_QUERY_CEILING,
                int(authorization.max_results_per_query),
            ):
                raise AcquisitionContractError(
                    "general_deep_result_ceiling_exceeded",
                    "general Linkup Deep result count exceeds its authorization",
                )


def retained_text_digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def normalized_host(url: str) -> str:
    host = (urlparse(url).hostname or "").casefold().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def url_is_within_request_scope(url: str, request: AcquisitionRequest) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = normalized_host(url)
    allowed = tuple(_domain(domain) for domain in request.include_domains if _domain(domain))
    if request.root_url and not allowed:
        allowed = (normalized_host(request.root_url),)
    if allowed and not any(host == item or host.endswith(f".{item}") for item in allowed):
        return False
    denied = tuple(_domain(domain) for domain in request.exclude_domains if _domain(domain))
    if any(host == item or host.endswith(f".{item}") for item in denied):
        return False
    path = parsed.path or "/"
    if request.include_path_prefix and not path.startswith(request.include_path_prefix):
        return False
    if any(path.startswith(prefix) for prefix in request.exclude_path_prefixes):
        return False
    return True


def compact_failure_detail(value: Any, *, limit: int = 400) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:limit] or "acquisition_failed_closed"


def _validate_allowed_domain(request: AcquisitionRequest, root_url: str) -> None:
    root_host = normalized_host(root_url)
    if not root_host:
        raise AcquisitionContractError(
            "root_domain_missing",
            "site acquisition requires a root domain",
        )
    allowed = tuple(_domain(domain) for domain in request.include_domains if _domain(domain))
    if allowed and not any(
        root_host == domain or root_host.endswith(f".{domain}")
        for domain in allowed
    ):
        raise AcquisitionContractError(
            "root_domain_not_allowed",
            "site acquisition root must match its allowed domain",
        )


def _required_url(value: Any, code: str) -> str:
    text = _text(value, limit=2_000)
    parsed = urlparse(text or "")
    if not text or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AcquisitionContractError(code, "acquisition URL must be absolute HTTP(S)")
    return text


def _domain(value: Any) -> str:
    text = _text(value, limit=260) or ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").casefold().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _text(value: Any, *, limit: int) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _token(value: Any, *, limit: int) -> str | None:
    text = _text(value, limit=limit)
    return text.casefold().replace(" ", "_") if text else None


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in payload.items()
        if value is not None and value != [] and value != () and value != {}
    }


def stable_json_digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "AcquisitionArtifact",
    "AcquisitionArtifactKind",
    "AcquisitionContractError",
    "AcquisitionExecutionResult",
    "AcquisitionExecutionStatus",
    "AcquisitionPageArtifact",
    "AcquisitionRequest",
    "CRAWL_AGGREGATE_RETAINED_CHARACTER_CEILING",
    "CRAWL_DEPTH_CEILING",
    "CRAWL_PAGE_CEILING",
    "CRAWL_PAGE_RETAINED_CHARACTER_CEILING",
    "FOCUS_TEXT_MAX_CHARACTERS",
    "GENERAL_DEEP_QUERY_CEILING",
    "GENERAL_DEEP_RESULTS_PER_QUERY_CEILING",
    "MAP_RETURNED_URL_CEILING",
    "READ_RETAINED_CHARACTER_CEILING",
    "SELECTED_URL_MAX_COUNT",
    "compact_failure_detail",
    "normalized_host",
    "retained_text_digest",
    "stable_json_digest",
    "url_is_within_request_scope",
    "validate_acquisition_request",
]
