"""Bounded, URL-safe SearchOS breadcrumb-navigation contracts.

This module is the neutral substrate for SearchOS Slice B.  Exact link
destinations live only in the transient draft, destination registry, and
one-shot execution overlay.  Canonical values produced here contain opaque
digests, safe structural facts, and exact authority refs; they never contain a
raw href, path, query, or reconstructable execution URL.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urljoin, urlsplit, urlunsplit

SEARCHOS_NAVIGATION_OWNER = "RunKernel.SearchOSBreadcrumbNavigation"

SEARCHOS_NAVIGATION_CANDIDATE_SET_SCHEMA_VERSION = (
    "searchos_navigation_candidate_set_v1"
)
SEARCHOS_NAVIGATION_OPTION_IDENTITY_SCHEMA_VERSION = (
    "searchos_navigation_option_identity_v1"
)
SEARCHOS_NAVIGATION_LINEAGE_SNAPSHOT_SCHEMA_VERSION = (
    "searchos_navigation_lineage_snapshot_v1"
)
SEARCHOS_NAVIGATION_OPTION_STATE_SCHEMA_VERSION = (
    "searchos_navigation_option_state_v1"
)
SEARCHOS_NAVIGATION_CANDIDATE_REF_SCHEMA_VERSION = (
    "searchos_navigation_candidate_ref_v1"
)
SEARCHOS_NAVIGATION_SELECTION_SCHEMA_VERSION = (
    "searchos_navigation_selection_v1"
)
SEARCHOS_NAVIGATION_EDGE_SCHEMA_VERSION = "searchos_navigation_edge_v1"
SEARCHOS_NAVIGATION_USE_CUSTODY_REF_SCHEMA_VERSION = (
    "searchos_navigation_use_custody_ref_v2"
)
SEARCHOS_NAVIGATION_RETAINED_STATE_SCHEMA_VERSION = (
    "searchos_navigation_retained_state_v1"
)

NAVIGATION_RETAINED_TEXT_CEILING = 20_000
NAVIGATION_EXTRACTED_OCCURRENCE_CEILING = 48
NAVIGATION_MODEL_WINDOW_CEILING = 12
NAVIGATION_CONTRIBUTORS_PER_OPTION_CEILING = 8
NAVIGATION_STABLE_OPTION_CEILING = 384
NAVIGATION_CONTRIBUTOR_CEILING = 768
NAVIGATION_LINEAGE_GENERATION_CEILING = 512
NAVIGATION_CANDIDATE_SET_CEILING = 32
NAVIGATION_DEEP_EDGE_CEILING = 24
NAVIGATION_REQUIRED_SLOT_RESERVE = 2
NAVIGATION_URL_LENGTH_CEILING = 700
NAVIGATION_MAX_DEPTH = 2

NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED = (
    "navigation_query_locator_not_supported"
)
NAVIGATION_EFFECTIVE_BASE_OUT_OF_SCOPE = (
    "navigation_effective_base_out_of_scope"
)
NAVIGATION_DESTINATION_BINDING_UNAVAILABLE = (
    "navigation_destination_binding_unavailable"
)
NAVIGATION_CANDIDATE_SET_CAPACITY_EXHAUSTED = (
    "navigation_candidate_set_capacity_exhausted"
)
NAVIGATION_DURABLE_SOURCE_IDENTITY_INVALID = (
    "navigation_durable_source_identity_invalid"
)
NAVIGATION_REDIRECT_CROSS_DOMAIN_BLOCKED = (
    "navigation_redirect_cross_domain_blocked"
)

_DESTINATION_BINDING_REF_FIELDS = frozenset(
    {
        "destination_binding_id",
        "destination_binding_digest",
        "full_destination_digest",
        "semantic_identity_digest",
        "physical_identity_digest",
        "normalized_scheme",
        "normalized_hostname",
        "port_posture",
        "path_digest",
        "query_present",
    }
)


class SearchOSNavigationError(ValueError):
    """Fail-closed navigation contract or transition error."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True, slots=True)
class _NormalizedNavigationURL:
    exact_url: str
    scheme: str
    hostname: str
    port: int | None
    port_posture: str
    path: str
    query: str
    full_digest: str
    semantic_digest: str
    physical_digest: str

    @property
    def query_present(self) -> bool:
        return bool(self.query)


@dataclass(frozen=True, slots=True)
class SearchOSNavigationExtractedOccurrence:
    """One exact occurrence retained only inside a transient draft."""

    resolved_destination: str
    normalized_destination: _NormalizedNavigationURL
    source_ordinal: int
    relationship_label: str
    label_digest: str
    href_digest: str


class SearchOSNavigationExtractionDraftV1:
    """Local URL-bearing extraction draft with explicit destruction.

    Deliberately has no ``to_dict``/JSON projection.  It grants no authority
    and must be joined to exact physical and parent-use custody before any
    canonical candidate set can be produced.
    """

    __slots__ = (
        "run_id",
        "request_id",
        "operation_identity_key",
        "source_obligation_ref",
        "component_ref",
        "answer_contract_ref",
        "artifact_ref",
        "physical_acquisition_ref",
        "retained_digest",
        "retained_character_count",
        "attempted_parent_url",
        "attempted_parent_full_digest",
        "attempted_parent_physical_digest",
        "effective_base_url",
        "effective_base_status",
        "occurrences",
        "extraction_counters",
        "overflow_digest",
        "_destroyed",
    )

    def __init__(
        self,
        *,
        run_id: str,
        request_id: str,
        operation_identity_key: str,
        source_obligation_ref: Mapping[str, Any],
        component_ref: Mapping[str, Any],
        answer_contract_ref: Mapping[str, Any],
        artifact_ref: Mapping[str, Any],
        physical_acquisition_ref: Mapping[str, Any],
        retained_digest: str,
        retained_character_count: int,
        attempted_parent_url: str,
        attempted_parent_full_digest: str,
        attempted_parent_physical_digest: str,
        effective_base_url: str | None,
        effective_base_status: str,
        occurrences: Sequence[SearchOSNavigationExtractedOccurrence],
        extraction_counters: Mapping[str, int],
        overflow_digest: str,
    ) -> None:
        self.run_id = _token(run_id, "run_id")
        self.request_id = _token(request_id, "request_id")
        self.operation_identity_key = _token(
            operation_identity_key, "operation_identity_key"
        )
        self.source_obligation_ref = _required_ref(
            source_obligation_ref, "source_obligation_ref"
        )
        self.component_ref = _required_ref(component_ref, "component_ref")
        self.answer_contract_ref = _required_ref(
            answer_contract_ref, "answer_contract_ref"
        )
        self.artifact_ref = _artifact_ref(artifact_ref)
        self.physical_acquisition_ref = _required_ref(
            physical_acquisition_ref, "physical_acquisition_ref"
        )
        self.retained_digest = _digest_token(
            retained_digest, "retained_digest"
        )
        self.retained_character_count = _bounded_nonnegative_int(
            retained_character_count,
            "retained_character_count",
            maximum=NAVIGATION_RETAINED_TEXT_CEILING,
        )
        self.attempted_parent_url = attempted_parent_url
        self.attempted_parent_full_digest = _digest_token(
            attempted_parent_full_digest, "attempted_parent_full_digest"
        )
        self.attempted_parent_physical_digest = _digest_token(
            attempted_parent_physical_digest,
            "attempted_parent_physical_digest",
        )
        self.effective_base_url = effective_base_url
        self.effective_base_status = _token(
            effective_base_status, "effective_base_status"
        )
        self.occurrences = tuple(occurrences)
        self.extraction_counters = dict(extraction_counters)
        self.overflow_digest = _digest_token(
            overflow_digest, "overflow_digest"
        )
        self._destroyed = False

    @property
    def destroyed(self) -> bool:
        return self._destroyed

    def require_live(self) -> None:
        if self._destroyed:
            raise SearchOSNavigationError("navigation_extraction_draft_destroyed")

    def destroy(self) -> None:
        self.occurrences = ()
        self.effective_base_url = None
        self.attempted_parent_url = ""
        self._destroyed = True

    def __reduce__(self) -> Any:
        raise TypeError("navigation extraction drafts are nonserializable")


class SearchOSNavigationDestinationRegistry:
    """Bounded run-local exact destination owner; never canonical state."""

    __slots__ = ("run_id", "request_id", "capacity", "_by_id", "_closed")

    def __init__(
        self,
        *,
        run_id: str,
        request_id: str,
        capacity: int = NAVIGATION_STABLE_OPTION_CEILING,
    ) -> None:
        self.run_id = _token(run_id, "run_id")
        self.request_id = _token(request_id, "request_id")
        self.capacity = _bounded_positive_int(capacity, "registry_capacity")
        self._by_id: dict[str, _NormalizedNavigationURL] = {}
        self._closed = False

    def register(self, exact_url: str) -> dict[str, Any]:
        self._require_open()
        normalized = normalize_navigation_url(exact_url)
        if normalized.query_present:
            raise SearchOSNavigationError(
                NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED
            )
        binding_id = (
            "navigation-destination:"
            f"{self.run_id}:{self.request_id}:{normalized.full_digest[:24]}"
        )
        prior = self._by_id.get(binding_id)
        if prior is not None and prior != normalized:
            raise SearchOSNavigationError(
                NAVIGATION_DESTINATION_BINDING_UNAVAILABLE
            )
        if prior is None:
            if len(self._by_id) >= self.capacity:
                raise SearchOSNavigationError(
                    "navigation_destination_registry_capacity_exhausted"
                )
            self._by_id[binding_id] = normalized
        return _destination_binding_ref(binding_id, normalized)

    def resolve(self, binding_ref: Mapping[str, Any]) -> str:
        self._require_open()
        ref = validate_navigation_destination_binding_ref(binding_ref)
        normalized = self._by_id.get(str(ref["destination_binding_id"]))
        if normalized is None or _destination_binding_ref(
            str(ref["destination_binding_id"]), normalized
        ) != ref:
            raise SearchOSNavigationError(
                NAVIGATION_DESTINATION_BINDING_UNAVAILABLE
            )
        return normalized.exact_url

    def normalized_record(
        self, binding_ref: Mapping[str, Any]
    ) -> _NormalizedNavigationURL:
        ref = validate_navigation_destination_binding_ref(binding_ref)
        self.resolve(ref)
        return self._by_id[str(ref["destination_binding_id"])]

    def discard(self) -> None:
        self._by_id.clear()
        self._closed = True

    def __len__(self) -> int:
        return len(self._by_id)

    def __reduce__(self) -> Any:
        raise TypeError("navigation destination registries are nonserializable")

    def _require_open(self) -> None:
        if self._closed:
            raise SearchOSNavigationError(
                NAVIGATION_DESTINATION_BINDING_UNAVAILABLE
            )


