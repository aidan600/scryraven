"""PRODUCT-PATH-REGRESSION: bounded quantitative Specialist activation.

Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: fixed product composition, bounded request/catalog/parser,
pure calculation adapter, claim alignment, S0 handoff authority, and ordinary
component/synthesis consumption.
Runtime consumer: core.ordinary_multicomponent_synthesis_runtime.
Expected cost: detailed phase owner; not ordinary fast_pr tax.
Promotion posture: remain phase_focus unless a smaller durable sentinel is named.
Demotion/retirement condition: replace only with equivalent product-path coverage.
Why not fast_pr: the parser/operator/custody matrix is phase-specific and broad.
"""

from __future__ import annotations

import ast
import json
import re
from copy import deepcopy
from dataclasses import fields
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

import core.ordinary_multicomponent_synthesis_runtime as ordinary_runtime
import core.pipeline_orchestrator as orchestrator
import core.quantitative_specialist_product_activation as quantitative_product
import core.specialist_source_bound_calculation_runtime as legacy_calculation
from core.component_work_graph_v1 import cross_component_input_packet
from core.cost_accounting import CostAccumulator
from core.multicomponent_component_admission import component_analyst_input_packet
from core.multicomponent_graph_scheduling import (
    MULTICOMPONENT_SCHEDULER_STAGE,
    MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION,
    MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION,
    WORK_KIND_SPECIALIST_CAPABILITY,
)
from core.multicomponent_role_runtime import (
    ROLE_COMPONENT_DPRIME,
    ROLE_CROSS_COMPONENT_ANALYST,
    ROLE_SCRUTINEER,
    ROLE_SYNTHESIS_DPRIME,
    ROLE_SYSTEM_PROMPTS,
    SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT,
)
from core.protocols import NullStatusWriter
from core.quantitative_specialist_product_activation import (
    NUMERIC_LITERAL_PARSER_VERSION,
    QUANTITATIVE_CAPABILITY_ID,
    QUANTITATIVE_CAPABILITY_REQUIREMENT,
    QUANTITATIVE_CAPABILITY_VERSION,
    QUANTITATIVE_INPUT_SCHEMA_REF,
    QUANTITATIVE_OPERAND_ALLOWED_FIELDS,
    QUANTITATIVE_OPERAND_REQUIRED_FIELDS,
    QUANTITATIVE_OPERATOR_ROLE_POLICIES,
    QUANTITATIVE_OUTPUT_SCHEMA_REF,
    QUANTITATIVE_PROPOSAL_CONTRACT_DIGEST,
    QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION,
    QUANTITATIVE_REQUEST_ALLOWED_FIELDS,
    QUANTITATIVE_REQUEST_REQUIRED_FIELDS,
    QUANTITATIVE_SYNTHESIS_TARGET_KEY_RULE,
    build_component_quantitative_source_catalog,
    build_quantitative_product_specialist_policy,
    build_quantitative_product_specialist_registry,
    build_quantitative_specialist_proposal_contract,
    build_synthesis_quantitative_source_catalog,
    compose_quantitative_specialist_product_deps,
    parse_source_bound_numeric_literal,
    quantitative_proposal_runtime_schema_facts,
    source_bound_quantitative_calculation_adapter,
    validate_quantitative_specialist_proposal_contract,
)
from core.run_config import RunDeps
from core.specialist_graph_runtime import (
    AVAILABILITY_BUDGET,
    AVAILABILITY_RESULT,
    EXECUTION_BLOCKED,
    EXECUTION_COMPLETED,
    EXECUTION_CONTESTED,
    SPECIALIST_CAPABILITY_REQUEST_MAX_BYTES,
    SPECIALIST_CAPABILITY_REQUEST_MAX_DEPTH,
    SPECIALIST_CAPABILITY_REQUEST_MAX_LIST_ITEMS,
    SPECIALIST_CAPABILITY_REQUEST_MAX_MAPPING_KEYS,
    SPECIALIST_CAPABILITY_REQUEST_MAX_STRING_LENGTH,
    SPECIALIST_WORK_PLANE_STAGE,
    SpecialistGraphRuntimeError,
    closed_specialist_execution_policy,
    closed_specialist_registry,
    normalize_specialist_capability_request,
)
from core.specialist_source_bound_calculation_runtime import (
    evaluate_source_bound_calculation,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    HANDOFF_SEMANTIC,
    HANDOFF_SUFFICIENCY,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)
from tests.test_multicomponent_orchestrator_nonqualifying_timing_01 import (
    ONE_COMPONENT_QUERY,
    SIX_COMPONENT_QUERY,
    _TimingHarness,
)
from tests.test_multicomponent_ordinary_end_to_end_synthesis_01 import (
    NORTHSTAR_REPORT,
    NorthstarHarness,
)
from tests.test_specialist_graph_substrate_01 import SpecialistNorthstarHarness

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _offline_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_offline_runtime(monkeypatch)


def _component_ref() -> dict[str, Any]:
    return {
        "component_id": "component:quantitative",
        "component_revision": "1",
        "component_digest": "component-digest-quantitative",
        "user_facing_label": "Quantitative component",
        "user_facing_question": "What is the derived amount?",
    }


def _evidence(text: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "evidence_status": "available",
        "evidence_ref_id": "evidence:quantitative",
        "bounded_text": text,
        "currentness": "current",
        "source_class": "current_primary_or_official",
        "source_class_posture": "current_primary_or_official",
        "source_tier": "official",
        "conflict_posture": "none",
        "candidate_custody_ref": {
            "candidate_id": "evidence:quantitative",
            "fact_disposition": "accepted",
            "readable_status": "readable",
            "currentness_signal": "current",
            "source_class": "current_primary_or_official",
            "source_tier": "official",
        },
    }
    payload.update(overrides)
    return payload


def _operand(
    key: str,
    literal: str,
    role: str,
    *,
    source: str = "component_evidence",
    occurrence: int | None = None,
    pair_key: str | None = None,
) -> dict[str, Any]:
    result = {
        "local_operand_key": key,
        "source_local_key": source,
        "source_numeric_literal": literal,
        "operand_role": role,
    }
    if occurrence is not None:
        result["literal_occurrence"] = occurrence
    if pair_key is not None:
        result["pair_key"] = pair_key
    return result


def _request(
    *,
    calculation_kind: str = "sum",
    operands: list[dict[str, Any]] | None = None,
    result_literal: str = "30 USD",
    result_unit: str = "USD",
    expected_output_unit: str | None = "USD",
    result_occurrence: int | None = None,
) -> dict[str, Any]:
    claim_binding = {
        "proposed_result_literal": result_literal,
        "literal_occurrence": result_occurrence,
        "expected_result_unit": result_unit,
    }
    return {
        "request_kind": "source_bound_calculation",
        "calculation_kind": calculation_kind,
        "formula_label": f"bounded {calculation_kind}",
        "expected_output_unit": expected_output_unit,
        "expected_precision_posture": "exact_as_reported",
        "operands": operands
        or [
            _operand("a", "10 USD", "term"),
            _operand("b", "20 USD", "term"),
        ],
        "claim_binding": claim_binding,
        "assumptions": [],
        "caveats": [],
    }


