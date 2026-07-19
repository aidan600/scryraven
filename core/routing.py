"""Sole policy owner for provider-capability routing."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
from typing import Mapping, Optional, Sequence


class AcquisitionCapability(str, Enum):
    DISCOVER = "DISCOVER"
    READ = "READ"
    FOCUSED_EXTRACT = "FOCUSED_EXTRACT"
    MAP_SITE = "MAP_SITE"
    CRAWL_SITE = "CRAWL_SITE"
    PROVIDER_SYNTHESIS = "PROVIDER_SYNTHESIS"


class DiscoverQualifier(str, Enum):
    GENERAL = "general"
    DOMAIN_TARGETED = "domain_targeted"
    ACADEMIC_TECHNICAL_SEMANTIC = "academic_technical_semantic"
    LIGHTWEIGHT_DISAMBIGUATION = "lightweight_disambiguation"
    INDEPENDENT_INDEX = "independent_index"


class RouteFidelity(str, Enum):
    EXACT = "exact"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


PROVIDER_NAMES = ("tavily", "linkup", "exa", "serper", "brave")

ACQUISITION_ROUTING_POLICY_SCHEMA_VERSION = (
    "acquisition_routing_policy_descriptor_v1"
)
ACQUISITION_ROUTING_POLICY_REVISION = (
    "exact_url_network_target_safety_owner_01"
)
ACQUISITION_ROUTING_SELECTION_ALGORITHM_REVISION = (
    "first_reachable_and_target_safety_eligible_preference_v1"
)

UNTRUSTED_EXACT_URL_TARGET_CLASS = "untrusted_exact_url"
TARGET_SAFETY_NOT_APPLICABLE = "target_safety_not_applicable"
_DYNAMIC_CONTENT_TARGET_CAPABILITIES = frozenset(
    {
        AcquisitionCapability.READ,
        AcquisitionCapability.FOCUSED_EXTRACT,
        AcquisitionCapability.MAP_SITE,
        AcquisitionCapability.CRAWL_SITE,
    }
)
PROVIDER_TARGET_SAFETY_ELIGIBILITY_SCHEMA_VERSION = (
    "provider_target_safety_eligibility_snapshot_v1"
)
PROVIDER_TARGET_SAFETY_ELIGIBILITY_POLICY_VERSION = (
    "provider_untrusted_exact_url_eligibility_v1"
)
OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_AUTHORITY_SCHEMA_VERSION = (
    "offline_provider_target_safety_validation_authority_v1"
)
OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_POSTURE = "PRODUCT-unreachable"


@dataclass(frozen=True, slots=True)
class GeneralDeepAuthorization:
    """Explicit bounded authorization facts for non-Scrutineer Linkup Deep."""

    parent_standard_acquisition_job_id: str
    acquisition_lineage_id: str
    obligation_reference: str
    sequential_acquisition_required: bool
    premium_authorized: bool
    remaining_run_budget: int
    general_escalations_used: int
    queries: tuple[str, ...]
    max_results_per_query: int
    output_type: str = "searchResults"

    @property
    def valid(self) -> bool:
        try:
            remaining_budget = int(self.remaining_run_budget)
            escalations_used = int(self.general_escalations_used)
            max_results = int(self.max_results_per_query)
        except (TypeError, ValueError):
            return False
        return bool(
            str(self.parent_standard_acquisition_job_id).strip()
            and str(self.acquisition_lineage_id).strip()
            and str(self.obligation_reference).strip()
            and self.sequential_acquisition_required
            and self.premium_authorized
            and remaining_budget > 0
            and escalations_used == 0
            and 1 <= len(self.queries) <= 2
            and all(str(query).strip() for query in self.queries)
            and 1 <= max_results <= 5
            and self.output_type == "searchResults"
        )

    def to_trace(self) -> dict[str, object]:
        return {
            "parent_standard_acquisition_job_id": self.parent_standard_acquisition_job_id,
            "acquisition_lineage_id": self.acquisition_lineage_id,
            "obligation_reference": self.obligation_reference,
            "sequential_acquisition_required": self.sequential_acquisition_required,
            "premium_authorized": self.premium_authorized,
            "remaining_run_budget": self.remaining_run_budget,
            "general_escalations_used": self.general_escalations_used,
            "query_count": len(self.queries),
            "max_results_per_query": self.max_results_per_query,
            "output_type": self.output_type,
            "authorization_valid": self.valid,
        }


@dataclass(frozen=True, slots=True)
class ProviderAvailability:
    """Boolean-only availability facts for the bounded provider set."""

    tavily: bool = False
    linkup: bool = False
    exa: bool = False
    serper: bool = False
    brave: bool = False

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> "ProviderAvailability":
        source = values or {}
        return cls(
            **{
                provider: bool(source.get(provider))
                for provider in PROVIDER_NAMES
            }
        )

    @classmethod
    def from_boolean_mapping(
        cls, values: Mapping[str, object] | None
    ) -> "ProviderAvailability":
        """Validate an exact boolean-only acquisition availability snapshot."""

        source = dict(values or {})
        unknown = set(source).difference(PROVIDER_NAMES)
        if unknown:
            raise ValueError(
                f"provider availability has unknown fields: {sorted(unknown)}"
            )
        for provider, value in source.items():
            if not isinstance(value, bool):
                raise ValueError(
                    f"provider availability {provider!r} must be boolean"
                )
        return cls(**{provider: source.get(provider, False) for provider in PROVIDER_NAMES})

    def to_mapping(self) -> dict[str, bool]:
        return {provider: bool(getattr(self, provider)) for provider in PROVIDER_NAMES}

    def is_available(self, provider: str) -> bool:
        return bool(self.to_mapping().get(str(provider).strip().lower(), False))


@dataclass(frozen=True, slots=True)
class ProviderCapabilityRequest:
    capability: AcquisitionCapability
    qualifier: DiscoverQualifier | None = None
    domain_constraints: tuple[str, ...] = ()
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    source_of_record_domain_constraints: tuple[str, ...] = ()
    derivation_reason: str = "explicit_capability_request"
    general_deep_requested: bool = False
    general_deep_authorization: GeneralDeepAuthorization | None = None
    target_class: str = TARGET_SAFETY_NOT_APPLICABLE

    def to_trace(self) -> dict[str, object]:
        return {
            "capability": self.capability.value,
            "qualifier": self.qualifier.value if self.qualifier is not None else None,
            "domain_constraints": list(self.domain_constraints),
            "include_domains": list(self.include_domains),
            "exclude_domains": list(self.exclude_domains),
            "source_of_record_domain_constraints": list(
                self.source_of_record_domain_constraints
            ),
            "derivation_reason": self.derivation_reason,
            "general_deep_requested": self.general_deep_requested,
            "general_deep_authorization": (
                self.general_deep_authorization.to_trace()
                if self.general_deep_authorization is not None
                else None
            ),
            "target_class": self.target_class,
        }


@dataclass(frozen=True, slots=True)
class ProviderCapabilityCatalogEntry:
    provider: str
    capability: AcquisitionCapability
    qualifier: DiscoverQualifier | None
    operation: str
    variant: str
    output_type: str
    vendor_operation_known: bool
    adapter_installed: bool
    ordinary_product_enabled: bool
    returned_material_class: str
    authority_posture: str


@dataclass(frozen=True, slots=True)
class ProviderCapabilityCatalogStatus:
    entry: ProviderCapabilityCatalogEntry
    currently_available: bool
    typed_runtime_reachable: bool
    ordinary_product_reachable: bool
    currently_reachable: bool

    def __getattr__(self, name: str) -> object:
        if name in ProviderCapabilityCatalogEntry.__dataclass_fields__:
            return getattr(self.entry, name)
        raise AttributeError(name)

    def to_trace(self) -> dict[str, object]:
        return {
            "provider": self.entry.provider,
            "capability": self.entry.capability.value,
            "qualifier": self.entry.qualifier.value if self.entry.qualifier is not None else None,
            "operation": self.entry.operation,
            "variant": self.entry.variant,
            "output_type": self.entry.output_type,
            "vendor_operation_known": self.entry.vendor_operation_known,
            "adapter_installed": self.entry.adapter_installed,
            "ordinary_product_enabled": self.entry.ordinary_product_enabled,
            "currently_available": self.currently_available,
            "typed_runtime_reachable": self.typed_runtime_reachable,
            "ordinary_product_reachable": self.ordinary_product_reachable,
            "currently_reachable": self.currently_reachable,
            "returned_material_class": self.entry.returned_material_class,
            "authority_posture": self.entry.authority_posture,
        }


def provider_operation_identity(
    *,
    provider: str,
    capability: AcquisitionCapability | str,
    operation: str,
    variant: str,
) -> str:
    capability_value = (
        capability.value
        if isinstance(capability, AcquisitionCapability)
        else str(capability)
    )
    return ":".join(
        (
            str(provider).strip().casefold(),
            capability_value.strip().upper(),
            str(operation).strip().casefold(),
            str(variant).strip().casefold(),
        )
    )


_UNTRUSTED_EXACT_URL_OPERATION_EVIDENCE: Mapping[str, str] = {
    provider_operation_identity(
        provider="linkup",
        capability=AcquisitionCapability.READ,
        operation="fetch",
        variant="known_url",
    ): "committed_public_target_guarantee_and_final_target_lineage_not_established",
    provider_operation_identity(
        provider="tavily",
        capability=AcquisitionCapability.READ,
        operation="extract",
        variant="basic",
    ): "committed_public_target_guarantee_and_final_target_lineage_not_established",
    provider_operation_identity(
        provider="tavily",
        capability=AcquisitionCapability.FOCUSED_EXTRACT,
        operation="extract",
        variant="query_focused",
    ): "committed_public_target_guarantee_and_final_target_lineage_not_established",
    provider_operation_identity(
        provider="tavily",
        capability=AcquisitionCapability.MAP_SITE,
        operation="map",
        variant="bounded",
    ): "committed_public_target_guarantee_and_final_target_lineage_not_established",
    provider_operation_identity(
        provider="tavily",
        capability=AcquisitionCapability.CRAWL_SITE,
        operation="crawl",
        variant="bounded",
    ): "committed_public_target_guarantee_and_final_target_lineage_not_established",
}


@dataclass(frozen=True, slots=True)
class OfflineProviderTargetSafetyValidationAuthorityV1:
    """Typed, product-unreachable authority for injected eligibility fixtures.

    The fixture can exercise pre-dispatch route-alternative mechanics in offline
    validation.  It cannot be passed to the ordinary product routing entrypoint,
    and every operation identity remains bounded by the code-owned evidence
    catalog above.
    """

    operation_eligibility: tuple[tuple[str, bool], ...]
    fixture_id: str
    fixture_digest: str
    authority_posture: str = OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_POSTURE
    product_reachable: bool = False
    schema_version: str = (
        OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_AUTHORITY_SCHEMA_VERSION
    )

    @classmethod
    def create(
        cls,
        operation_eligibility: Mapping[str, object],
    ) -> "OfflineProviderTargetSafetyValidationAuthorityV1":
        fixture = dict(operation_eligibility)
        unknown = set(fixture).difference(_UNTRUSTED_EXACT_URL_OPERATION_EVIDENCE)
        if unknown:
            raise ValueError(
                "offline provider target-safety fixture has unknown operation "
                f"identities: {sorted(unknown)}"
            )
        if any(not isinstance(value, bool) for value in fixture.values()):
            raise ValueError(
                "offline provider target-safety fixture values must be boolean"
            )
        entries = tuple(
            sorted((identity, value) for identity, value in fixture.items())
        )
        core = {
            "schema_version": (
                OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_AUTHORITY_SCHEMA_VERSION
            ),
            "authority_posture": OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_POSTURE,
            "product_reachable": False,
            "operation_eligibility": dict(entries),
        }
        digest = sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            operation_eligibility=entries,
            fixture_id=f"offline-provider-target-safety:{digest[:24]}",
            fixture_digest=digest,
        )

    def validated_mapping(self) -> dict[str, bool]:
        if (
            self.schema_version
            != OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_AUTHORITY_SCHEMA_VERSION
            or self.authority_posture
            != OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_POSTURE
            or self.product_reachable
        ):
            raise ValueError(
                "offline provider target-safety validation authority is invalid"
            )
        recreated = type(self).create(dict(self.operation_eligibility))
        if (
            recreated.operation_eligibility != self.operation_eligibility
            or recreated.fixture_id != self.fixture_id
            or recreated.fixture_digest != self.fixture_digest
        ):
            raise ValueError(
                "offline provider target-safety validation authority is stale or forged"
            )
        return dict(self.operation_eligibility)

    def ref(self) -> dict[str, object]:
        self.validated_mapping()
        return {
            "schema_version": self.schema_version,
            "fixture_id": self.fixture_id,
            "fixture_digest": self.fixture_digest,
            "authority_posture": self.authority_posture,
            "product_reachable": self.product_reachable,
        }


@dataclass(frozen=True, slots=True)
class ProviderTargetSafetyEligibilitySnapshot:
    """Code-owned route eligibility for one dynamic target class.

    Ordinary creation is code-owned.  Offline fixtures enter only through the
    separate product-unreachable validation authority and routing entrypoint.
    """

    target_class: str
    operation_eligibility: Mapping[str, bool]
    operation_blockers: Mapping[str, str]
    source_posture: str
    authority_posture: str
    product_reachable: bool
    offline_validation_authority_ref: Mapping[str, object]
    snapshot_id: str
    snapshot_digest: str
    schema_version: str = PROVIDER_TARGET_SAFETY_ELIGIBILITY_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        target_class: str,
    ) -> "ProviderTargetSafetyEligibilitySnapshot":
        normalized_class = str(target_class or TARGET_SAFETY_NOT_APPLICABLE).strip()
        if normalized_class == UNTRUSTED_EXACT_URL_TARGET_CLASS:
            eligibility = {
                identity: False
                for identity in sorted(_UNTRUSTED_EXACT_URL_OPERATION_EVIDENCE)
            }
            blockers = {
                identity: _UNTRUSTED_EXACT_URL_OPERATION_EVIDENCE[identity]
                for identity in eligibility
            }
            source = "code_owned_repository_evidence"
        else:
            eligibility = {}
            blockers = {}
            source = TARGET_SAFETY_NOT_APPLICABLE
        return cls._from_facts(
            target_class=normalized_class,
            eligibility=eligibility,
            blockers=blockers,
            source_posture=source,
            authority_posture="PRODUCT",
            product_reachable=True,
            offline_validation_authority_ref={},
        )

    @classmethod
    def for_offline_validation(
        cls,
        *,
        target_class: str,
        authority: OfflineProviderTargetSafetyValidationAuthorityV1,
    ) -> "ProviderTargetSafetyEligibilitySnapshot":
        normalized_class = str(target_class or TARGET_SAFETY_NOT_APPLICABLE).strip()
        if normalized_class != UNTRUSTED_EXACT_URL_TARGET_CLASS:
            raise ValueError(
                "offline provider target-safety validation requires the untrusted "
                "exact URL target class"
            )
        fixture = authority.validated_mapping()
        eligibility = {
            identity: bool(fixture.get(identity, False))
            for identity in sorted(_UNTRUSTED_EXACT_URL_OPERATION_EVIDENCE)
        }
        blockers = {
            identity: (
                ""
                if eligibility[identity]
                else _UNTRUSTED_EXACT_URL_OPERATION_EVIDENCE[identity]
            )
            for identity in eligibility
        }
        return cls._from_facts(
            target_class=normalized_class,
            eligibility=eligibility,
            blockers=blockers,
            source_posture="injected_offline_validation_fixture",
            authority_posture=OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_POSTURE,
            product_reachable=False,
            offline_validation_authority_ref=authority.ref(),
        )

    @classmethod
    def _from_facts(
        cls,
        *,
        target_class: str,
        eligibility: Mapping[str, bool],
        blockers: Mapping[str, str],
        source_posture: str,
        authority_posture: str,
        product_reachable: bool,
        offline_validation_authority_ref: Mapping[str, object],
    ) -> "ProviderTargetSafetyEligibilitySnapshot":
        core = {
            "schema_version": PROVIDER_TARGET_SAFETY_ELIGIBILITY_SCHEMA_VERSION,
            "policy_version": PROVIDER_TARGET_SAFETY_ELIGIBILITY_POLICY_VERSION,
            "target_class": target_class,
            "operation_eligibility": eligibility,
            "operation_blockers": blockers,
            "source_posture": source_posture,
            "authority_posture": authority_posture,
            "product_reachable": product_reachable,
            "offline_validation_authority_ref": dict(
                offline_validation_authority_ref
            ),
            "configuration_owned": False,
            "requester_preference_owned": False,
        }
        digest = sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            target_class=target_class,
            operation_eligibility=dict(eligibility),
            operation_blockers=dict(blockers),
            source_posture=source_posture,
            authority_posture=authority_posture,
            product_reachable=product_reachable,
            offline_validation_authority_ref=dict(
                offline_validation_authority_ref
            ),
            snapshot_id=f"provider-target-safety-eligibility:{digest[:24]}",
            snapshot_digest=digest,
        )

    def eligibility_for(self, status: "ProviderCapabilityCatalogStatus") -> bool:
        if self.target_class != UNTRUSTED_EXACT_URL_TARGET_CLASS:
            return True
        identity = provider_operation_identity(
            provider=status.provider,
            capability=status.capability,
            operation=status.operation,
            variant=status.variant,
        )
        return bool(self.operation_eligibility.get(identity, False))

    def blocker_for(self, status: "ProviderCapabilityCatalogStatus") -> str | None:
        if self.target_class != UNTRUSTED_EXACT_URL_TARGET_CLASS:
            return None
        identity = provider_operation_identity(
            provider=status.provider,
            capability=status.capability,
            operation=status.operation,
            variant=status.variant,
        )
        return self.operation_blockers.get(identity) or None

    def ref(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_version": PROVIDER_TARGET_SAFETY_ELIGIBILITY_POLICY_VERSION,
            "snapshot_id": self.snapshot_id,
            "snapshot_digest": self.snapshot_digest,
            "target_class": self.target_class,
            "source_posture": self.source_posture,
            "authority_posture": self.authority_posture,
            "product_reachable": self.product_reachable,
            "offline_validation_authority_ref": dict(
                self.offline_validation_authority_ref
            ),
            "configuration_owned": False,
            "requester_preference_owned": False,
        }

    def to_trace(self) -> dict[str, object]:
        return {
            **self.ref(),
            "operation_eligibility": dict(self.operation_eligibility),
            "operation_blockers": dict(self.operation_blockers),
        }


@dataclass(frozen=True, slots=True)
class ProviderFallbackCandidate:
    """A descriptive candidate that never authorizes dispatch."""

    provider: str
    operation: str
    variant: str
    output_type: str
    fidelity: RouteFidelity
    vendor_operation_known: bool
    adapter_installed: bool
    ordinary_product_enabled: bool
    currently_available: bool
    typed_runtime_reachable: bool
    ordinary_product_reachable: bool
    currently_reachable: bool
    returned_material_class: str
    authority_posture: str
    target_safety_eligible: bool | None = None
    target_safety_blocker: str | None = None

    @classmethod
    def from_status(
        cls,
        status: ProviderCapabilityCatalogStatus,
        *,
        fidelity: RouteFidelity,
        target_safety_eligibility: ProviderTargetSafetyEligibilitySnapshot | None = None,
    ) -> "ProviderFallbackCandidate":
        entry = status.entry
        safety = target_safety_eligibility
        return cls(
            provider=entry.provider,
            operation=entry.operation,
            variant=entry.variant,
            output_type=entry.output_type,
            fidelity=fidelity,
            vendor_operation_known=entry.vendor_operation_known,
            adapter_installed=entry.adapter_installed,
            ordinary_product_enabled=entry.ordinary_product_enabled,
            currently_available=status.currently_available,
            typed_runtime_reachable=status.typed_runtime_reachable,
            ordinary_product_reachable=status.ordinary_product_reachable,
            currently_reachable=status.currently_reachable,
            returned_material_class=entry.returned_material_class,
            authority_posture=entry.authority_posture,
            target_safety_eligible=(
                safety.eligibility_for(status) if safety is not None else None
            ),
            target_safety_blocker=(
                safety.blocker_for(status) if safety is not None else None
            ),
        )

    def to_trace(self) -> dict[str, object]:
        return {
            **{name: getattr(self, name) for name in self.__dataclass_fields__ if name != "fidelity"},
            "fidelity": self.fidelity.value,
            "dispatch_authorized": False,
        }


@dataclass(frozen=True, slots=True)
class ProviderRouteDecision:
    request: ProviderCapabilityRequest
    selected_provider: str | None
    operation: str | None
    variant: str | None
    output_type: str | None
    fidelity: RouteFidelity
    fallback_candidates: tuple[ProviderFallbackCandidate, ...]
    availability: ProviderAvailability
    availability_posture: str
    adapter_posture: str
    override_posture: str
    decision_reason: str
    block_reason: str | None
    returned_material_class: str
    authority_posture: str
    target_safety_eligibility_ref: Mapping[str, object] = field(default_factory=dict)
    selected_provider_target_safety_eligible: bool | None = None
    selected_provider_target_safety_blocker: str | None = None
    provider_synthesis_disabled: bool = True
    social_authority_granted: bool = False

    @property
    def capability(self) -> AcquisitionCapability:
        return self.request.capability

    @property
    def qualifier(self) -> DiscoverQualifier | None:
        return self.request.qualifier

    @property
    def blocked(self) -> bool:
        return self.fidelity is RouteFidelity.BLOCKED

    def providers(self) -> tuple[str, ...]:
        return (self.selected_provider,) if self.selected_provider is not None else ()

    def to_trace(self) -> dict[str, object]:
        return {
            **self.request.to_trace(),
            "selected_provider": self.selected_provider,
            "operation": self.operation,
            "variant": self.variant,
            "output_type": self.output_type,
            "fidelity": self.fidelity.value,
            "fallback_candidates": [candidate.to_trace() for candidate in self.fallback_candidates],
            "availability": self.availability.to_mapping(),
            "availability_posture": self.availability_posture,
            "adapter_posture": self.adapter_posture,
            "override_posture": self.override_posture,
            "decision_reason": self.decision_reason,
            "block_reason": self.block_reason,
            "returned_material_class": self.returned_material_class,
            "authority_posture": self.authority_posture,
            "target_safety_eligibility_ref": dict(
                self.target_safety_eligibility_ref
            ),
            "selected_provider_target_safety_eligible": (
                self.selected_provider_target_safety_eligible
            ),
            "selected_provider_target_safety_blocker": (
                self.selected_provider_target_safety_blocker
            ),
            "provider_synthesis_disabled": self.provider_synthesis_disabled,
            "social_authority_granted": self.social_authority_granted,
        }


class ProviderRouteBlockedError(RuntimeError):
    """Typed fail-closed terminal for an ordinary acquisition job."""

    def __init__(self, decision: ProviderRouteDecision) -> None:
        if not decision.blocked:
            raise ValueError("ProviderRouteBlockedError requires a blocked decision")
        self.decision = decision
        super().__init__(decision.block_reason or "provider_route_blocked")


_NONAUTHORITATIVE = "non_authoritative_acquisition_material"
_CANDIDATE_ONLY = "candidate_only_no_evidence_authority"
_SYNTHESIS_DISABLED = "provider_synthesis_disabled_no_authority"


def _entry(
    provider: str,
    capability: AcquisitionCapability,
    qualifier: DiscoverQualifier | None,
    operation: str,
    variant: str,
    output_type: str,
    *,
    adapter_installed: bool = True,
    ordinary_product_enabled: bool = True,
    returned_material_class: str = "url_bound_acquisition_material",
    authority_posture: str = _NONAUTHORITATIVE,
) -> ProviderCapabilityCatalogEntry:
    return ProviderCapabilityCatalogEntry(
        provider=provider,
        capability=capability,
        qualifier=qualifier,
        operation=operation,
        variant=variant,
        output_type=output_type,
        vendor_operation_known=True,
        adapter_installed=adapter_installed,
        ordinary_product_enabled=ordinary_product_enabled,
        returned_material_class=returned_material_class,
        authority_posture=authority_posture,
    )


PROVIDER_CAPABILITY_CATALOG: tuple[ProviderCapabilityCatalogEntry, ...] = (
    *(
        _entry("linkup", AcquisitionCapability.DISCOVER, qualifier, "search", variant, "searchResults")
        for variant in ("standard", "deep")
        for qualifier in (
            DiscoverQualifier.GENERAL,
            DiscoverQualifier.DOMAIN_TARGETED,
            DiscoverQualifier.ACADEMIC_TECHNICAL_SEMANTIC,
        )
    ),
    *(
        _entry("tavily", AcquisitionCapability.DISCOVER, qualifier, "search", "search", "searchResults")
        for qualifier in (
            DiscoverQualifier.GENERAL,
            DiscoverQualifier.DOMAIN_TARGETED,
            DiscoverQualifier.ACADEMIC_TECHNICAL_SEMANTIC,
        )
    ),
    _entry(
        "exa",
        AcquisitionCapability.DISCOVER,
        DiscoverQualifier.ACADEMIC_TECHNICAL_SEMANTIC,
        "search",
        "neural_with_text",
        "searchResults",
    ),
    _entry(
        "serper",
        AcquisitionCapability.DISCOVER,
        DiscoverQualifier.LIGHTWEIGHT_DISAMBIGUATION,
        "search",
        "web",
        "searchResults",
        returned_material_class="directional_candidate_material",
        authority_posture=_CANDIDATE_ONLY,
    ),
    _entry(
        "brave",
        AcquisitionCapability.DISCOVER,
        DiscoverQualifier.INDEPENDENT_INDEX,
        "search",
        "web",
        "searchResults",
        returned_material_class="directional_candidate_material",
        authority_posture=_CANDIDATE_ONLY,
    ),
    _entry(
        "linkup",
        AcquisitionCapability.READ,
        None,
        "fetch",
        "known_url",
        "markdown",
        returned_material_class="caller_selected_url_material",
    ),
    _entry(
        "tavily",
        AcquisitionCapability.READ,
        None,
        "extract",
        "basic",
        "extractedContent",
        returned_material_class="caller_selected_url_material",
    ),
    _entry(
        "tavily",
        AcquisitionCapability.FOCUSED_EXTRACT,
        None,
        "extract",
        "query_focused",
        "extractedContent",
        ordinary_product_enabled=False,
        returned_material_class="caller_selected_url_material",
    ),
    _entry(
        "tavily",
        AcquisitionCapability.MAP_SITE,
        None,
        "map",
        "bounded",
        "siteUrlMap",
        ordinary_product_enabled=False,
        returned_material_class="site_url_map",
    ),
    _entry(
        "tavily",
        AcquisitionCapability.CRAWL_SITE,
        None,
        "crawl",
        "bounded",
        "pageMaterial",
        ordinary_product_enabled=False,
        returned_material_class="bounded_multi_page_material",
    ),
    _entry(
        "linkup",
        AcquisitionCapability.PROVIDER_SYNTHESIS,
        None,
        "search",
        "deep",
        "sourcedAnswer",
        ordinary_product_enabled=False,
        returned_material_class="provider_written_synthesis",
        authority_posture=_SYNTHESIS_DISABLED,
    ),
    _entry(
        "linkup",
        AcquisitionCapability.PROVIDER_SYNTHESIS,
        None,
        "research",
        "async",
        "researchReport",
        adapter_installed=False,
        ordinary_product_enabled=False,
        returned_material_class="provider_written_synthesis",
        authority_posture=_SYNTHESIS_DISABLED,
    ),
    _entry(
        "tavily",
        AcquisitionCapability.PROVIDER_SYNTHESIS,
        None,
        "research",
        "async",
        "researchReport",
        adapter_installed=False,
        ordinary_product_enabled=False,
        returned_material_class="provider_written_synthesis",
        authority_posture=_SYNTHESIS_DISABLED,
    ),
)


POST_DISCOVERY_OPERATION_PREFERENCES: Mapping[
    AcquisitionCapability,
    tuple[tuple[str, str, RouteFidelity], ...],
] = {
    AcquisitionCapability.READ: (
        ("linkup", "known_url", RouteFidelity.EXACT),
        ("tavily", "basic", RouteFidelity.EXACT),
    ),
    AcquisitionCapability.FOCUSED_EXTRACT: (
        ("tavily", "query_focused", RouteFidelity.EXACT),
    ),
    AcquisitionCapability.MAP_SITE: (
        ("tavily", "bounded", RouteFidelity.EXACT),
    ),
    AcquisitionCapability.CRAWL_SITE: (
        ("tavily", "bounded", RouteFidelity.EXACT),
    ),
}


def acquisition_routing_policy_descriptor() -> dict[str, object]:
    """Return the stable code-owned routing policy consumed by post-discovery work."""

    catalog = [
        {
            "provider": entry.provider,
            "capability": entry.capability.value,
            "qualifier": (
                entry.qualifier.value if entry.qualifier is not None else None
            ),
            "operation": entry.operation,
            "variant": entry.variant,
            "output_type": entry.output_type,
            "vendor_operation_known": entry.vendor_operation_known,
            "adapter_installed": entry.adapter_installed,
            "ordinary_product_enabled": entry.ordinary_product_enabled,
            "returned_material_class": entry.returned_material_class,
            "authority_posture": entry.authority_posture,
        }
        for entry in PROVIDER_CAPABILITY_CATALOG
    ]
    preferences = {
        capability.value: [
            {
                "provider": provider,
                "variant": variant,
                "fidelity": fidelity.value,
            }
            for provider, variant, fidelity in entries
        ]
        for capability, entries in POST_DISCOVERY_OPERATION_PREFERENCES.items()
    }
    core: dict[str, object] = {
        "schema_version": ACQUISITION_ROUTING_POLICY_SCHEMA_VERSION,
        "owner": "core.routing",
        "revision": ACQUISITION_ROUTING_POLICY_REVISION,
        "selection_algorithm_revision": (
            ACQUISITION_ROUTING_SELECTION_ALGORITHM_REVISION
        ),
        "capability_catalog": catalog,
        "post_discovery_operation_preferences": preferences,
        "untrusted_exact_url_operation_eligibility": {
            identity: {
                "eligible": False,
                "reason": reason,
            }
            for identity, reason in sorted(
                _UNTRUSTED_EXACT_URL_OPERATION_EVIDENCE.items()
            )
        },
        "provider_target_safety_eligibility_policy_version": (
            PROVIDER_TARGET_SAFETY_ELIGIBILITY_POLICY_VERSION
        ),
        "offline_target_safety_validation_authority": {
            "schema_version": (
                OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_AUTHORITY_SCHEMA_VERSION
            ),
            "authority_posture": (
                OFFLINE_PROVIDER_TARGET_SAFETY_VALIDATION_POSTURE
            ),
            "product_reachable": False,
            "ordinary_route_entrypoint_accepts_authority": False,
        },
        "configuration_owned": False,
    }
    digest = sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {**core, "policy_digest": digest}


def acquisition_routing_policy_ref() -> dict[str, object]:
    descriptor = acquisition_routing_policy_descriptor()
    return {
        "schema_version": descriptor["schema_version"],
        "owner": descriptor["owner"],
        "revision": descriptor["revision"],
        "selection_algorithm_revision": descriptor[
            "selection_algorithm_revision"
        ],
        "policy_digest": descriptor["policy_digest"],
    }


def materialize_provider_capability_catalog(
    availability: ProviderAvailability | Mapping[str, object],
) -> tuple[ProviderCapabilityCatalogStatus, ...]:
    """Bind immutable catalog facts to one boolean availability snapshot."""

    snapshot = (
        availability
        if isinstance(availability, ProviderAvailability)
        else ProviderAvailability.from_mapping(availability)
    )
    return tuple(
        ProviderCapabilityCatalogStatus(
            entry=entry,
            currently_available=snapshot.is_available(entry.provider),
            typed_runtime_reachable=(
                snapshot.is_available(entry.provider) and entry.adapter_installed
            ),
            ordinary_product_reachable=(
                snapshot.is_available(entry.provider)
                and entry.adapter_installed
                and entry.ordinary_product_enabled
            ),
            currently_reachable=(
                snapshot.is_available(entry.provider)
                and entry.adapter_installed
                and entry.ordinary_product_enabled
            ),
        )
        for entry in PROVIDER_CAPABILITY_CATALOG
    )


QUERY_TYPE_ENUM = frozenset(
    {
        "news",
        "current_events",
        "event",
        "person",
        "product",
        "place",
        "comparison",
        "quantitative_comparison",
        "concept",
        "how_to",
        "other",
    }
)


def is_quantitative_query(query_type: str | None, report_type: str | None) -> bool:
    """True when retrieval/corpus logic should treat the run as comparison-heavy."""

    qt = (query_type or "other").strip().lower()
    rt = (report_type or "").strip().lower()
    return qt in {"comparison", "quantitative_comparison"} or rt in {
        "quantitative_comparison",
        "comparative_analysis",
        "benchmark",
        "cost_analysis",
        "unit_economics",
    }


def merge_search_provider_overrides(
    primary: list[str] | None,
    secondary: list[str] | None,
    available_keys: dict[str, bool],
    *,
    complexity: str | None = None,
    secondary_premium_escalation: bool = False,
) -> list[str] | None:
    """Merge ordered preferences without converting them into provider fan-out.

    Availability and capability compatibility are intentionally resolved only
    by :func:`route_provider_capability`.  Retaining unavailable or unsupported
    names here ensures an explicit but unsatisfied override becomes a typed
    block instead of silently falling back to ordinary policy.
    """

    del available_keys, complexity, secondary_premium_escalation
    if not primary and not secondary:
        return None
    seen: set[str] = set()
    preferences: list[str] = []
    for providers in (primary or (), secondary or ()):
        for provider in providers:
            normalized = str(provider).strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            preferences.append(normalized)
    return preferences


def derive_provider_capability_request(
    *,
    query_type: str | None,
    intent: str | None,
    is_academic: bool,
    include_domains: Sequence[str] = (),
    exclude_domains: Sequence[str] = (),
    discover_qualifier: DiscoverQualifier | str | None = None,
) -> ProviderCapabilityRequest:
    """Derive a DISCOVER request from existing deterministic acquisition facts."""

    del query_type, intent
    included = tuple(str(domain) for domain in include_domains if str(domain).strip())
    excluded = tuple(str(domain) for domain in exclude_domains if str(domain).strip())
    if discover_qualifier is not None:
        qualifier = DiscoverQualifier(discover_qualifier)
        reason = "explicit_discovery_role"
    elif is_academic:
        qualifier = DiscoverQualifier.ACADEMIC_TECHNICAL_SEMANTIC
        reason = "existing_is_academic_route_fact"
    elif included or excluded:
        qualifier = DiscoverQualifier.DOMAIN_TARGETED
        reason = "bounded_domain_constraint_present"
    else:
        qualifier = DiscoverQualifier.GENERAL
        reason = "ordinary_general_discovery"
    return ProviderCapabilityRequest(
        capability=AcquisitionCapability.DISCOVER,
        qualifier=qualifier,
        include_domains=included,
        exclude_domains=excluded,
        derivation_reason=reason,
    )


def _discover_preferences(
    qualifier: DiscoverQualifier,
    *,
    scrutineer_deep_authorized: bool,
) -> tuple[tuple[str, str, RouteFidelity], ...]:
    linkup_variant = "deep" if scrutineer_deep_authorized else "standard"
    if qualifier in {DiscoverQualifier.GENERAL, DiscoverQualifier.DOMAIN_TARGETED}:
        return (
            ("linkup", linkup_variant, RouteFidelity.EXACT),
            ("tavily", "search", RouteFidelity.EXACT),
        )
    if qualifier is DiscoverQualifier.ACADEMIC_TECHNICAL_SEMANTIC:
        return (
            ("exa", "neural_with_text", RouteFidelity.EXACT),
            ("linkup", linkup_variant, RouteFidelity.DEGRADED),
            ("tavily", "search", RouteFidelity.DEGRADED),
        )
    if qualifier is DiscoverQualifier.LIGHTWEIGHT_DISAMBIGUATION:
        return (("serper", "web", RouteFidelity.EXACT),)
    if qualifier is DiscoverQualifier.INDEPENDENT_INDEX:
        return (("brave", "web", RouteFidelity.EXACT),)
    return ()


def _matching_status(
    statuses: Sequence[ProviderCapabilityCatalogStatus],
    *,
    request: ProviderCapabilityRequest,
    provider: str,
    variant: str,
) -> ProviderCapabilityCatalogStatus | None:
    return next(
        (
            status
            for status in statuses
            if status.provider == provider
            and status.capability is request.capability
            and status.qualifier is request.qualifier
            and status.variant == variant
        ),
        None,
    )


def _status_reachable(
    status: ProviderCapabilityCatalogStatus,
    *,
    typed_runtime_only: bool,
) -> bool:
    return (
        status.typed_runtime_reachable
        if typed_runtime_only
        else status.ordinary_product_reachable
    )


def _operation_preferences(
    capability: AcquisitionCapability,
) -> tuple[tuple[str, str, RouteFidelity], ...]:
    return POST_DISCOVERY_OPERATION_PREFERENCES.get(capability, ())


def _blocked_decision(
    *,
    request: ProviderCapabilityRequest,
    availability: ProviderAvailability,
    candidates: Sequence[ProviderFallbackCandidate],
    override_posture: str,
    reason: str,
    target_safety_eligibility: ProviderTargetSafetyEligibilitySnapshot | None = None,
) -> ProviderRouteDecision:
    eligibility = target_safety_eligibility
    safety_block = reason == "no_safety_eligible_provider_for_untrusted_exact_url"
    return ProviderRouteDecision(
        request=request,
        selected_provider=None,
        operation=None,
        variant=None,
        output_type=None,
        fidelity=RouteFidelity.BLOCKED,
        fallback_candidates=tuple(candidates),
        availability=availability,
        availability_posture=(
            "available_provider_target_safety_ineligible"
            if safety_block
            else "no_compatible_provider_reachable"
        ),
        adapter_posture=(
            "not_invoked_target_safety_ineligible"
            if safety_block
            else "unavailable_or_incompatible"
        ),
        override_posture=override_posture,
        decision_reason=reason,
        block_reason=reason,
        returned_material_class="none",
        authority_posture="blocked_no_acquisition_authority",
        target_safety_eligibility_ref=(eligibility.ref() if eligibility else {}),
        selected_provider_target_safety_eligible=None,
        selected_provider_target_safety_blocker=(reason if safety_block else None),
    )


def route_provider_capability(
    request: ProviderCapabilityRequest,
    available_keys: dict[str, object],
    *,
    override: Sequence[str] | None = None,
    override_posture: str = "none",
    suppress_tavily: bool = False,
    scrutineer_deep_authorized: bool = False,
    typed_runtime_only: bool = False,
) -> ProviderRouteDecision:
    """Choose one production-compatible implementation or a typed block.

    Untrusted exact-URL eligibility is always derived from committed repository
    evidence here.  This ordinary entrypoint intentionally has no fixture or
    requester-supplied eligibility parameter.
    """

    request = _with_code_owned_target_class(request)
    target_safety = ProviderTargetSafetyEligibilitySnapshot.create(
        target_class=request.target_class
    )
    return _route_provider_capability_with_target_safety_snapshot(
        request,
        available_keys,
        override=override,
        override_posture=override_posture,
        suppress_tavily=suppress_tavily,
        scrutineer_deep_authorized=scrutineer_deep_authorized,
        typed_runtime_only=typed_runtime_only,
        target_safety=target_safety,
    )


def route_provider_capability_for_offline_target_safety_validation(
    request: ProviderCapabilityRequest,
    available_keys: dict[str, object],
    *,
    validation_authority: OfflineProviderTargetSafetyValidationAuthorityV1,
    override: Sequence[str] | None = None,
    override_posture: str = "none",
    suppress_tavily: bool = False,
    scrutineer_deep_authorized: bool = False,
    typed_runtime_only: bool = False,
) -> ProviderRouteDecision:
    """Exercise target-eligibility mechanics under offline-only authority.

    This API is structurally separate from ordinary routing and accepts only a
    validated, code-identity-bounded authority whose trace is explicitly
    ``PRODUCT-unreachable``.
    """

    if request.capability is AcquisitionCapability.DISCOVER:
        raise ValueError(
            "offline provider target-safety validation does not apply to DISCOVER"
        )
    if request.capability not in _DYNAMIC_CONTENT_TARGET_CAPABILITIES:
        raise ValueError(
            "offline provider target-safety validation requires a dynamic "
            "content-target capability"
        )
    request = _with_code_owned_target_class(request)
    target_safety = ProviderTargetSafetyEligibilitySnapshot.for_offline_validation(
        target_class=request.target_class,
        authority=validation_authority,
    )
    return _route_provider_capability_with_target_safety_snapshot(
        request,
        available_keys,
        override=override,
        override_posture=override_posture,
        suppress_tavily=suppress_tavily,
        scrutineer_deep_authorized=scrutineer_deep_authorized,
        typed_runtime_only=typed_runtime_only,
        target_safety=target_safety,
    )


def _with_code_owned_target_class(
    request: ProviderCapabilityRequest,
) -> ProviderCapabilityRequest:
    """Derive target class from capability; requester text cannot bypass policy."""

    target_class = (
        UNTRUSTED_EXACT_URL_TARGET_CLASS
        if request.capability in _DYNAMIC_CONTENT_TARGET_CAPABILITIES
        else TARGET_SAFETY_NOT_APPLICABLE
    )
    if request.target_class == target_class:
        return request
    return replace(request, target_class=target_class)


def _route_provider_capability_with_target_safety_snapshot(
    request: ProviderCapabilityRequest,
    available_keys: dict[str, object],
    *,
    override: Sequence[str] | None,
    override_posture: str,
    suppress_tavily: bool,
    scrutineer_deep_authorized: bool,
    typed_runtime_only: bool,
    target_safety: ProviderTargetSafetyEligibilitySnapshot,
) -> ProviderRouteDecision:
    """Shared deterministic selector for production and offline validation."""

    availability = ProviderAvailability.from_mapping(available_keys)
    statuses = materialize_provider_capability_catalog(availability)

    if request.capability is AcquisitionCapability.PROVIDER_SYNTHESIS:
        synthesis_candidates = tuple(
            ProviderFallbackCandidate.from_status(status, fidelity=RouteFidelity.BLOCKED)
            for status in statuses
            if status.capability is AcquisitionCapability.PROVIDER_SYNTHESIS
        )
        return _blocked_decision(
            request=request,
            availability=availability,
            candidates=synthesis_candidates,
            override_posture=override_posture,
            reason="provider_synthesis_disabled",
        )

    if request.capability is not AcquisitionCapability.DISCOVER:
        preferences = _operation_preferences(request.capability)
        candidates: list[tuple[ProviderCapabilityCatalogStatus, RouteFidelity]] = []
        for provider, variant, fidelity in preferences:
            status = _matching_status(
                statuses,
                request=request,
                provider=provider,
                variant=variant,
            )
            if status is not None:
                candidates.append((status, fidelity))
        selected_index = next(
            (
                index
                for index, (status, _) in enumerate(candidates)
                if _status_reachable(status, typed_runtime_only=typed_runtime_only)
                and target_safety.eligibility_for(status)
            ),
            None,
        )
        fallback_candidates = tuple(
            ProviderFallbackCandidate.from_status(
                status,
                fidelity=fidelity,
                target_safety_eligibility=target_safety,
            )
            for index, (status, fidelity) in enumerate(candidates)
            if index != selected_index
        )
        if selected_index is None:
            reachable_without_safety = any(
                _status_reachable(status, typed_runtime_only=typed_runtime_only)
                for status, _ in candidates
            )
            safety_blocked = (
                request.target_class == UNTRUSTED_EXACT_URL_TARGET_CLASS
                and reachable_without_safety
            )
            return _blocked_decision(
                request=request,
                availability=availability,
                candidates=fallback_candidates,
                override_posture=override_posture,
                reason=(
                    "no_safety_eligible_provider_for_untrusted_exact_url"
                    if safety_blocked
                    else "capability_not_ordinary_product_enabled"
                    if not typed_runtime_only
                    and any(status.typed_runtime_reachable for status, _ in candidates)
                    else "capability_unavailable"
                ),
                target_safety_eligibility=target_safety,
            )
        selected, fidelity = candidates[selected_index]
        return ProviderRouteDecision(
            request=request,
            selected_provider=selected.provider,
            operation=selected.operation,
            variant=selected.variant,
            output_type=selected.output_type,
            fidelity=fidelity,
            fallback_candidates=fallback_candidates,
            availability=availability,
            availability_posture="selected_provider_reachable",
            adapter_posture=(
                "installed_typed_runtime_only"
                if typed_runtime_only and not selected.ordinary_product_enabled
                else "installed_and_ordinary_enabled"
            ),
            override_posture=override_posture,
            decision_reason="first_reachable_policy_preference_selected",
            block_reason=None,
            returned_material_class=selected.returned_material_class,
            authority_posture=selected.authority_posture,
            target_safety_eligibility_ref=target_safety.ref(),
            selected_provider_target_safety_eligible=True,
            selected_provider_target_safety_blocker=None,
        )

    qualifier = request.qualifier or DiscoverQualifier.GENERAL
    normalized_request = (
        request
        if request.qualifier is not None
        else ProviderCapabilityRequest(
            capability=request.capability,
            qualifier=qualifier,
            domain_constraints=request.domain_constraints,
            include_domains=request.include_domains,
            exclude_domains=request.exclude_domains,
            source_of_record_domain_constraints=(
                request.source_of_record_domain_constraints
            ),
            derivation_reason=request.derivation_reason,
            general_deep_requested=request.general_deep_requested,
            general_deep_authorization=request.general_deep_authorization,
            target_class=request.target_class,
        )
    )
    if normalized_request.general_deep_requested and not scrutineer_deep_authorized:
        authorization = normalized_request.general_deep_authorization
        if authorization is None or not authorization.valid:
            return _blocked_decision(
                request=normalized_request,
                availability=availability,
                candidates=(),
                override_posture=override_posture,
                reason="general_deep_authorization_required",
            )
        if not typed_runtime_only:
            return _blocked_decision(
                request=normalized_request,
                availability=availability,
                candidates=(),
                override_posture=override_posture,
                reason="general_deep_no_ordinary_product_requester",
            )
        preferences = [("linkup", "deep", RouteFidelity.EXACT)]
    else:
        preferences = list(
            _discover_preferences(
                qualifier,
                scrutineer_deep_authorized=scrutineer_deep_authorized,
            )
        )
    if suppress_tavily:
        preferences = [preference for preference in preferences if preference[0] != "tavily"]

    explicit_preferences = None
    if override is not None:
        explicit_preferences = [str(provider).strip().lower() for provider in override]
        preference_by_provider = {
            provider: (provider, variant, fidelity) for provider, variant, fidelity in preferences
        }
        preferences = [
            preference_by_provider[provider] for provider in explicit_preferences if provider in preference_by_provider
        ]
        override_posture = override_posture if override_posture != "none" else "ordered_preferences"

    candidates: list[tuple[ProviderCapabilityCatalogStatus, RouteFidelity]] = []
    for provider, variant, fidelity in preferences:
        status = _matching_status(
            statuses,
            request=normalized_request,
            provider=provider,
            variant=variant,
        )
        if status is not None:
            candidates.append((status, fidelity))

    selected_index = next(
        (
            index
            for index, (status, _) in enumerate(candidates)
            if _status_reachable(
                status,
                typed_runtime_only=(
                    typed_runtime_only and normalized_request.general_deep_requested
                ),
            )
        ),
        None,
    )
    fallback_candidates = tuple(
        ProviderFallbackCandidate.from_status(status, fidelity=fidelity)
        for index, (status, fidelity) in enumerate(candidates)
        if index != selected_index
    )
    if selected_index is None:
        reason = (
            "override_no_compatible_available_provider"
            if explicit_preferences is not None
            else "no_compatible_provider_available"
        )
        return _blocked_decision(
            request=normalized_request,
            availability=availability,
            candidates=fallback_candidates,
            override_posture=override_posture,
            reason=reason,
        )

    selected, fidelity = candidates[selected_index]
    return ProviderRouteDecision(
        request=normalized_request,
        selected_provider=selected.provider,
        operation=selected.operation,
        variant=selected.variant,
        output_type=selected.output_type,
        fidelity=fidelity,
        fallback_candidates=fallback_candidates,
        availability=availability,
        availability_posture="selected_provider_reachable",
        adapter_posture=(
            "installed_authorized_runtime_only"
            if normalized_request.general_deep_requested
            else "installed_and_ordinary_enabled"
        ),
        override_posture=override_posture,
        decision_reason=(
            "first_compatible_override_preference_selected"
            if explicit_preferences is not None
            else "first_reachable_policy_preference_selected"
        ),
        block_reason=None,
        returned_material_class=selected.returned_material_class,
        authority_posture=selected.authority_posture,
    )


def select_providers(
    query_type: str,
    intent: str,
    complexity: str,
    available_keys: dict[str, bool],
    report_type: str = "general_research",
    is_academic: bool = False,
    suppress_tavily: bool = False,
    override: Optional[list[str]] = None,
    override_is_user: bool = True,
    premium_search_escalation: bool = False,
    include_domains: Sequence[str] = (),
    exclude_domains: Sequence[str] = (),
    discover_qualifier: DiscoverQualifier | str | None = None,
) -> list[str]:
    """Compatibility projection of the typed route decision.

    Complexity, report type, news/currentness, comparison, and quantitative
    posture do not select providers or activate provider-specific variants.
    """

    del complexity, report_type, premium_search_escalation
    request = derive_provider_capability_request(
        query_type=query_type,
        intent=intent,
        is_academic=is_academic,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        discover_qualifier=discover_qualifier,
    )
    decision = route_provider_capability(
        request,
        available_keys,
        override=override,
        override_posture=("user_ordered_preferences" if override_is_user else "internal_ordered_preferences"),
        suppress_tavily=suppress_tavily,
    )
    return list(decision.providers())
