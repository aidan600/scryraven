from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.component_coverage_record import (
    ContentAvailabilityStatus,
    CoverageState,
    CurrentnessPosture,
    EvidenceBasis,
    EvidenceCustodyStatus,
    FollowupNeed,
    SemanticSupportStatus,
    SourceObligationStatus,
)
from core.evidence_relative_analysis_packet import build_evidence_relative_analysis_packet
from core.run_kernel import RunKernelTransitionError
from core.semantic_observation_admission_bridge import (
    SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER,
    SemanticObservationAdmissionBridgeError,
    admit_semantic_observations_from_analysis_support_findings,
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
    _coverage_record,
    _reduce_coverage,
)

ROOT = Path(__file__).resolve().parents[1]
THIS_TEST = ROOT / "tests" / "test_ag_semantic_observation_admission_bridge_01.py"
BRIDGE_MODULE = ROOT / "core" / "semantic_observation_admission_bridge.py"
DOCS = (
    ROOT / "docs" / "architecture" / "AG_DOC_SEMANTIC_COVERAGE_CHECKPOINT_01.md",
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "architecture" / "AG_SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_01.md",
)


def _support_finding(packet: Mapping[str, Any]) -> dict[str, Any]:
    return next(
        dict(finding)
        for finding in packet["analyst_report"]["findings"]
        if finding["proposal_kind"] == "possible_support_proposal"
    )


def _non_support_finding(packet: Mapping[str, Any]) -> dict[str, Any]:
    return next(
        dict(finding)
        for finding in packet["analyst_report"]["findings"]
        if finding["proposal_kind"] != "possible_support_proposal"
    )


def _bridge(chain: Mapping[str, Any], *, finding_id: str | None = None):
    return admit_semantic_observations_from_analysis_support_findings(
        run_kernel=chain["kernel"],
        evidence_relative_analysis_packet=chain["analysis_packet"],
        fetch_read_content_packet=chain["fetch_read_packet"],
        finding_ids=(finding_id,) if finding_id else (),
    )[0]


