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
NAVIGATION_OWNER = "RunKernel.SearchOSIterativeJudgment"
NAVIGATION_EXTRACTION_LIMIT = 48
NAVIGATION_WINDOW_LIMIT = 12
NAVIGATION_URL_LENGTH_LIMIT = 700
NAVIGATION_LABEL_LENGTH_LIMIT = 160
NAVIGATION_SOURCE_TEXT_LIMIT = 20_000
NAVIGATION_RELATIONSHIP_POSTURE = "outbound_link_from_current_read_custody"

NAVIGATION_SELECTABLE = "selectable"
NAVIGATION_PENDING_EXECUTION = "pending_execution"
NAVIGATION_BINDING_UNAVAILABLE = "binding_unavailable"

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_URL_RE = re.compile(r"(?i)(?:\bhttps?://|\bwww\.)")
_EMAIL_RE = re.compile(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_HOST_RE = re.compile(
    r"(?i)(?:^|\s)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}(?=$|\s|[/:])"
)
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
            _json_mapping(self.bounded_relationship_context),
        )
        if self.disposition not in {
            NAVIGATION_SELECTABLE,
            NAVIGATION_PENDING_EXECUTION,
            NAVIGATION_BINDING_UNAVAILABLE,
        }:
            raise NavigationRuntimeError("navigation_option_disposition_invalid")
        if self.child_depth <= 0 or self.revision <= 0 or self.admission_ordinal <= 0:
            raise NavigationRuntimeError("navigation_option_positive_fields_invalid")
        _token(self.slot_id, "slot_id")
        for digest in self.ancestor_physical_identity_digests:
            _digest_token(digest, "ancestor_physical_identity_digest")
        _ensure_url_free(self.bounded_relationship_context, "relationship_context")

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
                f"navigation-binding:{self.run_id}:{self.request_id}:{normalized['full_destination_digest'][:24]}"
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
        """Reserved future seam; destination execution is closed in this phase."""

        del binding_ref
        raise NavigationRuntimeError("navigation_execution_not_licensed")

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
    return compact.startswith(("/", "\\", "./", "../", "~/")) or bool(re.search(r"(?:^|\s)(?:\.\.?/|/)[^\s]+", compact))


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
    _token(safe.get("destination_binding_id"), "destination_binding_id")
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
    "NAVIGATION_EXTRACTION_LIMIT",
    "NAVIGATION_OPTION_SCHEMA_VERSION",
    "NAVIGATION_PENDING_EXECUTION",
    "NAVIGATION_RELATIONSHIP_POSTURE",
    "NAVIGATION_SELECTABLE",
    "NAVIGATION_WINDOW_LIMIT",
    "NavigationOption",
    "NavigationRuntimeError",
    "admit_navigation_options_from_markdown",
    "extract_bounded_navigation_links",
    "navigation_candidate_ref",
    "navigation_destination_eligibility",
    "navigation_option_ref",
    "normalize_navigation_destination",
    "project_navigation_window",
    "sanitize_navigation_source_text",
    "scrub_navigation_relationship_label",
]
