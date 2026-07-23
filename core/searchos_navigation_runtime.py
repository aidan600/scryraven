"""Compact, inactive SearchOS bounded-navigation foundation.

Exact breadcrumb destinations are run-local data owned only by
``EphemeralNavigationLocatorStore``.  Canonical SearchOS state receives opaque
binding refs and safe digests, never a newly extracted URL.
"""

from __future__ import annotations

import ipaddress
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urljoin, urlsplit, urlunsplit

NAVIGATION_OPTION_SCHEMA_VERSION = "searchos_navigation_option_v1"
NAVIGATION_EDGE_SCHEMA_VERSION = "searchos_navigation_edge_v1"
NAVIGATION_OWNER = "RunKernel.SearchOSIterativeJudgment"
NAVIGATION_SELECTION_STAGE = "searchos_navigation_selection"
NAVIGATION_EXTRACTION_LIMIT = 48
NAVIGATION_WINDOW_LIMIT = 12
NAVIGATION_URL_LENGTH_LIMIT = 700
NAVIGATION_LABEL_LENGTH_LIMIT = 160
NAVIGATION_SOURCE_TEXT_LIMIT = 20_000
NAVIGATION_RELATIONSHIP_POSTURE = "outbound_link_from_current_read_custody"

NAVIGATION_SELECTABLE = "selectable"
NAVIGATION_PENDING_EXECUTION = "pending_execution"
NAVIGATION_BINDING_UNAVAILABLE = "binding_unavailable"
NAVIGATION_CUSTODIED = "custodied"
NAVIGATION_DESTINATION_FAILED = "destination_failed"

