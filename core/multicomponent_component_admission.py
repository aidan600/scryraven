"""Pure staging for RunKernel-owned multi-component component admission."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from core.component_coverage_reduction_runtime import (
    ComponentCoverageReductionError,
    build_component_coverage_reduction_projection,
    build_component_coverage_reduction_state,
)
from core.multicomponent_role_runtime import (
    COMPONENT_ANALYST_SUPPORTING_CASE_POSTURES,
    ROLE_COMPONENT_ANALYST,
    ROLE_COMPONENT_ANALYST_RESUME,
    role_artifact_ref,
    safe_packet_digest,
    validate_multicomponent_role_artifact,
)
from core.quantitative_finalization_authority import (
    specialist_quantitative_authority_ref_from_handoff,
)
from core.semantic_observation_admission_runtime import (
    SemanticObservationAdmissionError,
    build_semantic_observation_admission_projection,
    build_semantic_observation_admission_state,
)

MULTICOMPONENT_COMPONENT_ADMISSION_STAGE = "multicomponent_component_admission"
MULTICOMPONENT_COMPONENT_ADMISSION_OWNER = (
    "RunKernel.MulticomponentComponentAdmission"
)
COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION = (
    "component_analyst_input_binding_mismatch_v1"
)
COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH = (
    "component Analyst exact input binding mismatch"
)
_MULTICOMPONENT_SCHEDULER_PROJECTION = "multicomponent_graph_scheduler"
_MISMATCH_CLASS_VALUES = frozenset(
    {
        "CONTRACT_AUTHORITY_CHANGED",
        "PACKET_RECONSTRUCTION_NON_IDEMPOTENT",
        "SUPPLIED_PACKET_CHANGED",
        "ARTIFACT_DIGEST_CHANGED",
        "OTHER",
    }
)
_FIRST_DIVERGENT_SECTION_VALUES = frozenset(
    {
        "run_binding",
        "component_ref",
        "component_evidence",
        "quantitative_source_catalog",
        "quantitative_specialist_proposal_contract",
        "other",
        "unknown",
    }
)
_ACCEPTED_AUTHORITY_SOURCE_VALUES = frozenset(
    {"current", "initial_fallback", "unknown"}
)
_KNOWN_PACKET_SECTIONS = (
    "run_binding",
    "component_ref",
    "component_evidence",
    "quantitative_source_catalog",
    "quantitative_specialist_proposal_contract",
)


class MulticomponentComponentAdmissionError(ValueError):
    """Raised before canonical mutation when component admission is invalid."""

    def __init__(
        self,
        message: str,
        *,
        component_analyst_input_binding_mismatch_v1: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        projected = project_component_analyst_input_binding_mismatch_v1(
            component_analyst_input_binding_mismatch_v1
        )
        self.component_analyst_input_binding_mismatch_v1 = projected or None


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _clean_text(value: Any, *, limit: int = 1000) -> str | None:
    if value is None or isinstance(value, Mapping | list | tuple | set | frozenset):
        return None
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else None


def _closed_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _closed_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def _packet_section_digest(packet: Mapping[str, Any], section: str) -> str:
    value = packet.get(section) if isinstance(packet, Mapping) else None
    if isinstance(value, Mapping):
        return safe_packet_digest(value)
    return safe_packet_digest(
        {
            "section_presence": "non_mapping",
            "present": value is not None,
            "value_type": type(value).__name__ if value is not None else "missing",
        }
    )


def project_component_analyst_input_binding_mismatch_v1(
    value: Any,
) -> dict[str, Any]:
    """Return only the closed, privacy-safe mismatch projection."""

    raw = _safe_mapping(value)
    schema_version = _clean_text(raw.get("schema_version"), limit=80)
    mismatch_class = _clean_text(raw.get("mismatch_class"), limit=80)
    first_divergent_section = _clean_text(
        raw.get("first_divergent_section"), limit=80
    )
    accepted_authority_source = _clean_text(
        raw.get("accepted_authority_source"), limit=40
    )
    if (
        schema_version != COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION
        or mismatch_class not in _MISMATCH_CLASS_VALUES
        or first_divergent_section not in _FIRST_DIVERGENT_SECTION_VALUES
        or accepted_authority_source not in _ACCEPTED_AUTHORITY_SOURCE_VALUES
    ):
        return {}

    def digest_field(key: str) -> str | None:
        return _clean_text(raw.get(key), limit=128)

    def token_field(key: str, *, limit: int = 200) -> str | None:
        return _clean_text(raw.get(key), limit=limit)

    projected: dict[str, Any] = {
        "schema_version": schema_version,
        "mismatch_class": mismatch_class,
        "first_divergent_section": first_divergent_section,
        "artifact_input_packet_digest": digest_field(
            "artifact_input_packet_digest"
        ),
        "supplied_packet_digest": digest_field("supplied_packet_digest"),
        "reconstructed_packet_digest": digest_field("reconstructed_packet_digest"),
        "supplied_digest_equals_artifact": _closed_bool(
            raw.get("supplied_digest_equals_artifact")
        ),
        "supplied_digest_equals_reconstructed": _closed_bool(
            raw.get("supplied_digest_equals_reconstructed")
        ),
        "artifact_digest_equals_reconstructed": _closed_bool(
            raw.get("artifact_digest_equals_reconstructed")
        ),
        "initial_contract_present": _closed_bool(raw.get("initial_contract_present")),
        "initial_contract_version": token_field("initial_contract_version"),
        "initial_contract_digest": digest_field("initial_contract_digest"),
        "current_contract_present": _closed_bool(raw.get("current_contract_present")),
        "current_contract_version": token_field("current_contract_version"),
        "current_contract_digest": digest_field("current_contract_digest"),
        "accepted_authority_source": accepted_authority_source,
        "accepted_component_id": token_field("accepted_component_id"),
        "accepted_component_revision": token_field("accepted_component_revision"),
        "accepted_component_digest": digest_field("accepted_component_digest"),
        "packet_contract_version": token_field("packet_contract_version"),
        "packet_contract_digest": digest_field("packet_contract_digest"),
        "packet_component_revision": token_field("packet_component_revision"),
        "packet_component_digest": digest_field("packet_component_digest"),
        "run_binding_matches_accepted_contract": _closed_bool(
            raw.get("run_binding_matches_accepted_contract")
        ),
        "component_ref_matches_accepted_component": _closed_bool(
            raw.get("component_ref_matches_accepted_component")
        ),
        "component_count": _closed_count(raw.get("component_count")),
        "independent_dispatch_digest_present": _closed_bool(
            raw.get("independent_dispatch_digest_present")
        ),
        "independent_dispatch_input_digest": digest_field(
            "independent_dispatch_input_digest"
        ),
        "supplied_digest_equals_dispatch": _closed_bool(
            raw.get("supplied_digest_equals_dispatch")
        ),
        "artifact_digest_equals_dispatch": _closed_bool(
            raw.get("artifact_digest_equals_dispatch")
        ),
    }
    for section in _KNOWN_PACKET_SECTIONS:
        projected[f"{section}_supplied_digest"] = digest_field(
            f"{section}_supplied_digest"
        )
        projected[f"{section}_reconstructed_digest"] = digest_field(
            f"{section}_reconstructed_digest"
        )
        projected[f"{section}_equal"] = _closed_bool(raw.get(f"{section}_equal"))
    return projected


def component_analyst_input_binding_mismatch_from_exception(
    exc: BaseException,
) -> dict[str, Any]:
    """Extract the owner-authored mismatch projection from one exception chain."""

    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        projected = project_component_analyst_input_binding_mismatch_v1(
            getattr(current, "component_analyst_input_binding_mismatch_v1", None)
        )
        if projected:
            return projected
        current = current.__cause__ or current.__context__
    return {}


def contract_authority_facts_from_run_kernel(run_kernel: Any) -> dict[str, Any]:
    """Project existing current/initial contract presence without new retention."""

    state = getattr(run_kernel, "state", None)
    current_raw = getattr(state, "current_answer_contract", None)
    initial_raw = getattr(state, "initial_answer_contract", None)
    current_present = isinstance(current_raw, Mapping) and bool(current_raw)
    initial_present = isinstance(initial_raw, Mapping) and bool(initial_raw)
    current = _safe_mapping(current_raw) if current_present else {}
    initial = _safe_mapping(initial_raw) if initial_present else {}
    if current_present:
        source = "current"
    elif initial_present:
        source = "initial_fallback"
    else:
        source = "unknown"
    return {
        "initial_contract_present": initial_present,
        "initial_contract_version": _clean_text(
            initial.get("accepted_contract_version"), limit=200
        ),
        "initial_contract_digest": _clean_text(
            initial.get("accepted_contract_digest"), limit=128
        ),
        "current_contract_present": current_present,
        "current_contract_version": _clean_text(
            current.get("accepted_contract_version"), limit=200
        ),
        "current_contract_digest": _clean_text(
            current.get("accepted_contract_digest"), limit=128
        ),
        "accepted_authority_source": source,
    }


def independent_component_analyst_dispatch_input_digest(
    run_kernel: Any,
    *,
    evaluation_key: str,
) -> str | None:
    """Return the unique existing scheduler/lease digest for this evaluation."""

    state = getattr(run_kernel, "state", None)
    projections = getattr(state, "projections", None)
    if not isinstance(projections, Mapping):
        return None
    scheduler = _safe_mapping(projections.get(_MULTICOMPONENT_SCHEDULER_PROJECTION))
    found: set[str] = set()
    for raw_lease in scheduler.get("lease_history") or ():
        lease = _safe_mapping(raw_lease)
        work = _safe_mapping(lease.get("work"))
        if work.get("role") != ROLE_COMPONENT_ANALYST:
            continue
        if str(work.get("logical_evaluation_key") or "") != evaluation_key:
            continue
        digest = _clean_text(work.get("input_packet_digest"), limit=128)
        if digest:
            found.add(digest)
    if len(found) != 1:
        return None
    return next(iter(found))


def build_component_analyst_input_binding_mismatch_v1(
    *,
    analyst: Mapping[str, Any],
    supplied_input: Mapping[str, Any],
    reconstructed_input: Mapping[str, Any],
    accepted_contract: Mapping[str, Any],
    accepted_component: Mapping[str, Any],
    independent_dispatch_input_digest: str | None = None,
    contract_authority_facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the closed structural mismatch projection. Digest-only."""

    supplied = _safe_mapping(supplied_input)
    reconstructed = _safe_mapping(reconstructed_input)
    accepted = _safe_mapping(accepted_contract)
    component = _safe_mapping(accepted_component)
    facts = _safe_mapping(contract_authority_facts)
    artifact_digest = _clean_text(analyst.get("input_packet_digest"), limit=128)
    supplied_digest = safe_packet_digest(supplied)
    reconstructed_digest = safe_packet_digest(reconstructed)
    dispatch_digest = _clean_text(independent_dispatch_input_digest, limit=128)
    dispatch_present = dispatch_digest is not None
    packet_binding = _safe_mapping(supplied.get("run_binding"))
    packet_ref = _safe_mapping(supplied.get("component_ref"))
    packet_contract_version = _clean_text(
        packet_binding.get("accepted_contract_version"), limit=200
    )
    packet_contract_digest = _clean_text(
        packet_binding.get("accepted_contract_digest"), limit=128
    )
    accepted_contract_version = _clean_text(
        accepted.get("accepted_contract_version"), limit=200
    )
    accepted_contract_digest = _clean_text(
        accepted.get("accepted_contract_digest"), limit=128
    )
    packet_component_id = _clean_text(packet_ref.get("component_id"), limit=200)
    packet_component_revision = _clean_text(
        packet_ref.get("component_revision"), limit=200
    )
    packet_component_digest = _clean_text(packet_ref.get("component_digest"), limit=128)
    accepted_component_id = _clean_text(component.get("component_id"), limit=200)
    accepted_component_revision = _clean_text(
        component.get("component_revision"), limit=200
    )
    accepted_component_digest = _clean_text(
        component.get("component_digest"), limit=128
    )
    contract_authority_changed = (
        packet_contract_version is not None
        and packet_contract_digest is not None
        and accepted_contract_version is not None
        and accepted_contract_digest is not None
        and (
            packet_contract_version != accepted_contract_version
            or packet_contract_digest != accepted_contract_digest
        )
    )
    run_binding_matches_accepted_contract = (
        packet_contract_version is not None
        and packet_contract_digest is not None
        and packet_contract_version == accepted_contract_version
        and packet_contract_digest == accepted_contract_digest
    )
    component_ref_matches_accepted_component = (
        packet_component_id is not None
        and packet_component_id == accepted_component_id
        and packet_component_revision == accepted_component_revision
        and packet_component_digest == accepted_component_digest
    )
    supplied_equals_artifact = (
        artifact_digest is not None and supplied_digest == artifact_digest
    )
    supplied_equals_reconstructed = supplied_digest == reconstructed_digest
    artifact_equals_reconstructed = (
        artifact_digest is not None and artifact_digest == reconstructed_digest
    )
    supplied_equals_dispatch = dispatch_present and supplied_digest == dispatch_digest
    artifact_equals_dispatch = (
        dispatch_present and artifact_digest == dispatch_digest
    )
    section_fields: dict[str, Any] = {}
    first_divergent_section = None
    for section in _KNOWN_PACKET_SECTIONS:
        supplied_section_digest = _packet_section_digest(supplied, section)
        reconstructed_section_digest = _packet_section_digest(reconstructed, section)
        equal = supplied_section_digest == reconstructed_section_digest
        section_fields[f"{section}_supplied_digest"] = supplied_section_digest
        section_fields[f"{section}_reconstructed_digest"] = reconstructed_section_digest
        section_fields[f"{section}_equal"] = equal
        if first_divergent_section is None and not equal:
            first_divergent_section = section
    if first_divergent_section is None:
        first_divergent_section = (
            "other" if not supplied_equals_reconstructed else "unknown"
        )
    authority_source = facts.get("accepted_authority_source")
    if authority_source not in _ACCEPTED_AUTHORITY_SOURCE_VALUES:
        authority_source = "unknown"
    if contract_authority_changed:
        mismatch_class = "CONTRACT_AUTHORITY_CHANGED"
    elif (
        supplied_equals_artifact
        and not supplied_equals_reconstructed
        and (not dispatch_present or supplied_equals_dispatch)
    ):
        mismatch_class = "PACKET_RECONSTRUCTION_NON_IDEMPOTENT"
    elif dispatch_present and not supplied_equals_dispatch:
        mismatch_class = "SUPPLIED_PACKET_CHANGED"
    elif dispatch_present and not artifact_equals_dispatch:
        mismatch_class = "ARTIFACT_DIGEST_CHANGED"
    else:
        mismatch_class = "OTHER"
    component_refs = [
        item
        for item in accepted.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
    ]
    initial_present = facts.get("initial_contract_present")
    current_present = facts.get("current_contract_present")
    raw = {
        "schema_version": COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION,
        "mismatch_class": mismatch_class,
        "first_divergent_section": first_divergent_section,
        "artifact_input_packet_digest": artifact_digest,
        "supplied_packet_digest": supplied_digest,
        "reconstructed_packet_digest": reconstructed_digest,
        "supplied_digest_equals_artifact": supplied_equals_artifact,
        "supplied_digest_equals_reconstructed": supplied_equals_reconstructed,
        "artifact_digest_equals_reconstructed": artifact_equals_reconstructed,
        "initial_contract_present": initial_present is True,
        "initial_contract_version": _clean_text(
            facts.get("initial_contract_version"), limit=200
        ),
        "initial_contract_digest": _clean_text(
            facts.get("initial_contract_digest"), limit=128
        ),
        "current_contract_present": current_present is True,
        "current_contract_version": _clean_text(
            facts.get("current_contract_version"), limit=200
        ),
        "current_contract_digest": _clean_text(
            facts.get("current_contract_digest"), limit=128
        ),
        "accepted_authority_source": authority_source,
        "accepted_component_id": accepted_component_id,
        "accepted_component_revision": accepted_component_revision,
        "accepted_component_digest": accepted_component_digest,
        "packet_contract_version": packet_contract_version,
        "packet_contract_digest": packet_contract_digest,
        "packet_component_revision": packet_component_revision,
        "packet_component_digest": packet_component_digest,
        "run_binding_matches_accepted_contract": run_binding_matches_accepted_contract,
        "component_ref_matches_accepted_component": (
            component_ref_matches_accepted_component
        ),
        "component_count": len(component_refs),
        "independent_dispatch_digest_present": dispatch_present,
        "independent_dispatch_input_digest": dispatch_digest,
        "supplied_digest_equals_dispatch": (
            supplied_equals_dispatch if dispatch_present else None
        ),
        "artifact_digest_equals_dispatch": (
            artifact_equals_dispatch if dispatch_present else None
        ),
        **section_fields,
    }
    return project_component_analyst_input_binding_mismatch_v1(raw)