def _bridge_coverage_record(chain: Mapping[str, Any], result: Any):
    return _coverage_record(
        kernel=chain["kernel"],
        record_id="coverage:ag-semantic-observation-admission-bridge:supportable",
        coverage_state=CoverageState.SUPPORTED_WITH_CAVEATS,
        semantic_support_status=SemanticSupportStatus.SUPPORTED,
        source_obligation_status=SourceObligationStatus.PARTIAL,
        content_availability_status=ContentAvailabilityStatus.AVAILABLE,
        evidence_custody_status=EvidenceCustodyStatus.CUSTODIED,
        evidence_basis=(
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        observation=result.semantic_observation,
        content_ref=result.sanitized_content_reference,
        remaining_unknowns=(
            "source-obligation candidate ids remain lineage only",
            "blocked/follow-up gap lineage remains downstream",
        ),
        followup_need=FollowupNeed.OPTIONAL,
        currentness_posture=CurrentnessPosture.CURRENT,
        metadata={
            "semantic_observation_admission_bridge": (
                SEMANTIC_OBSERVATION_ADMISSION_BRIDGE_HELPER
            ),
            "analyst_finding_id": result.analyst_finding["finding_id"],
        },
    ).require_valid()


def _packet_with_proposal_kind(kind: str) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    kernel, fetch_read_packet, projection = _analysis_fixture(
        readable_count=1,
        failed_count=0,
    )
    record = _records_by_status(projection, "readable")[0]
    proposal = _support_proposal(record)
    proposal["proposal_kind"] = kind
    if kind == "analysis_gap":
        proposal.update(
            _analysis_gap_proposal(
                record,
                "analysis_gap",
                direction="Keep this as proposal-only gap structure.",
            )
        )
    contract_ref = _contract_ref_from_projection(projection)
    packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[proposal],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    return kernel, fetch_read_packet, packet


def _imports_and_calls(path: Path) -> tuple[set[str], set[str], set[str]]:
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


def test_valid_support_finding_admits_semantic_observation_through_runkernel() -> None:
    chain = _chain_fixture()
    support = _support_finding(chain["analysis_packet"])
    kernel = chain["kernel"]

    assert kernel.state.semantic_observation_admission_history == []
    result = _bridge(chain, finding_id=support["finding_id"])
    payload = result.to_dict()

    assert payload["durable_packet"] is False
    assert payload["source_analyst_finding_id"] == support["finding_id"]
    assert payload["source_analyst_finding_digest"] == support["finding_digest"]
    assert payload["admission_action_id"] == (
        kernel.state.semantic_observation_admission_projection["authorized_action_id"]
    )
    assert payload["admission_status"] == "admitted"
    assert len(kernel.state.semantic_observation_admission_history) == 1
    assert (
        kernel.state.semantic_observation_admission_projection["observation_id"]
        == result.semantic_observation.observation_id
    )
    assert result.semantic_observation.contract_digest == (
        kernel.state.initial_answer_contract["accepted_contract_digest"]
    )
    assert payload["current_answer_contract_ref"]["contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert payload["accepted_contract_ref"]["contract_digest"] == (
        kernel.state.initial_answer_contract["accepted_contract_digest"]
    )
    _assert_downstream_closed(kernel)


def test_component_coverage_reduces_after_admitted_observation_not_before() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    support = _support_finding(chain["analysis_packet"])
    prebuilt_result = _bridge(chain, finding_id=support["finding_id"])
    record = _bridge_coverage_record(chain, prebuilt_result)

    fresh = _chain_fixture()
    fresh_record = _bridge_coverage_record(fresh, prebuilt_result)
    with pytest.raises(RunKernelTransitionError, match="admitted SemanticObservation"):
        _reduce_coverage(fresh["kernel"], fresh_record)

    projection = _reduce_coverage(kernel, record)

    assert projection["coverage_state"] == "supported_with_caveats"
    assert projection["semantic_support_status"] == "supported"
    assert projection["accepted_observation_refs"][0]["observation_id"] == (
        prebuilt_result.semantic_observation.observation_id
    )
    assert projection["content_reference_bindings"][0]["content_ref_id"] == (
        prebuilt_result.sanitized_content_reference.content_ref_id
    )
    assert projection["lineage"]["created_from"] == [
        "passive_component_coverage_record",
        "accepted_initial_answer_contract",
        "admitted_semantic_observation",
    ]
    _assert_downstream_closed(kernel, projection)


def test_analyst_possible_support_alone_cannot_create_component_coverage() -> None:
    chain = _chain_fixture()
    kernel = chain["kernel"]
    support = _support_finding(chain["analysis_packet"])

    assert support["proposal_kind"] == "possible_support_proposal"
    assert support["semantic_observation_admitted"] is False
    assert support["component_coverage_created"] is False
    with pytest.raises(RunKernelTransitionError, match="admitted SemanticObservation"):
        action = kernel.authorize_component_coverage_reduction(
            coverage_record_id="coverage:analyst-only",
            coverage_record_digest="digest",
            answer_component_id=support["component_id"],
            component_revision="1",
            component_digest=(
                kernel.state.initial_answer_contract["accepted_answer_component_refs"][0][
                    "component_digest"
                ]
            ),
        )
        assert action
    assert kernel.state.component_coverage_state == {}


@pytest.mark.parametrize(
    "proposal_kind",
    [
        "analysis_gap",
        "missing_fact",
        "possible_contradiction",
        "currentness_concern",
        "scope_mismatch",
        "apparent_relevance",
        "caveat_proposal",
    ],
)
def test_non_support_findings_are_rejected_as_admission_inputs(
    proposal_kind: str,
) -> None:
    kernel, fetch_read_packet, packet = _packet_with_proposal_kind(proposal_kind)
    finding = packet["analyst_report"]["findings"][0]

    with pytest.raises(
        SemanticObservationAdmissionBridgeError,
        match="not eligible|blocker/proposal|no eligible",
    ):
        admit_semantic_observations_from_analysis_support_findings(
            run_kernel=kernel,
            evidence_relative_analysis_packet=packet,
            fetch_read_content_packet=fetch_read_packet,
            finding_ids=(finding["finding_id"],),
        )
    assert kernel.state.semantic_observation_admission_history == []


def test_missing_contract_component_custody_or_content_lineage_fails_closed() -> None:
    kernel, fetch_read_packet, projection = _analysis_fixture(
        readable_count=1,
        failed_count=0,
    )
    record = _records_by_status(projection, "readable")[0]
    contract_ref = _contract_ref_from_projection(projection)
    valid_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[_support_proposal(record)],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )

    missing_contract = deepcopy(valid_packet)
    missing_contract.pop("current_answer_contract_ref")
    with pytest.raises(SemanticObservationAdmissionBridgeError):
        admit_semantic_observations_from_analysis_support_findings(
            run_kernel=kernel,
            evidence_relative_analysis_packet=missing_contract,
            fetch_read_content_packet=fetch_read_packet,
        )

    bad_component = _support_proposal(record)
    bad_component["component_id"] = "component:unknown"
    bad_component_packet = build_evidence_relative_analysis_packet(
        evidence_ledger_projection=projection,
        analyst_proposal_records=[bad_component],
        current_answer_contract_ref=contract_ref,
        current_answer_contract_digest=contract_ref["contract_digest"],
    )
    with pytest.raises(SemanticObservationAdmissionBridgeError, match="component"):
        admit_semantic_observations_from_analysis_support_findings(
            run_kernel=kernel,
            evidence_relative_analysis_packet=bad_component_packet,
            fetch_read_content_packet=fetch_read_packet,
        )

    kernel.state.evidence_ledger.fetch_read_candidate_custody.clear()
    with pytest.raises(SemanticObservationAdmissionBridgeError, match="custody"):
        admit_semantic_observations_from_analysis_support_findings(
            run_kernel=kernel,
            evidence_relative_analysis_packet=valid_packet,
            fetch_read_content_packet=fetch_read_packet,
        )

    chain = _chain_fixture()
    broken_content = deepcopy(chain["fetch_read_packet"])
    broken_content["reference_records"][0].pop("bounded_text")
    with pytest.raises(SemanticObservationAdmissionBridgeError):
        admit_semantic_observations_from_analysis_support_findings(
            run_kernel=chain["kernel"],
            evidence_relative_analysis_packet=chain["analysis_packet"],
            fetch_read_content_packet=broken_content,
        )
    assert chain["kernel"].state.semantic_observation_admission_history == []