def normalize_navigation_url(value: str) -> _NormalizedNavigationURL:
    """Normalize a navigation URL without collapsing trailing slash identity."""

    raw = _token(value, "navigation_url", maximum=NAVIGATION_URL_LENGTH_CEILING)
    if any(ord(character) < 0x20 or character.isspace() for character in raw):
        raise SearchOSNavigationError("navigation_destination_malformed")
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise SearchOSNavigationError(
            "navigation_destination_malformed"
        ) from exc
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"}:
        raise SearchOSNavigationError("navigation_destination_scheme_unsupported")
    if parsed.username is not None or parsed.password is not None:
        raise SearchOSNavigationError("navigation_destination_userinfo_forbidden")
    hostname = str(parsed.hostname or "").casefold().rstrip(".")
    if not hostname or not _is_ascii(hostname):
        raise SearchOSNavigationError("navigation_destination_hostname_invalid")
    if port is not None and port != _default_port(scheme):
        raise SearchOSNavigationError("navigation_destination_port_not_supported")
    explicit_port = _netloc_has_explicit_port(parsed.netloc)
    if explicit_port and port is None:
        raise SearchOSNavigationError("navigation_destination_port_invalid")
    port_posture = (
        f"explicit_default_{_default_port(scheme)}"
        if explicit_port
        else f"implicit_default_{_default_port(scheme)}"
    )
    path = parsed.path or "/"
    netloc = hostname
    if explicit_port:
        netloc = f"{hostname}:{_default_port(scheme)}"
    exact = urlunsplit((scheme, netloc, path, parsed.query, ""))
    if len(exact) > NAVIGATION_URL_LENGTH_CEILING:
        raise SearchOSNavigationError("navigation_destination_too_long")
    full_digest = _digest_text(exact)
    semantic_digest = _digest(
        {
            "scheme": scheme,
            "hostname": hostname,
            "port_posture": port_posture,
            "path": path,
            "query": parsed.query,
        }
    )
    physical_digest = _digest(
        {
            "scheme": scheme,
            "hostname": hostname,
            "port_posture": port_posture,
            "path": path,
            "query": parsed.query,
            "trailing_slash_preserved": True,
        }
    )
    return _NormalizedNavigationURL(
        exact_url=exact,
        scheme=scheme,
        hostname=hostname,
        port=port,
        port_posture=port_posture,
        path=path,
        query=parsed.query,
        full_digest=full_digest,
        semantic_digest=semantic_digest,
        physical_digest=physical_digest,
    )


def navigation_physical_operation_identity(value: str) -> str:
    return f"read-navigation:{normalize_navigation_url(value).physical_digest}"


def validate_navigation_destination_binding_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    raw = _mapping(value, "navigation_destination_binding_ref")
    if set(raw) != _DESTINATION_BINDING_REF_FIELDS:
        raise SearchOSNavigationError(
            NAVIGATION_DESTINATION_BINDING_UNAVAILABLE
        )
    if raw.get("query_present") is not False:
        raise SearchOSNavigationError(
            NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED
        )
    safe = {
        "destination_binding_id": _token(
            raw.get("destination_binding_id"), "destination_binding_id"
        ),
        "destination_binding_digest": _digest_token(
            raw.get("destination_binding_digest"),
            "destination_binding_digest",
        ),
        "full_destination_digest": _digest_token(
            raw.get("full_destination_digest"), "full_destination_digest"
        ),
        "semantic_identity_digest": _digest_token(
            raw.get("semantic_identity_digest"), "semantic_identity_digest"
        ),
        "physical_identity_digest": _digest_token(
            raw.get("physical_identity_digest"), "physical_identity_digest"
        ),
        "normalized_scheme": _token(
            raw.get("normalized_scheme"), "normalized_scheme"
        ),
        "normalized_hostname": _token(
            raw.get("normalized_hostname"), "normalized_hostname"
        ),
        "port_posture": _token(raw.get("port_posture"), "port_posture"),
        "path_digest": _digest_token(raw.get("path_digest"), "path_digest"),
        "query_present": False,
    }
    binding_core = {
        key: safe[key]
        for key in safe
        if key not in {"destination_binding_id", "destination_binding_digest"}
    }
    if safe["destination_binding_digest"] != _digest(binding_core):
        raise SearchOSNavigationError(
            NAVIGATION_DESTINATION_BINDING_UNAVAILABLE
        )
    return safe


def extract_searchos_navigation_draft_v1(
    *,
    run_id: str,
    request_id: str,
    operation_identity_key: str,
    source_obligation_ref: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    answer_contract_ref: Mapping[str, Any],
    artifact_ref: Mapping[str, Any],
    physical_acquisition_ref: Mapping[str, Any],
    retained_text: str,
    retained_digest: str,
    retained_character_count: int,
    attempted_parent_url: str,
    final_url: str | None = None,
    resolved_url: str | None = None,
) -> SearchOSNavigationExtractionDraftV1:
    """Extract a bounded set of supported Markdown occurrences.

    The attempted parent is the immutable origin anchor.  Final/resolved may
    act only as a transient same-origin resolution base, in that precedence.
    """

    if not isinstance(retained_text, str):
        raise SearchOSNavigationError("navigation_retained_text_missing")
    if len(retained_text) > NAVIGATION_RETAINED_TEXT_CEILING:
        raise SearchOSNavigationError("navigation_retained_text_over_limit")
    count = _bounded_nonnegative_int(
        retained_character_count,
        "retained_character_count",
        maximum=NAVIGATION_RETAINED_TEXT_CEILING,
    )
    if count != len(retained_text):
        raise SearchOSNavigationError("navigation_retained_count_mismatch")
    digest = _digest_token(retained_digest, "retained_digest")
    if digest != _digest_text(retained_text):
        raise SearchOSNavigationError("navigation_retained_digest_mismatch")
    attempted = normalize_navigation_url(attempted_parent_url)
    base, base_status = _effective_resolution_base(
        attempted=attempted,
        final_url=final_url,
        resolved_url=resolved_url,
    )
    counters = {
        "supported_occurrences": 0,
        "retained_occurrences": 0,
        "unsupported_occurrences": 0,
        "rejected_query_occurrences": 0,
        "rejected_origin_occurrences": 0,
        "rejected_malformed_occurrences": 0,
        "overflow_occurrences": 0,
    }
    retained: list[SearchOSNavigationExtractedOccurrence] = []
    overflow_tokens: list[dict[str, Any]] = []
    if base is not None:
        for ordinal, label, raw_destination in _iter_supported_markdown_links(
            retained_text
        ):
            counters["supported_occurrences"] += 1
            href_digest = _digest_text(raw_destination)
            try:
                destination_text = urljoin(base.exact_url, raw_destination)
                destination = normalize_navigation_url(destination_text)
                if destination.query_present:
                    counters["rejected_query_occurrences"] += 1
                    continue
                _validate_origin_transition(attempted, destination)
            except SearchOSNavigationError as exc:
                if exc.code == NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED:
                    counters["rejected_query_occurrences"] += 1
                elif exc.code.startswith("navigation_destination_") and exc.code not in {
                    "navigation_destination_origin_out_of_scope",
                    "navigation_destination_scheme_downgrade",
                    "navigation_destination_port_posture_mismatch",
                }:
                    counters["rejected_malformed_occurrences"] += 1
                else:
                    counters["rejected_origin_occurrences"] += 1
                continue
            if len(retained) >= NAVIGATION_EXTRACTED_OCCURRENCE_CEILING:
                counters["overflow_occurrences"] += 1
                overflow_tokens.append(
                    {
                        "source_ordinal": ordinal,
                        "full_destination_digest": destination.full_digest,
                        "label_digest": _digest_text(label),
                        "href_digest": href_digest,
                    }
                )
                continue
            relationship_label = _bounded_relationship_label(label)
            retained.append(
                SearchOSNavigationExtractedOccurrence(
                    resolved_destination=destination.exact_url,
                    normalized_destination=destination,
                    source_ordinal=ordinal,
                    relationship_label=relationship_label,
                    label_digest=_digest_text(label),
                    href_digest=href_digest,
                )
            )
            counters["retained_occurrences"] += 1
    else:
        counters["unsupported_occurrences"] = _count_markdown_like_links(
            retained_text
        )
    return SearchOSNavigationExtractionDraftV1(
        run_id=run_id,
        request_id=request_id,
        operation_identity_key=operation_identity_key,
        source_obligation_ref=source_obligation_ref,
        component_ref=component_ref,
        answer_contract_ref=answer_contract_ref,
        artifact_ref=artifact_ref,
        physical_acquisition_ref=physical_acquisition_ref,
        retained_digest=digest,
        retained_character_count=count,
        attempted_parent_url=attempted.exact_url,
        attempted_parent_full_digest=attempted.full_digest,
        attempted_parent_physical_digest=attempted.physical_digest,
        effective_base_url=base.exact_url if base is not None else None,
        effective_base_status=base_status,
        occurrences=retained,
        extraction_counters=counters,
        overflow_digest=_digest(overflow_tokens),
    )


