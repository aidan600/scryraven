"""AG-SEM-12A FinalAnswerPacket semantic authority projection tests."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from core.final_answer_packet import (
    FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_REF_SCHEMA_VERSION,
    FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION,
    FinalAnswerPacket,
    _safe_json,
)
from core.final_answer_runtime_adapter import build_final_answer_packet, derive_author_input_payload
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgment,
    SufficiencyPosture,
)

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "core" / "final_answer_runtime_adapter.py"
PACKET = ROOT / "core" / "final_answer_packet.py"
AUTHOR_RUNTIME = ROOT / "core" / "author_execution_runtime.py"

SEMANTIC_DIGEST = "a" * 64
SEMANTIC_SCHEMA = "sufficiency_semantic_state_consumption_ag_sem_09_v1"


def _passage(**overrides):
    data = {
        "source_id": 1,
        "url": "https://irs.gov/pub/notice",
        "title": "IRS notice",
        "text": "Official text about a current rule.",
        "source_tier": "official",
        "source_class": "official_current_rules",
    }
    data.update(overrides)
    return data


def _semantic_consumption(**overrides) -> dict:
    payload = {
        "schema_version": SEMANTIC_SCHEMA,
        "semantic_state_facts_digest": SEMANTIC_DIGEST,
        "blocker_count": 0,
        "blocker_codes": [],
        "direct_answer_blocked": False,
        "finalization_blocked": False,
        "required_component_count": 1,
        "covered_component_count": 1,
        "amendment_admission_count": 0,
    }
    payload.update(overrides)
    return payload


def _canonical_sufficiency_projection(**overrides) -> dict:
    judgment = RunSufficiencyJudgment(
        judgment_id="ag-sem-12a:judgment",
        decision=RunSufficiencyDecision.READY_DIRECT,
        final_answer_posture=SufficiencyPosture.DIRECT_ANSWER,
        final_answer_allowed=True,
        semantic_consumption=_semantic_consumption(),
    )
    projection = judgment.to_projection()
    projection.update(overrides)
    return projection


def _expected_author_payload_semantic_trace_ref(packet: FinalAnswerPacket) -> dict:
    canonical_json = json.dumps(
        _safe_json(packet.semantic_authority_ref),
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "schema_version": FINAL_ANSWER_AUTHOR_PAYLOAD_SEMANTIC_REF_SCHEMA_VERSION,
        "available": True,
        "source_packet_id": packet.packet_id,
        "source_packet_schema_version": packet.schema_version,
        "semantic_authority_ref_schema_version": (
            FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION
        ),
        "authority_owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "semantic_state_facts_digest": SEMANTIC_DIGEST,
        "ref_digest": sha256(canonical_json.encode("utf-8")).hexdigest(),
        "prompt_visible": False,
        "final_text_included": False,
        "raw_content_included": False,
    }


def test_semantic_authority_ref_schema_from_canonical_sufficiency_projection() -> None:
    projection = _canonical_sufficiency_projection()
    packet = build_final_answer_packet(
        run_id="ag-sem-12a-positive",
        final_evidence=[_passage()],
        sufficiency_judgment_projection=projection,
    )
    ref = packet.semantic_authority_ref
    assert ref["schema_version"] == FINAL_ANSWER_SEMANTIC_AUTHORITY_REF_SCHEMA_VERSION
    assert ref["available"] is True
    assert ref["sufficiency_semantic_consumed"] is True
    assert ref["authority_owner"] == "RunKernel.RunAuthoritySufficiencyJudgment"
    assert ref["semantic_state_facts_digest"] == SEMANTIC_DIGEST
    assert ref["semantic_summary_schema_version"] == SEMANTIC_SCHEMA
    assert ref["required_component_count"] == 1
    assert ref["covered_component_count"] == 1
    assert ref["missing_component_count"] == 0
    assert ref["blocker_count"] == 0
    assert "satisfied_coverage_count" not in ref
    assert "consumed" not in ref
    assert ref["sufficiency_judgment_ref"]["judgment_id"] == "ag-sem-12a:judgment"

    payload = packet.to_dict()
    assert payload["semantic_authority_ref"] == ref
    assert packet.to_trace_fragment()["final_answer_packet"]["semantic_authority_ref"] == ref

    encoded = json.dumps(payload, sort_keys=True)
    for forbidden in (
        "bounded_text",
        "component_summaries",
        "amendment_summaries",
        "raw_prompt",
        "provider_payload",
    ):
        assert forbidden not in encoded


def test_author_payload_semantic_trace_ref_schema_and_digest() -> None:
    projection = _canonical_sufficiency_projection()
    packet = build_final_answer_packet(
        run_id="ag-sem-12b-positive",
        final_evidence=[_passage()],
        sufficiency_judgment_projection=projection,
    )

    payload = packet.to_author_input_payload(
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    expected = _expected_author_payload_semantic_trace_ref(packet)
    assert payload.semantic_authority_trace_ref == expected
    assert payload.to_trace_ref()["semantic_authority_trace_ref"] == expected
    assert expected["ref_digest"] == sha256(
        json.dumps(
            _safe_json(packet.semantic_authority_ref),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    encoded = json.dumps(expected, sort_keys=True)
    for forbidden in (
        "bounded_text",
        "component_summaries",
        "amendment_summaries",
        "prompt_text",
        "raw_prompt",
        "provider_payload",
        "model_response",
        "final_prose",
    ):
        assert forbidden not in encoded


def test_author_payload_semantic_trace_ref_empty_when_packet_ref_empty() -> None:
    packet = build_final_answer_packet(
        run_id="ag-sem-12b-empty",
        final_evidence=[_passage()],
    )

    payload = packet.to_author_input_payload(
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert packet.semantic_authority_ref == {}
    assert payload.semantic_authority_trace_ref == {}
    assert "semantic_authority_trace_ref" not in payload.to_trace_ref()


def test_author_payload_semantic_trace_ref_merges_into_packet_author_input_refs() -> None:
    projection = _canonical_sufficiency_projection()
    packet = build_final_answer_packet(
        run_id="ag-sem-12b-author-refs",
        final_evidence=[_passage()],
        sufficiency_judgment_projection=projection,
    )
    payload = packet.to_author_input_payload(
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )

    assert "semantic_authority_trace_ref" not in packet.author_input_refs
    packet_with_payload = packet.with_author_input_payload(payload)

    assert packet_with_payload.author_input_refs["semantic_authority_trace_ref"] == (
        payload.to_trace_ref()["semantic_authority_trace_ref"]
    )


def test_semantic_authority_ref_prefers_consumption_counts_over_summary_defaults() -> None:
    projection = _canonical_sufficiency_projection(
        semantic_consumption=_semantic_consumption(
            required_component_count=2,
            covered_component_count=1,
        ),
        semantic_state_facts_summary={
            "schema_version": SEMANTIC_SCHEMA,
            "semantic_state_facts_digest": SEMANTIC_DIGEST,
            "required_component_count": 0,
            "covered_component_count": 0,
        },
    )
    packet = build_final_answer_packet(
        run_id="ag-sem-12a-prefer-consumption",
        final_evidence=[_passage()],
        sufficiency_judgment_projection=projection,
    )
    ref = packet.semantic_authority_ref
    assert ref["required_component_count"] == 2
    assert ref["covered_component_count"] == 1
    assert ref["missing_component_count"] == 1


def test_semantic_authority_ref_omitted_when_consumption_present_without_count_keys() -> None:
    projection = _canonical_sufficiency_projection(
        semantic_consumption={
            "schema_version": SEMANTIC_SCHEMA,
            "semantic_state_facts_digest": SEMANTIC_DIGEST,
            "blocker_count": 1,
            "blocker_codes": ["example_blocker"],
        },
        semantic_state_facts_summary={
            "schema_version": SEMANTIC_SCHEMA,
            "semantic_state_facts_digest": SEMANTIC_DIGEST,
            "required_component_count": 0,
            "covered_component_count": 0,
        },
    )
    packet = build_final_answer_packet(
        run_id="ag-sem-12a-no-summary-fallback",
        final_evidence=[_passage()],
        sufficiency_judgment_projection=projection,
    )
    ref = packet.semantic_authority_ref
    assert "required_component_count" not in ref
    assert "covered_component_count" not in ref
    assert "missing_component_count" not in ref
    assert ref["blocker_count"] == 1


@pytest.mark.parametrize(
    ("projection_override", "label"),
    [
        (
            {
                "semantic_consumption": _semantic_consumption(
                    semantic_state_facts_digest=""
                ),
                "semantic_state_facts_summary": {},
            },
            "empty_digest",
        ),
        ({"owner": "TraceOnly.SufficiencyJudgment"}, "wrong_owner"),
        ({"canonical_state": False}, "noncanonical"),
        ({"trace_only": True}, "trace_only"),
    ],
)
def test_semantic_authority_ref_empty_for_invalid_or_missing_digest(
    projection_override: dict,
    label: str,
) -> None:
    projection = _canonical_sufficiency_projection(**projection_override)
    packet = build_final_answer_packet(
        run_id=f"ag-sem-12a-negative-{label}",
        final_evidence=[_passage()],
        sufficiency_judgment_projection=projection,
    )
    assert packet.semantic_authority_ref == {}
    assert "semantic_authority_ref" not in packet.to_dict()


def _author_surfaces(packet: FinalAnswerPacket) -> tuple:
    prompt_base = "unchanged author prompt for ag-sem-12a"
    _, payload = derive_author_input_payload(
        packet,
        prompt=prompt_base,
        author_system_prompt_key="author",
        author_effort="low",
    )
    citation_source_ids = tuple(
        record.source_id for record in packet.citation_eligible if record.source_id is not None
    )
    citation_ineligible_refs = tuple(
        {
            "evidence_id": record.evidence_id,
            "source_id": record.source_id,
            "reason": record.reason,
        }
        for record in packet.citation_ineligible
    )
    missing_source_obligations = tuple(packet.missing_required_obligations)
    partial_source_obligations = tuple(packet.partial_obligations)
    satisfied_source_obligations = tuple(packet.satisfied_obligations)
    authority_payload = packet.to_authority_payload(
        citation_source_ids=citation_source_ids,
        citation_ineligible_refs=citation_ineligible_refs,
        missing_source_obligations=missing_source_obligations,
        partial_source_obligations=partial_source_obligations,
        satisfied_source_obligations=satisfied_source_obligations,
    )
    authority_block = packet.to_author_authority_block(
        citation_source_ids=citation_source_ids,
        citation_ineligible_refs=citation_ineligible_refs,
        missing_source_obligations=missing_source_obligations,
        partial_source_obligations=partial_source_obligations,
        satisfied_source_obligations=satisfied_source_obligations,
        authority_payload=authority_payload,
    )
    return (
        payload.prompt,
        authority_block,
        payload.authority_payload,
        authority_payload,
        packet.citation_records,
        packet.source_obligations,
    )


def test_semantic_authority_ref_does_not_change_author_surfaces() -> None:
    projection = _canonical_sufficiency_projection()
    packet_with = build_final_answer_packet(
        run_id="ag-sem-12a-nondelta",
        final_evidence=[_passage(source_id=11)],
        author_evidence=[_passage(source_id=11)],
        sufficiency_judgment_projection=projection,
    )
    packet_without = replace(packet_with, semantic_authority_ref={})
    assert packet_with.semantic_authority_ref
    assert packet_without.semantic_authority_ref == {}

    with_surfaces = _author_surfaces(packet_with)
    without_surfaces = _author_surfaces(packet_without)
    assert with_surfaces == without_surfaces


def test_semantic_authority_ref_absent_from_forbidden_author_surfaces() -> None:
    projection = _canonical_sufficiency_projection()
    packet = build_final_answer_packet(
        run_id="ag-sem-12a-forbidden",
        final_evidence=[_passage()],
        sufficiency_judgment_projection=projection,
    )
    _, payload = derive_author_input_payload(
        packet,
        prompt="base prompt",
        author_system_prompt_key="author",
        author_effort="low",
    )
    assert "semantic_authority_ref" not in packet.author_input_refs
    assert "semantic_authority_ref" not in payload.authority_payload
    assert "semantic_authority_ref" not in payload.to_trace_ref()
    assert "semantic_authority_ref" not in payload.prompt
    assert "semantic_authority_trace_ref" not in payload.authority_payload
    assert "semantic_authority_trace_ref" not in payload.prompt


def test_static_guard_semantic_authority_ref_not_in_author_execution_runtime() -> None:
    assert "semantic_authority_ref" not in AUTHOR_RUNTIME.read_text(encoding="utf-8")
    assert "semantic_authority_trace_ref" not in AUTHOR_RUNTIME.read_text(
        encoding="utf-8"
    )


def test_static_guard_semantic_authority_ref_not_in_author_payload_paths() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    for region_name, start, end in (
        (
            "to_authority_payload",
            packet_source.index("def to_authority_payload("),
            packet_source.index("def to_author_input_payload("),
        ),
        (
            "to_author_authority_block",
            packet_source.index("def to_author_authority_block("),
            packet_source.index("def to_legacy_citation_handoff_inputs("),
        ),
        (
            "FinalAnswerAuthorInputPayload",
            packet_source.index("class FinalAnswerAuthorInputPayload"),
            packet_source.index("class FinalAnswerPacket"),
        ),
    ):
        region = packet_source[start:end]
        assert "semantic_authority_ref" not in region, region_name


def test_static_guard_semantic_authority_trace_ref_not_prompt_visible() -> None:
    packet_source = PACKET.read_text(encoding="utf-8")
    for region_name, start, end in (
        (
            "to_authority_payload",
            packet_source.index("def to_authority_payload("),
            packet_source.index("def to_author_input_payload("),
        ),
        (
            "to_author_authority_block",
            packet_source.index("def to_author_authority_block("),
            packet_source.index("def to_legacy_citation_handoff_inputs("),
        ),
    ):
        region = packet_source[start:end]
        assert "semantic_authority_trace_ref" not in region, region_name

    for path in (
        ROOT / "core" / "author_execution_runtime.py",
        ROOT / "core" / "retrieval.py",
        ROOT / "core" / "retrieval_dispatch_runtime.py",
        ROOT / "core" / "search_providers.py",
    ):
        assert "semantic_authority_trace_ref" not in path.read_text(encoding="utf-8")


def test_static_guard_adapter_does_not_read_run_kernel_semantic_histories() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    forbidden = (
        "initial_answer_contract",
        "semantic_observation_admission_history",
        "component_coverage_history",
        "build_semantic_state_facts_for_sufficiency",
    )
    for token in forbidden:
        assert token not in source


def test_static_guard_no_af_harness_imports_or_references() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    for module in imported:
        assert "followup_" not in module
        assert "offline_golden_harness" not in module
    for token in ("AF4B2", "AF4D", "AF5A", "AF5B", "followup_author"):
        assert token not in source
