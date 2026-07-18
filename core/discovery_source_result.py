"""Stable DISCOVER result identity and bounded run-local material custody.

The identity is created at the provider-result boundary, before URL deduplication,
chunking, or ranking.  It carries lineage and digests, never provider text.  The
companion store keeps the bounded material needed by the ordinary retrieval path
without granting fetch/read, evidence, citation, or answer authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from urllib.parse import SplitResult, urlsplit, urlunsplit

DISCOVERY_SOURCE_RESULT_IDENTITY_SCHEMA_VERSION = (
    "discovery_source_result_identity_discover_result_candidate_handoff_convergence_01_v1"
)
DISCOVERY_RESULT_MATERIAL_SCHEMA_VERSION = (
    "discovery_result_material_discover_result_candidate_handoff_convergence_01_v1"
)
DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_SCHEMA_VERSION = (
    "discovery_result_runkernel_projection_discover_result_candidate_handoff_convergence_01_v1"
)
DISCOVERY_SOURCE_RESULT_IDENTITY_OWNER = "retrieval.DiscoverySourceResultIdentity"
DISCOVERY_RESULT_MATERIAL_OWNER = "retrieval.DiscoveryResultMaterialStore"

DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP = 80
DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP = 4_096
DISCOVERY_RESULT_MATERIAL_CHAR_CAP = 20_000
DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP = 8
DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP = 16 * 1_024
DISCOVERY_RESULT_TITLE_CHAR_CAP = 220
DISCOVERY_RESULT_SNIPPET_CHAR_CAP = 500

_REFERENCE_METADATA_KEYS = frozenset(
    {
        "action_type",
        "kind",
        "owner",
        "revision",
        "schema_version",
        "sequence",
        "stage",
        "version",
    }
)

_CLOSED_SURFACE_FLAGS = MappingProxyType(
    {
        "raw_provider_payload_retained": False,
        "raw_payload_retained": False,
        "provider_result_text_in_identity": False,
        "fetch_read_executed": False,
        "fetch_read_retrieval_executed": False,
        "exact_url_fetch_read_executed": False,
        "separate_exact_url_transport_performed": False,
        "read_executed": False,
        "exact_url_acquisition_executed": False,
        "exact_url_cap_charged": False,
        "acquisition_need_proposal_created": False,
        "evidence_created": False,
        "evidence_ledger_admitted": False,
        "evidence_authority": False,
        "citation_eligible": False,
        "citation_created": False,
        "citation_authority": False,
        "source_obligation_satisfied": False,
        "sufficiency_decided": False,
        "final_answer_packet_created": False,
        "author_input_created": False,
        "downstream_answer_authority": False,
        "product_correctness_claimed": False,
    }
)


class DiscoverySourceResultError(ValueError):
    """Raised when required provider-result lineage cannot be represented safely."""


@dataclass(frozen=True, slots=True)
class DiscoverySourceResultIdentity:
    """Immutable, text-free identity for one ordered provider result occurrence."""

    source_result_id: str
    source_result_digest: str
    run_id: str
    request_id: str
    query_plan_ref: Mapping[str, Any]
    query_plan_item_ref: Mapping[str, Any]
    query_digest: str
    query_role: str
    retrieval_role: str
    iteration: int
    retrieval_action_ref: Mapping[str, Any]
    provider_plan_ref: Mapping[str, Any]
    provider_plan_record_ref: Mapping[str, Any]
    provider_route_ref: Mapping[str, Any]
    provider: str
    capability: str
    qualifier: str
    operation: str
    variant: str
    output_type: str
    provider_call_ordinal: int
    result_rank: int
    normalized_url: str
    domain: str
    published_or_observed_date: str | None
    material_ref: Mapping[str, Any]
    material_digest: str
    material_class: str
    material_chars_retained: int
    material_truncated: bool
    url_disposition: str
    current_answer_contract_ref: Mapping[str, Any] | None = None
    component_ref: Mapping[str, Any] | None = None

    def ref(self) -> dict[str, str]:
        """Return the only source-result reference shape exposed to consumers."""

        return {
            "source_result_id": self.source_result_id,
            "source_result_digest": self.source_result_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": DISCOVERY_SOURCE_RESULT_IDENTITY_SCHEMA_VERSION,
            "owner": DISCOVERY_SOURCE_RESULT_IDENTITY_OWNER,
            "source_result_id": self.source_result_id,
            "source_result_digest": self.source_result_digest,
            "run_id": self.run_id,
            "request_id": self.request_id,
            "query_plan_ref": dict(self.query_plan_ref),
            "query_plan_item_ref": dict(self.query_plan_item_ref),
            "query_digest": self.query_digest,
            "query_role": self.query_role,
            "retrieval_role": self.retrieval_role,
            "iteration": self.iteration,
            "retrieval_action_ref": dict(self.retrieval_action_ref),
            "provider_plan_ref": dict(self.provider_plan_ref),
            "provider_plan_record_ref": dict(self.provider_plan_record_ref),
            "provider_route_ref": dict(self.provider_route_ref),
            "provider": self.provider,
            "capability": self.capability,
            "qualifier": self.qualifier,
            "operation": self.operation,
            "variant": self.variant,
            "output_type": self.output_type,
            "provider_call_ordinal": self.provider_call_ordinal,
            "result_rank": self.result_rank,
            "normalized_url": self.normalized_url,
            "domain": self.domain,
            "material_ref": dict(self.material_ref),
            "material_digest": self.material_digest,
            "material_class": self.material_class,
            "material_chars_retained": self.material_chars_retained,
            "material_truncated": self.material_truncated,
            "url_disposition": self.url_disposition,
            **dict(_CLOSED_SURFACE_FLAGS),
        }
        if self.published_or_observed_date:
            payload["published_or_observed_date"] = self.published_or_observed_date
        if self.current_answer_contract_ref:
            payload["current_answer_contract_ref"] = dict(self.current_answer_contract_ref)
        if self.component_ref:
            payload["component_ref"] = dict(self.component_ref)
        return payload

    @property
    def canonical_bytes(self) -> int:
        return len(_canonical_json(self.to_dict()).encode("utf-8"))


@dataclass(frozen=True, slots=True)
class DiscoveryResultMaterialRecord:
    """Bounded run-local material for one admitted source-result occurrence."""

    material_id: str
    material_digest: str
    retained_material_digest: str
    primary_source_result_ref: Mapping[str, str]
    normalized_url: str
    domain: str
    provider: str
    material_class: str
    title: str
    snippet: str
    material_text: str
    original_chars: int
    retained_chars: int
    truncated: bool
    published_or_observed_date: str | None = None

    def ref(self) -> dict[str, str]:
        return {
            "material_id": self.material_id,
            "material_digest": self.material_digest,
        }

    def candidate_fields(self) -> dict[str, Any]:
        """Return the bounded non-evidence fields allowed into a candidate packet."""

        payload: dict[str, Any] = {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.normalized_url,
            "domain": self.domain,
            "material_ref": self.ref(),
            "material_class": self.material_class,
            "material_digest": self.material_digest,
        }
        if self.published_or_observed_date:
            payload["published_or_observed_date"] = self.published_or_observed_date
        return payload


class DiscoveryResultMaterialStore:
    """Run-scoped stable-first store for identities and bounded provider material."""

    def __init__(self, *, run_id: str | None = None, request_id: str | None = None) -> None:
        self._run_id = _optional_scope_token(run_id, "run_id")
        self._request_id = _optional_scope_token(request_id, "request_id")
        self._identities: list[DiscoverySourceResultIdentity] = []
        self._identities_by_id: dict[str, DiscoverySourceResultIdentity] = {}
        self._materials_by_id: dict[str, DiscoveryResultMaterialRecord] = {}
        self._primary_material_id_by_url: dict[str, str] = {}
        self._source_refs_by_url: dict[str, list[dict[str, str]]] = {}

        self._provider_call_count = 0
        self._last_reserved_provider_call_ordinal = 0
        self._provider_results_returned_count = 0
        self._provider_results_within_call_limit_count = 0
        self._provider_call_result_overflow_count = 0
        self._identity_canonical_bytes = 0
        self._identity_run_cap_overflow_count = 0
        self._identity_byte_cap_overflow_count = 0
        self._invalid_url_count = 0
        self._duplicate_url_count = 0
        self._material_chars_retained = 0
        self._material_truncation_count = 0

    @property
    def run_id(self) -> str | None:
        return self._run_id

    @property
    def request_id(self) -> str | None:
        return self._request_id

    def note_call(self, *, returned_count: int, admitted_limit: int) -> None:
        """Account one deterministically reduced call without retaining its payload."""

        returned = _nonnegative_int(returned_count, "returned_count")
        limit = _nonnegative_int(admitted_limit, "admitted_limit")
        within_limit = min(returned, limit)
        self._provider_call_count += 1
        self._provider_results_returned_count += returned
        self._provider_results_within_call_limit_count += within_limit
        self._provider_call_result_overflow_count += returned - within_limit

    def reserve_provider_call_ordinal(self) -> int:
        """Reserve the next run-scoped ordinal before concurrent dispatch."""

        self._last_reserved_provider_call_ordinal += 1
        return self._last_reserved_provider_call_ordinal

    def admit_result(
        self,
        *,
        context: Mapping[str, Any],
        provider: str,
        call_ordinal: int,
        result_rank: int,
        result: Mapping[str, Any],
        material_text: str | None,
        material_class: str,
    ) -> DiscoverySourceResultIdentity | None:
        """Admit one caller-ordered DISCOVER result or count a bounded rejection.

        Required lineage is validated before any state mutation.  Invalid URLs and
        cap excess are ordinary closed rejections and return ``None``.  A duplicate
        URL receives its own identity and material; stable-first URL representation
        is tracked separately from occurrence truth.
        """

        if not isinstance(context, Mapping):
            raise DiscoverySourceResultError("discovery result context must be a mapping")
        if not isinstance(result, Mapping):
            raise DiscoverySourceResultError("discovery provider result must be a mapping")

        lineage = _lineage_from_context(context)
        self._bind_scope(lineage["run_id"], lineage["request_id"])
        provider_name = _required_token(provider, "provider", limit=80).casefold()
        context_provider = _first_value(context, "provider", "provider_name", "selected_provider")
        if context_provider and _required_token(context_provider, "context provider", limit=80).casefold() != provider_name:
            raise DiscoverySourceResultError("provider does not match provider-route lineage")
        provider_call_ordinal = _positive_int(call_ordinal, "call_ordinal")
        provider_result_rank = _positive_int(result_rank, "result_rank")
        result_material_class = _required_token(material_class, "material_class", limit=120)

        try:
            normalized_url = normalize_discovery_result_url(result.get("url") or result.get("link"))
        except DiscoverySourceResultError:
            self._invalid_url_count += 1
            return None

        if len(self._identities) >= DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP:
            self._identity_run_cap_overflow_count += 1
            return None

        source_result_id = _source_result_id(
            run_id=lineage["run_id"],
            request_id=lineage["request_id"],
            query_plan_item_ref=lineage["query_plan_item_ref"],
            retrieval_action_ref=lineage["retrieval_action_ref"],
            provider_route_ref=lineage["provider_route_ref"],
            provider_call_ordinal=provider_call_ordinal,
            result_rank=provider_result_rank,
            normalized_url=normalized_url,
        )
        if source_result_id in self._identities_by_id:
            raise DiscoverySourceResultError("source-result lineage collision")

        duplicate_url = normalized_url in self._primary_material_id_by_url
        pending_material = _build_material_record(
            source_result_id=source_result_id,
            normalized_url=normalized_url,
            provider=provider_name,
            result=result,
            material_text=material_text,
            material_class=result_material_class,
        )
        material_ref = pending_material.ref()
        material_digest = pending_material.material_digest
        retained_chars = pending_material.retained_chars
        material_was_truncated = pending_material.truncated
        retained_material_class = pending_material.material_class
        disposition = "duplicate_url_material_retained" if duplicate_url else "primary_url_material_retained"

        identity = _build_identity(
            lineage=lineage,
            source_result_id=source_result_id,
            provider=provider_name,
            provider_call_ordinal=provider_call_ordinal,
            result_rank=provider_result_rank,
            normalized_url=normalized_url,
            result=result,
            material_ref=material_ref,
            material_digest=material_digest,
            material_class=retained_material_class,
            material_chars_retained=retained_chars,
            material_truncated=material_was_truncated,
            url_disposition=disposition,
        )
        if identity.canonical_bytes > DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP:
            self._identity_byte_cap_overflow_count += 1
            return None

        pending_material = DiscoveryResultMaterialRecord(
            material_id=pending_material.material_id,
            material_digest=pending_material.material_digest,
            retained_material_digest=pending_material.retained_material_digest,
            primary_source_result_ref=_frozen(identity.ref()),
            normalized_url=pending_material.normalized_url,
            domain=pending_material.domain,
            provider=pending_material.provider,
            material_class=pending_material.material_class,
            title=pending_material.title,
            snippet=pending_material.snippet,
            material_text=pending_material.material_text,
            original_chars=pending_material.original_chars,
            retained_chars=pending_material.retained_chars,
            truncated=pending_material.truncated,
            published_or_observed_date=pending_material.published_or_observed_date,
        )
        self._materials_by_id[pending_material.material_id] = pending_material
        if not duplicate_url:
            self._primary_material_id_by_url[normalized_url] = pending_material.material_id
        self._material_chars_retained += pending_material.retained_chars
        if pending_material.truncated:
            self._material_truncation_count += 1
        if duplicate_url:
            self._duplicate_url_count += 1

        self._identities.append(identity)
        self._identities_by_id[identity.source_result_id] = identity
        self._source_refs_by_url.setdefault(normalized_url, []).append(identity.ref())
        self._identity_canonical_bytes += identity.canonical_bytes
        return identity

    def identities(self) -> tuple[DiscoverySourceResultIdentity, ...]:
        return tuple(self._identities)

    def identity_for_ref(self, ref: Mapping[str, Any] | str) -> DiscoverySourceResultIdentity | None:
        source_result_id = _reference_id(ref, "source_result_id")
        return self._identities_by_id.get(source_result_id)

    def ref_for_url(self, url: str) -> dict[str, str]:
        """Return the stable-first source-result ref for an absolute HTTP(S) URL."""

        try:
            normalized_url = normalize_discovery_result_url(url)
        except DiscoverySourceResultError:
            return {}
        refs = self._source_refs_by_url.get(normalized_url, ())
        return dict(refs[0]) if refs else {}

    def contributors_for_url(self, url: str) -> dict[str, Any]:
        """Return bounded refs plus a digest covering the complete admitted sequence."""

        try:
            normalized_url = normalize_discovery_result_url(url)
        except DiscoverySourceResultError:
            return {
                "contributing_source_result_refs": [],
                "contributor_count": 0,
                "contributor_overflow_count": 0,
                "full_contributor_digest": _digest([]),
            }
        refs = [dict(item) for item in self._source_refs_by_url.get(normalized_url, ())]
        retained = refs[:DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP]
        return {
            "contributing_source_result_refs": retained,
            "contributor_count": len(refs),
            "contributor_overflow_count": max(0, len(refs) - len(retained)),
            "full_contributor_digest": _digest(refs),
        }

    def material_for_ref(
        self,
        ref: Mapping[str, Any] | str,
    ) -> DiscoveryResultMaterialRecord | None:
        """Resolve a material ref or source-result ref without copying provider text."""

        if isinstance(ref, str):
            token = ref.strip()
            if token.startswith("discovery-material:"):
                return self._materials_by_id.get(token)
            identity = self._identities_by_id.get(token)
            if identity is None:
                return None
            return self._materials_by_id.get(str(identity.material_ref.get("material_id") or ""))
        material_id = _reference_id(ref, "material_id")
        if material_id:
            return self._materials_by_id.get(material_id)
        source_result_id = _reference_id(ref, "source_result_id")
        identity = self._identities_by_id.get(source_result_id)
        if identity is None:
            return None
        return self._materials_by_id.get(str(identity.material_ref.get("material_id") or ""))

    def identity_set_ref(self) -> dict[str, Any]:
        """Return the stable ref for the complete admitted identity sequence."""

        run_id, request_id = self._scope_or_error()
        refs = [identity.ref() for identity in self._identities]
        set_digest = _digest(
            {
                "schema_version": DISCOVERY_SOURCE_RESULT_IDENTITY_SCHEMA_VERSION,
                "run_id": run_id,
                "request_id": request_id,
                "ordered_source_result_refs": refs,
            }
        )
        return {
            "source_result_identity_set_id": f"source-result-identity-set:{set_digest[:24]}",
            "source_result_identity_set_digest": set_digest,
            "source_result_identity_count": len(refs),
        }

    def runkernel_projection(
        self,
        *,
        selected_refs: Sequence[Mapping[str, Any]] = (),
        packet_ref: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a text-free projection bounded to exactly 16 KiB."""

        normalized_selected = [_source_result_ref(item) for item in selected_refs]
        normalized_selected = [item for item in normalized_selected if item]
        full_selected_digest = _digest(normalized_selected)
        retained = list(normalized_selected)
        safe_packet_ref = _optional_generic_ref(packet_ref)

        while True:
            projection = {
                "schema_version": DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_SCHEMA_VERSION,
                "owner": DISCOVERY_RESULT_MATERIAL_OWNER,
                "source_result_identity_set_ref": self.identity_set_ref(),
                "source_result_identity_run_cap": DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP,
                "source_result_identity_canonical_byte_cap": (
                    DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP
                ),
                "source_result_identity_canonical_bytes": self._identity_canonical_bytes,
                "selected_source_result_refs": retained,
                "selected_source_result_count": len(normalized_selected),
                "selected_source_result_refs_retained_count": len(retained),
                "selected_source_result_ref_overflow_count": len(normalized_selected) - len(retained),
                "full_selected_source_result_refs_digest": full_selected_digest,
                "search_result_candidate_packet_ref": safe_packet_ref,
                "projection_byte_cap": DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP,
                "disposition_counts": self._disposition_counts(),
                **dict(_CLOSED_SURFACE_FLAGS),
            }
            if len(_canonical_json(projection).encode("utf-8")) <= DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP:
                return projection
            if not retained:
                raise DiscoverySourceResultError("RunKernel discovery projection exceeds its 16 KiB cap")
            retained.pop()

    def telemetry(self) -> dict[str, Any]:
        """Return bounded counts and digests; never URLs, queries, or provider text."""

        contributor_overflow = sum(
            max(0, len(refs) - DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP)
            for refs in self._source_refs_by_url.values()
        )
        return {
            "schema_version": DISCOVERY_SOURCE_RESULT_IDENTITY_SCHEMA_VERSION,
            "source_result_identity_set_ref": self.identity_set_ref(),
            "provider_call_count": self._provider_call_count,
            "provider_results_returned_count": self._provider_results_returned_count,
            "provider_results_within_call_limit_count": self._provider_results_within_call_limit_count,
            "provider_call_result_overflow_count": self._provider_call_result_overflow_count,
            "provider_results_observed": self._provider_results_returned_count,
            "provider_results_admitted": len(self._identities),
            "provider_results_rejected": (
                self._invalid_url_count + self._identity_byte_cap_overflow_count
            ),
            "provider_results_truncated": (
                self._provider_call_result_overflow_count
                + self._identity_run_cap_overflow_count
            ),
            "provider_results_deduplicated": self._duplicate_url_count,
            "source_result_identity_count": len(self._identities),
            "source_result_identities_created": len(self._identities),
            "source_result_identity_run_cap": DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP,
            "source_result_identity_run_cap_overflow_count": self._identity_run_cap_overflow_count,
            "source_result_identity_canonical_byte_cap": (
                DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP
            ),
            "source_result_identity_canonical_bytes": self._identity_canonical_bytes,
            "canonical_result_identity_bytes_retained": (
                self._identity_canonical_bytes
            ),
            "source_result_identity_byte_cap_overflow_count": self._identity_byte_cap_overflow_count,
            "invalid_result_url_count": self._invalid_url_count,
            "unique_normalized_url_count": len(self._source_refs_by_url),
            "duplicate_normalized_url_count": self._duplicate_url_count,
            "material_record_count": len(self._materials_by_id),
            "material_char_cap": DISCOVERY_RESULT_MATERIAL_CHAR_CAP,
            "material_chars_retained": self._material_chars_retained,
            "material_truncation_count": self._material_truncation_count,
            "contributor_ref_cap": DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP,
            "contributor_ref_overflow_count": contributor_overflow,
            "disposition_counts": self._disposition_counts(),
            **dict(_CLOSED_SURFACE_FLAGS),
        }

    def _bind_scope(self, run_id: str, request_id: str) -> None:
        if self._run_id is None:
            self._run_id = run_id
        elif self._run_id != run_id:
            raise DiscoverySourceResultError("source-result store cannot cross run_id")
        if self._request_id is None:
            self._request_id = request_id
        elif self._request_id != request_id:
            raise DiscoverySourceResultError("source-result store cannot cross request_id")

    def _scope_or_error(self) -> tuple[str, str]:
        if not self._run_id or not self._request_id:
            raise DiscoverySourceResultError("source-result store requires run_id and request_id")
        return self._run_id, self._request_id

    def _disposition_counts(self) -> dict[str, int]:
        return {
            "primary_url_material_retained": len(self._primary_material_id_by_url),
            "duplicate_url_material_retained": self._duplicate_url_count,
            "invalid_result_url": self._invalid_url_count,
            "provider_call_result_overflow": self._provider_call_result_overflow_count,
            "identity_run_cap_overflow": self._identity_run_cap_overflow_count,
            "identity_byte_cap_overflow": self._identity_byte_cap_overflow_count,
        }


