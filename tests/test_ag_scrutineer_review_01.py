from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Mapping

from core.analysis_gap_followup_search_packet import build_followup_search_intent_packet
from core.evidence_relative_analysis_packet import build_evidence_relative_analysis_packet
from core.followup_search_authorization_loop import (
    run_fixture_followup_search_reentry_loop,
)
from core.followup_search_authorization_runtime import (
    FOLLOWUP_SEARCH_AUTHORIZATION_STAGE,
)
from core.run_kernel import SCRUTINEER_REVIEW_STAGE
from core.scrutineer_review_runtime import (
    SCRUTINEER_REVIEW_OWNER,
    build_scrutineer_review_record,
    reduce_scrutineer_review,
)
from core.scrutineer_review_runtime import (
    SCRUTINEER_REVIEW_STAGE as SCRUTINEER_REVIEW_RUNTIME_STAGE,
)
from tests.test_ag_analysis_gap_followup_search_01 import (
    _analysis_gap_proposal,
    _contract_ref_from_projection,
)
from tests.test_ag_analyst_evidence_relative_report_01 import (
    _analysis_fixture,
    _records_by_status,
    _support_proposal,
)
from tests.test_ag_component_coverage_reliability_proof_01 import (
    _assert_downstream_closed,
    _chain_fixture,
    _reduce_coverage,
)
from tests.test_ag_followup_search_authorization_reentry_01 import (
    _failed_material,
    _fixture_candidate,
    _readable_material,
)
from tests.test_ag_semantic_observation_admission_bridge_01 import (
    _bridge,
    _bridge_coverage_record,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "scrutineer_review_runtime.py"
RUN_KERNEL_MODULE = ROOT / "core" / "run_kernel.py"
DOCS = (
    ROOT / "docs" / "architecture" / "AG_SCRUTINEER_REVIEW_01.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
)


def _supported_chain() -> dict[str, Any]:
    kernel, fetch_read_packet, projection = _analysis_fixture(
        readable_count=1,
        failed_count=0,
    )
    record = _records_by_status(projection, "readable")[0]
    contract_ref = _contract_ref_from_projection(projection)
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_support_proposal(record)],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    chain = {
        "kernel": kernel,
        "fetch_read_packet": fetch_read_packet,
        "ledger_projection": projection,
        "analysis_packet": analysis_packet,
    }
    admission = _bridge(chain)
    coverage_record = _bridge_coverage_record(chain, admission)
    coverage_projection = _reduce_coverage(kernel, coverage_record)
    return {
        **chain,
        "semantic_admission": admission,
        "coverage_projection": coverage_projection,
    }


def _gap_chain(kind: str) -> dict[str, Any]:
    kernel, fetch_read_packet, projection = _analysis_fixture(
        readable_count=1,
        failed_count=0,
    )
    record = _records_by_status(projection, "readable")[0]
    contract_ref = _contract_ref_from_projection(projection)
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_analysis_gap_proposal(record, kind)],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    followup_packet = build_followup_search_intent_packet(
        evidence_relative_analysis_packet=analysis_packet
    )
    return {
        "kernel": kernel,
        "fetch_read_packet": fetch_read_packet,
        "ledger_projection": projection,
        "analysis_packet": analysis_packet,
        "followup_packet": followup_packet,
    }


