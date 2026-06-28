from __future__ import annotations

import ast
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.analysis_gap_followup_search_packet import (
    ANALYSIS_GAP_SEARCH_PROPOSAL_POSTURE,
    FOLLOWUP_SEARCH_INTENT_PACKET_OWNER,
    FOLLOWUP_SEARCH_INTENT_PACKET_SCHEMA_VERSION,
    GAP_KIND_TO_FOLLOWUP_INTENT,
    FollowupSearchIntentPacketError,
    build_followup_search_intent_packet,
    followup_search_intent_packet_ref_from_packet,
    validate_followup_search_intent_packet,
)
from core.evidence_relative_analysis_packet import (
    build_evidence_relative_analysis_packet,
)
from tests.test_ag_analyst_evidence_relative_report_01 import (
    _analysis_fixture,
    _records_by_status,
    _support_proposal,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "analysis_gap_followup_search_packet.py"
ANALYST_MODULE = ROOT / "core" / "evidence_relative_analysis_packet.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
)
LEGACY_AUDIT_DOC = (
    ROOT / "docs" / "architecture" / "AG_ANALYSIS_GAP_FOLLOWUP_SEARCH_01.md"
)

FALSE_FLAGS = {
    "authorized": False,
    "query_plan_created": False,
    "search_executor_handoff_created": False,
    "search_dispatched": False,
    "provider_called": False,
    "broker_called": False,
    "model_called": False,
    "retrieval_executed": False,
    "fetch_read_executed": False,
    "search_result_candidate_packet_created": False,
    "fetch_read_content_packet_created": False,
    "evidence_ledger_admitted": False,
    "semantic_observation_admitted": False,
    "component_coverage_created": False,
    "source_obligation_satisfied": False,
    "citation_eligible": False,
    "citation_created": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
    "product_correctness_claimed": False,
    "contract_mutated": False,
}


def _analysis_gap_proposal(
    record: Mapping[str, Any],
    kind: str,
    *,
    direction: str | None = "Find a bounded follow-up source for this gap.",
    query_hint: str | None = None,
) -> dict[str, Any]:
    return {
        "proposal_kind": "analysis_gap",
        "gap_kind": kind,
        "reference_id": record["reference_id"],
        "reference_digest": record["reference_digest"],
        "candidate_id": record["candidate_id"],
        "candidate_digest": record["candidate_digest"],
        "fetch_read_content_packet_digest": record[
            "fetch_read_content_packet_digest"
        ],
        "search_result_candidate_packet_digest": record[
            "search_result_candidate_packet_digest"
        ],
        "component_id": record["component_id"],
        "source_obligation_candidate_ids": record.get(
            "source_obligation_candidate_ids",
            [],
        ),
        "information_needed": f"Need more information for {kind}.",
        "proposed_search_direction": direction,
        "proposed_query_hint": query_hint or f"{kind} official follow-up source",
        "required_source_class_hint": "official_current_rules",
        "required_source_tier_hint": "primary",
        "required_currentness_hint": "current",
        "priority_hint": "high",
    }