def _accepted_component(
    accepted_contract: Mapping[str, Any],
    component_id: str,
) -> dict[str, Any]:
    for raw in accepted_contract.get("accepted_answer_component_refs") or ():
        component = _safe_mapping(raw)
        if component.get("component_id") == component_id:
            return component
    raise MulticomponentComponentAdmissionError(
        f"component admission references unknown component {component_id!r}"
    )


def component_analyst_input_packet(
    *,
    run_id: str,
    request_id: str,
    accepted_contract: Mapping[str, Any],
    component_ref: Mapping[str, Any],
    evidence_input: Mapping[str, Any],
) -> dict[str, Any]:
    from core.quantitative_specialist_product_activation import (
        build_component_quantitative_source_catalog,
        build_quantitative_specialist_proposal_contract,
    )

    packet = {
        "supported_query_class": (
            "ordinary-bounded-multicomponent-factual-synthesis-v1"
        ),
        "run_binding": {
            "run_id": run_id,
            "request_id": request_id,
            "accepted_contract_version": accepted_contract.get(
                "accepted_contract_version"
            ),
            "accepted_contract_digest": accepted_contract.get(
                "accepted_contract_digest"
            ),
        },
        "component_ref": {
            "component_id": component_ref.get("component_id"),
            "component_revision": component_ref.get("component_revision"),
            "component_digest": component_ref.get("component_digest"),
            "user_facing_label": component_ref.get("user_facing_label"),
            "user_facing_question": component_ref.get("user_facing_question"),
            "mandatory_caveats": list(
                component_ref.get("mandatory_caveats") or ()
            ),
            "prohibited_upgrades": list(
                component_ref.get("prohibited_upgrades") or ()
            ),
        },
        "component_evidence": _safe_mapping(evidence_input),
    }
    packet["quantitative_source_catalog"] = (
        build_component_quantitative_source_catalog(
            component_ref=packet["component_ref"],
            evidence_input=packet["component_evidence"],
        )
    )
    packet["quantitative_specialist_proposal_contract"] = (
        build_quantitative_specialist_proposal_contract(
            target_kind="component",
            target_key_or_rule=str(packet["component_ref"]["component_id"]),
            allowed_source_local_keys=("component_evidence",),
        )
    )
    return packet