def _review_record(chain: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    kernel = chain["kernel"]
    return build_scrutineer_review_record(
        evidence_relative_analysis_packet=chain["analysis_packet"],
        semantic_observation_admission_projection=(
            kernel.state.semantic_observation_admission_projection
        ),
        semantic_observation_admission_history=(
            kernel.state.semantic_observation_admission_history
        ),
        component_coverage_projection=kernel.state.component_coverage_projection,
        component_coverage_history=kernel.state.component_coverage_history,
        **kwargs,
    )


def _reduce_review(chain: Mapping[str, Any], record: Mapping[str, Any]):
    return reduce_scrutineer_review(
        run_kernel=chain["kernel"],
        scrutineer_review_record=record,
    )


def _compact_reentry_ref(result: Any) -> dict[str, Any]:
    return {
        "authorization_action_id": result.authorization_result.authorization_action_id,
        "analysis_packet_id": result.analysis_packet.get("packet_id"),
        "analysis_packet_digest": result.analysis_packet.get("packet_digest"),
        "semantic_observation_admission_count": len(result.semantic_admission_results),
        "coverage_reduced": bool(result.coverage_projection),
        "fixture_reentry_only": True,
        "live_dispatch_allowed": False,
    }


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


def test_clean_review_signs_off_without_downstream_product_state() -> None:
    chain = _supported_chain()
    kernel = chain["kernel"]
    record = _review_record(chain, mode="Balanced", red_flag_context=True)
    result = _reduce_review(chain, record)
    projection = result.review_projection

    assert record["review_outcome"] == "signed_off"
    assert record["issue_count"] == 0
    assert record["signoff"]["analyst_work_signed_off"] is True
    assert record["signoff"]["final_answer_signed_off"] is False
    assert record["signoff"]["product_correctness_claimed"] is False
    assert projection["owner"] == SCRUTINEER_REVIEW_OWNER
    assert projection["canonical_state"] is True
    assert projection["latest_review"]["review_outcome"] == "signed_off"
    assert kernel.state.projections[SCRUTINEER_REVIEW_STAGE] == projection
    assert SCRUTINEER_REVIEW_STAGE == SCRUTINEER_REVIEW_RUNTIME_STAGE
    _assert_downstream_closed(kernel, chain["coverage_projection"])


def test_overclaim_review_requires_remediation_without_authorizing_search() -> None:
    kernel, _fetch_read_packet, projection = _analysis_fixture(
        readable_count=1,
        failed_count=0,
    )
    record = _records_by_status(projection, "readable")[0]
    contract_ref = _contract_ref_from_projection(projection)
    analysis_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_support_proposal(record)],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    component = kernel.state.initial_answer_contract["accepted_answer_component_refs"][0]
    chain = {"kernel": kernel, "analysis_packet": analysis_packet}
    bad_coverage = {
        "coverage_record_id": "coverage:scrutineer:overclaim",
        "coverage_record_digest": "digest:overclaim",
        "answer_component_id": component["component_id"],
        "component_revision": component["component_revision"],
        "component_digest": component["component_digest"],
        "coverage_state": "supported_with_caveats",
        "semantic_support_status": "supported",
        "source_obligation_status": "partial",
        "accepted_observation_refs": [],
        "content_reference_bindings": [],
    }

    review = build_scrutineer_review_record(
        evidence_relative_analysis_packet=analysis_packet,
        mode="Balanced",
        component_coverage_projection=bad_coverage,
    )
    result = _reduce_review(chain, review)
    issue_kinds = {issue["issue_kind"] for issue in result.review_projection["issues"]}

    assert result.review_projection["review_outcome"] == "remediation_required"
    assert "coverage_overclaim" in issue_kinds
    assert "missing_semantic_observation_admission" in issue_kinds
    assert FOLLOWUP_SEARCH_AUTHORIZATION_STAGE not in kernel.state.projections
    assert kernel.state.semantic_observation_admission_history == []
    assert kernel.state.component_coverage_projection == {}
    _assert_downstream_closed(kernel)


def test_currentness_contradiction_or_scope_issue_references_followup_proposal_only() -> None:
    chain = _gap_chain("currentness_concern")
    kernel = chain["kernel"]
    review = _review_record(
        chain,
        mode="Balanced",
        followup_search_intent_packet=chain["followup_packet"],
    )
    result = _reduce_review(chain, review)
    issue = result.review_projection["issues"][0]

    assert result.review_projection["review_outcome"] == "remediation_required"
    assert issue["issue_kind"] == "currentness_unresolved"
    assert issue["followup_proposal_ref"]["proposal_id"].startswith(
        "analysis-gap-search-proposal:"
    )
    assert issue["followup_proposal_ref"]["authorized"] is False
    assert FOLLOWUP_SEARCH_AUTHORIZATION_STAGE not in kernel.state.projections
    _assert_downstream_closed(kernel)


def test_remediation_path_final_verification_signs_off_after_separate_followup_loop() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    initial = _review_record(
        chain,
        mode="Balanced",
        followup_search_intent_packet=chain["followup_packet"],
    )
    _reduce_review(chain, initial)

    assert kernel.state.projections[SCRUTINEER_REVIEW_STAGE]["review_outcome"] == (
        "remediation_required"
    )
    assert FOLLOWUP_SEARCH_AUTHORIZATION_STAGE not in kernel.state.projections

    reentry = run_fixture_followup_search_reentry_loop(
        run_kernel=kernel,
        followup_search_intent_packet=chain["followup_packet"],
        fixture_candidates=[_fixture_candidate()],
        fixture_fetch_read_materials=[_readable_material()],
        mode="Balanced",
        analyst_repass_outcome="support",
    )
    final_chain = {
        "kernel": kernel,
        "analysis_packet": reentry.analysis_packet,
    }
    final = _review_record(
        final_chain,
        mode="Balanced",
        review_pass_kind="final_verification",
        red_flag_context=True,
        followup_authorization_projection=kernel.state.projections[
            FOLLOWUP_SEARCH_AUTHORIZATION_STAGE
        ],
        followup_reentry_refs=_compact_reentry_ref(reentry),
    )
    result = _reduce_review(final_chain, final)

    assert result.review_projection["review_outcome"] == "signed_off"
    assert result.review_projection["issue_count"] == 0
    assert kernel.state.projections[FOLLOWUP_SEARCH_AUTHORIZATION_STAGE][
        "proposal_packet_authorizes_search_by_itself"
    ] is False
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}


