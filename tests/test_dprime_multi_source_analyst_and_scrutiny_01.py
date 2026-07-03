"""PRODUCT-PATH-REGRESSION: multi-source D-prime Analyst + Scrutineer gate.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: python -m proplex --live-semantic-coverage-status-dry-run
Runtime consumer: proplex.live_semantic_coverage_status consuming core.dprime_multi_source_analyst_scrutiny_runtime
Why ordinary product-path work cannot be done directly: live/model/provider/
search/fetch/read/retrieval calls are closed, so the ordinary status path uses
retained offline artifacts and injected fake D-prime review callables.
Integration deadline: current phase.
Exit condition: keep as the regression guard for product-consumed generic
multi-source D-prime relation intake and the narrow deterministic Scrutineer
challenge gate.
Why this is not a shadow product path: it invokes the ordinary product status
builder, existing D-prime relation intake, RunKernel admission/materialization,
ComponentCoverage, source/citation authority, FAP, AuthorProse, and citation
display reducers instead of a detached multi-source helper.
Forbidden interpretation: multi-source posture and the narrow Scrutineer gate
are not product correctness, full Scrutineer remediation, Economist/Specialist
routing, multi-component synthesis, live validation, or an alternate answer
path.
"""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from typing import Any, Mapping

from core.dprime_multi_source_analyst_scrutiny_runtime import (
    BLOCKED_DPRIME_MULTI_SOURCE_CONFLICT_UNRESOLVED,
    BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING,
    BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_GATE_MISSING,
)
from proplex.live_citation_source_obligation_readiness_status import (
    PASS_DECISION,
    build_live_citation_source_obligation_readiness_status,
)
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status
from tests.test_ag_semantic_coverage_product_consumption_01 import (
    _passport_retained_repo,
)
from tests.test_dprime_generic_analyst_intake_and_relations_01 import (
    GENERIC_COMPONENT_ID,
    GENERIC_OBLIGATION_ID,
    GENERIC_QUERY,
    GENERIC_TEXT,
    _fake_review,
    _generic_assessment_payload,
    _generic_followup_candidates,
    _generic_followup_materials,
    _generic_retained_repo,
)
from tests.test_dprime_model_review_assessment_slice_01 import _license

ROOT = Path(__file__).resolve().parents[1]
STATUS_MODULE = ROOT / "proplex" / "live_semantic_coverage_status.py"
MULTI_SOURCE_RUNTIME = ROOT / "core" / "dprime_multi_source_analyst_scrutiny_runtime.py"
SUPPORT_BUNDLE_RUNTIME = ROOT / "core" / "dprime_evidence_support_bundle_runtime.py"
SOURCE_CITATION_RUNTIME = (
    ROOT / "core" / "dprime_source_obligation_citation_authority_runtime.py"
)
FETCH_READ_PACKET = (
    "output/ag_live_source_survival_fetch_read_01/fetch_read_content_packet.json"
)
SECOND_SOURCE_TEXT = (
    "A second Example County official schedule also states that the "
    "small-claims filing fee for the example case type is $42."
)


def test_existing_single_source_and_followup_paths_remain_passes(tmp_path: Path) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path / "direct")

    direct = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("directly_supports"),
    )

    assert direct.decision == PASS_DECISION, direct.payload.get("blocker_detail")
    assert direct.payload["dprime_answer_path_ref"]["status"] == "consumed"
    assert (
        direct.payload.get(
            "dprime_multi_source_posture_consumed_by_product_status",
            False,
        )
        is False
    )
    assert direct.payload["answerability_correctness"] == "not claimed"

    followup_root, _candidate = _generic_retained_repo(tmp_path / "followup")
    followup = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=followup_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("currentness_mismatch"),
        dprime_followup_search_reentry_enabled=True,
        dprime_followup_candidate_results=_generic_followup_candidates(),
        dprime_followup_fetch_read_materials=_generic_followup_materials(),
        dprime_followup_second_pass_model_review_callable=_fake_review(
            "directly_supports"
        ),
    )

    assert followup.decision == PASS_DECISION, followup.payload.get("blocker_detail")
    assert followup.payload["dprime_answer_path_ref"]["status"] == "consumed"
    assert followup.payload["dprime_followup_search_reentry_ref"]["status"] == (
        "ordinary_search_reentry_to_answer_path_consumed"
    )