def test_bridge_preserves_source_and_packet_lineage_without_satisfying_obligations() -> None:
    chain = _chain_fixture()
    result = _bridge(chain)
    payload = result.to_dict()
    finding = _support_finding(chain["analysis_packet"])

    assert payload["candidate_id"] == finding["candidate_id"]
    assert payload["candidate_digest"] == finding["candidate_digest"]
    assert payload["reference_id"] == finding["reference_id"]
    assert payload["reference_digest"] == finding["reference_digest"]
    assert payload["fetch_read_content_packet_ref"]["packet_digest"] == (
        finding["fetch_read_content_packet_digest"]
    )
    assert payload["evidence_ledger_ref"]["projection_digest"] == (
        chain["analysis_packet"]["evidence_ledger_projection_digest"]
    )
    assert payload["fetch_read_candidate_custody_ref"]["projection_digest"] == (
        finding["evidence_ledger_custody_projection_ref"]["projection_digest"]
    )
    assert payload["source_obligation_candidate_ids"] == [
        "obligation:official-current"
    ]
    assert payload["source_obligation_candidate_ids_are_lineage_only"] is True
    assert payload["closed_downstream_flags"]["source_obligation_satisfied"] is False
    assert payload["closed_downstream_flags"]["citation_eligible"] is False
    assert "final_answer_packet" not in json.dumps(payload["admission_status"])


def test_followup_search_intent_remains_proposal_only_and_gap_lineage_downstream() -> None:
    chain = _chain_fixture()
    followup_packet = chain["followup_packet"]
    gap_finding = _non_support_finding(chain["analysis_packet"])
    proposal = next(
        item
        for item in followup_packet["analysis_gap_search_proposals"]
        if item["source_gap_id"]
        in {
            gap.get("gap_id")
            for gap in chain["analysis_packet"]["analyst_report"][
                "analysis_gap_proposals"
            ]
        }
    )

    result = _bridge(chain)

    assert gap_finding["proposal_kind"] == "analysis_gap"
    assert proposal["authorized"] is False
    assert proposal["query_plan_created"] is False
    assert proposal["search_dispatched"] is False
    assert proposal["component_coverage_created"] is False
    assert "downstream" in result.semantic_observation.candidate_followup_gaps[0]
    assert chain["kernel"].state.followup_authorization_state == {}


def test_no_sufficiency_fap_author_citation_or_product_correctness_state_is_created() -> None:
    chain = _chain_fixture()
    result = _bridge(chain)
    payload = result.to_dict()
    kernel = chain["kernel"]

    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert payload["closed_downstream_flags"]["sufficiency_decided"] is False
    assert payload["closed_downstream_flags"]["final_answer_packet_created"] is False
    assert payload["closed_downstream_flags"]["author_input_created"] is False
    assert payload["closed_downstream_flags"]["product_correctness_claimed"] is False
    assert payload["component_coverage_created_by_bridge"] is False


def test_static_import_and_call_guards_keep_bridge_out_of_closed_surfaces() -> None:
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
        "urllib",
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

    imported_names, called_names, class_names = _imports_and_calls(BRIDGE_MODULE)
    assert imported_names.isdisjoint(forbidden_imports)
    assert called_names.isdisjoint(forbidden_calls)
    assert not any(name.endswith("Packet") for name in class_names)

    imported_names, called_names, _class_names = _imports_and_calls(THIS_TEST)
    assert "core.pipeline_orchestrator" not in imported_names
    assert called_names.isdisjoint(forbidden_calls)


def test_docs_record_bridge_posture_and_remaining_downstream_gap() -> None:
    docs_text = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)
    required = (
        "AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01",
        "controlled promotion from Analyst support proposal to admitted SemanticObservation",
        "justified because ComponentCoverage consumes it immediately",
        "not a new durable proposal packet",
        "ComponentCoverage reduction remains separate",
        "source-obligation satisfaction",
        "citation eligibility",
        "Sufficiency",
        "FinalAnswerPacket",
        "Author input",
        "live search",
        "provider calls",
        "broker calls",
        "retrieval",
        "fetch/read",
        "model calls",
        "product correctness",
        "Blocked/follow-up gap-to-ComponentCoverage blocker lineage remains a downstream gap",
        "Next likely gate after this bridge is Scrutineer MVP",
    )
    for phrase in required:
        assert phrase in docs_text