def _component_transient(
    *,
    evidence_text: str = "Reported values were 10 USD and 20 USD.",
    claim_text: str = "The combined reported value is 30 USD.",
    request: Mapping[str, Any] | None = None,
    evidence_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = _evidence(evidence_text, **dict(evidence_overrides or {}))
    catalog = build_component_quantitative_source_catalog(
        component_ref=_component_ref(),
        evidence_input=evidence,
        include_material=True,
    )
    return {
        "bounded_question": "Calculate only from selected source literals.",
        "canonical_target_ref": {
            "target_kind": "component",
            "target_key": "component:quantitative",
            "target_revision": "1",
            "target_digest": "component-digest-quantitative",
        },
        "capability_request": deepcopy(dict(request or _request())),
        "quantitative_source_catalog": catalog,
        "nominated_claim": {
            "claim_text": claim_text,
            "claim_digest": "claim-digest",
            "claim_source": "component_analyst_proposal",
        },
    }


def _adapter_result(**kwargs: Any) -> dict[str, Any]:
    return source_bound_quantitative_calculation_adapter(
        _component_transient(**kwargs)
    )


def _synthesis_transient(
    *,
    claim_only_literal: bool = False,
    first_evidence_overrides: Mapping[str, Any] | None = None,
    second_evidence_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    nodes = [
        {
            "component_id": "component:a",
            "component_revision": "1",
            "component_digest": "component-a-digest",
            "node_id": "node:a",
            "node_revision": "1",
            "node_digest": "node-a-digest",
            "admission_status": "admitted",
            "current": True,
            "stale": False,
            "admitted_claim_ref": {
                "claim_id": "claim:a",
                "claim_digest": "claim-a-digest",
                "claim_text": "Component A reports 10 USD.",
            },
            "evidence_refs": [{"content_digest": "content-a"}],
        },
        {
            "component_id": "component:b",
            "component_revision": "1",
            "component_digest": "component-b-digest",
            "node_id": "node:b",
            "node_revision": "1",
            "node_digest": "node-b-digest",
            "admission_status": "admitted",
            "current": True,
            "stale": False,
            "admitted_claim_ref": {
                "claim_id": "claim:b",
                "claim_digest": "claim-b-digest",
                "claim_text": (
                    "Component B reports 999 USD."
                    if claim_only_literal
                    else "Component B reports 20 USD."
                ),
            },
            "evidence_refs": [{"content_digest": "content-b"}],
        },
    ]
    packets = {
        "component:a": {
            "component_evidence": _evidence(
                "Evidence A reports 10 USD.",
                **dict(first_evidence_overrides or {}),
            )
        },
        "component:b": {
            "component_evidence": _evidence(
                "Evidence B reports 20 USD.",
                evidence_ref_id="evidence:b",
                candidate_custody_ref={"candidate_id": "evidence:b"},
                **dict(second_evidence_overrides or {}),
            )
        },
    }
    catalog = build_synthesis_quantitative_source_catalog(
        component_nodes=nodes,
        component_analyst_input_packets=packets,
        include_material=True,
    )
    second_literal = "999 USD" if claim_only_literal else "20 USD"
    return {
        "bounded_question": "Calculate across exact admitted component literals.",
        "canonical_target_ref": {
            "target_kind": "synthesis",
            "target_key": "S",
            "target_revision": 1,
            "target_digest": "synthesis-digest",
        },
        "capability_request": _request(
            operands=[
                _operand("a", "10 USD", "term", source="component_01"),
                _operand("b", second_literal, "term", source="component_02"),
            ]
        ),
        "quantitative_source_catalog": catalog,
        "nominated_claim": {
            "claim_text": "The cross-component total is 30 USD.",
            "claim_digest": "synthesis-claim-digest",
            "claim_source": "cross_component_analyst_proposal",
        },
    }


def test_product_registry_policy_composition_and_closed_defaults() -> None:
    registry = build_quantitative_product_specialist_registry().projection()
    policy = build_quantitative_product_specialist_policy().projection()
    assert registry["capability_count"] == 1
    descriptor = registry["capability_descriptors"][0]
    assert descriptor["capability_id"] == QUANTITATIVE_CAPABILITY_ID
    assert descriptor["version"] == QUANTITATIVE_CAPABILITY_VERSION
    assert descriptor["capability_requirement"] == QUANTITATIVE_CAPABILITY_REQUIREMENT
    assert descriptor["supported_target_kinds"] == ["component", "synthesis"]
    assert descriptor["input_schema_ref"] == QUANTITATIVE_INPUT_SCHEMA_REF
    assert descriptor["output_schema_ref"] == QUANTITATIVE_OUTPUT_SCHEMA_REF
    assert descriptor["deterministic"] is descriptor["side_effect_free"] is True
    assert policy["enabled_capability_ids"] == [QUANTITATIVE_CAPABILITY_ID]
    assert policy["specialist_work_item_limit"] == 1
    assert policy["parallelism"] is policy["recursion"] is False
    assert closed_specialist_registry().projection()["capability_count"] == 0
    assert closed_specialist_execution_policy().projection()[
        "specialist_work_item_limit"
    ] == 0
    defaults = {field.name: field.default for field in fields(RunDeps)}
    assert defaults["specialist_capability_registry"] is None
    assert defaults["specialist_execution_policy"] is None

    deps = SimpleNamespace(
        specialist_capability_registry=None, specialist_execution_policy=None
    )
    # dataclasses.replace is intentionally used only with real RunDeps-like dataclasses.
    with pytest.raises(TypeError):
        compose_quantitative_specialist_product_deps(deps)


def _ordinary_cross_packet_for_contract() -> dict[str, Any]:
    nodes = [
        {
            "component_id": f"component:{index}",
            "component_revision": "1",
            "component_digest": f"component-digest:{index}",
            "node_kind": "component",
            "node_id": f"node:{index}",
            "node_revision": "1",
            "node_digest": f"node-digest:{index}",
            "admission_status": "admitted",
            "current": True,
            "stale": False,
            "admitted_claim_ref": {
                "claim_id": f"claim:{index}",
                "claim_digest": f"claim-digest:{index}",
                "claim_text": f"Component {index} reports {index * 10} USD.",
            },
            "evidence_refs": [{"content_digest": f"content:{index}"}],
        }
        for index in (1, 2)
    ]
    packets = {
        f"component:{index}": {
            "component_evidence": _evidence(
                f"Evidence {index} reports {index * 10} USD.",
                evidence_ref_id=f"evidence:{index}",
                candidate_custody_ref={
                    "candidate_id": f"evidence:{index}",
                    "source_class": "current_primary_or_official",
                    "source_tier": "official",
                },
            )
        }
        for index in (1, 2)
    }
    return cross_component_input_packet(
        component_nodes=nodes,
        accepted_contract_ref={"accepted_contract_digest": "contract-digest"},
        requested_synthesis_directive="Compare the exact values.",
        component_analyst_input_packets=packets,
    )


def test_versioned_proposal_contract_is_shared_by_component_and_cross_inputs() -> None:
    component_packet = component_analyst_input_packet(
        run_id="run",
        request_id="request",
        accepted_contract={
            "accepted_contract_version": "v1",
            "accepted_contract_digest": "contract-digest",
        },
        component_ref=_component_ref(),
        evidence_input=_evidence("Values are 10 USD and 20 USD."),
    )
    cross_packet = _ordinary_cross_packet_for_contract()
    component = component_packet["quantitative_specialist_proposal_contract"]
    cross = cross_packet["quantitative_specialist_proposal_contract"]
    for contract in (component, cross):
        assert contract["schema_version"] == (
            QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION
        )
        assert contract["contract_digest"] == QUANTITATIVE_PROPOSAL_CONTRACT_DIGEST
        assert validate_quantitative_specialist_proposal_contract(contract) == contract
        assert contract["proposal_schema"]["fixed_fields"] == {
            "capability_requirement": QUANTITATIVE_CAPABILITY_REQUIREMENT,
            "candidate_capability_hint": QUANTITATIVE_CAPABILITY_ID,
            "input_schema_ref": QUANTITATIVE_INPUT_SCHEMA_REF,
            "expected_output_schema_ref": QUANTITATIVE_OUTPUT_SCHEMA_REF,
            "recursion_depth": 0,
            "specialist_parent_ref": None,
        }
    assert component["target_contract"] == {
        "target_kind": "component",
        "target_key": _component_ref()["component_id"],
    }
    assert component["allowed_source_local_keys"] == ["component_evidence"]
    assert cross["target_contract"] == {
        "target_kind": "synthesis",
        "target_key_rule": QUANTITATIVE_SYNTHESIS_TARGET_KEY_RULE,
    }
    assert cross["allowed_source_local_keys"] == [
        "component_01",
        "component_02",
    ]
    assert "sibling specialist_need_proposal" in cross["output_rule"]


def test_contract_schema_fields_policies_and_generic_bounds_are_runtime_owned() -> None:
    facts = quantitative_proposal_runtime_schema_facts()
    request = facts["capability_request_schema"]
    operand = request["operand_schema"]
    assert set(request["allowed_fields"]) == QUANTITATIVE_REQUEST_ALLOWED_FIELDS
    assert set(request["required_fields"]) == QUANTITATIVE_REQUEST_REQUIRED_FIELDS
    assert set(operand["allowed_fields"]) == QUANTITATIVE_OPERAND_ALLOWED_FIELDS
    assert set(operand["required_fields"]) == QUANTITATIVE_OPERAND_REQUIRED_FIELDS
    assert request["operator_role_rules"] == QUANTITATIVE_OPERATOR_ROLE_POLICIES
    assert set(request["supported_operators"]) == set(
        QUANTITATIVE_OPERATOR_ROLE_POLICIES
    )
    assert request["limits"] == {
        "maximum_operands": 8,
        "maximum_numeric_literal_characters": 120,
        "generic_capability_request_maximum_canonical_json_bytes": (
            SPECIALIST_CAPABILITY_REQUEST_MAX_BYTES
        ),
        "generic_capability_request_maximum_depth": (
            SPECIALIST_CAPABILITY_REQUEST_MAX_DEPTH
        ),
        "generic_capability_request_maximum_mapping_keys": (
            SPECIALIST_CAPABILITY_REQUEST_MAX_MAPPING_KEYS
        ),
        "generic_capability_request_maximum_list_items": (
            SPECIALIST_CAPABILITY_REQUEST_MAX_LIST_ITEMS
        ),
        "generic_capability_request_maximum_string_characters": (
            SPECIALIST_CAPABILITY_REQUEST_MAX_STRING_LENGTH
        ),
    }
    assert request["raw_operand_array_order_defines_noncommutative_semantics"] is False


def test_contract_digest_is_deterministic_and_schema_drift_fails_closed() -> None:
    one = build_quantitative_specialist_proposal_contract(
        "component", "component:one", ("component_evidence",)
    )
    two = build_quantitative_specialist_proposal_contract(
        "component", "component:one", ("component_evidence",)
    )
    assert one == two
    assert one["instance_digest"] == two["instance_digest"]
    drifted = deepcopy(one)
    drifted["capability_request_schema"]["allowed_fields"].append(
        "model_prior_number"
    )
    with pytest.raises(Exception, match="does not match runtime"):
        validate_quantitative_specialist_proposal_contract(drifted)
    for mutation in (
        {},
        {**one, "schema_version": "stale.v0"},
        {**one, "instance_digest": "malformed"},
    ):
        with pytest.raises(Exception):
            validate_quantitative_specialist_proposal_contract(mutation)


def test_cli_and_ui_compose_fixed_product_deps_without_public_controls() -> None:
    cli = (ROOT / "proplex" / "__main__.py").read_text(encoding="utf-8")
    ui = (ROOT / "ui" / "pages_home.py").read_text(encoding="utf-8")
    diagnostic = (
        ROOT / "scripts" / "ag_live_bound_01_bounded_product_runner.py"
    ).read_text(encoding="utf-8")
    for source in (cli, ui, diagnostic):
        tree = ast.parse(source)
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "compose_quantitative_specialist_product_deps" in calls
    combined = (cli + ui).casefold()
    for forbidden in (
        "--specialist-capability",
        "--specialist-budget",
        "specialist capability selector",
        "specialist budget selector",
    ):
        assert forbidden not in combined


@pytest.mark.parametrize(
    "capability_request",
    (
        {f"k{i}": "x" for i in range(65)},
        {"items": ["x"] * 65},
        {"value": "x" * 1001},
        {"formula_expression": "a+b"},
        {"source_text": "private source material"},
        {"value": object()},
        {"value": b"binary"},
    ),
)
def test_generic_capability_request_rejects_key_list_string_and_material_bounds(
    capability_request: Mapping[str, Any],
) -> None:
    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_capability_request(capability_request)


def test_generic_capability_request_rejects_depth_and_canonical_byte_limits() -> None:
    nested: dict[str, Any] = {"value": "leaf"}
    for _ in range(7):
        nested = {"child": nested}
    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_capability_request(nested)
    with pytest.raises(SpecialistGraphRuntimeError):
        normalize_specialist_capability_request(
            {f"field_{index}": "x" * 1000 for index in range(17)}
        )


@pytest.mark.parametrize(
    "mutator",
    (
        lambda request: request.update({"unknown": True}),
        lambda request: request["operands"][0].update({"numeric_value": 10}),
        lambda request: request["operands"][0].update(
            {"source_numeric_literal": 10}
        ),
        lambda request: request["operands"][0].update({"source_path": "$.x"}),
        lambda request: request.update({"formula_expression": "a+b"}),
        lambda request: request.update({"formula_label": 123}),
        lambda request: request.update({"expected_output_unit": 123}),
        lambda request: request.update({"expected_precision_posture": 123}),
        lambda request: request["operands"][0].update({"label": 123}),
        lambda request: request.update(
            {"operands": request["operands"] * 5}
        ),
        lambda request: request["operands"][1].update(
            {"local_operand_key": "a"}
        ),
    ),
)
def test_quantitative_schema_rejects_unknown_authority_and_operand_bounds(
    mutator: Any,
) -> None:
    request = _request()
    mutator(request)
    result = _adapter_result(request=request)
    assert result["execution_posture"] == EXECUTION_BLOCKED
    assert result["bounded_result"]["calculation_status"] in {
        "invalid_input",
        "blocked",
    }
    assert (
        result["bounded_result"]["deterministic_arithmetic_applied_to_reported_values"]
        is False
    )
    assert result["bounded_result"]["input_provenance"] == "not_established"
    assert result["bounded_result"]["output_provenance"] == "not_produced"


def test_component_catalog_selector_exact_binding_and_repeated_occurrence() -> None:
    packet = component_analyst_input_packet(
        run_id="run",
        request_id="request",
        accepted_contract={
            "accepted_contract_version": "v1",
            "accepted_contract_digest": "contract-digest",
        },
        component_ref=_component_ref(),
        evidence_input=_evidence("10 USD then 10 USD and 20 USD."),
    )
    entry = packet["quantitative_source_catalog"]["component_evidence"]
    assert entry["source_local_key"] == "component_evidence"
    assert entry["source_binding_kind"] == "component_evidence"
    assert entry["allowed_source_field"] == "bounded_text"
    ambiguous = _adapter_result(
        evidence_text="10 USD then 10 USD and 20 USD.",
        request=_request(),
    )
    assert ambiguous["execution_posture"] == EXECUTION_BLOCKED
    selected = _request(
        operands=[
            _operand("a", "10 USD", "term", occurrence=2),
            _operand("b", "20 USD", "term"),
        ]
    )
    assert _adapter_result(
        evidence_text="10 USD then 10 USD and 20 USD.", request=selected
    )["execution_posture"] == EXECUTION_COMPLETED
    unknown = deepcopy(selected)
    unknown["operands"][0]["source_local_key"] = "missing_source"
    assert _adapter_result(request=unknown)["execution_posture"] == EXECUTION_BLOCKED


def test_synthesis_aliases_are_deterministic_and_two_hop_is_enforced() -> None:
    success = source_bound_quantitative_calculation_adapter(_synthesis_transient())
    assert success["execution_posture"] == EXECUTION_COMPLETED
    refs = success["bounded_result"]["literal_binding_refs"]
    assert [item["source_local_key"] for item in refs] == [
        "component_01",
        "component_02",
    ]
    assert all(
        item["underlying_evidence_match_posture"]
        == "exact_literal_found_in_underlying_evidence"
        for item in refs
    )
    blocked = source_bound_quantitative_calculation_adapter(
        _synthesis_transient(claim_only_literal=True)
    )
    assert blocked["execution_posture"] == EXECUTION_BLOCKED
    assert blocked["blockers"] == ["claim_only_numeric_invention"]


def test_ordinary_evidence_bridge_preserves_safe_candidate_facts_with_precedence() -> None:
    bindable = SimpleNamespace(
        evidence_ref_id="candidate:one",
        candidate_record={
            "candidate_id": "candidate:one",
            "source_class": "current_primary_or_official",
            "source_tier": "official",
            "currentness_signal": "current",
            "fact_disposition": "accepted",
            "readable_status": "readable",
        },
        passage={
            "title": "Bounded title",
            "url": "https://example.test/fact",
            "text": "The exact amount is 10 USD.",
            "source_class": "secondary_analysis",
            "source_tier": "secondary",
            "currentness_signal": "stale",
            "conflict_posture": "none",
            "canonical_currency_unit": "USD",
        },
    )
    bridged = ordinary_runtime._evidence_input(bindable)
    assert bridged["source_class"] == "current_primary_or_official"
    assert bridged["source_tier"] == "official"
    assert bridged["currentness"] == "current"
    assert bridged["fact_disposition"] == "accepted"
    assert bridged["readability_posture"] == "readable"
    assert bridged["conflict_posture"] == "none"
    assert bridged["contradictory"] is False
    assert bridged["canonical_currency_unit"] == "USD"
    assert set(bridged["candidate_custody_ref"]) <= {
        "candidate_id",
        "source_class",
        "source_tier",
        "fact_disposition",
        "readable_status",
        "currentness_signal",
        "conflict_posture",
        "contradictory",
        "canonical_currency_unit",
    }
    encoded = json.dumps(bridged)
    assert "provider_payload" not in encoded
    assert "complete candidate" not in encoded


def test_missing_evidence_metadata_stays_unknown_without_favorable_defaults() -> None:
    evidence = {
        "evidence_status": "available",
        "evidence_ref_id": "candidate:one",
        "bounded_text": "Values are 10 USD and 20 USD.",
        "candidate_custody_ref": {"candidate_id": "candidate:one"},
    }
    catalog = build_component_quantitative_source_catalog(
        component_ref=_component_ref(), evidence_input=evidence
    )
    entry = catalog["component_evidence"]
    assert entry["source_class"] == "unknown"
    assert entry["source_tier"] == "unknown"
    assert entry["currentness_posture"] == "unknown"
    assert entry["conflict_posture"] == "unknown"
    assert entry["source_quality_posture"] == "contested_source_posture"
    assert "custodied_component_evidence" not in json.dumps(catalog)
    result = _adapter_result(
        evidence_overrides={
            "source_class": None,
            "source_class_posture": None,
            "source_tier": None,
            "currentness": None,
            "conflict_posture": None,
            "candidate_custody_ref": {
                "candidate_id": "evidence:quantitative"
            },
        }
    )
    assert result["execution_posture"] == EXECUTION_CONTESTED


def test_model_and_execution_catalogs_share_posture_but_only_execution_has_material() -> None:
    cross_packet = _ordinary_cross_packet_for_contract()
    nodes = cross_packet["component_nodes"]
    packets = {
        f"component:{index}": {
            "component_evidence": _evidence(
                f"Evidence {index} reports {index * 10} USD.",
                evidence_ref_id=f"evidence:{index}",
                candidate_custody_ref={
                    "candidate_id": f"evidence:{index}",
                    "source_class": "current_primary_or_official",
                    "source_tier": "official",
                },
            )
        }
        for index in (1, 2)
    }
    model_catalog = build_synthesis_quantitative_source_catalog(
        component_nodes=nodes,
        component_analyst_input_packets=packets,
    )
    execution_catalog = build_synthesis_quantitative_source_catalog(
        component_nodes=nodes,
        component_analyst_input_packets=packets,
        include_material=True,
    )
    assert model_catalog["posture_digest"] == execution_catalog["posture_digest"]
    stripped = deepcopy(execution_catalog)
    for value in stripped.values():
        if isinstance(value, dict):
            value.pop("source_material", None)
    assert stripped == model_catalog
    assert "source_material" not in json.dumps(model_catalog)
    assert "bounded_claim_text" not in json.dumps(model_catalog)
    assert all(
        "source_material" in execution_catalog[f"component_{index:02d}"]
        for index in (1, 2)
    )


@pytest.mark.parametrize(
    "source_class",
    (
        "secondary",
        "secondary_analysis",
        "reputable_secondary",
        "social_signal",
        "social_or_forum",
        "social_media",
        "community",
        "context",
        "blog",
        "forum",
        "unvetted_secondary",
        "weak_secondary",
        "unknown",
    ),
)
def test_weak_secondary_social_and_unknown_sources_are_contested(
    source_class: str,
) -> None:
    result = _adapter_result(
        evidence_overrides={
            "source_class": source_class,
            "source_class_posture": source_class,
            "source_tier": "secondary",
        }
    )
    assert result["execution_posture"] == EXECUTION_CONTESTED
    assert result["bounded_result"]["calculation_status"] == "contested"
    assert all(
        item["source_quality_posture"] == "contested_source_posture"
        for item in result["bounded_result"]["input_refs"]
    )


@pytest.mark.parametrize("missing", ("source_class", "source_tier", "currentness"))
def test_each_missing_quality_dimension_contests_instead_of_completing(
    missing: str,
) -> None:
    overrides: dict[str, Any] = {}
    if missing == "source_class":
        overrides.update(source_class=None, source_class_posture=None)
    elif missing == "source_tier":
        overrides["source_tier"] = None
    else:
        overrides["currentness"] = None
    custody = dict(_evidence("")["candidate_custody_ref"])
    if missing == "source_class":
        custody.pop("source_class", None)
    elif missing == "source_tier":
        custody.pop("source_tier", None)
    else:
        custody.pop("currentness_signal", None)
    overrides["candidate_custody_ref"] = custody
    result = _adapter_result(evidence_overrides=overrides)
    assert result["execution_posture"] == EXECUTION_CONTESTED


def test_current_primary_official_source_completes_and_missing_lineage_blocks() -> None:
    completed = _adapter_result()
    assert completed["execution_posture"] == EXECUTION_COMPLETED
    assert all(
        item["source_quality_posture"] == "authoritative_current_clear"
        for item in completed["bounded_result"]["input_refs"]
    )
    blocked = _adapter_result(
        evidence_overrides={"candidate_custody_ref": {}}
    )
    assert blocked["execution_posture"] == EXECUTION_BLOCKED


def test_synthesis_inherits_weak_underlying_evidence_without_admission_upgrade() -> None:
    result = source_bound_quantitative_calculation_adapter(
        _synthesis_transient(
            second_evidence_overrides={
                "source_class": "secondary_analysis",
                "source_class_posture": "secondary_analysis",
                "source_tier": "secondary",
            }
        )
    )
    assert result["execution_posture"] == EXECUTION_CONTESTED
    refs = result["bounded_result"]["input_refs"]
    assert refs[1]["source_class"] == "secondary_analysis"
    assert refs[1]["source_quality_posture"] == "contested_source_posture"


@pytest.mark.parametrize(
    ("literal", "value", "unit", "precision"),
    (
        ("1,234.50 USD", Decimal("1234.50"), "USD", "exact_as_reported"),
        ("+12.5 percent", Decimal("12.5"), "percent", "exact_as_reported"),
        ("-2 million people", Decimal("-2000000"), "people", "exact_as_reported"),
        ("about 3 billion USD", Decimal("3000000000"), "USD", "approximate_as_reported"),
        ("rounded 4.5 kg", Decimal("4.5"), "kg", "rounded_as_reported"),
    ),
)
def test_closed_decimal_parser_valid_forms(
    literal: str, value: Decimal, unit: str, precision: str
) -> None:
    parsed = parse_source_bound_numeric_literal(literal)
    assert parsed["numeric_value"] == value
    assert parsed["unit"] == unit
    assert parsed["precision_posture"] == precision
    assert parsed["parser_version"] == NUMERIC_LITERAL_PARSER_VERSION


@pytest.mark.parametrize(
    "literal",
    (
        "1,23 USD",
        "1.234,56 USD",
        "(10) USD",
        "1e3 USD",
        "10 million million",
        "ten USD",
    ),
)
def test_closed_decimal_parser_rejects_grouping_locale_expression_and_scale(
    literal: str,
) -> None:
    with pytest.raises(Exception):
        parse_source_bound_numeric_literal(literal)


def test_currency_symbol_requires_exact_catalog_currency_fact() -> None:
    with pytest.raises(Exception):
        parse_source_bound_numeric_literal("$10")
    parsed = parse_source_bound_numeric_literal("$10", canonical_currency_unit="USD")
    assert parsed["numeric_value"] == Decimal("10")
    assert parsed["unit"] == "USD"


@pytest.mark.parametrize(
    ("kind", "evidence_text", "operands", "literal", "unit", "expected"),
    (
        (
            "sum",
            "Values are 10 USD and 20 USD.",
            [_operand("a", "10 USD", "term"), _operand("b", "20 USD", "term")],
            "30 USD",
            "USD",
            "30",
        ),
        (
            "difference",
            "Values are 20 USD and 10 USD.",
            [_operand("a", "20 USD", "minuend"), _operand("b", "10 USD", "subtrahend")],
            "10 USD",
            "USD",
            "10",
        ),
        (
            "product",
            "Factors are 2 items and 3 items.",
            [_operand("a", "2 items", "factor"), _operand("b", "3 items", "factor")],
            "6 items*items",
            "items*items",
            "6",
        ),
        (
            "ratio",
            "Values are 10 items and 2 items.",
            [_operand("a", "10 items", "numerator"), _operand("b", "2 items", "denominator")],
            "5",
            "dimensionless",
            "5",
        ),
        (
            "percentage",
            "Values are 10 items and 20 items.",
            [_operand("a", "10 items", "numerator"), _operand("b", "20 items", "denominator")],
            "50 percent",
            "percent",
            "50",
        ),
        (
            "percentage_point_difference",
            "Rates are 12.5 percent and 2.5 percent.",
            [_operand("a", "12.5 percent", "minuend"), _operand("b", "2.5 percent", "subtrahend")],
            "10 percentage_points",
            "percentage_points",
            "10",
        ),
        (
            "simple_rate",
            "Inputs are 10 USD and 2 hours.",
            [_operand("a", "10 USD", "numerator"), _operand("b", "2 hours", "denominator")],
            "5 USD/hours",
            "USD/hours",
            "5",
        ),
        (
            "weighted_average",
            "Values 10 USD weight 2 shares; values 20 USD weight 1 shares.",
            [
                _operand("av", "10 USD", "value", pair_key="a"),
                _operand("aw", "2 shares", "weight", pair_key="a"),
                _operand("bv", "20 USD", "value", pair_key="b"),
                _operand("bw", "1 shares", "weight", pair_key="b"),
            ],
            "13.33333333333333333333333333 USD",
            "USD",
            "13.33333333333333333333333333",
        ),
    ),
)
def test_all_supported_operators_use_roles_derived_units_and_decimal(
    kind: str,
    evidence_text: str,
    operands: list[dict[str, Any]],
    literal: str,
    unit: str,
    expected: str,
) -> None:
    request = _request(
        calculation_kind=kind,
        operands=operands,
        result_literal=literal,
        result_unit=unit,
        expected_output_unit=unit,
    )
    result = _adapter_result(
        evidence_text=evidence_text,
        claim_text=f"The deterministic result is {literal}.",
        request=request,
    )
    assert result["execution_posture"] == EXECUTION_COMPLETED
    bounded = result["bounded_result"]
    assert bounded["numeric_value_text"] == expected
    assert bounded["result_unit"] == unit
    assert bounded["claim_alignment"]["posture"] == "exact_match"
    assert bounded["input_provenance"] == "source_explicit"
    assert bounded["output_provenance"] == "derived_deterministic"
    assert bounded["deterministic_arithmetic_applied_to_reported_values"] is True


def test_weighted_average_rejects_incomplete_pairs_and_fixture_value_fields() -> None:
    incomplete = _request(
        calculation_kind="weighted_average",
        operands=[
            _operand("av", "10 USD", "value", pair_key="a"),
            _operand("aw", "2 shares", "weight", pair_key="a"),
            _operand("bv", "20 USD", "value", pair_key="b"),
        ],
    )
    assert _adapter_result(request=incomplete)["execution_posture"] == EXECUTION_BLOCKED
    fixture = _request()
    fixture["operands"][0]["fixture_bound"] = True
    assert _adapter_result(request=fixture)["execution_posture"] == EXECUTION_BLOCKED


def test_unit_precision_denominator_and_lineage_fail_closed() -> None:
    mismatch = _request(expected_output_unit="kg")
    assert _adapter_result(request=mismatch)["execution_posture"] == EXECUTION_BLOCKED
    mixed_units = _request(
        operands=[
            _operand("a", "10 USD", "term"),
            _operand("b", "2 kg", "term"),
        ]
    )
    assert (
        _adapter_result(
            evidence_text="Inputs are 10 USD and 2 kg.", request=mixed_units
        )["execution_posture"]
        == EXECUTION_BLOCKED
    )
    missing_units = _request(
        operands=[
            _operand("a", "10", "term"),
            _operand("b", "20", "term"),
        ],
        result_literal="30",
        result_unit="dimensionless",
        expected_output_unit=None,
    )
    assert (
        _adapter_result(
            evidence_text="Inputs are 10 and 20.",
            claim_text="The combined result is 30.",
            request=missing_units,
        )["execution_posture"]
        == EXECUTION_BLOCKED
    )
    denominator = _request(
        calculation_kind="ratio",
        operands=[
            _operand("a", "10 items", "numerator"),
            _operand("b", "0 items", "denominator"),
        ],
        result_literal="0",
        result_unit="dimensionless",
        expected_output_unit="dimensionless",
    )
    assert _adapter_result(
        evidence_text="Inputs are 10 items and 0 items.", request=denominator
    )["execution_posture"] == EXECUTION_BLOCKED
    stale = _adapter_result(
        evidence_overrides={"currentness": "stale"}
    )
    assert stale["execution_posture"] == EXECUTION_CONTESTED
    weak = _adapter_result(
        evidence_overrides={"source_class_posture": "weak_secondary"}
    )
    assert weak["execution_posture"] == EXECUTION_CONTESTED
    missing = _adapter_result(
        evidence_overrides={"candidate_custody_ref": {}}
    )
    assert missing["execution_posture"] == EXECUTION_BLOCKED


@pytest.mark.parametrize(
    ("claim_text", "literal", "unit", "occurrence", "posture"),
    (
        ("The result is 30 USD.", "31 USD", "USD", None, "result_literal_absent"),
        ("The result is 31 USD.", "31 USD", "USD", None, "numeric_mismatch"),
        ("The result is 30 kg.", "30 kg", "kg", None, "unit_mismatch"),
        ("The result is 30 USD and again 30 USD.", "30 USD", "USD", None, "ambiguous_result_literal"),
    ),
)
def test_claim_alignment_nonmatches_are_contested_spent(
    claim_text: str,
    literal: str,
    unit: str,
    occurrence: int | None,
    posture: str,
) -> None:
    request = _request(
        result_literal=literal,
        result_unit=unit,
        result_occurrence=occurrence,
    )
    result = _adapter_result(claim_text=claim_text, request=request)
    assert result["execution_posture"] == EXECUTION_CONTESTED
    assert result["bounded_result"]["claim_alignment"]["posture"] == posture


def test_proposed_claim_literal_is_not_an_operand_and_no_text_is_retained() -> None:
    request = _request(result_literal="999 USD")
    result = _adapter_result(
        claim_text="The nominated but wrong result is 999 USD.", request=request
    )
    assert result["execution_posture"] == EXECUTION_CONTESTED
    assert result["bounded_result"]["numeric_value_text"] == "30"
    retained = json.dumps(result, sort_keys=True)
    assert "Reported values were 10 USD and 20 USD." not in retained
    assert "The nominated but wrong result is 999 USD." not in retained
    for authority in (
        "admission_authority",
        "component_coverage_authority",
        "sufficiency_authority",
        "final_answer_packet_authority",
        "author_authority",
        "citation_authority",
        "source_obligation_authority",
    ):
        assert result["bounded_result"][authority] is False


def test_pure_evaluator_is_shared_without_legacy_reducer_authority() -> None:
    evaluated = evaluate_source_bound_calculation(
        calculation_kind="difference",
        input_records=[
            {
                "label": "a",
                "numeric_value": Decimal("20.5"),
                "unit": "USD",
                "source_bound": True,
                "source_bound_ref": {"reference_ref": {"digest": "a"}},
                "component_id": "component:a",
                "currentness_posture": "current",
                "source_class_posture": "current_primary_or_official",
                "conflict_posture": "none",
            },
            {
                "label": "b",
                "numeric_value": Decimal("10.2"),
                "unit": "USD",
                "source_bound": True,
                "source_bound_ref": {"reference_ref": {"digest": "b"}},
                "component_id": "component:b",
                "currentness_posture": "current",
                "source_class_posture": "current_primary_or_official",
                "conflict_posture": "none",
            },
        ],
        output_unit="USD",
    )
    assert evaluated["result"]["numeric_value_text"] == "10.3"
    source = (
        ROOT / "core" / "quantitative_specialist_product_activation.py"
    ).read_text(encoding="utf-8")
    assert "reduce_specialist_source_bound_calculation" not in source


def test_prompt_contracts_activate_quantitative_roles_but_not_scrutineer() -> None:
    prompts = ROLE_SYSTEM_PROMPTS
    component = prompts["component_analyst"]
    cross = prompts["cross_component_analyst"]
    component_dprime = prompts["component_dprime"]
    synthesis_dprime = prompts["synthesis_dprime"]
    assert "component_evidence" in component
    assert "quantitative_specialist_proposal_contract" in component
    assert "conforming exactly" in component
    assert "supplied fixed capability and schema values exactly" in component
    assert "required only" in component and "optional only" in component
    assert "later cross-component synthesis" in component
    assert "component_01/component_02/..." in cross
    assert "one sibling specialist_need_proposal" in cross
    assert "synthesis_proposals only" not in cross
    assert "underlying current component evidence" in cross
    assert "claim_alignment" in component_dprime
    assert "claim_alignment" in synthesis_dprime
    assert "two-hop source lineage" in synthesis_dprime
    scrutineer = prompts[ROLE_SCRUTINEER]
    assert sha256(scrutineer.encode("utf-8")).hexdigest() == (
        "fcc8ae953911a0f9147c3f91eae4e7dac49c9cfabd57e1b1524c1b8e8669a09c"  # pragma: allowlist secret
    )
    assert "source_bound_quantitative_calculation" not in scrutineer
    assert "claim_alignment" not in scrutineer
    assert sha256(
        SELECTIVE_CROSS_COMPONENT_ANALYST_SYSTEM_PROMPT.encode("utf-8")
    ).hexdigest() == (
        "bc36a9c8c63c00e33fe6a77fd6daaed8200f089593ff054d6a3fbf165be2aeb6"  # pragma: allowlist secret
    )
    for prompt in (component, cross, component_dprime, synthesis_dprime):
        assert "write final" in prompt or "render" in prompt
        assert "authorize search" in prompt
        assert "admit your" in prompt or "admit" in prompt


def _product_proposal(
    *,
    target_kind: str,
    target_key: str,
    capability_request: Mapping[str, Any],
    posture: str = "optional",
) -> dict[str, Any]:
    return {
        "local_need_id": "quantitative-need-one",
        "capability_requirement": QUANTITATIVE_CAPABILITY_REQUIREMENT,
        "candidate_capability_hint": QUANTITATIVE_CAPABILITY_ID,
        "bounded_question": "Calculate the nominated exact source literals.",
        "target": {"target_kind": target_kind, "target_key": target_key},
        "posture": posture,
        "input_schema_ref": QUANTITATIVE_INPUT_SCHEMA_REF,
        "expected_output_schema_ref": QUANTITATIVE_OUTPUT_SCHEMA_REF,
        "input_artifact_refs": [],
        "assumptions": [],
        "caveats": [],
        "nonclaims": ["The calculator does not admit the nominated claim."],
        "advisory_budget_posture": "one unit",
        "recursion_depth": 0,
        "specialist_parent_ref": None,
        "capability_request": deepcopy(dict(capability_request)),
    }


def _completed_exact_handoff(payload: Mapping[str, Any]) -> bool:
    handoff = dict(payload.get("specialist_need_handoff") or {})
    result = dict(handoff.get("result") or {})
    bounded = dict(result.get("bounded_result") or {})
    alignment = dict(bounded.get("claim_alignment") or {})
    return (
        result.get("execution_posture") == EXECUTION_COMPLETED
        and alignment.get("posture") == "exact_match"
    )


def _quantitative_dprime_response(payload: Mapping[str, Any]) -> str:
    exact = _completed_exact_handoff(payload)
    return json.dumps(
        {
            "validation_status": "supported" if exact else "unsupported",
            "reasons": [
                (
                    "The exact calculator result and claim alignment support the "
                    "unchanged nominated claim."
                    if exact
                    else "No completed exact-alignment calculator handoff supports "
                    "the nominated derived claim."
                )
            ],
            "caveats": [],
            "nonclaims": [],
            "blockers": [] if exact else ["derived claim lacks exact calculator support"],
        }
    )


def _contract_driven_quantitative_proposal(
    *,
    role_packet: Mapping[str, Any],
    target_key: str,
    posture: str,
    calculation_kind: str,
    operand_specs: list[tuple[str, str, str, str]],
    proposed_result_literal: str,
    expected_result_unit: str,
) -> dict[str, Any]:
    """Act like a fake role that knows only its production packet contract."""

    contract = dict(
        role_packet.get("quantitative_specialist_proposal_contract") or {}
    )
    contract = validate_quantitative_specialist_proposal_contract(contract)
    proposal_schema = dict(contract.get("proposal_schema") or {})
    request_schema = dict(contract.get("capability_request_schema") or {})
    operand_schema = dict(request_schema.get("operand_schema") or {})
    claim_schema = dict(request_schema.get("claim_binding_schema") or {})
    fixed_proposal = dict(proposal_schema.get("fixed_fields") or {})
    fixed_request = dict(request_schema.get("fixed_fields") or {})
    allowed_proposal = set(proposal_schema.get("allowed_fields") or ())
    allowed_request = set(request_schema.get("allowed_fields") or ())
    allowed_operand = set(operand_schema.get("allowed_fields") or ())
    allowed_claim = set(claim_schema.get("allowed_fields") or ())
    allowed_sources = set(contract.get("allowed_source_local_keys") or ())
    assert calculation_kind in set(request_schema.get("supported_operators") or ())
    assert all(source in allowed_sources for _, _, _, source in operand_specs)
    assert {
        "local_operand_key",
        "source_local_key",
        "source_numeric_literal",
        "operand_role",
    } <= allowed_operand
    assert {
        "proposed_result_literal",
        "literal_occurrence",
        "expected_result_unit",
    } == allowed_claim

    target_contract = dict(contract.get("target_contract") or {})
    if target_contract.get("target_kind") == "component":
        selected_target = str(target_contract["target_key"])
        source_material = {
            "component_evidence": str(
                dict(role_packet.get("component_evidence") or {}).get(
                    "bounded_text"
                )
                or ""
            )
        }
    else:
        assert target_contract.get("target_key_rule")
        selected_target = target_key
        source_material = {
            str(alias): str(
                dict(dict(node).get("direct_claim_ref") or {}).get(
                    "claim_text"
                )
                or ""
            )
            for alias, node in zip(
                contract.get("allowed_source_local_keys") or (),
                role_packet.get("component_nodes") or (),
                strict=True,
            )
        }
    assert all(
        literal in source_material[source]
        for _key, literal, _role, source in operand_specs
    )
    request: dict[str, Any] = {
        **fixed_request,
        "calculation_kind": calculation_kind,
        "operands": [
            {
                "local_operand_key": key,
                "source_local_key": source,
                "source_numeric_literal": literal,
                "operand_role": role,
            }
            for key, literal, role, source in operand_specs
        ],
        "claim_binding": {
            "proposed_result_literal": proposed_result_literal,
            "literal_occurrence": None,
            "expected_result_unit": expected_result_unit,
        },
    }
    optional_request_values = {
        "formula_label": f"bounded {calculation_kind}",
        "expected_output_unit": expected_result_unit,
        "expected_precision_posture": "exact_as_reported",
        "assumptions": [],
        "caveats": [],
    }
    request.update(
        {
            key: value
            for key, value in optional_request_values.items()
            if key in allowed_request
        }
    )
    proposal: dict[str, Any] = {
        **fixed_proposal,
        "local_need_id": "quantitative-need-one",
        "bounded_question": "Calculate the nominated exact source literals.",
        "target": {
            "target_kind": target_contract["target_kind"],
            "target_key": selected_target,
        },
        "posture": posture,
        "capability_request": request,
    }
    optional_proposal_values = {
        "input_artifact_refs": [],
        "assumptions": [],
        "caveats": [],
        "nonclaims": ["The calculator does not admit the nominated claim."],
        "advisory_budget_posture": "one unit",
    }
    proposal.update(
        {
            key: value
            for key, value in optional_proposal_values.items()
            if key in allowed_proposal
        }
    )
    assert set(proposal) <= allowed_proposal
    assert set(request) <= allowed_request
    return proposal


class QuantitativeComponentNorthstarHarness(SpecialistNorthstarHarness):
    proposal_origin = "component"
    component_posture = "optional"
    also_synthesis_proposal = False
    later_synthesis_posture = "optional"

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.component_inputs: list[dict[str, Any]] = []
        self.cross_inputs: list[dict[str, Any]] = []
        self._active_role_packet: dict[str, Any] = {}
        self.raw_author_response = (
            "Northstar quantitative result\n\n"
            "The supported derived combined amount is 1500 USD. The remaining "
            "Northstar filing facts and route synthesis are unchanged."
        )

    def _component_claim(self, question: str) -> str:
        if "base rebate" in question:
            return "The supported derived combined Northstar amount is 1500 USD."
        if "income" in question:
            return "The income bonus threshold is 60000 USD."
        return NorthstarHarness._component_claim(question)

    def build_search_passages(self) -> list[dict[str, Any]]:
        passages = super().build_search_passages()
        for passage in passages:
            passage["conflict_posture"] = "none"
        base = next(item for item in passages if item["source_id"] == 101)
        base["title"] = "Northstar exact quantitative inputs"
        base["text"] = (
            "The Northstar record reports a base amount of 1200 USD and a "
            "supplemental amount of 300 USD."
        )
        income = next(item for item in passages if item["source_id"] == 103)
        income["title"] = "Northstar income bonus threshold 60000 USD"
        income["text"] = "The Northstar income bonus threshold is 60000 USD."
        return passages

    def _proposal(
        self,
        *,
        target_kind: str,
        target_key: str,
        hint: str,
        posture: str,
        requirement: str,
    ) -> dict[str, Any]:
        del hint, posture, requirement, target_kind
        evidence_text = str(
            dict(self._active_role_packet.get("component_evidence") or {}).get(
                "bounded_text"
            )
            or ""
        )
        literals = re.findall(r"\b\d+(?:\.\d+)? USD\b", evidence_text)
        assert literals[:2] == ["1200 USD", "300 USD"]
        proposed = f"{sum(Decimal(item.split()[0]) for item in literals[:2]):f} USD"
        return _contract_driven_quantitative_proposal(
            role_packet=self._active_role_packet,
            target_key=target_key,
            posture=self.component_posture,
            calculation_kind="sum",
            operand_specs=[
                ("base", literals[0], "term", "component_evidence"),
                ("supplement", literals[1], "term", "component_evidence"),
            ],
            proposed_result_literal=proposed,
            expected_result_unit="USD",
        )

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        if system_prompt in ROLE_SYSTEM_PROMPTS.values():
            self._active_role_packet = json.loads(prompt)
        if system_prompt == ROLE_SYSTEM_PROMPTS["component_analyst"]:
            self.component_inputs.append(deepcopy(self._active_role_packet))
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            self.cross_inputs.append(json.loads(prompt))
        raw = super().ask_model(prompt, system_prompt, **kwargs)
        if (
            system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]
            and self.also_synthesis_proposal
        ):
            output = json.loads(raw)
            output["specialist_need_proposal"] = _product_proposal(
                target_kind="synthesis",
                target_key="S",
                posture=self.later_synthesis_posture,
                capability_request=_request(
                    operands=[
                        _operand(
                            "derived_base",
                            "1500 USD",
                            "term",
                            source="component_01",
                        ),
                        _operand(
                            "income_threshold",
                            "60000 USD",
                            "term",
                            source="component_03",
                        ),
                    ],
                    result_literal="61500 USD",
                    result_unit="USD",
                    expected_output_unit="USD",
                ),
            )
            return json.dumps(output)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_COMPONENT_DPRIME]:
            payload = json.loads(prompt)
            nominated_claim = str(
                dict(payload.get("nominated_claim") or {}).get("claim_text") or ""
            )
            if payload.get("specialist_need_handoff") and "derived combined" in nominated_claim:
                return _quantitative_dprime_response(payload)
        return raw


