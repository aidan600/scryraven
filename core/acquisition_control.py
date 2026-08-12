"""Provider-neutral post-discovery acquisition control contracts and reducers.

Workers may propose acquisition need.  This module deterministically interprets
those admitted facts, while RunKernel remains the canonical owner of accepted
state.  No provider catalog, provider availability, transport, evidence, or
answer authority is consulted here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from core.routing import AcquisitionCapability, acquisition_routing_policy_ref
from core.searchos_navigation_runtime import (
    validate_navigation_destination_binding_ref,
)

ACQUISITION_NEED_PROPOSAL_SCHEMA_VERSION = "acquisition_need_proposal_v1"
ACQUISITION_CAPABILITY_DECISION_SCHEMA_VERSION = (
    "acquisition_capability_decision_observation_v1"
)
ACQUISITION_WORK_ORDER_SCHEMA_VERSION = "acquisition_work_order_v1"
ACQUISITION_ROUTE_OBSERVATION_SCHEMA_VERSION = (
    "acquisition_route_observation_v1"
)
ACQUISITION_EXECUTION_OBSERVATION_SCHEMA_VERSION = (
    "acquisition_execution_observation_v1"
)
ACQUISITION_TERMINAL_RECEIPT_SCHEMA_VERSION = "acquisition_terminal_receipt_v1"
ACQUISITION_CUSTODY_AUTHORIZATION_SCHEMA_VERSION = (
    "acquisition_custody_authorization_v1"
)
ACQUISITION_CONTROL_STATE_SCHEMA_VERSION = "runkernel_acquisition_control_state_v1"

PROPOSER_POSTURE = "nonauthoritative_need_proposal"
WORK_ORDER_AUTHORITY_POSTURE = "acquisition_execution_only"
PREMIUM_SEQUENTIAL_ACQUISITION = "PREMIUM_SEQUENTIAL_ACQUISITION"
SEARCHOS_NAVIGATION_ORIGIN = "searchos_navigation"

READ_MATERIAL_SHAPES = frozenset(
    {"full_page_or_unknown", "ordinary_single_page", "explicit_known_url"}
)
FOCUSED_MATERIAL_SHAPES = frozenset(
    {"narrow_section", "exact_field", "exact_table", "exact_rule"}
)
KNOWN_MATERIAL_SHAPES = frozenset(
    {
        *READ_MATERIAL_SHAPES,
        *FOCUSED_MATERIAL_SHAPES,
        "site_topology",
        "bounded_multi_page",
        "premium_sequential_acquisition",
    }
)

_PROPOSAL_FIELDS = frozenset(
    {
        "schema_version",
        "proposal_id",
        "proposal_digest",
        "run_id",
        "request_id",
        "producer_surface",
        "producer_posture",
        "answer_contract_ref",
        "source_obligation_ref",
        "component_ref",
        "requested_material_shape",
        "origin",
        "destination_binding_ref",
        "candidate_ref",
        "available_urls",
        "root_url",
        "bounded_focus",
        "include_domains",
        "exclude_domains",
        "include_path_prefix",
        "exclude_path_prefixes",
        "requested_bounds",
        "explicit_multi_page_need",
        "previous_read_posture",
        "parent_acquisition_job_refs",
        "prior_acquisition_receipt_refs",
        "proposal_reason_code",
        "advisory_proposed_capability",
    }
)

_DECISION_FIELDS = frozenset(
    {
        "schema_version",
        "decision_id",
        "decision_digest",
        "proposal_ref",
        "derived_capability",
        "advisory_proposal_match_status",
        "prerequisite_evaluation",
        "decision_status",
        "block_code",
        "material_shape_interpretation",
        "operation_identity_key",
        "authority_posture",
    }
)
_DECISION_PREREQUISITES = frozenset(
    {
        "run_id_current",
        "request_id_current",
        "answer_contract_current",
        "component_revision_current",
        "source_obligation_current",
        "source_obligation_active",
        "material_shape_recognized",
        "operation_identity_present",
        "hard_operation_bounds_valid",
        "duplicate_completed_operation",
        "duplicate_terminal_operation",
        "operation_exhausted",
        "prior_receipt_refs_current",
        "active_conflicting_operation",
        "provider_availability_consulted",
        "mode_or_complexity_consulted",
    }
)
_WORK_ORDER_FIELDS = frozenset(
    {
        "schema_version",
        "work_order_id",
        "work_order_digest",
        "accepted_capability_observation_ref",
        "runkernel_authorization_ref",
        "answer_contract_ref",
        "source_obligation_ref",
        "component_ref",
        "authorized_capability",
        "origin",
        "destination_binding_ref",
        "candidate_ref",
        "selected_urls",
        "root_url",
        "bounded_focus",
        "include_domains",
        "exclude_domains",
        "include_path_prefix",
        "exclude_path_prefixes",
        "hard_operation_bounds",
        "parent_acquisition_job_refs",
        "routing_policy_ref",
        "operation_identity_key",
        "duplicate_check",
        "exhaustion_check",
        "authority_posture",
    }
)
_ROUTE_FIELDS = frozenset(
    {
        "schema_version",
        "route_observation_id",
        "route_observation_digest",
        "work_order_ref",
        "completed_route_decision_ref",
        "selected_provider",
        "selected_operation",
        "selected_variant",
        "selected_output_type",
        "routing_policy_ref",
        "availability_snapshot_ref",
        "terminal_status",
        "block_code",
    }
)
_EXECUTION_FIELDS = frozenset(
    {
        "schema_version",
        "execution_observation_id",
        "execution_observation_digest",
        "work_order_ref",
        "completed_route_ref",
        "execution_result_ref",
        "artifact_refs",
        "provider_calls_attempted",
        "provider_calls_completed",
        "terminal_status",
        "failure_or_block_code",
        "provider_failure_fallback_attempted",
        "capability_switch_attempted",
        "downstream_authority_granted",
    }
)
_EXECUTION_RESULT_REF_FIELDS = frozenset(
    {"execution_result_id", "execution_result_digest"}
)
_ARTIFACT_REF_FIELDS = frozenset(
    {
        "artifact_id",
        "artifact_digest",
        "kind",
        "acquisition_job_id",
        "provider",
        "operation",
        "provider_variant",
        "output_type",
        "status",
        "requested_url",
        "final_url",
        "canonical_url",
        "root_url",
        "retained_digest",
        "retained_character_count",
        "url_count",
        "page_count",
        "failure_code",
        "authority_posture",
        "retained_text_included",
        "raw_provider_payload_included",
    }
)
_TERMINAL_RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "receipt_id",
        "receipt_digest",
        "operation_identity_key",
        "capability",
        "terminal_status",
        "block_or_failure_code",
        "work_order_ref",
        "route_observation_ref",
        "execution_observation_ref",
        "source_obligation_ref",
        "retry_licensed",
        "active_slot_released",
    }
)
_CUSTODY_AUTHORIZATION_FIELDS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "authorization_digest",
        "work_order_ref",
        "route_observation_ref",
        "terminal_receipt_ref",
        "answer_contract_ref",
        "source_obligation_ref",
        "capability",
        "custody_consumer",
        "downstream_authority_granted",
    }
)

_FORBIDDEN_PROPOSAL_KEYS = frozenset(
    {
        "provider",
        "provider_authorized",
        "provider_used",
        "selected_provider",
        "provider_preference",
        "provider_operation",
        "provider_variant",
        "provider_output_type",
        "provider_availability",
        "availability",
        "transport",
        "adapter",
        "evidence",
        "evidence_admission",
        "evidence_authority",
        "source_authority",
        "citation",
        "citation_eligibility",
        "source_obligation_satisfied",
        "sufficiency",
        "fap",
        "final_answer_packet",
        "author",
        "answer",
        "answer_text",
        "executable_instruction",
        "tool_instruction",
        "raw_prompt",
        "raw_provider_payload",
    }
)


class AcquisitionControlError(ValueError):
    """Fail-closed acquisition-control contract or transition error."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True, slots=True)
