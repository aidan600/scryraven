from __future__ import annotations

import ast
import inspect
import json
from dataclasses import replace

import pytest

from core.run_authority_contract import (
    RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION,
    ContractSynthesisMode,
    RunContractRequirementKind,
    RunContractStrictness,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    OwnerSpecificScenarioPacket,
)
from scripts.evaluation.search_planner_owner_specific_scenario import (
    OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION,
    OwnerSpecificContextRecord,
    OwnerSpecificRelationshipPurpose,
    OwnerSpecificRelationshipRequirement,
    OwnerSpecificRouterSpecification,
    OwnerSpecificScenarioConstructionError,
    OwnerSpecificScenarioSpecification,
    OwnerSpecificSourceObligation,
    build_owner_specific_scenario_packet,
)
from tests.helpers import search_planner_owner_specific_fakes as owner_fakes


def _obligation(
    requirement_id: str,
    *,
    kind: RunContractRequirementKind = RunContractRequirementKind.OFFICIAL_CURRENT,
) -> OwnerSpecificSourceObligation:
    return OwnerSpecificSourceObligation(
        requirement_id=requirement_id,
        requirement_kind=kind,
        strictness=RunContractStrictness.REQUIRED,
        required_source_class="fictional_primary_record",
        required_source_tier="official",
        required_currentness="current",
        satisfaction_rule="direct fictional premise is required for planning",
        allowed_lower_tier_use="context_only",
        cannot_satisfy_with=("secondary_summary",),
        rationale="fictional direct-premise obligation",
    )


def _direct_spec() -> OwnerSpecificScenarioSpecification:
    return OwnerSpecificScenarioSpecification(
        scenario_id="direct-fictional-case",
        fictional_scenario=True,
        normalized_fictional_user_request=("Identify the fictional Northstar record relevant to Meridian Works."),
        requested_mode="Balanced",
        current_date="2026-08-03",
        focus_academic=False,
        force_intent_news=False,
        include_domains=("meridian.example", "northstar.example"),
        exclude_domains=(),
        news_preferred_domains=(),
        router=OwnerSpecificRouterSpecification(
            intent="General",
            report_type="Research Report",
            query_type="Factual",
            core_topic="Meridian Works fictional record",
            primary_entity="Meridian Works",
            entities=("Meridian Works", "Northstar"),
        ),
        direct_records=(
            OwnerSpecificContextRecord(
                record_id="northstar-record",
                label="Northstar fictional record",
                information_need="Identify the fictional record needed for planning.",
                fictional_summary=("Fictional Northstar record retained only as planning context."),
                source_obligation_requirement_id="northstar-record-source",
            ),
        ),
        source_obligations=(_obligation("northstar-record-source"),),
    )


def _depth_two_spec() -> OwnerSpecificScenarioSpecification:
    records = (
        OwnerSpecificContextRecord(
            record_id="northstar-certificate",
            label="active Northstar certificate",
            information_need="Establish the fictional certificate condition.",
            fictional_summary=("Fictional active Northstar certificate retained for planning."),
            source_obligation_requirement_id="certificate-source",
        ),
        OwnerSpecificContextRecord(
            record_id="registry-designation",
            label="registry designation",
            information_need="Establish the fictional registry designation.",
            fictional_summary=("Fictional registry designation retained for planning."),
            source_obligation_requirement_id="registry-source",
        ),
        OwnerSpecificContextRecord(
            record_id="regional-filing-flag",
            label="regional filing flag",
            information_need="Establish the fictional regional filing flag.",
            fictional_summary=("Fictional regional filing flag retained for planning."),
            source_obligation_requirement_id="regional-source",
        ),
    )
    return OwnerSpecificScenarioSpecification(
        scenario_id="case_03_pure_depth_two_live_confirmation_02",
        fictional_scenario=True,
        normalized_fictional_user_request=(
            "Using the fictional Northstar certificate, registry, and regional "
            "records, determine Meridian Works' filing route."
        ),
        requested_mode="Deep",
        current_date="2026-08-03",
        focus_academic=False,
        force_intent_news=True,
        include_domains=("meridian.example", "northstar.example"),
        exclude_domains=(),
        news_preferred_domains=("northstar.example",),
        router=OwnerSpecificRouterSpecification(
            intent="general",
            report_type="research_report",
            query_type="factual",
            core_topic="Meridian Works filing route",
            primary_entity="Meridian Works",
            entities=("Meridian Works", "Northstar"),
        ),
        direct_records=records,
        source_obligations=(
            _obligation("certificate-source"),
            _obligation(
                "registry-source",
                kind=RunContractRequirementKind.LEGAL_PRIMARY,
            ),
            _obligation("regional-source"),
        ),
        supporting_relationships=(
            OwnerSpecificRelationshipRequirement(
                relationship_id="compliance-class-need",
                purpose=OwnerSpecificRelationshipPurpose.SUPPORTING_PREMISE,
                input_ids=("northstar-certificate", "registry-designation"),
                output_need=(
                    "Determine the compliance-class need from the fictional certificate and registry designation."
                ),
                maximum_depth=1,
                inference_posture="required_inference",
            ),
        ),
        user_facing_relationship=OwnerSpecificRelationshipRequirement(
            relationship_id="filing-route-need",
            purpose=OwnerSpecificRelationshipPurpose.USER_FACING,
            input_ids=("compliance-class-need", "regional-filing-flag"),
            output_need=("Determine the filing-route need from the compliance-class need and regional flag."),
            maximum_depth=2,
            inference_posture="required_inference",
        ),
    )


