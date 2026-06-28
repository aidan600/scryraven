from __future__ import annotations

import ast
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.live_search_validation_runtime import (
    LIVE_SEARCH_VALIDATION_OWNER,
    LIVE_SEARCH_VALIDATION_SCHEMA_VERSION,
    LiveSearchValidationRuntimeError,
    build_live_search_validation_observation_payload,
)
from core.run_kernel import (
    LIVE_SEARCH_VALIDATION_STAGE,
    Observation,
    ObservationType,
    RunKernelTransitionError,
    RunStageStatus,
)
from tests.test_ag_search_executor_handoff_01 import (
    _current_contract_kernel,
    _initial_only_kernel,
    _reduce_handoff,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "live_search_validation_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
    ROOT / "docs" / "codex" / "AG_LIVE_PLAN_01_BOUNDED_LIVE_VALIDATION_PLAN.md",
)

FALSE_FLAGS = {
    "broker_invoked": False,
    "live_provider_called": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "fetch_read_executed": False,
    "fetch_read_retrieval_executed": False,
    "evidence_ledger_admitted": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "partial_answer_ready": False,
}


def _ready_kernel():
    kernel = _current_contract_kernel()
    _reduce_handoff(kernel)
    return kernel


def _selected_task_ids(kernel, *, count: int = 1) -> list[str]:
    tasks = kernel.state.search_executor_handoff_state["search_task_records"]
    return [task["search_task_id"] for task in tasks[:count]]


def _fake_results(
    kernel,
    *,
    count: int = 1,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    task_id = _selected_task_ids(kernel)[0]
    results = []
    for index in range(1, count + 1):
        payload = {
            "title": f"Official Example Permit Threshold {index}",
            "url": f"https://official.example.gov/permit/threshold-{index}",
            "domain": "official.example.gov",
            "snippet": "Official current threshold information.",
            "published_or_observed_date": "2026-01-01",
        }
        if extra:
            payload.update(extra)
        results.append(payload)
    return {task_id: results}


def _authorize_validation(
    kernel,
    *,
    selected: list[str] | None = None,
    provider: str | None = "serper",
    provider_call_cap: int = 2,
    results_per_task_cap: int = 2,
):
    return kernel.authorize_live_search_validation(
        selected_search_task_ids=selected or _selected_task_ids(kernel),
        provider_authorized=provider,
        provider_call_cap=provider_call_cap,
        results_per_task_cap=results_per_task_cap,
    )


def _validation_observation(
    kernel,
    action,
    *,
    provider_used: str = "serper",
    results: Mapping[str, list[dict[str, Any]]] | None = None,
) -> Observation:
    payload = build_live_search_validation_observation_payload(
        action=action,
        current_answer_contract=kernel.state.current_answer_contract,
        search_executor_handoff_state=kernel.state.search_executor_handoff_state,
        provider_used=provider_used,
        provider_results_by_task=results or _fake_results(kernel),
    )
    return Observation.from_action(
        action,
        observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )


def _reduce_validation(
    kernel,
    *,
    action=None,
    provider_used: str = "serper",
    results: Mapping[str, list[dict[str, Any]]] | None = None,
) -> None:
    authorized = action or _authorize_validation(kernel)
    kernel.reduce(
        _validation_observation(
            kernel,
            authorized,
            provider_used=provider_used,
            results=results,
        )
    )


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(_text(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


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


def test_live_search_validation_requires_current_contract() -> None:
    kernel = _initial_only_kernel()
    _reduce_handoff(kernel)

    with pytest.raises(RunKernelTransitionError, match="current_answer_contract"):
        _authorize_validation(kernel)

    assert kernel.state.live_search_validation_state == {}
    assert kernel.state.live_search_validation_projection == {}
    assert kernel.state.live_search_validation_history == []


def test_live_search_validation_requires_search_executor_handoff() -> None:
    kernel = _current_contract_kernel()

    with pytest.raises(RunKernelTransitionError, match="SearchExecutorHandoff"):
        _authorize_validation(kernel, selected=["search-task:missing"])

    assert kernel.state.live_search_validation_state == {}
    assert kernel.state.live_search_validation_projection == {}
    assert kernel.state.live_search_validation_history == []


def test_live_search_validation_reduces_fake_candidates_to_state_projection_history() -> None:
    kernel = _ready_kernel()

    _reduce_validation(kernel)

    state = kernel.state.live_search_validation_state
    projection = kernel.state.live_search_validation_projection
    assert state["owner"] == LIVE_SEARCH_VALIDATION_OWNER
    assert state["schema_version"] == LIVE_SEARCH_VALIDATION_SCHEMA_VERSION
    assert state["run_id"] == kernel.state.run_id
    assert state["request_id"] == kernel.state.request_id
    assert state["authorized_action_id"]
    assert state["parent_current_contract_ref"]["contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert state["parent_search_executor_handoff_ref"]["handoff_digest"] == (
        kernel.state.search_executor_handoff_state["handoff_digest"]
    )
    assert state["selected_search_task_ids"] == _selected_task_ids(kernel)
    assert state["candidate_count"] == 1
    assert state["search_result_candidates"]
    assert state["not_live_executed_by_pr1"] is True
    assert state["fake_provider_used"] is True
    for key, expected in FALSE_FLAGS.items():
        assert state[key] is expected
        assert projection[key] is expected
    assert kernel.state.live_search_validation_history[-1] == projection
    assert kernel.state.projections[LIVE_SEARCH_VALIDATION_STAGE] == projection


def test_live_search_validation_rejects_stale_current_contract_digest() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel)
    observation = _validation_observation(kernel, action)
    payload = dict(observation.payload)
    payload["live_search_validation"]["parent_current_contract_ref"][
        "contract_digest"
    ] = "stale-current"
    tampered = Observation.from_action(
        action,
        observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="current_answer_contract"):
        kernel.reduce(tampered)

    assert kernel.state.live_search_validation_state == {}
    assert kernel.state.live_search_validation_projection == {}
    assert kernel.state.live_search_validation_history == []


def test_live_search_validation_rejects_stale_handoff_digest() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel)
    observation = _validation_observation(kernel, action)
    payload = dict(observation.payload)
    payload["live_search_validation"]["parent_search_executor_handoff_ref"][
        "handoff_digest"
    ] = "stale-handoff"
    tampered = Observation.from_action(
        action,
        observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="SearchExecutorHandoff"):
        kernel.reduce(tampered)

    assert kernel.state.live_search_validation_state == {}
    assert kernel.state.live_search_validation_projection == {}
    assert kernel.state.live_search_validation_history == []


def test_live_search_validation_rejects_unselected_or_unknown_task_id() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel)
    observation = _validation_observation(kernel, action)
    payload = dict(observation.payload)
    candidate = payload["live_search_validation"]["search_result_candidates"][0]
    candidate["search_task_id"] = "search-task:unknown"
    tampered = Observation.from_action(
        action,
        observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="unselected search task"):
        kernel.reduce(tampered)

    assert kernel.state.live_search_validation_state == {}
    assert kernel.state.live_search_validation_projection == {}
    assert kernel.state.live_search_validation_history == []


