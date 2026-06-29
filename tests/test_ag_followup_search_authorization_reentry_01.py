from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.analysis_gap_followup_search_packet import build_followup_search_intent_packet
from core.followup_search_authorization_loop import (
    FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER,
    FollowupSearchAuthorizationLoopError,
    authorize_followup_search_work,
    run_fixture_followup_search_reentry_loop,
)
from core.followup_search_authorization_runtime import (
    FOLLOWUP_SEARCH_AUTHORIZATION_OWNER,
    FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
)
from tests.test_ag_analysis_gap_followup_search_01 import (
    _analysis_gap_proposal,
    _analysis_packet,
    _build_analysis_packet,
)
from tests.test_ag_analyst_evidence_relative_report_01 import _records_by_status
from tests.test_ag_component_coverage_reliability_proof_01 import (
    _assert_downstream_closed,
    _chain_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "followup_search_authorization_runtime.py"
LOOP_MODULE = ROOT / "core" / "followup_search_authorization_loop.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"
DOCS = (
    ROOT / "docs" / "architecture" / "AG_FOLLOWUP_SEARCH_AUTHORIZATION_REENTRY_01.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
)


def _ready_proposal(followup_packet: Mapping[str, Any]) -> dict[str, Any]:
    return next(
        dict(proposal)
        for proposal in followup_packet["analysis_gap_search_proposals"]
        if proposal["ready_for_authorization_review"] is True
    )


def _fixture_candidate() -> dict[str, Any]:
    return {
        "title": "Official Follow-up Permit Threshold",
        "url": "https://official.example.gov/followup/permit-threshold",
        "domain": "official.example.gov",
        "snippet": "Fixture search candidate for the missing permit threshold.",
        "published_or_observed_date": "2026-01-15",
        "source_obligation_candidate_ids": ["obligation:official-current"],
    }


def _readable_material() -> dict[str, Any]:
    bounded_text = (
        "Bounded sanitized follow-up evidence confirms the permit threshold "
        "for the requested component."
    )
    return {
        "fetch_read_status": "readable",
        "content_title": "Official Follow-up Permit Threshold",
        "bounded_text": bounded_text,
        "bounded_text_char_count": len(bounded_text),
        "published_or_observed_date": "2026-01-15",
    }


def _failed_material() -> dict[str, Any]:
    return {
        "fetch_read_status": "failed",
        "read_error_code": "timeout",
        "failure_reason": "fixture follow-up source remained unreadable",
    }


def _packet_with_source_class(source_class: str) -> tuple[Any, dict[str, Any]]:
    kernel, projection, _packet = _analysis_packet(readable_count=1, failed_count=0)
    record = _records_by_status(projection, "readable")[0]
    proposal = _analysis_gap_proposal(record, "missing_fact")
    proposal["required_source_class_hint"] = source_class
    analysis_packet = _build_analysis_packet(projection, [proposal])
    return kernel, build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet
    )


def _packet_without_contract_lineage() -> tuple[Any, dict[str, Any]]:
    kernel, projection, _packet = _analysis_packet(
        readable_count=1,
        failed_count=0,
        include_contract=False,
    )
    projection_without_ref = deepcopy(projection)
    for record in projection_without_ref["fetch_read_candidate_custody"][
        "fetch_read_candidate_custody_records"
    ]:
        record.pop("current_answer_contract_ref", None)
    record = _records_by_status(projection, "readable")[0]
    analysis_packet = _build_analysis_packet(
        projection_without_ref,
        [_analysis_gap_proposal(record, "missing_fact")],
        include_contract=False,
    )
    return kernel, build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet
    )


