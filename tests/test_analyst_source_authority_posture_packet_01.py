"""INTEGRATION-STAGING: Analyst source-authority posture packet contract.

Harness label: INTEGRATION-STAGING
Ordinary product path guarded or fed: future query-to-relation planning and
D-prime relation intake source-authority requirements; no current product path
is wired in this phase.
Runtime consumer: future GENERIC-QUERY-TO-RELATION-PLANNING-01 and later
Analyst/D-prime relation-intake consumers.
Why ordinary product-path work cannot be done directly: this phase explicitly
closes query planning, source-class adapters, social/review aggregation, model
calls, live calls, Scrutineer, FAP, and Author wiring.
Integration deadline: GENERIC-QUERY-TO-RELATION-PLANNING-01.
Exit condition: a later planning/intake phase consumes this Analyst-owned
contract or deliberately updates/retires it.
Why this is not a shadow product path: the tests validate a passive contract and
examples only; they do not create a planner, source-ranking lane, D-prime
review path, answer path, CLI flag, or live dogfood route.
Forbidden interpretation: this is not product correctness, citation rendering,
source-obligation satisfaction, social/review consensus, authority scoring,
domain allowlisting, live validation, or arbitrary query support.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

import core.source_authority_posture_packet as sap
from core.mvp_supported_query_class_boundary import (
    MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF,
    build_mvp_supported_query_class_boundary_profile,
    build_mvp_supported_query_class_boundary_status,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "source_authority_posture_packet.py"
BOUNDARY_PATH = ROOT / "core" / "mvp_supported_query_class_boundary.py"


def test_source_authority_posture_profile_validates() -> None:
    profile = sap.validate_source_authority_posture_profile(
        sap.build_source_authority_posture_profile()
    )

    assert profile["schema_version"] == sap.SOURCE_AUTHORITY_POSTURE_SCHEMA_VERSION
    assert profile["phase"] == sap.SOURCE_AUTHORITY_POSTURE_PHASE
    assert profile["owner"] == sap.SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST
    assert profile["source_authority_is_analyst_owned"] is True
    assert profile["source_authority_is_not_domain_allowlist"] is True
    assert profile["source_authority_is_not_source_ranking"] is True
    assert profile["source_authority_is_not_numeric_scoring"] is True
    assert profile["planner_must_not_invent_source_authority_policy"] is True
    assert "official_or_source_of_record" in profile["source_class_labels"]
    assert "user_review" in profile["source_class_labels"]
    assert set(sap.SOURCE_AUTHORITY_RECOMMENDED_USES).issubset(
        profile["recommended_source_use_definitions"]
    )


def test_packet_owner_is_analyst_and_required_fields_are_declared() -> None:
    packet = sap.build_official_source_of_record_example_posture_packet()
    profile = sap.build_source_authority_posture_profile()

    assert packet["owner"] == sap.SOURCE_AUTHORITY_POSTURE_OWNER_ANALYST
    assert packet["source_authority_posture_id"]
    assert packet["source_authority_posture_digest"]
    assert set(sap.SOURCE_AUTHORITY_REQUIRED_PACKET_FIELDS).issubset(packet)
    assert set(sap.SOURCE_AUTHORITY_REQUIRED_PACKET_FIELDS).issubset(
        profile["required_packet_fields"]
    )
    for required in (
        "source_class",
        "issuer_or_source_owner",
        "document_type",
        "primary_derivative_posture",
        "directness_to_answer_component",
        "recency_currentness",
        "scope_match",
        "claim_specificity",
        "conflict_qualification_posture",
        "recommended_source_use",
        "limitations",
        "required_caveats",
    ):
        assert required in packet


def test_official_source_of_record_example_validates_without_specific_architecture() -> None:
    packet = sap.validate_source_authority_posture_packet(
        sap.build_official_source_of_record_example_posture_packet()
    )
    serialized = json.dumps(packet, sort_keys=True).casefold()
    module_text = MODULE_PATH.read_text(encoding="utf-8").casefold()

    assert packet["source_class"] == "official_or_source_of_record"
    assert packet["issuer_or_source_owner"] == "Example County Clerk"
    assert packet["document_type"] == "official fee schedule"
    assert packet["primary_derivative_posture"] == "primary"
    assert packet["directness_to_answer_component"] == "direct"
    assert packet["scope_match"] == "exact"
    assert packet["claim_specificity"] == "exact claim present"
    assert packet["source_contains_exact_claim"] is True
    assert packet["recommended_source_use"] == sap.SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY
    assert "product correctness remains unclaimed" in serialized
    assert "passport" not in module_text


def test_authority_requires_full_posture_not_source_class_alone() -> None:
    packet = sap.build_official_source_of_record_example_posture_packet()

    source_class_only = copy.deepcopy(packet)
    source_class_only["recommended_source_use_supporting_fields"] = ["source_class"]
    source_class_only.pop("source_authority_posture_digest")
    with pytest.raises(sap.SourceAuthorityPosturePacketError):
        sap.validate_source_authority_posture_packet(source_class_only)

    missing_exact_claim = copy.deepcopy(packet)
    missing_exact_claim["source_contains_exact_claim"] = False
    missing_exact_claim.pop("source_authority_posture_digest")
    with pytest.raises(sap.SourceAuthorityPosturePacketError):
        sap.validate_source_authority_posture_packet(missing_exact_claim)

    missing_owner = copy.deepcopy(packet)
    missing_owner["issuer_or_source_owner"] = ""
    missing_owner.pop("source_authority_posture_digest")
    with pytest.raises(sap.SourceAuthorityPosturePacketError):
        sap.validate_source_authority_posture_packet(missing_owner)


def test_recommended_source_use_supporting_fields_rejects_unknown_names() -> None:
    packet = sap.build_official_source_of_record_example_posture_packet()

    assert "source_class" in sap.SOURCE_AUTHORITY_RECOMMENDED_USE_SUPPORTING_FIELD_VALUES
    assert "source_ref" in sap.SOURCE_AUTHORITY_RECOMMENDED_USE_SUPPORTING_FIELD_VALUES
    assert (
        "evidence_content_ref"
        in sap.SOURCE_AUTHORITY_RECOMMENDED_USE_SUPPORTING_FIELD_VALUES
    )

    packet["recommended_source_use_supporting_fields"] = [
        "source_class",
        "fake_field",
        "made_up_field",
    ]
    packet.pop("source_authority_posture_digest")
    with pytest.raises(sap.SourceAuthorityPosturePacketError):
        sap.validate_source_authority_posture_packet(packet)


def test_social_forum_review_validates_as_directionality_or_ignore_not_authority() -> None:
    packet = sap.validate_source_authority_posture_packet(
        sap.build_social_review_directionality_example_posture_packet()
    )

    assert packet["source_class"] == "social_or_forum_discussion"
    assert packet["recommended_source_use"] == (
        sap.SOURCE_AUTHORITY_RECOMMENDED_USE_DIRECTIONALITY
    )
    assert packet["source_contains_exact_claim"] is False
    assert packet["anti_laundering_flags"] == sap.SOURCE_AUTHORITY_ANTI_LAUNDERING_FLAGS

    ignored = copy.deepcopy(packet)
    ignored["recommended_source_use"] = sap.SOURCE_AUTHORITY_RECOMMENDED_USE_IGNORE
    ignored["recommended_source_use_rationale"] = (
        "Analyst posture recommends ignore because the single social item is not "
        "usable for the answer component."
    )
    ignored.pop("source_authority_posture_digest")
    assert (
        sap.validate_source_authority_posture_packet(ignored)["recommended_source_use"]
        == sap.SOURCE_AUTHORITY_RECOMMENDED_USE_IGNORE
    )

    authority = copy.deepcopy(packet)
    authority["recommended_source_use"] = sap.SOURCE_AUTHORITY_RECOMMENDED_USE_AUTHORITY
    authority["source_contains_exact_claim"] = True
    authority["recommended_source_use_supporting_fields"] = list(
        sap.SOURCE_AUTHORITY_AUTHORITY_REQUIRED_SUPPORTING_FIELDS
    )
    authority.pop("source_authority_posture_digest")
    with pytest.raises(sap.SourceAuthorityPosturePacketError):
        sap.validate_source_authority_posture_packet(authority)


def test_single_social_review_item_cannot_be_laundered_into_consensus() -> None:
    packet = sap.build_social_review_directionality_example_posture_packet()
    serialized = json.dumps(packet, sort_keys=True).casefold()

    assert "single social/forum/review item is not consensus" in serialized
    assert "single social/forum/review item is not reliability evidence" in serialized
    assert "single social/forum/review item is not authority-bearing support" in serialized

    for flag in (
        "single_item_consensus_claimed",
        "single_item_reliability_evidence_claimed",
        "single_item_authority_bearing_support_claimed",
        "social_review_upgraded_to_authority",
        "social_review_upgraded_to_consensus",
    ):
        laundered = copy.deepcopy(packet)
        laundered["anti_laundering_flags"][flag] = True
        laundered.pop("source_authority_posture_digest")
        with pytest.raises(sap.SourceAuthorityPosturePacketError):
            sap.validate_source_authority_posture_packet(laundered)


def test_product_correctness_and_raw_private_retention_remain_unclaimed() -> None:
    for packet in (
        sap.build_official_source_of_record_example_posture_packet(),
        sap.build_social_review_directionality_example_posture_packet(),
    ):
        assert all(value is False for value in packet["raw_private_retention_flags"].values())
        assert packet["closed_surface_flags"]["product_correctness_claimed"] is False
        assert packet["closed_surface_flags"]["provider_call_made"] is False
        assert packet["closed_surface_flags"]["model_call_made"] is False
        assert packet["closed_surface_flags"]["fetch_read_call_made"] is False
        assert "product correctness remains unclaimed" in packet["nonclaims"]


def test_boundary_profile_has_metadata_pointer_without_enabling_posture() -> None:
    profile = build_mvp_supported_query_class_boundary_profile()
    status = build_mvp_supported_query_class_boundary_status()

    assert profile["source_authority_posture_contract_ref"] == (
        MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF
    )
    assert status["source_authority_posture_contract_ref"] == (
        MVP_SUPPORTED_QUERY_CLASS_SOURCE_AUTHORITY_POSTURE_CONTRACT_REF
    )
    assert status["source_authority_posture_supported"] is False


def test_no_query_planning_cli_live_or_model_surface_is_added() -> None:
    imported, called, function_names, string_literals = _module_static_shape(
        MODULE_PATH
    )
    boundary_imports, boundary_calls, _boundary_functions, _boundary_strings = (
        _module_static_shape(BOUNDARY_PATH)
    )

    forbidden_imports = {
        "argparse",
        "click",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "dotenv",
        "httpx",
        "openai",
        "requests",
        "subprocess",
    }
    forbidden_calls = {
        "ask_model",
        "dispatch_retrieval",
        "fetch_page",
        "fetch_url",
        "read_url",
        "retrieve",
        "run_dprime_model_review_assessment",
        "run_pipeline",
        "search_web",
    }
    forbidden_function_markers = (
        "classify_query",
        "plan_query",
        "query_to_relation",
        "source_rank",
    )

    assert imported.isdisjoint(forbidden_imports)
    assert boundary_imports.isdisjoint(forbidden_imports)
    assert called.isdisjoint(forbidden_calls)
    assert boundary_calls.isdisjoint(forbidden_calls)
    assert not any(
        marker in name for marker in forbidden_function_markers for name in function_names
    )
    assert not any(text.strip().startswith("--") for text in string_literals)
    assert "OFFICIAL_DOMAINS" not in MODULE_PATH.read_text(encoding="utf-8")
    assert "authority_score" in MODULE_PATH.read_text(encoding="utf-8")
    assert "def rank" not in MODULE_PATH.read_text(encoding="utf-8")


def _module_static_shape(
    path: Path,
) -> tuple[set[str], set[str], set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    function_names: set[str] = set()
    string_literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.FunctionDef):
            function_names.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            string_literals.add(node.value)
    return imported, called, function_names, string_literals