def normalize_discovery_result_url(value: Any) -> str:
    """Normalize one absolute HTTP(S) URL without changing path/query semantics."""

    if not isinstance(value, str) or not value.strip():
        raise DiscoverySourceResultError("discovery result requires an absolute URL")
    raw = value.strip()
    if len(raw) > 4_096 or any(ord(character) < 32 for character in raw):
        raise DiscoverySourceResultError("discovery result URL is invalid")
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise DiscoverySourceResultError("discovery result URL is invalid") from exc
    scheme = parsed.scheme.casefold()
    host = (parsed.hostname or "").casefold().rstrip(".")
    if scheme not in {"http", "https"} or not host:
        raise DiscoverySourceResultError("discovery result requires an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise DiscoverySourceResultError("discovery result URL cannot contain user information")

    netloc_host = f"[{host}]" if ":" in host else host
    if port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc_host = f"{netloc_host}:{port}"
    normalized = SplitResult(
        scheme=scheme,
        netloc=netloc_host,
        path=parsed.path or "/",
        query=parsed.query,
        fragment="",
    )
    return urlunsplit(normalized)


def _lineage_from_context(context: Mapping[str, Any]) -> dict[str, Any]:
    run_id = _required_token(context.get("run_id"), "run_id", limit=260)
    request_id = _required_token(context.get("request_id"), "request_id", limit=260)
    query_plan_ref = _required_named_ref(
        context.get("query_plan_ref"),
        label="query_plan_ref",
        output_id_key="query_plan_id",
        id_keys=("query_plan_id", "plan_id"),
        output_digest_key="query_plan_digest",
        digest_keys=("query_plan_digest", "plan_digest"),
    )
    query_plan_item_ref = _required_named_ref(
        context.get("query_plan_item_ref") or context.get("query_item_ref"),
        label="query_plan_item_ref",
        output_id_key="query_plan_item_id",
        id_keys=("query_plan_item_id", "item_id"),
        output_digest_key="query_plan_item_digest",
        digest_keys=("query_plan_item_digest", "item_digest"),
        extra_digest_keys=("query_digest",),
    )
    query_digest = _digest_token(
        query_plan_item_ref.get("query_digest") or context.get("query_digest"),
        "query_digest",
    )
    query_plan_item_ref = {**query_plan_item_ref, "query_digest": query_digest}
    retrieval_action_ref = _retrieval_action_ref(
        context.get("retrieval_action_ref") or context.get("action_ref")
    )
    provider_plan_ref = _required_named_ref(
        context.get("provider_plan_ref"),
        label="provider_plan_ref",
        output_id_key="provider_plan_id",
        id_keys=("provider_plan_id", "plan_id"),
        output_digest_key="provider_plan_digest",
        digest_keys=("provider_plan_digest", "plan_digest"),
    )
    provider_plan_record_ref = _required_named_ref(
        context.get("provider_plan_record_ref") or context.get("provider_record_ref"),
        label="provider_plan_record_ref",
        output_id_key="provider_plan_record_id",
        id_keys=("provider_plan_record_id", "record_id"),
        output_digest_key="provider_plan_record_digest",
        digest_keys=("provider_plan_record_digest", "record_digest"),
    )
    provider_route_ref = _required_named_ref(
        context.get("provider_route_ref")
        or context.get("provider_plan_route_ref")
        or context.get("route_decision_ref"),
        label="provider_route_ref",
        output_id_key="route_decision_id",
        id_keys=("route_decision_id", "provider_route_id", "route_id"),
        output_digest_key="route_decision_digest",
        digest_keys=("route_decision_digest", "provider_route_digest", "route_digest"),
    )

    capability = _required_token(
        _first_value(context, "provider_capability", "capability"),
        "provider_capability",
        limit=40,
    ).upper()
    if capability != "DISCOVER":
        raise DiscoverySourceResultError("source-result identity requires DISCOVER capability")
    qualifier = _required_token(
        _first_value(context, "discover_qualifier", "provider_qualifier", "qualifier"),
        "discover_qualifier",
        limit=80,
    )
    operation = _required_token(
        _first_value(context, "provider_operation", "operation"),
        "provider_operation",
        limit=120,
    )
    variant = _required_token(
        _first_value(context, "provider_variant", "variant"),
        "provider_variant",
        limit=120,
    )
    output_type = _required_token(
        _first_value(context, "provider_output_type", "output_type", "output"),
        "provider_output_type",
        limit=120,
    )
    query_role = _required_token(
        _first_value(context, "query_plan_role", "query_role", "role"),
        "query_role",
        limit=120,
    )
    retrieval_role = _required_token(
        _first_value(context, "retrieval_role", "provider_role"),
        "retrieval_role",
        limit=120,
    )
    iteration = _nonnegative_int(context.get("iteration"), "iteration")

    contract_ref = _optional_named_ref(
        context.get("current_answer_contract_ref") or context.get("answer_contract_ref"),
        output_id_key="contract_id",
        id_keys=("contract_id", "answer_contract_id"),
        output_digest_key="contract_digest",
        digest_keys=("contract_digest", "answer_contract_digest"),
    )
    component_value = context.get("component_ref")
    if component_value is None and context.get("component_id"):
        component_value = {"component_id": context.get("component_id")}
    component_ref = _optional_component_ref(component_value)

    return {
        "run_id": run_id,
        "request_id": request_id,
        "query_plan_ref": _frozen(query_plan_ref),
        "query_plan_item_ref": _frozen(query_plan_item_ref),
        "query_digest": query_digest,
        "query_role": query_role,
        "retrieval_role": retrieval_role,
        "iteration": iteration,
        "retrieval_action_ref": _frozen(retrieval_action_ref),
        "provider_plan_ref": _frozen(provider_plan_ref),
        "provider_plan_record_ref": _frozen(provider_plan_record_ref),
        "provider_route_ref": _frozen(provider_route_ref),
        "capability": capability,
        "qualifier": qualifier,
        "operation": operation,
        "variant": variant,
        "output_type": output_type,
        "current_answer_contract_ref": _frozen(contract_ref) if contract_ref else None,
        "component_ref": _frozen(component_ref) if component_ref else None,
    }


def _build_identity(
    *,
    lineage: Mapping[str, Any],
    source_result_id: str,
    provider: str,
    provider_call_ordinal: int,
    result_rank: int,
    normalized_url: str,
    result: Mapping[str, Any],
    material_ref: Mapping[str, Any],
    material_digest: str,
    material_class: str,
    material_chars_retained: int,
    material_truncated: bool,
    url_disposition: str,
) -> DiscoverySourceResultIdentity:
    values: dict[str, Any] = {
        "source_result_id": source_result_id,
        "run_id": lineage["run_id"],
        "request_id": lineage["request_id"],
        "query_plan_ref": lineage["query_plan_ref"],
        "query_plan_item_ref": lineage["query_plan_item_ref"],
        "query_digest": lineage["query_digest"],
        "query_role": lineage["query_role"],
        "retrieval_role": lineage["retrieval_role"],
        "iteration": lineage["iteration"],
        "retrieval_action_ref": lineage["retrieval_action_ref"],
        "provider_plan_ref": lineage["provider_plan_ref"],
        "provider_plan_record_ref": lineage["provider_plan_record_ref"],
        "provider_route_ref": lineage["provider_route_ref"],
        "provider": provider,
        "capability": lineage["capability"],
        "qualifier": lineage["qualifier"],
        "operation": lineage["operation"],
        "variant": lineage["variant"],
        "output_type": lineage["output_type"],
        "provider_call_ordinal": provider_call_ordinal,
        "result_rank": result_rank,
        "normalized_url": normalized_url,
        "domain": (urlsplit(normalized_url).hostname or "").casefold(),
        "published_or_observed_date": _clean_text(
            result.get("published_or_observed_date") or result.get("date"),
            limit=80,
        ),
        "material_ref": _frozen(material_ref),
        "material_digest": material_digest,
        "material_class": material_class,
        "material_chars_retained": material_chars_retained,
        "material_truncated": material_truncated,
        "url_disposition": url_disposition,
        "current_answer_contract_ref": lineage.get("current_answer_contract_ref"),
        "component_ref": lineage.get("component_ref"),
    }
    digest_payload = {
        "schema_version": DISCOVERY_SOURCE_RESULT_IDENTITY_SCHEMA_VERSION,
        **{key: _jsonable(value) for key, value in values.items() if value is not None},
        **dict(_CLOSED_SURFACE_FLAGS),
    }
    return DiscoverySourceResultIdentity(
        source_result_digest=_digest(digest_payload),
        **values,
    )


def _build_material_record(
    *,
    source_result_id: str,
    normalized_url: str,
    provider: str,
    result: Mapping[str, Any],
    material_text: str | None,
    material_class: str,
) -> DiscoveryResultMaterialRecord:
    full_material = material_text if isinstance(material_text, str) else str(material_text or "")
    retained_material = full_material[:DISCOVERY_RESULT_MATERIAL_CHAR_CAP]
    material_digest = _digest(
        {
            "material_class": material_class,
            "bounded_material": retained_material,
        }
    )
    retained_material_digest = material_digest
    material_id_digest = _digest(
        {
            "source_result_id": source_result_id,
            "normalized_url": normalized_url,
            "material_digest": material_digest,
        }
    )
    title = _clean_text(result.get("title") or result.get("name"), limit=DISCOVERY_RESULT_TITLE_CHAR_CAP) or ""
    snippet = _clean_text(result.get("snippet"), limit=DISCOVERY_RESULT_SNIPPET_CHAR_CAP)
    if not snippet:
        snippet = _clean_text(retained_material, limit=DISCOVERY_RESULT_SNIPPET_CHAR_CAP) or ""
    return DiscoveryResultMaterialRecord(
        material_id=f"discovery-material:{material_id_digest[:24]}",
        material_digest=material_digest,
        retained_material_digest=retained_material_digest,
        primary_source_result_ref=_frozen({}),
        normalized_url=normalized_url,
        domain=(urlsplit(normalized_url).hostname or "").casefold(),
        provider=provider,
        material_class=material_class,
        title=title,
        snippet=snippet,
        material_text=retained_material,
        original_chars=len(full_material),
        retained_chars=len(retained_material),
        truncated=len(retained_material) < len(full_material),
        published_or_observed_date=_clean_text(
            result.get("published_or_observed_date") or result.get("date"),
            limit=80,
        ),
    )


def _source_result_id(
    *,
    run_id: str,
    request_id: str,
    query_plan_item_ref: Mapping[str, Any],
    retrieval_action_ref: Mapping[str, Any],
    provider_route_ref: Mapping[str, Any],
    provider_call_ordinal: int,
    result_rank: int,
    normalized_url: str,
) -> str:
    digest = _digest(
        {
            "run_id": run_id,
            "request_id": request_id,
            "query_plan_item_ref": query_plan_item_ref,
            "retrieval_action_ref": retrieval_action_ref,
            "provider_plan_route_ref": provider_route_ref,
            "provider_call_ordinal": provider_call_ordinal,
            "result_rank": result_rank,
            "normalized_url": normalized_url,
        }
    )
    return f"source-result:{digest[:32]}"


def _required_named_ref(
    value: Any,
    *,
    label: str,
    output_id_key: str,
    id_keys: Sequence[str],
    output_digest_key: str,
    digest_keys: Sequence[str],
    extra_digest_keys: Sequence[str] = (),
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DiscoverySourceResultError(f"{label} is required")
    output = {
        output_id_key: _required_token(_first_value(value, *id_keys), output_id_key, limit=260),
        output_digest_key: _digest_token(_first_value(value, *digest_keys), output_digest_key),
    }
    for key in extra_digest_keys:
        if value.get(key):
            output[key] = _digest_token(value.get(key), key)
    output.update(_reference_metadata(value))
    return output


def _optional_named_ref(
    value: Any,
    *,
    output_id_key: str,
    id_keys: Sequence[str],
    output_digest_key: str,
    digest_keys: Sequence[str],
) -> dict[str, Any]:
    if value in (None, {}, ""):
        return {}
    return _required_named_ref(
        value,
        label=output_id_key.removesuffix("_id") + "_ref",
        output_id_key=output_id_key,
        id_keys=id_keys,
        output_digest_key=output_digest_key,
        digest_keys=digest_keys,
    )


def _optional_component_ref(value: Any) -> dict[str, Any]:
    if value in (None, {}, ""):
        return {}
    if not isinstance(value, Mapping):
        raise DiscoverySourceResultError("component_ref must be a mapping")
    component_id = _required_token(value.get("component_id"), "component_id", limit=260)
    output: dict[str, Any] = {"component_id": component_id}
    if value.get("component_digest"):
        output["component_digest"] = _digest_token(value.get("component_digest"), "component_digest")
    output.update(_reference_metadata(value))
    return output


def _retrieval_action_ref(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DiscoverySourceResultError("retrieval_action_ref is required")
    action_id = _required_token(value.get("action_id"), "action_id", limit=260)
    action_type = _required_token(value.get("action_type"), "action_type", limit=120)
    stage = _required_token(value.get("stage"), "stage", limit=120)
    sequence = _nonnegative_int(value.get("sequence"), "sequence")
    basis = {
        "action_id": action_id,
        "action_type": action_type,
        "stage": stage,
        "sequence": sequence,
    }
    supplied_digest = value.get("action_digest") or value.get("retrieval_action_digest")
    if supplied_digest:
        supplied = _digest_token(supplied_digest, "retrieval_action_digest")
        if supplied != _digest(basis):
            raise DiscoverySourceResultError("retrieval_action_ref digest does not match its lineage")
    return {**basis, "retrieval_action_digest": _digest(basis)}


def _reference_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in sorted(_REFERENCE_METADATA_KEYS):
        if key not in value:
            continue
        item = value.get(key)
        if key == "sequence":
            metadata[key] = _nonnegative_int(item, key)
        elif item not in (None, ""):
            metadata[key] = _required_token(item, key, limit=160)
    return metadata


def _optional_generic_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    if not isinstance(value, Mapping):
        raise DiscoverySourceResultError("packet_ref must be a mapping")
    output: dict[str, Any] = {}
    for key in sorted(value):
        key_text = str(key)
        if not (
            key_text.endswith("_id")
            or key_text.endswith("_digest")
            or key_text.endswith("_revision")
            or key_text in _REFERENCE_METADATA_KEYS
        ):
            continue
        item = value.get(key)
        if item in (None, ""):
            continue
        if key_text.endswith("_digest"):
            output[key_text] = _digest_token(item, key_text)
        elif isinstance(item, (bool, int)):
            output[key_text] = item
        else:
            output[key_text] = _required_token(item, key_text, limit=260)
    return output


def _source_result_ref(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    source_result_id = value.get("source_result_id")
    source_result_digest = value.get("source_result_digest")
    if not source_result_id or not source_result_digest:
        return {}
    return {
        "source_result_id": _required_token(source_result_id, "source_result_id", limit=260),
        "source_result_digest": _digest_token(source_result_digest, "source_result_digest"),
    }


def _reference_id(value: Mapping[str, Any] | str, key: str) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get(key) or "").strip()
    return ""


def _first_value(value: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        item = value.get(key)
        if item not in (None, ""):
            return item
    return None


def _required_token(value: Any, label: str, *, limit: int) -> str:
    if value is None:
        raise DiscoverySourceResultError(f"{label} is required")
    enum_value = getattr(value, "value", value)
    text = str(enum_value).strip()
    if not text or len(text) > limit or any(ord(character) < 32 for character in text):
        raise DiscoverySourceResultError(f"{label} is invalid")
    return text


def _optional_scope_token(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _required_token(value, label, limit=260)


def _digest_token(value: Any, label: str) -> str:
    text = _required_token(value, label, limit=80).casefold()
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise DiscoverySourceResultError(f"{label} must be a SHA-256 digest")
    return text


def _positive_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise DiscoverySourceResultError(f"{label} must be a positive integer") from exc
    if isinstance(value, bool) or number < 1:
        raise DiscoverySourceResultError(f"{label} must be a positive integer")
    return number


def _nonnegative_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise DiscoverySourceResultError(f"{label} must be a non-negative integer") from exc
    if isinstance(value, bool) or number < 0:
        raise DiscoverySourceResultError(f"{label} must be a non-negative integer")
    return number


def _clean_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    return text[:limit]


def _frozen(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = [
    "DISCOVERY_RESULT_CONTRIBUTOR_REF_CAP",
    "DISCOVERY_RESULT_MATERIAL_CHAR_CAP",
    "DISCOVERY_RESULT_MATERIAL_OWNER",
    "DISCOVERY_RESULT_MATERIAL_SCHEMA_VERSION",
    "DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_BYTE_CAP",
    "DISCOVERY_RESULT_RUN_KERNEL_PROJECTION_SCHEMA_VERSION",
    "DISCOVERY_RESULT_SNIPPET_CHAR_CAP",
    "DISCOVERY_RESULT_TITLE_CHAR_CAP",
    "DISCOVERY_SOURCE_RESULT_IDENTITY_CANONICAL_BYTE_CAP",
    "DISCOVERY_SOURCE_RESULT_IDENTITY_OWNER",
    "DISCOVERY_SOURCE_RESULT_IDENTITY_RUN_CAP",
    "DISCOVERY_SOURCE_RESULT_IDENTITY_SCHEMA_VERSION",
    "DiscoveryResultMaterialRecord",
    "DiscoveryResultMaterialStore",
    "DiscoverySourceResultError",
    "DiscoverySourceResultIdentity",
    "normalize_discovery_result_url",
]