def test_builds_valid_direct_single_fact_scenario() -> None:
    packet = build_owner_specific_scenario_packet(_direct_spec())

    assert isinstance(packet, OwnerSpecificScenarioPacket)
    assert set(packet.router_input) == {
        "intent",
        "report_type",
        "query_type",
        "core_topic",
        "primary_entity",
        "entities",
        "is_academic",
    }
    assert packet.router_input["intent"] == "general"
    assert packet.router_input["report_type"] == "research_report"
    assert packet.router_input["is_academic"] is packet.focus_academic
    assert packet.include_domains == ("meridian.example", "northstar.example")
    assert set(packet.route_projection) == {"route_id"}
    assert packet.route_projection["route_id"].startswith("route:owner-specific:")
    assert set(packet.run_contract_projection) == {
        "contract_id",
        "schema_version",
        "synthesis_mode",
        "selected_depth",
        "source_requirements",
    }
    assert packet.run_contract_projection["schema_version"] == RUN_AUTHORITY_CONTRACT_SCHEMA_VERSION
    assert packet.run_contract_projection["synthesis_mode"] == ContractSynthesisMode.DETERMINISTIC_TEMPLATE.value
    assert packet.run_contract_projection["selected_depth"] == "Balanced"
    assert packet.run_contract_projection["source_requirements"] == [
        {
            "requirement_id": "northstar-record-source",
            "requirement_kind": "official_current",
            "strictness": "required",
            "required_source_class": "fictional_primary_record",
            "required_source_tier": "official",
            "required_currentness": "current",
            "satisfaction_rule": "direct fictional premise is required for planning",
            "allowed_lower_tier_use": "context_only",
            "cannot_satisfy_with": ["secondary_summary"],
            "rationale": "fictional direct-premise obligation",
        }
    ]
    context = packet.supplied_context
    assert context["construction_version"] == (OWNER_SPECIFIC_SCENARIO_CONSTRUCTION_VERSION)
    assert context["context_posture"] == {
        "fictional_planning_context": True,
        "evidence_admitted": False,
        "answers_question": False,
        "citation_eligible": False,
        "final_answer_authority": False,
        "raw_prompt_retained": False,
        "raw_model_output_retained": False,
        "provider_payload_retained": False,
    }
    assert context["supporting_relationship_requirements"] == []
    assert context["user_facing_relationship_requirements"] == []
    assert context["direct_records"][0]["directly_supplied"] is True
    assert context["direct_records"][0]["source_obligation_kind"] == (RunContractRequirementKind.OFFICIAL_CURRENT.value)


def test_builds_pure_depth_two_witness_without_teacher_or_answer_material() -> None:
    packet = build_owner_specific_scenario_packet(_depth_two_spec())

    context = packet.supplied_context
    direct_records = context["direct_records"]
    assert [record["label"] for record in direct_records] == [
        "active Northstar certificate",
        "regional filing flag",
        "registry designation",
    ]
    assert all(record["directly_supplied"] is True for record in direct_records)
    assert context["supporting_relationship_requirements"] == [
        {
            "relationship_id": "compliance-class-need",
            "purpose": "supporting_premise",
            "input_ids": ["northstar-certificate", "registry-designation"],
            "output_need": (
                "Determine the compliance-class need from the fictional certificate and registry designation."
            ),
            "maximum_depth": 1,
            "inference_posture": "required_inference",
        }
    ]
    assert context["user_facing_relationship_requirements"] == [
        {
            "relationship_id": "filing-route-need",
            "purpose": "user_facing",
            "input_ids": ["compliance-class-need", "regional-filing-flag"],
            "output_need": ("Determine the filing-route need from the compliance-class need and regional flag."),
            "maximum_depth": 2,
            "inference_posture": "required_inference",
        }
    ]
    rendered = json.dumps(packet.to_packet(), sort_keys=True).casefold()
    assert "resulting compliance class" not in rendered
    assert "resulting filing route" not in rendered
    assert "expected searchplanner" not in rendered
    assert "teacher" not in rendered


