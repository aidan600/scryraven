from __future__ import annotations

import ast
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.evidence_ledger_lifecycle import (
    reduce_fetch_read_content_packet_into_evidence_ledger,
)
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
)
from core.run_kernel import RunKernelTransitionError
from scripts import ag_live_semantic_support_coverage_01 as harness
from tests.test_ag_fetch_read_content_reference_01 import _readable_material
from tests.test_ag_search_executor_handoff_01 import _initial_only_kernel
from tests.test_ag_search_result_candidate_packet_01 import _packet_from_state

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ag_live_semantic_support_coverage_01.py"
DOC = ROOT / "docs" / "architecture" / "AG_LIVE_SEMANTIC_SUPPORT_COVERAGE_01.md"

SUPPORT_TEXT = (
    "Passport Fees Travel.gov Adult Applicants age 16 and older. "
    "Renewal customers for a U.S. passport book pay the passport book fee $130. "
    "This bounded sanitized text is only a component-under-test source excerpt."
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _read_json(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _source_survival_packet(*, result: str = "source_survival_pass") -> dict[str, Any]:
    return {
        "packet_kind": "source_survival_packet",
        "phase": "AG-LIVE-SOURCE-SURVIVAL-FETCH-READ-CUSTODY-01",
        "mode": "PROOF",
        "selected_source_survived": result,
        "selected_candidate": {
            "rank": 1,
            "domain": "travel.state.gov",
            "url": "https://travel.state.gov/en/passports/apply/help/fees.html",
            "title": "Passport Fees",
        },
        "fetch_read_calls_attempted": 1,
        "fetch_read_calls_completed": 1,
        "final_domain": "travel.state.gov",
        "http_status_class": "2xx",
        "content_type": "text/html",
        "evidence_ledger_candidate_content_custody_count": 1,
        "raw_html_retained": False,
        "raw_response_headers_retained": False,
        "raw_cookies_retained": False,
        "raw_page_text_retained": False,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def _fixture_inputs(
    tmp_path: Path,
    *,
    bounded_text: str = SUPPORT_TEXT,
    source_survival_result: str = "source_survival_pass",
) -> dict[str, Any]:
    _candidate_kernel, candidate_packet = _packet_from_state(candidate_count=1)
    kernel = _initial_only_kernel()
    material = _readable_material(
        candidate_packet,
        extra={
            "bounded_text": bounded_text,
            "bounded_text_char_count": len(bounded_text),
            "content_title": "Passport Fees",
        },
    )
    fetch_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [material],
    )
    ledger_projection = reduce_fetch_read_content_packet_into_evidence_ledger(
        run_kernel=kernel,
        fetch_read_content_packet=fetch_packet,
        observation_id=f"{candidate_packet['run_id']}:evidence-ledger:ag-live-semantic-support",
    )
    reference = dict(fetch_packet["reference_records"][0])
    source = _source_survival_packet(result=source_survival_result)
    input_dir = tmp_path / "prior-358"
    paths = {
        "source_survival_packet": _write_json(
            input_dir / "source_survival_packet.json",
            source,
        ),
        "fetch_read_content_packet": _write_json(
            input_dir / "fetch_read_content_packet.json",
            fetch_packet,
        ),
        "sanitized_content_reference": _write_json(
            input_dir / "sanitized_content_reference.json",
            reference,
        ),
        "evidence_ledger_projection": _write_json(
            input_dir / "evidence_ledger_projection.json",
            ledger_projection,
        ),
    }
    return {
        "kernel": kernel,
        "paths": paths,
        "source": source,
        "fetch_packet": fetch_packet,
        "reference": reference,
        "ledger_projection": ledger_projection,
    }


def _prepare(tmp_path: Path, fixture: Mapping[str, Any]) -> dict[str, Any]:
    paths = fixture["paths"]
    return harness.prepare_request(
        source_survival_packet_path=paths["source_survival_packet"],
        fetch_read_content_packet_path=paths["fetch_read_content_packet"],
        sanitized_content_reference_path=paths["sanitized_content_reference"],
        evidence_ledger_projection_path=paths["evidence_ledger_projection"],
        output_dir=tmp_path / "out",
    )


def _reduce(
    tmp_path: Path,
    fixture: Mapping[str, Any],
    *,
    confirm: bool = True,
    run_kernel: Any | None = None,
) -> dict[str, Any]:
    paths = fixture["paths"]
    return harness.reduce_semantic_coverage(
        source_survival_packet_path=paths["source_survival_packet"],
        fetch_read_content_packet_path=paths["fetch_read_content_packet"],
        sanitized_content_reference_path=paths["sanitized_content_reference"],
        evidence_ledger_projection_path=paths["evidence_ledger_projection"],
        output_dir=tmp_path / "out",
        confirm_semantic_coverage=confirm,
        run_kernel=run_kernel,
    )


def _imports_and_calls(path: Path) -> tuple[set[str], set[str], list[ast.Assign]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    assignments: list[ast.Assign] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
        elif isinstance(node, ast.Assign):
            assignments.append(node)
    return imported, called, assignments


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()


def _support_bridge_result(tmp_path: Path, fixture: Mapping[str, Any]) -> Any:
    packet = _reduce(tmp_path, fixture, run_kernel=fixture["kernel"])
    assert packet["semantic_support_result"] == "semantic_support_coverage_pass"
    history = fixture["kernel"].state.semantic_observation_admission_history
    assert len(history) == 1
    return packet


def test_prepare_request_loads_358_paths_and_does_not_reduce_semantic_coverage(
    tmp_path: Path,
) -> None:
    fixture = _fixture_inputs(tmp_path)

    packet = _prepare(tmp_path, fixture)

    assert packet["packet_kind"] == "semantic_support_coverage_request_packet"
    assert packet["semantic_support_result"] == "validation_not_run_operator_blocked"
    assert packet["semantic_observation_attempted_count"] == 0
    assert packet["semantic_observation_admitted_count"] == 0
    assert packet["component_coverage_attempted_count"] == 0
    assert packet["component_coverage_reduced_count"] == 0
    assert (tmp_path / "out" / "request_packet.json").exists()
    assert (tmp_path / "out" / "request_packet.md").exists()


def test_missing_358_packet_fails_closed(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path)
    fixture["paths"]["source_survival_packet"].unlink()

    with pytest.raises(harness.SemanticSupportCoverageError) as exc_info:
        _prepare(tmp_path, fixture)

    assert exc_info.value.code == "input_packet_missing"
    assert exc_info.value.gate == "gate_1_load_358_source_survival_output"


def test_source_survival_must_be_source_survival_pass(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path, source_survival_result="source_survival_fail")

    with pytest.raises(harness.SemanticSupportCoverageError) as exc_info:
        _prepare(tmp_path, fixture)

    assert exc_info.value.code == "source_survival_must_pass"
    assert exc_info.value.gate == "gate_2_source_survival_pass"


def test_raw_retention_flags_must_be_false(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path)
    source = deepcopy(fixture["source"])
    source["raw_html_retained"] = True
    _write_json(fixture["paths"]["source_survival_packet"], source)

    with pytest.raises(harness.SemanticSupportCoverageError) as exc_info:
        _prepare(tmp_path, fixture)

    assert exc_info.value.code == "raw_retention_flag_must_be_false"


def test_reduce_command_requires_confirm_semantic_coverage(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path)

    with pytest.raises(harness.SemanticSupportCoverageError) as exc_info:
        _reduce(tmp_path, fixture, confirm=False)

    assert exc_info.value.code == "confirm_semantic_coverage_required"


def test_no_provider_search_broker_fetch_or_model_imports_or_calls_are_used() -> None:
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.author_execution_runtime",
        "dotenv",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "subprocess",
        "scripts.run_provider_proxy_broker_once",
    }
    forbidden_calls = {
        "run_pipeline",
        "call_broker",
        "invoke_broker",
        "search_web",
        "fetch_url",
        "fetch_page",
        "read_url",
        "retrieve",
        "dispatch_retrieval",
        "ask_model",
        "execute_author",
        "create_final_answer_packet",
    }

    imported, called, _assignments = _imports_and_calls(SCRIPT)

    assert imported.isdisjoint(forbidden_imports)
    assert called.isdisjoint(forbidden_calls)


def test_bounded_content_insufficient_returns_source_content_insufficient(
    tmp_path: Path,
) -> None:
    fixture = _fixture_inputs(
        tmp_path,
        bounded_text="Passport fees page without the target renewal amount.",
    )

    packet = _reduce(tmp_path, fixture, run_kernel=fixture["kernel"])

    assert packet["semantic_support_result"] == ("semantic_support_fail_source_content_insufficient")
    assert packet["first_failed_gate"] == ("gate_5_evidence_relative_analysis_proposal")
    assert packet["semantic_observation_attempted_count"] == 0
    assert packet["component_coverage_attempted_count"] == 0


def test_source_bound_bounded_content_fixture_admits_one_semantic_observation(
    tmp_path: Path,
) -> None:
    fixture = _fixture_inputs(tmp_path)

    packet = _reduce(tmp_path, fixture, run_kernel=fixture["kernel"])

    assert packet["semantic_support_result"] == "semantic_support_coverage_pass"
    assert packet["semantic_observation_attempted_count"] == 1
    assert packet["semantic_observation_admitted_count"] == 1
    assert packet["semantic_observation_id"]
    assert fixture["kernel"].state.semantic_observation_admission_history
    assert (tmp_path / "out" / "semantic_observation_projection.json").exists()


def test_semantic_support_packet_names_358_input_artifact_digests_accurately(
    tmp_path: Path,
) -> None:
    fixture = _fixture_inputs(tmp_path)

    packet = _reduce(tmp_path, fixture, run_kernel=fixture["kernel"])

    assert "prior_357_digest" not in packet
    assert "prior_358_digest" not in packet
    for key in packet:
        if key.startswith("prior_357"):
            encoded = json.dumps(packet[key], sort_keys=True)
            assert _file_digest(fixture["paths"]["source_survival_packet"]) not in encoded
            assert _file_digest(fixture["paths"]["fetch_read_content_packet"]) not in encoded
            assert _file_digest(fixture["paths"]["sanitized_content_reference"]) not in encoded
            assert _file_digest(fixture["paths"]["evidence_ledger_projection"]) not in encoded
    assert packet["prior_358_source_survival_packet_digest"] == _file_digest(fixture["paths"]["source_survival_packet"])
    assert packet["prior_358_fetch_read_content_packet_digest"] == _file_digest(
        fixture["paths"]["fetch_read_content_packet"]
    )
    assert packet["prior_358_sanitized_content_reference_digest"] == _file_digest(
        fixture["paths"]["sanitized_content_reference"]
    )
    assert packet["prior_358_evidence_ledger_projection_digest"] == _file_digest(
        fixture["paths"]["evidence_ledger_projection"]
    )


def test_component_coverage_reduction_requires_the_admitted_semantic_observation(
    tmp_path: Path,
) -> None:
    fixture = _fixture_inputs(tmp_path)
    paths = fixture["paths"]
    context = harness._load_and_validate_inputs(
        source_survival_packet_path=paths["source_survival_packet"],
        fetch_read_content_packet_path=paths["fetch_read_content_packet"],
        sanitized_content_reference_path=paths["sanitized_content_reference"],
        evidence_ledger_projection_path=paths["evidence_ledger_projection"],
    )
    proposal = harness._source_bound_support_proposal(context)
    assert proposal is not None
    analysis_packet = harness.build_evidence_relative_analysis_packet(
        evidence_ledger_projection=context["evidence_ledger_projection"],
        analyst_proposal_records=[proposal],
        current_answer_contract_ref=context["current_answer_contract_ref"],
        current_answer_contract_digest=context["current_answer_contract_digest"],
    )
    result = harness.admit_semantic_observations_from_analysis_support_findings(
        run_kernel=fixture["kernel"],
        evidence_relative_analysis_packet=analysis_packet,
        fetch_read_content_packet=context["fetch_read_content_packet"],
    )[0]

    fresh = _fixture_inputs(tmp_path / "fresh")

    with pytest.raises(RunKernelTransitionError, match="admitted SemanticObservation"):
        harness._reduce_component_coverage(
            run_kernel=fresh["kernel"],
            admission_result=result,
        )


def test_no_direct_runkernel_semantic_or_coverage_state_mutation_is_used() -> None:
    _imported, _called, assignments = _imports_and_calls(SCRIPT)
    targets = [ast.unparse(target) for item in assignments for target in item.targets]

    forbidden_fragments = (
        ".state.semantic_observation_admission_history",
        ".state.semantic_observation_admission_projection",
        ".state.component_coverage_state",
        ".state.component_coverage_projection",
    )
    assert not any(fragment in target for target in targets for fragment in forbidden_fragments)


def test_closed_surfaces_remain_closed_zero_after_pass(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path)

    packet = _reduce(tmp_path, fixture, run_kernel=fixture["kernel"])

    assert packet["citation_eligibility_decisions"] == 0
    assert packet["source_obligation_satisfaction_decisions"] == 0
    assert packet["sufficiency_fap_author_authorprose_count"] == 0
    assert packet["provider_search_calls"] == 0
    assert packet["broker_calls"] == 0
    assert packet["fetch_read_calls"] == 0
    assert packet["model_calls"] == 0
    assert fixture["kernel"].state.sufficiency_judgment == {}
    assert fixture["kernel"].state.final_answer_packet == {}
    assert fixture["kernel"].state.author_observation == {}


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "raw_html",
        "headers",
        "unbounded_text",
        "answer_text",
        "citations",
        "final_answer_packet",
        "author_material",
        "prompt",
        "model_response",
        "provider_payload",
        "secret",
    ],
)
def test_output_rejects_raw_unbounded_answer_citation_fap_author_prompt_model_provider_secret_fields(
    tmp_path: Path,
    forbidden_key: str,
) -> None:
    fixture = _fixture_inputs(tmp_path)
    packet = _prepare(tmp_path, fixture)
    spoofed = deepcopy(packet)
    spoofed[forbidden_key] = "forbidden"

    with pytest.raises(harness.SemanticSupportCoverageError):
        harness.validate_review_packet(spoofed)