def test_compatible_multi_source_relations_reach_product_citation_display(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path / "base")
    extra = _additional_relation_input(
        tmp_path,
        suffix="second-source",
        domain="example-county-records.invalid",
    )

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("directly_supports"),
        dprime_multi_source_relation_inputs=[extra],
    )

    assert result.decision == PASS_DECISION, result.payload.get("blocker_detail")
    assert result.payload["dprime_multi_source_relation_count"] == 2
    assert result.payload["dprime_multi_source_source_count"] == 2
    assert result.payload["dprime_multi_source_posture_consumed_by_product_status"]
    assert result.payload["dprime_multi_source_scrutineer_consumed_by_product_status"]
    assert result.payload["dprime_multi_source_answer_path_allowed"] is True
    assert result.payload["dprime_multi_source_relation_set_ref"]["status"] == (
        "consumed"
    )
    assert result.payload["dprime_multi_source_support_posture_ref"][
        "conflict_posture"
    ] == "none"
    assert result.payload["dprime_scrutineer_challenge_ref"]["status"] == "passed"
    assert result.payload["dprime_scrutineer_challenge_ref"]["challenge_kind"] == (
        "none"
    )
    assert result.payload["dprime_answer_path_ref"]["status"] == "consumed"
    display = result.payload["dprime_answer_path_ref"]["citation_source_display"]
    assert display["status"] == "created"
    assert display["rendered_source_count"] == 2
    assert len(display["citation_source_entries"]) == 2
    assert result.payload["answerability_correctness"] == "not claimed"
    assert result.payload["dprime_status"]["objects_created"][
        "multi_source_additional_semantic_observations"
    ] is True
    assert result.payload["dprime_status"]["objects_created"]["component_coverage"]
    assert result.payload["dprime_status"]["objects_created"]["final_answer_packet"]
    assert "D-prime multi-source relation set status: consumed" in result.output
    assert "D-prime Scrutineer gate status: passed" in result.output


def test_contradictory_multi_source_relation_blocks_before_answer_path(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path / "base")
    extra = _additional_relation_input(
        tmp_path,
        suffix="contradiction",
        domain="example-county-audit.invalid",
        support_relation="contradicts",
    )

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("directly_supports"),
        dprime_multi_source_relation_inputs=[extra],
    )

    assert result.decision == BLOCKED_DPRIME_MULTI_SOURCE_CONFLICT_UNRESOLVED
    assert result.payload["component_coverage_ref"]["status"] == (
        "blocked_by_multi_source_scrutineer"
    )
    assert result.payload["dprime_multi_source_support_posture_ref"][
        "conflict_posture"
    ] == "present"
    assert result.payload["dprime_multi_source_answer_path_allowed"] is False
    assert result.payload["dprime_scrutineer_challenge_ref"]["status"] == (
        "challenged"
    )
    assert result.payload["dprime_scrutineer_challenge_ref"][
        "challenge_kind"
    ] == "contradiction"
    objects = result.payload["dprime_status"]["objects_created"]
    assert objects["multi_source_relation_set"] is True
    assert objects["multi_source_support_posture"] is True
    assert objects["component_coverage"] is False
    assert objects.get("final_answer_packet", False) is False
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"
    assert "D-prime Scrutineer gate status: challenged" in result.output


def test_multi_source_path_blocks_when_scrutineer_gate_is_not_consumed(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path / "base")
    extra = _additional_relation_input(
        tmp_path,
        suffix="gate-missing",
        domain="example-county-ordinance.invalid",
    )

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("directly_supports"),
        dprime_multi_source_relation_inputs=[extra],
        dprime_multi_source_scrutineer_enabled=False,
    )

    assert result.decision == BLOCKED_DPRIME_MULTI_SOURCE_SCRUTINEER_GATE_MISSING
    assert result.payload["dprime_multi_source_posture_consumed_by_product_status"]
    assert result.payload["dprime_multi_source_scrutineer_consumed_by_product_status"]
    assert result.payload["dprime_multi_source_answer_path_allowed"] is False
    assert result.payload["dprime_scrutineer_challenge_ref"]["status"] == "blocked"
    assert result.payload["component_coverage_ref"]["status"] == (
        "blocked_by_multi_source_scrutineer"
    )
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"


def test_multi_source_rejects_cross_component_relation_set(tmp_path: Path) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path / "base")
    extra = _additional_relation_input(
        tmp_path,
        suffix="wrong-component",
        domain="neighbor-county.invalid",
        component_id="component:neighbor-county-small-claims-filing-fee",
        review_component_id="component:neighbor-county-small-claims-filing-fee",
    )

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("directly_supports"),
        dprime_multi_source_relation_inputs=[extra],
    )

    assert result.decision == BLOCKED_DPRIME_MULTI_SOURCE_RELATION_SET_MISSING
    assert result.payload["dprime_answer_path_ref"]["status"] == "not reached"
    assert result.payload["dprime_status"]["objects_created"]["component_coverage"] is (
        False
    )