def _analysis_packet(
    proposals: list[Mapping[str, Any]] | None = None,
    *,
    readable_count: int = 1,
    failed_count: int = 0,
    include_contract: bool = True,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    kernel, _fetch_read_packet, projection = _analysis_fixture(
        readable_count=readable_count,
        failed_count=failed_count,
    )
    packet = _build_analysis_packet(
        projection,
        proposals or [],
        include_contract=include_contract,
    )
    return kernel, projection, packet


def _build_analysis_packet(
    projection: Mapping[str, Any],
    proposals: list[Mapping[str, Any]],
    *,
    include_contract: bool = True,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if include_contract:
        contract_ref = _contract_ref_from_projection(projection)
        kwargs = {
            "current_answer_contract_ref": contract_ref,
            "current_answer_contract_digest": contract_ref["contract_digest"],
        }
    return build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=list(proposals),
        **kwargs,
    )


def _contract_ref_from_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    record = _records_by_status(projection, "readable")[0]
    ref = dict(record.get("current_answer_contract_ref") or {})
    return {
        "source": ref.get("source") or "current_answer_contract",
        "contract_version": (
            ref.get("contract_version")
            or ref.get("current_contract_version")
            or ref.get("accepted_contract_version")
        ),
        "contract_digest": (
            ref.get("contract_digest")
            or ref.get("current_contract_digest")
            or ref.get("accepted_contract_digest")
            or record["current_answer_contract_digest"]
        ),
    }


def _packet_for_gap_kind(kind: str) -> tuple[dict[str, Any], dict[str, Any]]:
    _kernel, projection, _packet = _analysis_packet([])
    record = _records_by_status(projection, "readable")[0]
    analysis_packet = _build_analysis_packet(
        projection,
        [_analysis_gap_proposal(record, kind)],
    )
    followup_packet = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet
    )
    proposal = next(
        item
        for item in followup_packet["analysis_gap_search_proposals"]
        if item["source_gap_kind"] == kind
    )
    return followup_packet, proposal


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(_text(path))
    imported_names: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)
    return imported_names, called_names


def test_happy_path_packet_creation_from_validated_evidence_relative_analysis() -> None:
    followup_packet, proposal = _packet_for_gap_kind("missing_fact")

    assert followup_packet["owner"] == FOLLOWUP_SEARCH_INTENT_PACKET_OWNER
    assert (
        followup_packet["schema_version"]
        == FOLLOWUP_SEARCH_INTENT_PACKET_SCHEMA_VERSION
    )
    assert followup_packet["proposal_only"] is True
    assert followup_packet["canonical_state"] is False
    assert followup_packet["reduced_state"] is False
    assert followup_packet["current_answer_contract_ref"]["source"] == (
        "current_answer_contract"
    )
    assert followup_packet["current_answer_contract_ref"]["contract_digest"] == (
        followup_packet["current_answer_contract_digest"]
    )
    assert followup_packet["proposal_count"] == 1
    assert followup_packet["followup_search_intent_proposal_count"] == 1
    assert followup_packet["review_ready_proposal_count"] == 1

    assert proposal["proposal_posture"] == ANALYSIS_GAP_SEARCH_PROPOSAL_POSTURE
    assert proposal["source_gap_kind"] == "missing_fact"
    assert proposal["followup_intent_kind"] == "targeted_fact_search"
    assert proposal["ready_for_authorization_review"] is True
    assert proposal["authorized"] is False
    assert proposal["query_plan_created"] is False
    assert proposal["search_executor_handoff_created"] is False
    assert proposal["search_dispatched"] is False
    assert proposal["proposed_query_hint"] == "missing_fact official follow-up source"
    assert proposal["required_source_class_hint"] == "official_current_rules"
    assert proposal["evidence_relative_analysis_packet_id"] == (
        followup_packet["evidence_relative_analysis_packet_id"]
    )
    assert proposal["analyst_report_id"] == followup_packet["analyst_report_id"]