class QuantitativeSynthesisNorthstarHarness(SpecialistNorthstarHarness):
    proposal_origin = "synthesis"
    synthesis_target_key = "E"

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self._source_aliases: dict[str, str] = {}
        self.cross_inputs: list[dict[str, Any]] = []
        self._active_role_packet: dict[str, Any] = {}
        self.raw_author_response = (
            "Northstar quantitative synthesis\n\n"
            "The supported difference between the 60000 USD threshold and the "
            "1200 USD base amount is 58800 USD. The filing-route synthesis remains "
            "subject to the admitted paper and online rules."
        )

    def _component_claim(self, question: str) -> str:
        if "base rebate" in question:
            return "The Northstar base rebate is 1200 USD."
        if "income" in question:
            return "The income bonus threshold is 60000 USD."
        return NorthstarHarness._component_claim(question)

    @staticmethod
    def _component_ids(payload: dict[str, Any]) -> dict[str, str]:
        found: dict[str, str] = {}
        for node in payload.get("component_nodes", []):
            question = str(node.get("component_question") or "").casefold()
            component_id = str(node["component_id"])
            if "base rebate" in question:
                found["base"] = component_id
            if "income" in question:
                found["income"] = component_id
            if "paper" in question:
                found["paper"] = component_id
            if "online" in question:
                found["online"] = component_id
        assert set(found) == {"base", "income", "paper", "online"}
        return found

    def build_search_passages(self) -> list[dict[str, Any]]:
        passages = super().build_search_passages()
        for passage in passages:
            passage["conflict_posture"] = "none"
            if passage["source_id"] == 101:
                passage["title"] = "Northstar base rebate amount 1200 USD"
                passage["text"] = "The Northstar base rebate amount is 1200 USD."
            if passage["source_id"] == 103:
                passage["title"] = "Northstar income bonus threshold 60000 USD"
                passage["text"] = "The Northstar income bonus threshold is 60000 USD."
        return passages

    def _proposal(
        self,
        *,
        target_kind: str,
        target_key: str,
        hint: str,
        posture: str,
        requirement: str,
    ) -> dict[str, Any]:
        del hint, posture, requirement, target_kind
        return _contract_driven_quantitative_proposal(
            role_packet=self._active_role_packet,
            target_key=target_key,
            posture="optional",
            calculation_kind="difference",
            operand_specs=[
                (
                    "threshold",
                    "60000 USD",
                    "minuend",
                    self._source_aliases["income"],
                ),
                (
                    "base",
                    "1200 USD",
                    "subtrahend",
                    self._source_aliases["base"],
                ),
            ],
            proposed_result_literal="58800 USD",
            expected_result_unit="USD",
        )

    def ask_model(self, prompt: str, system_prompt: str, **kwargs: Any) -> str:
        payload = json.loads(prompt) if system_prompt in ROLE_SYSTEM_PROMPTS.values() else {}
        if payload:
            self._active_role_packet = deepcopy(payload)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            self.cross_inputs.append(deepcopy(payload))
            catalog = dict(payload.get("quantitative_source_catalog") or {})
            aliases = list(
                dict(
                    payload.get("quantitative_specialist_proposal_contract")
                    or {}
                ).get("allowed_source_local_keys")
                or ()
            )
            for alias, node in zip(
                aliases, payload.get("component_nodes") or (), strict=True
            ):
                assert alias in catalog
                claim = str(
                    dict(dict(node).get("direct_claim_ref") or {}).get(
                        "claim_text"
                    )
                    or ""
                )
                if "1200 USD" in claim:
                    self._source_aliases["base"] = str(alias)
                if "60000 USD" in claim:
                    self._source_aliases["income"] = str(alias)
            assert set(self._source_aliases) == {"base", "income"}
        raw = super().ask_model(prompt, system_prompt, **kwargs)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_CROSS_COMPONENT_ANALYST]:
            output = json.loads(raw)
            component_ids = self._component_ids(payload)
            output["synthesis_proposals"] = [
                {
                    "synthesis_key": "E",
                    "claim_text": (
                        "The difference between the 60000 USD threshold and the "
                        "1200 USD base amount is 58800 USD."
                    ),
                    "relationship_type": "source_bound_numeric_difference",
                    "component_inputs": [
                        component_ids["base"],
                        component_ids["income"],
                    ],
                    "synthesis_inputs": [],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                },
                {
                    "synthesis_key": "S",
                    "claim_text": (
                        "The admitted quantitative difference is 58800 USD; bonus "
                        "claimants still use paper and non-claimants may file online."
                    ),
                    "relationship_type": "quantitative_and_filing_route",
                    "component_inputs": [
                        component_ids["paper"],
                        component_ids["online"],
                    ],
                    "synthesis_inputs": ["E"],
                    "caveats": [],
                    "nonclaims": [],
                    "blockers": [],
                },
            ]
            return json.dumps(output)
        if system_prompt == ROLE_SYSTEM_PROMPTS[ROLE_SYNTHESIS_DPRIME] and payload.get(
            "specialist_need_handoff"
        ):
            return _quantitative_dprime_response(payload)
        return raw