def component_analyst_resume_input_packet(
    *,
    analyst_artifact: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    specialist_need_handoff: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact, model-safe input for one component Analyst resumption."""

    from core.specialist_graph_runtime import (
        SpecialistGraphRuntimeError,
        specialist_need_handoff_packet,
        validate_specialist_need_handoff,
    )

    analyst = validate_multicomponent_role_artifact(
        analyst_artifact,
        expected_role=ROLE_COMPONENT_ANALYST,
    )
    supplied_input = _safe_mapping(analyst_input_packet)
    run_binding = _safe_mapping(supplied_input.get("run_binding"))
    component_ref = _safe_mapping(supplied_input.get("component_ref"))
    evidence_input = _safe_mapping(supplied_input.get("component_evidence"))
    run_id = _clean_text(run_binding.get("run_id"), limit=200)
    request_id = _clean_text(run_binding.get("request_id"), limit=200)
    accepted_contract_version = _clean_text(
        run_binding.get("accepted_contract_version"), limit=200
    )
    accepted_contract_digest = _clean_text(
        run_binding.get("accepted_contract_digest"), limit=128
    )
    component_id = _clean_text(component_ref.get("component_id"), limit=200)
    if not (
        run_id
        and request_id
        and accepted_contract_version
        and accepted_contract_digest
        and component_id
    ):
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume requires an exact Analyst input packet"
        )
    if analyst.get("run_id") != run_id or analyst.get("request_id") != request_id:
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume input cross-run binding"
        )
    exact_input = component_analyst_input_packet(
        run_id=run_id,
        request_id=request_id,
        accepted_contract={
            "accepted_contract_version": accepted_contract_version,
            "accepted_contract_digest": accepted_contract_digest,
        },
        component_ref=component_ref,
        evidence_input=evidence_input,
    )
    if (
        supplied_input != exact_input
        or analyst.get("input_packet_digest") != safe_packet_digest(exact_input)
    ):
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume exact input binding mismatch"
        )
    try:
        handoff = validate_specialist_need_handoff(specialist_need_handoff)
    except SpecialistGraphRuntimeError as exc:
        raise MulticomponentComponentAdmissionError(str(exc)) from exc
    target = _safe_mapping(handoff.get("canonical_target_ref"))
    if (
        target.get("target_kind") != "component"
        or target.get("target_key") != component_id
        or target.get("target_revision") != component_ref.get("component_revision")
        or target.get("target_digest") != component_ref.get("component_digest")
    ):
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume Specialist handoff target mismatch"
        )
    analyst_case_ref = role_artifact_ref(analyst)
    origin_artifact_ref = _safe_mapping(handoff.get("origin_artifact_ref"))
    if (
        handoff.get("origin_role") != ROLE_COMPONENT_ANALYST
        or (origin_artifact_ref and origin_artifact_ref != analyst_case_ref)
    ):
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume Specialist handoff origin mismatch"
        )
    return {
        "supported_query_class": exact_input["supported_query_class"],
        "component_analyst_case_ref": analyst_case_ref,
        "component_analyst_input_digest": safe_packet_digest(exact_input),
        "prior_component_case": deepcopy(analyst["semantic_output"]),
        "exact_component_and_evidence_input": deepcopy(exact_input),
        "specialist_need_handoff": specialist_need_handoff_packet(handoff),
    }


def component_dprime_input_packet(
    *,
    analyst_artifact: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    specialist_need_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    analyst = validate_multicomponent_role_artifact(
        analyst_artifact,
        expected_role=ROLE_COMPONENT_ANALYST,
    )
    exact_component_input = _safe_mapping(analyst_input_packet)
    exact_component_input.pop(
        "quantitative_specialist_proposal_contract", None
    )
    packet = {
        "supported_query_class": (
            "ordinary-bounded-multicomponent-factual-synthesis-v1"
        ),
        "analyst_artifact_ref": role_artifact_ref(analyst),
        "nominated_claim": {
            "claim_text": analyst["semantic_output"]["claim_text"],
            "support_status": analyst["semantic_output"]["support_status"],
            "caveats": list(analyst["semantic_output"].get("caveats") or ()),
            "nonclaims": list(
                analyst["semantic_output"].get("nonclaims") or ()
            ),
        },
        "exact_component_and_evidence_input": exact_component_input,
    }
    if specialist_need_handoff:
        from core.specialist_graph_runtime import (
            specialist_need_handoff_packet,
            validate_specialist_need_handoff,
        )

        handoff = validate_specialist_need_handoff(specialist_need_handoff)
        target = _safe_mapping(handoff.get("canonical_target_ref"))
        component_id = _safe_mapping(
            analyst_input_packet.get("component_ref")
        ).get("component_id")
        if (
            target.get("target_kind") != "component"
            or target.get("target_key") != component_id
        ):
            raise ValueError(
                "component D-prime Specialist handoff target mismatch"
            )
        packet["specialist_need_handoff"] = specialist_need_handoff_packet(
            handoff
        )
    return packet


def _typed_lane_custody_gap_exception_authorized(
    accepted_contract: Mapping[str, Any],
) -> bool:
    """Return True only for the exact Phase 1 typed-lane contract shape."""

    metadata = _safe_mapping(accepted_contract.get("question_meaning_metadata"))
    component_refs = [
        item
        for item in accepted_contract.get("accepted_answer_component_refs") or ()
        if isinstance(item, Mapping)
    ]
    return (
        metadata.get("explicit_factual_component_list") is True
        and _clean_text(metadata.get("requested_synthesis_directive"), limit=360) is not None
        and 2 <= len(component_refs) <= 5
    )


def _exact_component_analyst_input_for_admission(
    *,
    analyst: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    run_id: str,
    request_id: str,
    accepted_contract: Mapping[str, Any],
    component: Mapping[str, Any],
    evaluation_key: str,
    specialist_need_handoff: Mapping[str, Any] | None,
    independent_dispatch_input_digest: str | None = None,
    contract_authority_facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the exact initial or bounded-resume Analyst input."""

    analyst_role = str(analyst.get("role") or "")
    supplied_input = _safe_mapping(analyst_input_packet)
    if analyst_role == ROLE_COMPONENT_ANALYST:
        base_input = supplied_input
    elif analyst_role == ROLE_COMPONENT_ANALYST_RESUME:
        base_input = _safe_mapping(
            supplied_input.get("exact_component_and_evidence_input")
        )
    else:
        raise MulticomponentComponentAdmissionError(
            "component admission requires a Component Analyst case role"
        )
    expected_base_input = component_analyst_input_packet(
        run_id=run_id,
        request_id=request_id,
        accepted_contract=accepted_contract,
        component_ref=component,
        evidence_input=_safe_mapping(base_input.get("component_evidence")),
    )
    if analyst_role == ROLE_COMPONENT_ANALYST:
        if analyst.get("input_packet_digest") != safe_packet_digest(
            expected_base_input
        ):
            raise MulticomponentComponentAdmissionError(
                COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH,
                component_analyst_input_binding_mismatch_v1=(
                    build_component_analyst_input_binding_mismatch_v1(
                        analyst=analyst,
                        supplied_input=supplied_input,
                        reconstructed_input=expected_base_input,
                        accepted_contract=accepted_contract,
                        accepted_component=component,
                        independent_dispatch_input_digest=(
                            independent_dispatch_input_digest
                        ),
                        contract_authority_facts=contract_authority_facts,
                    )
                ),
            )
        return expected_base_input

    if base_input != expected_base_input:
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume base input binding mismatch"
        )
    initial_case_ref = _safe_mapping(
        supplied_input.get("component_analyst_case_ref")
    )
    prior_case = _safe_mapping(supplied_input.get("prior_component_case"))
    if (
        supplied_input.get("supported_query_class")
        != expected_base_input.get("supported_query_class")
        or supplied_input.get("component_analyst_input_digest")
        != safe_packet_digest(expected_base_input)
        or initial_case_ref.get("role") != ROLE_COMPONENT_ANALYST
        or initial_case_ref.get("run_id") != run_id
        or initial_case_ref.get("request_id") != request_id
        or initial_case_ref.get("logical_evaluation_key") != evaluation_key
        or initial_case_ref.get("input_packet_digest")
        != safe_packet_digest(expected_base_input)
        or not initial_case_ref.get("artifact_digest")
        or not prior_case
    ):
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume prior-case/input binding mismatch"
        )
    if not specialist_need_handoff:
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume requires the exact Specialist handoff"
        )
    from core.specialist_graph_runtime import (
        VALIDATOR_COMPONENT_ANALYST,
        VALIDATOR_TERMINAL,
        SpecialistGraphRuntimeError,
        specialist_need_handoff_packet,
        validate_specialist_need_handoff,
    )

    try:
        handoff = validate_specialist_need_handoff(specialist_need_handoff)
    except SpecialistGraphRuntimeError as exc:
        raise MulticomponentComponentAdmissionError(str(exc)) from exc
    target = _safe_mapping(handoff.get("canonical_target_ref"))
    if (
        target.get("target_kind") != "component"
        or target.get("target_key") != component.get("component_id")
        or target.get("target_revision") != component.get("component_revision")
        or target.get("target_digest") != component.get("component_digest")
        or handoff.get("validator_consumption") != VALIDATOR_COMPONENT_ANALYST
        or handoff.get("validator_consumption_terminal") != VALIDATOR_TERMINAL
        or _safe_mapping(handoff.get("validator_artifact_ref"))
        != role_artifact_ref(analyst)
        or supplied_input.get("specialist_need_handoff")
        != specialist_need_handoff_packet(handoff)
    ):
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume Specialist handoff binding mismatch"
        )
    if analyst.get("input_packet_digest") != safe_packet_digest(supplied_input):
        raise MulticomponentComponentAdmissionError(
            "component Analyst resume exact input digest mismatch"
        )
    return expected_base_input