def test_live_search_validation_rejects_provider_preference_hint_without_authorization() -> None:
    kernel = _ready_kernel()
    task = kernel.state.search_executor_handoff_state["search_task_records"][0]
    assert task["provider_preference_hint"] == "serper"

    with pytest.raises(RunKernelTransitionError, match="provider_authorized"):
        _authorize_validation(kernel, provider=None)

    assert kernel.state.live_search_validation_state == {}


def test_live_search_validation_rejects_action_provider_mismatch() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel, provider="serper")
    observation = _validation_observation(
        kernel,
        action,
        provider_used="brave",
    )

    with pytest.raises(RunKernelTransitionError, match="provider_used"):
        kernel.reduce(observation)

    assert kernel.state.live_search_validation_state == {}


def test_live_search_validation_enforces_task_cap() -> None:
    kernel = _ready_kernel()
    task_id = _selected_task_ids(kernel)[0]

    with pytest.raises(RunKernelTransitionError, match="task count"):
        _authorize_validation(
            kernel,
            selected=[task_id, "search-task:extra:2", "search-task:extra:3"],
        )

    assert kernel.state.live_search_validation_state == {}


def test_live_search_validation_enforces_provider_call_cap() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel, provider_call_cap=1)
    results = _fake_results(kernel, extra={"provider_call_index": 2})
    observation = _validation_observation(kernel, action, results=results)

    with pytest.raises(RunKernelTransitionError, match="provider_call_cap"):
        kernel.reduce(observation)

    assert kernel.state.live_search_validation_state == {}


def test_live_search_validation_enforces_results_per_task_cap() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel, results_per_task_cap=1)
    observation = _validation_observation(
        kernel,
        action,
        results=_fake_results(kernel, count=2),
    )

    with pytest.raises(RunKernelTransitionError, match="results_per_task_cap"):
        kernel.reduce(observation)

    assert kernel.state.live_search_validation_state == {}


def test_live_search_validation_candidates_are_sanitized() -> None:
    kernel = _ready_kernel()

    _reduce_validation(kernel)

    candidate = kernel.state.live_search_validation_state[
        "search_result_candidates"
    ][0]
    for key in ("title", "url", "domain", "snippet"):
        assert candidate[key]
    forbidden_keys = {
        "raw_provider_payload",
        "raw_search_response",
        "api_key",
        "auth_headers",
        "private_logs",
        "raw_prompt",
        "model_response",
        "full_trace",
        "db_row",
        "content_fetched_from_url",
    }
    assert _all_keys(candidate).isdisjoint(forbidden_keys)
    assert candidate["raw_provider_payload_retained"] is False
    assert candidate["raw_search_response_retained"] is False
    assert candidate["fetch_read_executed"] is False