NAVIGATION_SELECTION_ADMITTED = "admitted_selection"
NAVIGATION_SELECTION_AUTHORITY_REJECTED = "rejected_authority_integrity"
NAVIGATION_SELECTION_UNAVAILABLE = "rejected_navigation_unavailable"

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_URL_RE = re.compile(r"(?i)(?:\bhttps?://|\bwww\.)")
_EMAIL_RE = re.compile(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_HOST_RE = re.compile(
    r"(?i)(?<![a-z0-9-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}\.?(?=$|[^a-z0-9-])"
)
_IPV4_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_BINDING_ID_RE = re.compile(r"navigation-binding:[0-9a-f]{24}:[0-9a-f]{24}")
_QUERY_RE = re.compile(r"(?:\?|\b[a-zA-Z0-9_-]{1,40}=\S*)")
_CREDENTIAL_RE = re.compile(
    r"(?i)(?:\b(?:password|passwd|token|secret|api[_-]?key|credential)s?\b|"
    r"\S+:\S+@)"
)
_NAKED_URL_RE = re.compile(r"(?i)https?://[^\s<>()]+")


class NavigationRuntimeError(ValueError):
    """Raised when bounded-navigation input or authority fails closed."""


@dataclass(frozen=True, slots=True)
class NavigationOption:
    """The sole canonical navigation option record."""

    slot_id: str
    destination_binding_ref: Mapping[str, Any]
    parent_read_custody_ref: Mapping[str, Any]
    child_depth: int
    ancestor_physical_identity_digests: tuple[str, ...]
    bounded_relationship_context: Mapping[str, Any]
    revision: int
    disposition: str
    active_selection_ref: Mapping[str, Any]
    admission_ordinal: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "destination_binding_ref",
            _validate_binding_ref(self.destination_binding_ref),
        )
        object.__setattr__(
            self,
            "parent_read_custody_ref",
            _compact_ref(self.parent_read_custody_ref, "parent_read_custody_ref"),
        )
        object.__setattr__(
            self,
            "bounded_relationship_context",
            _validate_relationship_context(
                self.bounded_relationship_context,
                child_depth=self.child_depth,
            ),
        )
        if self.disposition not in {
            NAVIGATION_SELECTABLE,
            NAVIGATION_PENDING_EXECUTION,
            NAVIGATION_BINDING_UNAVAILABLE,
            NAVIGATION_CUSTODIED,
            NAVIGATION_DESTINATION_FAILED,
        }:
            raise NavigationRuntimeError("navigation_option_disposition_invalid")
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in (self.child_depth, self.revision, self.admission_ordinal)
        ):
            raise NavigationRuntimeError("navigation_option_positive_fields_invalid")
        active = _json_mapping(self.active_selection_ref)
        if self.disposition == NAVIGATION_PENDING_EXECUTION:
            if set(active) != {"navigation_selection_id", "navigation_selection_digest"}:
                raise NavigationRuntimeError("navigation_active_selection_ref_invalid")
            selection_digest = _digest_token(
                active.get("navigation_selection_digest"), "navigation_selection_digest"
            )
            if active.get("navigation_selection_id") != (
                f"searchos-navigation-selection:{selection_digest[:24]}"
            ):
                raise NavigationRuntimeError("navigation_active_selection_ref_invalid")
        elif active:
            raise NavigationRuntimeError("navigation_active_selection_ref_invalid")
        object.__setattr__(self, "active_selection_ref", active)
        _token(self.slot_id, "slot_id")
        for digest in self.ancestor_physical_identity_digests:
            _digest_token(digest, "ancestor_physical_identity_digest")
        if self.destination_binding_ref["physical_identity_digest"] in self.ancestor_physical_identity_digests:
            raise NavigationRuntimeError("navigation_option_ancestor_cycle")

    def to_dict(self) -> dict[str, Any]:
        identity_core = {
            "schema_version": NAVIGATION_OPTION_SCHEMA_VERSION,
            "owner": NAVIGATION_OWNER,
            "slot_id": self.slot_id,
            "destination_binding_ref": deepcopy(dict(self.destination_binding_ref)),
            "parent_read_custody_ref": deepcopy(dict(self.parent_read_custody_ref)),
            "child_depth": self.child_depth,
            "ancestor_physical_identity_digests": list(self.ancestor_physical_identity_digests),
            "bounded_relationship_context": deepcopy(dict(self.bounded_relationship_context)),
            "admission_ordinal": self.admission_ordinal,
        }
        identity_digest = _digest(identity_core)
        core = {
            **identity_core,
            "revision": self.revision,
            "disposition": self.disposition,
            "active_selection_ref": deepcopy(dict(self.active_selection_ref)),
        }
        digest = _digest(core)
        return {
            **core,
            "navigation_option_id": (f"searchos-navigation-option:{identity_digest[:24]}"),
            "navigation_option_digest": digest,
        }

    def ref(self) -> dict[str, Any]:
        value = self.to_dict()
        return {
            "navigation_option_id": value["navigation_option_id"],
            "navigation_option_digest": value["navigation_option_digest"],
            "revision": self.revision,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NavigationOption":
        safe = _mapping(value)
        if safe.get("schema_version") != NAVIGATION_OPTION_SCHEMA_VERSION:
            raise NavigationRuntimeError("navigation_option_schema_invalid")
        option = cls(
            slot_id=_token(safe.get("slot_id"), "slot_id"),
            destination_binding_ref=_mapping(safe.get("destination_binding_ref")),
            parent_read_custody_ref=_mapping(safe.get("parent_read_custody_ref")),
            child_depth=int(safe.get("child_depth") or 0),
            ancestor_physical_identity_digests=tuple(
                str(item) for item in safe.get("ancestor_physical_identity_digests") or ()
            ),
            bounded_relationship_context=_mapping(safe.get("bounded_relationship_context")),
            revision=int(safe.get("revision") or 0),
            disposition=str(safe.get("disposition") or ""),
            active_selection_ref=_mapping(safe.get("active_selection_ref")),
            admission_ordinal=int(safe.get("admission_ordinal") or 0),
        )
        expected = option.to_dict()
        if safe != expected:
            raise NavigationRuntimeError("navigation_option_identity_invalid")
        return option


class EphemeralNavigationLocatorStore:
    """One run-local, deliberately nonserializable exact-destination owner."""

    __slots__ = ("run_id", "request_id", "_staged", "_committed", "_closed")

    def __init__(self, *, run_id: str, request_id: str) -> None:
        self.run_id = _token(run_id, "run_id")
        self.request_id = _token(request_id, "request_id")
        self._staged: dict[str, dict[str, Any]] = {}
        self._committed: dict[str, dict[str, Any]] = {}
        self._closed = False

    def __getstate__(self) -> None:
        raise TypeError("EphemeralNavigationLocatorStore is nonserializable")

    def __reduce_ex__(self, protocol: int) -> None:
        del protocol
        raise TypeError("EphemeralNavigationLocatorStore is nonserializable")

    @property
    def staged_count(self) -> int:
        return len(self._staged)

    @property
    def committed_count(self) -> int:
        return len(self._committed)

    def stage(self, normalized_destination: Mapping[str, Any]) -> dict[str, Any]:
        self._require_open()
        normalized = _validate_normalized_destination(normalized_destination)
        if normalized["query_present"]:
            raise NavigationRuntimeError("navigation_query_not_supported")
        binding = _binding_ref(
            normalized,
            binding_id=(
                f"navigation-binding:{_digest({'run_id': self.run_id, 'request_id': self.request_id})[:24]}:"
                f"{normalized['full_destination_digest'][:24]}"
            ),
        )
        binding_id = binding["destination_binding_id"]
        existing = self._committed.get(binding_id) or self._staged.get(binding_id)
        entry = {"binding_ref": binding, "exact_url": normalized["exact_url"]}
        if existing is not None and existing != entry:
            raise NavigationRuntimeError("navigation_binding_identity_collision")
        if existing is None:
            self._staged[binding_id] = entry
        return deepcopy(binding)

    def commit(self, binding_ref: Mapping[str, Any]) -> None:
        self._require_open()
        binding = _validate_binding_ref(binding_ref)
        binding_id = binding["destination_binding_id"]
        staged = self._staged.pop(binding_id, None)
        if staged is None:
            existing = self._committed.get(binding_id)
            if existing is None or existing["binding_ref"] != binding:
                raise NavigationRuntimeError("navigation_binding_not_staged")
            return
        if staged["binding_ref"] != binding:
            raise NavigationRuntimeError("navigation_binding_stage_mismatch")
        self._committed[binding_id] = staged

    def discard_staged(self, binding_refs: Sequence[Mapping[str, Any]] | None = None) -> None:
        self._require_open()
        if binding_refs is None:
            self._staged.clear()
            return
        for raw in binding_refs:
            binding = _validate_binding_ref(raw)
            self._staged.pop(binding["destination_binding_id"], None)

    def resolve(self, binding_ref: Mapping[str, Any]) -> str | None:
        self._require_open()
        try:
            binding = _validate_binding_ref(binding_ref)
        except NavigationRuntimeError:
            return None
        entry = self._committed.get(binding["destination_binding_id"])
        if entry is None or entry["binding_ref"] != binding:
            return None
        try:
            normalized = normalize_navigation_destination(entry["exact_url"])
        except NavigationRuntimeError:
            return None
        if _binding_ref(normalized, binding_id=binding["destination_binding_id"]) != binding:
            return None
        return str(normalized["exact_url"])

    def consume_once_for_execution(self, binding_ref: Mapping[str, Any]) -> str:
        """Return one exact committed destination and retire it atomically."""

        self._require_open()
        binding = _validate_binding_ref(binding_ref)
        binding_id = binding["destination_binding_id"]
        entry = self._committed.pop(binding_id, None)
        if entry is None or entry["binding_ref"] != binding:
            raise NavigationRuntimeError("navigation_destination_binding_unavailable")
        normalized = normalize_navigation_destination(entry["exact_url"])
        if _binding_ref(normalized, binding_id=binding_id) != binding:
            raise NavigationRuntimeError("navigation_destination_binding_mismatch")
        return str(normalized["exact_url"])

    def discard_all(self) -> None:
        self._staged.clear()
        self._committed.clear()
        self._closed = True

    def _require_open(self) -> None:
        if self._closed:
            raise NavigationRuntimeError("navigation_locator_store_closed")


def normalize_navigation_destination(value: str) -> dict[str, Any]:
    """Normalize one absolute HTTP(S) destination without network access."""

    raw = _token(value, "navigation_destination", maximum=NAVIGATION_URL_LENGTH_LIMIT)
    if any(ord(character) < 0x20 or character.isspace() for character in raw):
        raise NavigationRuntimeError("navigation_destination_malformed")
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise NavigationRuntimeError("navigation_destination_malformed") from exc
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"}:
        raise NavigationRuntimeError("navigation_destination_scheme_unsupported")
    if parsed.username is not None or parsed.password is not None:
        raise NavigationRuntimeError("navigation_destination_userinfo_forbidden")
    explicit_port = _explicit_port(parsed.netloc)
    hostname = str(parsed.hostname or "").casefold()
    if not hostname or not _is_ascii(hostname) or "%" in hostname:
        raise NavigationRuntimeError("navigation_destination_hostname_invalid")
    is_ipv6 = ":" in hostname
    if is_ipv6:
        host_port = parsed.netloc.rsplit("@", 1)[-1]
        if not host_port.startswith("[") or "]" not in host_port:
            raise NavigationRuntimeError("navigation_destination_hostname_invalid")
        try:
            hostname = ipaddress.IPv6Address(hostname).compressed
        except ValueError as exc:
            raise NavigationRuntimeError("navigation_destination_hostname_invalid") from exc
    elif not _valid_ascii_hostname(hostname):
        raise NavigationRuntimeError("navigation_destination_hostname_invalid")
    if explicit_port and port is None:
        raise NavigationRuntimeError("navigation_destination_port_invalid")
    if port is not None and not 1 <= port <= 65535:
        raise NavigationRuntimeError("navigation_destination_port_invalid")
    path = parsed.path or "/"
    netloc = f"[{hostname}]" if is_ipv6 else hostname
    if explicit_port:
        netloc = f"{netloc}:{port}"
    exact = urlunsplit((scheme, netloc, path, parsed.query, ""))
    if len(exact) > NAVIGATION_URL_LENGTH_LIMIT:
        raise NavigationRuntimeError("navigation_destination_too_long")
    port_posture = _port_posture(scheme=scheme, port=port, explicit=explicit_port)
    identity_core = {
        "scheme": scheme,
        "hostname": hostname,
        "port_posture": port_posture,
        "path": path,
        "query": parsed.query,
    }
    return {
        "exact_url": exact,
        "scheme": scheme,
        "hostname": hostname,
        "port": port,
        "port_explicit": explicit_port,
        "port_posture": port_posture,
        "path": path,
        "query_present": bool(parsed.query),
        "full_destination_digest": _digest_text(exact),
        "semantic_identity_digest": _digest(identity_core),
        "physical_identity_digest": _digest({**identity_core, "trailing_slash_preserved": True}),
    }


def navigation_destination_eligibility(parent: Mapping[str, Any], destination: Mapping[str, Any]) -> tuple[bool, str]:
    """Apply the first-build origin and port policy after normalization."""

    source = _validate_normalized_destination(parent)
    child = _validate_normalized_destination(destination)
    if child["query_present"]:
        return False, "navigation_query_not_supported"
    if source["hostname"] != child["hostname"]:
        return False, "navigation_hostname_changed"
    if _nondefault_port(source) or _nondefault_port(child):
        return False, "navigation_nondefault_port_ineligible"
    if source["scheme"] == "https" and child["scheme"] == "http":
        return False, "navigation_https_downgrade_ineligible"
    if source["scheme"] == child["scheme"]:
        if source["port_explicit"] != child["port_explicit"]:
            return False, "navigation_default_port_explicitness_changed"
        return True, "navigation_destination_eligible"
    if (
        source["scheme"] == "http"
        and child["scheme"] == "https"
        and source["port_explicit"] is False
        and child["port_explicit"] is False
    ):
        return True, "navigation_http_to_https_upgrade_eligible"
    return False, "navigation_scheme_transition_ineligible"


def scrub_navigation_relationship_label(value: str) -> str:
    """Return bounded safe relationship text or the fixed privacy fallback."""

    raw = str(value or "")
    had_control = bool(_CONTROL_RE.search(raw))
    compact = " ".join(_CONTROL_RE.sub(" ", raw).split())
    unsafe = (
        had_control
        or bool(_URL_RE.search(compact))
        or bool(_EMAIL_RE.search(compact))
        or bool(_HOST_RE.search(compact))
        or bool(_IPV4_RE.search(compact))
        or _ipv6_literal_like(compact)
        or bool(_QUERY_RE.search(compact))
        or bool(_CREDENTIAL_RE.search(compact))
        or _path_like(compact)
    )
    if unsafe or not compact:
        return "linked page"
    return compact[:NAVIGATION_LABEL_LENGTH_LIMIT]


def extract_bounded_navigation_links(
    *, markdown_text: str, parent_url: str, limit: int = NAVIGATION_EXTRACTION_LIMIT
) -> dict[str, Any]:
    """Extract a deterministic supported-link prefix as transient plain data."""

    if not isinstance(markdown_text, str) or len(markdown_text) > NAVIGATION_SOURCE_TEXT_LIMIT:
        raise NavigationRuntimeError("navigation_source_text_invalid")
    bound = int(limit)
    if bound <= 0 or bound > NAVIGATION_EXTRACTION_LIMIT:
        raise NavigationRuntimeError("navigation_extraction_limit_invalid")
    parent = normalize_navigation_destination(parent_url)
    occurrences: list[dict[str, Any]] = []
    rejections: dict[str, int] = {}
    seen_physical: set[str] = set()
    overflow = 0
    for ordinal, label, raw_destination in _iter_supported_markdown_links(markdown_text):
        try:
            resolved = urljoin(parent["exact_url"], raw_destination)
            destination = normalize_navigation_destination(resolved)
        except NavigationRuntimeError:
            _increment(rejections, "navigation_destination_malformed")
            continue
        if destination["query_present"]:
            _increment(rejections, "navigation_query_not_supported")
            continue
        if destination["physical_identity_digest"] == parent["physical_identity_digest"]:
            _increment(rejections, "navigation_self_link")
            continue
        eligible, reason = navigation_destination_eligibility(parent, destination)
        if not eligible:
            _increment(rejections, reason)
            continue
        physical = str(destination["physical_identity_digest"])
        if physical in seen_physical:
            _increment(rejections, "navigation_duplicate_destination")
            continue
        seen_physical.add(physical)
        if len(occurrences) >= bound:
            overflow += 1
            continue
        occurrences.append(
            {
                "source_link_ordinal": ordinal,
                "relationship_label": scrub_navigation_relationship_label(label),
                "normalized_destination": destination,
            }
        )
    return {
        "occurrences": occurrences,
        "rejection_counts": rejections,
        "overflow_count": overflow,
    }


def sanitize_navigation_source_text(markdown_text: str) -> str:
    """Remove supported Markdown destinations and remaining naked HTTP(S) text."""

    if not isinstance(markdown_text, str) or len(markdown_text) > NAVIGATION_SOURCE_TEXT_LIMIT:
        raise NavigationRuntimeError("navigation_source_text_invalid")
    output: list[str] = []
    cursor = 0
    index = 0
    while index < len(markdown_text):
        character = markdown_text[index]
        if character == "<":
            close = markdown_text.find(">", index + 1, min(len(markdown_text), index + 704))
            if close != -1 and markdown_text[index + 1 : close].casefold().startswith(("http://", "https://")):
                output.extend((markdown_text[cursor:index], "linked page"))
                cursor = close + 1
                index = cursor
                continue
        image = character == "!" and index + 1 < len(markdown_text) and markdown_text[index + 1] == "["
        label_start = index + 1 if image else index
        if markdown_text[label_start : label_start + 1] == "[":
            label_close = _scan_balanced(markdown_text, label_start, "[", "]", 512)
            if label_close is not None and markdown_text[label_close + 1 : label_close + 2] == "(":
                destination_close = _scan_balanced(markdown_text, label_close + 1, "(", ")", 900)
                if destination_close is not None:
                    label = scrub_navigation_relationship_label(markdown_text[label_start + 1 : label_close])
                    output.extend((markdown_text[cursor:index], "image" if image else label))
                    cursor = destination_close + 1
                    index = cursor
                    continue
        index += 1
    output.append(markdown_text[cursor:])
    return _NAKED_URL_RE.sub("linked page", "".join(output))


def admit_navigation_options_from_markdown(
    state: Mapping[str, Any],
    *,
    slot_id: str,
    parent_read_custody_ref: Mapping[str, Any],
    parent_url: str,
    parent_depth: int,
    ancestor_physical_identity_digests: Sequence[str],
    markdown_text: str,
    locator_store: EphemeralNavigationLocatorStore,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Admit URL-free options beneath existing SearchOS ownership."""

    from core.searchos_iterative_judgment_runtime import validate_searchos_state

    canonical = validate_searchos_state(state)
    if canonical.get("run_id") != locator_store.run_id or canonical.get("request_id") != locator_store.request_id:
        raise NavigationRuntimeError("navigation_locator_scope_mismatch")
    policy = _mapping(canonical.get("policy_snapshot"))
    navigation = _mapping(canonical.get("navigation"))
    if policy.get("navigation_runtime_open") is not True or not navigation:
        raise NavigationRuntimeError("navigation_runtime_closed")
    token = _token(slot_id, "slot_id")
    slot = _mapping(_mapping(canonical.get("slots_by_id")).get(token))
    if not slot:
        raise NavigationRuntimeError("navigation_slot_not_current")
    parent = _mapping(parent_read_custody_ref)
    if parent not in [_mapping(item) for item in slot.get("custody_refs") or ()]:
        raise NavigationRuntimeError("navigation_parent_custody_not_current")
    parent_normalized = normalize_navigation_destination(parent_url)
    custody_parent_url = parent.get("normalized_url")
    if (
        not custody_parent_url
        or normalize_navigation_destination(str(custody_parent_url))["exact_url"] != parent_normalized["exact_url"]
    ):
        raise NavigationRuntimeError("navigation_parent_source_identity_mismatch")
    depth = int(parent_depth)
    child_depth = depth + 1
    if depth < 0 or child_depth > int(policy.get("navigation_max_depth") or 0):
        return canonical, {
            "admitted_option_count": 0,
            "rejection_counts": {"navigation_depth_ineligible": 1},
            "overflow_count": 0,
        }
    extracted = extract_bounded_navigation_links(
        markdown_text=markdown_text,
        parent_url=parent_url,
    )
    ancestors = list(ancestor_physical_identity_digests)
    for digest in ancestors:
        _digest_token(digest, "ancestor_physical_identity_digest")
    if parent_normalized["physical_identity_digest"] not in ancestors:
        ancestors.append(str(parent_normalized["physical_identity_digest"]))
    blocked_physical = set(ancestors)
    options = _mapping(navigation.get("options_by_id"))
    existing_physical = {
        _mapping(_mapping(item).get("destination_binding_ref")).get("physical_identity_digest")
        for item in options.values()
        if _mapping(item).get("slot_id") == token
    }
    staged: list[dict[str, Any]] = []
    admitted: list[NavigationOption] = []
    try:
        for occurrence in extracted["occurrences"]:
            normalized = _mapping(occurrence["normalized_destination"])
            if normalized["physical_identity_digest"] in blocked_physical:
                _increment(extracted["rejection_counts"], "navigation_ancestor_cycle")
                continue
            if normalized["physical_identity_digest"] in existing_physical:
                _increment(
                    extracted["rejection_counts"],
                    "navigation_duplicate_destination",
                )
                continue
            binding = locator_store.stage(normalized)
            staged.append(binding)
            context = {
                "parent_depth": depth,
                "child_depth": child_depth,
                "source_link_ordinal": int(occurrence["source_link_ordinal"]),
                "relationship_label": occurrence["relationship_label"],
            }
            admitted.append(
                NavigationOption(
                    slot_id=token,
                    destination_binding_ref=binding,
                    parent_read_custody_ref=parent,
                    child_depth=child_depth,
                    ancestor_physical_identity_digests=tuple(ancestors),
                    bounded_relationship_context=context,
                    revision=1,
                    disposition=NAVIGATION_SELECTABLE,
                    active_selection_ref={},
                    admission_ordinal=len(options) + len(admitted) + 1,
                )
            )
        for option in admitted:
            value = option.to_dict()
            options[value["navigation_option_id"]] = value
        navigation["options_by_id"] = options
        canonical["navigation"] = navigation
        refreshed = _refresh_searchos_state(canonical)
        for binding in staged:
            locator_store.commit(binding)
    except Exception:
        locator_store.discard_staged(staged)
        raise
    return refreshed, {
        "admitted_option_count": len(admitted),
        "rejection_counts": deepcopy(extracted["rejection_counts"]),
        "overflow_count": int(extracted["overflow_count"]),
    }


def navigation_option_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    return NavigationOption.from_dict(value).ref()


def navigation_candidate_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    option = NavigationOption.from_dict(value)
    core = {"navigation_option_ref": option.ref()}
    digest = _digest(core)
    return {
        "navigation_candidate_id": f"searchos-navigation-candidate:{digest[:24]}",
        "navigation_candidate_digest": digest,
        "navigation_option_ref": option.ref(),
    }


def validate_navigation_destination_binding_ref(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one URL-free locator binding owned by this module."""

    return _validate_binding_ref(value)


def validate_navigation_destination_for_binding(
    exact_url: str,
    binding_ref: Mapping[str, Any],
) -> str:
    """Validate one transient exact destination against its opaque binding."""

    binding = _validate_binding_ref(binding_ref)
    normalized = normalize_navigation_destination(exact_url)
    reproduced = _binding_ref(
        normalized,
        binding_id=binding["destination_binding_id"],
    )
    if reproduced != binding:
        raise NavigationRuntimeError("navigation_destination_binding_mismatch")
    return str(normalized["exact_url"])


def build_searchos_navigation_acquisition_need_proposal(
    *,
    run_kernel: Any,
    slot_ref: Mapping[str, Any],
    navigation_option_ref: Mapping[str, Any],
    navigation_selection_ref: Mapping[str, Any],
    destination_binding_ref: Mapping[str, Any],
    parent_read_custody_ref: Mapping[str, Any],
) -> Any:
    """Build the URL-free V1 READ proposal for one exact pending selection."""

    from core.acquisition_control import (
        SEARCHOS_NAVIGATION_ORIGIN,
        AcquisitionNeedProposalV1,
    )

    context = _navigation_execution_context(
        run_kernel.state.searchos_state,
        slot_ref=slot_ref,
        navigation_option_ref=navigation_option_ref,
        navigation_selection_ref=navigation_selection_ref,
        destination_binding_ref=destination_binding_ref,
        parent_read_custody_ref=parent_read_custody_ref,
    )
    snapshot = run_kernel.acquisition_authority_snapshot()
    slot = context["slot"]
    component = _mapping(slot.get("component_ref"))
    obligation = _mapping(slot.get("source_obligation_ref"))
    component_id = _token(component.get("component_id"), "component_id")
    obligation_id = _token(
        obligation.get("source_obligation_id"),
        "source_obligation_id",
    )
    searchos_contract = _mapping(context["state"].get("answer_contract_ref"))
    acquisition_contract = _mapping(snapshot.get("answer_contract_ref"))
    if (
        acquisition_contract.get("contract_digest")
        not in {
            searchos_contract.get("contract_digest"),
            searchos_contract.get("answer_contract_digest"),
        }
        or _mapping(_mapping(snapshot.get("components_by_id")).get(component_id))
        != component
        or _mapping(
            _mapping(snapshot.get("source_obligations_by_id")).get(obligation_id)
        )
        != obligation
    ):
        raise NavigationRuntimeError("navigation_acquisition_lineage_stale")
    return AcquisitionNeedProposalV1.create(
        run_id=context["state"]["run_id"],
        request_id=context["state"]["request_id"],
        producer_surface="core.searchos_navigation_runtime",
        answer_contract_ref=acquisition_contract,
        source_obligation_ref=obligation,
        component_ref=component,
        requested_material_shape="explicit_known_url",
        origin=SEARCHOS_NAVIGATION_ORIGIN,
        destination_binding_ref=context["option"].destination_binding_ref,
        proposal_reason_code="selected_navigation_destination_read",
        advisory_proposed_capability="READ",
    )


def _navigation_execution_context(
    state: Mapping[str, Any],
    *,
    slot_ref: Mapping[str, Any],
    navigation_option_ref: Mapping[str, Any],
    navigation_selection_ref: Mapping[str, Any],
    destination_binding_ref: Mapping[str, Any],
    parent_read_custody_ref: Mapping[str, Any],
) -> dict[str, Any]:
    from core.searchos_iterative_judgment_runtime import (
        SearchOSSlotPosture,
        validate_searchos_state,
    )

    canonical = validate_searchos_state(state)
    slot_lineage = _json_mapping(slot_ref)
    slot_id = _token(slot_lineage.get("slot_id"), "slot_id")
    slot = _mapping(_mapping(canonical.get("slots_by_id")).get(slot_id))
    option_lineage = _json_mapping(navigation_option_ref)
    option_id = _token(
        option_lineage.get("navigation_option_id"),
        "navigation_option_id",
    )
    option = NavigationOption.from_dict(
        _mapping(
            _mapping(_mapping(canonical.get("navigation")).get("options_by_id")).get(
                option_id
            )
        )
    )
    selection = _json_mapping(navigation_selection_ref)
    binding = _validate_binding_ref(destination_binding_ref)
    parent = _compact_ref(parent_read_custody_ref, "parent_read_custody_ref")
    if (
        not slot
        or _mapping(slot.get("slot_ref")) != slot_lineage
        or slot.get("posture")
        != SearchOSSlotPosture.AWAITING_NAVIGATION_EXECUTION.value
        or option.ref() != option_lineage
        or option.disposition != NAVIGATION_PENDING_EXECUTION
        or option.active_selection_ref != selection
        or option.destination_binding_ref != binding
        or option.parent_read_custody_ref != parent
        or option.slot_id != slot_id
    ):
        raise NavigationRuntimeError("navigation_execution_lineage_not_current")
    parent_refs = {
        tuple(sorted(_compact_ref(item, "parent_read_custody_ref").items()))
        for item in slot.get("custody_refs") or ()
    }
    if tuple(sorted(parent.items())) not in parent_refs:
        raise NavigationRuntimeError("navigation_parent_custody_not_current")
    edge_matches = [
        edge
        for edge in _mapping(canonical.get("navigation")).get("edges") or ()
        if _mapping(_mapping(edge).get("navigation_selection_ref")) == selection
        and _mapping(_mapping(edge).get("navigation_option_ref")).get(
            "navigation_option_id"
        )
        == option_lineage.get("navigation_option_id")
        and int(
            _mapping(_mapping(edge).get("navigation_option_ref")).get("revision")
            or 0
        )
        == option.revision - 1
        and _mapping(_mapping(edge).get("destination_binding_ref")) == binding
        and _mapping(_mapping(edge).get("parent_read_custody_ref")) == parent
    ]
    if len(edge_matches) != 1:
        raise NavigationRuntimeError("navigation_selected_edge_not_current")
    return {
        "state": canonical,
        "slot": slot,
        "option": option,
        "lineage": {
            "slot_ref": slot_lineage,
            "navigation_option_ref": option_lineage,
            "navigation_selection_ref": selection,
            "destination_binding_ref": binding,
            "parent_read_custody_ref": parent,
        },
    }


def build_navigation_failure_action_inputs(
    state: Mapping[str, Any],
    *,
    navigation_lineage: Mapping[str, Any],
    failure_reason: str,
    terminal_receipt_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    lineage = _json_mapping(navigation_lineage)
    context = _navigation_execution_context(state, **lineage)
    result = {
        **context["lineage"],
        "failure_reason": _reason_code(failure_reason),
        "terminal_receipt_ref": _compact_optional_ref(terminal_receipt_ref),
    }
    _ensure_url_free(result, "navigation_failure")
    return result


def record_navigation_destination_failure(
    state: Mapping[str, Any], *, failure_record: Mapping[str, Any]
) -> dict[str, Any]:
    record = _json_mapping(failure_record)
    lineage = {
        key: _mapping(record.get(key))
        for key in (
            "slot_ref",
            "navigation_option_ref",
            "navigation_selection_ref",
            "destination_binding_ref",
            "parent_read_custody_ref",
        )
    }
    context = _navigation_execution_context(state, **lineage)
    _reason_code(record.get("failure_reason"))
    return _finish_navigation_execution(
        context,
        disposition=NAVIGATION_DESTINATION_FAILED,
        reason=str(record["failure_reason"]),
        material_ref=None,
    )


def _validate_navigation_custody_lineage_after_admission(
    state: Mapping[str, Any], custody_material_ref: Mapping[str, Any]
) -> dict[str, Any]:
    custody = _json_mapping(custody_material_ref)
    claimed = _digest_token(custody.get("read_custody_material_digest"), "read_custody_material_digest")
    core = {
        key: deepcopy(value) for key, value in custody.items()
        if key not in {"read_custody_material_id", "read_custody_material_digest", "replay_identity"}
    }
    canonical = _mapping(state)
    slot_ref = _mapping(custody.get("slot_ref"))
    slot = _mapping(_mapping(canonical.get("slots_by_id")).get(slot_ref.get("slot_id")))
    if (
        custody.get("origin") != "searchos_navigation"
        or _digest(core) != claimed
        or custody.get("read_custody_material_id") != f"searchos-read-custody:{claimed[:24]}"
        or _mapping(slot.get("slot_ref")) != slot_ref
        or custody not in [_mapping(item) for item in slot.get("custody_refs") or ()]
    ):
        raise NavigationRuntimeError("navigation_custody_lineage_not_current")
    option_ref = _mapping(custody.get("navigation_option_ref"))
    selection_ref = _mapping(custody.get("navigation_selection_ref"))
    option = NavigationOption.from_dict(
        _mapping(_mapping(_mapping(canonical.get("navigation")).get("options_by_id")).get(
            option_ref.get("navigation_option_id")))
    )
    if (
        option.disposition != NAVIGATION_CUSTODIED
        or option.revision != int(option_ref.get("revision") or 0) + 1
        or option.destination_binding_ref != _mapping(custody.get("destination_binding_ref"))
        or option.parent_read_custody_ref != _mapping(custody.get("parent_read_custody_ref"))
    ):
        raise NavigationRuntimeError("navigation_custody_option_not_current")
    option_value = option.to_dict()
    option_core = {key: deepcopy(value) for key, value in option_value.items()
                   if key not in {"navigation_option_id", "navigation_option_digest"}}
    pending_core = {**option_core, "revision": option.revision - 1,
                    "disposition": NAVIGATION_PENDING_EXECUTION,
                    "active_selection_ref": selection_ref}
    selected_core = {**option_core, "revision": option.revision - 2,
                     "disposition": NAVIGATION_SELECTABLE, "active_selection_ref": {}}
    pending_ref = {"navigation_option_id": option_value["navigation_option_id"],
                   "navigation_option_digest": _digest(pending_core), "revision": option.revision - 1}
    selected_ref = {"navigation_option_id": option_value["navigation_option_id"],
                    "navigation_option_digest": _digest(selected_core), "revision": option.revision - 2}
    edges = [
        _mapping(item)
        for item in _mapping(canonical.get("navigation")).get("edges") or ()
        if _mapping(item.get("navigation_selection_ref")) == selection_ref
        and _mapping(item.get("navigation_option_ref")) == selected_ref
        and _mapping(item.get("destination_binding_ref")) == option.destination_binding_ref
        and _mapping(item.get("parent_read_custody_ref")) == option.parent_read_custody_ref
    ]
    if pending_ref != option_ref or len(edges) != 1:
        raise NavigationRuntimeError("navigation_custody_selection_not_current")
    return {"slot": slot, "option": option}


def _navigation_custody_packet_reference(
    custody_material_ref: Mapping[str, Any], packet_value: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    from core.fetch_read_content_reference import (
        fetch_read_content_packet_ref_from_packet,
        validate_fetch_read_content_packet,
    )

    custody = _mapping(custody_material_ref)
    packet = validate_fetch_read_content_packet(packet_value)
    packet_ref = fetch_read_content_packet_ref_from_packet(packet)
    if _compact_ref(packet_ref, "fetch_read_content_packet_ref") != _mapping(
        custody.get("fetch_read_content_packet_ref")
    ):
        raise NavigationRuntimeError("navigation_custody_packet_stale")
    ledger_ref = _mapping(custody.get("evidence_ledger_custody_ref"))
    references = [_mapping(item) for item in packet.get("reference_records") or ()
                  if _mapping(item).get("reference_id") == ledger_ref.get("reference_id")
                  and _mapping(item).get("reference_digest") == ledger_ref.get("reference_digest")]
    if len(references) != 1:
        raise NavigationRuntimeError("navigation_custody_packet_binding_ambiguous")
    validate_navigation_destination_for_binding(str(references[0].get("attempted_url") or ""),
                                                _mapping(custody.get("destination_binding_ref")))
    return packet_ref, references[0]


def _build_navigation_custody_judgment_material(
    state: Mapping[str, Any], custody_material_ref: Mapping[str, Any], packet_value: Mapping[str, Any]
) -> dict[str, Any]:
    custody = _mapping(custody_material_ref)
    _validate_navigation_custody_lineage_after_admission(state, custody)
    packet_ref, reference = _navigation_custody_packet_reference(custody, packet_value)
    bounded_text = str(reference.get("bounded_text") or "")
    bounded_count = int(reference.get("bounded_character_count") or 0)
    if (
        not bounded_text
        or bounded_count != len(bounded_text)
        or reference.get("excerpt_digest") != _digest({"bounded_text": bounded_text})
    ):
        raise NavigationRuntimeError("navigation_custody_bounded_text_invalid")
    lineage = {key: deepcopy(custody[key]) for key in (
        "slot_ref", "navigation_option_ref", "navigation_selection_ref",
        "destination_binding_ref", "parent_read_custody_ref",
        "evidence_ledger_custody_ref", "terminal_receipt_ref", "custody_authorization_ref")}
    return {
        "schema_version": "searchos_read_custody_judgment_material_v1",
        "origin": "searchos_navigation",
        **lineage,
        "read_custody_ref": deepcopy(custody),
        "fetch_read_content_packet_ref": packet_ref,
        "title": " ".join(str(reference.get("content_title") or "").split())[:300] or None,
        "bounded_text": bounded_text,
        "bounded_text_digest": reference["excerpt_digest"],
        "bounded_character_count": bounded_count,
        "readability_posture": "readable",
        "completeness_posture": "unknown",
        "truncation_posture": "unknown",
        "same_normalized_url_reused": False,
    }


def build_navigation_read_custody_material_ref(
    state: Mapping[str, Any],
    *,
    navigation_lineage: Mapping[str, Any],
    fetch_read_content_packet_ref: Mapping[str, Any],
    evidence_ledger_custody_ref: Mapping[str, Any],
    confirmed_evidence_ledger_candidate_id: str,
    terminal_receipt_ref: Mapping[str, Any],
    custody_authorization_ref: Mapping[str, Any],
) -> dict[str, Any]:
    lineage = _json_mapping(navigation_lineage)
    context = _navigation_execution_context(state, **lineage)
    lineage = context["lineage"]
    candidate_id = str(confirmed_evidence_ledger_candidate_id or "").strip()
    if not re.fullmatch(r"searchos_custody_candidate:[0-9a-f]{64}", candidate_id):
        raise NavigationRuntimeError(
            "navigation_custody_candidate_id_not_canonical"
        )
    core = {
        "schema_version": "searchos_read_custody_material_ref_v1",
        "owner": NAVIGATION_OWNER,
        "origin": "searchos_navigation",
        **lineage,
        "fetch_read_content_packet_ref": _compact_ref(
            fetch_read_content_packet_ref, "fetch_read_content_packet_ref"
        ),
        "evidence_ledger_custody_ref": _compact_ref(
            evidence_ledger_custody_ref, "evidence_ledger_custody_ref"
        ),
        "evidence_ledger_candidate_id": candidate_id,
        "terminal_receipt_ref": _compact_ref(terminal_receipt_ref, "terminal_receipt_ref"),
        "custody_authorization_ref": _compact_ref(
            custody_authorization_ref, "custody_authorization_ref"
        ),
        "material_authority": "read_custody_material",
        "readable": True,
        "bounded_retention": True,
        "stale": False,
        "component_analyst_proposal_eligible": True,
        "support_admitted": False,
        "source_obligation_satisfied": False,
        "citation_eligible": False,
    }
    digest = _digest(core)
    return {
        **core,
        "read_custody_material_id": f"searchos-read-custody:{digest[:24]}",
        "read_custody_material_digest": digest,
        "replay_identity": f"searchos-read-custody:{digest}",
    }


def record_navigation_read_custody_material(
    state: Mapping[str, Any], *, custody_material_ref: Mapping[str, Any]
) -> dict[str, Any]:
    custody = _json_mapping(custody_material_ref)
    claimed = _digest_token(
        custody.get("read_custody_material_digest"),
        "read_custody_material_digest",
    )
    core = {
        key: deepcopy(value)
        for key, value in custody.items()
        if key
        not in {
            "read_custody_material_id",
            "read_custody_material_digest",
            "replay_identity",
        }
    }
    if (
        custody.get("origin") != "searchos_navigation"
        or _digest(core) != claimed
        or custody.get("read_custody_material_id")
        != f"searchos-read-custody:{claimed[:24]}"
        or custody.get("readable") is not True
    ):
        raise NavigationRuntimeError("navigation_custody_material_invalid")
    lineage = {
        key: _mapping(custody.get(key))
        for key in (
            "slot_ref",
            "navigation_option_ref",
            "navigation_selection_ref",
            "destination_binding_ref",
            "parent_read_custody_ref",
        )
    }
    context = _navigation_execution_context(state, **lineage)
    return _finish_navigation_execution(
        context,
        disposition=NAVIGATION_CUSTODIED,
        reason="navigation_read_custody_admitted_for_rejudgment",
        material_ref=custody,
    )


def _finish_navigation_execution(
    context: Mapping[str, Any],
    *,
    disposition: str,
    reason: str,
    material_ref: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate = deepcopy(_mapping(context["state"]))
    option = context["option"]
    slot = deepcopy(_mapping(context["slot"]))
    if material_ref is not None:
        slot["custody_refs"].append(deepcopy(dict(material_ref)))
    slot["posture"] = "active_unjudged"
    slot["latest_reason"] = reason
    slot["navigation_availability_reason"] = reason
    slot["action_history"].append(
        {
            "event": disposition,
            "navigation_selection_ref": deepcopy(option.active_selection_ref),
            "support_admitted": False,
        }
    )
    updated = NavigationOption(
        slot_id=option.slot_id,
        destination_binding_ref=option.destination_binding_ref,
        parent_read_custody_ref=option.parent_read_custody_ref,
        child_depth=option.child_depth,
        ancestor_physical_identity_digests=option.ancestor_physical_identity_digests,
        bounded_relationship_context=option.bounded_relationship_context,
        revision=option.revision + 1,
        disposition=disposition,
        active_selection_ref={},
        admission_ordinal=option.admission_ordinal,
    )
    candidate["slots_by_id"][option.slot_id] = _refresh_navigation_slot(slot)
    candidate["navigation"]["options_by_id"][
        updated.ref()["navigation_option_id"]
    ] = updated.to_dict()
    return _refresh_searchos_state(candidate)


def _verified_navigation_ledger_candidate_id(
    run_kernel: Any,
    *,
    candidate_id: str,
    reference: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> str:
    candidate_records = [
        _mapping(item)
        for item in run_kernel.state.evidence_ledger.to_projection().to_dict().get(
            "candidate_records", ()
        )
        if _mapping(item).get("candidate_id") == candidate_id
    ]
    custody_records = [
        _mapping(item)
        for item in (
            run_kernel.state.evidence_ledger
            .to_fetch_read_candidate_custody_projection()
            .get("fetch_read_candidate_custody_records", ())
        )
        if _mapping(item).get("candidate_id") == candidate_id
        and _mapping(item).get("reference_id") == reference.get("reference_id")
        and _mapping(item).get("reference_digest") == reference.get("reference_digest")
        and _mapping(item).get("fetch_read_content_packet_id") == packet.get("packet_id")
        and _mapping(item).get("fetch_read_content_packet_digest")
        == packet.get("packet_digest")
    ]
    if (
        len(candidate_records) != 1
        or len(custody_records) != 1
        or candidate_records[0].get("fact_disposition") != "observed"
        or candidate_records[0].get("readable_status") != "readable"
        or candidate_records[0].get("fetchable_status") != "fetchable"
        or candidate_records[0].get("evidence_material_type")
        != "searchos_read_custody"
        or candidate_records[0].get("eligible_for_stronger_obligation") is not False
        or candidate_records[0].get("final_evidence_eligible") is not False
        or custody_records[0].get("origin") != "searchos_navigation"
        or custody_records[0].get("fetch_read_status") != "readable"
        or custody_records[0].get("disposition") != "observed"
        or custody_records[0].get("lineage_only") is not True
        or custody_records[0].get("eligible_for_stronger_obligation") is not False
        or custody_records[0].get("final_evidence_eligible") is not False
        or custody_records[0].get("semantic_support_created") is not False
        or custody_records[0].get("citation_eligible") is not False
    ):
        raise NavigationRuntimeError(
            "navigation_custody_candidate_not_canonical"
        )
    return candidate_id


def execute_searchos_navigation_read_to_custody(
    *,
    run_kernel: Any,
    locator_store: EphemeralNavigationLocatorStore,
    navigation_lineage: Mapping[str, Any],
    available_providers: Mapping[str, object],
    acquisition_transports: Any = None,
    before_transport: Any = None,
) -> dict[str, Any]:
    """Bridge one pending selection through existing acquisition and custody."""

    from core.authorized_acquisition_runtime import (
        execute_acquisition_custody_authorization_action,
        execute_acquisition_work_order_to_terminal,
    )
    from core.cap_enforcement import RunCapExceeded
    from core.evidence_ledger_candidate_custody import (
        build_evidence_ledger_observation_from_fetch_read_content_packet,
    )
    from core.evidence_ledger_runtime import (
        execute_evidence_ledger_reduction_action,
    )
    from core.fetch_read_content_reference import (
        build_fetch_read_content_packet_from_navigation,
        fetch_read_content_packet_ref_from_packet,
        select_bounded_answer_bearing_text,
    )
    from core.run_kernel import (
        ACQUISITION_TERMINAL_REDUCTION_STAGE,
        Observation,
        RunStageStatus,
    )

    lineage = _json_mapping(navigation_lineage)
    try:
        context = _navigation_execution_context(run_kernel.state.searchos_state, **lineage)
        lineage = context["lineage"]
        if (
            locator_store.run_id != context["state"]["run_id"]
            or locator_store.request_id != context["state"]["request_id"]
        ):
            raise NavigationRuntimeError("navigation_locator_scope_mismatch")
        proposal = build_searchos_navigation_acquisition_need_proposal(run_kernel=run_kernel, **lineage)
    except Exception:
        slot_id = str(_mapping(lineage.get("slot_ref")).get("slot_id") or "")
        if slot_id:
            try:
                run_kernel.mark_searchos_slot_stale_or_invalid(
                    slot_id=slot_id, reason="navigation_execution_authority_invalid")
            except ValueError:
                pass
        return {"status": "failed", "failure_reason": "navigation_execution_authority_invalid",
                "provider_calls_attempted": 0, "provider_calls_completed": 0}
    try:
        acquisition = execute_acquisition_work_order_to_terminal(
            run_kernel=run_kernel,
            proposal=proposal,
            available_providers=available_providers,
            transports=acquisition_transports,
            before_transport=before_transport,
            transient_destination_resolver=lambda: locator_store.consume_once_for_execution(
                context["option"].destination_binding_ref),
        )
    except RunCapExceeded:
        receipt = _mapping(_mapping(run_kernel.state.projections.get(
            ACQUISITION_TERMINAL_REDUCTION_STAGE)).get("terminal_receipt"))
        result = _reduce_navigation_failure(
            run_kernel,
            lineage=lineage,
            reason="navigation_read_run_cap_exceeded",
            terminal_receipt_ref=_compact_ref(receipt, "terminal_receipt_ref"),
            acquisition={},
        )
        run_kernel.mark_searchos_slot_budget_exhausted(
            slot_id=context["option"].slot_id, reason="navigation_read_run_cap_exceeded")
        return result
    terminal = acquisition.get("terminal_receipt")
    execution = acquisition.get("execution_result")
    if execution is None or not execution.succeeded or len(execution.artifacts) != 1:
        if locator_store.resolve(context["option"].destination_binding_ref):
            locator_store.consume_once_for_execution(context["option"].destination_binding_ref)
        return _reduce_navigation_failure(
            run_kernel,
            lineage=lineage,
            reason=str(acquisition.get("failure_code") or "navigation_read_failed"),
            terminal_receipt_ref=terminal.ref() if terminal else None,
            acquisition=acquisition,
        )
    ledger_committed = False
    try:
        custody_action = run_kernel.authorize_acquisition_custody_consumption(
            terminal_receipt_ref=terminal.ref(),
            custody_consumer="core.searchos_navigation_runtime",
        )
        custody = execute_acquisition_custody_authorization_action(
            custody_action,
            work_order=acquisition["work_order"],
            route_observation=acquisition["route_observation"],
            terminal_receipt=terminal,
            custody_consumer="core.searchos_navigation_runtime",
            acquisition_control_state=run_kernel.state.acquisition_control_state,
        )
        run_kernel.reduce(custody.observation)
        artifact = execution.artifacts[0]
        selection = select_bounded_answer_bearing_text(artifact.retained_text or "")
        packet = build_fetch_read_content_packet_from_navigation(
            run_id=context["state"]["run_id"],
            request_id=context["state"]["request_id"],
            answer_contract_ref=proposal.answer_contract_ref,
            component_ref=proposal.component_ref,
            source_obligation_ref=proposal.source_obligation_ref,
            navigation_lineage=lineage,
            terminal_receipt_ref=terminal.ref(),
            custody_authorization_ref=custody.custody_authorization.ref(),
            sanitized_material={
                "fetch_read_status": "readable",
                "attempted_url": artifact.attempted_url,
                "provider_reported_url": artifact.provider_reported_url,
                "resolved_url": artifact.resolved_url,
                "final_url": artifact.final_url,
                "canonical_url": artifact.canonical_url,
                "content_type": artifact.content_type,
                "retrieved_or_observed_at": artifact.observed_at,
                "content_title": artifact.title,
                "bounded_text": selection.bounded_text,
                "bounded_text_sanitized": True,
                "bounded_text_bounded": True,
                "bounded_character_count": selection.bounded_text_char_count,
                "excerpt_digest": selection.bounded_text_digest,
            },
        )
        prospective_ledger = build_evidence_ledger_observation_from_fetch_read_content_packet(
            packet).to_dict()
        candidate_records = prospective_ledger["candidates"]
        custody_records = prospective_ledger["fetch_read_candidate_custody"]
        if (
            len(candidate_records) != 1
            or len(custody_records) != 1
            or candidate_records[0].get("candidate_id")
            != custody_records[0].get("candidate_id")
        ):
            raise NavigationRuntimeError(
                "navigation_custody_candidate_observation_mismatch"
            )
        canonical_candidate_id = str(candidate_records[0]["candidate_id"])
        record = custody_records[0]
        deepcopy(run_kernel.state.evidence_ledger).reduce_observation(prospective_ledger)
        ledger_action = run_kernel.authorize_evidence_ledger_reduction(
            inputs={
                "observation_source": prospective_ledger["observation_source"],
                "canonical_candidate_id": canonical_candidate_id,
                "reference_id": record["reference_id"],
                "reference_digest": record["reference_digest"],
                "fetch_read_content_packet_id": packet["packet_id"],
                "fetch_read_content_packet_digest": packet["packet_digest"],
                "fetch_read_candidate_custody_count": len(custody_records),
            }
        )
        ledger_result = execute_evidence_ledger_reduction_action(
            ledger_action, payload=prospective_ledger)
        run_kernel.reduce(ledger_result.observation)
        ledger_committed = True
        canonical_candidate_id = _verified_navigation_ledger_candidate_id(
            run_kernel,
            candidate_id=canonical_candidate_id,
            reference=packet["reference_records"][0],
            packet=packet,
        )
        material_ref = build_navigation_read_custody_material_ref(
            run_kernel.state.searchos_state,
            navigation_lineage=lineage,
            fetch_read_content_packet_ref=fetch_read_content_packet_ref_from_packet(packet),
            evidence_ledger_custody_ref={"reference_id": record["reference_id"],
                                         "reference_digest": record["reference_digest"]},
            confirmed_evidence_ledger_candidate_id=canonical_candidate_id,
            terminal_receipt_ref=terminal.ref(),
            custody_authorization_ref=custody.custody_authorization.ref(),
        )
        record_navigation_read_custody_material(
            run_kernel.state.searchos_state, custody_material_ref=material_ref)
        action = run_kernel.authorize_searchos_read_custody_admission(custody_material_ref=material_ref)
        run_kernel.reduce(
            Observation.from_action(
                action,
                observation_type=action.expected_observation_type,
                status=RunStageStatus.COMPLETED,
                payload={"custody_material_ref": material_ref},
            )
        )
    except Exception as exc:
        if ledger_committed:
            run_kernel.mark_searchos_slot_stale_or_invalid(
                slot_id=context["option"].slot_id,
                reason="navigation_custody_committed_searchos_admission_failed")
            raise NavigationRuntimeError(
                "navigation_custody_committed_searchos_admission_failed") from exc
        return _reduce_navigation_failure(
            run_kernel,
            lineage=lineage,
            reason=f"navigation_custody_{type(exc).__name__.casefold()}",
            terminal_receipt_ref=terminal.ref(),
            acquisition=acquisition,
        )
    return {
        "status": "custodied",
        "terminal_receipt_ref": terminal.ref(),
        "custody_authorization_ref": custody.custody_authorization.ref(),
        "fetch_read_content_packet_ref": fetch_read_content_packet_ref_from_packet(packet),
        "fetch_read_content_packet": packet,
        "evidence_ledger_custody_ref": material_ref["evidence_ledger_custody_ref"],
        "searchos_read_custody_ref": {
            "read_custody_material_id": material_ref["read_custody_material_id"],
            "read_custody_material_digest": material_ref["read_custody_material_digest"],
        },
        "provider_calls_attempted": acquisition["provider_calls_attempted"],
        "provider_calls_completed": acquisition["provider_calls_completed"],
    }


def _reduce_navigation_failure(
    run_kernel: Any,
    *,
    lineage: Mapping[str, Any],
    reason: str,
    terminal_receipt_ref: Mapping[str, Any] | None,
    acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    from core.run_kernel import Observation, RunStageStatus

    code = re.sub(r"[^a-z0-9_]+", "_", reason.casefold()).strip("_")
    if not code or not code[0].isalpha():
        code = f"navigation_failure_{code}"[:120]
    action = run_kernel.authorize_searchos_navigation_failure(
        navigation_lineage=lineage,
        failure_reason=code[:120],
        terminal_receipt_ref=terminal_receipt_ref,
    )
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload=dict(action.inputs),
        )
    )
    return {
        "status": "failed",
        "failure_reason": code[:120],
        "terminal_receipt_ref": dict(terminal_receipt_ref or {}),
        "provider_calls_attempted": int(acquisition.get("provider_calls_attempted") or 0),
        "provider_calls_completed": int(acquisition.get("provider_calls_completed") or 0),
    }


def project_navigation_window(state: Mapping[str, Any], *, slot_id: str) -> list[dict[str, Any]]:
    """Project the current deterministic selectable prefix without persisting it."""

    from core.searchos_iterative_judgment_runtime import validate_searchos_state

    canonical = validate_searchos_state(state)
    if _mapping(canonical.get("policy_snapshot")).get("navigation_runtime_open") is not True:
        return []
    navigation = _mapping(canonical.get("navigation"))
    options = [
        NavigationOption.from_dict(item)
        for item in _mapping(navigation.get("options_by_id")).values()
        if _mapping(item).get("slot_id") == slot_id and _mapping(item).get("disposition") == NAVIGATION_SELECTABLE
    ]
    options.sort(key=lambda item: item.admission_ordinal)
    limit = min(
        NAVIGATION_WINDOW_LIMIT,
        int(_mapping(canonical["policy_snapshot"]).get("candidate_use_window_size") or 0),
    )
    projected: list[dict[str, Any]] = []
    for option in options[:limit]:
        context = dict(option.bounded_relationship_context)
        projected.append(
            {
                "navigation_candidate_ref": navigation_candidate_ref(option.to_dict()),
                "parent_read_custody_ref": deepcopy(dict(option.parent_read_custody_ref)),
                **context,
                "source_relationship_posture": NAVIGATION_RELATIONSHIP_POSTURE,
            }
        )
    _ensure_url_free(projected, "navigation_window")
    return projected


def build_navigation_selection_action_inputs(
    state: Mapping[str, Any],
    *,
    judgment_decision_ref: Mapping[str, Any],
    navigation_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Perform only the canonical envelope checks needed for authorization."""

    from core.searchos_iterative_judgment_runtime import (
        SearchOSSlotPosture,
        validate_searchos_state,
    )

    canonical = validate_searchos_state(state)
    if _mapping(canonical.get("policy_snapshot")).get("navigation_runtime_open") is not True:
        raise NavigationRuntimeError("navigation_runtime_closed")
    decision_ref = _compact_ref(judgment_decision_ref, "judgment_decision_ref")
    candidate_ref = _json_mapping(navigation_candidate)
    matches = [
        _mapping(slot)
        for slot in _mapping(canonical.get("slots_by_id")).values()
        if _compact_optional_ref(slot.get("pending_navigation_decision_ref"))
        == decision_ref
    ]
    if len(matches) != 1:
        raise NavigationRuntimeError("navigation_pending_decision_not_current")
    slot = matches[0]
    if slot.get("posture") != SearchOSSlotPosture.AWAITING_NAVIGATION_ADMISSION.value:
        raise NavigationRuntimeError("navigation_pending_posture_not_current")
    if _mapping(slot.get("pending_navigation_candidate_ref")) != candidate_ref:
        raise NavigationRuntimeError("navigation_pending_candidate_not_current")
    option_ref = _mapping(candidate_ref.get("navigation_option_ref"))
    option_id = _token(option_ref.get("navigation_option_id"), "navigation_option_id")
    option_value = _mapping(
        _mapping(_mapping(canonical.get("navigation")).get("options_by_id")).get(
            option_id
        )
    )
    if not option_value:
        raise NavigationRuntimeError("navigation_option_not_current")
    option = NavigationOption.from_dict(option_value)
    if option.ref() != option_ref or navigation_candidate_ref(option_value) != candidate_ref:
        raise NavigationRuntimeError("navigation_candidate_not_current")
    inputs = {
        "expected_searchos_state_ref": {
            "state_id": canonical["state_id"],
            "state_digest": canonical["state_digest"],
        },
        "slot_ref": deepcopy(slot["slot_ref"]),
        "judgment_decision_ref": decision_ref,
        "navigation_candidate_ref": candidate_ref,
        "navigation_option_ref": option.ref(),
        "destination_binding_ref": deepcopy(dict(option.destination_binding_ref)),
        "parent_read_custody_ref": deepcopy(dict(option.parent_read_custody_ref)),
        "requested_selection_evaluation_posture": "bounded_navigation_selection_evaluation",
    }
    _ensure_url_free(inputs, "navigation_selection_action")
    return inputs


def execute_navigation_selection(
    *,
    action: Any,
    authorized_state_snapshot: Mapping[str, Any],
    locator_store: EphemeralNavigationLocatorStore,
) -> Any:
    """Evaluate one authorized selection without canonical mutation or charge."""

    from core.run_kernel import (
        ActionType,
        Observation,
        ObservationType,
        RunStageStatus,
    )
    from core.searchos_iterative_judgment_runtime import validate_searchos_state

    action.validate(
        action_type=ActionType.SEARCHOS_NAVIGATION_SELECT,
        stage=NAVIGATION_SELECTION_STAGE,
        expected_observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
    )
    inputs = _mapping(action.inputs)
    snapshot = validate_searchos_state(authorized_state_snapshot)

    def observed(outcome: str, reason: str) -> Any:
        payload = {
            **_selection_observation_base(action, inputs),
            "outcome": outcome,
            "reason": reason,
        }
        if outcome == NAVIGATION_SELECTION_ADMITTED:
            selection_ref, edge_ref, _ = _proposed_selection_records(action, inputs)
            payload["proposed_navigation_selection_ref"] = selection_ref
            payload["proposed_navigation_edge_ref"] = edge_ref
        _ensure_url_free(payload, "navigation_selection_observation")
        return Observation.from_action(
            action,
            observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
            status=RunStageStatus.COMPLETED,
            payload=payload,
        )

    if set(inputs) != {
        "expected_searchos_state_ref",
        "slot_ref",
        "judgment_decision_ref",
        "navigation_candidate_ref",
        "navigation_option_ref",
        "destination_binding_ref",
        "parent_read_custody_ref",
        "requested_selection_evaluation_posture",
    } or inputs.get("requested_selection_evaluation_posture") != (
        "bounded_navigation_selection_evaluation"
    ):
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_action_contract_mismatch",
        )

    expected_state = _mapping(inputs.get("expected_searchos_state_ref"))
    if expected_state != {
        "state_id": snapshot.get("state_id"),
        "state_digest": snapshot.get("state_digest"),
    }:
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_state_binding_mismatch",
        )
    slot_id = _token(_mapping(inputs.get("slot_ref")).get("slot_id"), "slot_id")
    slot = _mapping(_mapping(snapshot.get("slots_by_id")).get(slot_id))
    if not slot or _mapping(slot.get("slot_ref")) != _mapping(inputs.get("slot_ref")):
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_slot_not_current",
        )
    if _compact_optional_ref(slot.get("pending_navigation_decision_ref")) != _mapping(
        inputs.get("judgment_decision_ref")
    ):
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_pending_decision_mismatch",
        )
    if _mapping(slot.get("pending_navigation_candidate_ref")) != _mapping(
        inputs.get("navigation_candidate_ref")
    ):
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_pending_candidate_mismatch",
        )
    option_ref = _mapping(inputs.get("navigation_option_ref"))
    option_id = _token(option_ref.get("navigation_option_id"), "navigation_option_id")
    option_value = _mapping(
        _mapping(_mapping(snapshot.get("navigation")).get("options_by_id")).get(
            option_id
        )
    )
    if not option_value:
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_option_not_current",
        )
    try:
        option = NavigationOption.from_dict(option_value)
    except NavigationRuntimeError:
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_option_not_current",
        )
    if option.ref() != option_ref or navigation_candidate_ref(option_value) != _mapping(
        inputs.get("navigation_candidate_ref")
    ):
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_option_revision_mismatch",
        )
    if option.destination_binding_ref != _mapping(
        inputs.get("destination_binding_ref")
    ) or option.parent_read_custody_ref != _mapping(
        inputs.get("parent_read_custody_ref")
    ):
        return observed(
            NAVIGATION_SELECTION_AUTHORITY_REJECTED,
            "navigation_action_material_mismatch",
        )
    if option.disposition != NAVIGATION_SELECTABLE:
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_option_not_selectable",
        )
    current_parent_refs = {
        tuple(sorted(_compact_ref(item, "parent_read_custody_ref").items()))
        for item in slot.get("custody_refs") or ()
    }
    if tuple(sorted(option.parent_read_custody_ref.items())) not in current_parent_refs:
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_parent_relationship_unavailable",
        )
    policy = _mapping(snapshot.get("policy_snapshot"))
    if option.child_depth > int(policy.get("navigation_max_depth") or 0):
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_depth_limit_exhausted",
        )
    if option.destination_binding_ref["physical_identity_digest"] in set(
        option.ancestor_physical_identity_digests
    ):
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_ancestor_cycle",
        )
    if int(slot.get("navigation_selection_count") or 0) >= int(
        policy.get("navigation_selections_per_slot") or 0
    ):
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_selection_limit_exhausted",
        )
    if len(_mapping(snapshot.get("navigation")).get("edges") or ()) >= int(
        policy.get("navigation_edges_per_run") or 0
    ):
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_run_edge_limit_exhausted",
        )
    if int(slot.get("read_nomination_count") or 0) >= int(
        policy.get("read_nominations_per_slot") or 0
    ):
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_read_nomination_limit_exhausted",
        )
    try:
        exact = locator_store.resolve(option.destination_binding_ref)
    except NavigationRuntimeError:
        exact = None
    if exact is None:
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_destination_binding_missing",
        )
    reproduced = _binding_ref(
        normalize_navigation_destination(exact),
        binding_id=option.destination_binding_ref["destination_binding_id"],
    )
    if reproduced != option.destination_binding_ref:
        return observed(
            NAVIGATION_SELECTION_UNAVAILABLE,
            "navigation_destination_binding_mismatch",
        )
    return observed(NAVIGATION_SELECTION_ADMITTED, "navigation_selection_admitted")


def reduce_navigation_selection_observation(
    state: Mapping[str, Any],
    *,
    action: Any,
    observation: Any,
) -> dict[str, Any]:
    """Apply one URL-free selection observation to canonical SearchOS state."""

    from core.run_kernel import ActionType, ObservationType
    from core.searchos_iterative_judgment_runtime import (
        SearchOSSlotPosture,
        validate_searchos_state,
    )

    action.validate(
        action_type=ActionType.SEARCHOS_NAVIGATION_SELECT,
        stage=NAVIGATION_SELECTION_STAGE,
        expected_observation_type=ObservationType.SEARCHOS_NAVIGATION_SELECTED,
    )
    candidate = validate_searchos_state(state)
    inputs = _mapping(action.inputs)
    expected_state = _mapping(inputs.get("expected_searchos_state_ref"))
    if expected_state != {
        "state_id": candidate.get("state_id"),
        "state_digest": candidate.get("state_digest"),
    }:
        raise NavigationRuntimeError("navigation_observation_stale")
    payload = _mapping(observation.payload)
    base = _selection_observation_base(action, inputs)
    outcome = _token(payload.get("outcome"), "navigation_selection_outcome")
    reason = _reason_code(payload.get("reason"))
    allowed = {*base, "outcome", "reason"}
    if outcome == NAVIGATION_SELECTION_ADMITTED:
        allowed.update(
            {
                "proposed_navigation_selection_ref",
                "proposed_navigation_edge_ref",
            }
        )
    if set(payload) != allowed or any(payload.get(key) != value for key, value in base.items()):
        raise NavigationRuntimeError("navigation_observation_contract_mismatch")
    if outcome not in {
        NAVIGATION_SELECTION_ADMITTED,
        NAVIGATION_SELECTION_AUTHORITY_REJECTED,
        NAVIGATION_SELECTION_UNAVAILABLE,
    }:
        raise NavigationRuntimeError("navigation_selection_outcome_invalid")

    slot_id = _token(_mapping(inputs.get("slot_ref")).get("slot_id"), "slot_id")
    slots = deepcopy(_mapping(candidate.get("slots_by_id")))
    slot = _mapping(slots.get(slot_id))
    option_ref = _mapping(inputs.get("navigation_option_ref"))
    option_id = _token(option_ref.get("navigation_option_id"), "navigation_option_id")
    navigation = deepcopy(_mapping(candidate.get("navigation")))
    options = deepcopy(_mapping(navigation.get("options_by_id")))
    option = NavigationOption.from_dict(_mapping(options.get(option_id)))
    if not slot or option.ref() != option_ref:
        raise NavigationRuntimeError("navigation_reduction_authority_not_current")

    if outcome == NAVIGATION_SELECTION_ADMITTED:
        selection_ref, edge_ref, edge = _proposed_selection_records(action, inputs)
        if (
            _mapping(payload.get("proposed_navigation_selection_ref")) != selection_ref
            or _mapping(payload.get("proposed_navigation_edge_ref")) != edge_ref
            or option.disposition != NAVIGATION_SELECTABLE
        ):
            raise NavigationRuntimeError("navigation_admission_proposal_mismatch")
        slot["read_nomination_count"] = int(slot.get("read_nomination_count") or 0) + 1
        slot["navigation_selection_count"] = int(slot.get("navigation_selection_count") or 0) + 1
        slot["posture"] = SearchOSSlotPosture.AWAITING_NAVIGATION_EXECUTION.value
        option = NavigationOption(
            slot_id=option.slot_id,
            destination_binding_ref=option.destination_binding_ref,
            parent_read_custody_ref=option.parent_read_custody_ref,
            child_depth=option.child_depth,
            ancestor_physical_identity_digests=option.ancestor_physical_identity_digests,
            bounded_relationship_context=option.bounded_relationship_context,
            revision=option.revision + 1,
            disposition=NAVIGATION_PENDING_EXECUTION,
            active_selection_ref=selection_ref,
            admission_ordinal=option.admission_ordinal,
        )
        options[option_id] = option.to_dict()
        edges = list(navigation.get("edges") or ())
        edges.append(edge)
        navigation["edges"] = edges
        slot["latest_reason"] = "navigation_selection_admitted"
        slot["navigation_availability_reason"] = None
    elif outcome == NAVIGATION_SELECTION_AUTHORITY_REJECTED:
        slot["posture"] = SearchOSSlotPosture.STALE_OR_INVALID.value
        slot["latest_reason"] = reason
        slot["navigation_availability_reason"] = reason
    else:
        slot["posture"] = SearchOSSlotPosture.ACTIVE_UNJUDGED.value
        slot["latest_reason"] = reason
        slot["navigation_availability_reason"] = reason
        if reason in {
            "navigation_destination_binding_missing",
            "navigation_destination_binding_mismatch",
        }:
            options[option_id] = NavigationOption(
                slot_id=option.slot_id,
                destination_binding_ref=option.destination_binding_ref,
                parent_read_custody_ref=option.parent_read_custody_ref,
                child_depth=option.child_depth,
                ancestor_physical_identity_digests=option.ancestor_physical_identity_digests,
                bounded_relationship_context=option.bounded_relationship_context,
                revision=option.revision + 1,
                disposition=NAVIGATION_BINDING_UNAVAILABLE,
                active_selection_ref={},
                admission_ordinal=option.admission_ordinal,
            ).to_dict()
    slot["pending_navigation_decision_ref"] = {}
    slot["pending_navigation_candidate_ref"] = {}
    slot.setdefault("action_history", []).append(
        {
            "navigation_selection_action_id": action.action_id,
            "outcome": outcome,
            "posture_after": slot["posture"],
            "reason": slot["latest_reason"],
        }
    )
    slots[slot_id] = _refresh_navigation_slot(slot)
    navigation["options_by_id"] = options
    candidate["slots_by_id"] = slots
    candidate["navigation"] = navigation
    return _refresh_searchos_state(candidate)


def _selection_observation_base(action: Any, inputs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authorized_action_id": _token(action.action_id, "authorized_action_id"),
        "authorized_action_sequence": int(action.sequence),
        "expected_searchos_state_ref": deepcopy(
            _mapping(inputs.get("expected_searchos_state_ref"))
        ),
        "slot_ref": deepcopy(_mapping(inputs.get("slot_ref"))),
        "judgment_decision_ref": deepcopy(
            _mapping(inputs.get("judgment_decision_ref"))
        ),
        "navigation_candidate_ref": deepcopy(
            _mapping(inputs.get("navigation_candidate_ref"))
        ),
        "navigation_option_ref": deepcopy(
            _mapping(inputs.get("navigation_option_ref"))
        ),
        "destination_binding_ref": deepcopy(
            _mapping(inputs.get("destination_binding_ref"))
        ),
        "parent_read_custody_ref": deepcopy(
            _mapping(inputs.get("parent_read_custody_ref"))
        ),
    }


def _proposed_selection_records(
    action: Any, inputs: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    selection_core = {
        "authorized_action_id": _token(action.action_id, "authorized_action_id"),
        "judgment_decision_ref": deepcopy(
            _mapping(inputs.get("judgment_decision_ref"))
        ),
        "navigation_candidate_ref": deepcopy(
            _mapping(inputs.get("navigation_candidate_ref"))
        ),
        "navigation_option_ref": deepcopy(
            _mapping(inputs.get("navigation_option_ref"))
        ),
    }
    selection_digest = _digest(selection_core)
    selection_ref = {
        "navigation_selection_id": f"searchos-navigation-selection:{selection_digest[:24]}",
        "navigation_selection_digest": selection_digest,
    }
    edge_core = {
        "schema_version": NAVIGATION_EDGE_SCHEMA_VERSION,
        "owner": NAVIGATION_OWNER,
        "navigation_selection_ref": selection_ref,
        "slot_ref": deepcopy(_mapping(inputs.get("slot_ref"))),
        "navigation_option_ref": deepcopy(
            _mapping(inputs.get("navigation_option_ref"))
        ),
        "destination_binding_ref": deepcopy(
            _mapping(inputs.get("destination_binding_ref"))
        ),
        "parent_read_custody_ref": deepcopy(
            _mapping(inputs.get("parent_read_custody_ref"))
        ),
    }
    edge_digest = _digest(edge_core)
    edge_ref = {
        "navigation_edge_id": f"searchos-navigation-edge:{edge_digest[:24]}",
        "navigation_edge_digest": edge_digest,
    }
    return selection_ref, edge_ref, {**edge_core, **edge_ref}


def _iter_supported_markdown_links(text: str) -> Iterable[tuple[int, str, str]]:
    index = 0
    ordinal = 0
    while index < len(text):
        character = text[index]
        if character == "<":
            close = text.find(">", index + 1, min(len(text), index + 704))
            if close != -1:
                target = text[index + 1 : close]
                if target.casefold().startswith(("http://", "https://")):
                    ordinal += 1
                    yield ordinal, "linked page", target
                    index = close + 1
                    continue
        if character == "[" and (index == 0 or text[index - 1] != "!"):
            label_close = _scan_balanced(text, index, "[", "]", 512)
            if label_close is not None and text[label_close + 1 : label_close + 2] == "(":
                destination_close = _scan_balanced(text, label_close + 1, "(", ")", 900)
                if destination_close is not None:
                    destination = _markdown_destination(text[label_close + 2 : destination_close])
                    if destination is not None:
                        ordinal += 1
                        yield ordinal, text[index + 1 : label_close], destination
                    index = destination_close + 1
                    continue
        index += 1


def _scan_balanced(text: str, start: int, opening: str, closing: str, maximum_span: int) -> int | None:
    depth = 0
    escaped = False
    for index in range(start, min(len(text), start + maximum_span)):
        character = text[index]
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
        elif character == opening:
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
        return value[1:close] if close > 1 else None
    escaped = False
    depth = 0
    for index, character in enumerate(value):
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        elif character.isspace() and depth == 0:
            return value[:index] or None
    return value


def _explicit_port(netloc: str) -> bool:
    host_port = netloc.rsplit("@", 1)[-1]
    if host_port.startswith("["):
        close = host_port.find("]")
        suffix = host_port[close + 1 :] if close != -1 else ""
        if close == -1 or (suffix and not suffix.startswith(":")):
            raise NavigationRuntimeError("navigation_destination_authority_invalid")
        return bool(suffix)
    if host_port.count(":") > 1:
        raise NavigationRuntimeError("navigation_destination_hostname_invalid")
    return ":" in host_port


def _port_posture(*, scheme: str, port: int | None, explicit: bool) -> str:
    default = 443 if scheme == "https" else 80
    if not explicit:
        return f"implicit_default_{default}"
    if port == default:
        return f"explicit_default_{default}"
    return f"explicit_nondefault_{port}"


def _nondefault_port(value: Mapping[str, Any]) -> bool:
    return bool(value["port_explicit"]) and int(value["port"] or 0) != (443 if value["scheme"] == "https" else 80)


def _valid_ascii_hostname(value: str) -> bool:
    if len(value) > 253 or value.startswith(".") or value.endswith("."):
        return False
    labels = value.split(".")
    return all(
        label
        and len(label) <= 63
        and label[0].isalnum()
        and label[-1].isalnum()
        and all(character.isalnum() or character == "-" for character in label)
        for label in labels
    )


def _path_like(value: str) -> bool:
    compact = value.strip()
    return bool(re.search(r"(?i)(?:[/\\]|%2f|%5c)", compact))


def _ipv6_literal_like(value: str) -> bool:
    for raw_token in value[:NAVIGATION_LABEL_LENGTH_LIMIT].split():
        token = raw_token.strip("\"'(),.;!?{}<>")
        if not token:
            continue
        address = token
        if token.startswith("["):
            close = token.find("]")
            if close < 0:
                continue
            address = token[1:close]
            suffix = token[close + 1 :]
            if suffix and (not suffix.startswith(":") or not suffix[1:].isdigit()):
                continue
        try:
            ipaddress.IPv6Address(address)
        except ValueError:
            continue
        return True
    return False


def _validate_relationship_context(value: Mapping[str, Any], *, child_depth: int) -> dict[str, Any]:
    safe = _json_mapping(value)
    if set(safe) != {"parent_depth", "child_depth", "source_link_ordinal", "relationship_label"}:
        raise NavigationRuntimeError("navigation_relationship_context_invalid")
    parent = safe.get("parent_depth")
    child = safe.get("child_depth")
    ordinal = safe.get("source_link_ordinal")
    if (
        not isinstance(parent, int)
        or isinstance(parent, bool)
        or not isinstance(child, int)
        or isinstance(child, bool)
        or not isinstance(ordinal, int)
        or isinstance(ordinal, bool)
        or parent < 0
        or child != parent + 1
        or child != child_depth
        or ordinal <= 0
    ):
        raise NavigationRuntimeError("navigation_relationship_context_invalid")
    label = safe.get("relationship_label")
    if not isinstance(label, str) or label != scrub_navigation_relationship_label(label):
        raise NavigationRuntimeError("navigation_relationship_label_not_canonical")
    return safe


def _binding_ref(normalized: Mapping[str, Any], *, binding_id: str) -> dict[str, Any]:
    core = {
        "full_destination_digest": _digest_token(
            normalized.get("full_destination_digest"),
            "full_destination_digest",
        ),
        "semantic_identity_digest": _digest_token(
            normalized.get("semantic_identity_digest"),
            "semantic_identity_digest",
        ),
        "physical_identity_digest": _digest_token(
            normalized.get("physical_identity_digest"),
            "physical_identity_digest",
        ),
    }
    return {
        "destination_binding_id": _token(binding_id, "destination_binding_id"),
        "destination_binding_digest": _digest(core),
        **core,
    }


def _validate_binding_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(value)
    if set(safe) != {
        "destination_binding_id",
        "destination_binding_digest",
        "full_destination_digest",
        "semantic_identity_digest",
        "physical_identity_digest",
    }:
        raise NavigationRuntimeError("navigation_binding_ref_invalid")
    core = {
        "full_destination_digest": _digest_token(safe.get("full_destination_digest"), "full_destination_digest"),
        "semantic_identity_digest": _digest_token(safe.get("semantic_identity_digest"), "semantic_identity_digest"),
        "physical_identity_digest": _digest_token(safe.get("physical_identity_digest"), "physical_identity_digest"),
    }
    if safe.get("destination_binding_digest") != _digest(core):
        raise NavigationRuntimeError("navigation_binding_ref_invalid")
    binding_id = _token(safe.get("destination_binding_id"), "destination_binding_id")
    if not _BINDING_ID_RE.fullmatch(binding_id) or not binding_id.endswith(core["full_destination_digest"][:24]):
        raise NavigationRuntimeError("navigation_binding_ref_invalid")
    return deepcopy(safe)


def _validate_normalized_destination(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _mapping(value)
    exact = _token(
        safe.get("exact_url"),
        "normalized_navigation_destination",
        maximum=NAVIGATION_URL_LENGTH_LIMIT,
    )
    rebuilt = normalize_navigation_destination(exact)
    if safe != rebuilt:
        raise NavigationRuntimeError("navigation_normalized_destination_invalid")
    return rebuilt


def _compact_ref(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    safe = _mapping(value)
    for id_key, ref_id in reversed(tuple(safe.items())):
        if not id_key.endswith("_id") or not ref_id:
            continue
        digest_key = f"{id_key[:-3]}_digest"
        digest = safe.get(digest_key)
        if isinstance(digest, str) and len(digest) == 64:
            return {id_key: str(ref_id), digest_key: digest}
    raise NavigationRuntimeError(f"{field}_invalid")


def _compact_optional_ref(value: Any) -> dict[str, Any]:
    safe = _mapping(value)
    return _compact_ref(safe, "optional_ref") if safe else {}


def _reason_code(value: Any) -> str:
    reason = _token(value, "navigation_reason", maximum=120)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", reason):
        raise NavigationRuntimeError("navigation_reason_invalid")
    return reason


def _refresh_navigation_slot(slot: Mapping[str, Any]) -> dict[str, Any]:
    safe = deepcopy(dict(slot))
    safe.pop("slot_state_digest", None)
    safe["slot_state_digest"] = _digest(safe)
    return safe


def _ensure_url_free(value: Any, field: str) -> None:
    forbidden = {"url", "host", "path", "query", "href", "provider", "route"}
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).casefold()
            if any(token in lowered for token in forbidden):
                raise NavigationRuntimeError(f"{field}_contains_locator_key")
            _ensure_url_free(item, field)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _ensure_url_free(item, field)


def _refresh_searchos_state(value: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        key: deepcopy(item) for key, item in value.items() if key not in {"state_id", "state_digest", "replay_identity"}
    }
    digest = _digest(core)
    return {
        **core,
        "state_id": f"searchos-state:{digest[:24]}",
        "state_digest": digest,
        "replay_identity": f"searchos-state:{digest}",
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _json_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise NavigationRuntimeError("navigation_mapping_invalid")
    try:
        return json.loads(json.dumps(dict(value), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise NavigationRuntimeError("navigation_mapping_not_json_safe") from exc


def _token(value: Any, field: str, *, maximum: int = 320) -> str:
    token = str(value or "").strip()
    if not token or len(token) > maximum:
        raise NavigationRuntimeError(f"{field}_invalid")
    return token


def _digest_token(value: Any, field: str) -> str:
    token = _token(value, field, maximum=64)
    if len(token) != 64 or any(character not in "0123456789abcdef" for character in token):
        raise NavigationRuntimeError(f"{field}_invalid")
    return token


def _digest(value: Any) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise NavigationRuntimeError("navigation_value_not_json_safe") from exc
    return sha256(encoded.encode("utf-8")).hexdigest()


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _is_ascii(value: str) -> bool:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _increment(counts: dict[str, int], key: str) -> None:
    counts[key] = int(counts.get(key) or 0) + 1


__all__ = [
    "EphemeralNavigationLocatorStore",
    "NAVIGATION_BINDING_UNAVAILABLE",
    "NAVIGATION_EDGE_SCHEMA_VERSION",
    "NAVIGATION_EXTRACTION_LIMIT",
    "NAVIGATION_OPTION_SCHEMA_VERSION",
    "NAVIGATION_PENDING_EXECUTION",
    "NAVIGATION_RELATIONSHIP_POSTURE",
    "NAVIGATION_SELECTABLE",
    "NAVIGATION_SELECTION_ADMITTED",
    "NAVIGATION_SELECTION_AUTHORITY_REJECTED",
    "NAVIGATION_SELECTION_STAGE",
    "NAVIGATION_SELECTION_UNAVAILABLE",
    "NAVIGATION_WINDOW_LIMIT",
    "NavigationOption",
    "NavigationRuntimeError",
    "admit_navigation_options_from_markdown",
    "build_navigation_selection_action_inputs",
    "execute_navigation_selection",
    "extract_bounded_navigation_links",
    "navigation_candidate_ref",
    "navigation_destination_eligibility",
    "navigation_option_ref",
    "normalize_navigation_destination",
    "project_navigation_window",
    "reduce_navigation_selection_observation",
    "sanitize_navigation_source_text",
    "scrub_navigation_relationship_label",
    "build_searchos_navigation_acquisition_need_proposal",
    "validate_navigation_destination_for_binding",
    "validate_navigation_destination_binding_ref",
]