class AcquisitionNeedProposalV1:
    proposal_id: str
    proposal_digest: str
    run_id: str
    request_id: str
    producer_surface: str
    answer_contract_ref: Mapping[str, Any]
    source_obligation_ref: Mapping[str, Any]
    requested_material_shape: str
    origin: str | None = None
    destination_binding_ref: Mapping[str, Any] = field(default_factory=dict)
    candidate_ref: Mapping[str, Any] = field(default_factory=dict)
    component_ref: Mapping[str, Any] = field(default_factory=dict)
    available_urls: tuple[str, ...] = ()
    root_url: str | None = None
    bounded_focus: Mapping[str, Any] = field(default_factory=dict)
    include_domains: tuple[str, ...] = ()
    exclude_domains: tuple[str, ...] = ()
    include_path_prefix: str | None = None
    exclude_path_prefixes: tuple[str, ...] = ()
    requested_bounds: Mapping[str, Any] = field(default_factory=dict)
    explicit_multi_page_need: bool = False
    previous_read_posture: str | None = None
    parent_acquisition_job_refs: tuple[Mapping[str, Any], ...] = ()
    prior_acquisition_receipt_refs: tuple[Mapping[str, Any], ...] = ()
    proposal_reason_code: str = "post_discovery_acquisition_need"
    advisory_proposed_capability: str | None = None
    schema_version: str = ACQUISITION_NEED_PROPOSAL_SCHEMA_VERSION
    producer_posture: str = PROPOSER_POSTURE

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        request_id: str,
        producer_surface: str,
        answer_contract_ref: Mapping[str, Any],
        source_obligation_ref: Mapping[str, Any],
        requested_material_shape: str,
        origin: str | None = None,
        destination_binding_ref: Mapping[str, Any] | None = None,
        candidate_ref: Mapping[str, Any] | None = None,
        component_ref: Mapping[str, Any] | None = None,
        available_urls: Sequence[str] = (),
        root_url: str | None = None,
        bounded_focus: Mapping[str, Any] | None = None,
        include_domains: Sequence[str] = (),
        exclude_domains: Sequence[str] = (),
        include_path_prefix: str | None = None,
        exclude_path_prefixes: Sequence[str] = (),
        requested_bounds: Mapping[str, Any] | None = None,
        explicit_multi_page_need: bool = False,
        previous_read_posture: str | None = None,
        parent_acquisition_job_refs: Sequence[Mapping[str, Any]] = (),
        prior_acquisition_receipt_refs: Sequence[Mapping[str, Any]] = (),
        proposal_reason_code: str = "post_discovery_acquisition_need",
        advisory_proposed_capability: str | None = None,
    ) -> "AcquisitionNeedProposalV1":
        canonical_candidate_ref = _candidate_ref(candidate_ref)
        canonical_urls = [
            _required_url(url, "proposal_url_invalid") for url in available_urls
        ]
        origin_fields = _acquisition_origin_fields(
            origin=origin,
            destination_binding_ref=destination_binding_ref,
            candidate_ref=canonical_candidate_ref,
            available_urls=canonical_urls,
            root_url=root_url,
            requested_material_shape=requested_material_shape,
        )
        core = {
            "schema_version": ACQUISITION_NEED_PROPOSAL_SCHEMA_VERSION,
            "run_id": _required_token(run_id, "proposal_run_id_missing"),
            "request_id": _required_token(
                request_id, "proposal_request_id_missing"
            ),
            "producer_surface": _required_token(
                producer_surface, "proposal_producer_surface_missing", limit=240
            ),
            "producer_posture": PROPOSER_POSTURE,
            "answer_contract_ref": _contract_ref(answer_contract_ref),
            "source_obligation_ref": _source_obligation_ref(
                source_obligation_ref
            ),
            "component_ref": _component_ref(component_ref),
            "requested_material_shape": _required_token(
                requested_material_shape,
                "requested_material_shape_missing",
                limit=100,
            ).casefold(),
            **origin_fields,
            "candidate_ref": canonical_candidate_ref,
            "available_urls": canonical_urls,
            "root_url": (
                _required_url(root_url, "proposal_root_url_invalid")
                if root_url
                else None
            ),
            "bounded_focus": _bounded_focus(bounded_focus),
            "include_domains": _tokens(include_domains, limit=260),
            "exclude_domains": _tokens(exclude_domains, limit=260),
            "include_path_prefix": _optional_path(include_path_prefix),
            "exclude_path_prefixes": _paths(exclude_path_prefixes),
            "requested_bounds": _bounded_int_mapping(requested_bounds),
            "explicit_multi_page_need": _strict_bool(
                explicit_multi_page_need,
                "explicit_multi_page_need_boolean_required",
            ),
            "previous_read_posture": _optional_token(
                previous_read_posture, limit=100
            ),
            "parent_acquisition_job_refs": [
                _compact_ref(item) for item in parent_acquisition_job_refs
            ],
            "prior_acquisition_receipt_refs": [
                _compact_ref(item) for item in prior_acquisition_receipt_refs
            ],
            "proposal_reason_code": _required_token(
                proposal_reason_code, "proposal_reason_code_missing", limit=160
            ),
            "advisory_proposed_capability": _optional_capability(
                advisory_proposed_capability
            ),
        }
        _validate_material_shape(core["requested_material_shape"])
        digest = stable_json_digest(core)
        payload = {
            **core,
            "proposal_id": f"acquisition-need:{core['request_id']}:{digest[:20]}",
            "proposal_digest": digest,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "AcquisitionNeedProposalV1":
        raw = _mapping(value, "proposal_mapping_required")
        unknown = set(raw).difference(_PROPOSAL_FIELDS)
        if unknown:
            raise AcquisitionControlError(
                "proposal_unknown_fields",
                f"proposal contains unknown fields: {sorted(unknown)}",
            )
        forbidden = _collect_normalized_keys(raw).intersection(
            {_canonical_key(key) for key in _FORBIDDEN_PROPOSAL_KEYS}
        )
        forbidden.update(_forbidden_concept_keys(raw))
        if forbidden:
            raise AcquisitionControlError(
                "proposal_forbidden_authority_fields",
                f"proposal contains forbidden fields: {sorted(forbidden)}",
            )
        if raw.get("schema_version") != ACQUISITION_NEED_PROPOSAL_SCHEMA_VERSION:
            raise AcquisitionControlError("proposal_schema_version_invalid")
        if raw.get("producer_posture") != PROPOSER_POSTURE:
            raise AcquisitionControlError("proposal_posture_invalid")
        core = {
            key: _json_clone(item)
            for key, item in raw.items()
            if key not in {"proposal_id", "proposal_digest"}
        }
        expected_digest = stable_json_digest(core)
        if raw.get("proposal_digest") != expected_digest:
            raise AcquisitionControlError("proposal_digest_mismatch")
        request_id = _required_token(
            raw.get("request_id"), "proposal_request_id_missing"
        )
        expected_id = f"acquisition-need:{request_id}:{expected_digest[:20]}"
        if raw.get("proposal_id") != expected_id:
            raise AcquisitionControlError("proposal_id_mismatch")
        material_shape = _required_token(
            raw.get("requested_material_shape"),
            "requested_material_shape_missing",
            limit=100,
        )
        if material_shape != material_shape.casefold():
            raise AcquisitionControlError("requested_material_shape_not_canonical")
        _validate_material_shape(material_shape)
        candidate_ref = _candidate_ref(raw.get("candidate_ref"))
        available_urls = tuple(
            _required_url(url, "proposal_url_invalid")
            for url in _sequence(raw.get("available_urls"))
        )
        origin_fields = _acquisition_origin_fields(
            origin=raw.get("origin"),
            destination_binding_ref=raw.get("destination_binding_ref"),
            candidate_ref=candidate_ref,
            available_urls=available_urls,
            root_url=raw.get("root_url"),
            requested_material_shape=material_shape,
        )
        proposal = cls(
            proposal_id=expected_id,
            proposal_digest=expected_digest,
            run_id=_required_token(raw.get("run_id"), "proposal_run_id_missing"),
            request_id=request_id,
            producer_surface=_required_token(
                raw.get("producer_surface"),
                "proposal_producer_surface_missing",
                limit=240,
            ),
            answer_contract_ref=_contract_ref(raw.get("answer_contract_ref")),
            source_obligation_ref=_source_obligation_ref(
                raw.get("source_obligation_ref")
            ),
            component_ref=_component_ref(raw.get("component_ref")),
            requested_material_shape=material_shape,
            origin=origin_fields.get("origin"),
            destination_binding_ref=_json_clone(
                origin_fields.get("destination_binding_ref") or {}
            ),
            candidate_ref=candidate_ref,
            available_urls=available_urls,
            root_url=(
                _required_url(raw.get("root_url"), "proposal_root_url_invalid")
                if raw.get("root_url")
                else None
            ),
            bounded_focus=_bounded_focus(raw.get("bounded_focus")),
            include_domains=tuple(_tokens(raw.get("include_domains"), limit=260)),
            exclude_domains=tuple(_tokens(raw.get("exclude_domains"), limit=260)),
            include_path_prefix=_optional_path(raw.get("include_path_prefix")),
            exclude_path_prefixes=tuple(
                _paths(raw.get("exclude_path_prefixes"))
            ),
            requested_bounds=_bounded_int_mapping(raw.get("requested_bounds")),
            explicit_multi_page_need=_strict_bool(
                raw.get("explicit_multi_page_need"),
                "explicit_multi_page_need_boolean_required",
            ),
            previous_read_posture=_optional_token(
                raw.get("previous_read_posture"), limit=100
            ),
            parent_acquisition_job_refs=tuple(
                _compact_ref(item)
                for item in _sequence(raw.get("parent_acquisition_job_refs"))
            ),
            prior_acquisition_receipt_refs=tuple(
                _compact_ref(item)
                for item in _sequence(raw.get("prior_acquisition_receipt_refs"))
            ),
            proposal_reason_code=_required_token(
                raw.get("proposal_reason_code"),
                "proposal_reason_code_missing",
                limit=160,
            ),
            advisory_proposed_capability=_optional_capability(
                raw.get("advisory_proposed_capability")
            ),
        )
        canonical_payload = proposal.to_dict()
        canonical_core = {
            key: _json_clone(item)
            for key, item in canonical_payload.items()
            if key not in {"proposal_id", "proposal_digest"}
        }
        canonical_digest = stable_json_digest(canonical_core)
        canonical_id = (
            f"acquisition-need:{proposal.request_id}:"
            f"{canonical_digest[:20]}"
        )
        if (
            core != canonical_core
            or expected_digest != canonical_digest
            or expected_id != canonical_id
        ):
            raise AcquisitionControlError("proposal_not_canonical")
        return proposal

    def to_dict(self) -> dict[str, Any]:
        return _json_clone(
            {
                "schema_version": self.schema_version,
                "proposal_id": self.proposal_id,
                "proposal_digest": self.proposal_digest,
                "run_id": self.run_id,
                "request_id": self.request_id,
                "producer_surface": self.producer_surface,
                "producer_posture": self.producer_posture,
                "answer_contract_ref": self.answer_contract_ref,
                "source_obligation_ref": self.source_obligation_ref,
                "component_ref": self.component_ref,
                "requested_material_shape": self.requested_material_shape,
                **(
                    {
                        "origin": self.origin,
                        "destination_binding_ref": self.destination_binding_ref,
                    }
                    if self.origin is not None
                    else {}
                ),
                "candidate_ref": self.candidate_ref,
                "available_urls": list(self.available_urls),
                "root_url": self.root_url,
                "bounded_focus": self.bounded_focus,
                "include_domains": list(self.include_domains),
                "exclude_domains": list(self.exclude_domains),
                "include_path_prefix": self.include_path_prefix,
                "exclude_path_prefixes": list(self.exclude_path_prefixes),
                "requested_bounds": self.requested_bounds,
                "explicit_multi_page_need": self.explicit_multi_page_need,
                "previous_read_posture": self.previous_read_posture,
                "parent_acquisition_job_refs": list(
                    self.parent_acquisition_job_refs
                ),
                "prior_acquisition_receipt_refs": list(
                    self.prior_acquisition_receipt_refs
                ),
                "proposal_reason_code": self.proposal_reason_code,
                "advisory_proposed_capability": (
                    self.advisory_proposed_capability
                ),
            }
        )

    def ref(self) -> dict[str, str]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_digest": self.proposal_digest,
        }


def validate_selected_candidate_material_need_proposal(
    *,
    proposal: AcquisitionNeedProposalV1,
    run_id: str,
    request_id: str,
    candidate_packet: Mapping[str, Any],
    selected_candidate: Mapping[str, Any],
    authority_snapshot: Mapping[str, Any],
) -> AcquisitionNeedProposalV1:
    """Bind an independently produced need to admitted URL provenance.

    This helper never creates acquisition need. It only proves that a proposal
    supplied by another current authority matches the selected candidate, the
    current AnswerContract component, and the current source obligation.
    """

    if not isinstance(proposal, AcquisitionNeedProposalV1):
        raise AcquisitionControlError("acquisition_need_proposal_required")
    packet = _mapping(candidate_packet, "candidate_packet_missing")
    candidate = _mapping(selected_candidate, "selected_candidate_missing")
    snapshot = _mapping(authority_snapshot, "authority_snapshot_missing")
    if proposal.run_id != run_id or proposal.request_id != request_id:
        raise AcquisitionControlError("proposal_identity_mismatch")
    if packet.get("run_id") != run_id or packet.get("request_id") != request_id:
        raise AcquisitionControlError("candidate_packet_identity_mismatch")

    contract_ref = _contract_ref(snapshot.get("answer_contract_ref"))
    if packet.get("current_answer_contract_digest") != contract_ref.get(
        "contract_digest"
    ):
        raise AcquisitionControlError("stale_answer_contract")
    if dict(proposal.answer_contract_ref) != contract_ref:
        raise AcquisitionControlError("proposal_answer_contract_binding_mismatch")

    candidate_identity = {
        key: candidate.get(key)
        for key in (
            "candidate_id",
            "candidate_digest",
            "record_digest",
            "url",
            "component_id",
            "source_obligation_candidate_ids",
        )
    }
    matching_records = [
        _mapping(record, "candidate_record_invalid")
        for record in _sequence(packet.get("candidate_records"))
        if all(
            _mapping(record, "candidate_record_invalid").get(key) == value
            for key, value in candidate_identity.items()
        )
    ]
    if len(matching_records) != 1:
        raise AcquisitionControlError("selected_candidate_not_bound_to_packet")

    component_id = _required_token(
        candidate.get("component_id"), "selected_candidate_component_missing"
    )
    component = _component_ref(
        _mapping(
            _mapping(
                snapshot.get("components_by_id"), "snapshot_components_missing"
            ).get(component_id),
            "selected_candidate_component_binding_missing",
        )
    )
    if dict(proposal.component_ref) != component:
        raise AcquisitionControlError("proposal_component_binding_mismatch")

    obligation_ids = _tokens(
        candidate.get("source_obligation_candidate_ids"), limit=200
    )
    if len(obligation_ids) != 1:
        raise AcquisitionControlError("source_obligation_identity_missing")
    obligation = _source_obligation_ref(
        _mapping(
            snapshot.get("source_obligations_by_id"),
            "snapshot_source_obligations_missing",
        ).get(obligation_ids[0])
    )
    if component_id not in obligation.get("component_ids", ()):
        raise AcquisitionControlError("mismatched_source_obligation")
    if dict(proposal.source_obligation_ref) != obligation:
        raise AcquisitionControlError("proposal_source_obligation_binding_mismatch")

    expected_candidate_ref = {
        "packet_id": packet.get("packet_id"),
        "packet_digest": packet.get("packet_digest"),
        "candidate_id": candidate.get("candidate_id"),
        "candidate_digest": candidate.get("candidate_digest"),
        "record_digest": candidate.get("record_digest"),
        "url": candidate.get("url"),
    }
    if dict(proposal.candidate_ref) != expected_candidate_ref:
        raise AcquisitionControlError("proposal_candidate_binding_mismatch")
    selected_url = _required_url(
        candidate.get("url"), "selected_candidate_url_invalid"
    )
    if tuple(proposal.available_urls) != (selected_url,):
        raise AcquisitionControlError("proposal_selected_url_binding_mismatch")
    if proposal.explicit_multi_page_need or proposal.root_url:
        raise AcquisitionControlError("selected_candidate_single_url_need_required")
    if proposal.requested_material_shape == "explicit_known_url":
        raise AcquisitionControlError("url_provenance_is_not_material_need")
    if proposal.producer_surface == "core.ordinary_live_source_custody_runtime":
        raise AcquisitionControlError("material_need_producer_not_independent")
    if proposal.proposal_reason_code == "selected_candidate_read_required":
        raise AcquisitionControlError("legacy_selected_candidate_trigger_forbidden")
    return proposal


