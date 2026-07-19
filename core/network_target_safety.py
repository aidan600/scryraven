"""Canonical, offline-only safety policy for dynamic content targets.

This module deliberately performs no DNS lookup and opens no network transport.
Callers supply immutable resolver snapshots, and the returned decision grants
only permission for the exact target to proceed at the named safety gate.
"""

from __future__ import annotations

import ipaddress
import json
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence
from urllib.parse import SplitResult, urlsplit, urlunsplit

NETWORK_TARGET_SAFETY_POLICY_VERSION = "network_target_safety_policy_v1"
NETWORK_TARGET_RESOLUTION_SNAPSHOT_SCHEMA_VERSION = (
    "network_target_resolution_snapshot_v1"
)
NETWORK_TARGET_SAFETY_DECISION_SCHEMA_VERSION = (
    "network_target_safety_decision_v1"
)
MAX_NETWORK_TARGET_URL_CHARACTERS = 4_096
MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES = 16
MAX_NETWORK_TARGET_RESOLUTION_SNAPSHOTS = 20


class NetworkTargetSafetyStage(str, Enum):
    ADMISSION_PRE_ROUTE = "admission_pre_route"
    FINAL_PRETRANSPORT = "final_pretransport"
    POSTTRANSPORT_OBSERVED_TARGET = "posttransport_observed_target"


class NetworkTargetTransportMode(str, Enum):
    PROVIDER_MEDIATED = "provider_mediated_content_target"


class NetworkTargetFactKind(str, Enum):
    EXPLICIT_USER = "explicit_user_url"
    SELECTED_CANDIDATE = "selected_candidate_url"
    REQUESTED = "requested_url"
    ATTEMPTED = "attempted_url"
    PROVIDER_REPORTED = "provider_reported_url"
    RESOLVED = "resolved_url"
    REDIRECT = "redirect_target_url"
    FINAL = "final_url"
    CANONICAL = "canonical_url"