def test_packet_and_proposal_ids_and_digests_are_stable() -> None:
    _followup_packet, proposal = _packet_for_gap_kind("currentness_concern")
    _kernel, projection, _packet = _analysis_packet([])
    record = _records_by_status(projection, "readable")[0]
    analysis_packet = _build_analysis_packet(
        projection,
        [_analysis_gap_proposal(record, "currentness_concern")],
    )

    first = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=deepcopy(analysis_packet)
    )
    second = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=deepcopy(analysis_packet)
    )
    rebuilt = validate_followup_search_intent_packet(deepcopy(first))

    assert second["packet_id"] == first["packet_id"]
    assert second["packet_digest"] == first["packet_digest"]
    assert second["analysis_gap_search_proposals"][0]["proposal_id"] == (
        first["analysis_gap_search_proposals"][0]["proposal_id"]
    )
    assert second["analysis_gap_search_proposals"][0]["proposal_digest"] == (
        first["analysis_gap_search_proposals"][0]["proposal_digest"]
    )
    assert rebuilt == first
    assert proposal["proposal_id"]
    assert followup_search_intent_packet_ref_from_packet(first)["packet_id"] == (
        first["packet_id"]
    )


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("missing_readable_source", "replacement_readable_source_search"),
        ("unreadable_source", "replacement_readable_source_search"),
        ("missing_fact", "targeted_fact_search"),
        (
            "currentness_concern",
            "official_current_or_currentness_verification_search",
        ),
        ("scope_mismatch", "scoped_disambiguation_search"),
        ("analysis_gap", "targeted_analysis_gap_search"),
        (
            "possible_contradiction",
            "reconciliation_or_source_comparison_search",
        ),
    ],
)
def test_gap_kind_mappings(kind: str, expected: str) -> None:
    assert GAP_KIND_TO_FOLLOWUP_INTENT[kind] == expected
    _packet, proposal = _packet_for_gap_kind(kind)

    assert proposal["source_gap_kind"] == kind
    assert proposal["followup_intent_kind"] == expected
    assert proposal["ready_for_authorization_review"] is True


def test_analysis_missing_is_not_search_by_default_unless_explicit() -> None:
    _kernel, projection, _analysis = _analysis_packet(
        readable_count=2,
        failed_count=0,
    )
    readable = _records_by_status(projection, "readable")
    default_analysis = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_support_proposal(readable[0])],
        current_answer_contract_ref=_contract_ref_from_projection(projection),
        current_answer_contract_digest=_contract_ref_from_projection(projection)[
            "contract_digest"
        ],
    )
    default_packet = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=default_analysis
    )
    default_gap = next(
        item
        for item in default_packet["analysis_gap_search_proposals"]
        if item["source_gap_kind"] == "analysis_missing"
    )
    assert default_gap["followup_intent_kind"] == "non_searchable_review_gap"
    assert default_gap["search_intent_proposed"] is False
    assert default_gap["ready_for_authorization_review"] is False
    assert "gap_does_not_propose_search_intent" in default_gap[
        "authorization_review_blockers"
    ]

    explicit_analysis = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[
            _support_proposal(readable[0]),
            _analysis_gap_proposal(
                readable[1],
                "analysis_missing",
                direction="Search for a second readable analysis source.",
                query_hint="second readable analysis source",
            ),
        ],
        current_answer_contract_ref=_contract_ref_from_projection(projection),
        current_answer_contract_digest=_contract_ref_from_projection(projection)[
            "contract_digest"
        ],
    )
    explicit_packet = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=explicit_analysis
    )
    explicit_gap = next(
        item
        for item in explicit_packet["analysis_gap_search_proposals"]
        if item["source_gap_kind"] == "analysis_missing"
    )
    assert explicit_gap["followup_intent_kind"] == "targeted_analysis_gap_search"
    assert explicit_gap["search_intent_proposed"] is True
    assert explicit_gap["ready_for_authorization_review"] is True


def test_current_contract_ref_and_digest_are_required_for_review_ready() -> None:
    _kernel, projection, _packet = _analysis_packet([], include_contract=False)
    projection_without_ref = deepcopy(projection)
    for record in projection_without_ref["fetch_read_candidate_custody"][
        "fetch_read_candidate_custody_records"
    ]:
        record.pop("current_answer_contract_ref", None)
    record = _records_by_status(projection, "readable")[0]
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection_without_ref,
        analyst_proposal_records=[_analysis_gap_proposal(record, "missing_fact")],
    )

    followup_packet = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet
    )
    proposal = followup_packet["analysis_gap_search_proposals"][0]

    assert followup_packet.get("current_answer_contract_ref") is None
    assert proposal["ready_for_authorization_review"] is False
    assert "missing_current_answer_contract_ref" in proposal[
        "authorization_review_blockers"
    ]
    assert proposal["authorized"] is False
    assert proposal["search_dispatched"] is False