def test_equivalent_collection_order_is_deterministic_and_round_trips() -> None:
    specification = _depth_two_spec()
    reordered = replace(
        specification,
        direct_records=tuple(reversed(specification.direct_records)),
        source_obligations=tuple(reversed(specification.source_obligations)),
        include_domains=tuple(reversed(specification.include_domains)),
        news_preferred_domains=tuple(reversed(specification.news_preferred_domains)),
    )

    packet = build_owner_specific_scenario_packet(specification)
    equivalent = build_owner_specific_scenario_packet(reordered)

    assert equivalent.to_packet() == packet.to_packet()
    assert equivalent.sha256 == packet.sha256
    assert OwnerSpecificScenarioPacket.from_mapping(packet.to_packet()).to_packet() == packet.to_packet()


def test_route_and_contract_ids_are_sensitive_to_owner_semantics() -> None:
    specification = _direct_spec()
    packet = build_owner_specific_scenario_packet(specification)
    changed_route = build_owner_specific_scenario_packet(
        replace(
            specification,
            router=replace(
                specification.router,
                core_topic="Meridian Works fictional legal record",
            ),
        )
    )
    changed_contract = build_owner_specific_scenario_packet(
        replace(
            specification,
            source_obligations=(
                replace(
                    specification.source_obligations[0],
                    required_source_class="fictional_legal_record",
                ),
            ),
        )
    )

    assert changed_route.route_projection["route_id"] != packet.route_projection["route_id"]
    assert changed_contract.run_contract_projection["contract_id"] != (packet.run_contract_projection["contract_id"])


@pytest.mark.parametrize(
    ("specification", "match"),
    [
        (
            lambda: replace(
                _direct_spec(),
                direct_records=(
                    _direct_spec().direct_records[0],
                    _direct_spec().direct_records[0],
                ),
            ),
            "direct record identities",
        ),
        (
            lambda: replace(_direct_spec(), requested_mode="Unknown"),
            "requested mode",
        ),
        (
            lambda: replace(_direct_spec(), current_date="2026-02-30"),
            "current date",
        ),
        (
            lambda: replace(_direct_spec(), include_domains=("not/a-domain",)),
            "host names",
        ),
        (
            lambda: replace(
                _direct_spec(),
                router=replace(
                    _direct_spec().router,
                    entities=("Meridian Works", "meridian works"),
                ),
            ),
            "router entities",
        ),
        (
            lambda: replace(
                _direct_spec(),
                direct_records=(
                    replace(
                        _direct_spec().direct_records[0],
                        fictional_summary="answer value: fictional route",
                    ),
                ),
            ),
            "forbidden material",
        ),
        (
            lambda: replace(
                _direct_spec(),
                direct_records=(
                    replace(
                        _direct_spec().direct_records[0],
                        label="teacher label",
                    ),
                ),
            ),
            "forbidden material",
        ),
        (
            lambda: replace(
                _direct_spec(),
                source_obligations=(
                    replace(
                        _direct_spec().source_obligations[0],
                        strictness=RunContractStrictness.PREFERRED,
                    ),
                ),
            ),
            "must be required",
        ),
    ],
)
def test_rejects_invalid_typed_scenario_inputs(specification, match: str) -> None:
    with pytest.raises(OwnerSpecificScenarioConstructionError, match=match):
        build_owner_specific_scenario_packet(specification())


@pytest.mark.parametrize(
    "relationship_id",
    ("regional-filing-flag", "REGIONAL-FILING-FLAG"),
    ids=("exact", "case-insensitive"),
)
def test_rejects_supporting_relationship_id_collision_with_direct_record(
    relationship_id: str,
) -> None:
    specification = _depth_two_spec()
    collision = replace(
        specification,
        supporting_relationships=(
            replace(
                specification.supporting_relationships[0],
                relationship_id=relationship_id,
            ),
        ),
        user_facing_relationship=replace(
            specification.user_facing_relationship,
            input_ids=(relationship_id, "northstar-certificate"),
        ),
    )
    with pytest.raises(
        OwnerSpecificScenarioConstructionError,
        match="relationship identities.*direct record identities",
    ):
        build_owner_specific_scenario_packet(collision)