class NetworkTargetSafetyStatus(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


_RESOLUTION_STATUSES = frozenset(
    {
        "resolved",
        "empty",
        "malformed",
        "resolver_exception",
        "indeterminate",
        "overflow",
    }
)
_PROHIBITED_ADDRESS_CLASSIFICATIONS = frozenset(
    {
        "unspecified",
        "loopback",
        "link_local",
        "private_network",
        "reserved",
        "multicast",
        "non_global",
    }
)
_LINEAGE_KEYS = frozenset(
    {
        "run_id",
        "request_id",
        "proposal_id",
        "work_order_id",
        "route_observation_id",
        "execution_action_id",
        "artifact_id",
        "source_obligation_id",
        "observation_kind",
    }
)
_ASCII_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_NUMERIC_TOKEN = re.compile(r"[+-]?(?:0[xX][0-9a-fA-F]+|[0-9]+)\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DECISION_REF_FIELDS = frozenset(
    {
        "decision_id",
        "decision_digest",
        "policy_version",
        "policy_digest",
        "stage",
        "status",
        "blocker_code",
        "transport_mode",
        "fact_kind",
        "supplied_url_digest",
        "normalized_target_digest",
        "canonical_host",
        "resolver_snapshot_id",
        "resolver_snapshot_digest",
        "lineage_ref",
        "raw_dns_retained",
        "raw_private_network_data_retained",
        "credentials_retained",
        "all_downstream_authority_granted",
    }
)
_DECISION_TRACE_FIELDS = _DECISION_REF_FIELDS | {
    "schema_version",
    "scheme",
    "normalized_port",
    "port_posture",
    "host_posture",
    "address_family_posture",
    "fragment_posture",
    "resolver_snapshot_ref",
    "address_classification_counts",
    "previous_decision_ref",
    "unrelated_host_data_retained",
    "acquisition_authority_granted",
    "capability_authority_granted",
    "provider_authority_granted",
    "route_authority_granted",
    "execution_authority_granted",
    "custody_authority_granted",
    "evidence_authority_granted",
    "citation_authority_granted",
}
_RESOLUTION_SNAPSHOT_REF_FIELDS = frozenset(
    {
        "snapshot_id",
        "snapshot_digest",
        "canonical_host",
        "resolution_status",
        "address_count",
        "raw_dns_retained",
        "raw_private_network_data_retained",
    }
)
_FALSE_DECISION_TRACE_FIELDS = frozenset(
    {
        "raw_dns_retained",
        "raw_private_network_data_retained",
        "credentials_retained",
        "all_downstream_authority_granted",
        "unrelated_host_data_retained",
        "acquisition_authority_granted",
        "capability_authority_granted",
        "provider_authority_granted",
        "route_authority_granted",
        "execution_authority_granted",
        "custody_authority_granted",
        "evidence_authority_granted",
        "citation_authority_granted",
    }
)
_PORT_POSTURES = frozenset(
    {
        "unavailable",
        "default_implicit",
        "default_explicit_normalized",
        "nondefault_explicit",
    }
)
_HOST_POSTURES = frozenset({"unavailable", "literal_ip", "hostname"})
_ADDRESS_FAMILY_POSTURES = frozenset(
    {
        "unavailable",
        "resolver_dependent",
        "ipv4",
        "ipv6",
        "ipv4_mapped_ipv6_effective_ipv4",
    }
)
_FRAGMENT_POSTURES = frozenset(
    {
        "not_retained",
        "fragment_absent",
        "fragment_stripped_from_source_identity",
    }
)


class _TargetParseBlocked(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def stable_json_digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def network_target_safety_policy_ref() -> dict[str, str]:
    core = {
        "owner": "core.network_target_safety",
        "policy_version": NETWORK_TARGET_SAFETY_POLICY_VERSION,
        "resolver_boundary": "injected_snapshot_only_no_live_dns",
        "public_target_rule": "all_observed_addresses_must_be_global",
        "credentials_retained": "false",
    }
    return {**core, "policy_digest": stable_json_digest(core)}


@dataclass(frozen=True, slots=True)
class NetworkTargetResolutionSnapshotV1:
    snapshot_id: str
    snapshot_digest: str
    canonical_host: str
    resolution_status: str
    address_entries: tuple[Mapping[str, Any], ...]
    address_count: int
    schema_version: str = NETWORK_TARGET_RESOLUTION_SNAPSHOT_SCHEMA_VERSION
    raw_dns_retained: bool = False
    raw_private_network_data_retained: bool = False

    @classmethod
    def create(
        cls,
        *,
        canonical_host: str,
        addresses: Sequence[str] = (),
        resolution_status: str = "resolved",
    ) -> "NetworkTargetResolutionSnapshotV1":
        host = _canonical_snapshot_host(canonical_host)
        status = str(resolution_status or "").strip().casefold()
        if status not in _RESOLUTION_STATUSES:
            status = "indeterminate"
        parsed: dict[str, ipaddress.IPv4Address | ipaddress.IPv6Address] = {}
        malformed = False
        for raw in addresses:
            text = str(raw or "").strip()
            try:
                address = ipaddress.ip_address(text)
            except ValueError:
                malformed = True
                continue
            parsed[address.compressed.casefold()] = address
        if malformed:
            status = "malformed"
        elif len(parsed) > MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES:
            status = "overflow"
        elif status == "resolved" and not parsed:
            status = "empty"
        ordered = [parsed[key] for key in sorted(parsed)]
        if len(ordered) > MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES:
            ordered = ordered[:MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES]
        entries = tuple(
            sorted(
                (_address_entry(address) for address in ordered),
                key=lambda item: str(item["address_digest"]),
            )
        )
        core = {
            "schema_version": NETWORK_TARGET_RESOLUTION_SNAPSHOT_SCHEMA_VERSION,
            "canonical_host": host,
            "resolution_status": status,
            "address_entries": [dict(entry) for entry in entries],
            "address_count": len(parsed),
            "address_bound": MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES,
            "raw_dns_retained": False,
            "raw_private_network_data_retained": False,
        }
        digest = stable_json_digest(core)
        return cls(
            snapshot_id=f"network-target-resolution:{digest[:24]}",
            snapshot_digest=digest,
            canonical_host=host,
            resolution_status=status,
            address_entries=entries,
            address_count=len(parsed),
        )

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "NetworkTargetResolutionSnapshotV1":
        raw = dict(value or {})
        expected = {
            "schema_version",
            "snapshot_id",
            "snapshot_digest",
            "canonical_host",
            "resolution_status",
            "address_entries",
            "address_count",
            "address_bound",
            "raw_dns_retained",
            "raw_private_network_data_retained",
        }
        if set(raw) != expected:
            raise ValueError("network_target_resolution_snapshot_fields_invalid")
        if raw.get("schema_version") != NETWORK_TARGET_RESOLUTION_SNAPSHOT_SCHEMA_VERSION:
            raise ValueError("network_target_resolution_snapshot_schema_invalid")
        if raw.get("raw_dns_retained") is not False:
            raise ValueError("network_target_resolution_snapshot_raw_dns_forbidden")
        if raw.get("raw_private_network_data_retained") is not False:
            raise ValueError("network_target_resolution_snapshot_private_data_forbidden")
        if raw.get("address_bound") != MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES:
            raise ValueError("network_target_resolution_snapshot_bound_invalid")
        host = _canonical_snapshot_host(raw.get("canonical_host"))
        status = str(raw.get("resolution_status") or "")
        if status not in _RESOLUTION_STATUSES:
            raise ValueError("network_target_resolution_snapshot_status_invalid")
        entries = tuple(
            _validated_address_entry(item)
            for item in raw.get("address_entries") or ()
        )
        if len(entries) > MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES:
            raise ValueError("network_target_resolution_snapshot_overflow")
        if list(entries) != sorted(
            entries,
            key=lambda item: str(item["address_digest"]),
        ):
            raise ValueError("network_target_resolution_snapshot_order_invalid")
        address_count_raw = raw.get("address_count")
        if (
            isinstance(address_count_raw, bool)
            or not isinstance(address_count_raw, int)
            or address_count_raw < 0
        ):
            raise ValueError("network_target_resolution_snapshot_count_invalid")
        address_count = address_count_raw
        if status == "overflow":
            if address_count < len(entries):
                raise ValueError(
                    "network_target_resolution_snapshot_overflow_count_invalid"
                )
        elif address_count != len(entries):
            raise ValueError("network_target_resolution_snapshot_count_invalid")
        if status == "resolved" and address_count == 0:
            raise ValueError("network_target_resolution_snapshot_resolved_empty")
        if status == "empty" and address_count != 0:
            raise ValueError("network_target_resolution_snapshot_empty_count_invalid")
        core = {
            "schema_version": NETWORK_TARGET_RESOLUTION_SNAPSHOT_SCHEMA_VERSION,
            "canonical_host": host,
            "resolution_status": status,
            "address_entries": [dict(entry) for entry in entries],
            "address_count": address_count,
            "address_bound": MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES,
            "raw_dns_retained": False,
            "raw_private_network_data_retained": False,
        }
        digest = stable_json_digest(core)
        if raw.get("snapshot_digest") != digest or raw.get("snapshot_id") != (
            f"network-target-resolution:{digest[:24]}"
        ):
            raise ValueError("network_target_resolution_snapshot_identity_invalid")
        return cls(
            snapshot_id=str(raw["snapshot_id"]),
            snapshot_digest=digest,
            canonical_host=host,
            resolution_status=status,
            address_entries=entries,
            address_count=address_count,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "snapshot_digest": self.snapshot_digest,
            "canonical_host": self.canonical_host,
            "resolution_status": self.resolution_status,
            "address_entries": [dict(entry) for entry in self.address_entries],
            "address_count": self.address_count,
            "address_bound": MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES,
            "raw_dns_retained": self.raw_dns_retained,
            "raw_private_network_data_retained": (
                self.raw_private_network_data_retained
            ),
        }

    def ref(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "snapshot_digest": self.snapshot_digest,
            "canonical_host": self.canonical_host,
            "resolution_status": self.resolution_status,
            "address_count": self.address_count,
            "raw_dns_retained": False,
            "raw_private_network_data_retained": False,
        }


@dataclass(frozen=True, slots=True)
class NetworkTargetSafetyDecisionV1:
    decision_id: str
    decision_digest: str
    stage: str
    status: str
    blocker_code: str | None
    transport_mode: str
    fact_kind: str
    supplied_url_digest: str
    normalized_target_url: str | None
    normalized_target_digest: str | None
    scheme: str | None
    canonical_host: str | None
    normalized_port: int | None
    port_posture: str
    host_posture: str
    address_family_posture: str
    fragment_posture: str
    resolver_snapshot_ref: Mapping[str, Any]
    address_classification_counts: Mapping[str, int]
    lineage_ref: Mapping[str, str]
    previous_decision_ref: Mapping[str, Any]
    schema_version: str = NETWORK_TARGET_SAFETY_DECISION_SCHEMA_VERSION
    raw_dns_retained: bool = False
    raw_private_network_data_retained: bool = False
    credentials_retained: bool = False
    unrelated_host_data_retained: bool = False
    acquisition_authority_granted: bool = False
    capability_authority_granted: bool = False
    provider_authority_granted: bool = False
    route_authority_granted: bool = False
    execution_authority_granted: bool = False
    custody_authority_granted: bool = False
    evidence_authority_granted: bool = False
    citation_authority_granted: bool = False

    @classmethod
    def from_trace(
        cls, value: Mapping[str, Any]
    ) -> "NetworkTargetSafetyDecisionV1":
        """Rehydrate one exact, current-policy, persistence-safe decision."""

        if not isinstance(value, Mapping):
            raise ValueError("network_target_safety_decision_trace_mapping_required")
        raw = dict(value)
        if set(raw) != _DECISION_TRACE_FIELDS:
            raise ValueError("network_target_safety_decision_trace_fields_invalid")
        if (
            raw.get("schema_version")
            != NETWORK_TARGET_SAFETY_DECISION_SCHEMA_VERSION
        ):
            raise ValueError("network_target_safety_decision_trace_schema_invalid")
        policy = network_target_safety_policy_ref()
        if (
            raw.get("policy_version") != policy["policy_version"]
            or raw.get("policy_digest") != policy["policy_digest"]
        ):
            raise ValueError("network_target_safety_decision_policy_invalid")
        if any(raw.get(field) is not False for field in _FALSE_DECISION_TRACE_FIELDS):
            raise ValueError("network_target_safety_decision_authority_invalid")

        stage = _validated_enum_value(
            raw.get("stage"),
            NetworkTargetSafetyStage,
            "network_target_safety_decision_stage_invalid",
        )
        status = _validated_enum_value(
            raw.get("status"),
            NetworkTargetSafetyStatus,
            "network_target_safety_decision_status_invalid",
        )
        blocker_code = _validated_optional_token(
            raw.get("blocker_code"),
            limit=220,
            code="network_target_safety_decision_blocker_invalid",
        )
        if (status == NetworkTargetSafetyStatus.BLOCKED.value) != bool(
            blocker_code
        ):
            raise ValueError("network_target_safety_decision_blocker_mismatch")
        transport_mode = _validated_enum_value(
            raw.get("transport_mode"),
            NetworkTargetTransportMode,
            "network_target_safety_decision_transport_mode_invalid",
        )
        fact_kind = _validated_enum_value(
            raw.get("fact_kind"),
            NetworkTargetFactKind,
            "network_target_safety_decision_fact_kind_invalid",
        )
        supplied_url_digest = _validated_sha256(
            raw.get("supplied_url_digest"),
            "network_target_safety_decision_supplied_digest_invalid",
        )
        normalized_target_digest = _validated_optional_sha256(
            raw.get("normalized_target_digest"),
            "network_target_safety_decision_normalized_digest_invalid",
        )
        scheme = raw.get("scheme")
        if scheme not in {None, "http", "https"}:
            raise ValueError("network_target_safety_decision_scheme_invalid")
        canonical_host = _validated_optional_canonical_host(
            raw.get("canonical_host")
        )
        if str(blocker_code or "").startswith("target_address_") and (
            canonical_host is not None
        ):
            raise ValueError(
                "network_target_safety_decision_private_host_retained"
            )
        normalized_port = raw.get("normalized_port")
        if normalized_port is not None and (
            isinstance(normalized_port, bool)
            or not isinstance(normalized_port, int)
            or not 1 <= normalized_port <= 65_535
        ):
            raise ValueError("network_target_safety_decision_port_invalid")
        port_posture = _validated_choice(
            raw.get("port_posture"),
            _PORT_POSTURES,
            "network_target_safety_decision_port_posture_invalid",
        )
        host_posture = _validated_choice(
            raw.get("host_posture"),
            _HOST_POSTURES,
            "network_target_safety_decision_host_posture_invalid",
        )
        address_family_posture = _validated_choice(
            raw.get("address_family_posture"),
            _ADDRESS_FAMILY_POSTURES,
            "network_target_safety_decision_address_family_invalid",
        )
        fragment_posture = _validated_choice(
            raw.get("fragment_posture"),
            _FRAGMENT_POSTURES,
            "network_target_safety_decision_fragment_posture_invalid",
        )
        resolver_snapshot_ref = _validated_resolution_snapshot_ref(
            raw.get("resolver_snapshot_ref")
        )
        resolver_snapshot_id = raw.get("resolver_snapshot_id")
        resolver_snapshot_digest = raw.get("resolver_snapshot_digest")
        if resolver_snapshot_ref:
            if (
                resolver_snapshot_id != resolver_snapshot_ref["snapshot_id"]
                or resolver_snapshot_digest
                != resolver_snapshot_ref["snapshot_digest"]
            ):
                raise ValueError(
                    "network_target_safety_decision_resolver_ref_mismatch"
                )
        elif resolver_snapshot_id is not None or resolver_snapshot_digest is not None:
            raise ValueError(
                "network_target_safety_decision_resolver_ref_mismatch"
            )
        counts = _validated_classification_counts(
            raw.get("address_classification_counts")
        )
        if (
            resolver_snapshot_ref.get("resolution_status") == "resolved"
            and resolver_snapshot_ref.get("canonical_host") == canonical_host
            and sum(counts.values())
            != resolver_snapshot_ref.get("address_count")
        ):
            raise ValueError(
                "network_target_safety_decision_address_counts_mismatch"
            )
        if (
            status == NetworkTargetSafetyStatus.ALLOWED.value
            and host_posture == "hostname"
            and (
                not resolver_snapshot_ref
                or resolver_snapshot_ref.get("resolution_status") != "resolved"
                or resolver_snapshot_ref.get("canonical_host") != canonical_host
                or resolver_snapshot_ref.get("address_count", 0) <= 0
                or set(counts).difference({"public"})
                or counts.get("public")
                != resolver_snapshot_ref.get("address_count")
            )
        ):
            raise ValueError(
                "network_target_safety_decision_allowed_resolution_invalid"
            )
        lineage_ref = _validated_lineage_ref(raw.get("lineage_ref"))
        previous_decision_ref = _validated_previous_decision_ref(
            raw.get("previous_decision_ref")
        )
        decision_digest = _validated_sha256(
            raw.get("decision_digest"),
            "network_target_safety_decision_digest_invalid",
        )
        core = _decision_digest_core(
            stage=stage,
            status=status,
            blocker_code=blocker_code,
            transport_mode=transport_mode,
            fact_kind=fact_kind,
            supplied_url_digest=supplied_url_digest,
            normalized_target_digest=normalized_target_digest,
            scheme=scheme,
            canonical_host=canonical_host,
            normalized_port=normalized_port,
            port_posture=port_posture,
            host_posture=host_posture,
            address_family_posture=address_family_posture,
            fragment_posture=fragment_posture,
            resolver_snapshot_ref=resolver_snapshot_ref,
            address_classification_counts=counts,
            lineage_ref=lineage_ref,
            previous_decision_ref=previous_decision_ref,
        )
        expected_digest = stable_json_digest(core)
        expected_id = (
            f"network-target-safety:{stage}:{expected_digest[:24]}"
        )
        if (
            decision_digest != expected_digest
            or raw.get("decision_id") != expected_id
        ):
            raise ValueError("network_target_safety_decision_identity_invalid")
        return cls(
            decision_id=expected_id,
            decision_digest=expected_digest,
            stage=stage,
            status=status,
            blocker_code=blocker_code,
            transport_mode=transport_mode,
            fact_kind=fact_kind,
            supplied_url_digest=supplied_url_digest,
            normalized_target_url=None,
            normalized_target_digest=normalized_target_digest,
            scheme=scheme,
            canonical_host=canonical_host,
            normalized_port=normalized_port,
            port_posture=port_posture,
            host_posture=host_posture,
            address_family_posture=address_family_posture,
            fragment_posture=fragment_posture,
            resolver_snapshot_ref=resolver_snapshot_ref,
            address_classification_counts=counts,
            lineage_ref=lineage_ref,
            previous_decision_ref=previous_decision_ref,
        )

    def ref(self) -> dict[str, Any]:
        policy = network_target_safety_policy_ref()
        canonical_host = self.canonical_host
        if str(self.blocker_code or "").startswith("target_address_"):
            canonical_host = None
        return {
            "decision_id": self.decision_id,
            "decision_digest": self.decision_digest,
            "policy_version": policy["policy_version"],
            "policy_digest": policy["policy_digest"],
            "stage": self.stage,
            "status": self.status,
            "blocker_code": self.blocker_code,
            "transport_mode": self.transport_mode,
            "fact_kind": self.fact_kind,
            "supplied_url_digest": self.supplied_url_digest,
            "normalized_target_digest": self.normalized_target_digest,
            "canonical_host": canonical_host,
            "resolver_snapshot_id": self.resolver_snapshot_ref.get("snapshot_id"),
            "resolver_snapshot_digest": self.resolver_snapshot_ref.get(
                "snapshot_digest"
            ),
            "lineage_ref": dict(self.lineage_ref),
            "raw_dns_retained": False,
            "raw_private_network_data_retained": False,
            "credentials_retained": False,
            "all_downstream_authority_granted": False,
        }

    def to_dict(self, *, include_normalized_target: bool = True) -> dict[str, Any]:
        payload = {
            **self.ref(),
            "schema_version": self.schema_version,
            "scheme": self.scheme,
            "normalized_port": self.normalized_port,
            "port_posture": self.port_posture,
            "host_posture": self.host_posture,
            "address_family_posture": self.address_family_posture,
            "fragment_posture": self.fragment_posture,
            "resolver_snapshot_ref": dict(self.resolver_snapshot_ref),
            "address_classification_counts": dict(
                self.address_classification_counts
            ),
            "previous_decision_ref": dict(self.previous_decision_ref),
            "unrelated_host_data_retained": False,
            "acquisition_authority_granted": False,
            "capability_authority_granted": False,
            "provider_authority_granted": False,
            "route_authority_granted": False,
            "execution_authority_granted": False,
            "custody_authority_granted": False,
            "evidence_authority_granted": False,
            "citation_authority_granted": False,
        }
        if include_normalized_target:
            payload["normalized_target_url"] = self.normalized_target_url
        return payload

    def to_trace(self) -> dict[str, Any]:
        """Return a bounded persistence-safe form without path/query material."""

        return self.to_dict(include_normalized_target=False)


def evaluate_network_target_safety(
    url: str,
    *,
    stage: NetworkTargetSafetyStage | str,
    transport_mode: NetworkTargetTransportMode | str,
    fact_kind: NetworkTargetFactKind | str,
    resolver_snapshot: NetworkTargetResolutionSnapshotV1 | None = None,
    previous_decision_ref: Mapping[str, Any] | None = None,
    lineage_ref: Mapping[str, Any] | None = None,
    require_hostname_resolution: bool = True,
    posttransport_observation_overflow: bool = False,
) -> NetworkTargetSafetyDecisionV1:
    """Evaluate one exact content target without performing any I/O."""

    if resolver_snapshot is not None:
        resolver_snapshot = _canonical_resolution_snapshot(resolver_snapshot)
    stage_value = NetworkTargetSafetyStage(stage).value
    transport_value = NetworkTargetTransportMode(transport_mode).value
    fact_value = NetworkTargetFactKind(fact_kind).value
    if not isinstance(posttransport_observation_overflow, bool):
        raise ValueError("posttransport_observation_overflow_boolean_required")
    if posttransport_observation_overflow and (
        stage_value
        != NetworkTargetSafetyStage.POSTTRANSPORT_OBSERVED_TARGET.value
        or transport_value != NetworkTargetTransportMode.PROVIDER_MEDIATED.value
        or fact_value != NetworkTargetFactKind.PROVIDER_REPORTED.value
    ):
        raise ValueError("posttransport_observation_overflow_posture_invalid")
    supplied = url if isinstance(url, str) else ""
    supplied_digest = stable_json_digest({"supplied_url": supplied})
    parsed_target: dict[str, Any] = {}
    blocker: str | None = None
    try:
        parsed_target = _parse_target(supplied)
    except _TargetParseBlocked as exc:
        blocker = exc.code

    if blocker is None and posttransport_observation_overflow:
        blocker = "posttransport_target_observation_overflow"

    snapshot_ref: dict[str, Any] = {}
    counts: dict[str, int] = {}
    if blocker is None:
        literal_classification = parsed_target.get("literal_classification")
        if literal_classification and literal_classification != "public":
            blocker = f"target_address_{literal_classification}_blocked"
            counts[literal_classification] = 1
        elif parsed_target.get("host_posture") == "hostname":
            if require_hostname_resolution:
                if resolver_snapshot is None:
                    blocker = "target_resolution_snapshot_missing"
                else:
                    snapshot_ref = resolver_snapshot.ref()
                    if resolver_snapshot.canonical_host != parsed_target.get(
                        "canonical_host"
                    ):
                        blocker = "target_resolution_snapshot_host_mismatch"
                    elif resolver_snapshot.resolution_status != "resolved":
                        blocker = {
                            "empty": "target_resolution_empty",
                            "malformed": "target_resolution_malformed",
                            "resolver_exception": "target_resolution_exception",
                            "indeterminate": "target_resolution_indeterminate",
                            "overflow": "target_resolution_overflow",
                        }.get(
                            resolver_snapshot.resolution_status,
                            "target_resolution_indeterminate",
                        )
                    else:
                        counts = _classification_counts(
                            resolver_snapshot.address_entries
                        )
                        prohibited = sorted(
                            classification
                            for classification, count in counts.items()
                            if count
                            and classification
                            in _PROHIBITED_ADDRESS_CLASSIFICATIONS
                        )
                        if prohibited:
                            blocker = (
                                "target_resolution_contains_prohibited_address:"
                                + prohibited[0]
                            )
            elif resolver_snapshot is not None:
                snapshot_ref = resolver_snapshot.ref()

    previous = _bounded_decision_ref(previous_decision_ref)
    if blocker is None and stage_value == NetworkTargetSafetyStage.FINAL_PRETRANSPORT.value:
        if not previous:
            blocker = "admission_target_safety_decision_missing"
        elif previous.get("stage") != NetworkTargetSafetyStage.ADMISSION_PRE_ROUTE.value:
            blocker = "admission_target_safety_stage_invalid"
        elif previous.get("status") != NetworkTargetSafetyStatus.ALLOWED.value:
            blocker = "admission_target_safety_not_allowed"
        elif previous.get("policy_digest") != network_target_safety_policy_ref()[
            "policy_digest"
        ]:
            blocker = "target_safety_policy_changed_between_gates"
        elif previous.get("normalized_target_digest") != parsed_target.get(
            "normalized_target_digest"
        ):
            blocker = "target_changed_between_admission_and_pretransport"
        elif previous.get("transport_mode") != transport_value:
            blocker = "target_transport_mode_changed_between_gates"
        elif previous.get("resolver_snapshot_digest") != snapshot_ref.get(
            "snapshot_digest"
        ):
            blocker = "target_resolution_changed_between_gates"

    status = (
        NetworkTargetSafetyStatus.BLOCKED.value
        if blocker
        else NetworkTargetSafetyStatus.ALLOWED.value
    )
    lineage = _bounded_lineage_ref(lineage_ref)
    persisted_canonical_host = _persisted_decision_canonical_host(
        blocker_code=blocker,
        canonical_host=parsed_target.get("canonical_host"),
    )
    core = _decision_digest_core(
        stage=stage_value,
        status=status,
        blocker_code=blocker,
        transport_mode=transport_value,
        fact_kind=fact_value,
        supplied_url_digest=supplied_digest,
        normalized_target_digest=parsed_target.get("normalized_target_digest"),
        scheme=parsed_target.get("scheme"),
        canonical_host=persisted_canonical_host,
        normalized_port=parsed_target.get("normalized_port"),
        port_posture=parsed_target.get("port_posture", "unavailable"),
        host_posture=parsed_target.get("host_posture", "unavailable"),
        address_family_posture=parsed_target.get(
            "address_family_posture", "unavailable"
        ),
        fragment_posture=parsed_target.get("fragment_posture", "not_retained"),
        resolver_snapshot_ref=snapshot_ref,
        address_classification_counts=counts,
        lineage_ref=lineage,
        previous_decision_ref=previous,
    )
    digest = stable_json_digest(core)
    return NetworkTargetSafetyDecisionV1(
        decision_id=f"network-target-safety:{stage_value}:{digest[:24]}",
        decision_digest=digest,
        stage=stage_value,
        status=status,
        blocker_code=blocker,
        transport_mode=transport_value,
        fact_kind=fact_value,
        supplied_url_digest=supplied_digest,
        normalized_target_url=parsed_target.get("normalized_target_url"),
        normalized_target_digest=parsed_target.get("normalized_target_digest"),
        scheme=parsed_target.get("scheme"),
        canonical_host=parsed_target.get("canonical_host"),
        normalized_port=parsed_target.get("normalized_port"),
        port_posture=parsed_target.get("port_posture", "unavailable"),
        host_posture=parsed_target.get("host_posture", "unavailable"),
        address_family_posture=parsed_target.get(
            "address_family_posture", "unavailable"
        ),
        fragment_posture=parsed_target.get("fragment_posture", "not_retained"),
        resolver_snapshot_ref=snapshot_ref,
        address_classification_counts=counts,
        lineage_ref=lineage,
        previous_decision_ref=previous,
    )


def static_network_target_block_code(url: str) -> str | None:
    """Return a static parser/address blocker without requiring DNS."""

    decision = evaluate_network_target_safety(
        url,
        stage=NetworkTargetSafetyStage.ADMISSION_PRE_ROUTE,
        transport_mode=NetworkTargetTransportMode.PROVIDER_MEDIATED,
        fact_kind=NetworkTargetFactKind.REQUESTED,
        require_hostname_resolution=False,
    )
    return decision.blocker_code


def resolution_snapshot_for_url(
    url: str,
    snapshots: Sequence[NetworkTargetResolutionSnapshotV1],
) -> NetworkTargetResolutionSnapshotV1 | None:
    canonical_snapshots = tuple(
        _canonical_resolution_snapshot(snapshot) for snapshot in snapshots
    )
    if len(canonical_snapshots) > MAX_NETWORK_TARGET_RESOLUTION_SNAPSHOTS:
        raise ValueError("network_target_resolution_snapshot_bundle_overflow")
    try:
        target = _parse_target(url)
    except _TargetParseBlocked:
        return None
    host = target.get("canonical_host")
    matches = [
        snapshot
        for snapshot in canonical_snapshots
        if snapshot.canonical_host == host
    ]
    if len(matches) > 1:
        raise ValueError("duplicate_network_target_resolution_snapshot")
    return matches[0] if matches else None


def canonical_resolution_snapshot_bundle(
    snapshots: Sequence[NetworkTargetResolutionSnapshotV1],
    *,
    expected_target_urls: Sequence[str] | None = None,
) -> tuple[dict[str, Any], ...]:
    if len(snapshots) > MAX_NETWORK_TARGET_RESOLUTION_SNAPSHOTS:
        raise ValueError("network_target_resolution_snapshot_bundle_overflow")
    expected_hosts: set[str] | None = None
    if expected_target_urls is not None:
        if len(expected_target_urls) > MAX_NETWORK_TARGET_RESOLUTION_SNAPSHOTS:
            raise ValueError("network_target_resolution_target_bundle_overflow")
        expected_hosts = set()
        for target_url in expected_target_urls:
            try:
                target = _parse_target(target_url)
            except _TargetParseBlocked:
                continue
            if target.get("host_posture") == "hostname":
                expected_hosts.add(str(target["canonical_host"]))
    by_host: dict[str, NetworkTargetResolutionSnapshotV1] = {}
    for snapshot in snapshots:
        canonical_snapshot = _canonical_resolution_snapshot(snapshot)
        if (
            expected_hosts is not None
            and canonical_snapshot.canonical_host not in expected_hosts
        ):
            raise ValueError("unrelated_network_target_resolution_snapshot")
        if canonical_snapshot.canonical_host in by_host:
            raise ValueError("duplicate_network_target_resolution_snapshot")
        by_host[canonical_snapshot.canonical_host] = canonical_snapshot
    return tuple(by_host[host].to_dict() for host in sorted(by_host))


def resolution_snapshots_from_bundle(
    value: Sequence[Mapping[str, Any]] | None,
) -> tuple[NetworkTargetResolutionSnapshotV1, ...]:
    snapshots = tuple(
        NetworkTargetResolutionSnapshotV1.from_dict(item) for item in (value or ())
    )
    canonical_resolution_snapshot_bundle(snapshots)
    return snapshots


def _canonical_resolution_snapshot(
    snapshot: NetworkTargetResolutionSnapshotV1,
) -> NetworkTargetResolutionSnapshotV1:
    if not isinstance(snapshot, NetworkTargetResolutionSnapshotV1):
        raise ValueError("typed_network_target_resolution_snapshot_required")
    return NetworkTargetResolutionSnapshotV1.from_dict(snapshot.to_dict())


def _parse_target(value: str) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        raise _TargetParseBlocked("target_url_empty")
    if len(value) > MAX_NETWORK_TARGET_URL_CHARACTERS:
        raise _TargetParseBlocked("target_url_too_long")
    if value != value.strip():
        raise _TargetParseBlocked("target_url_surrounding_whitespace")
    if any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in value):
        raise _TargetParseBlocked("target_url_control_character")
    if any(character.isspace() for character in value):
        raise _TargetParseBlocked("target_url_embedded_whitespace")
    if "\\" in value:
        raise _TargetParseBlocked("target_url_authority_delimiter_confusion")
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise _TargetParseBlocked("target_url_malformed") from exc
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise _TargetParseBlocked("target_url_scheme_unsupported")
    if not parsed.netloc:
        raise _TargetParseBlocked("target_url_host_missing")
    if "@" in parsed.netloc or parsed.username is not None or parsed.password is not None:
        raise _TargetParseBlocked("target_url_credentials_forbidden")
    try:
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise _TargetParseBlocked("target_url_port_or_ipv6_malformed") from exc
    if not host:
        raise _TargetParseBlocked("target_url_host_missing")
    if "%" in parsed.netloc or "%" in host:
        raise _TargetParseBlocked("target_url_encoded_host_confusion")
    if unicodedata.normalize("NFC", host) != host or not host.isascii():
        raise _TargetParseBlocked("target_url_idna_unicode_ambiguous")
    host = host.casefold()
    if host.endswith("."):
        host = host[:-1]
    if not host or ".." in host:
        raise _TargetParseBlocked("target_url_host_malformed")
    if port is not None and not 1 <= port <= 65_535:
        raise _TargetParseBlocked("target_url_port_invalid")
    scheme = parsed.scheme.casefold()
    default_port = 443 if scheme == "https" else 80
    normalized_port = None if port in {None, default_port} else port
    port_posture = (
        "default_implicit"
        if port is None
        else "default_explicit_normalized"
        if port == default_port
        else "nondefault_explicit"
    )

    literal: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
    if ":" in host:
        if "%" in host:
            raise _TargetParseBlocked("target_url_ipv6_zone_identifier_forbidden")
        try:
            literal = ipaddress.IPv6Address(host)
        except ValueError as exc:
            raise _TargetParseBlocked("target_url_ipv6_malformed") from exc
    else:
        try:
            literal = ipaddress.IPv4Address(host)
        except ValueError:
            literal = None
        if literal is None and _numeric_looking_host(host):
            raise _TargetParseBlocked("target_url_ambiguous_numeric_host")

    if literal is not None:
        canonical_host = literal.compressed.casefold()
        classification, effective_family = _classify_address(literal)
        host_posture = "literal_ip"
        family = effective_family
    else:
        canonical_host = _canonical_dns_host(host)
        if canonical_host == "localhost" or canonical_host.endswith(".localhost"):
            raise _TargetParseBlocked("target_url_localhost_forbidden")
        if "." not in canonical_host:
            raise _TargetParseBlocked("target_url_single_label_host_forbidden")
        classification = None
        host_posture = "hostname"
        family = "resolver_dependent"

    authority_host = (
        f"[{canonical_host}]" if ":" in canonical_host else canonical_host
    )
    authority = (
        f"{authority_host}:{normalized_port}"
        if normalized_port is not None
        else authority_host
    )
    normalized = urlunsplit(
        SplitResult(
            scheme,
            authority,
            parsed.path or "/",
            parsed.query,
            "",
        )
    )
    return {
        "normalized_target_url": normalized,
        "normalized_target_digest": stable_json_digest(
            {"normalized_target_url": normalized}
        ),
        "scheme": scheme,
        "canonical_host": canonical_host,
        "normalized_port": normalized_port,
        "port_posture": port_posture,
        "host_posture": host_posture,
        "address_family_posture": family,
        "literal_classification": classification,
        "fragment_posture": (
            "fragment_stripped_from_source_identity"
            if parsed.fragment
            else "fragment_absent"
        ),
    }


def _canonical_dns_host(host: str) -> str:
    if len(host) > 253:
        raise _TargetParseBlocked("target_url_host_too_long")
    labels = host.split(".")
    for label in labels:
        if not label or len(label) > 63 or not _ASCII_DNS_LABEL.fullmatch(label):
            raise _TargetParseBlocked("target_url_idna_or_dns_label_invalid")
        if label.startswith("xn--"):
            try:
                decoded = label.encode("ascii").decode("idna")
                if decoded.encode("idna").decode("ascii").casefold() != label:
                    raise UnicodeError
            except UnicodeError as exc:
                raise _TargetParseBlocked("target_url_idna_alabel_invalid") from exc
    return host


def _numeric_looking_host(host: str) -> bool:
    if host and all(character in "0123456789abcdefABCDEFxX.+-" for character in host):
        labels = host.split(".")
        if all(label and _NUMERIC_TOKEN.fullmatch(label) for label in labels):
            return True
        if len(labels) <= 4 and any(character.isdigit() for character in host):
            return True
    return False


def _canonical_snapshot_host(value: Any) -> str:
    host = str(value or "").strip().casefold()
    if host.endswith("."):
        host = host[:-1]
    if not host or not host.isascii() or "%" in host:
        raise ValueError("network_target_resolution_snapshot_host_invalid")
    try:
        return ipaddress.ip_address(host).compressed.casefold()
    except ValueError:
        try:
            return _canonical_dns_host(host)
        except _TargetParseBlocked as exc:
            raise ValueError("network_target_resolution_snapshot_host_invalid") from exc


def _classify_address(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> tuple[str, str]:
    effective: ipaddress.IPv4Address | ipaddress.IPv6Address = address
    family = "ipv4" if address.version == 4 else "ipv6"
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        effective = address.ipv4_mapped
        family = "ipv4_mapped_ipv6_effective_ipv4"
    if effective.is_unspecified:
        return "unspecified", family
    if effective.is_loopback:
        return "loopback", family
    if effective.is_link_local:
        return "link_local", family
    if effective.is_multicast:
        return "multicast", family
    if effective.is_reserved:
        return "reserved", family
    if effective.is_private:
        return "private_network", family
    if not effective.is_global:
        return "non_global", family
    return "public", family


def _address_entry(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> dict[str, Any]:
    normalized = address.compressed.casefold()
    classification, family = _classify_address(address)
    digest = stable_json_digest({"normalized_address": normalized})
    return {
        "address_digest": digest,
        "public_address": normalized if classification == "public" else None,
        "address_family": "ipv4" if address.version == 4 else "ipv6",
        "effective_address_family": family,
        "classification": classification,
        "raw_private_network_data_retained": False,
    }


def _validated_address_entry(value: Mapping[str, Any]) -> dict[str, Any]:
    raw = dict(value or {})
    expected = {
        "address_digest",
        "public_address",
        "address_family",
        "effective_address_family",
        "classification",
        "raw_private_network_data_retained",
    }
    if set(raw) != expected or raw.get("raw_private_network_data_retained") is not False:
        raise ValueError("network_target_resolution_address_entry_invalid")
    classification = str(raw.get("classification") or "")
    if classification not in _PROHIBITED_ADDRESS_CLASSIFICATIONS | {"public"}:
        raise ValueError("network_target_resolution_address_classification_invalid")
    public_address = raw.get("public_address")
    if classification == "public":
        try:
            address = ipaddress.ip_address(str(public_address or ""))
        except ValueError as exc:
            raise ValueError("network_target_resolution_public_address_invalid") from exc
        expected_entry = _address_entry(address)
        if raw != expected_entry:
            raise ValueError("network_target_resolution_public_address_mismatch")
    elif public_address is not None:
        raise ValueError("network_target_resolution_private_address_retained")
    digest = str(raw.get("address_digest") or "")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("network_target_resolution_address_digest_invalid")
    return raw


def _classification_counts(
    entries: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        classification = str(entry.get("classification") or "indeterminate")
        counts[classification] = counts.get(classification, 0) + 1
    return dict(sorted(counts.items()))


def _persisted_decision_canonical_host(
    *, blocker_code: str | None, canonical_host: Any
) -> str | None:
    if str(blocker_code or "").startswith("target_address_"):
        return None
    return str(canonical_host) if canonical_host is not None else None


def _decision_digest_core(
    *,
    stage: str,
    status: str,
    blocker_code: str | None,
    transport_mode: str,
    fact_kind: str,
    supplied_url_digest: str,
    normalized_target_digest: str | None,
    scheme: str | None,
    canonical_host: str | None,
    normalized_port: int | None,
    port_posture: str,
    host_posture: str,
    address_family_posture: str,
    fragment_posture: str,
    resolver_snapshot_ref: Mapping[str, Any],
    address_classification_counts: Mapping[str, int],
    lineage_ref: Mapping[str, str],
    previous_decision_ref: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": NETWORK_TARGET_SAFETY_DECISION_SCHEMA_VERSION,
        "policy_ref": network_target_safety_policy_ref(),
        "stage": stage,
        "status": status,
        "blocker_code": blocker_code,
        "transport_mode": transport_mode,
        "fact_kind": fact_kind,
        "supplied_url_digest": supplied_url_digest,
        "normalized_target_digest": normalized_target_digest,
        "scheme": scheme,
        "canonical_host": canonical_host,
        "normalized_port": normalized_port,
        "port_posture": port_posture,
        "host_posture": host_posture,
        "address_family_posture": address_family_posture,
        "fragment_posture": fragment_posture,
        "resolver_snapshot_ref": dict(resolver_snapshot_ref),
        "address_classification_counts": dict(address_classification_counts),
        "lineage_ref": dict(lineage_ref),
        "previous_decision_ref": dict(previous_decision_ref),
        "raw_dns_retained": False,
        "raw_private_network_data_retained": False,
        "credentials_retained": False,
        "unrelated_host_data_retained": False,
        "all_downstream_authority_granted": False,
    }


def _validated_sha256(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(code)
    return value


def _validated_optional_sha256(value: Any, code: str) -> str | None:
    if value is None:
        return None
    return _validated_sha256(value, code)


def _validated_optional_token(
    value: Any, *, limit: int, code: str
) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > limit
    ):
        raise ValueError(code)
    return value


def _validated_choice(
    value: Any, allowed: frozenset[str], code: str
) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(code)
    return value


def _validated_enum_value(
    value: Any, enum_type: type[Enum], code: str
) -> str:
    try:
        return enum_type(value).value
    except (TypeError, ValueError) as exc:
        raise ValueError(code) from exc


def _validated_optional_canonical_host(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 253:
        raise ValueError("network_target_safety_decision_host_invalid")
    try:
        canonical = _canonical_snapshot_host(value)
    except ValueError as exc:
        raise ValueError("network_target_safety_decision_host_invalid") from exc
    if canonical != value:
        raise ValueError("network_target_safety_decision_host_noncanonical")
    return canonical


def _validated_resolution_snapshot_ref(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(
            "network_target_safety_decision_resolver_ref_mapping_required"
        )
    raw = dict(value)
    if not raw:
        return {}
    if set(raw) != _RESOLUTION_SNAPSHOT_REF_FIELDS:
        raise ValueError("network_target_safety_decision_resolver_ref_fields_invalid")
    if (
        raw.get("raw_dns_retained") is not False
        or raw.get("raw_private_network_data_retained") is not False
    ):
        raise ValueError("network_target_safety_decision_resolver_ref_raw_data_invalid")
    digest = _validated_sha256(
        raw.get("snapshot_digest"),
        "network_target_safety_decision_resolver_digest_invalid",
    )
    if raw.get("snapshot_id") != f"network-target-resolution:{digest[:24]}":
        raise ValueError("network_target_safety_decision_resolver_identity_invalid")
    host = _validated_optional_canonical_host(raw.get("canonical_host"))
    if host is None:
        raise ValueError("network_target_safety_decision_resolver_host_invalid")
    status = raw.get("resolution_status")
    if status not in _RESOLUTION_STATUSES:
        raise ValueError("network_target_safety_decision_resolver_status_invalid")
    count = raw.get("address_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("network_target_safety_decision_resolver_count_invalid")
    if (
        (status == "resolved" and not 1 <= count <= MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES)
        or (status == "empty" and count != 0)
        or (status == "overflow" and count <= MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES)
        or (
            status not in {"resolved", "empty", "overflow"}
            and count > MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES
        )
    ):
        raise ValueError("network_target_safety_decision_resolver_count_invalid")
    return {
        "snapshot_id": str(raw["snapshot_id"]),
        "snapshot_digest": digest,
        "canonical_host": host,
        "resolution_status": str(status),
        "address_count": count,
        "raw_dns_retained": False,
        "raw_private_network_data_retained": False,
    }


def _validated_classification_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValueError(
            "network_target_safety_decision_address_counts_mapping_required"
        )
    raw = dict(value)
    allowed = _PROHIBITED_ADDRESS_CLASSIFICATIONS | {"public"}
    if len(raw) > len(allowed) or any(key not in allowed for key in raw):
        raise ValueError("network_target_safety_decision_address_counts_invalid")
    result: dict[str, int] = {}
    for key, count in raw.items():
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or not 1 <= count <= MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES
        ):
            raise ValueError(
                "network_target_safety_decision_address_count_invalid"
            )
        result[str(key)] = count
    if sum(result.values()) > MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES:
        raise ValueError("network_target_safety_decision_address_counts_overflow")
    return dict(sorted(result.items()))


def _validated_lineage_ref(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("network_target_safety_decision_lineage_mapping_required")
    raw = dict(value)
    if len(raw) > len(_LINEAGE_KEYS) or any(key not in _LINEAGE_KEYS for key in raw):
        raise ValueError("network_target_safety_decision_lineage_fields_invalid")
    result: dict[str, str] = {}
    for key, item in raw.items():
        if (
            not isinstance(key, str)
            or not isinstance(item, str)
            or not item
            or item != item.strip()
            or len(item) > 300
        ):
            raise ValueError("network_target_safety_decision_lineage_value_invalid")
        result[key] = item
    return dict(sorted(result.items()))


def _validated_previous_decision_ref(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(
            "network_target_safety_previous_decision_ref_mapping_required"
        )
    raw = dict(value)
    if any(key not in _DECISION_REF_FIELDS for key in raw):
        raise ValueError("network_target_safety_previous_decision_ref_fields_invalid")
    if "lineage_ref" in raw:
        raw["lineage_ref"] = _validated_lineage_ref(raw["lineage_ref"])
    for field in (
        "decision_digest",
        "policy_digest",
        "supplied_url_digest",
        "normalized_target_digest",
        "resolver_snapshot_digest",
    ):
        if field in raw:
            raw[field] = _validated_optional_sha256(
                raw[field],
                "network_target_safety_previous_decision_digest_invalid",
            )
    for field, limit in (
        ("decision_id", 300),
        ("policy_version", 100),
        ("stage", 80),
        ("status", 80),
        ("blocker_code", 220),
        ("transport_mode", 100),
        ("fact_kind", 100),
        ("canonical_host", 260),
        ("resolver_snapshot_id", 300),
    ):
        if field in raw:
            raw[field] = _validated_optional_token(
                raw[field],
                limit=limit,
                code="network_target_safety_previous_decision_token_invalid",
            )
    for field in (
        "raw_dns_retained",
        "raw_private_network_data_retained",
        "credentials_retained",
        "all_downstream_authority_granted",
    ):
        if field in raw and raw[field] is not False:
            raise ValueError(
                "network_target_safety_previous_decision_authority_invalid"
            )
    return {key: raw[key] for key in sorted(raw)}


def _bounded_lineage_ref(value: Mapping[str, Any] | None) -> dict[str, str]:
    source = dict(value or {})
    return {
        key: str(source[key]).strip()[:300]
        for key in sorted(set(source) & _LINEAGE_KEYS)
        if str(source[key]).strip()
    }


def _bounded_decision_ref(value: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(value or {})
    allowed = {
        "decision_id",
        "decision_digest",
        "policy_version",
        "policy_digest",
        "stage",
        "status",
        "blocker_code",
        "transport_mode",
        "fact_kind",
        "supplied_url_digest",
        "normalized_target_digest",
        "canonical_host",
        "resolver_snapshot_id",
        "resolver_snapshot_digest",
        "lineage_ref",
        "raw_dns_retained",
        "raw_private_network_data_retained",
        "credentials_retained",
        "all_downstream_authority_granted",
    }
    return {key: source[key] for key in sorted(set(source) & allowed)}


__all__ = [
    "MAX_NETWORK_TARGET_RESOLUTION_ADDRESSES",
    "MAX_NETWORK_TARGET_RESOLUTION_SNAPSHOTS",
    "NETWORK_TARGET_SAFETY_POLICY_VERSION",
    "NetworkTargetFactKind",
    "NetworkTargetResolutionSnapshotV1",
    "NetworkTargetSafetyDecisionV1",
    "NetworkTargetSafetyStage",
    "NetworkTargetSafetyStatus",
    "NetworkTargetTransportMode",
    "canonical_resolution_snapshot_bundle",
    "evaluate_network_target_safety",
    "network_target_safety_policy_ref",
    "resolution_snapshot_for_url",
    "resolution_snapshots_from_bundle",
    "static_network_target_block_code",
]
