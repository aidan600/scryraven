from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.run_authority_sufficiency import RunSufficiencyJudgmentInput
from core.run_authority_sufficiency_validation import build_deterministic_sufficiency_judgment
from core.sufficiency_semantic_state_consumption_runtime import (
    SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION,
    build_semantic_state_facts_for_sufficiency,
)

ROOT = Path(__file__).resolve().parents[1]

COMPONENT_ID = "component:reported-total"
COMPONENT_DIGEST = "c" * 64
CONTENT_REF_ID = "content:reported-total-value"
CONTENT_DIGEST = "d" * 64
COVERAGE_RECORD_ID = "coverage:reported-total"
COVERAGE_RECORD_DIGEST = "e" * 64
OBSERVATION_ID = "observation:reported-total"
OBSERVATION_DIGEST = "f" * 64
EVIDENCE_ID = "evidence:public-record-notice"
SOURCE_OBLIGATION_ID = "source-obligation:official-current"


def _accepted_contract() -> dict[str, Any]:
    return {
        "accepted_contract_version": "1.0",
        "accepted_contract_digest": "a" * 64,
        "accepted_answer_component_refs": [
            {
                "component_id": COMPONENT_ID,
                "component_revision": "1",
                "component_digest": COMPONENT_DIGEST,
                "requirement_posture": "required",
            }
        ],
    }


def _canonical_coverage(**overrides: Any) -> dict[str, Any]:
    coverage = {
        "owner": "RunKernel.ComponentCoverageReduction",
        "schema_version": "component_coverage_reduction_ag_sem_07_v1",
        "canonical_state": True,
        "trace_only": False,
        "storage_only": False,
        "coverage_record_id": COVERAGE_RECORD_ID,
        "coverage_record_digest": COVERAGE_RECORD_DIGEST,
        "answer_component_id": COMPONENT_ID,
        "component_revision": "1",
        "component_digest": COMPONENT_DIGEST,
        "coverage_state": "satisfied",
        "semantic_support_status": "supported",
        "source_obligation_status": "satisfied",
        "content_availability_status": "available",
        "evidence_custody_status": "custodied",
        "version_validity": "valid",
        "accepted_observation_refs": [
            {
                "observation_id": OBSERVATION_ID,
                "observation_digest": OBSERVATION_DIGEST,
                "answer_component_id": COMPONENT_ID,
                "component_revision": "1",
                "component_contract_digest": COMPONENT_DIGEST,
                "support_status": "supports",
                "support_posture": "direct",
                "content_refs": [CONTENT_REF_ID],
                "accepted": True,
            }
        ],
        "content_reference_bindings": [
            {
                "content_ref_id": CONTENT_REF_ID,
                "content_digest": CONTENT_DIGEST,
                "evidence_ref_id": EVIDENCE_ID,
                "answer_component_id": COMPONENT_ID,
                "component_revision": "1",
                "component_contract_digest": COMPONENT_DIGEST,
                "answer_bearing": True,
                "availability_status": "available",
            }
        ],
        "evidence_basis": [
            "semantic_observation",
            "answer_bearing_content",
            "evidence_ledger_custody",
        ],
        "conflict_posture": "none",
        "stale": False,
        "remaining_unknowns": [],
        "followup_need": "none",
        "evidence_ledger_binding": {
            "ledger_snapshot_id": "evidence-ledger:test",
            "ledger_schema_version": "evidence_ledger_ag91j_v1",
            "ledger_digest": "ledger-digest",
            "custody_status": "custodied",
            "source_requirement_ids": [SOURCE_OBLIGATION_ID],
            "ledger_observation_refs": [],
            "version_validity": "valid",
        },
    }
    coverage.update(overrides)
    return coverage


def _sufficiency_projection(*coverages: dict[str, Any]) -> dict[str, Any]:
    accepted = _accepted_contract()
    facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=accepted,
        component_coverage_history=list(coverages),
        contract_amendment_admission_history=[],
        evidence_ledger_projection={},
    )
    judgment = build_deterministic_sufficiency_judgment(
        RunSufficiencyJudgmentInput(
            contract_projection={},
            evidence_ledger_projection={},
            search_judgment_projection={"decision": "stop_satisfied"},
            final_evidence_facts={"final_evidence_count": 1, "author_evidence_count": 1},
            semantic_state_facts=facts,
        )
    )
    return judgment.to_projection()


def _semantic_ref_projection(*coverages: dict[str, Any]) -> dict[str, Any]:
    semantic_consumption = _sufficiency_projection(*coverages)["semantic_consumption"]
    return semantic_consumption["semantic_ref_projection"]


def test_semantic_ref_projection_carries_canonical_refs_and_digests_only() -> None:
    projection = _sufficiency_projection(_canonical_coverage())
    ref_projection = projection["semantic_consumption"]["semantic_ref_projection"]

    assert ref_projection["schema_version"] == SUFFICIENCY_SEMANTIC_REF_PROJECTION_SCHEMA_VERSION
    assert ref_projection["available"] is True
    assert ref_projection["semantic_state_facts_digest"] == projection["semantic_state_facts_summary"][
        "semantic_state_facts_digest"
    ]
    assert ref_projection["component_refs"] == [
        {"component_id": COMPONENT_ID, "component_digest": COMPONENT_DIGEST}
    ]
    assert ref_projection["coverage_record_refs"] == [
        {
            "coverage_record_id": COVERAGE_RECORD_ID,
            "coverage_record_digest": COVERAGE_RECORD_DIGEST,
            "answer_component_id": COMPONENT_ID,
        }
    ]
    assert ref_projection["semantic_observation_refs"] == [
        {"observation_id": OBSERVATION_ID, "observation_digest": OBSERVATION_DIGEST}
    ]
    assert ref_projection["sanitized_content_ref_ids"] == [CONTENT_REF_ID]
    assert ref_projection["content_ref_digests"] == [CONTENT_DIGEST]
    assert ref_projection["evidence_ids"] == [EVIDENCE_ID]
    assert ref_projection["source_obligation_refs"] == [SOURCE_OBLIGATION_ID]
    assert ref_projection["content_refs_available"] is True
    assert ref_projection["coverage_refs_available"] is True
    assert ref_projection["raw_content_included"] is False
    assert ref_projection["bounded_text_included"] is False
    assert ref_projection["prompt_visible"] is False
    assert ref_projection["author_payload_visible"] is False
    assert ref_projection["model_request_visible"] is False
    assert ref_projection["final_text_included"] is False