@dataclass(frozen=True, slots=True)
class AcquisitionCapabilityDecisionObservationV1:
    decision_id: str
    decision_digest: str
    proposal_ref: Mapping[str, Any]
    derived_capability: str | None
    advisory_proposal_match_status: str
    prerequisite_evaluation: Mapping[str, Any]
    decision_status: str
    block_code: str | None
    material_shape_interpretation: str
    operation_identity_key: str | None
    schema_version: str = ACQUISITION_CAPABILITY_DECISION_SCHEMA_VERSION
    authority_posture: str = "capability_decision_only"

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "AcquisitionCapabilityDecisionObservationV1":
        raw = _mapping(value, "capability_decision_mapping_required")
        _reject_unknown_fields(raw, _DECISION_FIELDS, "capability_decision")
        if raw.get("schema_version") != ACQUISITION_CAPABILITY_DECISION_SCHEMA_VERSION:
            raise AcquisitionControlError("capability_decision_schema_invalid")
        if raw.get("authority_posture") != "capability_decision_only":
            raise AcquisitionControlError("capability_decision_posture_invalid")
        core = {
            key: _json_clone(raw.get(key))
            for key in (
                "schema_version",
                "proposal_ref",
                "derived_capability",
                "advisory_proposal_match_status",
                "prerequisite_evaluation",
                "decision_status",
                "block_code",
                "material_shape_interpretation",
                "operation_identity_key",
                "authority_posture",
            )
        }
        digest = stable_json_digest(core)
        proposal_id = _required_token(
            _mapping(raw.get("proposal_ref"), "decision_proposal_ref_missing").get(
                "proposal_id"
            ),
            "decision_proposal_id_missing",
            limit=300,
        )
        expected_id = f"acquisition-capability-decision:{proposal_id}:{digest[:20]}"
        if raw.get("decision_digest") != digest or raw.get("decision_id") != expected_id:
            raise AcquisitionControlError("capability_decision_identity_mismatch")
        decision_status = _required_token(
            raw.get("decision_status"), "decision_status_missing"
        )
        block_code = _optional_token(raw.get("block_code"), limit=180)
        if decision_status not in {"accepted", "blocked"}:
            raise AcquisitionControlError("capability_decision_status_invalid")
        if (decision_status == "blocked") != bool(block_code):
            raise AcquisitionControlError("capability_decision_block_status_mismatch")
        prerequisites = _mapping(
            raw.get("prerequisite_evaluation"),
            "prerequisite_evaluation_missing",
        )
        _reject_unknown_fields(
            prerequisites,
            _DECISION_PREREQUISITES,
            "capability_decision_prerequisites",
        )
        if set(prerequisites) != set(_DECISION_PREREQUISITES) or any(
            not isinstance(value, bool) for value in prerequisites.values()
        ):
            raise AcquisitionControlError(
                "capability_decision_prerequisites_invalid"
            )
        return cls(
            decision_id=expected_id,
            decision_digest=digest,
            proposal_ref=_compact_ref(raw.get("proposal_ref")),
            derived_capability=_optional_capability(raw.get("derived_capability")),
            advisory_proposal_match_status=_required_token(
                raw.get("advisory_proposal_match_status"),
                "advisory_match_status_missing",
            ),
            prerequisite_evaluation=_json_clone(prerequisites),
            decision_status=decision_status,
            block_code=block_code,
            material_shape_interpretation=_required_token(
                raw.get("material_shape_interpretation"),
                "material_shape_interpretation_missing",
                limit=180,
            ),
            operation_identity_key=_optional_token(
                raw.get("operation_identity_key"), limit=180
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_clone(
            {
                "schema_version": self.schema_version,
                "decision_id": self.decision_id,
                "decision_digest": self.decision_digest,
                "proposal_ref": self.proposal_ref,
                "derived_capability": self.derived_capability,
                "advisory_proposal_match_status": (
                    self.advisory_proposal_match_status
                ),
                "prerequisite_evaluation": self.prerequisite_evaluation,
                "decision_status": self.decision_status,
                "block_code": self.block_code,
                "material_shape_interpretation": (
                    self.material_shape_interpretation
                ),
                "operation_identity_key": self.operation_identity_key,
                "authority_posture": self.authority_posture,
            }
        )

    def ref(self) -> dict[str, str]:
        return {
            "decision_id": self.decision_id,
            "decision_digest": self.decision_digest,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionWorkOrderV1:
    work_order_id: str
    work_order_digest: str
    accepted_capability_observation_ref: Mapping[str, Any]
    runkernel_authorization_ref: Mapping[str, Any]
    answer_contract_ref: Mapping[str, Any]
    source_obligation_ref: Mapping[str, Any]
    component_ref: Mapping[str, Any]
    authorized_capability: str
    candidate_ref: Mapping[str, Any]
    selected_urls: tuple[str, ...]
    root_url: str | None
    bounded_focus: Mapping[str, Any]
    include_domains: tuple[str, ...]
    exclude_domains: tuple[str, ...]
    include_path_prefix: str | None
    exclude_path_prefixes: tuple[str, ...]
    hard_operation_bounds: Mapping[str, Any]
    parent_acquisition_job_refs: tuple[Mapping[str, Any], ...]
    routing_policy_ref: Mapping[str, Any]
    operation_identity_key: str
    origin: str | None = None
    destination_binding_ref: Mapping[str, Any] = field(default_factory=dict)
    duplicate_check: str = "clear"
    exhaustion_check: str = "clear"
    schema_version: str = ACQUISITION_WORK_ORDER_SCHEMA_VERSION
    authority_posture: str = WORK_ORDER_AUTHORITY_POSTURE

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AcquisitionWorkOrderV1":
        raw = _mapping(value, "work_order_mapping_required")
        _reject_unknown_fields(raw, _WORK_ORDER_FIELDS, "work_order")
        if raw.get("schema_version") != ACQUISITION_WORK_ORDER_SCHEMA_VERSION:
            raise AcquisitionControlError("work_order_schema_invalid")
        core = {
            key: _json_clone(raw.get(key))
            for key in raw
            if key not in {"work_order_id", "work_order_digest"}
        }
        digest = stable_json_digest(core)
        decision_id = _required_token(
            _mapping(
                raw.get("accepted_capability_observation_ref"),
                "work_order_decision_ref_missing",
            ).get("decision_id"),
            "work_order_decision_id_missing",
            limit=300,
        )
        expected_id = f"acquisition-work-order:{decision_id}:{digest[:20]}"
        if raw.get("work_order_digest") != digest or raw.get("work_order_id") != expected_id:
            raise AcquisitionControlError("work_order_identity_mismatch")
        if raw.get("authority_posture") != WORK_ORDER_AUTHORITY_POSTURE:
            raise AcquisitionControlError("work_order_authority_posture_invalid")
        if raw.get("duplicate_check") != "clear":
            raise AcquisitionControlError("work_order_duplicate_check_invalid")
        if raw.get("exhaustion_check") != "clear":
            raise AcquisitionControlError("work_order_exhaustion_check_invalid")
        candidate_ref = _candidate_ref(raw.get("candidate_ref"))
        selected_urls = tuple(
            _required_url(url, "work_order_url_invalid")
            for url in _sequence(raw.get("selected_urls"))
        )
        origin_fields = _acquisition_origin_fields(
            origin=raw.get("origin"),
            destination_binding_ref=raw.get("destination_binding_ref"),
            candidate_ref=candidate_ref,
            available_urls=selected_urls,
            root_url=raw.get("root_url"),
            requested_material_shape=(
                "explicit_known_url"
                if raw.get("origin") == SEARCHOS_NAVIGATION_ORIGIN
                else "ordinary_single_page"
            ),
        )
        if origin_fields and raw.get("authorized_capability") != AcquisitionCapability.READ.value:
            raise AcquisitionControlError("navigation_work_order_capability_invalid")
        return cls(
            work_order_id=expected_id,
            work_order_digest=digest,
            accepted_capability_observation_ref=_compact_ref(
                raw.get("accepted_capability_observation_ref")
            ),
            runkernel_authorization_ref=_compact_ref(
                raw.get("runkernel_authorization_ref")
            ),
            answer_contract_ref=_contract_ref(raw.get("answer_contract_ref")),
            source_obligation_ref=_source_obligation_ref(
                raw.get("source_obligation_ref")
            ),
            component_ref=_component_ref(raw.get("component_ref")),
            authorized_capability=_required_token(
                raw.get("authorized_capability"),
                "work_order_capability_missing",
            ),
            candidate_ref=candidate_ref,
            selected_urls=selected_urls,
            root_url=(
                _required_url(raw.get("root_url"), "work_order_root_invalid")
                if raw.get("root_url")
                else None
            ),
            bounded_focus=_bounded_focus(raw.get("bounded_focus")),
            include_domains=tuple(_tokens(raw.get("include_domains"), limit=260)),
            exclude_domains=tuple(_tokens(raw.get("exclude_domains"), limit=260)),
            include_path_prefix=_optional_path(raw.get("include_path_prefix")),
            exclude_path_prefixes=tuple(_paths(raw.get("exclude_path_prefixes"))),
            hard_operation_bounds=_bounded_int_mapping(
                raw.get("hard_operation_bounds")
            ),
            parent_acquisition_job_refs=tuple(
                _compact_ref(item)
                for item in _sequence(raw.get("parent_acquisition_job_refs"))
            ),
            routing_policy_ref=_routing_policy_ref(raw.get("routing_policy_ref")),
            operation_identity_key=_required_token(
                raw.get("operation_identity_key"),
                "operation_identity_key_missing",
                limit=180,
            ),
            origin=origin_fields.get("origin"),
            destination_binding_ref=_json_clone(
                origin_fields.get("destination_binding_ref") or {}
            ),
            duplicate_check=_required_token(
                raw.get("duplicate_check"), "duplicate_check_missing"
            ),
            exhaustion_check=_required_token(
                raw.get("exhaustion_check"), "exhaustion_check_missing"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_clone(
            {
                "schema_version": self.schema_version,
                "work_order_id": self.work_order_id,
                "work_order_digest": self.work_order_digest,
                "accepted_capability_observation_ref": (
                    self.accepted_capability_observation_ref
                ),
                "runkernel_authorization_ref": self.runkernel_authorization_ref,
                "answer_contract_ref": self.answer_contract_ref,
                "source_obligation_ref": self.source_obligation_ref,
                "component_ref": self.component_ref,
                "authorized_capability": self.authorized_capability,
                **(
                    {
                        "origin": self.origin,
                        "destination_binding_ref": self.destination_binding_ref,
                    }
                    if self.origin is not None
                    else {}
                ),
                "candidate_ref": self.candidate_ref,
                "selected_urls": list(self.selected_urls),
                "root_url": self.root_url,
                "bounded_focus": self.bounded_focus,
                "include_domains": list(self.include_domains),
                "exclude_domains": list(self.exclude_domains),
                "include_path_prefix": self.include_path_prefix,
                "exclude_path_prefixes": list(self.exclude_path_prefixes),
                "hard_operation_bounds": self.hard_operation_bounds,
                "parent_acquisition_job_refs": list(
                    self.parent_acquisition_job_refs
                ),
                "routing_policy_ref": self.routing_policy_ref,
                "operation_identity_key": self.operation_identity_key,
                "duplicate_check": self.duplicate_check,
                "exhaustion_check": self.exhaustion_check,
                "authority_posture": self.authority_posture,
            }
        )

    def ref(self) -> dict[str, str]:
        return {
            "work_order_id": self.work_order_id,
            "work_order_digest": self.work_order_digest,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionRouteObservationV1:
    route_observation_id: str
    route_observation_digest: str
    work_order_ref: Mapping[str, Any]
    completed_route_decision_ref: Mapping[str, Any]
    selected_provider: str | None
    selected_operation: str | None
    selected_variant: str | None
    selected_output_type: str | None
    routing_policy_ref: Mapping[str, Any]
    availability_snapshot_ref: Mapping[str, Any]
    terminal_status: str
    block_code: str | None
    schema_version: str = ACQUISITION_ROUTE_OBSERVATION_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        work_order_ref: Mapping[str, Any],
        route_decision_trace: Mapping[str, Any],
        routing_policy_ref: Mapping[str, Any],
        availability_snapshot_ref: Mapping[str, Any],
    ) -> "AcquisitionRouteObservationV1":
        route_trace = _json_clone(
            _mapping(route_decision_trace, "route_decision_trace_missing")
        )
        policy_ref = _routing_policy_ref(routing_policy_ref)
        decision_digest = stable_json_digest(
            {"routing_policy_ref": policy_ref, "route_decision": route_trace}
        )
        work_ref = _compact_ref(work_order_ref)
        work_id = _required_token(
            work_ref.get("work_order_id"), "route_work_order_id_missing", limit=300
        )
        decision_ref = {
            "route_decision_id": f"provider-route-decision:{work_id}:{decision_digest[:20]}",
            "route_decision_digest": decision_digest,
        }
        blocked = str(route_trace.get("fidelity") or "").casefold() == "blocked"
        core = {
            "schema_version": ACQUISITION_ROUTE_OBSERVATION_SCHEMA_VERSION,
            "work_order_ref": work_ref,
            "completed_route_decision_ref": decision_ref,
            "selected_provider": route_trace.get("selected_provider"),
            "selected_operation": route_trace.get("operation"),
            "selected_variant": route_trace.get("variant"),
            "selected_output_type": route_trace.get("output_type"),
            "routing_policy_ref": policy_ref,
            "availability_snapshot_ref": _compact_ref(
                availability_snapshot_ref
            ),
            "terminal_status": "blocked" if blocked else "selected",
            "block_code": route_trace.get("block_reason") if blocked else None,
        }
        digest = stable_json_digest(core)
        payload = {
            **core,
            "route_observation_id": f"acquisition-route:{work_id}:{digest[:20]}",
            "route_observation_digest": digest,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AcquisitionRouteObservationV1":
        raw = _mapping(value, "route_observation_mapping_required")
        _reject_unknown_fields(raw, _ROUTE_FIELDS, "route_observation")
        if raw.get("schema_version") != ACQUISITION_ROUTE_OBSERVATION_SCHEMA_VERSION:
            raise AcquisitionControlError("route_observation_schema_invalid")
        core = {
            key: _json_clone(raw.get(key))
            for key in raw
            if key not in {"route_observation_id", "route_observation_digest"}
        }
        digest = stable_json_digest(core)
        work_id = _required_token(
            _mapping(raw.get("work_order_ref"), "route_work_order_ref_missing").get(
                "work_order_id"
            ),
            "route_work_order_id_missing",
            limit=300,
        )
        expected_id = f"acquisition-route:{work_id}:{digest[:20]}"
        if raw.get("route_observation_digest") != digest or raw.get("route_observation_id") != expected_id:
            raise AcquisitionControlError("route_observation_identity_mismatch")
        status = _required_token(
            raw.get("terminal_status"), "route_terminal_status_missing"
        )
        if status not in {"selected", "blocked"}:
            raise AcquisitionControlError("route_terminal_status_invalid")
        provider = _optional_token(raw.get("selected_provider"), limit=80)
        if (status == "selected") != bool(provider):
            raise AcquisitionControlError("route_selected_provider_status_mismatch")
        block_code = _optional_token(raw.get("block_code"), limit=180)
        if (status == "blocked") != bool(block_code):
            raise AcquisitionControlError("route_block_status_mismatch")
        return cls(
            route_observation_id=expected_id,
            route_observation_digest=digest,
            work_order_ref=_compact_ref(raw.get("work_order_ref")),
            completed_route_decision_ref=_compact_ref(
                raw.get("completed_route_decision_ref")
            ),
            selected_provider=provider,
            selected_operation=_optional_token(raw.get("selected_operation"), limit=80),
            selected_variant=_optional_token(raw.get("selected_variant"), limit=80),
            selected_output_type=_optional_token(
                raw.get("selected_output_type"), limit=100
            ),
            routing_policy_ref=_routing_policy_ref(raw.get("routing_policy_ref")),
            availability_snapshot_ref=_compact_ref(
                raw.get("availability_snapshot_ref")
            ),
            terminal_status=status,
            block_code=block_code,
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_clone(
            {
                "schema_version": self.schema_version,
                "route_observation_id": self.route_observation_id,
                "route_observation_digest": self.route_observation_digest,
                "work_order_ref": self.work_order_ref,
                "completed_route_decision_ref": self.completed_route_decision_ref,
                "selected_provider": self.selected_provider,
                "selected_operation": self.selected_operation,
                "selected_variant": self.selected_variant,
                "selected_output_type": self.selected_output_type,
                "routing_policy_ref": self.routing_policy_ref,
                "availability_snapshot_ref": self.availability_snapshot_ref,
                "terminal_status": self.terminal_status,
                "block_code": self.block_code,
            }
        )

    def ref(self) -> dict[str, str]:
        return {
            "route_observation_id": self.route_observation_id,
            "route_observation_digest": self.route_observation_digest,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionExecutionObservationV1:
    execution_observation_id: str
    execution_observation_digest: str
    work_order_ref: Mapping[str, Any]
    completed_route_ref: Mapping[str, Any]
    execution_result_ref: Mapping[str, Any]
    artifact_refs: tuple[Mapping[str, Any], ...]
    provider_calls_attempted: int
    provider_calls_completed: int
    terminal_status: str
    failure_or_block_code: str | None
    schema_version: str = ACQUISITION_EXECUTION_OBSERVATION_SCHEMA_VERSION
    provider_failure_fallback_attempted: bool = False
    capability_switch_attempted: bool = False
    downstream_authority_granted: bool = False

    @classmethod
    def create(
        cls,
        *,
        work_order_ref: Mapping[str, Any],
        completed_route_ref: Mapping[str, Any],
        execution_result_trace: Mapping[str, Any],
        artifact_refs: Sequence[Mapping[str, Any]],
        provider_calls_attempted: int,
        provider_calls_completed: int,
        terminal_status: str,
        failure_or_block_code: str | None,
    ) -> "AcquisitionExecutionObservationV1":
        work_ref = _compact_ref(work_order_ref)
        work_id = _required_token(
            work_ref.get("work_order_id"),
            "execution_work_order_id_missing",
            limit=300,
        )
        result_trace = _json_clone(execution_result_trace)
        result_digest = stable_json_digest(result_trace)
        result_ref = {
            "execution_result_id": f"acquisition-execution-result:{work_id}:{result_digest[:20]}",
            "execution_result_digest": result_digest,
        }
        core = {
            "schema_version": ACQUISITION_EXECUTION_OBSERVATION_SCHEMA_VERSION,
            "work_order_ref": work_ref,
            "completed_route_ref": _compact_ref(completed_route_ref),
            "execution_result_ref": result_ref,
            "artifact_refs": [
                _artifact_observation_ref(item) for item in artifact_refs
            ],
            "provider_calls_attempted": int(provider_calls_attempted),
            "provider_calls_completed": int(provider_calls_completed),
            "terminal_status": _required_token(
                terminal_status, "execution_terminal_status_missing"
            ),
            "failure_or_block_code": _optional_token(
                failure_or_block_code, limit=180
            ),
            "provider_failure_fallback_attempted": False,
            "capability_switch_attempted": False,
            "downstream_authority_granted": False,
        }
        digest = stable_json_digest(core)
        payload = {
            **core,
            "execution_observation_id": f"acquisition-execution:{work_id}:{digest[:20]}",
            "execution_observation_digest": digest,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "AcquisitionExecutionObservationV1":
        raw = _mapping(value, "execution_observation_mapping_required")
        _reject_unknown_fields(raw, _EXECUTION_FIELDS, "execution_observation")
        if raw.get("schema_version") != ACQUISITION_EXECUTION_OBSERVATION_SCHEMA_VERSION:
            raise AcquisitionControlError("execution_observation_schema_invalid")
        for false_key in (
            "provider_failure_fallback_attempted",
            "capability_switch_attempted",
            "downstream_authority_granted",
        ):
            if raw.get(false_key) is not False:
                raise AcquisitionControlError("execution_observation_authority_invalid")
        work_ref = _compact_ref(raw.get("work_order_ref"))
        route_ref = _compact_ref(raw.get("completed_route_ref"))
        result_ref = _execution_result_ref(raw.get("execution_result_ref"))
        artifact_refs = [
            _artifact_observation_ref(item)
            for item in _sequence(raw.get("artifact_refs"))
        ]
        work_id = _required_token(
            work_ref.get("work_order_id"),
            "execution_work_order_id_missing",
            limit=300,
        )
        if result_ref.get("execution_result_id") != (
            f"acquisition-execution-result:{work_id}:"
            f"{str(result_ref.get('execution_result_digest'))[:20]}"
        ):
            raise AcquisitionControlError("execution_result_ref_identity_invalid")
        for artifact_ref in artifact_refs:
            artifact_job_id = str(
                artifact_ref.get("acquisition_job_id") or ""
            )
            if artifact_job_id != work_id or artifact_ref.get(
                "artifact_id"
            ) != (
                f"acquisition-artifact:{artifact_job_id}:"
                f"{str(artifact_ref.get('artifact_digest'))[:20]}"
            ):
                raise AcquisitionControlError("artifact_ref_identity_invalid")
        attempted = _nonnegative_int(raw.get("provider_calls_attempted"))
        completed = _nonnegative_int(raw.get("provider_calls_completed"))
        if attempted > 1 or completed > attempted:
            raise AcquisitionControlError("execution_call_counts_invalid")
        terminal_status = _required_token(
            raw.get("terminal_status"), "execution_terminal_status_missing"
        )
        if terminal_status not in {"completed", "failed", "blocked"}:
            raise AcquisitionControlError("execution_terminal_status_invalid")
        failure_code = _optional_token(
            raw.get("failure_or_block_code"), limit=180
        )
        if (terminal_status == "completed") == bool(failure_code):
            raise AcquisitionControlError("execution_failure_status_mismatch")
        if terminal_status == "completed" and (
            attempted != 1
            or completed != 1
            or not artifact_refs
            or any(
                item.get("status") == "failed"
                or item.get("failure_code")
                for item in artifact_refs
            )
        ):
            raise AcquisitionControlError(
                "completed_execution_material_invalid"
            )
        if terminal_status == "blocked" and (attempted or completed):
            raise AcquisitionControlError("blocked_execution_call_count_invalid")
        core = {
            "schema_version": ACQUISITION_EXECUTION_OBSERVATION_SCHEMA_VERSION,
            "work_order_ref": work_ref,
            "completed_route_ref": route_ref,
            "execution_result_ref": result_ref,
            "artifact_refs": artifact_refs,
            "provider_calls_attempted": attempted,
            "provider_calls_completed": completed,
            "terminal_status": terminal_status,
            "failure_or_block_code": failure_code,
            "provider_failure_fallback_attempted": False,
            "capability_switch_attempted": False,
            "downstream_authority_granted": False,
        }
        digest = stable_json_digest(core)
        expected_id = f"acquisition-execution:{work_id}:{digest[:20]}"
        if (
            raw.get("execution_observation_digest") != digest
            or raw.get("execution_observation_id") != expected_id
        ):
            raise AcquisitionControlError(
                "execution_observation_identity_mismatch"
            )
        return cls(
            execution_observation_id=expected_id,
            execution_observation_digest=digest,
            work_order_ref=work_ref,
            completed_route_ref=route_ref,
            execution_result_ref=result_ref,
            artifact_refs=tuple(artifact_refs),
            provider_calls_attempted=attempted,
            provider_calls_completed=completed,
            terminal_status=terminal_status,
            failure_or_block_code=failure_code,
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_clone(
            {
                "schema_version": self.schema_version,
                "execution_observation_id": self.execution_observation_id,
                "execution_observation_digest": self.execution_observation_digest,
                "work_order_ref": self.work_order_ref,
                "completed_route_ref": self.completed_route_ref,
                "execution_result_ref": self.execution_result_ref,
                "artifact_refs": list(self.artifact_refs),
                "provider_calls_attempted": self.provider_calls_attempted,
                "provider_calls_completed": self.provider_calls_completed,
                "terminal_status": self.terminal_status,
                "failure_or_block_code": self.failure_or_block_code,
                "provider_failure_fallback_attempted": False,
                "capability_switch_attempted": False,
                "downstream_authority_granted": False,
            }
        )

    def ref(self) -> dict[str, str]:
        return {
            "execution_observation_id": self.execution_observation_id,
            "execution_observation_digest": self.execution_observation_digest,
        }


@dataclass(frozen=True, slots=True)
class AcquisitionTerminalReceiptV1:
    receipt_id: str
    receipt_digest: str
    operation_identity_key: str
    capability: str | None
    terminal_status: str
    block_or_failure_code: str | None
    work_order_ref: Mapping[str, Any]
    route_observation_ref: Mapping[str, Any]
    execution_observation_ref: Mapping[str, Any]
    source_obligation_ref: Mapping[str, Any]
    retry_licensed: bool = False
    active_slot_released: bool = True
    schema_version: str = ACQUISITION_TERMINAL_RECEIPT_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        operation_identity_key: str,
        capability: str | None,
        terminal_status: str,
        block_or_failure_code: str | None,
        source_obligation_ref: Mapping[str, Any],
        work_order_ref: Mapping[str, Any] | None = None,
        route_observation_ref: Mapping[str, Any] | None = None,
        execution_observation_ref: Mapping[str, Any] | None = None,
    ) -> "AcquisitionTerminalReceiptV1":
        operation_key = _required_token(
            operation_identity_key, "terminal_operation_identity_missing", limit=180
        )
        core = {
            "schema_version": ACQUISITION_TERMINAL_RECEIPT_SCHEMA_VERSION,
            "operation_identity_key": operation_key,
            "capability": _optional_capability(capability),
            "terminal_status": _required_token(
                terminal_status, "terminal_status_missing"
            ),
            "block_or_failure_code": _optional_token(
                block_or_failure_code, limit=180
            ),
            "work_order_ref": _compact_ref(work_order_ref),
            "route_observation_ref": _compact_ref(route_observation_ref),
            "execution_observation_ref": _compact_ref(
                execution_observation_ref
            ),
            "source_obligation_ref": _source_obligation_ref(
                source_obligation_ref
            ),
            "retry_licensed": False,
            "active_slot_released": True,
        }
        digest = stable_json_digest(core)
        payload = {
            **core,
            "receipt_id": f"acquisition-terminal:{operation_key}:{digest[:20]}",
            "receipt_digest": digest,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AcquisitionTerminalReceiptV1":
        raw = _mapping(value, "terminal_receipt_mapping_required")
        _reject_unknown_fields(raw, _TERMINAL_RECEIPT_FIELDS, "terminal_receipt")
        if raw.get("schema_version") != ACQUISITION_TERMINAL_RECEIPT_SCHEMA_VERSION:
            raise AcquisitionControlError("terminal_receipt_schema_invalid")
        if raw.get("retry_licensed") is not False or raw.get("active_slot_released") is not True:
            raise AcquisitionControlError("terminal_receipt_posture_invalid")
        core = {
            key: _json_clone(raw.get(key))
            for key in raw
            if key not in {"receipt_id", "receipt_digest"}
        }
        digest = stable_json_digest(core)
        key = _required_token(
            raw.get("operation_identity_key"),
            "terminal_operation_identity_missing",
            limit=180,
        )
        expected_id = f"acquisition-terminal:{key}:{digest[:20]}"
        if raw.get("receipt_digest") != digest or raw.get("receipt_id") != expected_id:
            raise AcquisitionControlError("terminal_receipt_identity_mismatch")
        terminal_status = _required_token(
            raw.get("terminal_status"), "terminal_status_missing"
        )
        if terminal_status not in {"completed", "failed", "blocked"}:
            raise AcquisitionControlError("terminal_receipt_status_invalid")
        failure_code = _optional_token(
            raw.get("block_or_failure_code"), limit=180
        )
        if (terminal_status == "completed") == bool(failure_code):
            raise AcquisitionControlError("terminal_receipt_failure_status_mismatch")
        return cls(
            receipt_id=expected_id,
            receipt_digest=digest,
            operation_identity_key=key,
            capability=_optional_capability(raw.get("capability")),
            terminal_status=terminal_status,
            block_or_failure_code=failure_code,
            work_order_ref=_compact_ref(raw.get("work_order_ref")),
            route_observation_ref=_compact_ref(
                raw.get("route_observation_ref")
            ),
            execution_observation_ref=_compact_ref(
                raw.get("execution_observation_ref")
            ),
            source_obligation_ref=_source_obligation_ref(
                raw.get("source_obligation_ref")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_clone(
            {
                "schema_version": self.schema_version,
                "receipt_id": self.receipt_id,
                "receipt_digest": self.receipt_digest,
                "operation_identity_key": self.operation_identity_key,
                "capability": self.capability,
                "terminal_status": self.terminal_status,
                "block_or_failure_code": self.block_or_failure_code,
                "work_order_ref": self.work_order_ref,
                "route_observation_ref": self.route_observation_ref,
                "execution_observation_ref": self.execution_observation_ref,
                "source_obligation_ref": self.source_obligation_ref,
                "retry_licensed": False,
                "active_slot_released": True,
            }
        )

    def ref(self) -> dict[str, str]:
        return {"receipt_id": self.receipt_id, "receipt_digest": self.receipt_digest}


@dataclass(frozen=True, slots=True)
class AcquisitionCustodyAuthorizationV1:
    authorization_id: str
    authorization_digest: str
    work_order_ref: Mapping[str, Any]
    route_observation_ref: Mapping[str, Any]
    terminal_receipt_ref: Mapping[str, Any]
    answer_contract_ref: Mapping[str, Any]
    source_obligation_ref: Mapping[str, Any]
    capability: str
    custody_consumer: str
    schema_version: str = ACQUISITION_CUSTODY_AUTHORIZATION_SCHEMA_VERSION
    downstream_authority_granted: bool = False

    @classmethod
    def create(
        cls,
        *,
        work_order_ref: Mapping[str, Any],
        route_observation_ref: Mapping[str, Any],
        terminal_receipt_ref: Mapping[str, Any],
        answer_contract_ref: Mapping[str, Any],
        source_obligation_ref: Mapping[str, Any],
        capability: str,
        custody_consumer: str,
    ) -> "AcquisitionCustodyAuthorizationV1":
        receipt_ref = _compact_ref(terminal_receipt_ref)
        receipt_id = _required_token(
            receipt_ref.get("receipt_id"), "custody_receipt_id_missing", limit=300
        )
        core = {
            "schema_version": ACQUISITION_CUSTODY_AUTHORIZATION_SCHEMA_VERSION,
            "work_order_ref": _compact_ref(work_order_ref),
            "route_observation_ref": _compact_ref(route_observation_ref),
            "terminal_receipt_ref": receipt_ref,
            "answer_contract_ref": _contract_ref(answer_contract_ref),
            "source_obligation_ref": _source_obligation_ref(source_obligation_ref),
            "capability": _required_token(capability, "custody_capability_missing"),
            "custody_consumer": _required_token(
                custody_consumer, "custody_consumer_missing", limit=240
            ),
            "downstream_authority_granted": False,
        }
        digest = stable_json_digest(core)
        payload = {
            **core,
            "authorization_id": f"acquisition-custody:{receipt_id}:{digest[:20]}",
            "authorization_digest": digest,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "AcquisitionCustodyAuthorizationV1":
        raw = _mapping(value, "custody_authorization_mapping_required")
        _reject_unknown_fields(
            raw, _CUSTODY_AUTHORIZATION_FIELDS, "custody_authorization"
        )
        if raw.get("schema_version") != ACQUISITION_CUSTODY_AUTHORIZATION_SCHEMA_VERSION:
            raise AcquisitionControlError("custody_authorization_schema_invalid")
        if raw.get("downstream_authority_granted") is not False:
            raise AcquisitionControlError("custody_authorization_posture_invalid")
        core = {
            key: _json_clone(raw.get(key))
            for key in raw
            if key not in {"authorization_id", "authorization_digest"}
        }
        digest = stable_json_digest(core)
        receipt_id = _required_token(
            _mapping(
                raw.get("terminal_receipt_ref"), "custody_receipt_ref_missing"
            ).get("receipt_id"),
            "custody_receipt_id_missing",
            limit=300,
        )
        expected_id = f"acquisition-custody:{receipt_id}:{digest[:20]}"
        if raw.get("authorization_digest") != digest or raw.get("authorization_id") != expected_id:
            raise AcquisitionControlError("custody_authorization_identity_mismatch")
        return cls(
            authorization_id=expected_id,
            authorization_digest=digest,
            work_order_ref=_compact_ref(raw.get("work_order_ref")),
            route_observation_ref=_compact_ref(
                raw.get("route_observation_ref")
            ),
            terminal_receipt_ref=_compact_ref(raw.get("terminal_receipt_ref")),
            answer_contract_ref=_contract_ref(raw.get("answer_contract_ref")),
            source_obligation_ref=_source_obligation_ref(
                raw.get("source_obligation_ref")
            ),
            capability=_required_token(
                raw.get("capability"), "custody_capability_missing"
            ),
            custody_consumer=_required_token(
                raw.get("custody_consumer"), "custody_consumer_missing", limit=240
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return _json_clone(
            {
                "schema_version": self.schema_version,
                "authorization_id": self.authorization_id,
                "authorization_digest": self.authorization_digest,
                "work_order_ref": self.work_order_ref,
                "route_observation_ref": self.route_observation_ref,
                "terminal_receipt_ref": self.terminal_receipt_ref,
                "answer_contract_ref": self.answer_contract_ref,
                "source_obligation_ref": self.source_obligation_ref,
                "capability": self.capability,
                "custody_consumer": self.custody_consumer,
                "downstream_authority_granted": False,
            }
        )

    def ref(self) -> dict[str, str]:
        return {
            "authorization_id": self.authorization_id,
            "authorization_digest": self.authorization_digest,
        }


def initial_acquisition_control_state(*, run_id: str, request_id: str) -> dict[str, Any]:
    return {
        "schema_version": ACQUISITION_CONTROL_STATE_SCHEMA_VERSION,
        "owner": "RunKernel",
        "canonical_state": True,
        "run_id": run_id,
        "request_id": request_id,
        "proposals_by_id": {},
        "capability_decisions_by_id": {},
        "work_orders_by_id": {},
        "routes_by_id": {},
        "execution_authorizations_by_id": {},
        "execution_observations_by_id": {},
        "active_by_source_obligation": {},
        "terminal_receipts_by_operation_key": {},
        "exhausted_operation_keys": {},
        "custody_authorizations_by_receipt": {},
        "event_history": [],
        "provider_selection_owner": "core.routing",
        "mechanical_adapter_owner": "core.acquisition_adapters",
        "provider_failure_fallback_licensed": False,
        "capability_switch_after_failure_licensed": False,
    }


def ensure_acquisition_control_state(
    state: Mapping[str, Any] | None, *, run_id: str, request_id: str
) -> dict[str, Any]:
    if not state:
        return initial_acquisition_control_state(run_id=run_id, request_id=request_id)
    safe = _json_clone(state)
    if (
        safe.get("schema_version") != ACQUISITION_CONTROL_STATE_SCHEMA_VERSION
        or safe.get("owner") != "RunKernel"
        or safe.get("canonical_state") is not True
        or safe.get("run_id") != run_id
        or safe.get("request_id") != request_id
    ):
        raise AcquisitionControlError("acquisition_control_state_identity_mismatch")
    return safe


def _canonical_source_obligation_descriptor(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Remove component-local lineage from the shared governed descriptor."""

    descriptor = _json_clone(value)
    metadata = _mapping(descriptor.get("metadata"), "")
    metadata.pop("accepted_component_id", None)
    if metadata:
        descriptor["metadata"] = metadata
    else:
        descriptor.pop("metadata", None)
    return descriptor


def build_pre_acquisition_source_obligation_ref(
    *,
    answer_contract_ref: Mapping[str, Any],
    source_obligation_id: str,
    source_obligation_descriptor: Mapping[str, Any],
    component_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the acquisition owner's compact active-obligation lineage ref."""

    contract_ref = _contract_ref(answer_contract_ref)
    obligation_id = _required_token(
        source_obligation_id,
        "source_obligation_id_missing",
        limit=200,
    )
    descriptor = _canonical_source_obligation_descriptor(
        _mapping(
            source_obligation_descriptor,
            "source_obligation_descriptor_invalid",
        )
    )
    components = sorted(
        (
            _component_ref(_mapping(value, "component_mapping_required"))
            for value in component_refs
        ),
        key=lambda value: (
            str(value.get("component_id") or ""),
            str(value.get("component_revision") or ""),
            str(value.get("component_digest") or ""),
        ),
    )
    if not components:
        raise AcquisitionControlError("source_obligation_component_missing")
    component_ids = [str(value.get("component_id") or "") for value in components]
    if len(component_ids) != len(set(component_ids)):
        raise AcquisitionControlError("source_obligation_component_duplicate")
    binding_core = {
        "binding_kind": "pre_acquisition_source_obligation_lineage",
        "answer_contract_ref": contract_ref,
        "source_obligation_id": obligation_id,
        "source_obligation_descriptor": descriptor,
        "component_refs": components,
        "source_authority_granted": False,
        "source_obligation_satisfied": False,
    }
    return {
        "source_obligation_id": obligation_id,
        "source_obligation_digest": stable_json_digest(binding_core),
        "binding_kind": binding_core["binding_kind"],
        "answer_contract_digest": contract_ref["contract_digest"],
        "component_ids": component_ids,
        "active": True,
    }


def build_acquisition_authority_snapshot(
    *,
    run_id: str,
    request_id: str,
    current_answer_contract: Mapping[str, Any] | None,
    initial_answer_contract: Mapping[str, Any] | None = None,
    search_executor_handoff_state: Mapping[str, Any],
    search_work_plan: Mapping[str, Any] | None = None,
    allow_no_dispatch_planning_snapshot: bool = False,
) -> dict[str, Any]:
    current = _json_clone(current_answer_contract or {})
    initial = _json_clone(initial_answer_contract or {})
    contract = _mapping(
        current or initial,
        "active_answer_contract_missing",
    )
    contract_source = (
        "current_answer_contract" if current else "initial_answer_contract"
    )
    contract_ref = _contract_ref(
        {
            "source": contract_source,
            "contract_version": contract.get("accepted_contract_version"),
            "contract_digest": contract.get("accepted_contract_digest"),
        }
    )
    components: dict[str, dict[str, Any]] = {}
    obligation_to_components: dict[str, list[dict[str, Any]]] = {}
    for raw_component in _sequence(contract.get("accepted_answer_component_refs")):
        raw_component_mapping = _mapping(
            raw_component, "component_mapping_required"
        )
        if "direct" not in _tokens(
            raw_component_mapping.get("allowed_support_kinds") or ("direct",),
            limit=80,
        ):
            continue
        component = _component_ref(
            {
                "component_id": raw_component_mapping.get("component_id"),
                "component_revision": raw_component_mapping.get(
                    "component_revision"
                ),
                "component_digest": raw_component_mapping.get(
                    "component_digest"
                ),
            }
        )
        if not component:
            continue
        component_id = str(component["component_id"])
        if component_id in components:
            raise AcquisitionControlError("duplicate_answer_component_id")
        components[component_id] = component
        source_ids = _tokens(
            raw_component_mapping.get(
                "source_obligation_candidate_ids"
            ),
            limit=200,
        )
        for source_id in source_ids:
            obligation_to_components.setdefault(source_id, []).append(component)

    handoff = _mapping(
        search_executor_handoff_state, "search_executor_handoff_state_missing"
    )
    no_dispatch_planning = bool(
        allow_no_dispatch_planning_snapshot and not handoff
    )
    if not no_dispatch_planning and (
        handoff.get("run_id") != run_id
        or handoff.get("request_id") != request_id
    ):
        raise AcquisitionControlError("search_executor_handoff_identity_mismatch")
    if (
        handoff.get("origin_kind") == "ordinary_query_provider"
        or no_dispatch_planning
    ):
        if (
            not no_dispatch_planning
            and _contract_ref(handoff.get("answer_contract_ref"))
            != contract_ref
        ):
            raise AcquisitionControlError(
                "ordinary_search_executor_handoff_contract_ref_mismatch"
            )
        work_plan = _mapping(search_work_plan, "search_work_plan_missing")
        accepted_ref = _mapping(
            _mapping(
                work_plan.get("metadata"),
                "search_work_plan_metadata_missing",
            ).get("accepted_contract_ref"),
            "search_work_plan_contract_ref_missing",
        )
        if not (
            str(accepted_ref.get("contract_version") or "")
            == str(contract_ref.get("contract_version") or "")
            and accepted_ref.get("contract_digest")
            == contract_ref.get("contract_digest")
            and accepted_ref.get("parent_kind") == contract_source
        ):
            raise AcquisitionControlError("search_work_plan_contract_ref_mismatch")
        obligation_occurrences: dict[str, dict[str, Any]] = {}
        seen_component_ids: set[str] = set()
        for raw_work_component in _sequence(work_plan.get("components")):
            work_component = _mapping(
                raw_work_component, "search_work_component_mapping_required"
            )
            component_id = _required_token(
                work_component.get("component_id"),
                "search_work_component_id_missing",
                limit=200,
            )
            canonical_component = components.get(component_id)
            if canonical_component is None:
                raise AcquisitionControlError(
                    "search_work_component_not_in_active_contract"
                )
            raw_work_component_ref = _mapping(
                _mapping(
                    work_component.get("metadata"),
                    "search_work_component_metadata_missing",
                ).get("accepted_component_ref"),
                "search_work_component_ref_missing",
            )
            work_component_ref = _component_ref(
                {
                    "component_id": raw_work_component_ref.get("component_id"),
                    "component_revision": raw_work_component_ref.get(
                        "component_revision"
                    ),
                    "component_digest": raw_work_component_ref.get(
                        "component_digest"
                    ),
                }
            )
            if work_component_ref != canonical_component:
                raise AcquisitionControlError(
                    "search_work_component_ref_mismatch"
                )
            seen_component_ids.add(component_id)
            expected_obligation_ids = {
                obligation_id
                for obligation_id, component_refs in obligation_to_components.items()
                if component_id
                in {str(ref.get("component_id")) for ref in component_refs}
            }
            seen_obligation_ids: set[str] = set()
            for raw_obligation in _sequence(
                work_component.get("source_obligations")
            ):
                descriptor = _mapping(
                    raw_obligation, "source_obligation_descriptor_invalid"
                )
                obligation_id = _required_token(
                    descriptor.get("obligation_id"),
                    "source_obligation_descriptor_id_missing",
                    limit=200,
                )
                if obligation_id not in expected_obligation_ids:
                    raise AcquisitionControlError(
                        "search_work_source_obligation_not_in_active_contract"
                    )
                if obligation_id in seen_obligation_ids:
                    raise AcquisitionControlError(
                        "duplicate_source_obligation_in_component"
                    )
                governed_descriptor = (
                    _canonical_source_obligation_descriptor(descriptor)
                )
                occurrence = obligation_occurrences.get(obligation_id)
                if occurrence is None:
                    obligation_occurrences[obligation_id] = {
                        "descriptor": governed_descriptor,
                        "component_refs": [canonical_component],
                    }
                else:
                    if occurrence["descriptor"] != governed_descriptor:
                        raise AcquisitionControlError(
                            "shared_source_obligation_descriptor_conflict"
                        )
                    occurrence["component_refs"].append(canonical_component)
                seen_obligation_ids.add(obligation_id)
            if seen_obligation_ids != expected_obligation_ids:
                raise AcquisitionControlError(
                    "search_work_source_obligation_membership_mismatch"
                )
        if seen_component_ids != set(components):
            raise AcquisitionControlError(
                "search_work_component_membership_mismatch"
            )
        obligations: dict[str, dict[str, Any]] = {}
        for obligation_id in sorted(obligation_occurrences):
            occurrence = obligation_occurrences[obligation_id]
            expected_components = {
                str(value.get("component_id") or "")
                for value in obligation_to_components.get(obligation_id, ())
            }
            occurrence_components = {
                str(value.get("component_id") or "")
                for value in occurrence["component_refs"]
            }
            if occurrence_components != expected_components:
                raise AcquisitionControlError(
                    "shared_source_obligation_component_membership_mismatch"
                )
            obligations[obligation_id] = (
                build_pre_acquisition_source_obligation_ref(
                    answer_contract_ref=contract_ref,
                    source_obligation_id=obligation_id,
                    source_obligation_descriptor=occurrence["descriptor"],
                    component_refs=occurrence["component_refs"],
                )
            )
        snapshot_core = {
            "run_id": run_id,
            "request_id": request_id,
            "answer_contract_ref": contract_ref,
            "components_by_id": components,
            "source_obligations_by_id": obligations,
            "lineage_posture": (
                "pre_dispatch_planning_only_no_satisfaction_authority"
                if no_dispatch_planning
                else "pre_acquisition_only_no_satisfaction_authority"
            ),
        }
        return {
            **snapshot_core,
            "snapshot_digest": stable_json_digest(snapshot_core),
        }
    if handoff.get("contract_parent_kind") != "current_answer_contract":
        raise AcquisitionControlError("search_executor_handoff_contract_parent_stale")
    if contract_source != "current_answer_contract":
        raise AcquisitionControlError(
            "legacy_search_executor_handoff_requires_current_contract"
        )
    if _contract_ref(handoff.get("parent_current_contract_ref")) != contract_ref:
        raise AcquisitionControlError("search_executor_handoff_contract_ref_mismatch")
    descriptors: dict[str, dict[str, Any]] = {}
    for raw_descriptor in _sequence(
        handoff.get("source_obligation_candidate_refs")
    ):
        descriptor = _mapping(
            raw_descriptor, "source_obligation_descriptor_invalid"
        )
        descriptor_id = _required_token(
            descriptor.get("candidate_id"),
            "source_obligation_descriptor_id_missing",
            limit=200,
        )
        if descriptor_id in descriptors:
            raise AcquisitionControlError("duplicate_source_obligation_id")
        descriptors[descriptor_id] = _json_clone(descriptor)
    obligations: dict[str, dict[str, Any]] = {}
    for obligation_id, component_refs in obligation_to_components.items():
        descriptor = descriptors.get(obligation_id)
        if descriptor is None:
            raise AcquisitionControlError(
                "source_obligation_descriptor_missing"
            )
        descriptor_components = set(
            _tokens(descriptor.get("component_candidate_ids"), limit=200)
        )
        expected_components = {
            str(ref.get("component_id")) for ref in component_refs
        }
        if descriptor_components != expected_components:
            raise AcquisitionControlError(
                "source_obligation_descriptor_component_mismatch"
            )
        obligations[obligation_id] = build_pre_acquisition_source_obligation_ref(
            answer_contract_ref=contract_ref,
            source_obligation_id=obligation_id,
            source_obligation_descriptor=descriptor,
            component_refs=component_refs,
        )
    extra_descriptors = set(descriptors).difference(obligations)
    if extra_descriptors:
        raise AcquisitionControlError("unbound_source_obligation_descriptor")
    snapshot_core = {
        "run_id": run_id,
        "request_id": request_id,
        "answer_contract_ref": contract_ref,
        "components_by_id": components,
        "source_obligations_by_id": obligations,
        "lineage_posture": "pre_acquisition_only_no_satisfaction_authority",
    }
    return {
        **snapshot_core,
        "snapshot_digest": stable_json_digest(snapshot_core),
    }


def derive_acquisition_capability_decision(
    *,
    proposal: AcquisitionNeedProposalV1,
    authority_snapshot: Mapping[str, Any],
    acquisition_control_state: Mapping[str, Any],
) -> AcquisitionCapabilityDecisionObservationV1:
    snapshot = _mapping(authority_snapshot, "authority_snapshot_missing")
    state = _mapping(acquisition_control_state, "acquisition_control_state_missing")
    current_contract_ref = _mapping(
        snapshot.get("answer_contract_ref"), "snapshot_contract_ref_missing"
    )
    current_components = _mapping(
        snapshot.get("components_by_id"), "snapshot_components_missing"
    )
    current_obligations = _mapping(
        snapshot.get("source_obligations_by_id"),
        "snapshot_source_obligations_missing",
    )
    component_id = str(proposal.component_ref.get("component_id") or "")
    obligation_id = str(
        proposal.source_obligation_ref.get("source_obligation_id") or ""
    )
    contract_current = proposal.answer_contract_ref == current_contract_ref
    component_current = bool(component_id) and proposal.component_ref == _mapping(
        current_components.get(component_id), ""
    )
    obligation_current = bool(obligation_id) and proposal.source_obligation_ref == _mapping(
        current_obligations.get(obligation_id), ""
    )
    obligation_active = obligation_current and (
        proposal.source_obligation_ref.get("active") is True
    )

    derived, material_interpretation = _derive_capability_from_material(proposal)
    bounds_error: str | None = None
    if derived is not None:
        try:
            _hard_bounds_for_capability(derived, proposal.requested_bounds)
        except AcquisitionControlError as exc:
            bounds_error = exc.code
    operation_key = (
        _operation_identity_key(proposal, derived) if derived is not None else None
    )
    advisory = proposal.advisory_proposed_capability
    advisory_status = (
        "not_supplied"
        if advisory is None
        else "matched"
        if derived == advisory
        else "conflict"
    )
    active = _mapping(state.get("active_by_source_obligation"), "")
    receipts = _mapping(state.get("terminal_receipts_by_operation_key"), "")
    exhausted = _mapping(state.get("exhausted_operation_keys"), "")
    canonical_receipt_refs = {
        (
            item.get("receipt_id"),
            item.get("receipt_digest"),
        )
        for item in receipts.values()
        if isinstance(item, Mapping)
    }
    prior_receipt_refs_current = all(
        (item.get("receipt_id"), item.get("receipt_digest"))
        in canonical_receipt_refs
        for item in proposal.prior_acquisition_receipt_refs
    )
    active_conflict = bool(obligation_id and active.get(obligation_id))
    prior_receipt = _mapping(receipts.get(operation_key), "") if operation_key else {}
    duplicate_completed = prior_receipt.get("terminal_status") == "completed"
    duplicate_terminal = bool(prior_receipt) and not duplicate_completed
    operation_exhausted = bool(operation_key and exhausted.get(operation_key))
    prerequisites = {
        "run_id_current": proposal.run_id == snapshot.get("run_id"),
        "request_id_current": proposal.request_id == snapshot.get("request_id"),
        "answer_contract_current": contract_current,
        "component_revision_current": component_current,
        "source_obligation_current": obligation_current,
        "source_obligation_active": obligation_active,
        "material_shape_recognized": derived is not None,
        "operation_identity_present": operation_key is not None,
        "hard_operation_bounds_valid": bounds_error is None,
        "duplicate_completed_operation": duplicate_completed,
        "duplicate_terminal_operation": duplicate_terminal,
        "operation_exhausted": operation_exhausted,
        "prior_receipt_refs_current": prior_receipt_refs_current,
        "active_conflicting_operation": active_conflict,
        "provider_availability_consulted": False,
        "mode_or_complexity_consulted": False,
    }
    block_code: str | None = None
    if not prerequisites["run_id_current"] or not prerequisites["request_id_current"]:
        block_code = "proposal_run_or_request_mismatch"
    elif not contract_current:
        block_code = "stale_answer_contract"
    elif not component_current:
        block_code = "stale_component_revision"
    elif not obligation_current or not obligation_active:
        block_code = "mismatched_source_obligation"
    elif derived is None:
        block_code = "capability_prerequisites_not_met"
    elif bounds_error is not None:
        block_code = bounds_error
    elif advisory_status == "conflict":
        block_code = "advisory_capability_conflict"
    elif not prior_receipt_refs_current:
        block_code = "prior_acquisition_receipt_ref_stale"
    elif duplicate_completed:
        block_code = "duplicate_completed_operation"
    elif duplicate_terminal or operation_exhausted:
        block_code = "duplicate_terminal_operation_retry_unlicensed"
    elif active_conflict:
        block_code = "active_conflicting_operation"
    elif derived == AcquisitionCapability.FOCUSED_EXTRACT.value:
        block_code = "focused_extract_requester_not_installed"
    elif derived == AcquisitionCapability.MAP_SITE.value:
        block_code = "map_candidate_reentry_not_installed"
    elif derived == AcquisitionCapability.CRAWL_SITE.value:
        block_code = "crawl_page_custody_not_installed"
    elif derived == PREMIUM_SEQUENTIAL_ACQUISITION:
        block_code = "premium_sequential_acquisition_not_licensed"
    decision_status = "blocked" if block_code else "accepted"
    core = {
        "schema_version": ACQUISITION_CAPABILITY_DECISION_SCHEMA_VERSION,
        "proposal_ref": proposal.ref(),
        "derived_capability": derived,
        "advisory_proposal_match_status": advisory_status,
        "prerequisite_evaluation": prerequisites,
        "decision_status": decision_status,
        "block_code": block_code,
        "material_shape_interpretation": material_interpretation,
        "operation_identity_key": operation_key,
        "authority_posture": "capability_decision_only",
    }
    digest = stable_json_digest(core)
    payload = {
        **core,
        "decision_id": f"acquisition-capability-decision:{proposal.proposal_id}:{digest[:20]}",
        "decision_digest": digest,
    }
    return AcquisitionCapabilityDecisionObservationV1.from_dict(payload)


def build_acquisition_work_order(
    *,
    proposal: AcquisitionNeedProposalV1,
    decision: AcquisitionCapabilityDecisionObservationV1,
    runkernel_authorization_ref: Mapping[str, Any],
) -> AcquisitionWorkOrderV1:
    if decision.decision_status != "accepted" or not decision.derived_capability:
        raise AcquisitionControlError("blocked_decision_cannot_create_work_order")
    bounds = _hard_bounds_for_capability(
        decision.derived_capability, proposal.requested_bounds
    )
    core = {
        "schema_version": ACQUISITION_WORK_ORDER_SCHEMA_VERSION,
        "accepted_capability_observation_ref": decision.ref(),
        "runkernel_authorization_ref": _compact_ref(runkernel_authorization_ref),
        "answer_contract_ref": _json_clone(proposal.answer_contract_ref),
        "source_obligation_ref": _json_clone(proposal.source_obligation_ref),
        "component_ref": _json_clone(proposal.component_ref),
        "authorized_capability": decision.derived_capability,
        **(
            {
                "origin": proposal.origin,
                "destination_binding_ref": _json_clone(
                    proposal.destination_binding_ref
                ),
            }
            if proposal.origin is not None
            else {}
        ),
        "candidate_ref": _json_clone(proposal.candidate_ref),
        "selected_urls": list(proposal.available_urls),
        "root_url": proposal.root_url,
        "bounded_focus": _json_clone(proposal.bounded_focus),
        "include_domains": list(proposal.include_domains),
        "exclude_domains": list(proposal.exclude_domains),
        "include_path_prefix": proposal.include_path_prefix,
        "exclude_path_prefixes": list(proposal.exclude_path_prefixes),
        "hard_operation_bounds": bounds,
        "parent_acquisition_job_refs": list(proposal.parent_acquisition_job_refs),
        "routing_policy_ref": acquisition_routing_policy_ref(),
        "operation_identity_key": decision.operation_identity_key,
        "duplicate_check": "clear",
        "exhaustion_check": "clear",
        "authority_posture": WORK_ORDER_AUTHORITY_POSTURE,
    }
    digest = stable_json_digest(core)
    payload = {
        **core,
        "work_order_id": f"acquisition-work-order:{decision.decision_id}:{digest[:20]}",
        "work_order_digest": digest,
    }
    return AcquisitionWorkOrderV1.from_dict(payload)


def build_terminal_receipt_from_decision(
    *,
    proposal: AcquisitionNeedProposalV1,
    decision: AcquisitionCapabilityDecisionObservationV1,
) -> AcquisitionTerminalReceiptV1 | None:
    if (
        decision.decision_status != "blocked"
        or not decision.operation_identity_key
        or decision.block_code
        not in {
            "focused_extract_requester_not_installed",
            "map_candidate_reentry_not_installed",
            "crawl_page_custody_not_installed",
            "premium_sequential_acquisition_not_licensed",
        }
    ):
        return None
    return AcquisitionTerminalReceiptV1.create(
        operation_identity_key=decision.operation_identity_key,
        capability=decision.derived_capability,
        terminal_status="blocked",
        block_or_failure_code=decision.block_code,
        source_obligation_ref=proposal.source_obligation_ref,
    )


def build_terminal_receipt_from_route(
    *,
    work_order: AcquisitionWorkOrderV1,
    route: AcquisitionRouteObservationV1,
) -> AcquisitionTerminalReceiptV1:
    if route.terminal_status != "blocked":
        raise AcquisitionControlError("selected_route_is_not_terminal")
    return AcquisitionTerminalReceiptV1.create(
        operation_identity_key=work_order.operation_identity_key,
        capability=work_order.authorized_capability,
        terminal_status="blocked",
        block_or_failure_code=route.block_code,
        source_obligation_ref=work_order.source_obligation_ref,
        work_order_ref=work_order.ref(),
        route_observation_ref=route.ref(),
    )


def build_terminal_receipt_from_work_order_invalidation(
    *,
    work_order: AcquisitionWorkOrderV1,
    block_code: str,
) -> AcquisitionTerminalReceiptV1:
    if block_code not in {
        "stale_answer_contract",
        "stale_component_revision",
        "mismatched_source_obligation",
        "routing_policy_is_stale",
    }:
        raise AcquisitionControlError(
            "work_order_invalidation_code_not_licensed"
        )
    return AcquisitionTerminalReceiptV1.create(
        operation_identity_key=work_order.operation_identity_key,
        capability=work_order.authorized_capability,
        terminal_status="blocked",
        block_or_failure_code=block_code,
        source_obligation_ref=work_order.source_obligation_ref,
        work_order_ref=work_order.ref(),
    )


def build_terminal_receipt_from_execution(
    *,
    work_order: AcquisitionWorkOrderV1,
    route: AcquisitionRouteObservationV1,
    execution: AcquisitionExecutionObservationV1,
) -> AcquisitionTerminalReceiptV1:
    return AcquisitionTerminalReceiptV1.create(
        operation_identity_key=work_order.operation_identity_key,
        capability=work_order.authorized_capability,
        terminal_status=execution.terminal_status,
        block_or_failure_code=execution.failure_or_block_code,
        source_obligation_ref=work_order.source_obligation_ref,
        work_order_ref=work_order.ref(),
        route_observation_ref=route.ref(),
        execution_observation_ref=execution.ref(),
    )


def current_receipt_refs(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    receipts = _mapping(state.get("terminal_receipts_by_operation_key"), "")
    return [
        AcquisitionTerminalReceiptV1.from_dict(item).ref()
        for item in receipts.values()
        if isinstance(item, Mapping)
    ]


def normalize_acquisition_url(value: str) -> str:
    parsed = urlsplit(_required_url(value, "acquisition_url_invalid"))
    scheme = parsed.scheme.casefold()
    host = (parsed.hostname or "").casefold().rstrip(".")
    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunsplit((scheme, host, path, parsed.query, ""))


def _canonical_site_root(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    return normalize_acquisition_url(value)


def _canonical_domains(values: Sequence[str]) -> tuple[str, ...]:
    domains: list[str] = []
    for value in values:
        if not isinstance(value, str):
            return ()
        domain = value.strip().casefold().rstrip(".")
        if (
            not domain
            or any(character in domain for character in "/:@?#")
            or urlsplit(f"//{domain}").hostname != domain
        ):
            return ()
        if domain not in domains:
            domains.append(domain)
    return tuple(domains)


def stable_json_digest(value: Any) -> str:
    return sha256(
        json.dumps(
            _json_clone(value), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _derive_capability_from_material(
    proposal: AcquisitionNeedProposalV1,
) -> tuple[str | None, str]:
    shape = proposal.requested_material_shape
    url_count = len(proposal.available_urls)
    focus = _mapping(proposal.bounded_focus, "")
    focus_bound = bool(
        focus.get("focus_text")
        and focus.get("source_obligation_digest")
        == proposal.source_obligation_ref.get("source_obligation_digest")
        and (
            not proposal.component_ref
            or focus.get("component_revision")
            == proposal.component_ref.get("component_revision")
        )
    )
    prior_too_broad = proposal.previous_read_posture in {
        "too_broad",
        "truncated",
    }
    if (
        1 <= url_count <= 20
        and focus_bound
        and (shape in FOCUSED_MATERIAL_SHAPES or prior_too_broad)
    ):
        return AcquisitionCapability.FOCUSED_EXTRACT.value, "exact_bounded_focus"
    selected_candidate_read = bool(
        proposal.candidate_ref.get("candidate_id")
        and proposal.candidate_ref.get("candidate_digest")
        and proposal.candidate_ref.get("url") == proposal.available_urls[0]
    )
    explicit_known_url_read = bool(
        shape == "explicit_known_url" and not proposal.candidate_ref
        and (
            len(proposal.available_urls) == 1
            or (
                proposal.origin == SEARCHOS_NAVIGATION_ORIGIN
                and bool(proposal.destination_binding_ref)
            )
        )
    )
    if (
        shape in READ_MATERIAL_SHAPES
        and (
            url_count == 1
            or (
                proposal.origin == SEARCHOS_NAVIGATION_ORIGIN
                and url_count == 0
            )
        )
        and (selected_candidate_read or explicit_known_url_read)
    ):
        return (
            AcquisitionCapability.READ.value,
            (
                "selected_candidate_single_url_read"
                if selected_candidate_read
                else "explicit_known_url_read"
            ),
        )
    site_root = _canonical_site_root(proposal.root_url)
    if shape == "site_topology" and site_root:
        return AcquisitionCapability.MAP_SITE.value, "unknown_relevant_page_site_root"
    include_domains = _canonical_domains(proposal.include_domains)
    exclude_domains = _canonical_domains(proposal.exclude_domains)
    root_host = urlsplit(site_root).hostname if site_root else None
    if (
        shape == "bounded_multi_page"
        and site_root
        and include_domains
        and (not proposal.exclude_domains or exclude_domains)
        and root_host in include_domains
        and proposal.include_path_prefix
        and proposal.explicit_multi_page_need
    ):
        return AcquisitionCapability.CRAWL_SITE.value, "explicit_bounded_multi_page"
    if shape == "premium_sequential_acquisition":
        return PREMIUM_SEQUENTIAL_ACQUISITION, "premium_sequential_acquisition"
    return None, "unclassified_or_incomplete_material_need"


def _operation_identity_key(
    proposal: AcquisitionNeedProposalV1, capability: str
) -> str:
    base = {
        "contract_digest": proposal.answer_contract_ref.get("contract_digest"),
        "source_obligation_digest": proposal.source_obligation_ref.get(
            "source_obligation_digest"
        ),
        "component_revision": proposal.component_ref.get("component_revision"),
        "component_digest": proposal.component_ref.get("component_digest"),
        "capability": capability,
    }
    if capability == AcquisitionCapability.READ.value:
        if proposal.origin == SEARCHOS_NAVIGATION_ORIGIN:
            base.update(
                {
                    "origin": SEARCHOS_NAVIGATION_ORIGIN,
                    "destination_binding_digest": (
                        proposal.destination_binding_ref.get(
                            "destination_binding_digest"
                        )
                    ),
                    "physical_identity_digest": (
                        proposal.destination_binding_ref.get(
                            "physical_identity_digest"
                        )
                    ),
                }
            )
            digest = stable_json_digest(base)
            return f"{capability.casefold().replace('_', '-')}:{digest}"
        normalized_url = normalize_acquisition_url(
            proposal.available_urls[0]
        )
        base.update({"url": normalized_url})
        if proposal.candidate_ref:
            base["candidate_digest"] = proposal.candidate_ref.get(
                "candidate_digest"
            )
        else:
            base["explicit_url_digest"] = stable_json_digest(
                {"normalized_url": normalized_url}
            )
    elif capability == AcquisitionCapability.FOCUSED_EXTRACT.value:
        base.update(
            {
                "urls": sorted(
                    {
                        normalize_acquisition_url(url)
                        for url in proposal.available_urls
                    }
                ),
                "focus_digest": proposal.bounded_focus.get("focus_digest"),
            }
        )
    elif capability == AcquisitionCapability.MAP_SITE.value:
        base.update({"root_url": _canonical_site_root(proposal.root_url)})
    elif capability == AcquisitionCapability.CRAWL_SITE.value:
        base.update(
            {
                "root_url": _canonical_site_root(proposal.root_url),
                "path_scope_digest": stable_json_digest(
                    {
                        "include_domains": sorted(
                            set(_canonical_domains(proposal.include_domains))
                        ),
                        "exclude_domains": sorted(
                            set(_canonical_domains(proposal.exclude_domains))
                        ),
                        "include_path_prefix": proposal.include_path_prefix,
                        "exclude_path_prefixes": sorted(
                            set(proposal.exclude_path_prefixes)
                        ),
                    }
                ),
            }
        )
    digest = stable_json_digest(base)
    return f"{capability.casefold().replace('_', '-')}:{digest}"


def _hard_bounds_for_capability(
    capability: str, requested: Mapping[str, Any]
) -> dict[str, int]:
    supplied = _bounded_int_mapping(requested)
    defaults: dict[str, dict[str, int]] = {
        AcquisitionCapability.READ.value: {"max_retained_characters": 20_000},
        AcquisitionCapability.FOCUSED_EXTRACT.value: {
            "max_selected_urls": 20,
            "max_focus_characters": 2_000,
            "max_retained_characters": 20_000,
        },
        AcquisitionCapability.MAP_SITE.value: {"max_results": 100},
        AcquisitionCapability.CRAWL_SITE.value: {
            "max_depth": 2,
            "max_pages": 10,
            "max_retained_characters": 20_000,
            "max_aggregate_retained_characters": 100_000,
        },
    }
    maximums = defaults.get(capability, {})
    unknown = set(supplied).difference(maximums)
    if unknown:
        raise AcquisitionControlError("operation_bound_not_allowed")
    result = dict(maximums)
    for key, value in supplied.items():
        if value > maximums[key]:
            raise AcquisitionControlError(
                "operation_bound_exceeds_code_owned_maximum"
            )
        result[key] = value
    return result


def _contract_ref(value: Any) -> dict[str, Any]:
    ref = _mapping(value, "answer_contract_ref_missing")
    _reject_unknown_fields(
        ref,
        {"source", "contract_version", "contract_digest"},
        "answer_contract_ref",
    )
    version = _required_token(
        ref.get("contract_version"),
        "answer_contract_version_missing",
    )
    digest = _required_token(
        ref.get("contract_digest"),
        "answer_contract_digest_missing",
        limit=128,
    )
    return {
        "source": _optional_token(ref.get("source"), limit=100)
        or "current_answer_contract",
        "contract_version": version,
        "contract_digest": digest,
    }


def _component_ref(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    ref = _mapping(value, "component_ref_invalid")
    _reject_unknown_fields(
        ref,
        {"component_id", "component_revision", "component_digest"},
        "component_ref",
    )
    return {
        "component_id": _required_token(
            ref.get("component_id"), "component_id_missing", limit=200
        ),
        "component_revision": _required_token(
            ref.get("component_revision"),
            "component_revision_missing",
            limit=100,
        ),
        "component_digest": _required_token(
            ref.get("component_digest"), "component_digest_missing", limit=128
        ),
    }


def _source_obligation_ref(value: Any) -> dict[str, Any]:
    ref = _mapping(value, "source_obligation_ref_missing")
    if "source_authority_granted" in ref or "source_obligation_satisfied" in ref:
        raise AcquisitionControlError("source_obligation_authority_spoof")
    _reject_unknown_fields(
        ref,
        {
            "source_obligation_id",
            "source_obligation_digest",
            "binding_kind",
            "answer_contract_digest",
            "component_ids",
            "active",
        },
        "source_obligation_ref",
    )
    if not isinstance(ref.get("active"), bool):
        raise AcquisitionControlError("source_obligation_active_boolean_required")
    result = {
        "source_obligation_id": _required_token(
            ref.get("source_obligation_id"),
            "source_obligation_id_missing",
            limit=200,
        ),
        "source_obligation_digest": _required_token(
            ref.get("source_obligation_digest"),
            "source_obligation_digest_missing",
            limit=128,
        ),
        "binding_kind": _required_token(
            ref.get("binding_kind"), "source_obligation_binding_kind_missing"
        ),
        "answer_contract_digest": _required_token(
            ref.get("answer_contract_digest"),
            "source_obligation_contract_digest_missing",
            limit=128,
        ),
        "component_ids": _tokens(ref.get("component_ids"), limit=200),
        "active": ref.get("active") is True,
    }
    return result


def _candidate_ref(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    ref = _mapping(value, "candidate_ref_invalid")
    allowed = {
        "packet_id",
        "packet_digest",
        "candidate_id",
        "candidate_digest",
        "record_digest",
        "url",
    }
    if set(ref).difference(allowed):
        raise AcquisitionControlError("candidate_ref_unknown_fields")
    result = {
        key: _required_token(ref.get(key), f"candidate_ref_{key}_missing", limit=400)
        for key in allowed.difference({"url"})
        if ref.get(key) is not None
    }
    if ref.get("url") is not None:
        result["url"] = _required_url(ref.get("url"), "candidate_ref_url_invalid")
    return result


def _acquisition_origin_fields(
    *,
    origin: Any,
    destination_binding_ref: Any,
    candidate_ref: Mapping[str, Any],
    available_urls: Sequence[str],
    root_url: Any,
    requested_material_shape: Any,
) -> dict[str, Any]:
    origin_token = _optional_token(origin, limit=100)
    has_binding = bool(destination_binding_ref)
    if origin_token is None and not has_binding:
        return {}
    if origin_token != SEARCHOS_NAVIGATION_ORIGIN or not has_binding:
        raise AcquisitionControlError("acquisition_origin_branch_incomplete")
    if candidate_ref or available_urls or root_url:
        raise AcquisitionControlError("acquisition_origin_branches_mixed")
    if str(requested_material_shape or "").strip().casefold() != "explicit_known_url":
        raise AcquisitionControlError("navigation_material_shape_invalid")
    return {
        "origin": SEARCHOS_NAVIGATION_ORIGIN,
        "destination_binding_ref": validate_navigation_destination_binding_ref(
            destination_binding_ref
        ),
    }


def _bounded_focus(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    focus = _mapping(value, "bounded_focus_invalid")
    allowed = {
        "focus_text",
        "focus_digest",
        "source_obligation_digest",
        "component_revision",
    }
    if set(focus).difference(allowed):
        raise AcquisitionControlError("bounded_focus_unknown_fields")
    text = _required_token(
        focus.get("focus_text"), "bounded_focus_text_missing", limit=2_000
    )
    digest = stable_json_digest({"focus_text": text})
    if focus.get("focus_digest") not in (None, digest):
        raise AcquisitionControlError("bounded_focus_digest_mismatch")
    return {
        "focus_text": text,
        "focus_digest": digest,
        "source_obligation_digest": _required_token(
            focus.get("source_obligation_digest"),
            "bounded_focus_source_obligation_digest_missing",
            limit=128,
        ),
        "component_revision": _required_token(
            focus.get("component_revision"),
            "bounded_focus_component_revision_missing",
            limit=100,
        ),
    }


def _routing_policy_ref(value: Any) -> dict[str, Any]:
    ref = _mapping(value, "routing_policy_ref_missing")
    _reject_unknown_fields(
        ref,
        {
            "schema_version",
            "owner",
            "revision",
            "selection_algorithm_revision",
            "policy_digest",
        },
        "routing_policy_ref",
    )
    return {
        "schema_version": _required_token(
            ref.get("schema_version"), "routing_policy_schema_missing"
        ),
        "owner": _required_token(ref.get("owner"), "routing_policy_owner_missing"),
        "revision": _required_token(
            ref.get("revision"), "routing_policy_revision_missing", limit=180
        ),
        "selection_algorithm_revision": _required_token(
            ref.get("selection_algorithm_revision"),
            "routing_policy_algorithm_revision_missing",
            limit=180,
        ),
        "policy_digest": _required_token(
            ref.get("policy_digest"), "routing_policy_digest_missing", limit=128
        ),
    }


def _execution_result_ref(value: Any) -> dict[str, Any]:
    ref = _mapping(value, "execution_result_ref_missing")
    _reject_unknown_fields(
        ref,
        _EXECUTION_RESULT_REF_FIELDS,
        "execution_result_ref",
    )
    return {
        "execution_result_id": _required_token(
            ref.get("execution_result_id"),
            "execution_result_id_missing",
            limit=500,
        ),
        "execution_result_digest": _required_token(
            _required_sha256_digest(
                ref.get("execution_result_digest"),
                "execution_result_digest_invalid",
            ),
            "execution_result_digest_missing",
            limit=64,
        ),
    }


def _artifact_observation_ref(value: Any) -> dict[str, Any]:
    ref = _mapping(value, "artifact_ref_missing")
    _reject_unknown_fields(ref, _ARTIFACT_REF_FIELDS, "artifact_ref")
    if (
        ref.get("retained_text_included") is not False
        or ref.get("raw_provider_payload_included") is not False
    ):
        raise AcquisitionControlError("artifact_ref_private_material_invalid")
    kind = _required_token(
        ref.get("kind"), "artifact_kind_missing", limit=100
    )
    if kind not in {
        "discovery_candidate_material",
        "selected_url_read_material",
        "focused_selected_url_extraction",
        "site_url_topology",
        "bounded_page_collection",
        "typed_provider_failure",
        "typed_policy_or_availability_block",
    }:
        raise AcquisitionControlError("artifact_kind_invalid")
    status = _required_token(
        ref.get("status"), "artifact_status_missing", limit=100
    )
    if status not in {
        "candidate_returned",
        "readable",
        "mapped",
        "crawled",
        "failed",
        "blocked",
    }:
        raise AcquisitionControlError("artifact_status_invalid")
    result: dict[str, Any] = {
        "artifact_id": _required_token(
            ref.get("artifact_id"), "artifact_id_missing", limit=700
        ),
        "artifact_digest": _required_sha256_digest(
            ref.get("artifact_digest"),
            "artifact_digest_invalid",
        ),
        "kind": kind,
        "acquisition_job_id": _required_token(
            ref.get("acquisition_job_id"),
            "artifact_acquisition_job_id_missing",
            limit=500,
        ),
        "status": status,
        "retained_character_count": _nonnegative_int(
            ref.get("retained_character_count")
        ),
        "url_count": _nonnegative_int(ref.get("url_count")),
        "page_count": _nonnegative_int(ref.get("page_count")),
        "authority_posture": _required_token(
            ref.get("authority_posture"),
            "artifact_authority_posture_missing",
            limit=100,
        ),
        "retained_text_included": False,
        "raw_provider_payload_included": False,
    }
    if result["authority_posture"] != "acquisition_material_only":
        raise AcquisitionControlError("artifact_authority_posture_invalid")
    for key, limit in {
        "provider": 100,
        "operation": 180,
        "provider_variant": 180,
        "output_type": 180,
        "requested_url": 2_000,
        "final_url": 2_000,
        "canonical_url": 2_000,
        "root_url": 2_000,
        "failure_code": 180,
    }.items():
        item = _optional_token(ref.get(key), limit=limit)
        if item is not None:
            result[key] = item
    if ref.get("retained_digest") not in (None, ""):
        result["retained_digest"] = _required_sha256_digest(
            ref.get("retained_digest"), "artifact_retained_digest_invalid"
        )
    if status == "failed" and not result.get("failure_code"):
        raise AcquisitionControlError("failed_artifact_code_missing")
    if status != "failed" and result.get("failure_code"):
        raise AcquisitionControlError("artifact_failure_status_mismatch")
    digest_core = {
        key: value
        for key, value in result.items()
        if key
        not in {
            "artifact_id",
            "artifact_digest",
            "retained_text_included",
            "raw_provider_payload_included",
        }
    }
    expected_digest = stable_json_digest(digest_core)
    expected_id = (
        f"acquisition-artifact:{result['acquisition_job_id']}:"
        f"{expected_digest[:20]}"
    )
    if (
        result["artifact_digest"] != expected_digest
        or result["artifact_id"] != expected_id
    ):
        raise AcquisitionControlError("artifact_ref_identity_invalid")
    return result


def _compact_ref(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    ref = _mapping(value, "compact_ref_invalid")
    result: dict[str, Any] = {}
    for key, item in ref.items():
        if item in (None, "", [], {}, ()):
            continue
        if isinstance(item, (Mapping, list, tuple, set, frozenset, bytes, bytearray)):
            raise AcquisitionControlError("compact_ref_scalar_values_required")
        if not isinstance(item, (str, int, bool)):
            raise AcquisitionControlError("compact_ref_scalar_values_required")
        safe_key = _required_token(
            key, "compact_ref_key_missing", limit=100
        )
        result[safe_key] = (
            _required_token(item, "compact_ref_value_missing", limit=500)
            if isinstance(item, str)
            else item
        )
    return result


def _bounded_int_mapping(value: Any) -> dict[str, int]:
    if not value:
        return {}
    raw = _mapping(value, "bounded_int_mapping_invalid")
    result: dict[str, int] = {}
    for key, item in raw.items():
        parsed = _nonnegative_int(item)
        if parsed <= 0:
            raise AcquisitionControlError("operation_bound_must_be_positive")
        result[_required_token(key, "operation_bound_name_missing")] = parsed
    return result


def _mapping(value: Any, code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        if not value and not code:
            return {}
        raise AcquisitionControlError(code or "mapping_required")
    return {str(key): _json_clone(item) for key, item in value.items()}


def _reject_unknown_fields(
    value: Mapping[str, Any], allowed: set[str] | frozenset[str], label: str
) -> None:
    unknown = set(value).difference(allowed)
    if unknown:
        raise AcquisitionControlError(
            f"{label}_unknown_fields",
            f"{label} contains unknown fields: {sorted(unknown)}",
        )


def _canonical_key(value: Any) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def _key_has_forbidden_concept(key: str) -> bool:
    return any(
        concept in key
        for concept in (
            "provider",
            "transport",
            "adapter",
            "authority",
            "evidence",
            "citation",
            "sufficiency",
            "finalanswer",
            "answertext",
            "rawprompt",
            "rawpayload",
            "instruction",
            "secret",
            "apikey",
        )
    )


def _forbidden_concept_keys(value: Any) -> set[str]:
    return {
        key
        for key in _collect_normalized_keys(value)
        if _key_has_forbidden_concept(key)
    }


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return []
    return list(value)


def _tokens(value: Any, *, limit: int) -> list[str]:
    result: list[str] = []
    for item in _sequence(value):
        token = _optional_token(item, limit=limit)
        if token and token not in result:
            result.append(token)
    return result


def _paths(value: Any) -> list[str]:
    result: list[str] = []
    for item in _sequence(value):
        path = _optional_path(item)
        if path and path not in result:
            result.append(path)
    return result


def _optional_path(value: Any) -> str | None:
    text = _optional_token(value, limit=1_000)
    if not text:
        return None
    if not text.startswith("/"):
        raise AcquisitionControlError("path_scope_invalid")
    return text


def _required_url(value: Any, code: str) -> str:
    text = _required_token(value, code, limit=2_000)
    parsed = urlsplit(text)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        raise AcquisitionControlError(code)
    return text


def _required_token(value: Any, code: str, *, limit: int = 300) -> str:
    token = _optional_token(value, limit=limit)
    if not token:
        raise AcquisitionControlError(code)
    return token


def _required_sha256_digest(value: Any, code: str) -> str:
    digest = _required_token(value, code, limit=64)
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise AcquisitionControlError(code)
    return digest


def _optional_token(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AcquisitionControlError("string_token_required")
    text = " ".join(value.strip().split())
    return text[:limit] if text else None


def _optional_capability(value: Any) -> str | None:
    token = _optional_token(value, limit=100)
    return token.upper() if token else None


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AcquisitionControlError("nonnegative_integer_required")
    parsed = value
    if parsed < 0:
        raise AcquisitionControlError("nonnegative_integer_required")
    return parsed


def _strict_bool(value: Any, code: str) -> bool:
    if not isinstance(value, bool):
        raise AcquisitionControlError(code)
    return value


def _validate_material_shape(value: str) -> None:
    if value not in KNOWN_MATERIAL_SHAPES:
        raise AcquisitionControlError("requested_material_shape_unknown")


def _collect_normalized_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_canonical_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_normalized_keys(item))
        return keys
    if isinstance(value, (list, tuple, set, frozenset)):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_normalized_keys(item))
        return keys
    return set()


def _json_clone(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_clone(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_clone(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


__all__ = [
    "ACQUISITION_CONTROL_STATE_SCHEMA_VERSION",
    "AcquisitionCapabilityDecisionObservationV1",
    "AcquisitionControlError",
    "AcquisitionCustodyAuthorizationV1",
    "AcquisitionExecutionObservationV1",
    "AcquisitionNeedProposalV1",
    "AcquisitionRouteObservationV1",
    "AcquisitionTerminalReceiptV1",
    "AcquisitionWorkOrderV1",
    "SEARCHOS_NAVIGATION_ORIGIN",
    "build_acquisition_authority_snapshot",
    "build_pre_acquisition_source_obligation_ref",
    "build_acquisition_work_order",
    "build_terminal_receipt_from_decision",
    "build_terminal_receipt_from_execution",
    "build_terminal_receipt_from_route",
    "current_receipt_refs",
    "derive_acquisition_capability_decision",
    "ensure_acquisition_control_state",
    "initial_acquisition_control_state",
    "normalize_acquisition_url",
    "stable_json_digest",
    "validate_selected_candidate_material_need_proposal",
]