def test_failed_remediation_final_verification_preserves_contested_posture() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    initial = _review_record(
        chain,
        mode="Balanced",
        followup_search_intent_packet=chain["followup_packet"],
    )
    _reduce_review(chain, initial)

    reentry = run_fixture_followup_search_reentry_loop(
        run_kernel=kernel,
        followup_search_intent_packet=chain["followup_packet"],
        fixture_candidates=[_fixture_candidate()],
        fixture_fetch_read_materials=[_failed_material()],
        mode="Balanced",
        analyst_repass_outcome="insufficient",
    )
    final_chain = {
        "kernel": kernel,
        "analysis_packet": reentry.analysis_packet,
    }
    final = _review_record(
        final_chain,
        mode="Balanced",
        review_pass_kind="final_verification",
        red_flag_context=True,
        followup_authorization_projection=kernel.state.projections[
            FOLLOWUP_SEARCH_AUTHORIZATION_STAGE
        ],
        followup_reentry_refs=_compact_reentry_ref(reentry),
        unresolved_component_posture=reentry.unresolved_component_posture,
    )
    result = _reduce_review(final_chain, final)
    issue_kinds = {issue["issue_kind"] for issue in result.review_projection["issues"]}

    assert result.review_projection["review_outcome"] == "contested"
    assert result.review_projection["contested"] is True
    assert "followup_attempt_unresolved" in issue_kinds
    assert reentry.semantic_admission_results == ()
    assert reentry.coverage_projection == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}


def test_fast_balanced_and_deep_mode_posture() -> None:
    chain = _supported_chain()

    fast = _review_record(chain, mode="Fast")
    assert fast["review_outcome"] == "not_applicable"
    assert fast["mode_policy"]["fast_scrutineer_default_enabled"] is False

    balanced_without_red_flag = _review_record(chain, mode="Balanced")
    assert balanced_without_red_flag["review_outcome"] == "not_applicable"
    assert balanced_without_red_flag["mode_policy"][
        "balanced_requires_red_flag_context"
    ] is True

    deep = _review_record(chain, mode="Deep", red_flag_context=True)
    assert deep["review_outcome"] == "signed_off"
    assert deep["mode_policy"]["deep_scrutineer_required_later"] is True
    assert deep["mode_policy"]["deep_orchestration_implemented"] is False


def test_closed_surfaces_static_guards_and_no_packet_sprawl() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "core.authoring",
        "core.scrutineer_remediation_handoff_contract",
        "core.scrutineer_remediation_runtime_handoff",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    forbidden_calls = {
        "authorize_followup_search",
        "authorize_semantic_observation_admission",
        "authorize_component_coverage_reduction",
        "run_fixture_followup_search_reentry_loop",
        "call_broker",
        "invoke_broker",
        "search_web",
        "retrieve",
        "dispatch_retrieval",
        "fetch_url",
        "read_url",
        "execute_author",
        "execute_author_action",
        "create_final_answer_packet",
        "derive_author_input_payload",
        "ask_model",
    }
    imports, calls, classes = _imports_calls_and_classes(RUNTIME_MODULE)
    assert imports.isdisjoint(forbidden_imports)
    assert calls.isdisjoint(forbidden_calls)
    assert not any(name.endswith("Packet") for name in classes)

    source = RUNTIME_MODULE.read_text(encoding="utf-8")
    assert "durable_packet" in source
    assert "proposal_packet" in source
    assert "SearchWorkPlan" not in source
    run_kernel_source = RUN_KERNEL_MODULE.read_text(encoding="utf-8")
    assert "SCRUTINEER_REVIEW_REDUCE" in run_kernel_source
    assert "SCRUTINEER_REVIEW_REDUCED" in run_kernel_source

    chain = _supported_chain()
    record = _review_record(chain, mode="Balanced", red_flag_context=True)
    result = _reduce_review(chain, record)
    assert result.review_projection["review_history"][0]["review_digest"] == (
        result.review_projection["review_digest"]
    )
    for value in result.review_projection["closed_surface_flags"].values():
        assert value is False
    assert result.review_projection["review_only"] is True
    assert result.review_projection["authorizes_search"] is False
    assert result.review_projection["creates_final_answer_packet"] is False
    assert result.review_projection["creates_author_input"] is False


def test_docs_record_scrutineer_review_posture() -> None:
    docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    required = (
        "AG-SCRUTINEER-REVIEW-01",
        "supervisory review/sign-off layer for Analyst work product",
        "not product authority",
        "does not authorize search",
        "does not run remediation",
        "Follow-up authorization remains RunKernel-owned",
        "initial review and final verification",
        "contested posture must be preserved",
        "Fast has no Scrutineer in MVP",
        "Balanced uses Scrutineer on red flags",
        "Deep requires Scrutineer later",
        "source-bound calculation Specialist MVP",
    )
    for phrase in required:
        assert phrase in docs_text