@pytest.mark.parametrize(
    "coverage_overrides",
    [
        {"canonical_state": False},
        {"trace_only": True},
        {"storage_only": True},
        {"coverage_state": "stale", "stale": True},
        {"coverage_state": "conflicted", "conflict_posture": "present"},
        {"semantic_support_status": "unsupported"},
        {"source_obligation_status": "unsatisfied"},
        {"content_availability_status": "missing"},
        {"evidence_custody_status": "unbound"},
        {"followup_need": "blocked"},
        {"remaining_unknowns": ["unresolved semantic support"]},
        {"evidence_basis": ["search_result_snippet"]},
        {"content_reference_bindings": []},
        {
            "accepted_observation_refs": [
                {
                    "observation_id": OBSERVATION_ID,
                    "observation_digest": OBSERVATION_DIGEST,
                    "content_refs": [CONTENT_REF_ID],
                    "accepted": False,
                }
            ]
        },
        {
            "accepted_observation_refs": [
                {
                    "observation_id": OBSERVATION_ID,
                    "observation_digest": OBSERVATION_DIGEST,
                    "content_refs": [],
                    "accepted": True,
                }
            ]
        },
        {
            "accepted_observation_refs": [
                {
                    "observation_id": OBSERVATION_ID,
                    "observation_digest": OBSERVATION_DIGEST,
                    "content_refs": ["content:missing-binding"],
                    "accepted": True,
                }
            ]
        },
    ],
)
def test_semantic_ref_projection_excludes_noncanonical_or_unsafe_coverage(
    coverage_overrides: dict[str, Any],
) -> None:
    ref_projection = _semantic_ref_projection(_canonical_coverage(**coverage_overrides))

    assert ref_projection["available"] is False
    assert ref_projection["content_refs_available"] is False
    assert ref_projection["coverage_refs_available"] is False
    assert "sanitized_content_ref_ids" not in ref_projection
    assert "content_ref_digests" not in ref_projection
    assert "coverage_record_refs" not in ref_projection


def test_semantic_ref_projection_raw_leakage_scan() -> None:
    tainted = _canonical_coverage(
        raw_content="SENTINEL_RAW_CONTENT",
        bounded_text="SENTINEL_BOUNDED_TEXT",
        prompt_text="SENTINEL_PROMPT",
        raw_prompt="SENTINEL_RAW_PROMPT",
        provider_payload={"se" + "cret": "SENTINEL_PRIVATE_MARKER"},
        raw_model_response="SENTINEL_MODEL",
        final_text="SENTINEL_FINAL",
        full_trace={"logs": "SENTINEL_LOGS"},
    )
    ref_projection = _semantic_ref_projection(tainted)
    encoded = json.dumps(ref_projection, sort_keys=True)

    forbidden_values = (
        "SENTINEL_RAW_CONTENT",
        "SENTINEL_BOUNDED_TEXT",
        "SENTINEL_PROMPT",
        "SENTINEL_RAW_PROMPT",
        "SENTINEL_PRIVATE_MARKER",
        "SENTINEL_MODEL",
        "SENTINEL_FINAL",
        "SENTINEL_LOGS",
    )
    for forbidden in forbidden_values:
        assert forbidden not in encoded

    forbidden_keys = {
        "raw_content",
        "bounded_text",
        "text",
        "prompt_text",
        "raw_prompt",
        "provider_payload",
        "raw_provider_payload",
        "model_response",
        "raw_model_response",
        "final_prose",
        "final_text",
        "db_row",
        "cache",
        "secret",
        "token",
        "full_trace",
        "logs",
    }

    def walk_keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            keys = set(value)
            for item in value.values():
                keys.update(walk_keys(item))
            return keys
        if isinstance(value, list):
            keys: set[str] = set()
            for item in value:
                keys.update(walk_keys(item))
            return keys
        return set()

    assert walk_keys(ref_projection).isdisjoint(forbidden_keys)


def test_static_guards_keep_semantic_ref_projection_out_of_closed_surfaces() -> None:
    final_answer_packet = (ROOT / "core" / "final_answer_packet.py").read_text(encoding="utf-8")
    final_answer_adapter = (ROOT / "core" / "final_answer_runtime_adapter.py").read_text(encoding="utf-8")
    author_runtime = (ROOT / "core" / "author_execution_runtime.py").read_text(encoding="utf-8")
    assert "semantic_observation_admission_history" not in final_answer_packet
    assert "component_coverage_history" not in final_answer_packet
    assert "semantic_observation_admission_history" not in final_answer_adapter
    assert "component_coverage_history" not in final_answer_adapter
    assert "semantic_ref_projection" not in author_runtime

    for path in (
        ROOT / "core" / "retrieval.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "search_providers.py",
    ):
        assert "semantic_ref_projection" not in path.read_text(encoding="utf-8")