def discard_navigation_extraction_draft(
    draft: SearchOSNavigationExtractionDraftV1 | None,
) -> None:
    if draft is not None:
        draft.destroy()


def build_searchos_navigation_candidate_set_v1(
    *,
    draft: SearchOSNavigationExtractionDraftV1,
    destination_registry: SearchOSNavigationDestinationRegistry,
    fetch_read_packet: Mapping[str, Any],
    evidence_ledger_custody: Mapping[str, Any],
    parent_custody_ref: Mapping[str, Any],
    slot_ref: Mapping[str, Any],
    parent_depth: int = 0,
    parent_custody_admission_ordinal: int = 1,
) -> dict[str, Any]:
    """Join one live extraction draft to exact parent physical/use custody.

    The returned value is an admission proposal.  It is not canonical state
    until ``admit_searchos_navigation_candidate_set`` commits a deterministic
    prefix under the retained-capacity rules.
    """

    if not isinstance(draft, SearchOSNavigationExtractionDraftV1):
        raise SearchOSNavigationError("navigation_extraction_draft_required")
    draft.require_live()
    if not isinstance(destination_registry, SearchOSNavigationDestinationRegistry):
        raise SearchOSNavigationError("navigation_destination_registry_required")
    if (
        destination_registry.run_id != draft.run_id
        or destination_registry.request_id != draft.request_id
    ):
        raise SearchOSNavigationError("navigation_destination_registry_scope_mismatch")
    packet = _mapping(fetch_read_packet, "fetch_read_packet")
    ledger = _mapping(evidence_ledger_custody, "evidence_ledger_custody")
    parent = _required_ref(parent_custody_ref, "parent_custody_ref")
    slot = _required_ref(slot_ref, "slot_ref")
    _validate_navigation_parent_custody_join(
        draft=draft,
        fetch_read_packet=packet,
        evidence_ledger_custody=ledger,
        parent_custody_ref=parent,
        slot_ref=slot,
    )
    depth = _bounded_nonnegative_int(
        parent_depth, "navigation_parent_depth", maximum=NAVIGATION_MAX_DEPTH
    )
    child_depth = depth + 1
    if child_depth > NAVIGATION_MAX_DEPTH:
        raise SearchOSNavigationError("navigation_depth_violation")
    parent_ordinal = _bounded_positive_int(
        parent_custody_admission_ordinal,
        "parent_custody_admission_ordinal",
    )
    parent_physical_digest = _digest_token(
        parent.get("physical_identity_digest"), "parent_physical_identity_digest"
    )
    ancestor_digests = {
        _digest_token(item, "ancestor_physical_identity_digest")
        for item in _sequence(parent.get("ancestor_physical_identity_digests", ()))
    }
    slot_id = _slot_id(slot)
    contributor_records: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for occurrence in draft.occurrences:
        destination = occurrence.normalized_destination
        failure_code: str | None = None
        if destination.physical_digest == parent_physical_digest:
            failure_code = "navigation_self_link"
        elif destination.physical_digest in ancestor_digests:
            failure_code = "navigation_ancestor_cycle"
        if failure_code is not None:
            excluded.append(
                {
                    "source_ordinal": occurrence.source_ordinal,
                    "full_destination_digest": destination.full_digest,
                    "failure_code": failure_code,
                }
            )
            continue
        binding_ref = destination_registry.register(
            occurrence.resolved_destination
        )
        option_identity = build_searchos_navigation_option_identity_v1(
            slot_id=slot_id,
            destination_binding_ref=binding_ref,
        )
        contributor_core = {
            "slot_ref": slot,
            "stable_option_ref": searchos_navigation_option_identity_ref(
                option_identity
            ),
            "destination_binding_ref": binding_ref,
            "parent_custody_ref": parent,
            "parent_depth": depth,
            "child_depth": child_depth,
            "parent_custody_admission_ordinal": parent_ordinal,
            "source_link_ordinal": occurrence.source_ordinal,
            "relationship_label": occurrence.relationship_label,
            "label_digest": occurrence.label_digest,
            "href_digest": occurrence.href_digest,
        }
        contributor_digest = _digest(contributor_core)
        contributor_records.append(
            {
                "navigation_contributor_id": (
                    f"navigation-contributor:{slot_id}:{contributor_digest[:24]}"
                ),
                "navigation_contributor_digest": contributor_digest,
                **contributor_core,
            }
        )
    contributor_records.sort(key=_contributor_order_key)
    overflow_core = {
        "draft_overflow_digest": draft.overflow_digest,
        "excluded": excluded,
    }
    core = {
        "schema_version": SEARCHOS_NAVIGATION_CANDIDATE_SET_SCHEMA_VERSION,
        "owner": SEARCHOS_NAVIGATION_OWNER,
        "run_id": draft.run_id,
        "request_id": draft.request_id,
        "slot_ref": slot,
        "parent_custody_ref": parent,
        "physical_acquisition_ref": deepcopy(draft.physical_acquisition_ref),
        "fetch_read_content_packet_ref": _fetch_packet_ref(packet),
        "evidence_ledger_custody_ref": _ledger_custody_ref(ledger),
        "source_obligation_ref": deepcopy(draft.source_obligation_ref),
        "component_ref": deepcopy(draft.component_ref),
        "answer_contract_ref": deepcopy(draft.answer_contract_ref),
        "candidate_contributors": contributor_records,
        "candidate_contributor_total": len(contributor_records),
        "excluded_contributor_total": len(excluded),
        "excluded_contributor_summary_digest": _digest(excluded),
        "draft_extraction_counters": dict(draft.extraction_counters),
        "draft_overflow_digest": draft.overflow_digest,
        "combined_overflow_digest": _digest(overflow_core),
        "admission_posture": "pending_runkernel_admission",
    }
    candidate_set_digest = _digest(core)
    return {
        **core,
        "navigation_candidate_set_id": (
            f"navigation-candidate-set:{slot_id}:{candidate_set_digest[:24]}"
        ),
        "navigation_candidate_set_digest": candidate_set_digest,
    }


def searchos_navigation_candidate_set_ref(
    candidate_set: Mapping[str, Any],
) -> dict[str, str]:
    value = _mapping(candidate_set, "navigation_candidate_set")
    return {
        "navigation_candidate_set_id": _token(
            value.get("navigation_candidate_set_id"),
            "navigation_candidate_set_id",
        ),
        "navigation_candidate_set_digest": _digest_token(
            value.get("navigation_candidate_set_digest"),
            "navigation_candidate_set_digest",
        ),
    }


def build_searchos_navigation_option_identity_v1(
    *,
    slot_id: str,
    destination_binding_ref: Mapping[str, Any],
) -> dict[str, Any]:
    slot = _token(slot_id, "slot_id")
    binding = validate_navigation_destination_binding_ref(
        destination_binding_ref
    )
    core = {
        "schema_version": SEARCHOS_NAVIGATION_OPTION_IDENTITY_SCHEMA_VERSION,
        "owner": SEARCHOS_NAVIGATION_OWNER,
        "slot_id": slot,
        "full_destination_digest": binding["full_destination_digest"],
        "destination_binding_ref": binding,
    }
    digest = _digest(core)
    return {
        **core,
        "navigation_option_id": f"navigation-option:{slot}:{digest[:24]}",
        "navigation_option_digest": digest,
    }


def searchos_navigation_option_identity_ref(
    option_identity: Mapping[str, Any],
) -> dict[str, str]:
    value = validate_searchos_navigation_option_identity_v1(option_identity)
    return {
        "navigation_option_id": value["navigation_option_id"],
        "navigation_option_digest": value["navigation_option_digest"],
    }


def validate_searchos_navigation_option_identity_v1(
    option_identity: Mapping[str, Any],
) -> dict[str, Any]:
    value = _mapping(option_identity, "navigation_option_identity")
    required = {
        "schema_version",
        "owner",
        "slot_id",
        "full_destination_digest",
        "destination_binding_ref",
        "navigation_option_id",
        "navigation_option_digest",
    }
    if set(value) != required:
        raise SearchOSNavigationError("navigation_option_identity_fields_invalid")
    if value.get("schema_version") != SEARCHOS_NAVIGATION_OPTION_IDENTITY_SCHEMA_VERSION:
        raise SearchOSNavigationError("navigation_option_identity_schema_invalid")
    if value.get("owner") != SEARCHOS_NAVIGATION_OWNER:
        raise SearchOSNavigationError("navigation_option_identity_owner_invalid")
    binding = validate_navigation_destination_binding_ref(
        value.get("destination_binding_ref")
    )
    if value.get("full_destination_digest") != binding["full_destination_digest"]:
        raise SearchOSNavigationError("navigation_option_destination_mismatch")
    expected = build_searchos_navigation_option_identity_v1(
        slot_id=_token(value.get("slot_id"), "slot_id"),
        destination_binding_ref=binding,
    )
    if expected != value:
        raise SearchOSNavigationError("navigation_option_identity_mismatch")
    return deepcopy(value)