def test_multi_source_output_hygiene_and_static_closed_surfaces(
    tmp_path: Path,
) -> None:
    repo_root, _candidate = _generic_retained_repo(tmp_path / "base")
    extra = _additional_relation_input(
        tmp_path,
        suffix="hygiene",
        domain="example-county-board.invalid",
    )

    result = build_live_semantic_coverage_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
        dprime_model_review_license=_license(),
        dprime_model_review_callable=_fake_review("directly_supports"),
        dprime_multi_source_relation_inputs=[extra],
    )
    serialized = json.dumps(result.payload, sort_keys=True)

    for forbidden in (
        "bounded_text",
        GENERIC_TEXT,
        SECOND_SOURCE_TEXT,
        "api_key",
        "secret",
        "product correctness claimed: true",
    ):
        assert forbidden not in serialized
        assert forbidden not in result.output
    for forbidden_output in (
        "raw prompt:",
        "raw model response:",
        "provider payload:",
    ):
        assert forbidden_output not in result.output.casefold()
    assert result.payload["answerability_correctness"] == "not claimed"
    assert result.payload["dprime_scrutineer_challenge_ref"][
        "product_correctness_claimed"
    ] is False

    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "openai",
        "requests",
        "httpx",
        "dotenv",
        "subprocess",
    }
    forbidden_calls = {
        "run_pipeline",
        "search_web",
        "retrieve",
        "dispatch_retrieval",
        "fetch_url",
        "fetch_page",
        "read_url",
        "ask_model",
    }
    for path in (
        STATUS_MODULE,
        MULTI_SOURCE_RUNTIME,
        SUPPORT_BUNDLE_RUNTIME,
        SOURCE_CITATION_RUNTIME,
    ):
        imported, called = _imports_and_calls(path)
        assert imported.isdisjoint(forbidden_imports)
        assert called.isdisjoint(forbidden_calls)


def _additional_relation_input(
    tmp_path: Path,
    *,
    suffix: str,
    domain: str,
    support_relation: str = "directly_supports",
    component_id: str = GENERIC_COMPONENT_ID,
    review_component_id: str = GENERIC_COMPONENT_ID,
    source_obligation_id: str = GENERIC_OBLIGATION_ID,
) -> dict[str, Any]:
    repo_root, _candidate = _passport_retained_repo(
        tmp_path / f"extra-{suffix}",
        bounded_text=SECOND_SOURCE_TEXT,
        component_id=component_id,
        source_obligation_id=source_obligation_id,
        title=f"Example County Extra Fee Schedule {suffix}",
        url=f"https://{domain}/small-claims-fees-{suffix}",
        domain=domain,
        candidate_id=f"search-result-candidate:example-county-fee-{suffix}",
        candidate_digest=f"candidate-digest-example-county-fee-{suffix}",
        snippet="A second Example County official source lists a $42 fee.",
        published_or_observed_date="2026-07-01",
    )
    readiness = build_live_citation_source_obligation_readiness_status(
        query=GENERIC_QUERY,
        repo_root=repo_root,
    )
    assert readiness.decision == PASS_DECISION, readiness.payload.get(
        "blocker_detail"
    )
    fetch_packet = json.loads((repo_root / FETCH_READ_PACKET).read_text("utf-8"))
    return {
        "fetch_read_content_packet": fetch_packet,
        "source_evidence_admission_ref": readiness.payload[
            "source_evidence_admission_ref"
        ],
        "citation_source_obligation_readiness_ref": readiness.payload[
            "citation_source_obligation_readiness_ref"
        ],
        "component_ref": readiness.payload["component_ref"],
        "source_obligation_ref": readiness.payload["source_obligation_ref"],
        "model_review_callable": _review_for_component(
            support_relation,
            component_id=review_component_id,
        ),
    }


def _review_for_component(
    support_relation: str,
    *,
    component_id: str,
) -> Any:
    payload = _assessment_payload_for_component(
        support_relation,
        component_id=component_id,
    )

    def fake_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return payload

    return fake_review


def _assessment_payload_for_component(
    support_relation: str,
    *,
    component_id: str,
) -> dict[str, Any]:
    payload = copy.deepcopy(_generic_assessment_payload(support_relation))
    payload["answer_component_claim"]["component_id"] = component_id
    if support_relation == "contradicts":
        payload["support_relation"] = "contradicts"
        payload["contradiction_check"] = {"status": "contradicts"}
        payload["challenge_recommended"] = True
        payload["non_support_reason_when_not_direct"] = "fake contradiction"
    return payload


def _imports_and_calls(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return imported, called


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