def test_no_dispatch_query_plan_or_downstream_authority_flags() -> None:
    followup_packet, proposal = _packet_for_gap_kind("possible_contradiction")

    for surface in (followup_packet, proposal):
        flags = surface["closed_surface_flags"]
        for key, expected in FALSE_FLAGS.items():
            assert surface[key] is expected
            assert flags[key] is expected


def test_raw_private_closed_authority_and_dangerous_true_inputs_are_rejected() -> None:
    _followup_packet, _proposal = _packet_for_gap_kind("missing_fact")
    _kernel, projection, _packet = _analysis_packet([])
    record = _records_by_status(projection, "readable")[0]
    analysis_packet = _build_analysis_packet(
        projection,
        [_analysis_gap_proposal(record, "missing_fact")],
    )

    with pytest.raises(FollowupSearchIntentPacketError, match="raw/private"):
        build_followup_search_intent_packet(
            evidence_relative_analysis_packet=analysis_packet,
            mode_budget_hints={"raw_prompt": "do not retain"},
        )
    with pytest.raises(FollowupSearchIntentPacketError, match="closed authority"):
        build_followup_search_intent_packet(
            evidence_relative_analysis_packet=analysis_packet,
            mode_budget_hints={"final_answer_packet": {"packet_id": "forbidden"}},
        )
    with pytest.raises(FollowupSearchIntentPacketError, match="closed runtime"):
        build_followup_search_intent_packet(
            evidence_relative_analysis_packet=analysis_packet,
            mode_budget_hints={"search_dispatched": True},
        )


def test_tampered_packet_report_gap_and_proposal_digests_are_rejected() -> None:
    _kernel, projection, _packet = _analysis_packet([])
    record = _records_by_status(projection, "readable")[0]
    analysis_packet = _build_analysis_packet(
        projection,
        [_analysis_gap_proposal(record, "missing_fact")],
    )

    tampered_packet = deepcopy(analysis_packet)
    tampered_packet["packet_digest"] = "0" * 64
    with pytest.raises(FollowupSearchIntentPacketError, match="analysis packet"):
        build_followup_search_intent_packet(
            evidence_relative_analysis_packet=tampered_packet
        )

    tampered_report = deepcopy(analysis_packet)
    tampered_report["analyst_report"]["report_digest"] = "1" * 64
    with pytest.raises(FollowupSearchIntentPacketError, match="analyst report"):
        build_followup_search_intent_packet(
            evidence_relative_analysis_packet=tampered_report
        )

    tampered_gap = deepcopy(analysis_packet)
    tampered_gap["analyst_report"]["analysis_gap_proposals"][0][
        "gap_digest"
    ] = "2" * 64
    with pytest.raises(FollowupSearchIntentPacketError, match="analysis gap"):
        build_followup_search_intent_packet(
            evidence_relative_analysis_packet=tampered_gap
        )

    followup_packet = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet
    )
    tampered_proposal = deepcopy(followup_packet)
    tampered_proposal["analysis_gap_search_proposals"][0][
        "proposal_digest"
    ] = "3" * 64
    with pytest.raises(FollowupSearchIntentPacketError, match="proposal digest"):
        validate_followup_search_intent_packet(tampered_proposal)


def test_source_obligation_candidate_ids_remain_lineage_only() -> None:
    _packet, proposal = _packet_for_gap_kind("missing_fact")

    assert proposal["source_obligation_candidate_ids"]
    assert proposal["source_obligation_candidate_ids_are_lineage_only"] is True
    assert proposal["source_obligation_satisfied"] is False
    assert "source_obligation_satisfaction" not in json.dumps(
        proposal,
        sort_keys=True,
    )