def test_no_live_network_is_run_in_pytest_or_ci(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path)

    packet = _prepare(tmp_path, fixture)

    assert packet["provider_search_calls"] == 0
    assert packet["broker_calls"] == 0
    assert packet["fetch_read_calls"] == 0
    assert packet["model_calls"] == 0
    source = SCRIPT.read_text(encoding="utf-8")
    assert "urllib" not in source
    assert "requests" not in source
    assert "httpx" not in source
    assert "--confirm-semantic-coverage" in source


def test_cli_path_reports_first_broken_runkernel_consumer_seam(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path)

    packet = _reduce(tmp_path, fixture, run_kernel=None)

    assert packet["semantic_support_result"] == ("semantic_support_fail_semantic_observation_admission")
    assert packet["first_failed_gate"] == "gate_6_semantic_observation_admission"
    assert packet["semantic_observation_attempted_count"] == 1
    assert packet["semantic_observation_admitted_count"] == 0
    assert packet["component_coverage_reduced_count"] == 0


def test_output_contains_no_forbidden_material_after_pass(tmp_path: Path) -> None:
    fixture = _fixture_inputs(tmp_path)
    packet = _reduce(tmp_path, fixture, run_kernel=fixture["kernel"])

    forbidden = {
        "raw_html",
        "raw_page_text",
        "unbounded_text",
        "answer_text",
        "citations",
        "final_answer_packet",
        "author_material",
        "prompt",
        "model_response",
        "provider_payload",
        "secret",
    }
    assert _all_keys(packet).isdisjoint(forbidden)
    assert "bounded_text" not in json.dumps(packet, sort_keys=True)


def test_docs_record_proof_mode_caps_non_proofs_and_next_checkpoint() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = (
        "Mode: PROOF",
        "NO-BUT-JUSTIFIED",
        "PR #357",
        "PR #358",
        "provider/search/broker calls: 0",
        "URL fetch/read calls: 0",
        "model calls: 0",
        "adult U.S. passport book renewal fee",
        "SemanticObservation",
        "ComponentCoverage",
        "Explicit Non-Proofs",
        "mandatory next Build/product checkpoint",
    )
    for needle in required:
        assert needle in text