def stage_multicomponent_component_admission(
    *,
    action_id: str,
    run_id: str,
    request_id: str,
    accepted_contract: Mapping[str, Any],
    evidence_ledger_projection: Mapping[str, Any],
    semantic_observation_admission_history: Sequence[Mapping[str, Any]],
    component_coverage_history: Sequence[Mapping[str, Any]],
    component_id: str,
    analyst_artifact: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    semantic_observation: Mapping[str, Any] | None,
    sanitized_content_references: Sequence[Mapping[str, Any]],
    component_coverage_record: Mapping[str, Any] | None,
    specialist_need_handoff: Mapping[str, Any] | None = None,
    allow_searchos_semantic_requirement_historical_gap_exception: bool = False,
    logical_evaluation_key: str | None = None,
    searchos_recovery_cycle_ref: Mapping[str, Any] | None = None,
    independent_dispatch_input_digest: str | None = None,
    contract_authority_facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and stage one Analyst case for RunKernel-owned admission."""

    accepted = _safe_mapping(accepted_contract)
    component = _accepted_component(accepted, component_id)
    analyst = validate_multicomponent_role_artifact(analyst_artifact)
    analyst_role = str(analyst.get("role") or "")
    if analyst_role not in {
        ROLE_COMPONENT_ANALYST,
        ROLE_COMPONENT_ANALYST_RESUME,
    }:
        raise MulticomponentComponentAdmissionError(
            "component admission requires a final Component Analyst case"
        )
    analyst_evaluation_count = (
        2 if analyst_role == ROLE_COMPONENT_ANALYST_RESUME else 1
    )
    if analyst.get("run_id") != run_id or analyst.get("request_id") != request_id:
        raise MulticomponentComponentAdmissionError(
            "component Analyst case cross-run binding"
        )
    evaluation_key = str(logical_evaluation_key or component_id)
    if analyst.get("logical_evaluation_key") != evaluation_key:
        raise MulticomponentComponentAdmissionError(
            "component Analyst logical evaluation key mismatch"
        )
    exact_component_input = _exact_component_analyst_input_for_admission(
        analyst=analyst,
        analyst_input_packet=analyst_input_packet,
        run_id=run_id,
        request_id=request_id,
        accepted_contract=accepted,
        component=component,
        evaluation_key=evaluation_key,
        specialist_need_handoff=specialist_need_handoff,
        independent_dispatch_input_digest=independent_dispatch_input_digest,
        contract_authority_facts=contract_authority_facts,
    )
    evidence_input = _safe_mapping(
        exact_component_input.get("component_evidence")
    )

    case_posture = str(analyst["semantic_output"]["case_posture"])
    supported = case_posture in COMPONENT_ANALYST_SUPPORTING_CASE_POSTURES
    observation_payload = _safe_mapping(semantic_observation)
    content_refs = [
        _safe_mapping(item)
        for item in sanitized_content_references
        if isinstance(item, Mapping)
    ]
    coverage_payload = _safe_mapping(component_coverage_record)
    if supported and (
        not observation_payload or not content_refs or not coverage_payload
    ):
        raise MulticomponentComponentAdmissionError(
            "supported component admission requires semantic observation, content refs, and coverage"
        )
    if not supported and (observation_payload or content_refs or coverage_payload):
        raise MulticomponentComponentAdmissionError(
            "non-supporting component Analyst case cannot manufacture admitted semantic state"
        )
    claim_text = analyst["semantic_output"].get("claim_text")
    if supported and observation_payload.get("claim_or_value") != claim_text:
        raise MulticomponentComponentAdmissionError(
            "SemanticObservation claim must equal the Analyst-nominated claim"
        )
    if supported:
        expected_evidence_ref = evidence_input.get("evidence_ref_id")
        observation_evidence = [
            item for item in observation_payload.get("evidence_refs") or () if item
        ]
        if (
            not expected_evidence_ref
            or observation_evidence != [expected_evidence_ref]
            or any(
                item.get("evidence_ref_id") != expected_evidence_ref
                for item in content_refs
            )
        ):
            raise MulticomponentComponentAdmissionError(
                "component admission evidence bindings must match Analyst input evidence"
            )

    admission_state: dict[str, Any] = {}
    admission_projection: dict[str, Any] = {}
    coverage_state: dict[str, Any] = {}
    coverage_projection: dict[str, Any] = {}
    if supported:
        admission_inputs = {
            "semantic_observation_id": observation_payload.get(
                "observation_id"
            ),
            "semantic_observation_digest": observation_payload.get(
                "observation_digest"
            ),
            "accepted_contract_digest": accepted.get(
                "accepted_contract_digest"
            ),
            "accepted_contract_version": accepted.get(
                "accepted_contract_version"
            ),
            "answer_component_id": component["component_id"],
            "component_revision": component["component_revision"],
            "component_digest": component["component_digest"],
            "request_id": request_id,
        }
        try:
            admission_state = build_semantic_observation_admission_state(
                action_id=action_id,
                action_inputs=admission_inputs,
                observation_payload={
                    "semantic_observation": observation_payload,
                    "sanitized_content_references": content_refs,
                },
                accepted_contract=accepted,
                evidence_ledger_projection=evidence_ledger_projection,
                existing_observation_ids=[
                    _safe_mapping(item).get("observation_id")
                    for item in semantic_observation_admission_history
                ],
                existing_observation_digests=[
                    _safe_mapping(item).get("observation_digest")
                    for item in semantic_observation_admission_history
                ],
                run_id=run_id,
                request_id=request_id,
            )
            admission_projection = build_semantic_observation_admission_projection(
                admission_state=admission_state
            )
            coverage_inputs = {
                "coverage_record_id": coverage_payload.get("record_id"),
                "coverage_record_digest": coverage_payload.get("record_digest"),
                "accepted_contract_digest": accepted.get(
                    "accepted_contract_digest"
                ),
                "accepted_contract_version": accepted.get(
                    "accepted_contract_version"
                ),
                "answer_component_id": component["component_id"],
                "component_revision": component["component_revision"],
                "component_digest": component["component_digest"],
                "request_id": request_id,
            }
            coverage_state = build_component_coverage_reduction_state(
                action_id=action_id,
                action_inputs=coverage_inputs,
                coverage_payload={
                    "component_coverage_record": coverage_payload,
                },
                accepted_contract=accepted,
                admission_history=[
                    *[
                        deepcopy(dict(item))
                        for item in semantic_observation_admission_history
                    ],
                    admission_projection,
                ],
                evidence_ledger_projection=evidence_ledger_projection,
                existing_coverage_record_ids=[
                    _safe_mapping(item).get("coverage_record_id")
                    for item in component_coverage_history
                ],
                existing_coverage_record_digests=[
                    _safe_mapping(item).get("coverage_record_digest")
                    for item in component_coverage_history
                ],
                run_id=run_id,
                request_id=request_id,
                ignore_satisfied_provider_job_historical_gaps=(
                    _typed_lane_custody_gap_exception_authorized(accepted)
                    or (
                        allow_searchos_semantic_requirement_historical_gap_exception
                        and any(
                            str(item).startswith(
                                "searchos_semantic_requirement:"
                            )
                            for item in _safe_mapping(
                                coverage_payload.get("evidence_ledger_binding")
                            ).get("source_requirement_ids", ())
                        )
                    )
                ),
            )
            coverage_projection = build_component_coverage_reduction_projection(
                coverage_state=coverage_state
            )
        except (
            SemanticObservationAdmissionError,
            ComponentCoverageReductionError,
        ) as exc:
            raise MulticomponentComponentAdmissionError(str(exc)) from exc

    caveats = list(analyst["semantic_output"].get("caveats", ()))
    nonclaims = list(analyst["semantic_output"].get("nonclaims", ()))
    blockers = list(analyst["semantic_output"].get("blockers", ()))
    admission_status = (
        "admitted_with_caveats"
        if supported and caveats
        else "admitted"
        if supported
        else "unsupported"
        if case_posture == "unsupported"
        else "blocked"
    )
    analyst_case_ref = role_artifact_ref(analyst)
    specialist_quantitative_authority_ref = (
        specialist_quantitative_authority_ref_from_handoff(
            specialist_need_handoff,
            applicable_analyst_case_ref=analyst_case_ref,
        )
        if supported and specialist_need_handoff
        else {}
    )
    return {
        "admission_state": admission_state,
        "admission_projection": admission_projection,
        "coverage_state": coverage_state,
        "coverage_projection": coverage_projection,
        "component_admission_ref": {
            "schema_version": "multicomponent_component_admission_ref_v1",
            "owner": MULTICOMPONENT_COMPONENT_ADMISSION_OWNER,
            "canonical_state": True,
            "run_id": run_id,
            "request_id": request_id,
            "action_id": action_id,
            "accepted_contract_version": accepted.get(
                "accepted_contract_version"
            ),
            "accepted_contract_digest": accepted.get(
                "accepted_contract_digest"
            ),
            "component_id": component["component_id"],
            "logical_evaluation_key": evaluation_key,
            "component_revision": component["component_revision"],
            "component_digest": component["component_digest"],
            "case_posture": case_posture,
            "admission_status": admission_status,
            "current": True,
            "stale": False,
            "component_analyst_case_ref": analyst_case_ref,
            # Compatibility alias; the component case ref is the authority.
            "analyst_finding_ref": deepcopy(analyst_case_ref),
            "specialist_quantitative_authority_ref": (
                specialist_quantitative_authority_ref
            ),
            "admitted_claim_ref": (
                {
                    "claim_id": f"component-claim:{component['component_id']}",
                    "claim_text": claim_text,
                    "claim_digest": safe_packet_digest(
                        {"claim_text": claim_text}
                    ),
                }
                if supported
                else {}
            ),
            "semantic_observation_ref": (
                {
                    "observation_id": admission_projection.get(
                        "observation_id"
                    ),
                    "observation_digest": admission_projection.get(
                        "observation_digest"
                    ),
                }
                if admission_projection
                else {}
            ),
            "component_coverage_ref": (
                {
                    "coverage_record_id": coverage_projection.get(
                        "coverage_record_id"
                    ),
                    "coverage_record_digest": coverage_projection.get(
                        "coverage_record_digest"
                    ),
                    "run_id": coverage_projection.get("run_id"),
                    "request_id": coverage_projection.get("request_id"),
                    "coverage_state": coverage_projection.get("coverage_state"),
                    "answer_component_id": coverage_projection.get(
                        "answer_component_id"
                    ),
                    "component_revision": coverage_projection.get(
                        "component_revision"
                    ),
                    "component_digest": coverage_projection.get(
                        "component_digest"
                    ),
                    "accepted_contract_version": coverage_projection.get(
                        "accepted_contract_version"
                    ),
                    "accepted_contract_digest": coverage_projection.get(
                        "accepted_contract_digest"
                    ),
                    "source_requirement_ids": list(
                        dict(
                            coverage_projection.get(
                                "evidence_ledger_binding"
                            )
                            or {}
                        ).get("source_requirement_ids")
                        or ()
                    ),
                    "source_obligation_ids": list(
                        coverage_projection.get("source_obligation_ids") or ()
                    ),
                    "candidate_ids": list(
                        coverage_projection.get("candidate_ids") or ()
                    ),
                    "owned_requirement_candidate_refs": [
                        dict(item)
                        for item in coverage_projection.get(
                            "owned_requirement_candidate_refs"
                        )
                        or ()
                        if isinstance(item, Mapping)
                    ],
                }
                if coverage_projection
                else {}
            ),
            "evidence_refs": [
                {
                    "evidence_ref_id": item.get("evidence_ref_id"),
                    "content_ref_id": item.get("content_ref_id"),
                    "content_digest": item.get("content_digest"),
                }
                for item in content_refs
            ],
            "required_caveats": caveats,
            "preserved_nonclaims": nonclaims,
            "blocker_refs": [{"reason": item} for item in blockers],
            "searchos_recovery_cycle_ref": deepcopy(
                _safe_mapping(searchos_recovery_cycle_ref)
            ),
            "same_component_reassessment": bool(
                searchos_recovery_cycle_ref
            ),
            "derived_component_recovery": False,
            "scrutineer_recovery_input": False,
            "logical_component_analyst_evaluations": analyst_evaluation_count,
            "physical_component_analyst_calls": analyst_evaluation_count,
        },
    }


def execute_multicomponent_component_admission(
    *,
    run_kernel: Any,
    component_id: str,
    analyst_artifact: Mapping[str, Any],
    analyst_input_packet: Mapping[str, Any],
    semantic_observation: Mapping[str, Any] | None,
    sanitized_content_references: Sequence[Mapping[str, Any]],
    component_coverage_record: Mapping[str, Any] | None,
    specialist_need_handoff: Mapping[str, Any] | None = None,
    allow_searchos_semantic_requirement_historical_gap_exception: bool = False,
    logical_evaluation_key: str | None = None,
    searchos_recovery_cycle_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage then atomically admit one completed Component Analyst case."""

    from core.run_kernel import Observation, RunStageStatus

    analyst = validate_multicomponent_role_artifact(analyst_artifact)
    analyst_role = str(analyst.get("role") or "")
    if analyst_role not in {
        ROLE_COMPONENT_ANALYST,
        ROLE_COMPONENT_ANALYST_RESUME,
    }:
        raise MulticomponentComponentAdmissionError(
            "component admission requires a final Component Analyst case"
        )
    evaluation_key = str(logical_evaluation_key or component_id)
    completed_analyst = run_kernel.state.projections.get(
        f"multicomponent_role:{analyst_role}:{evaluation_key}"
    )
    if (
        not isinstance(completed_analyst, Mapping)
        or role_artifact_ref(completed_analyst) != role_artifact_ref(analyst)
    ):
        raise MulticomponentComponentAdmissionError(
            "component admission requires the exact completed RunKernel Analyst case"
        )
    action = run_kernel.authorize_multicomponent_component_admission(
        component_id=component_id,
        analyst_artifact_digest=analyst["artifact_digest"],
        logical_evaluation_key=evaluation_key,
        searchos_recovery_cycle_ref=searchos_recovery_cycle_ref,
    )
    accepted_contract = (
        run_kernel.state.current_answer_contract
        or run_kernel.state.initial_answer_contract
    )
    staged = stage_multicomponent_component_admission(
        action_id=action.action_id,
        run_id=run_kernel.state.run_id,
        request_id=run_kernel.state.request_id,
        accepted_contract=accepted_contract,
        evidence_ledger_projection=(
            run_kernel.state.evidence_ledger.to_projection().to_dict()
        ),
        semantic_observation_admission_history=(
            run_kernel.state.semantic_observation_admission_history
        ),
        component_coverage_history=run_kernel.state.component_coverage_history,
        component_id=component_id,
        analyst_artifact=analyst,
        analyst_input_packet=analyst_input_packet,
        semantic_observation=semantic_observation,
        sanitized_content_references=sanitized_content_references,
        component_coverage_record=component_coverage_record,
        specialist_need_handoff=specialist_need_handoff,
        allow_searchos_semantic_requirement_historical_gap_exception=(
            allow_searchos_semantic_requirement_historical_gap_exception
        ),
        logical_evaluation_key=evaluation_key,
        searchos_recovery_cycle_ref=searchos_recovery_cycle_ref,
        independent_dispatch_input_digest=(
            independent_component_analyst_dispatch_input_digest(
                run_kernel,
                evaluation_key=evaluation_key,
            )
            if analyst_role == ROLE_COMPONENT_ANALYST
            else None
        ),
        contract_authority_facts=contract_authority_facts_from_run_kernel(
            run_kernel
        ),
    )
    component_ref = staged["component_admission_ref"]
    prior = _safe_mapping(
        run_kernel.state.projections.get(MULTICOMPONENT_COMPONENT_ADMISSION_STAGE)
    )
    prior_refs = [
        deepcopy(dict(item))
        for item in prior.get("component_admission_refs") or ()
        if isinstance(item, Mapping)
    ]
    if any(
        item.get("logical_evaluation_key") == evaluation_key
        for item in prior_refs
    ):
        raise MulticomponentComponentAdmissionError(
            "component admission logical evaluation is already present"
        )
    if (
        any(item.get("component_id") == component_id for item in prior_refs)
        and not searchos_recovery_cycle_ref
    ):
        raise MulticomponentComponentAdmissionError(
            "component admission is append-only and component is already present"
        )
    refs = [*prior_refs, component_ref]
    aggregate_core = {
        "schema_version": "multicomponent_component_admission_projection_v1",
        "owner": MULTICOMPONENT_COMPONENT_ADMISSION_OWNER,
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "run_id": run_kernel.state.run_id,
        "request_id": run_kernel.state.request_id,
        "accepted_contract_version": accepted_contract.get(
            "accepted_contract_version"
        ),
        "accepted_contract_digest": accepted_contract.get(
            "accepted_contract_digest"
        ),
        "component_admission_refs": refs,
        "component_count": len(refs),
        "admitted_component_count": sum(
            item.get("admission_status") in {"admitted", "admitted_with_caveats"}
            for item in refs
        ),
        "blocked_component_count": sum(
            item.get("admission_status") not in {"admitted", "admitted_with_caveats"}
            for item in refs
        ),
        "logical_component_analyst_evaluations": sum(
            int(item.get("logical_component_analyst_evaluations") or 0)
            for item in refs
        ),
        "physical_component_analyst_calls": sum(
            int(item.get("physical_component_analyst_calls") or 0)
            for item in refs
        ),
        "latest_action_id": action.action_id,
    }
    aggregate = {
        **aggregate_core,
        "projection_digest": safe_packet_digest(aggregate_core),
    }
    run_kernel.reduce(
        Observation.from_action(
            action,
            observation_type=action.expected_observation_type,
            status=RunStageStatus.COMPLETED,
            payload={
                "component_admission_projection": aggregate,
                "component_admission_ref": component_ref,
                "semantic_observation_admission_state": staged["admission_state"],
                "semantic_observation_admission_projection": staged[
                    "admission_projection"
                ],
                "component_coverage_state": staged["coverage_state"],
                "component_coverage_projection": staged["coverage_projection"],
            },
        )
    )
    return deepcopy(component_ref)


__all__ = [
    "COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH",
    "COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION",
    "MULTICOMPONENT_COMPONENT_ADMISSION_OWNER",
    "MULTICOMPONENT_COMPONENT_ADMISSION_STAGE",
    "MulticomponentComponentAdmissionError",
    "build_component_analyst_input_binding_mismatch_v1",
    "component_analyst_input_binding_mismatch_from_exception",
    "component_analyst_input_packet",
    "component_analyst_resume_input_packet",
    "component_dprime_input_packet",
    "contract_authority_facts_from_run_kernel",
    "execute_multicomponent_component_admission",
    "independent_component_analyst_dispatch_input_digest",
    "project_component_analyst_input_binding_mismatch_v1",
    "stage_multicomponent_component_admission",
]