def _imports_calls_and_classes(path: Path) -> tuple[set[str], set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    called_names: set[str] = set()
    class_names: set[str] = set()
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
        elif isinstance(node, ast.ClassDef):
            class_names.add(node.name)
    return imported_names, called_names, class_names


def test_valid_followup_intent_authorizes_bounded_query_bundle_without_self_authorizing() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    followup_packet = chain["followup_packet"]
    proposal = _ready_proposal(followup_packet)
    handoff_before = deepcopy(kernel.state.search_executor_handoff_state)

    result = authorize_followup_search_work(
        run_kernel=kernel,
        followup_search_intent_packet=followup_packet,
        proposal_ids=(proposal["proposal_id"],),
        mode="Balanced",
    )
    projection = result.authorization_projection
    work = result.authorized_work_identity

    assert projection["owner"] == FOLLOWUP_SEARCH_AUTHORIZATION_OWNER
    assert projection["authorized_loop_count"] == 1
    assert projection["latest_authorization"]["authorization_id"]
    assert work["handoff_id"].startswith("followup-search-work:")
    assert work["search_executor_handoff_style_identity"] is True
    assert work["actual_search_executor_handoff_state"] is False
    assert work["query_bundle_ref"]["query_count"] >= 1
    assert proposal["authorized"] is False
    assert proposal["search_dispatched"] is False
    assert followup_packet["search_dispatched"] is False
    assert kernel.state.search_executor_handoff_state == handoff_before
    assert FOLLOWUP_SEARCH_AUTHORIZATION_STAGE in kernel.state.projections
    _assert_downstream_closed(kernel)


def test_followup_authorization_rejects_budget_duplicates_lineage_source_and_depth() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    packet = chain["followup_packet"]
    proposal = _ready_proposal(packet)

    with pytest.raises(FollowupSearchAuthorizationLoopError, match="mode_fast"):
        authorize_followup_search_work(
            run_kernel=kernel,
            followup_search_intent_packet=packet,
            mode="Fast",
        )

    kernel.state.projections[FOLLOWUP_SEARCH_AUTHORIZATION_STAGE] = {
        "authorized_loop_count": 2,
        "authorized_work_identities": [],
    }
    with pytest.raises(FollowupSearchAuthorizationLoopError, match="budget_exhausted"):
        authorize_followup_search_work(
            run_kernel=kernel,
            followup_search_intent_packet=packet,
            mode="Balanced",
        )
    kernel.state.projections.pop(FOLLOWUP_SEARCH_AUTHORIZATION_STAGE)

    authorize_followup_search_work(
        run_kernel=kernel,
        followup_search_intent_packet=packet,
        proposal_ids=(proposal["proposal_id"],),
        mode="Balanced",
    )
    with pytest.raises(FollowupSearchAuthorizationLoopError, match="duplicate_work"):
        authorize_followup_search_work(
            run_kernel=kernel,
            followup_search_intent_packet=packet,
            proposal_ids=(proposal["proposal_id"],),
            mode="Balanced",
            unresolved_blocker_ids=(proposal["source_gap_id"],),
        )

    missing_kernel, missing_packet = _packet_without_contract_lineage()
    with pytest.raises(
        FollowupSearchAuthorizationLoopError,
        match="current_answer_contract lineage",
    ):
        authorize_followup_search_work(
            run_kernel=missing_kernel,
            followup_search_intent_packet=missing_packet,
            mode="Balanced",
        )

    unsupported_kernel, unsupported_packet = _packet_with_source_class("social_media")
    with pytest.raises(FollowupSearchAuthorizationLoopError, match="unsupported_source_class"):
        authorize_followup_search_work(
            run_kernel=unsupported_kernel,
            followup_search_intent_packet=unsupported_packet,
            mode="Balanced",
        )

    depth_chain = _chain_fixture()
    with pytest.raises(FollowupSearchAuthorizationLoopError, match="logical_depth"):
        authorize_followup_search_work(
            run_kernel=depth_chain["kernel"],
            followup_search_intent_packet=depth_chain["followup_packet"],
            mode="Balanced",
            logical_depth=2,
        )

    no_new_chain = _chain_fixture()
    with pytest.raises(FollowupSearchAuthorizationLoopError, match="no_new_evidence"):
        authorize_followup_search_work(
            run_kernel=no_new_chain["kernel"],
            followup_search_intent_packet=no_new_chain["followup_packet"],
            mode="Balanced",
            new_evidence_expected=False,
        )


def test_authorized_fixture_reentry_updates_coverage_through_existing_chain() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    current_contract_before = deepcopy(kernel.state.current_answer_contract)

    result = run_fixture_followup_search_reentry_loop(
        run_kernel=kernel,
        followup_search_intent_packet=chain["followup_packet"],
        fixture_candidates=[_fixture_candidate()],
        fixture_fetch_read_materials=[_readable_material()],
        mode="Balanced",
        analyst_repass_outcome="support",
    )

    assert result.candidate_packet["candidate_count"] == 1
    assert result.candidate_packet["candidate_records"][0]["candidate_id"].startswith(
        "followup-search-candidate:"
    )
    assert result.fetch_read_packet["reference_count"] == 1
    assert result.fetch_read_packet["reference_records"][0]["fetch_read_status"] == "readable"
    assert result.ledger_projection["fetch_read_candidate_custody"]["custody_record_count"] >= 1
    assert result.analysis_packet["analyst_report"]["finding_count"] == 1
    assert result.semantic_admission_results
    assert result.coverage_projection["coverage_state"] == "supported_with_caveats"
    assert result.coverage_projection["semantic_support_status"] == "supported"
    assert result.coverage_projection["followup_need"] == "optional"
    assert kernel.state.component_coverage_projection == result.coverage_projection
    assert kernel.state.current_answer_contract == current_contract_before
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert result.to_dict()["provider_called"] is False


def test_unresolved_fixture_reentry_remains_blocked_or_contested_without_support() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]

    result = run_fixture_followup_search_reentry_loop(
        run_kernel=kernel,
        followup_search_intent_packet=chain["followup_packet"],
        fixture_candidates=[_fixture_candidate()],
        fixture_fetch_read_materials=[_failed_material()],
        mode="Balanced",
        analyst_repass_outcome="insufficient",
    )

    posture = result.unresolved_component_posture
    assert result.semantic_admission_results == ()
    assert result.coverage_projection == {}
    assert posture["coverage_state"] == "blocked"
    assert posture["followup_need"] == "required"
    assert posture["semantic_support_status"] == "unknown"
    assert posture["support_admitted"] is False
    assert kernel.state.semantic_observation_admission_history == []
    assert kernel.state.component_coverage_projection == {}
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}