def _execute_product_run(
    *,
    harness: NorthstarHarness,
    monkeypatch: pytest.MonkeyPatch,
    run_id: str,
    activate_product: bool = True,
) -> tuple[Any, Any, dict[str, Any], RunDeps]:
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(
            HANDOFF_SEMANTIC,
            HANDOFF_SUFFICIENCY,
            HANDOFF_PACKET,
            HANDOFF_AUTHOR,
        ),
    )
    setattr(harness, "_quantitative_test_capture", captured)
    base_deps = harness.deps()
    deps = (
        compose_quantitative_specialist_product_deps(base_deps)
        if activate_product
        else base_deps
    )
    outcome = orchestrator.run_pipeline(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-13",
            session_id=f"session:{run_id}",
            run_id=run_id,
        ),
        deps,
        NullStatusWriter(),
        CostAccumulator(),
    )
    return outcome, captured["semantic_run_kernel"], captured, deps


def _forbid_legacy_reducer(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("ordinary quantitative product path called legacy reducer")


def test_component_origin_product_path_and_paired_final_answer_delta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        legacy_calculation,
        "reduce_specialist_source_bound_calculation",
        _forbid_legacy_reducer,
    )
    with monkeypatch.context() as positive_patch:
        positive_harness = QuantitativeComponentNorthstarHarness(tmp_path / "positive")
        positive, positive_kernel, _captured, deps = _execute_product_run(
            harness=positive_harness,
            monkeypatch=positive_patch,
            run_id="quantitative-component-positive",
        )
    positive_plane = positive_kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    positive_result = positive_plane["result_artifacts"][0]
    positive_scheduler = positive_kernel.state.projections[
        MULTICOMPONENT_SCHEDULER_STAGE
    ]
    assert deps.specialist_capability_registry is not None
    assert deps.specialist_execution_policy is not None
    assert positive_result["capability_id"] == QUANTITATIVE_CAPABILITY_ID
    assert positive_result["execution_posture"] == EXECUTION_COMPLETED, json.dumps(
        positive_result, sort_keys=True
    )
    assert "1500 USD" in positive.report
    assert positive_result["bounded_result"]["numeric_value_text"] == "1500"
    assert positive_result["bounded_result"]["claim_alignment"]["posture"] == (
        "exact_match"
    )
    assert positive_result["validator_consumption"] == "consumed_by_component_dprime"
    dprime_packet = positive_harness.specialist_dprime_inputs[0]
    assert "quantitative_specialist_proposal_contract" not in json.dumps(
        dprime_packet
    )
    assert dprime_packet["nominated_claim"]["claim_text"] == (
        "The supported derived combined Northstar amount is 1500 USD."
    )
    component_role_packet = next(
        packet
        for packet in positive_harness.component_inputs
        if "base rebate"
        in str(
            dict(packet.get("component_ref") or {}).get(
                "user_facing_question"
            )
            or ""
        ).casefold()
    )
    assert validate_quantitative_specialist_proposal_contract(
        component_role_packet["quantitative_specialist_proposal_contract"]
    )
    assert component_role_packet["quantitative_source_catalog"][
        "component_evidence"
    ]["source_quality_posture"] == "authoritative_current_clear"
    assert "_request" not in _contract_driven_quantitative_proposal.__code__.co_names
    assert (
        "_product_proposal"
        not in _contract_driven_quantitative_proposal.__code__.co_names
    )
    assert positive_scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION
    assert positive_scheduler["specialist_compatibility_pool"]["specialist_spent"] == 1
    assert positive_scheduler["specialist_compatibility_pool"]["specialist_remaining"] == 0
    assert positive_scheduler["compatibility_envelope"]["total_units"] == 22
    assert positive_plane["provider_request_attempt_count"] == 0
    assert positive_plane["model_call_count"] == 0
    assert positive_plane["token_usage"] == positive_plane["model_cost"] == 0
    specialist_actions = [
        action.to_dict()
        for action in positive_kernel.state.issued_actions.values()
        if "specialist" in action.action_type.value
    ]
    retained_specialist_state = json.dumps(
        {
            "work_nodes": positive_plane["work_nodes"],
            "result_artifacts": positive_plane["result_artifacts"],
            "proposal_dispositions": positive_plane["proposal_dispositions"],
            "need_handoffs": positive_plane["need_handoffs"],
            "specialist_leases": [
                item
                for item in positive_scheduler["lease_history"]
                if dict(item.get("work") or {}).get("work_kind")
                == WORK_KIND_SPECIALIST_CAPABILITY
            ],
            "specialist_actions": specialist_actions,
        },
        sort_keys=True,
    )
    for forbidden in (
        "The Northstar record reports a base amount",
        "The supported derived combined Northstar amount",
        "quantitative_source_catalog",
        "quantitative_specialist_proposal_contract",
        QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION,
        "capability_request",
        "source_numeric_literal",
        "provider_name",
        "normalized_source_identity",
    ):
        assert forbidden not in retained_specialist_state
    retained_product_projections = json.dumps(
        {
            "specialist": positive_plane,
            "scheduler": positive_scheduler,
            "graph": positive_kernel.state.projections.get(
                "multicomponent_component_work_graph_v1"
            ),
            "actions": specialist_actions,
        },
        sort_keys=True,
    )
    assert "quantitative_specialist_proposal_contract" not in (
        retained_product_projections
    )
    assert QUANTITATIVE_PROPOSAL_CONTRACT_SCHEMA_VERSION not in (
        retained_product_projections
    )

    def unavailable_adapter(_transient: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "bounded_result": {"calculation_status": "blocked"},
            "execution_posture": EXECUTION_BLOCKED,
            "blockers": ["negative control has no valid calculator result"],
        }

    with monkeypatch.context() as negative_patch:
        negative_patch.setattr(
            quantitative_product,
            "source_bound_quantitative_calculation_adapter",
            unavailable_adapter,
        )
        negative_harness = QuantitativeComponentNorthstarHarness(tmp_path / "negative")
        negative, negative_kernel, _captured, _deps = _execute_product_run(
            harness=negative_harness,
            monkeypatch=negative_patch,
            run_id="quantitative-component-negative",
        )
    negative_plane = negative_kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    negative_result = negative_plane["result_artifacts"][0]
    assert negative_plane["proposals"][0]["capability_request"] == (
        positive_plane["proposals"][0]["capability_request"]
    )
    assert negative_result["execution_posture"] == EXECUTION_BLOCKED
    assert negative_result["validator_consumption"] == "rejected_by_validator"
    assert "supported derived combined amount is 1500 USD" not in negative.report
    assert negative_harness.author_prompts == []