def test_no_runkernel_state_mutation() -> None:
    kernel, projection, _packet = _analysis_packet([])
    record = _records_by_status(projection, "readable")[0]
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_analysis_gap_proposal(record, "missing_fact")],
        current_answer_contract_ref=_contract_ref_from_projection(projection),
        current_answer_contract_digest=_contract_ref_from_projection(projection)[
            "contract_digest"
        ],
    )
    projections_before = deepcopy(kernel.state.projections)
    search_executor_before = deepcopy(kernel.state.search_executor_handoff_state)
    evidence_projection_before = kernel.state.evidence_ledger.to_projection().to_dict()

    build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet
    )

    assert kernel.state.projections == projections_before
    assert kernel.state.search_executor_handoff_state == search_executor_before
    assert kernel.state.evidence_ledger.to_projection().to_dict() == (
        evidence_projection_before
    )
    assert "followup_search_intent_packet" not in kernel.state.projections
    assert kernel.state.followup_authorization_state == {}
    assert kernel.state.followup_evidence_intake_state == {}
    assert kernel.state.followup_sufficiency_recheck_state == {}
    assert kernel.state.followup_final_answer_packet_state == {}
    assert kernel.state.followup_author_observation_state == {}


def test_static_import_and_call_guards_keep_closed_surfaces_closed() -> None:
    forbidden_imports = {
        "core.run_kernel",
        "core.pipeline_orchestrator",
        "core.search_executor_handoff_runtime",
        "core.search_result_candidate_packet",
        "core.fetch_read_content_reference",
        "core.evidence_ledger_lifecycle",
        "core.semantic_observation_foundation",
        "core.semantic_observation_admission_runtime",
        "core.component_coverage_record",
        "core.component_coverage_reduction_runtime",
        "core.run_authority_sufficiency",
        "core.run_authority_sufficiency_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    forbidden_calls = {
        "ask_model",
        "search_web_results",
        "search_exa_results",
        "search_linkup_results",
        "brave_reconnaissance",
        "fetch_page",
        "fetch_url_text",
        "urlopen",
        "execute_author_action",
        "derive_author_input_payload",
        "format_citation",
        "render_citations",
        "build_search_executor_handoff_observation_payload",
        "build_search_result_candidate_packet_from_live_validation_state",
        "build_fetch_read_content_packet_from_candidate_packet",
        "reduce_fetch_read_content_packet_into_evidence_ledger",
        "build_semantic_observation_admission_state",
        "build_component_coverage_reduction_state",
        "build_sufficiency_judgment",
        "FinalAnswerPacket",
    }

    imported_names, called_names = _imports_and_calls(RUNTIME_MODULE)
    assert imported_names.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint(forbidden_calls)
    source = _text(RUNTIME_MODULE)
    for token in (
        "SERPER_API_KEY",
        "requests.",
        "httpx.",
        "openai.",
        "SearchExecutorHandoff(",
        "SearchResultCandidatePacket(",
        "FetchReadContentPacket(",
        "EvidenceLedger(",
        "SemanticObservation(",
        "ComponentCoverage",
        "SufficiencyJudgment(",
        "FinalAnswerPacket(",
        "AuthorExecutor(",
    ):
        assert token not in source, token

    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", str(PIPELINE.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert diff.stdout.strip() == ""
    assert "possible_contradiction" in _text(ANALYST_MODULE)


def test_docs_record_followup_search_intent_posture() -> None:
    required = (
        "FollowupSearchIntentPacket",
        "AnalysisGapSearchProposal",
        "proposal-only gap-to-search-intent posture",
        "not search authorization",
        "not a query plan",
        "does not create SearchExecutorHandoff",
        "does not dispatch search",
        "does not create evidence",
        "RunKernel/SearchPlanner/SearchExecutorHandoff authorization remains required",
    )
    for path in DOCS:
        text = " ".join(_text(path).replace("`", "").split())
        for needle in required:
            assert needle in text, (path, needle)


def test_legacy_surface_audit_is_documented() -> None:
    text = _text(LEGACY_AUDIT_DOC)
    required = (
        "Legacy surface audit",
        "AG-96 followup_* provider/FAP/Author stack",
        "source-class recovery bridges",
        "component gap recovery runtime",
        "SearchWorkPlan shadow machinery",
        "offline SearchExecutor bridge",
        "provider wrappers/retrieval/pipeline orchestrator",
        "avoided/legacy/passive",
        "later retirement targets",
    )
    for needle in required:
        assert needle in text, needle