def test_authorization_and_reentry_keep_closed_surfaces_and_avoid_packet_sprawl() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.authoring",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    forbidden_calls = {
        "run_pipeline",
        "call_broker",
        "invoke_broker",
        "search_web",
        "retrieve",
        "dispatch_retrieval",
        "fetch_url",
        "fetch_page",
        "read_url",
        "execute_author",
        "execute_author_action",
        "create_final_answer_packet",
        "derive_author_input_payload",
        "ask_model",
    }
    for path in (RUNTIME_MODULE, LOOP_MODULE):
        imports, calls, classes = _imports_calls_and_classes(path)
        assert imports.isdisjoint(forbidden_imports)
        assert calls.isdisjoint(forbidden_calls)
        assert not any(name.endswith("Packet") for name in classes)
        source = path.read_text(encoding="utf-8")
        assert "SearchWorkPlan" not in source
        assert "offline_search_executor_bridge" not in source

    run_kernel_source = RUN_KERNEL_MODULE.read_text(encoding="utf-8")
    assert "FOLLOWUP_SEARCH_AUTHORIZE" in run_kernel_source
    assert "FOLLOWUP_AUTHORIZATION_CONSUME" in run_kernel_source
    assert FOLLOWUP_SEARCH_AUTHORIZATION_LOOP_HELPER in LOOP_MODULE.read_text(
        encoding="utf-8"
    )


def test_docs_record_followup_search_authorization_reentry_posture() -> None:
    docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    required = (
        "AG-FOLLOWUP-SEARCH-AUTHORIZATION-REENTRY-01",
        "first governed remediation loop",
        "FollowupSearchIntent remains proposal-only",
        "RunKernel owns follow-up search authorization",
        "authorized work identity/query bundle is not live dispatch",
        "Fixture-backed reentry proves the future product path without live providers",
        "SearchResultCandidatePacket",
        "FetchReadContentPacket",
        "EvidenceLedger",
        "EvidenceRelativeAnalysisPacket",
        "SemanticObservation",
        "ComponentCoverage",
        "blocked/follow-up-required/contested",
        "Scrutineer comes next",
        "No Sufficiency/FAP/Author/citation/source-obligation satisfaction/product correctness",
    )
    for phrase in required:
        assert phrase in docs_text