def test_synthesis_origin_uses_same_product_capability_and_two_hop_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        legacy_calculation,
        "reduce_specialist_source_bound_calculation",
        _forbid_legacy_reducer,
    )
    harness = QuantitativeSynthesisNorthstarHarness(tmp_path)
    outcome, kernel, _captured, _deps = _execute_product_run(
        harness=harness,
        monkeypatch=monkeypatch,
        run_id="quantitative-synthesis-positive",
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert plane["result_artifacts"], json.dumps(plane, sort_keys=True)
    result = plane["result_artifacts"][0]
    assert "58800 USD" in outcome.report
    assert result["capability_id"] == QUANTITATIVE_CAPABILITY_ID
    assert result["execution_posture"] == EXECUTION_COMPLETED, json.dumps(
        result, sort_keys=True
    )
    assert result["bounded_result"]["numeric_value_text"] == "58800"
    assert result["bounded_result"]["claim_alignment"]["posture"] == "exact_match"
    assert result["validator_consumption"] == "consumed_by_synthesis_dprime"
    assert all(
        ref["underlying_evidence_match_posture"]
        == "exact_literal_found_in_underlying_evidence"
        for ref in result["bounded_result"]["literal_binding_refs"]
    )
    assert harness.specialist_dprime_inputs[0]["nominated_synthesis"][
        "synthesis_key"
    ] == "E"
    assert "quantitative_specialist_proposal_contract" not in json.dumps(
        harness.specialist_dprime_inputs[0]
    )
    cross_role_packet = harness.cross_inputs[0]
    assert validate_quantitative_specialist_proposal_contract(
        cross_role_packet["quantitative_specialist_proposal_contract"]
    )
    assert "source_material" not in json.dumps(
        cross_role_packet["quantitative_source_catalog"]
    )
    assert set(harness._source_aliases.values()) <= set(
        cross_role_packet["quantitative_specialist_proposal_contract"][
            "allowed_source_local_keys"
        ]
    )
    scheduler_source = (ROOT / "core" / "multicomponent_graph_scheduling.py").read_text(
        encoding="utf-8"
    )
    driver_source = (
        ROOT / "core" / "ordinary_multicomponent_synthesis_runtime.py"
    ).read_text(encoding="utf-8")
    assert QUANTITATIVE_CAPABILITY_ID not in scheduler_source + driver_source


def test_product_enabled_no_need_preserves_answer_and_closed_path_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as product_patch:
        product_harness = NorthstarHarness(tmp_path / "product")
        product, product_kernel, _captured, _deps = _execute_product_run(
            harness=product_harness,
            monkeypatch=product_patch,
            run_id="quantitative-no-need-product",
        )
    with monkeypatch.context() as closed_patch:
        closed_harness = NorthstarHarness(tmp_path / "closed")
        closed, closed_kernel, _captured, _deps = _execute_product_run(
            harness=closed_harness,
            monkeypatch=closed_patch,
            run_id="quantitative-no-need-closed",
            activate_product=False,
        )
    assert product.report == closed.report == NORTHSTAR_REPORT
    product_scheduler = product_kernel.state.projections[
        MULTICOMPONENT_SCHEDULER_STAGE
    ]
    closed_scheduler = closed_kernel.state.projections[
        MULTICOMPONENT_SCHEDULER_STAGE
    ]
    assert product_scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V3_SCHEMA_VERSION
    assert closed_scheduler["schema_version"] == MULTICOMPONENT_SCHEDULER_V2_SCHEMA_VERSION
    product_plane = product_kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    assert product_plane["proposal_count"] == product_plane["result_artifact_count"] == 0
    assert SPECIALIST_WORK_PLANE_STAGE not in closed_kernel.state.projections


@pytest.mark.parametrize(
    ("component_count", "query"),
    ((1, ONE_COMPONENT_QUERY), (6, SIX_COMPONENT_QUERY)),
)
def test_product_composition_preserves_nonqualifying_and_single_component_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component_count: int,
    query: str,
) -> None:
    with monkeypatch.context() as product_patch:
        product_harness = _TimingHarness(
            tmp_path / "product",
            query=query,
            component_count=component_count,
        )
        product, product_kernel, _captured, _deps = _execute_product_run(
            harness=product_harness,
            monkeypatch=product_patch,
            run_id=f"quantitative-nonqual-product-{component_count}",
        )
    with monkeypatch.context() as closed_patch:
        closed_harness = _TimingHarness(
            tmp_path / "closed",
            query=query,
            component_count=component_count,
        )
        closed, closed_kernel, _captured, _deps = _execute_product_run(
            harness=closed_harness,
            monkeypatch=closed_patch,
            run_id=f"quantitative-nonqual-closed-{component_count}",
            activate_product=False,
        )
    assert product.report == closed.report
    assert MULTICOMPONENT_SCHEDULER_STAGE not in product_kernel.state.projections
    assert MULTICOMPONENT_SCHEDULER_STAGE not in closed_kernel.state.projections
    assert SPECIALIST_WORK_PLANE_STAGE not in product_kernel.state.projections
    assert SPECIALIST_WORK_PLANE_STAGE not in closed_kernel.state.projections