def test_live_search_validation_rejects_raw_payload_or_closed_authority_fields() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel)

    with pytest.raises(LiveSearchValidationRuntimeError):
        build_live_search_validation_observation_payload(
            action=action,
            current_answer_contract=kernel.state.current_answer_contract,
            search_executor_handoff_state=(
                kernel.state.search_executor_handoff_state
            ),
            provider_used="serper",
            provider_results_by_task=_fake_results(
                kernel,
                extra={"raw_provider_payload": {"private": True}},
            ),
        )

    observation = _validation_observation(kernel, action)
    payload = dict(observation.payload)
    payload["live_search_validation"].update(
        {
            "raw_search_response": {"private": True},
            "evidence_ledger_admission": {"claim": "not allowed"},
            "citation_eligible": True,
            "source_obligation_satisfied": True,
            "final_answer_packet_created": True,
            "author_input_created": True,
            "partial_answer_ready": True,
        }
    )
    tampered = Observation.from_action(
        action,
        observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError):
        kernel.reduce(tampered)

    assert kernel.state.live_search_validation_state == {}
    assert kernel.state.live_search_validation_projection == {}
    assert kernel.state.live_search_validation_history == []


def test_live_search_validation_does_not_activate_fetch_read_evidence_citation_sufficiency_fap_author() -> None:
    kernel = _ready_kernel()
    evidence_before = kernel.state.evidence_ledger.to_projection().to_dict()
    citation_before = deepcopy(kernel.state.followup_citation_eligibility_history)
    sufficiency_before = deepcopy(kernel.state.sufficiency_judgment)
    final_packet_before = deepcopy(kernel.state.final_answer_packet)
    author_before = deepcopy(kernel.state.author_observation)

    _reduce_validation(kernel)

    assert kernel.state.evidence_ledger.to_projection().to_dict() == evidence_before
    assert kernel.state.followup_citation_eligibility_history == citation_before
    assert kernel.state.sufficiency_judgment == sufficiency_before
    assert kernel.state.final_answer_packet == final_packet_before
    assert kernel.state.author_observation == author_before
    for key, expected in FALSE_FLAGS.items():
        assert kernel.state.live_search_validation_state[key] is expected


def test_live_search_validation_rejects_duplicate_context() -> None:
    kernel = _ready_kernel()
    _reduce_validation(kernel)

    action = _authorize_validation(kernel)
    observation = _validation_observation(kernel, action)

    with pytest.raises(RunKernelTransitionError, match="duplicate live search validation"):
        kernel.reduce(observation)


def test_live_search_validation_rejects_tampered_candidate_digest() -> None:
    kernel = _ready_kernel()
    action = _authorize_validation(kernel)
    observation = _validation_observation(kernel, action)
    payload = dict(observation.payload)
    candidate = payload["live_search_validation"]["search_result_candidates"][0]
    candidate["candidate_digest"] = "0" * 64
    tampered = Observation.from_action(
        action,
        observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="SearchResultCandidate"):
        kernel.reduce(tampered)

    assert kernel.state.live_search_validation_state == {}


def test_static_closed_surface_guard_for_live_search_validation() -> None:
    forbidden_imports = {
        "core.run_kernel",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.evidence_ledger_admission_runtime",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.citations",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    assert _imports(RUNTIME_MODULE).isdisjoint(forbidden_imports)
    source = _text(RUNTIME_MODULE)
    for token in (
        "SERPER_API_KEY",
        "API key",
        "requests.",
        "httpx.",
        "openai.",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "fetch_linkup_precision_block",
        "execute_author_action(",
        "build_citation",
        "EvidenceLedger(",
    ):
        assert token not in source, token
    kernel_text = _text(RUN_KERNEL)
    assert "LIVE_SEARCH_VALIDATE" in kernel_text
    assert "LIVE_SEARCH_VALIDATED" in kernel_text

    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", str(PIPELINE.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert diff.stdout.strip() == ""


def test_docs_use_merge_stable_live_search_validation_01a_posture() -> None:
    required = (
        "AG-LIVE-XAXIS-VALIDATION-01A",
        "current_answer_contract",
        "SearchExecutorHandoff",
        "sanitized SearchResultCandidate records only",
        "fetch/read",
        "EvidenceLedger",
        "citations",
        "source-obligation satisfaction",
        "Sufficiency",
        "FinalAnswerPacket",
        "Author",
        "partial-answer readiness",
        "product correctness",
        "provider_preference_hint is only a hint",
    )
    forbidden = (
        "SearchResultCandidate records are evidence",
        "provider_preference_hint authorizes",
        "01A satisfies source obligations",
        "01A creates citations",
        "01A prepares FinalAnswerPacket",
        "01A makes partial answers ready",
    )
    for path in DOCS:
        text = " ".join(_text(path).replace("`", "").split())
        for needle in required:
            assert needle in text, (path, needle)
        for needle in forbidden:
            assert needle not in text, (path, needle)