def build_searchos_navigation_lineage_snapshot_v1(
    *,
    stable_option_identity: Mapping[str, Any],
    contributors: Sequence[Mapping[str, Any]],
    generation_ordinal: int,
    overflow_count: int = 0,
    overflow_digest: str | None = None,
) -> dict[str, Any]:
    option = validate_searchos_navigation_option_identity_v1(
        stable_option_identity
    )
    explicit = [_validate_contributor(item) for item in contributors]
    explicit.sort(key=_contributor_order_key)
    if len(explicit) > NAVIGATION_CONTRIBUTORS_PER_OPTION_CEILING:
        raise SearchOSNavigationError("navigation_option_contributor_limit_exceeded")
    option_ref = searchos_navigation_option_identity_ref(option)
    if any(item["stable_option_ref"] != option_ref for item in explicit):
        raise SearchOSNavigationError("navigation_contributor_option_mismatch")
    ordinal = _bounded_positive_int(generation_ordinal, "generation_ordinal")
    overflow = _bounded_nonnegative_int(
        overflow_count, "overflow_count", maximum=1_000_000
    )
    rolling = overflow_digest or _digest([])
    rolling = _digest_token(rolling, "overflow_digest")
    core = {
        "schema_version": SEARCHOS_NAVIGATION_LINEAGE_SNAPSHOT_SCHEMA_VERSION,
        "owner": SEARCHOS_NAVIGATION_OWNER,
        "stable_option_ref": option_ref,
        "generation_ordinal": ordinal,
        "contributor_refs": [navigation_contributor_ref(item) for item in explicit],
        "contributor_total": len(explicit) + overflow,
        "explicit_contributor_total": len(explicit),
        "overflow_count": overflow,
        "rolling_overflow_digest": rolling,
    }
    digest = _digest(core)
    return {
        **core,
        "navigation_lineage_id": (
            f"navigation-lineage:{option_ref['navigation_option_id']}:{ordinal}:{digest[:20]}"
        ),
        "navigation_lineage_digest": digest,
    }


def searchos_navigation_lineage_snapshot_ref(
    lineage: Mapping[str, Any],
) -> dict[str, str]:
    value = _mapping(lineage, "navigation_lineage_snapshot")
    return {
        "navigation_lineage_id": _token(
            value.get("navigation_lineage_id"), "navigation_lineage_id"
        ),
        "navigation_lineage_digest": _digest_token(
            value.get("navigation_lineage_digest"),
            "navigation_lineage_digest",
        ),
    }