def test_rejects_user_facing_relationship_id_collision_with_direct_record() -> None:
    specification = _depth_two_spec()
    collision = replace(
        specification,
        user_facing_relationship=replace(
            specification.user_facing_relationship,
            relationship_id="regional-filing-flag",
        ),
    )
    with pytest.raises(
        OwnerSpecificScenarioConstructionError,
        match="relationship identities.*direct record identities",
    ):
        build_owner_specific_scenario_packet(collision)


def test_rejects_dangling_cycle_and_direct_source_relationships() -> None:
    specification = _depth_two_spec()
    dangling = replace(
        specification,
        user_facing_relationship=replace(
            specification.user_facing_relationship,
            input_ids=("not-a-bound-input", "regional-filing-flag"),
        ),
    )
    with pytest.raises(OwnerSpecificScenarioConstructionError, match="not bound"):
        build_owner_specific_scenario_packet(dangling)

    cycle = replace(
        specification,
        supporting_relationships=(
            OwnerSpecificRelationshipRequirement(
                relationship_id="support-a",
                purpose=OwnerSpecificRelationshipPurpose.SUPPORTING_PREMISE,
                input_ids=("support-b", "northstar-certificate"),
                output_need="Determine fictional supporting need A.",
                maximum_depth=2,
            ),
            OwnerSpecificRelationshipRequirement(
                relationship_id="support-b",
                purpose=OwnerSpecificRelationshipPurpose.SUPPORTING_PREMISE,
                input_ids=("support-a", "registry-designation"),
                output_need="Determine fictional supporting need B.",
                maximum_depth=2,
            ),
        ),
        user_facing_relationship=OwnerSpecificRelationshipRequirement(
            relationship_id="filing-route-need",
            purpose=OwnerSpecificRelationshipPurpose.USER_FACING,
            input_ids=("support-a", "regional-filing-flag"),
            output_need="Determine fictional filing-route need.",
            maximum_depth=2,
        ),
    )
    with pytest.raises(OwnerSpecificScenarioConstructionError, match="cycle"):
        build_owner_specific_scenario_packet(cycle)

    direct_source = replace(
        specification,
        supporting_relationships=(
            replace(
                specification.supporting_relationships[0],
                source_posture="direct_source",
            ),
        ),
    )
    with pytest.raises(
        OwnerSpecificScenarioConstructionError,
        match="direct-source posture",
    ):
        build_owner_specific_scenario_packet(direct_source)


def test_public_builder_rejects_projection_injection_and_test_imports() -> None:
    assert tuple(inspect.signature(build_owner_specific_scenario_packet).parameters) == ("specification",)
    fields = OwnerSpecificScenarioSpecification.__dataclass_fields__
    assert not {
        "router_input",
        "route_projection",
        "run_contract_projection",
        "supplied_context",
    }.intersection(fields)
    with pytest.raises(OwnerSpecificScenarioConstructionError, match="typed"):
        build_owner_specific_scenario_packet({"route_projection": {}})
    with pytest.raises(TypeError, match="route_projection"):
        OwnerSpecificScenarioSpecification(route_projection={})

    module_source = inspect.getsource(
        __import__(
            "scripts.evaluation.search_planner_owner_specific_scenario",
            fromlist=["*"],
        )
    )
    tree = ast.parse(module_source)
    imported_modules = [
        alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names
    ]
    assert not any(name == "tests" or name.startswith("tests.") for name in imported_modules)


def test_helper_delegates_without_post_build_projection_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = build_owner_specific_scenario_packet(_direct_spec())
    monkeypatch.setattr(
        owner_fakes,
        "build_owner_specific_scenario_packet",
        lambda specification: sentinel,
    )

    assert owner_fakes.scenario_packet() is sentinel
    helper_source = inspect.getsource(owner_fakes.scenario_packet)
    assert "run_contract_fixture_v1" not in helper_source
    assert "offline_fixture" not in helper_source
    helper_tree = ast.parse(helper_source)
    assert not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "OwnerSpecificScenarioPacket"
        for node in ast.walk(helper_tree)
    )