def test_product_one_unit_component_priority_and_optional_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = QuantitativeComponentNorthstarHarness(tmp_path)
    harness.also_synthesis_proposal = True
    outcome, kernel, _captured, _deps = _execute_product_run(
        harness=harness,
        monkeypatch=monkeypatch,
        run_id="quantitative-component-priority",
    )
    assert outcome.report == harness.raw_author_response
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    availability = [
        item["execution_availability_posture"]
        for item in plane["proposal_dispositions"]
    ]
    specialist_leases = [
        item
        for item in scheduler["lease_history"]
        if dict(item.get("work") or {}).get("work_kind")
        == WORK_KIND_SPECIALIST_CAPABILITY
    ]
    assert availability[0] == AVAILABILITY_RESULT
    assert availability[1:] == [AVAILABILITY_BUDGET]
    assert len(specialist_leases) == 1
    assert scheduler["specialist_compatibility_pool"]["specialist_spent"] == 1
    assert [item["validator_consumption"] for item in plane["need_handoffs"]] == [
        "consumed_by_component_dprime",
        "consumed_by_synthesis_dprime",
    ]
    assert any(
        packet["specialist_need_handoff"]["availability_posture"]
        == AVAILABILITY_BUDGET
        for packet in harness.specialist_dprime_inputs
    )