def build_searchos_navigation_option_state_v1(
    *,
    stable_option_identity: Mapping[str, Any],
    lineage_snapshot: Mapping[str, Any],
    feasible_contributors: Sequence[Mapping[str, Any]],
    disposition: str = "selectable",
    disposition_reason: str = "navigation_option_available",
    active_lease_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    option = validate_searchos_navigation_option_identity_v1(
        stable_option_identity
    )
    contributors = [_validate_contributor(item) for item in feasible_contributors]
    contributors.sort(key=_contributor_order_key)
    if not contributors and disposition == "selectable":
        raise SearchOSNavigationError("navigation_selectable_option_has_no_contributor")
    option_ref = searchos_navigation_option_identity_ref(option)
    if any(item["stable_option_ref"] != option_ref for item in contributors):
        raise SearchOSNavigationError("navigation_contributor_option_mismatch")
    lineage_ref = searchos_navigation_lineage_snapshot_ref(lineage_snapshot)
    representative = navigation_contributor_ref(contributors[0]) if contributors else {}
    core = {
        "schema_version": SEARCHOS_NAVIGATION_OPTION_STATE_SCHEMA_VERSION,
        "owner": SEARCHOS_NAVIGATION_OWNER,
        "stable_option_ref": option_ref,
        "latest_selectable_lineage_ref": lineage_ref,
        "feasible_contributor_refs": [
            navigation_contributor_ref(item) for item in contributors
        ],
        "representative_contributor_ref": representative,
        "disposition": _token(disposition, "navigation_option_disposition"),
        "disposition_reason": _token(
            disposition_reason,
            "navigation_option_disposition_reason",
            maximum=240,
        ),
        "active_lease_ref": (
            _required_ref(active_lease_ref, "active_lease_ref")
            if active_lease_ref
            else {}
        ),
    }
    digest = _digest(core)
    return {
        **core,
        "navigation_option_state_id": (
            f"navigation-option-state:{option_ref['navigation_option_id']}:{digest[:24]}"
        ),
        "navigation_option_state_digest": digest,
    }


def build_searchos_navigation_candidate_ref_v1(
    *,
    option_identity: Mapping[str, Any],
    lineage_snapshot: Mapping[str, Any],
    representative_contributor: Mapping[str, Any],
) -> dict[str, Any]:
    option = validate_searchos_navigation_option_identity_v1(option_identity)
    contributor = _validate_contributor(representative_contributor)
    option_ref = searchos_navigation_option_identity_ref(option)
    if contributor["stable_option_ref"] != option_ref:
        raise SearchOSNavigationError("navigation_candidate_contributor_mismatch")
    lineage_ref = searchos_navigation_lineage_snapshot_ref(lineage_snapshot)
    binding_ref = validate_navigation_destination_binding_ref(
        option["destination_binding_ref"]
    )
    core = {
        "schema_version": SEARCHOS_NAVIGATION_CANDIDATE_REF_SCHEMA_VERSION,
        "stable_option_ref": option_ref,
        "navigation_lineage_snapshot_ref": lineage_ref,
        "representative_contributor_ref": navigation_contributor_ref(contributor),
        "destination_binding_ref": binding_ref,
    }
    digest = _digest(core)
    return {
        **core,
        "navigation_candidate_id": (
            f"navigation-candidate:{option_ref['navigation_option_id']}:{digest[:24]}"
        ),
        "navigation_candidate_digest": digest,
    }


def navigation_contributor_ref(contributor: Mapping[str, Any]) -> dict[str, str]:
    value = _validate_contributor(contributor)
    return {
        "navigation_contributor_id": value["navigation_contributor_id"],
        "navigation_contributor_digest": value["navigation_contributor_digest"],
    }


def build_searchos_navigation_retained_state(
    *,
    run_id: str,
    request_id: str,
    required_slot_ids: Sequence[str],
    ceilings: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    required = [_token(item, "required_slot_id") for item in required_slot_ids]
    if len(set(required)) != len(required):
        raise SearchOSNavigationError("navigation_required_slot_duplicate")
    configured = {
        "stable_options": NAVIGATION_STABLE_OPTION_CEILING,
        "contributors": NAVIGATION_CONTRIBUTOR_CEILING,
        "lineages": NAVIGATION_LINEAGE_GENERATION_CEILING,
        "candidate_sets": NAVIGATION_CANDIDATE_SET_CEILING,
        "deep_edges": NAVIGATION_DEEP_EDGE_CEILING,
    }
    if ceilings:
        unknown = set(ceilings).difference(configured)
        if unknown:
            raise SearchOSNavigationError("navigation_capacity_category_unknown")
        for key, value in ceilings.items():
            configured[key] = _bounded_positive_int(value, f"{key}_ceiling")
    core = {
        "schema_version": SEARCHOS_NAVIGATION_RETAINED_STATE_SCHEMA_VERSION,
        "owner": SEARCHOS_NAVIGATION_OWNER,
        "run_id": _token(run_id, "run_id"),
        "request_id": _token(request_id, "request_id"),
        "ceilings": configured,
        "required_slot_ids": required,
        "slot_reservation_status": {slot_id: "reserved" for slot_id in required},
        "retained_counts": {key: 0 for key in configured},
        "options_by_id": {},
        "contributors_by_id": {},
        "lineages_by_id": {},
        "option_states_by_id": {},
        "candidate_sets_by_id": {},
        "edges_by_id": {},
        "selection_leases_by_id": {},
        "terminal_physical_operations_by_key": {},
        "physical_custody_by_digest": {},
        "logical_edge_charges": 0,
        "logical_read_nomination_charges": 0,
        "next_admission_ordinal": 1,
        "overflow_totals": {
            "stable_options": 0,
            "contributors": 0,
            "lineages": 0,
            "candidate_sets": 0,
        },
        "rolling_overflow_digest": _digest([]),
    }
    return core


def admit_searchos_navigation_candidate_set(
    state: Mapping[str, Any],
    *,
    candidate_set: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically retain the largest deterministic contributor prefix."""

    current = _validated_retained_state(state)
    proposal = _validate_candidate_set_proposal(candidate_set)
    if proposal["run_id"] != current["run_id"] or proposal["request_id"] != current["request_id"]:
        raise SearchOSNavigationError("navigation_candidate_set_scope_mismatch")
    slot_id = _slot_id(proposal["slot_ref"])
    if not _capacity_available(current, "candidate_sets", slot_id, 1):
        raise SearchOSNavigationError(
            NAVIGATION_CANDIDATE_SET_CAPACITY_EXHAUSTED
        )
    next_state = deepcopy(current)
    contributors = [
        _validate_contributor(item)
        for item in proposal["candidate_contributors"]
    ]
    contributors.sort(key=_contributor_order_key)
    accepted: list[dict[str, Any]] = []
    changed_options: set[str] = set()
    planned_options: set[str] = set()
    planned_contributors: set[str] = set()
    planned_lineages: set[str] = set()
    for contributor in contributors:
        option_id = contributor["stable_option_ref"]["navigation_option_id"]
        contributor_id = contributor["navigation_contributor_id"]
        existing_state = next_state["option_states_by_id"].get(option_id, {})
        existing_refs = list(existing_state.get("feasible_contributor_refs", ()))
        if contributor_id in {
            item.get("navigation_contributor_id") for item in existing_refs
        }:
            continue
        if len(existing_refs) + sum(
            1
            for item in accepted
            if item["stable_option_ref"]["navigation_option_id"] == option_id
        ) >= NAVIGATION_CONTRIBUTORS_PER_OPTION_CEILING:
            break
        option_cost = (
            0
            if option_id in next_state["options_by_id"] or option_id in planned_options
            else 1
        )
        contributor_cost = 0 if contributor_id in planned_contributors else 1
        lineage_cost = 0 if option_id in planned_lineages else 1
        if option_cost and not _capacity_available(
            next_state,
            "stable_options",
            slot_id,
            len(planned_options) + option_cost,
        ):
            break
        if contributor_cost and not _capacity_available(
            next_state,
            "contributors",
            slot_id,
            len(planned_contributors) + contributor_cost,
        ):
            break
        if lineage_cost and not _capacity_available(
            next_state,
            "lineages",
            slot_id,
            len(planned_lineages) + lineage_cost,
        ):
            break
        accepted.append(contributor)
        if option_cost:
            planned_options.add(option_id)
        planned_contributors.add(contributor_id)
        planned_lineages.add(option_id)
        changed_options.add(option_id)
    excluded_count = len(contributors) - len(accepted)
    option_candidates: list[dict[str, Any]] = []
    for contributor in accepted:
        option_id = contributor["stable_option_ref"]["navigation_option_id"]
        next_state["contributors_by_id"][contributor["navigation_contributor_id"]] = contributor
        if option_id not in next_state["options_by_id"]:
            identity = build_searchos_navigation_option_identity_v1(
                slot_id=slot_id,
                destination_binding_ref=contributor["destination_binding_ref"],
            )
            next_state["options_by_id"][option_id] = identity
    for option_id in sorted(changed_options):
        identity = next_state["options_by_id"][option_id]
        prior_state = next_state["option_states_by_id"].get(option_id, {})
        contributor_refs = list(prior_state.get("feasible_contributor_refs", ()))
        all_contributors = [
            next_state["contributors_by_id"][ref["navigation_contributor_id"]]
            for ref in contributor_refs
        ]
        all_contributors.extend(
            item
            for item in accepted
            if item["stable_option_ref"]["navigation_option_id"] == option_id
        )
        unique = {
            item["navigation_contributor_id"]: item for item in all_contributors
        }
        feasible = sorted(unique.values(), key=_contributor_order_key)
        generation = 1 + sum(
            1
            for lineage in next_state["lineages_by_id"].values()
            if lineage.get("stable_option_ref", {}).get("navigation_option_id") == option_id
        )
        lineage = build_searchos_navigation_lineage_snapshot_v1(
            stable_option_identity=identity,
            contributors=feasible,
            generation_ordinal=generation,
        )
        next_state["lineages_by_id"][lineage["navigation_lineage_id"]] = lineage
        terminal = prior_state.get("disposition") in {
            "custodied",
            "destination_failed",
            "binding_unavailable",
            "durable_source_identity_invalid",
        }
        option_state = build_searchos_navigation_option_state_v1(
            stable_option_identity=identity,
            lineage_snapshot=lineage,
            feasible_contributors=feasible,
            disposition=(prior_state["disposition"] if terminal else "selectable"),
            disposition_reason=(
                prior_state["disposition_reason"]
                if terminal
                else "navigation_option_available"
            ),
            active_lease_ref=prior_state.get("active_lease_ref") or None,
        )
        next_state["option_states_by_id"][option_id] = option_state
        if feasible:
            option_candidates.append(
                build_searchos_navigation_candidate_ref_v1(
                    option_identity=identity,
                    lineage_snapshot=lineage,
                    representative_contributor=feasible[0],
                )
            )
    admitted_core = {
        key: deepcopy(value)
        for key, value in proposal.items()
        if key
        not in {
            "navigation_candidate_set_id",
            "navigation_candidate_set_digest",
            "candidate_contributors",
            "candidate_contributor_total",
            "admission_posture",
        }
    }
    admitted_core.update(
        {
            "candidate_contributor_refs": [
                navigation_contributor_ref(item) for item in accepted
            ],
            "candidate_contributor_total": len(accepted),
            "navigation_candidate_refs": sorted(
                option_candidates,
                key=lambda item: item["navigation_candidate_id"],
            ),
            "admission_excluded_count": excluded_count,
            "admission_overflow_digest": _digest(
                [navigation_contributor_ref(item) for item in contributors[len(accepted) :]]
            ),
            "admission_posture": "runkernel_admitted",
            "admission_ordinal": next_state["next_admission_ordinal"],
        }
    )
    admitted_digest = _digest(admitted_core)
    admitted = {
        **admitted_core,
        "navigation_candidate_set_id": (
            f"navigation-candidate-set:{slot_id}:{admitted_digest[:24]}"
        ),
        "navigation_candidate_set_digest": admitted_digest,
    }
    set_id = admitted["navigation_candidate_set_id"]
    next_state["candidate_sets_by_id"][set_id] = admitted
    next_state["next_admission_ordinal"] += 1
    next_state["retained_counts"] = {
        "stable_options": len(next_state["options_by_id"]),
        "contributors": len(next_state["contributors_by_id"]),
        "lineages": len(next_state["lineages_by_id"]),
        "candidate_sets": len(next_state["candidate_sets_by_id"]),
        "deep_edges": len(next_state["edges_by_id"]),
    }
    if excluded_count:
        next_state["overflow_totals"]["contributors"] += excluded_count
        next_state["rolling_overflow_digest"] = _digest(
            {
                "prior": next_state["rolling_overflow_digest"],
                "candidate_set_ref": searchos_navigation_candidate_set_ref(admitted),
                "excluded_count": excluded_count,
                "excluded_digest": admitted["admission_overflow_digest"],
            }
        )
    if any(item["child_depth"] >= 2 for item in accepted):
        if slot_id in next_state["slot_reservation_status"]:
            next_state["slot_reservation_status"][slot_id] = (
                "lawful_depth_two_represented"
            )
    return _validated_retained_state(next_state)


def build_searchos_navigation_candidate_window_v1(
    state: Mapping[str, Any],
    *,
    slot_id: str,
) -> dict[str, Any]:
    current = _validated_retained_state(state)
    slot = _token(slot_id, "slot_id")
    candidates: list[dict[str, Any]] = []
    for option_id, option_state in current["option_states_by_id"].items():
        option = current["options_by_id"][option_id]
        if option["slot_id"] != slot or option_state["disposition"] != "selectable":
            continue
        if option_state["active_lease_ref"]:
            continue
        lineage = current["lineages_by_id"].get(
            option_state["latest_selectable_lineage_ref"]["navigation_lineage_id"]
        )
        contributor = current["contributors_by_id"].get(
            option_state["representative_contributor_ref"]["navigation_contributor_id"]
        )
        if lineage is None or contributor is None:
            raise SearchOSNavigationError("navigation_option_state_lineage_missing")
        candidates.append(
            build_searchos_navigation_candidate_ref_v1(
                option_identity=option,
                lineage_snapshot=lineage,
                representative_contributor=contributor,
            )
        )
    candidates.sort(key=lambda item: item["navigation_candidate_id"])
    visible = candidates[:NAVIGATION_MODEL_WINDOW_CEILING]
    core = {
        "schema_version": "searchos_navigation_candidate_window_v1",
        "slot_id": slot,
        "navigation_candidate_refs": visible,
        "visible_count": len(visible),
        "hidden_count": len(candidates) - len(visible),
        "hidden_digest": _digest(candidates[len(visible) :]),
    }
    digest = _digest(core)
    return {
        **core,
        "navigation_candidate_window_id": (
            f"navigation-window:{slot}:{digest[:24]}"
        ),
        "navigation_candidate_window_digest": digest,
    }


def admit_searchos_navigation_selection(
    state: Mapping[str, Any],
    *,
    navigation_candidate_ref: Mapping[str, Any],
    destination_registry: SearchOSNavigationDestinationRegistry,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Admit one exact current candidate, immutable lease, and logical edge."""

    current = _validated_retained_state(state)
    candidate = _validate_navigation_candidate_ref(navigation_candidate_ref)
    option_id = candidate["stable_option_ref"]["navigation_option_id"]
    option = current["options_by_id"].get(option_id)
    option_state = current["option_states_by_id"].get(option_id)
    if option is None or option_state is None:
        raise SearchOSNavigationError("navigation_candidate_hidden_or_stale")
    if option_state["disposition"] != "selectable":
        raise SearchOSNavigationError("navigation_candidate_completed")
    if option_state["active_lease_ref"]:
        raise SearchOSNavigationError("navigation_candidate_active_lease_conflict")
    lineage_ref = candidate["navigation_lineage_snapshot_ref"]
    contributor_ref = candidate["representative_contributor_ref"]
    if option_state["latest_selectable_lineage_ref"] != lineage_ref:
        raise SearchOSNavigationError("navigation_candidate_stale_lineage")
    if option_state["representative_contributor_ref"] != contributor_ref:
        raise SearchOSNavigationError(
            "navigation_candidate_stale_representative_contributor"
        )
    lineage = current["lineages_by_id"].get(lineage_ref["navigation_lineage_id"])
    contributor = current["contributors_by_id"].get(
        contributor_ref["navigation_contributor_id"]
    )
    if lineage is None or contributor is None:
        raise SearchOSNavigationError("navigation_candidate_hidden_or_stale")
    expected = build_searchos_navigation_candidate_ref_v1(
        option_identity=option,
        lineage_snapshot=lineage,
        representative_contributor=contributor,
    )
    if expected != candidate:
        raise SearchOSNavigationError("navigation_candidate_hidden_or_stale")
    destination_registry.resolve(candidate["destination_binding_ref"])
    if not _capacity_available(current, "deep_edges", option["slot_id"], 1):
        raise SearchOSNavigationError("navigation_deep_edge_capacity_exhausted")
    selection_core = {
        "schema_version": SEARCHOS_NAVIGATION_SELECTION_SCHEMA_VERSION,
        "stable_option_ref": candidate["stable_option_ref"],
        "navigation_lineage_snapshot_ref": lineage_ref,
        "representative_contributor_ref": contributor_ref,
        "destination_binding_ref": candidate["destination_binding_ref"],
        "physical_identity_digest": candidate["destination_binding_ref"][
            "physical_identity_digest"
        ],
        "full_destination_digest": candidate["destination_binding_ref"][
            "full_destination_digest"
        ],
        "lease_posture": "active_immutable_selection",
    }
    selection_digest = _digest(selection_core)
    selection = {
        **selection_core,
        "navigation_selection_id": f"navigation-selection:{selection_digest[:24]}",
        "navigation_selection_digest": selection_digest,
    }
    edge_core = {
        "schema_version": SEARCHOS_NAVIGATION_EDGE_SCHEMA_VERSION,
        "navigation_selection_ref": navigation_selection_ref(selection),
        "stable_option_ref": candidate["stable_option_ref"],
        "navigation_lineage_snapshot_ref": lineage_ref,
        "representative_contributor_ref": contributor_ref,
        "parent_custody_ref": contributor["parent_custody_ref"],
        "destination_binding_ref": candidate["destination_binding_ref"],
        "child_depth": contributor["child_depth"],
        "edge_posture": "admitted_pending_read",
    }
    edge_digest = _digest(edge_core)
    edge = {
        **edge_core,
        "navigation_edge_id": f"navigation-edge:{edge_digest[:24]}",
        "navigation_edge_digest": edge_digest,
    }
    next_state = deepcopy(current)
    next_state["selection_leases_by_id"][selection["navigation_selection_id"]] = selection
    next_state["edges_by_id"][edge["navigation_edge_id"]] = edge
    updated_state = deepcopy(option_state)
    updated_state["active_lease_ref"] = navigation_selection_ref(selection)
    updated_state["navigation_option_state_digest"] = _digest(
        {
            key: value
            for key, value in updated_state.items()
            if key
            not in {
                "navigation_option_state_id",
                "navigation_option_state_digest",
            }
        }
    )
    updated_state["navigation_option_state_id"] = (
        f"navigation-option-state:{option_id}:"
        f"{updated_state['navigation_option_state_digest'][:24]}"
    )
    next_state["option_states_by_id"][option_id] = updated_state
    next_state["logical_edge_charges"] += 1
    next_state["logical_read_nomination_charges"] += 1
    next_state["retained_counts"]["deep_edges"] = len(next_state["edges_by_id"])
    return _validated_retained_state(next_state), selection, edge


def navigation_selection_ref(selection: Mapping[str, Any]) -> dict[str, str]:
    value = _mapping(selection, "navigation_selection")
    return {
        "navigation_selection_id": _token(
            value.get("navigation_selection_id"), "navigation_selection_id"
        ),
        "navigation_selection_digest": _digest_token(
            value.get("navigation_selection_digest"),
            "navigation_selection_digest",
        ),
    }


def navigation_edge_ref(edge: Mapping[str, Any]) -> dict[str, str]:
    value = _mapping(edge, "navigation_edge")
    return {
        "navigation_edge_id": _token(
            value.get("navigation_edge_id"), "navigation_edge_id"
        ),
        "navigation_edge_digest": _digest_token(
            value.get("navigation_edge_digest"), "navigation_edge_digest"
        ),
    }


def mark_searchos_navigation_slot_structurally_terminal(
    state: Mapping[str, Any], *, slot_id: str
) -> dict[str, Any]:
    current = _validated_retained_state(state)
    slot = _token(slot_id, "slot_id")
    if slot not in current["slot_reservation_status"]:
        raise SearchOSNavigationError("navigation_slot_not_required")
    next_state = deepcopy(current)
    next_state["slot_reservation_status"][slot] = "terminal_or_depth_two_unreachable"
    return next_state


def record_searchos_navigation_contributor_failure(
    state: Mapping[str, Any],
    *,
    contributor_ref: Mapping[str, Any],
    failure_code: str,
) -> dict[str, Any]:
    current = _validated_retained_state(state)
    ref = {
        "navigation_contributor_id": _token(
            contributor_ref.get("navigation_contributor_id"),
            "navigation_contributor_id",
        ),
        "navigation_contributor_digest": _digest_token(
            contributor_ref.get("navigation_contributor_digest"),
            "navigation_contributor_digest",
        ),
    }
    contributor = current["contributors_by_id"].get(ref["navigation_contributor_id"])
    if contributor is None or navigation_contributor_ref(contributor) != ref:
        raise SearchOSNavigationError("navigation_contributor_not_current")
    option_id = contributor["stable_option_ref"]["navigation_option_id"]
    option_state = current["option_states_by_id"][option_id]
    if option_state["active_lease_ref"]:
        raise SearchOSNavigationError("navigation_leased_contributor_immutable")
    next_state = deepcopy(current)
    feasible_refs = [
        item
        for item in option_state["feasible_contributor_refs"]
        if item != ref
    ]
    feasible = [
        next_state["contributors_by_id"][item["navigation_contributor_id"]]
        for item in feasible_refs
    ]
    option = next_state["options_by_id"][option_id]
    generation = 1 + sum(
        1
        for lineage in next_state["lineages_by_id"].values()
        if lineage.get("stable_option_ref", {}).get("navigation_option_id") == option_id
    )
    if next_state["retained_counts"]["lineages"] >= next_state["ceilings"]["lineages"]:
        raise SearchOSNavigationError("navigation_lineage_capacity_exhausted")
    lineage = build_searchos_navigation_lineage_snapshot_v1(
        stable_option_identity=option,
        contributors=feasible,
        generation_ordinal=generation,
    )
    next_state["lineages_by_id"][lineage["navigation_lineage_id"]] = lineage
    next_state["option_states_by_id"][option_id] = build_searchos_navigation_option_state_v1(
        stable_option_identity=option,
        lineage_snapshot=lineage,
        feasible_contributors=feasible,
        disposition="selectable" if feasible else "contributors_exhausted",
        disposition_reason=failure_code,
    )
    next_state["retained_counts"]["lineages"] = len(next_state["lineages_by_id"])
    return _validated_retained_state(next_state)


def record_searchos_navigation_destination_terminal(
    state: Mapping[str, Any],
    *,
    stable_option_ref: Mapping[str, Any],
    operation_identity_key: str,
    disposition: str,
    failure_code: str | None = None,
) -> dict[str, Any]:
    current = _validated_retained_state(state)
    option_id = _token(
        stable_option_ref.get("navigation_option_id"), "navigation_option_id"
    )
    option = current["options_by_id"].get(option_id)
    option_state = current["option_states_by_id"].get(option_id)
    if option is None or option_state is None:
        raise SearchOSNavigationError("navigation_option_not_current")
    if searchos_navigation_option_identity_ref(option) != dict(stable_option_ref):
        raise SearchOSNavigationError("navigation_option_not_current")
    terminal_disposition = _token(disposition, "navigation_terminal_disposition")
    if terminal_disposition not in {
        "custodied",
        "destination_failed",
        "binding_unavailable",
        "durable_source_identity_invalid",
    }:
        raise SearchOSNavigationError("navigation_terminal_disposition_invalid")
    operation_key = _token(operation_identity_key, "operation_identity_key")
    next_state = deepcopy(current)
    next_state["terminal_physical_operations_by_key"][operation_key] = {
        "stable_option_ref": dict(stable_option_ref),
        "terminal_disposition": terminal_disposition,
        "failure_code": failure_code,
        "retry_licensed": False,
    }
    updated = deepcopy(option_state)
    updated["disposition"] = terminal_disposition
    updated["disposition_reason"] = failure_code or terminal_disposition
    updated["active_lease_ref"] = {}
    updated_core = {
        key: value
        for key, value in updated.items()
        if key
        not in {
            "navigation_option_state_id",
            "navigation_option_state_digest",
        }
    }
    updated["navigation_option_state_digest"] = _digest(updated_core)
    updated["navigation_option_state_id"] = (
        f"navigation-option-state:{option_id}:"
        f"{updated['navigation_option_state_digest'][:24]}"
    )
    next_state["option_states_by_id"][option_id] = updated
    return _validated_retained_state(next_state)


def build_searchos_navigation_use_custody_ref_v2(
    *,
    slot_ref: Mapping[str, Any],
    selection_ref: Mapping[str, Any],
    edge_ref: Mapping[str, Any],
    physical_custody_ref: Mapping[str, Any],
    fetch_read_content_packet_ref: Mapping[str, Any],
    evidence_ledger_custody_ref: Mapping[str, Any],
    destination_binding_ref: Mapping[str, Any],
    physical_acquisition_origin: str,
    navigation_depth: int,
    ancestor_physical_identity_digests: Sequence[str],
) -> dict[str, Any]:
    binding = validate_navigation_destination_binding_ref(destination_binding_ref)
    origin = _token(physical_acquisition_origin, "physical_acquisition_origin")
    if origin not in {"discovery_candidate", "navigation_candidate"}:
        raise SearchOSNavigationError("physical_acquisition_origin_invalid")
    core = {
        "schema_version": SEARCHOS_NAVIGATION_USE_CUSTODY_REF_SCHEMA_VERSION,
        "slot_ref": _required_ref(slot_ref, "slot_ref"),
        "navigation_selection_ref": _required_ref(selection_ref, "selection_ref"),
        "navigation_edge_ref": _required_ref(edge_ref, "edge_ref"),
        "physical_custody_ref": _required_ref(
            physical_custody_ref, "physical_custody_ref"
        ),
        "fetch_read_content_packet_ref": _required_ref(
            fetch_read_content_packet_ref, "fetch_read_content_packet_ref"
        ),
        "evidence_ledger_custody_ref": _required_ref(
            evidence_ledger_custody_ref, "evidence_ledger_custody_ref"
        ),
        "destination_binding_ref": binding,
        "physical_identity_digest": binding["physical_identity_digest"],
        "full_destination_digest": binding["full_destination_digest"],
        "physical_acquisition_origin": origin,
        "navigation_depth": _bounded_nonnegative_int(
            navigation_depth, "navigation_depth", maximum=NAVIGATION_MAX_DEPTH
        ),
        "ancestor_physical_identity_digests": [
            _digest_token(item, "ancestor_physical_identity_digest")
            for item in ancestor_physical_identity_digests
        ],
        "bounded_content_present": True,
    }
    digest = _digest(core)
    return {
        **core,
        "searchos_navigation_use_custody_id": (
            f"searchos-navigation-use-custody:{digest[:24]}"
        ),
        "searchos_navigation_use_custody_digest": digest,
    }


def _validate_navigation_parent_custody_join(
    *,
    draft: SearchOSNavigationExtractionDraftV1,
    fetch_read_packet: Mapping[str, Any],
    evidence_ledger_custody: Mapping[str, Any],
    parent_custody_ref: Mapping[str, Any],
    slot_ref: Mapping[str, Any],
) -> None:
    if fetch_read_packet.get("schema_version") != "fetch_read_content_packet_v2":
        raise SearchOSNavigationError("navigation_parent_packet_v2_required")
    expected_pairs = (
        ("run_id", draft.run_id),
        ("request_id", draft.request_id),
        ("retained_digest", draft.retained_digest),
        ("retained_character_count", draft.retained_character_count),
    )
    for key, expected in expected_pairs:
        if fetch_read_packet.get(key) != expected:
            raise SearchOSNavigationError(f"navigation_parent_packet_{key}_mismatch")
    for key, expected in (
        ("acquisition_artifact_ref", draft.artifact_ref),
        ("physical_acquisition_ref", draft.physical_acquisition_ref),
        ("source_obligation_ref", draft.source_obligation_ref),
        ("component_ref", draft.component_ref),
        ("answer_contract_ref", draft.answer_contract_ref),
    ):
        if fetch_read_packet.get(key) != expected:
            raise SearchOSNavigationError(f"navigation_parent_packet_{key}_mismatch")
    if fetch_read_packet.get("attempted_source_full_digest") != draft.attempted_parent_full_digest:
        raise SearchOSNavigationError("navigation_parent_attempted_identity_mismatch")
    packet_ref = _fetch_packet_ref(fetch_read_packet)
    ledger_ref = _ledger_custody_ref(evidence_ledger_custody)
    if evidence_ledger_custody.get("fetch_read_content_packet_ref") != packet_ref:
        raise SearchOSNavigationError("navigation_parent_ledger_packet_mismatch")
    if evidence_ledger_custody.get("physical_acquisition_ref") != draft.physical_acquisition_ref:
        raise SearchOSNavigationError("navigation_parent_ledger_physical_mismatch")
    if parent_custody_ref.get("fetch_read_content_packet_ref") != packet_ref:
        raise SearchOSNavigationError("navigation_parent_use_packet_mismatch")
    if parent_custody_ref.get("evidence_ledger_custody_ref") != ledger_ref:
        raise SearchOSNavigationError("navigation_parent_use_ledger_mismatch")
    if parent_custody_ref.get("physical_acquisition_ref") != draft.physical_acquisition_ref:
        raise SearchOSNavigationError("navigation_parent_use_physical_mismatch")
    if parent_custody_ref.get("slot_ref") != slot_ref:
        raise SearchOSNavigationError("navigation_parent_use_slot_mismatch")
    if parent_custody_ref.get("source_obligation_ref") != draft.source_obligation_ref:
        raise SearchOSNavigationError("navigation_parent_use_obligation_mismatch")
    if parent_custody_ref.get("component_ref") != draft.component_ref:
        raise SearchOSNavigationError("navigation_parent_use_component_mismatch")
    if parent_custody_ref.get("attempted_source_full_digest") != draft.attempted_parent_full_digest:
        raise SearchOSNavigationError("navigation_parent_use_attempted_identity_mismatch")


def _fetch_packet_ref(packet: Mapping[str, Any]) -> dict[str, str]:
    return {
        "fetch_read_content_packet_id": _token(
            packet.get("fetch_read_content_packet_id"),
            "fetch_read_content_packet_id",
        ),
        "fetch_read_content_packet_digest": _digest_token(
            packet.get("fetch_read_content_packet_digest"),
            "fetch_read_content_packet_digest",
        ),
    }


def _ledger_custody_ref(custody: Mapping[str, Any]) -> dict[str, str]:
    return {
        "evidence_ledger_custody_id": _token(
            custody.get("evidence_ledger_custody_id"),
            "evidence_ledger_custody_id",
        ),
        "evidence_ledger_custody_digest": _digest_token(
            custody.get("evidence_ledger_custody_digest"),
            "evidence_ledger_custody_digest",
        ),
    }


def _validate_contributor(value: Mapping[str, Any]) -> dict[str, Any]:
    contributor = _mapping(value, "navigation_contributor")
    required = {
        "navigation_contributor_id",
        "navigation_contributor_digest",
        "slot_ref",
        "stable_option_ref",
        "destination_binding_ref",
        "parent_custody_ref",
        "parent_depth",
        "child_depth",
        "parent_custody_admission_ordinal",
        "source_link_ordinal",
        "relationship_label",
        "label_digest",
        "href_digest",
    }
    if set(contributor) != required:
        raise SearchOSNavigationError("navigation_contributor_fields_invalid")
    core = {
        key: deepcopy(value)
        for key, value in contributor.items()
        if key not in {"navigation_contributor_id", "navigation_contributor_digest"}
    }
    digest = _digest(core)
    slot_id = _slot_id(core["slot_ref"])
    expected_id = f"navigation-contributor:{slot_id}:{digest[:24]}"
    if contributor.get("navigation_contributor_digest") != digest or contributor.get("navigation_contributor_id") != expected_id:
        raise SearchOSNavigationError("navigation_contributor_identity_mismatch")
    validate_navigation_destination_binding_ref(core["destination_binding_ref"])
    _required_ref(core["parent_custody_ref"], "parent_custody_ref")
    _bounded_nonnegative_int(core["parent_depth"], "parent_depth", maximum=NAVIGATION_MAX_DEPTH)
    _bounded_positive_int(core["child_depth"], "child_depth")
    _bounded_positive_int(
        core["parent_custody_admission_ordinal"],
        "parent_custody_admission_ordinal",
    )
    _bounded_positive_int(core["source_link_ordinal"], "source_link_ordinal")
    _token(core["relationship_label"], "relationship_label", maximum=160)
    _digest_token(core["label_digest"], "label_digest")
    _digest_token(core["href_digest"], "href_digest")
    return deepcopy(contributor)


def _contributor_order_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(value.get("child_depth", 0)),
        int(value.get("parent_custody_admission_ordinal", 0)),
        int(value.get("source_link_ordinal", 0)),
        str(value.get("navigation_contributor_digest", "")),
    )


def _validate_candidate_set_proposal(value: Mapping[str, Any]) -> dict[str, Any]:
    proposal = _mapping(value, "navigation_candidate_set")
    if proposal.get("schema_version") != SEARCHOS_NAVIGATION_CANDIDATE_SET_SCHEMA_VERSION:
        raise SearchOSNavigationError("navigation_candidate_set_schema_invalid")
    if proposal.get("owner") != SEARCHOS_NAVIGATION_OWNER:
        raise SearchOSNavigationError("navigation_candidate_set_owner_invalid")
    if proposal.get("admission_posture") != "pending_runkernel_admission":
        raise SearchOSNavigationError("navigation_candidate_set_posture_invalid")
    core = {
        key: deepcopy(item)
        for key, item in proposal.items()
        if key
        not in {
            "navigation_candidate_set_id",
            "navigation_candidate_set_digest",
        }
    }
    digest = _digest(core)
    slot_id = _slot_id(proposal.get("slot_ref"))
    expected_id = f"navigation-candidate-set:{slot_id}:{digest[:24]}"
    if proposal.get("navigation_candidate_set_digest") != digest or proposal.get("navigation_candidate_set_id") != expected_id:
        raise SearchOSNavigationError("navigation_candidate_set_identity_mismatch")
    for contributor in _sequence(proposal.get("candidate_contributors")):
        _validate_contributor(contributor)
    return deepcopy(proposal)


def _validate_navigation_candidate_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _mapping(value, "navigation_candidate_ref")
    required = {
        "schema_version",
        "stable_option_ref",
        "navigation_lineage_snapshot_ref",
        "representative_contributor_ref",
        "destination_binding_ref",
        "navigation_candidate_id",
        "navigation_candidate_digest",
    }
    if set(candidate) != required:
        raise SearchOSNavigationError("navigation_candidate_ref_fields_invalid")
    if candidate.get("schema_version") != SEARCHOS_NAVIGATION_CANDIDATE_REF_SCHEMA_VERSION:
        raise SearchOSNavigationError("navigation_candidate_ref_schema_invalid")
    core = {
        key: deepcopy(item)
        for key, item in candidate.items()
        if key not in {"navigation_candidate_id", "navigation_candidate_digest"}
    }
    digest = _digest(core)
    option_id = _token(
        candidate.get("stable_option_ref", {}).get("navigation_option_id"),
        "navigation_option_id",
    )
    expected_id = f"navigation-candidate:{option_id}:{digest[:24]}"
    if candidate.get("navigation_candidate_digest") != digest or candidate.get("navigation_candidate_id") != expected_id:
        raise SearchOSNavigationError("navigation_candidate_ref_identity_mismatch")
    validate_navigation_destination_binding_ref(candidate["destination_binding_ref"])
    return deepcopy(candidate)


def _validated_retained_state(value: Mapping[str, Any]) -> dict[str, Any]:
    state = _mapping(value, "navigation_retained_state")
    if state.get("schema_version") != SEARCHOS_NAVIGATION_RETAINED_STATE_SCHEMA_VERSION:
        raise SearchOSNavigationError("navigation_retained_state_schema_invalid")
    if state.get("owner") != SEARCHOS_NAVIGATION_OWNER:
        raise SearchOSNavigationError("navigation_retained_state_owner_invalid")
    required_buckets = (
        "ceilings",
        "slot_reservation_status",
        "retained_counts",
        "options_by_id",
        "contributors_by_id",
        "lineages_by_id",
        "option_states_by_id",
        "candidate_sets_by_id",
        "edges_by_id",
        "selection_leases_by_id",
        "terminal_physical_operations_by_key",
        "physical_custody_by_digest",
        "overflow_totals",
    )
    if any(not isinstance(state.get(key), Mapping) for key in required_buckets):
        raise SearchOSNavigationError("navigation_retained_state_bucket_invalid")
    actual = {
        "stable_options": len(state["options_by_id"]),
        "contributors": len(state["contributors_by_id"]),
        "lineages": len(state["lineages_by_id"]),
        "candidate_sets": len(state["candidate_sets_by_id"]),
        "deep_edges": len(state["edges_by_id"]),
    }
    if state["retained_counts"] != actual:
        raise SearchOSNavigationError("navigation_retained_count_mismatch")
    for key, count in actual.items():
        if count > int(state["ceilings"].get(key, -1)):
            raise SearchOSNavigationError("navigation_retained_capacity_exceeded")
    return deepcopy(state)


def _capacity_available(
    state: Mapping[str, Any],
    category: str,
    slot_id: str,
    requested_increment: int,
) -> bool:
    used = int(state["retained_counts"][category])
    ceiling = int(state["ceilings"][category])
    if category == "deep_edges":
        return used + requested_increment <= ceiling
    protected_other_slots = sum(
        NAVIGATION_REQUIRED_SLOT_RESERVE
        for required_slot, status in state["slot_reservation_status"].items()
        if required_slot != slot_id and status == "reserved"
    )
    return used + requested_increment <= ceiling - protected_other_slots


def _slot_id(slot_ref: Mapping[str, Any] | Any) -> str:
    slot = _mapping(slot_ref, "slot_ref")
    return _token(slot.get("slot_id"), "slot_id")


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SearchOSNavigationError("navigation_sequence_required")
    return list(value)


def _iter_supported_markdown_links(
    text: str,
) -> Iterable[tuple[int, str, str]]:
    """Bounded scanner for inline links and HTTP(S) autolinks."""

    index = 0
    ordinal = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character == "<":
            close = text.find(">", index + 1, min(length, index + 704))
            if close != -1:
                target = text[index + 1 : close]
                if target.startswith(("http://", "https://", "HTTP://", "HTTPS://")):
                    ordinal += 1
                    yield ordinal, "linked page", target
                    index = close + 1
                    continue
        if character == "[" and (index == 0 or text[index - 1] != "!"):
            label_close = _scan_balanced(text, index, "[", "]", 512)
            if label_close is not None and label_close + 1 < length and text[label_close + 1] == "(":
                destination_close = _scan_balanced(
                    text, label_close + 1, "(", ")", 900
                )
                if destination_close is not None:
                    raw = text[label_close + 2 : destination_close]
                    destination = _markdown_destination(raw)
                    if destination is not None:
                        ordinal += 1
                        yield ordinal, text[index + 1 : label_close], destination
                    index = destination_close + 1
                    continue
        index += 1


def _scan_balanced(
    text: str,
    start: int,
    opening: str,
    closing: str,
    maximum_span: int,
) -> int | None:
    depth = 0
    escaped = False
    stop = min(len(text), start + maximum_span)
    for index in range(start, stop):
        character = text[index]
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == opening:
            depth += 1
        elif character == closing:
            depth -= 1
            if depth == 0:
                return index
    return None


def _markdown_destination(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if value.startswith("<"):
        close = value.find(">")
        if close <= 1:
            return None
        return value[1:close]
    escaped = False
    depth = 0
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character.isspace() and depth == 0:
            return value[:index] or None
    return value


def _effective_resolution_base(
    *,
    attempted: _NormalizedNavigationURL,
    final_url: str | None,
    resolved_url: str | None,
) -> tuple[_NormalizedNavigationURL | None, str]:
    for label, candidate in (("final", final_url), ("resolved", resolved_url)):
        if not candidate:
            continue
        try:
            normalized = normalize_navigation_url(candidate)
            _validate_origin_transition(attempted, normalized)
        except SearchOSNavigationError:
            return None, NAVIGATION_EFFECTIVE_BASE_OUT_OF_SCOPE
        return normalized, f"{label}_url_accepted_as_resolution_base"
    return attempted, "attempted_parent_url_resolution_base"


def _validate_origin_transition(
    anchor: _NormalizedNavigationURL,
    destination: _NormalizedNavigationURL,
) -> None:
    if destination.query_present:
        raise SearchOSNavigationError(
            NAVIGATION_QUERY_LOCATOR_NOT_SUPPORTED
        )
    if anchor.hostname != destination.hostname:
        raise SearchOSNavigationError(
            "navigation_destination_origin_out_of_scope"
        )
    if anchor.scheme == "https" and destination.scheme == "http":
        raise SearchOSNavigationError("navigation_destination_scheme_downgrade")
    same_scheme = anchor.scheme == destination.scheme
    implicit_upgrade = (
        anchor.scheme == "http"
        and destination.scheme == "https"
        and anchor.port_posture == "implicit_default_80"
        and destination.port_posture == "implicit_default_443"
    )
    if not same_scheme and not implicit_upgrade:
        raise SearchOSNavigationError(
            "navigation_destination_origin_out_of_scope"
        )
    if same_scheme and anchor.port_posture != destination.port_posture:
        raise SearchOSNavigationError(
            "navigation_destination_port_posture_mismatch"
        )


def _destination_binding_ref(
    binding_id: str, normalized: _NormalizedNavigationURL
) -> dict[str, Any]:
    core = {
        "full_destination_digest": normalized.full_digest,
        "semantic_identity_digest": normalized.semantic_digest,
        "physical_identity_digest": normalized.physical_digest,
        "normalized_scheme": normalized.scheme,
        "normalized_hostname": normalized.hostname,
        "port_posture": normalized.port_posture,
        "path_digest": _digest_text(normalized.path),
        "query_present": False,
    }
    return {
        "destination_binding_id": binding_id,
        "destination_binding_digest": _digest(core),
        **core,
    }


def _count_markdown_like_links(text: str) -> int:
    return sum(1 for _ in _iter_supported_markdown_links(text))


def _bounded_relationship_label(value: str) -> str:
    compact = " ".join(value.split())
    return compact[:160] or "linked page"


def _netloc_has_explicit_port(netloc: str) -> bool:
    host_port = netloc.rsplit("@", 1)[-1]
    if host_port.startswith("["):
        close = host_port.find("]")
        return close != -1 and host_port[close + 1 :].startswith(":")
    return ":" in host_port


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def _is_ascii(value: str) -> bool:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _artifact_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    ref = _required_ref(value, "artifact_ref")
    if not ref.get("artifact_id") or not ref.get("artifact_digest"):
        raise SearchOSNavigationError("navigation_artifact_ref_invalid")
    _digest_token(ref.get("artifact_digest"), "artifact_digest")
    return ref


def _mapping(value: Mapping[str, Any] | Any, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SearchOSNavigationError(f"{field}_mapping_required")
    return dict(value)


def _required_ref(value: Mapping[str, Any] | Any, field: str) -> dict[str, Any]:
    ref = _mapping(value, field)
    if not ref:
        raise SearchOSNavigationError(f"{field}_missing")
    _reject_url_bearing_keys(ref, field)
    return deepcopy(ref)


def _reject_url_bearing_keys(value: Any, field: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized in {
                "url",
                "href",
                "path",
                "query",
                "raw_href",
                "selected_urls",
                "available_urls",
                "root_url",
                "requested_url",
                "attempted_url",
                "final_url",
                "resolved_url",
                "canonical_url",
                "provider_reported_url",
                "durable_source_url",
            }:
                raise SearchOSNavigationError(
                    f"{field}_contains_exact_locator"
                )
            _reject_url_bearing_keys(item, field)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_url_bearing_keys(item, field)


def _token(value: Any, field: str, *, maximum: int = 700) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise SearchOSNavigationError(f"{field}_invalid")
    return value


def _digest_token(value: Any, field: str) -> str:
    token = _token(value, field, maximum=64)
    if len(token) != 64 or any(character not in "0123456789abcdef" for character in token):
        raise SearchOSNavigationError(f"{field}_invalid")
    return token


def _bounded_nonnegative_int(value: Any, field: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
        raise SearchOSNavigationError(f"{field}_invalid")
    return value


def _bounded_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SearchOSNavigationError(f"{field}_invalid")
    return value


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
