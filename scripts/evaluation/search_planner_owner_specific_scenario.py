"""Deterministic construction for owner-specific fictional scenarios.

This evaluation-preparation owner turns a typed, teacher-free fictional
scenario specification into the already-installed ``OwnerSpecificScenarioPacket``
shape.  It deliberately has no model, provider, broker, or ordinary-pipeline
dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Mapping, Sequence

from core.run_authority_contract import (
    RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION,
    ContractSynthesisMode,
    RunAuthorityContract,
    RunContractRequirementKind,
    RunContractSourceRequirement,
    RunContractStrictness,
    query_ref,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    SCENARIO_PACKET_SCHEMA_VERSION,
    OwnerSpecificScenarioPacket,
    canonical_sha256,
)

OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION = "owner_specific_scenario_construction_v1"
OWNER_SPECIFIC_SCENARIO_CONTEXT_SCHEMA_VERSION = "owner_specific_fictional_context_v1"
OWNER_SPECIFIC_SCENARIO_CONTRACT_TEMPLATE_ID = "owner_specific_fictional_direct_premise_template_v1"

_OWNER = "OwnerSpecificScenarioConstruction"
_SUPPORTED_MODES = frozenset({"Fast", "Balanced", "Deep"})
_MODE_MAXIMUM_DEPTH = {"Fast": 1, "Balanced": 1, "Deep": 2}
_DIRECT_SOURCE_POSTURES = frozenset({"direct", "direct_source", "directly_supplied", "supplied_direct"})
_DOMAIN_PATTERN = re.compile(r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z")
_FORBIDDEN_MATERIAL = re.compile(
    r"(?:"
    r"api[_ -]?key|authorization\s*:\s*bearer|credential|password|"
    r"session[_ -]?token|secret(?:[_ -]?key)?|"
    r"raw[_ -]?(?:prompt|model[_ -]?(?:output|response)|provider[_ -]?payload)|"
    r"model[_ -]?response|provider[_ -]?payload|"
    r"answer[_ -]?(?:key|value|result|proposal)|"
    r"expected[_ -]?(?:searchplanner[_ -]?)?proposal|"
    r"expected[_ -]?(?:searchplanner[_ -]?)?component(?:[_ -]?ids?)?|"
    r"teacher(?:[_ -]?(?:label|proposal|payload|id))?|"
    r"expected[_ -]?(?:class|route)(?:[_ -]?value)?|"
    r"expected[_ -]?(?:compliance[_ -]?class|filing[_ -]?route)|"
    r"resulting[_ -]?(?:compliance[_ -]?class|filing[_ -]?route)"
    r")",
    re.IGNORECASE,
)


class OwnerSpecificScenarioConstructionError(ValueError):
    """Raised when a typed fictional scenario cannot be safely constructed."""


class OwnerSpecificRelationshipPurpose(str, Enum):
    """The two relationship roles allowed in supplied fictional context."""

    SUPPORTING_PREMISE = "supporting_premise"
    USER_FACING = "user_facing"


@dataclass(frozen=True, slots=True)
class OwnerSpecificRouterSpecification:
    """Typed semantic router facts; the builder owns the final mapping shape."""

    intent: str
    report_type: str
    query_type: str
    core_topic: str
    primary_entity: str
    entities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OwnerSpecificSourceObligation:
    """One explicit direct-premise obligation for the production contract owner."""

    requirement_id: str
    requirement_kind: RunContractRequirementKind | str
    strictness: RunContractStrictness | str
    required_source_class: str
    required_source_tier: str | None = None
    required_currentness: str | None = None
    satisfaction_rule: str | None = None
    allowed_lower_tier_use: str | None = None
    cannot_satisfy_with: tuple[str, ...] = ()
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class OwnerSpecificContextRecord:
    """Bounded planning material for one directly supplied fictional record."""

    record_id: str
    label: str
    information_need: str
    fictional_summary: str
    source_obligation_requirement_id: str
    directly_supplied: bool = True


@dataclass(frozen=True, slots=True)
class OwnerSpecificRelationshipRequirement:
    """A required inferred relationship in the fictional planning graph."""

    relationship_id: str
    purpose: OwnerSpecificRelationshipPurpose | str
    input_ids: tuple[str, ...]
    output_need: str
    maximum_depth: int
    inference_posture: str = "required_inference"
    source_posture: str = "inferred_relationship"


@dataclass(frozen=True, slots=True)
class OwnerSpecificScenarioSpecification:
    """The complete typed input for one owner-specific fictional scenario."""

    scenario_id: str
    fictional_scenario: bool
    normalized_fictional_user_request: str
    requested_mode: str
    current_date: str
    focus_academic: bool
    force_intent_news: bool
    include_domains: tuple[str, ...]
    exclude_domains: tuple[str, ...]
    news_preferred_domains: tuple[str, ...]
    router: OwnerSpecificRouterSpecification
    direct_records: tuple[OwnerSpecificContextRecord, ...]
    source_obligations: tuple[OwnerSpecificSourceObligation, ...]
    supporting_relationships: tuple[OwnerSpecificRelationshipRequirement, ...] = ()
    user_facing_relationship: OwnerSpecificRelationshipRequirement | None = None


@dataclass(frozen=True, slots=True)
class _NormalizedRelationship:
    relationship_id: str
    purpose: OwnerSpecificRelationshipPurpose
    input_ids: tuple[str, ...]
    output_need: str
    maximum_depth: int
    inference_posture: str


def build_owner_specific_scenario_packet(
    specification: OwnerSpecificScenarioSpecification,
) -> OwnerSpecificScenarioPacket:
    """Build one strict, complete, teacher-free scenario packet.

    No final scenario projection can be supplied by callers.  Each projection is
    derived from the typed specification and the installed run-contract owner.
    """

    if not isinstance(specification, OwnerSpecificScenarioSpecification):
        raise OwnerSpecificScenarioConstructionError("scenario construction requires one typed specification")
    scenario_id = _normalize_identifier(specification.scenario_id, "scenario ID")
    if specification.fictional_scenario is not True:
        raise OwnerSpecificScenarioConstructionError("owner-specific scenario construction requires fictional posture")
    request = _normalize_text(
        specification.normalized_fictional_user_request,
        "fictional user request",
        limit=4000,
    )
    requested_mode = _normalize_requested_mode(specification.requested_mode)
    current_date = _normalize_date(specification.current_date)
    focus_academic = _require_bool(
        specification.focus_academic,
        "focus_academic",
    )
    force_intent_news = _require_bool(
        specification.force_intent_news,
        "force_intent_news",
    )
    include_domains = _normalize_domains(
        specification.include_domains,
        "include_domains",
    )
    exclude_domains = _normalize_domains(
        specification.exclude_domains,
        "exclude_domains",
    )
    news_preferred_domains = _normalize_domains(
        specification.news_preferred_domains,
        "news_preferred_domains",
    )
    router_input = _build_router_input(
        specification.router,
        focus_academic=focus_academic,
    )
    source_requirements = _build_source_requirements(specification.source_obligations)
    direct_records = _build_direct_records(
        specification.direct_records,
        source_requirements=source_requirements,
    )
    (
        supporting_relationships,
        user_facing_relationship,
    ) = _build_relationship_requirements(
        specification.supporting_relationships,
        specification.user_facing_relationship,
        direct_record_ids=tuple(item["record_id"] for item in direct_records),
        requested_mode=requested_mode,
    )
    route_projection = _build_route_projection(
        scenario_id=scenario_id,
        request=request,
        requested_mode=requested_mode,
        current_date=current_date,
        focus_academic=focus_academic,
        force_intent_news=force_intent_news,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        news_preferred_domains=news_preferred_domains,
        router_input=router_input,
    )
    contract = _build_run_authority_contract(
        scenario_id=scenario_id,
        request=request,
        requested_mode=requested_mode,
        route_projection=route_projection,
        router_input=router_input,
        source_requirements=source_requirements,
        direct_records=direct_records,
        supporting_relationships=supporting_relationships,
        user_facing_relationship=user_facing_relationship,
    )
    run_contract_projection = reduce_owner_specific_run_contract_projection(contract)
    supplied_context = _build_supplied_context(
        direct_records=direct_records,
        source_requirements=source_requirements,
        supporting_relationships=supporting_relationships,
        user_facing_relationship=user_facing_relationship,
    )
    packet = OwnerSpecificScenarioPacket(
        schema_version=SCENARIO_PACKET_SCHEMA_VERSION,
        scenario_id=scenario_id,
        fictional_scenario=True,
        normalized_fictional_user_request=request,
        requested_mode=requested_mode,
        current_date=current_date,
        focus_academic=focus_academic,
        force_intent_news=force_intent_news,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        news_preferred_domains=news_preferred_domains,
        router_input=router_input,
        route_projection=route_projection,
        run_contract_projection=run_contract_projection,
        supplied_context=supplied_context,
    )
    round_tripped = OwnerSpecificScenarioPacket.from_mapping(packet.to_packet())
    if round_tripped.to_packet() != packet.to_packet():
        raise OwnerSpecificScenarioConstructionError("owner-specific scenario packet did not round-trip")
    return packet


def reduce_owner_specific_run_contract_projection(
    contract: RunAuthorityContract,
) -> dict[str, Any]:
    """Reduce one production run contract to the installed evaluator shape."""

    if not isinstance(contract, RunAuthorityContract):
        raise OwnerSpecificScenarioConstructionError("scenario contract reduction requires RunAuthorityContract")
    if contract.schema_version != RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION:
        raise OwnerSpecificScenarioConstructionError("scenario contract uses an unsupported run-contract schema")
    if contract.synthesis_mode is not ContractSynthesisMode.DETERMINISTIC_TEMPLATE:
        raise OwnerSpecificScenarioConstructionError("scenario contract must use deterministic-template synthesis")
    projection = contract.to_projection()
    return {
        "contract_id": projection["contract_id"],
        "schema_version": projection["schema_version"],
        "synthesis_mode": projection["synthesis_mode"],
        "selected_depth": projection["selected_depth"],
        "source_requirements": projection["source_requirements"],
    }


def _build_router_input(
    specification: OwnerSpecificRouterSpecification,
    *,
    focus_academic: bool,
) -> dict[str, Any]:
    if not isinstance(specification, OwnerSpecificRouterSpecification):
        raise OwnerSpecificScenarioConstructionError("router construction requires one typed router specification")
    primary_entity = _normalize_text(
        specification.primary_entity,
        "router primary_entity",
        limit=500,
    )
    entities = _normalize_entities(specification.entities)
    if entities[0].casefold() != primary_entity.casefold():
        raise OwnerSpecificScenarioConstructionError("router primary entity must be the first stable entity")
    return {
        "intent": _normalize_router_token(specification.intent, "intent"),
        "report_type": _normalize_router_token(
            specification.report_type,
            "report_type",
        ),
        "query_type": _normalize_router_token(
            specification.query_type,
            "query_type",
        ),
        "core_topic": _normalize_text(
            specification.core_topic,
            "router core_topic",
            limit=500,
        ),
        "primary_entity": primary_entity,
        "entities": list(entities),
        "is_academic": focus_academic,
    }


def _build_source_requirements(
    obligations: Sequence[OwnerSpecificSourceObligation],
) -> dict[str, RunContractSourceRequirement]:
    source_items = _require_typed_sequence(
        obligations,
        OwnerSpecificSourceObligation,
        "source obligations",
        allow_empty=False,
    )
    normalized: dict[str, RunContractSourceRequirement] = {}
    for obligation in source_items:
        requirement_id = _normalize_identifier(
            obligation.requirement_id,
            "source obligation ID",
        )
        key = requirement_id.casefold()
        if key in normalized:
            raise OwnerSpecificScenarioConstructionError("source obligation identities must be unique")
        kind = _normalize_enum_value(
            obligation.requirement_kind,
            RunContractRequirementKind,
            "source obligation kind",
        )
        strictness = _normalize_enum_value(
            obligation.strictness,
            RunContractStrictness,
            "source obligation strictness",
        )
        if kind is RunContractRequirementKind.GENERAL:
            raise OwnerSpecificScenarioConstructionError("source obligation kind must name a concrete source posture")
        if strictness is not RunContractStrictness.REQUIRED:
            raise OwnerSpecificScenarioConstructionError("direct-premise source obligations must be required")
        required_source_class = _normalize_text(
            obligation.required_source_class,
            "required source class",
            limit=240,
        )
        normalized[key] = RunContractSourceRequirement(
            requirement_id=requirement_id,
            requirement_kind=kind,
            strictness=strictness,
            required_source_class=required_source_class,
            required_source_tier=_optional_text(
                obligation.required_source_tier,
                "required source tier",
                limit=240,
            ),
            required_currentness=_optional_text(
                obligation.required_currentness,
                "required currentness",
                limit=240,
            ),
            satisfaction_rule=_optional_text(
                obligation.satisfaction_rule,
                "source satisfaction rule",
                limit=260,
            ),
            allowed_lower_tier_use=_optional_text(
                obligation.allowed_lower_tier_use,
                "allowed lower tier use",
                limit=180,
            ),
            cannot_satisfy_with=tuple(
                sorted(
                    _normalize_unique_texts(
                        obligation.cannot_satisfy_with,
                        "cannot_satisfy_with",
                        limit=120,
                    ),
                    key=str.casefold,
                )
            ),
            rationale=_optional_text(
                obligation.rationale,
                "source obligation rationale",
                limit=260,
            ),
        )
    return dict(sorted(normalized.items()))


def _build_direct_records(
    records: Sequence[OwnerSpecificContextRecord],
    *,
    source_requirements: Mapping[str, RunContractSourceRequirement],
) -> tuple[dict[str, Any], ...]:
    record_items = _require_typed_sequence(
        records,
        OwnerSpecificContextRecord,
        "direct records",
        allow_empty=False,
    )
    normalized: list[dict[str, Any]] = []
    record_keys: set[str] = set()
    obligation_keys: set[str] = set()
    for record in record_items:
        record_id = _normalize_identifier(record.record_id, "record ID")
        record_key = record_id.casefold()
        if record_key in record_keys:
            raise OwnerSpecificScenarioConstructionError("direct record identities must be unique")
        record_keys.add(record_key)
        if _require_bool(record.directly_supplied, "directly_supplied") is not True:
            raise OwnerSpecificScenarioConstructionError("fictional context records must be directly supplied")
        obligation_id = _normalize_identifier(
            record.source_obligation_requirement_id,
            "record source obligation ID",
        )
        obligation_key = obligation_id.casefold()
        requirement = source_requirements.get(obligation_key)
        if requirement is None:
            raise OwnerSpecificScenarioConstructionError("direct record references an unknown source obligation")
        if obligation_key in obligation_keys:
            raise OwnerSpecificScenarioConstructionError("each direct record requires one distinct source obligation")
        obligation_keys.add(obligation_key)
        normalized.append(
            {
                "record_id": record_id,
                "label": _normalize_text(record.label, "record label", limit=240),
                "information_need": _normalize_text(
                    record.information_need,
                    "record information need",
                    limit=1000,
                ),
                "fictional_summary": _normalize_text(
                    record.fictional_summary,
                    "fictional record summary",
                    limit=1000,
                ),
                "source_obligation_requirement_id": requirement.requirement_id,
                "source_obligation_kind": requirement.requirement_kind.value,
                "source_obligation_strictness": requirement.strictness.value,
                "directly_supplied": True,
            }
        )
    if obligation_keys != set(source_requirements):
        raise OwnerSpecificScenarioConstructionError("source obligations must each bind one direct record")
    return tuple(sorted(normalized, key=lambda item: item["record_id"].casefold()))


def _build_relationship_requirements(
    supporting: Sequence[OwnerSpecificRelationshipRequirement],
    user_facing: OwnerSpecificRelationshipRequirement | None,
    *,
    direct_record_ids: tuple[str, ...],
    requested_mode: str,
) -> tuple[tuple[_NormalizedRelationship, ...], _NormalizedRelationship | None]:
    supporting_items = _require_typed_sequence(
        supporting,
        OwnerSpecificRelationshipRequirement,
        "supporting relationships",
        allow_empty=True,
    )
    normalized_supporting = tuple(_normalize_relationship(item) for item in supporting_items)
    if any(item.purpose is not OwnerSpecificRelationshipPurpose.SUPPORTING_PREMISE for item in normalized_supporting):
        raise OwnerSpecificScenarioConstructionError("supporting relationships must use supporting-premise purpose")
    normalized_user = _normalize_relationship(user_facing) if user_facing is not None else None
    if normalized_user is not None and normalized_user.purpose is not OwnerSpecificRelationshipPurpose.USER_FACING:
        raise OwnerSpecificScenarioConstructionError("user-facing relationship must use user-facing purpose")
    if normalized_supporting and normalized_user is None:
        raise OwnerSpecificScenarioConstructionError("supporting relationships require one user-facing relationship")
    all_relationships = (*normalized_supporting, *(() if normalized_user is None else (normalized_user,)))
    all_ids = [item.relationship_id for item in all_relationships]
    if len({item.casefold() for item in all_ids}) != len(all_ids):
        raise OwnerSpecificScenarioConstructionError("relationship identities must be unique")
    known_records = {item.casefold() for item in direct_record_ids}
    relationship_by_key = {item.relationship_id.casefold(): item for item in all_relationships}
    for item in all_relationships:
        for input_id in item.input_ids:
            key = input_id.casefold()
            if key not in known_records and key not in relationship_by_key:
                raise OwnerSpecificScenarioConstructionError("relationship input is not bound to context")
    if normalized_user is not None:
        user_key = normalized_user.relationship_id.casefold()
        if any(user_key in {value.casefold() for value in item.input_ids} for item in normalized_supporting):
            raise OwnerSpecificScenarioConstructionError("user-facing relationship must remain terminal")
        if normalized_supporting and not any(
            input_id.casefold() in {item.relationship_id.casefold() for item in normalized_supporting}
            for input_id in normalized_user.input_ids
        ):
            raise OwnerSpecificScenarioConstructionError(
                "user-facing relationship must depend on a supporting relationship"
            )
    depths = _relationship_depths(
        relationship_by_key=relationship_by_key,
        direct_record_keys=known_records,
    )
    mode_maximum = _MODE_MAXIMUM_DEPTH[requested_mode]
    for item in all_relationships:
        depth = depths[item.relationship_id.casefold()]
        if depth > item.maximum_depth or depth > mode_maximum:
            raise OwnerSpecificScenarioConstructionError("relationship depth exceeds its authorized scenario posture")
    return (
        tuple(
            sorted(
                normalized_supporting,
                key=lambda item: item.relationship_id.casefold(),
            )
        ),
        normalized_user,
    )


def _normalize_relationship(
    relationship: OwnerSpecificRelationshipRequirement,
) -> _NormalizedRelationship:
    if not isinstance(relationship, OwnerSpecificRelationshipRequirement):
        raise OwnerSpecificScenarioConstructionError(
            "relationship construction requires typed relationship requirements"
        )
    purpose = _normalize_enum_value(
        relationship.purpose,
        OwnerSpecificRelationshipPurpose,
        "relationship purpose",
    )
    source_posture = _normalize_router_token(
        relationship.source_posture,
        "relationship source posture",
    )
    if source_posture in _DIRECT_SOURCE_POSTURES:
        raise OwnerSpecificScenarioConstructionError("inferred relationships cannot claim direct-source posture")
    if source_posture != "inferred_relationship":
        raise OwnerSpecificScenarioConstructionError("relationship source posture is unsupported")
    inference_posture = _normalize_router_token(
        relationship.inference_posture,
        "relationship inference posture",
    )
    if inference_posture not in {"inferred", "required_inference"}:
        raise OwnerSpecificScenarioConstructionError("relationship inference posture must be required inference")
    input_ids = _normalize_unique_texts(
        relationship.input_ids,
        "relationship input IDs",
        limit=160,
        minimum=2,
    )
    if isinstance(relationship.maximum_depth, bool) or not isinstance(
        relationship.maximum_depth,
        int,
    ):
        raise OwnerSpecificScenarioConstructionError("relationship maximum depth must be an integer")
    if not 1 <= relationship.maximum_depth <= 2:
        raise OwnerSpecificScenarioConstructionError("relationship maximum depth is unsupported")
    return _NormalizedRelationship(
        relationship_id=_normalize_identifier(
            relationship.relationship_id,
            "relationship ID",
        ),
        purpose=purpose,
        input_ids=tuple(sorted(input_ids, key=str.casefold)),
        output_need=_normalize_text(
            relationship.output_need,
            "relationship output need",
            limit=1000,
        ),
        maximum_depth=relationship.maximum_depth,
        inference_posture="required_inference",
    )


def _relationship_depths(
    *,
    relationship_by_key: Mapping[str, _NormalizedRelationship],
    direct_record_keys: set[str],
) -> dict[str, int]:
    resolved: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(node_key: str) -> int:
        if node_key in direct_record_keys:
            return 0
        if node_key in resolved:
            return resolved[node_key]
        if node_key in visiting:
            raise OwnerSpecificScenarioConstructionError("relationship graph contains a cycle")
        relationship = relationship_by_key[node_key]
        visiting.add(node_key)
        value = 1 + max(depth(item.casefold()) for item in relationship.input_ids)
        visiting.remove(node_key)
        resolved[node_key] = value
        return value

    for key in relationship_by_key:
        depth(key)
    return resolved


def _build_route_projection(
    *,
    scenario_id: str,
    request: str,
    requested_mode: str,
    current_date: str,
    focus_academic: bool,
    force_intent_news: bool,
    include_domains: tuple[str, ...],
    exclude_domains: tuple[str, ...],
    news_preferred_domains: tuple[str, ...],
    router_input: Mapping[str, Any],
) -> dict[str, str]:
    digest = canonical_sha256(
        {
            "construction_version": OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION,
            "scenario_id": scenario_id,
            "request_sha256": canonical_sha256({"request": request}),
            "requested_mode": requested_mode,
            "current_date": current_date,
            "focus_academic": focus_academic,
            "force_intent_news": force_intent_news,
            "include_domains": list(include_domains),
            "exclude_domains": list(exclude_domains),
            "news_preferred_domains": list(news_preferred_domains),
            "router_input": dict(router_input),
        }
    )
    return {"route_id": f"route:owner-specific:{digest}"}


def _build_run_authority_contract(
    *,
    scenario_id: str,
    request: str,
    requested_mode: str,
    route_projection: Mapping[str, str],
    router_input: Mapping[str, Any],
    source_requirements: Mapping[str, RunContractSourceRequirement],
    direct_records: tuple[dict[str, Any], ...],
    supporting_relationships: tuple[_NormalizedRelationship, ...],
    user_facing_relationship: _NormalizedRelationship | None,
) -> RunAuthorityContract:
    ordered_requirements = tuple(source_requirements[key] for key in sorted(source_requirements))
    relationship_identity = [
        _relationship_context_projection(item)
        for item in (
            *supporting_relationships,
            *(() if user_facing_relationship is None else (user_facing_relationship,)),
        )
    ]
    contract_id = "run-contract:owner-specific:" + canonical_sha256(
        {
            "construction_version": OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION,
            "scenario_id": scenario_id,
            "route_id": route_projection["route_id"],
            "requested_mode": requested_mode,
            "direct_records": [dict(item) for item in direct_records],
            "source_requirements": [item.to_dict() for item in ordered_requirements],
            "relationship_requirements": relationship_identity,
        }
    )
    return RunAuthorityContract(
        contract_id=contract_id,
        synthesis_mode=ContractSynthesisMode.DETERMINISTIC_TEMPLATE,
        selected_template_ids=(OWNER_SPECIFIC_SCENARIO_CONTRACT_TEMPLATE_ID,),
        user_query_ref=query_ref(request),
        selected_depth=requested_mode,
        route_facts_used=dict(router_input),
        question_type="owner_specific_fictional",
        claim_type="fictional_planning",
        source_requirements=ordered_requirements,
        inference_policy={
            "owner": _OWNER,
            "construction_version": OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION,
            "maximum_depth": _MODE_MAXIMUM_DEPTH[requested_mode],
            "relationship_requirement_count": len(relationship_identity),
            "fictional_context_only": True,
        },
        final_posture_policy={
            "evidence_admitted": False,
            "citation_eligible": False,
            "final_answer_authority": False,
        },
        downstream_hints={"query_strategy_hints": []},
        schema_version=RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION,
    )


def _build_supplied_context(
    *,
    direct_records: tuple[dict[str, Any], ...],
    source_requirements: Mapping[str, RunContractSourceRequirement],
    supporting_relationships: tuple[_NormalizedRelationship, ...],
    user_facing_relationship: _NormalizedRelationship | None,
) -> dict[str, Any]:
    del source_requirements
    return {
        "schema_version": OWNER_SPECIFIC_SCENARIO_CONTEXT_SCHEMA_VERSION,
        "owner": _OWNER,
        "construction_version": OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION,
        "context_posture": {
            "fictional_planning_context": True,
            "evidence_admitted": False,
            "answers_question": False,
            "citation_eligible": False,
            "final_answer_authority": False,
            "raw_prompt_retained": False,
            "raw_model_output_retained": False,
            "provider_payload_retained": False,
        },
        "direct_records": [dict(item) for item in direct_records],
        "supporting_relationship_requirements": [
            _relationship_context_projection(item) for item in supporting_relationships
        ],
        "user_facing_relationship_requirements": (
            [] if user_facing_relationship is None else [_relationship_context_projection(user_facing_relationship)]
        ),
    }


def _relationship_context_projection(
    relationship: _NormalizedRelationship,
) -> dict[str, Any]:
    return {
        "relationship_id": relationship.relationship_id,
        "purpose": relationship.purpose.value,
        "input_ids": list(relationship.input_ids),
        "output_need": relationship.output_need,
        "maximum_depth": relationship.maximum_depth,
        "inference_posture": relationship.inference_posture,
    }


def _normalize_requested_mode(value: Any) -> str:
    mode = _normalize_text(value, "requested mode", limit=32)
    if mode not in _SUPPORTED_MODES:
        raise OwnerSpecificScenarioConstructionError("requested mode is unsupported")
    return mode


def _normalize_date(value: Any) -> str:
    text = _normalize_text(value, "current date", limit=32)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise OwnerSpecificScenarioConstructionError("current date must be ISO-8601") from exc
    if parsed.isoformat() != text:
        raise OwnerSpecificScenarioConstructionError("current date must be YYYY-MM-DD")
    return text


def _normalize_domains(value: Any, label: str) -> tuple[str, ...]:
    values = _require_sequence(value, label)
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        domain = _normalize_text(item, label, limit=253).casefold()
        if _DOMAIN_PATTERN.fullmatch(domain) is None:
            raise OwnerSpecificScenarioConstructionError("domain values must be host names")
        if domain in seen:
            raise OwnerSpecificScenarioConstructionError("domain values must be unique")
        seen.add(domain)
        normalized.append(domain)
    return tuple(sorted(normalized))


def _normalize_entities(value: Any) -> tuple[str, ...]:
    entities = _normalize_unique_texts(
        value,
        "router entities",
        limit=500,
        minimum=1,
    )
    return tuple(entities)


def _normalize_unique_texts(
    value: Any,
    label: str,
    *,
    limit: int,
    minimum: int = 0,
) -> tuple[str, ...]:
    values = _require_sequence(value, label)
    if len(values) < minimum:
        raise OwnerSpecificScenarioConstructionError(f"{label} is incomplete")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _normalize_text(item, label, limit=limit)
        key = text.casefold()
        if key in seen:
            raise OwnerSpecificScenarioConstructionError(f"{label} must be unique")
        seen.add(key)
        normalized.append(text)
    return tuple(normalized)


def _normalize_router_token(value: Any, label: str) -> str:
    return _normalize_text(value, label, limit=240).casefold().replace(" ", "_")


def _normalize_identifier(value: Any, label: str) -> str:
    return _normalize_text(value, label, limit=160)


def _optional_text(value: Any, label: str, *, limit: int) -> str | None:
    if value is None:
        return None
    return _normalize_text(value, label, limit=limit)


def _normalize_text(value: Any, label: str, *, limit: int) -> str:
    if not isinstance(value, str):
        raise OwnerSpecificScenarioConstructionError(f"{label} must be text")
    text = " ".join(value.strip().split())
    if not text or len(text) > limit:
        raise OwnerSpecificScenarioConstructionError(f"{label} is invalid")
    if _FORBIDDEN_MATERIAL.search(text):
        raise OwnerSpecificScenarioConstructionError("scenario input contains forbidden material")
    return text


def _normalize_enum_value(
    value: Any,
    enum_type: type[Enum],
    label: str,
) -> Any:
    raw = value.value if isinstance(value, enum_type) else value
    normalized = _normalize_router_token(raw, label)
    try:
        return enum_type(normalized)
    except ValueError as exc:
        raise OwnerSpecificScenarioConstructionError(f"{label} is unsupported") from exc


def _require_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise OwnerSpecificScenarioConstructionError(f"{label} must be boolean")
    return value


def _require_sequence(value: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise OwnerSpecificScenarioConstructionError(f"{label} must be ordered")
    return tuple(value)


def _require_typed_sequence(
    value: Any,
    item_type: type[Any],
    label: str,
    *,
    allow_empty: bool,
) -> tuple[Any, ...]:
    values = _require_sequence(value, label)
    if not allow_empty and not values:
        raise OwnerSpecificScenarioConstructionError(f"{label} must be nonempty")
    if not all(isinstance(item, item_type) for item in values):
        raise OwnerSpecificScenarioConstructionError(f"{label} must be typed")
    return values


__all__ = [
    "OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION",
    "OWNER_SPECIFIC_SCENARIO_CONTEXT_SCHEMA_VERSION",
    "OWNER_SPECIFIC_SCENARIO_CONTRACT_TEMPLATE_ID",
    "OwnerSpecificContextRecord",
    "OwnerSpecificRelationshipPurpose",
    "OwnerSpecificRelationshipRequirement",
    "OwnerSpecificRouterSpecification",
    "OwnerSpecificScenarioConstructionError",
    "OwnerSpecificScenarioSpecification",
    "OwnerSpecificSourceObligation",
    "build_owner_specific_scenario_packet",
    "reduce_owner_specific_run_contract_projection",
]