def test_later_required_synthesis_need_blocks_after_component_consumes_unit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = QuantitativeComponentNorthstarHarness(tmp_path)
    harness.also_synthesis_proposal = True
    harness.later_synthesis_posture = "required"
    outcome, kernel, _captured, _deps = _execute_product_run(
        harness=harness,
        monkeypatch=monkeypatch,
        run_id="quantitative-required-synthesis-exhaustion",
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    assert outcome.report != harness.raw_author_response
    assert scheduler["status"] == "blocked_exhausted"
    assert [
        item["execution_availability_posture"]
        for item in plane["proposal_dispositions"]
    ] == [AVAILABILITY_RESULT, AVAILABILITY_BUDGET]
    assert plane["need_handoffs"][1]["validator_consumption"] == (
        "pending_validator_consumption"
    )
    assert not any(
        packet.get("specialist_need_handoff", {}).get("availability_posture")
        == AVAILABILITY_BUDGET
        for packet in harness.specialist_dprime_inputs
    )


def test_required_noncomputed_product_result_blocks_before_component_dprime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def blocked_adapter(_transient: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "bounded_result": {"calculation_status": "blocked"},
            "execution_posture": EXECUTION_BLOCKED,
            "blockers": ["required deterministic result unavailable"],
        }

    monkeypatch.setattr(
        quantitative_product,
        "source_bound_quantitative_calculation_adapter",
        blocked_adapter,
    )
    harness = QuantitativeComponentNorthstarHarness(tmp_path)
    harness.component_posture = "required"
    outcome, kernel, _captured, _deps = _execute_product_run(
        harness=harness,
        monkeypatch=monkeypatch,
        run_id="quantitative-required-noncomputed",
    )
    plane = kernel.state.projections[SPECIALIST_WORK_PLANE_STAGE]
    scheduler = kernel.state.projections[MULTICOMPONENT_SCHEDULER_STAGE]
    assert outcome.report != harness.raw_author_response
    assert scheduler["status"] == "blocked_required_specialist_work"
    assert plane["result_artifacts"][0]["execution_posture"] == EXECUTION_BLOCKED
    assert plane["result_artifacts"][0]["validator_consumption"] == (
        "pending_validator_consumption"
    )
    assert not any(
        packet.get("specialist_need_handoff")
        for packet in harness.all_dprime_inputs
    )
