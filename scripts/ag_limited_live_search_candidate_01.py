from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import retained_live_artifact_preflight as retained_preflight  # noqa: E402
from core.contract_amendment_record import (  # noqa: E402
    AmendmentOperation,
    AmendmentOperationKind,
    AmendmentTriggerRefs,
    ContractAmendmentRecord,
    MaterialityPosture,
    ModePermissionPosture,
    MonotonicityPosture,
    ProposalDisposition,
    WeakeningPosture,
)
from core.live_search_validation_runtime import (  # noqa: E402
    LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP,
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
    LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
    LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP,
    build_live_search_validation_observation_payload,
)
from core.run_kernel import (  # noqa: E402
    Observation,
    ObservationType,
    RunKernel,
    RunStageStatus,
)
from core.search_executor_handoff_runtime import (  # noqa: E402
    SearchExecutorHandoffInput,
    execute_search_executor_handoff_action,
    planner_ref_from_search_planner_state,
)
from core.search_executor_handoff_runtime import (  # noqa: E402
    contract_ref_from_contract as handoff_contract_ref_from_contract,
)
from core.search_planner_runtime import (  # noqa: E402
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from core.search_planner_runtime import (  # noqa: E402
    contract_ref_from_contract as planner_contract_ref_from_contract,
)
from core.search_result_candidate_packet import (  # noqa: E402
    build_search_result_candidate_packet_from_live_validation_state,
    search_result_candidate_packet_ref_from_packet,
    validate_search_result_candidate_packet,
)

PHASE = "AG-LIMITED-LIVE-SEARCH-CANDIDATE-01"
MODE = "PROOF"
USABLE_ANSWER_VERDICT_TARGET = "NO-BUT-JUSTIFIED"
PROOF_CLASS = "live_component_proof"
PRODUCT_FACING_PROGRESS_TYPE = "live-search-only validation with explicit live license"
PRODUCT_PATH_AFFECTED = (
    "standalone local validation harness only; installed product behavior is unchanged"
)
ACTUAL_CONSUMER_SEAM = (
    "ordinary query/SearchExecutorHandoff -> RunKernel live_search_validation "
    "-> SearchResultCandidatePacket"
)
DEFAULT_QUERY = "current adult U.S. passport book renewal fee official"
USER_FACING_QUESTION = "What is the current adult U.S. passport book renewal fee?"
REQUIRED_SOURCE_CLASS = (
    "official/current government source, preferably a .gov source controlled by "
    "the U.S. State Department or official passport agency"
)
DEFAULT_PROVIDER = "serper"
DEFAULT_OPERATION = "search.query"
EXPECTED_SEARCH_SCHEMA_VERSION = "2"
EXPECTED_SEARCH_PROOF_KIND = "scryraven_search_query_proof_v2"
EXPECTED_SEARCH_COST_CEILING_USD = "0.05"
MAX_SEARCH_TASKS = 1
MAX_PROVIDER_CALLS = 1
MAX_RESULTS = 5
MODEL_CALLS = 0
OUTPUT_ROOT = ROOT / "output"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "ag_limited_live_search_candidate_01"
DEFAULT_PROVIDER_RESULTS = DEFAULT_OUTPUT_DIR / "sanitized_provider_results.json"
REQUEST_PACKET_NAME = "request_packet.json"
REQUEST_MARKDOWN_NAME = "request_packet.md"
VALIDATION_PACKET_NAME = "validation_packet.json"
VALIDATION_MARKDOWN_NAME = "validation_packet.md"
CANDIDATE_PACKET_NAME = retained_preflight.CANDIDATE_PACKET_NAME
CURRENT_RUN_CANDIDATE_PACKET_NAME = retained_preflight.CURRENT_RUN_CANDIDATE_PACKET_NAME
RETAINED_ARTIFACT_BLOCKED_CANDIDATE_LINEAGE = (
    retained_preflight.RETAINED_ARTIFACT_BLOCKED_CANDIDATE_LINEAGE
)
RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_MISSING = (
    retained_preflight.RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_MISSING
)
RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH = (
    retained_preflight.RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_PATH_MISMATCH
)
RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_UNREADABLE = (
    retained_preflight.RETAINED_ARTIFACT_BLOCKED_LOCAL_ARTIFACT_UNREADABLE
)
RETAINED_ARTIFACT_BLOCKED_OUTPUT_BOUNDARY = (
    retained_preflight.RETAINED_ARTIFACT_BLOCKED_OUTPUT_BOUNDARY
)
RETAINED_ARTIFACT_BLOCKED_RAW_OR_PRIVATE_FIELD = (
    retained_preflight.RETAINED_ARTIFACT_BLOCKED_RAW_OR_PRIVATE_FIELD
)
RETAINED_ARTIFACT_BLOCKED_RETENTION_FLAG = (
    retained_preflight.RETAINED_ARTIFACT_BLOCKED_RETENTION_FLAG
)
RETAINED_ARTIFACT_OUTPUT_DIR_NAME = retained_preflight.RETAINED_ARTIFACT_OUTPUT_DIR_NAME
RETAINED_ARTIFACT_PREFLIGHT_DECISIONS = (
    retained_preflight.RETAINED_ARTIFACT_PREFLIGHT_DECISIONS
)
RETAINED_ARTIFACT_PREFLIGHT_PASS = retained_preflight.RETAINED_ARTIFACT_PREFLIGHT_PASS
RETAINED_ARTIFACT_REPAIR_PHASE = retained_preflight.RETAINED_ARTIFACT_REPAIR_PHASE
RETAINED_ARTIFACT_REQUIRED_NAMES = retained_preflight.RETAINED_ARTIFACT_REQUIRED_NAMES
preflight_retained_live_artifacts = retained_preflight.preflight_retained_live_artifacts
DEFAULT_RETAINED_ARTIFACT_DIR = OUTPUT_ROOT / RETAINED_ARTIFACT_OUTPUT_DIR_NAME
MANDATORY_NEXT_BUILD_CHECKPOINT = (
    "targeted live source-survival / fetch-read / evidence-custody phase if "
    "candidate acquisition passes, or targeted acquisition repair if live "
    "candidate acquisition fails"
)
COMPONENT_ID = "component:adult-us-passport-book-renewal-fee"
SOURCE_OBLIGATION_ID = "obligation:official-current-passport-fee-source"
SEARCH_REQUIREMENT_ID = "searchreq:adult-us-passport-book-renewal-fee"

OPENED_SURFACES = [
    "trusted-local generic provider-proxy brokered serper search, max one call",
    "sanitized provider result records under repo-local output/",
    "RunKernel live_search_validation reduction into SearchResultCandidatePacket",
]
CLOSED_SURFACES = [
    "model calls",
    "URL fetch/read",
    "retrieval",
    "EvidenceLedger admissions from live content",
    "citation eligibility or rendering",
    "source-obligation satisfaction",
    "Sufficiency/FAP/Author/AuthorProse from live evidence",
    "old Author/FAP/pipeline paths",
    "raw provider payload/search response retention",
]
EXPLICIT_NON_PROOFS = [
    "source survival after candidate acquisition",
    "URL fetch/read success",
    "EvidenceLedger custody from live content",
    "semantic support",
    "citation eligibility",
    "citation rendering",
    "source-obligation satisfaction",
    "Sufficiency, FAP, Author, or AuthorProse behavior",
    "answer correctness or product correctness",
    "product-quality prose",
]

LIKELY_ACQUISITION_RESULTS = frozenset(
    {
        "candidate_acquisition_pass",
        "candidate_acquisition_partial",
        "candidate_acquisition_fail",
        "validation_inconclusive",
        "validation_not_run_operator_blocked",
    }
)

ALLOWED_PROVIDER_RESULT_KEYS = frozenset(
    {
        "title",
        "url",
        "link",
        "domain",
        "snippet",
        "date",
        "published_or_observed_date",
        "rank",
        "result_rank",
        "call_index",
        "provider_call_index",
        "provider",
        "operation",
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    }
)
ALLOWED_PROVIDER_ENVELOPE_KEYS = frozenset(
    {
        "schema_version",
        "proof_kind",
        "provider",
        "operation",
        "status",
        "result_count",
        "results",
        "physical_attempt_count",
        "caller_authorized_cost_ceiling_usd",
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
        "raw_search_response_retained",
    }
)
RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "auth_header",
        "auth_headers",
        "authorization",
        "authorization_header",
        "cache",
        "cache_row",
        "cookie",
        "db",
        "db_cache_row",
        "db_cache_rows",
        "db_row",
        "env",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
        "html",
        "log",
        "logs",
        "model_response",
        "output_packet",
        "page_content",
        "password",
        "private_log",
        "private_logs",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_html",
        "raw_model_response",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "serper_api_key",
        "serper_payload",
        "token",
        "unbounded_text",
    }
)
FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "admitted_source",
        "admitted_sources",
        "answer",
        "author",
        "author_input",
        "author_material",
        "citation",
        "citation_record",
        "citation_records",
        "citation_source",
        "citation_sources",
        "citations",
        "content",
        "content_fetched_from_url",
        "evidence",
        "evidence_ledger",
        "evidence_ledger_admission",
        "evidence_record",
        "evidence_records",
        "evidence_sources",
        "fap",
        "fap_material",
        "fetched_content",
        "final_answer",
        "final_answer_packet",
        "read_content",
        "retrieved_content",
        "semantic_observation",
        "source_obligation_claim",
        "source_obligation_support",
        "sufficiency_decision",
        "sufficiency_judgment",
    }
)
PRIVATE_VALUE_MARKERS = frozenset(
    {
        "api_key",
        "authorization:",
        "bearer ",
        "private_sentinel",
        "provider_payload",
        "raw_private",
        "raw_prompt",
        "raw_provider",
        "secret",
    }
)


class LimitedLiveSearchCandidateError(ValueError):
    """Raised when the limited live search candidate harness must fail closed."""


@dataclass(frozen=True, slots=True)
class FrontHalf:
    kernel: RunKernel
    selected_search_task_ids: list[str]
    query_digest: str
    output_dir: Path


@dataclass(frozen=True, slots=True)
class InProcessLiveCandidateHandoff:
    """In-memory-only carrier for replay consumers that need the live RunKernel."""

    run_kernel: RunKernel
    candidate_packet: dict[str, Any]
    validation_packet: dict[str, Any]
    sanitized_provider_results: tuple[dict[str, Any], ...]
    provider_results_ref: dict[str, Any]


class DeterministicPassportFeePlannerAdapter:
    """Repo-visible deterministic adapter; never calls a model or provider."""

    def __init__(self, *, query: str) -> None:
        self.query = query

    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return _planner_adapter_result(planner_input, query=self.query)


def prepare_request(
    *,
    query: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Write the request/review-prep packet without broker or provider contact."""

    target = _phase_output_dir(output_dir)
    front_half = build_front_half(query=query, output_dir=target)
    request_packet = _base_packet(
        front_half=front_half,
        query=query,
        provider_used=None,
        provider_calls_attempted=0,
        provider_calls_completed=0,
        broker_invoked=False,
        live_provider_called=False,
        sanitized_provider_results=[],
        search_result_candidate_packet=None,
        likely_acquisition_result="validation_not_run_operator_blocked",
        likely_failure_layer="operator_pending",
        budget_exhausted=False,
    )
    request_packet.update(
        {
            "packet_kind": "limited_live_search_candidate_request_prep",
            "request_generation_provider_free": True,
            "reduce_results_provider_free": True,
            "provider_results_expected_path": _rel(DEFAULT_PROVIDER_RESULTS),
            "operator_command": _operator_command(),
            "expected_output_paths": {
                "request_packet": _rel(target / REQUEST_PACKET_NAME),
                "request_markdown": _rel(target / REQUEST_MARKDOWN_NAME),
                "sanitized_provider_results": _rel(DEFAULT_PROVIDER_RESULTS),
                "validation_packet": _rel(target / VALIDATION_PACKET_NAME),
                "validation_markdown": _rel(target / VALIDATION_MARKDOWN_NAME),
                "search_result_candidate_packet": _rel(target / CANDIDATE_PACKET_NAME),
                "search_candidate_packet": _rel(
                    target / CURRENT_RUN_CANDIDATE_PACKET_NAME
                ),
            },
            "operator_blocked_status_is_distinct_from_inconclusive": True,
            "validation_inconclusive_meaning": (
                "the reducer ran but available sanitized facts do not localize "
                "candidate acquisition"
            ),
        }
    )
    _write_json(target / REQUEST_PACKET_NAME, request_packet)
    (target / REQUEST_MARKDOWN_NAME).write_text(
        _request_markdown(request_packet),
        encoding="utf-8",
    )
    return request_packet


def reduce_results(
    *,
    query: str,
    provider_results_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Reduce sanitized provider records through RunKernel and candidate packet."""

    target = _phase_output_dir(output_dir)
    results_path = _phase_output_path(provider_results_path)
    front_half = build_front_half(query=query, output_dir=target)
    sanitized_results, envelope = load_sanitized_provider_results(results_path)
    task_id = front_half.selected_search_task_ids[0]
    action = front_half.kernel.authorize_live_search_validation(
        selected_search_task_ids=front_half.selected_search_task_ids,
        provider_authorized=DEFAULT_PROVIDER,
        provider_call_cap=MAX_PROVIDER_CALLS,
        results_per_task_cap=MAX_RESULTS,
        parent_current_contract_version=front_half.kernel.state.current_answer_contract[
            "accepted_contract_version"
        ],
        parent_current_contract_digest=front_half.kernel.state.current_answer_contract[
            "accepted_contract_digest"
        ],
        handoff_id=front_half.kernel.state.search_executor_handoff_state[
            "handoff_id"
        ],
        handoff_digest=front_half.kernel.state.search_executor_handoff_state[
            "handoff_digest"
        ],
    )
    payload = build_live_search_validation_observation_payload(
        action=action,
        current_answer_contract=front_half.kernel.state.current_answer_contract,
        search_executor_handoff_state=(
            front_half.kernel.state.search_executor_handoff_state
        ),
        provider_used=DEFAULT_PROVIDER,
        provider_results_by_task={task_id: sanitized_results},
        provider_calls_attempted_count=MAX_PROVIDER_CALLS,
        provider_calls_completed_count=MAX_PROVIDER_CALLS,
        execution_mode=LIVE_SEARCH_VALIDATION_EXECUTION_MODE_BROKER_LIVE,
        broker_invoked=True,
        live_provider_called=True,
    )
    front_half.kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
            status=RunStageStatus.COMPLETED,
            payload=payload,
        )
    )
    candidate_packet = validate_search_result_candidate_packet(
        build_search_result_candidate_packet_from_live_validation_state(
            front_half.kernel.state.live_search_validation_state
        )
    )
    candidate_packet_path = target / CANDIDATE_PACKET_NAME
    _write_json(candidate_packet_path, candidate_packet)
    current_run_candidate_packet_path = target / CURRENT_RUN_CANDIDATE_PACKET_NAME
    _write_json(current_run_candidate_packet_path, candidate_packet)

    official_current = any(
        appears_official_current_government_source(result)
        for result in sanitized_results
    )
    candidate_packet_status = _candidate_packet_status(candidate_packet)
    result, failure_layer = _candidate_acquisition_result(
        sanitized_results=sanitized_results,
        official_current=official_current,
        candidate_packet_status=candidate_packet_status,
    )
    validation_packet = _base_packet(
        front_half=front_half,
        query=query,
        provider_used=envelope.get("provider") or DEFAULT_PROVIDER,
        provider_calls_attempted=MAX_PROVIDER_CALLS,
        provider_calls_completed=MAX_PROVIDER_CALLS,
        broker_invoked=True,
        live_provider_called=True,
        sanitized_provider_results=sanitized_results,
        search_result_candidate_packet=candidate_packet,
        likely_acquisition_result=result,
        likely_failure_layer=failure_layer,
        budget_exhausted=True,
    )
    validation_packet.update(
        {
            "packet_kind": "limited_live_search_candidate_validation_packet",
            "provider_results_path": _rel(results_path),
            "provider_results_envelope": envelope,
            "search_result_candidate_packet_path": _rel(candidate_packet_path),
            "search_candidate_packet_path": _rel(current_run_candidate_packet_path),
            "validation_reducer_provider_free": True,
            "decision_this_run_makes": (
                "Can the ordinary-query/SearchExecutorHandoff path acquire "
                "sanitized live official/current candidate results for the "
                "approved query and reduce them into SearchResultCandidatePacket "
                "without raw/private leakage or old-path revival?"
            ),
        }
    )
    _write_json(target / VALIDATION_PACKET_NAME, validation_packet)
    (target / VALIDATION_MARKDOWN_NAME).write_text(
        _validation_markdown(validation_packet),
        encoding="utf-8",
    )
    return validation_packet


def reduce_existing_sanitized_provider_results_in_process(
    *,
    query: str,
    provider_results_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> InProcessLiveCandidateHandoff:
    """Replay existing sanitized provider results while preserving RunKernel.

    This helper performs no provider, broker, search, fetch/read, model, or
    retrieval call.  It exists only for in-process consumers that must keep the
    RunKernel authority lineage alive; the returned object must not be
    serialized.
    """

    target = _phase_output_dir(output_dir)
    results_path = _phase_output_path(provider_results_path)
    front_half = build_front_half(query=query, output_dir=target)
    sanitized_results, envelope = load_sanitized_provider_results(results_path)
    task_id = front_half.selected_search_task_ids[0]
    action = front_half.kernel.authorize_live_search_validation(
        selected_search_task_ids=front_half.selected_search_task_ids,
        provider_authorized=DEFAULT_PROVIDER,
        provider_call_cap=MAX_PROVIDER_CALLS,
        results_per_task_cap=MAX_RESULTS,
        parent_current_contract_version=front_half.kernel.state.current_answer_contract[
            "accepted_contract_version"
        ],
        parent_current_contract_digest=front_half.kernel.state.current_answer_contract[
            "accepted_contract_digest"
        ],
        handoff_id=front_half.kernel.state.search_executor_handoff_state[
            "handoff_id"
        ],
        handoff_digest=front_half.kernel.state.search_executor_handoff_state[
            "handoff_digest"
        ],
    )
    payload = build_live_search_validation_observation_payload(
        action=action,
        current_answer_contract=front_half.kernel.state.current_answer_contract,
        search_executor_handoff_state=(
            front_half.kernel.state.search_executor_handoff_state
        ),
        provider_used=DEFAULT_PROVIDER,
        provider_results_by_task={task_id: sanitized_results},
        provider_calls_attempted_count=0,
        provider_calls_completed_count=0,
        execution_mode=LIVE_SEARCH_VALIDATION_EXECUTION_MODE_OFFLINE_FAKE,
        broker_invoked=False,
        live_provider_called=False,
    )
    front_half.kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.LIVE_SEARCH_VALIDATED,
            status=RunStageStatus.COMPLETED,
            payload=payload,
        )
    )
    candidate_packet = validate_search_result_candidate_packet(
        build_search_result_candidate_packet_from_live_validation_state(
            front_half.kernel.state.live_search_validation_state
        )
    )
    official_current = any(
        appears_official_current_government_source(result)
        for result in sanitized_results
    )
    candidate_packet_status = _candidate_packet_status(candidate_packet)
    result, failure_layer = _candidate_acquisition_result(
        sanitized_results=sanitized_results,
        official_current=official_current,
        candidate_packet_status=candidate_packet_status,
    )
    validation_packet = _base_packet(
        front_half=front_half,
        query=query,
        provider_used=envelope.get("provider") or DEFAULT_PROVIDER,
        provider_calls_attempted=0,
        provider_calls_completed=0,
        broker_invoked=False,
        live_provider_called=False,
        sanitized_provider_results=sanitized_results,
        search_result_candidate_packet=candidate_packet,
        likely_acquisition_result=result,
        likely_failure_layer=failure_layer,
        budget_exhausted=False,
    )
    validation_packet.update(
        {
            "packet_kind": "limited_live_search_candidate_in_process_replay_packet",
            "sanitized_provider_results_replayed_from_existing_local_output": True,
            "provider_search_calls_performed_by_replay": 0,
            "broker_calls_performed_by_replay": 0,
            "model_calls_performed_by_replay": 0,
            "fetch_read_calls_performed_by_replay": 0,
            "runkernel_preserved_for_handoff": True,
            "candidate_packet_json_is_output_not_state_source": True,
            "projection_to_runkernel_rehydration": False,
        }
    )
    return InProcessLiveCandidateHandoff(
        run_kernel=front_half.kernel,
        candidate_packet=candidate_packet,
        validation_packet=validation_packet,
        sanitized_provider_results=tuple(dict(item) for item in sanitized_results),
        provider_results_ref={
            "path": _rel(results_path),
            "digest": _file_digest(results_path),
            "result_count": len(sanitized_results),
        },
    )


def build_front_half(*, query: str, output_dir: Path) -> FrontHalf:
    normalized_query = _normalize_query(query)
    query_digest = _ordinary_query_digest(normalized_query)
    run_id = f"run:ag-limited-live-search-candidate-01:{query_digest[:12]}"
    request_id = f"request:ag-limited-live-search-candidate-01:{query_digest[:12]}"
    kernel = RunKernel.start(
        run_id=run_id,
        request_id=request_id,
        request={
            "phase": PHASE,
            "mode": MODE,
            "proof_class": PROOF_CLASS,
            "query_class": "ordinary-query live search candidate validation",
            "query_text_retained": False,
            "model_calls": MODEL_CALLS,
        },
    )
    _reduce_deterministic_planner(kernel, query=normalized_query)
    _accept_initial_contract(kernel)
    _apply_current_contract_caveat(kernel, query=normalized_query)
    _reduce_search_executor_handoff(kernel)
    selected_ids = _selected_task_ids(kernel)
    if len(selected_ids) != MAX_SEARCH_TASKS:
        raise LimitedLiveSearchCandidateError(
            "limited live validation requires exactly one SearchExecutorHandoff task"
        )
    return FrontHalf(
        kernel=kernel,
        selected_search_task_ids=selected_ids,
        query_digest=query_digest,
        output_dir=output_dir,
    )


def load_sanitized_provider_results(
    path: str | Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    resolved = _phase_output_path(path)
    try:
        decoded = json.loads(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LimitedLiveSearchCandidateError(
            "could not read sanitized provider results"
        ) from exc
    except json.JSONDecodeError as exc:
        raise LimitedLiveSearchCandidateError(
            "sanitized provider results must be JSON"
        ) from exc

    return _decode_sanitized_provider_results(decoded)


def _decode_sanitized_provider_results(
    decoded: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    envelope: dict[str, Any]
    raw_results: Any
    if isinstance(decoded, Mapping):
        envelope = _validate_provider_results_envelope(decoded)
        raw_results = decoded.get("results")
    else:
        raise LimitedLiveSearchCandidateError(
            "sanitized provider results must use the versioned search proof object"
        )

    if not isinstance(raw_results, list):
        raise LimitedLiveSearchCandidateError(
            "sanitized provider results require a results list"
        )
    if len(raw_results) > MAX_RESULTS:
        raise LimitedLiveSearchCandidateError(
            f"sanitized provider results exceed max results cap {MAX_RESULTS}"
        )
    if int(envelope.get("result_count", len(raw_results))) != len(raw_results):
        raise LimitedLiveSearchCandidateError(
            "sanitized provider result_count does not match results length"
        )

    normalized = [
        normalize_provider_result(record, default_rank=index)
        for index, record in enumerate(raw_results, start=1)
    ]
    return normalized, envelope


def normalize_provider_result(
    result: Mapping[str, Any],
    *,
    default_rank: int,
) -> dict[str, Any]:
    raw = _safe_mapping(result)
    _reject_forbidden_material(raw, context="provider result")
    unknown = sorted(set(raw) - ALLOWED_PROVIDER_RESULT_KEYS)
    if unknown:
        raise LimitedLiveSearchCandidateError(
            "provider result contains unsupported fields: " + ", ".join(unknown)
        )
    _validate_false_retention(raw, context="provider result")
    if (
        raw.get("provider") != DEFAULT_PROVIDER
        or raw.get("operation") != DEFAULT_OPERATION
    ):
        raise LimitedLiveSearchCandidateError(
            "provider result route attestation mismatch"
        )
    title = _required_token(raw.get("title"), "provider result requires title", 220)
    url = _required_url(raw.get("url") or raw.get("link"))
    domain = _clean_domain(raw.get("domain")) or _domain_from_url(url)
    if not domain:
        raise LimitedLiveSearchCandidateError(
            "provider result requires domain or http(s) URL"
        )
    return _without_empty(
        {
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": _clean_token(raw.get("snippet"), limit=500),
            "published_or_observed_date": _clean_token(
                raw.get("published_or_observed_date") or raw.get("date"),
                limit=80,
            ),
            "result_rank": _positive_int(
                raw.get("result_rank") or raw.get("rank") or default_rank,
                "provider result rank must be positive",
            ),
            "provider_call_index": _positive_int(
                raw.get("provider_call_index") or raw.get("call_index") or 1,
                "provider result call index must be positive",
            ),
        }
    )


def appears_official_current_government_source(result: Mapping[str, Any]) -> bool:
    domain = str(result.get("domain") or "").casefold()
    url = str(result.get("url") or "").casefold()
    title = str(result.get("title") or "").casefold()
    snippet = str(result.get("snippet") or "").casefold()
    text = " ".join((domain, url, title, snippet))
    government = domain.endswith(".gov") or ".gov/" in url
    passport_agency = (
        "travel.state.gov" in domain
        or "state.gov" in domain
        or "passport" in text
    )
    fee_context = "passport" in text and any(token in text for token in ("fee", "fees", "renewal", "book"))
    return government and passport_agency and fee_context


def _base_packet(
    *,
    front_half: FrontHalf,
    query: str,
    provider_used: str | None,
    provider_calls_attempted: int,
    provider_calls_completed: int,
    broker_invoked: bool,
    live_provider_called: bool,
    sanitized_provider_results: Sequence[Mapping[str, Any]],
    search_result_candidate_packet: Mapping[str, Any] | None,
    likely_acquisition_result: str,
    likely_failure_layer: str | None,
    budget_exhausted: bool,
) -> dict[str, Any]:
    if likely_acquisition_result not in LIKELY_ACQUISITION_RESULTS:
        raise LimitedLiveSearchCandidateError("unknown acquisition result")
    kernel = front_half.kernel
    candidate_packet_ref = search_result_candidate_packet_ref_from_packet(
        search_result_candidate_packet
    )
    return _json_safe(
        {
            "phase": PHASE,
            "mode": MODE,
            "usable_answer_verdict_target": USABLE_ANSWER_VERDICT_TARGET,
            "proof_class": PROOF_CLASS,
            "product_facing_progress_type": PRODUCT_FACING_PROGRESS_TYPE,
            "product_path_affected": PRODUCT_PATH_AFFECTED,
            "runtime_consumer": "RunKernel live_search_validation and SearchResultCandidatePacket builder",
            "actual_consumer_seam": ACTUAL_CONSUMER_SEAM,
            "actual_app_delta": (
                "No installed product behavior changes; the local harness can "
                "review live-search candidate acquisition into the current "
                "non-evidence candidate packet seam."
            ),
            "user_facing_reviewable_output_delta": (
                "JSON/Markdown packets under output/ag_limited_live_search_candidate_01/"
            ),
            "non_product_exception_leash": (
                "This Proof phase is limited to live candidate acquisition "
                "because source survival, fetch/read, evidence custody, citation, "
                "Sufficiency, FAP, and Author surfaces remain closed."
            ),
            "original_user_style_query": USER_FACING_QUESTION,
            "validation_search_query": _normalize_query(query),
            "query_digest_ref": {
                "ordinary_query_ref": {
                    "ref_kind": "ordinary_user_query_digest",
                    "digest": front_half.query_digest,
                    "algorithm": "sha256(phase plus normalized query text)",
                },
                "current_path_user_query_ref": (
                    kernel.state.search_planner_proposal_state.get("user_query_ref")
                    or {}
                ),
            },
            "required_source_class": REQUIRED_SOURCE_CLASS,
            "provider_requested": DEFAULT_PROVIDER,
            "provider_operation": DEFAULT_OPERATION,
            "provider_used": provider_used,
            "provider_calls_attempted": provider_calls_attempted,
            "provider_calls_completed": provider_calls_completed,
            "broker_invoked": broker_invoked,
            "live_provider_called": live_provider_called,
            "live_budget": {
                "budget_scope": "phase-local licensed budget; not a global default",
                "max_scry_raven_validation_runs": 1,
                "max_search_tasks": MAX_SEARCH_TASKS,
                "max_provider_search_calls_total": MAX_PROVIDER_CALLS,
                "provider": DEFAULT_PROVIDER,
                "operation": DEFAULT_OPERATION,
                "max_results": MAX_RESULTS,
                "ordinary_default_results_per_task_cap": (
                    LIVE_SEARCH_VALIDATION_DEFAULT_RESULTS_PER_TASK_CAP
                ),
                "explicit_results_per_task_ceiling": (
                    LIVE_SEARCH_VALIDATION_EXPLICIT_RESULTS_PER_TASK_CAP
                ),
                "model_calls": MODEL_CALLS,
                "broker_calls": "max 1 trusted-local generic provider-proxy call",
                "fetch_read_calls": 0,
                "retrieval_calls": 0,
                "evidence_ledger_admissions_from_live_content": 0,
                "citation_eligibility_decisions": 0,
                "source_obligation_satisfaction_decisions": 0,
                "sufficiency_fap_author_authorprose_from_live_evidence": 0,
                "retries": 0,
            },
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
            "selected_search_executor_handoff_task_ids": list(
                front_half.selected_search_task_ids
            ),
            "search_executor_handoff_ref": {
                "handoff_id": kernel.state.search_executor_handoff_state.get(
                    "handoff_id"
                ),
                "handoff_digest": kernel.state.search_executor_handoff_state.get(
                    "handoff_digest"
                ),
            },
            "sanitized_provider_result_count": len(sanitized_provider_results),
            "sanitized_provider_result_summaries": [
                _result_summary(result) for result in sanitized_provider_results
            ],
            "search_result_candidate_packet_ref": candidate_packet_ref,
            "search_result_candidate_packet_status": _candidate_packet_status(
                search_result_candidate_packet
            ),
            "at_least_one_result_appears_official_current_government_source": any(
                appears_official_current_government_source(result)
                for result in sanitized_provider_results
            ),
            "likely_acquisition_result": likely_acquisition_result,
            "likely_failure_layer_if_not_pass": likely_failure_layer,
            "opened_surfaces": list(OPENED_SURFACES),
            "closed_surfaces": list(CLOSED_SURFACES),
            "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
            "budget_exhausted": budget_exhausted,
            "mandatory_next_build_product_checkpoint": MANDATORY_NEXT_BUILD_CHECKPOINT,
            "old_path_treatment": (
                "Old Author/FAP/sufficiency/follow-up/pipeline/offline bridge "
                "surfaces remain closed, legacy, passive, or historical; this "
                "harness does not import or call them."
            ),
            "existing_machinery_reused": [
                "ordinary-query normalization/digest pattern",
                "SearchPlannerInput with deterministic adapter",
                "initial/current answer contract acceptance",
                "SearchExecutorHandoff",
                "RunKernel live_search_validation observation/reduction",
                "SearchResultCandidatePacket builder/validator",
            ],
            "new_machinery_introduced": [
                "scripts/ag_limited_live_search_candidate_01.py",
                "tests/test_ag_limited_live_search_candidate_01.py",
                "docs/architecture/AG_LIMITED_LIVE_SEARCH_CANDIDATE_01.md",
            ],
            "why_not_reinventing_existing_surface": (
                "The harness starts from an ordinary query and reduces through "
                "the existing SearchExecutorHandoff and SearchResultCandidatePacket "
                "seams; the broker remains generic credential plumbing."
            ),
        }
    )


def _reduce_deterministic_planner(kernel: RunKernel, *, query: str) -> None:
    planner_input = SearchPlannerInput(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        user_query_text=query,
        requested_mode="balanced",
        safe_context={
            "phase": PHASE,
            "mode": MODE,
            "front_half_source": "deterministic_limited_live_candidate_harness",
            "source_policy": "official-current-government",
            "not_product_path": True,
            "model_calls": MODEL_CALLS,
        },
        route_context_ref={"route_ref": "ag-limited-live-search-candidate-01"},
        run_context_ref={"run_ref": "ag-limited-live-search-candidate-01"},
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )
    action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=DeterministicPassportFeePlannerAdapter(query=query),
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )


def _accept_initial_contract(kernel: RunKernel) -> None:
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=str(qmr["record_id"]),
        parent_proposal_digest=str(qmr["record_digest"]),
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
            status=RunStageStatus.COMPLETED,
            payload={"question_meaning_record": dict(qmr)},
        )
    )


def _apply_current_contract_caveat(kernel: RunKernel, *, query: str) -> None:
    accepted = kernel.state.initial_answer_contract
    record = _current_contract_caveat_record(kernel, accepted, query=query)
    action = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={"contract_amendment_record": record.to_dict()},
        )
    )
    admission = kernel.state.contract_amendment_admission_projection
    apply_action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=str(admission["admission_digest"]),
    )
    kernel.reduce(
        Observation.from_action(
            apply_action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
            status=RunStageStatus.COMPLETED,
            payload={},
        )
    )


def _reduce_search_executor_handoff(kernel: RunKernel) -> None:
    contract = kernel.state.current_answer_contract
    handoff_input = SearchExecutorHandoffInput(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        parent_current_contract_ref=handoff_contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
        parent_initial_contract_ref=handoff_contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        contract_parent_kind="current_answer_contract",
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            kernel.state.search_planner_proposal_state
        ),
        answer_component_refs=contract.get("accepted_answer_component_refs", []),
        source_obligation_candidate_refs=_source_refs_from_contract(contract),
        component_search_requirements=(
            kernel.state.search_planner_proposal_state.get(
                "component_search_requirements",
                [],
            )
        ),
        required_caveats=contract.get("mandatory_caveats", []),
        prohibited_upgrades=contract.get("prohibited_upgrades", []),
        query_budget={"max_search_tasks": MAX_SEARCH_TASKS, "max_results_per_task": MAX_RESULTS},
        allowed_verticals=["search"],
        provider_preference_hint=DEFAULT_PROVIDER,
    )
    action = kernel.authorize_search_executor_handoff()
    result = execute_search_executor_handoff_action(
        action=action,
        handoff_input=handoff_input,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
            status=RunStageStatus.COMPLETED,
            payload=result.observation_payload,
        )
    )


def _planner_adapter_result(
    planner_input: Mapping[str, Any],
    *,
    query: str,
) -> dict[str, Any]:
    query_ref = _mapping(planner_input.get("user_query_ref"))
    return {
        "question_meaning_summary": (
            "Prepare one official-current government-source search candidate "
            "lookup for the current adult U.S. passport book renewal fee."
        ),
        "requested_output": "Sanitized SearchResultCandidate records only; no answer.",
        "semantic_slots": [
            {
                "slot_id": "slot:passport-fee-currentness",
                "slot_kind": "source_basis",
                "status": "explicit",
                "selected_value": "official-current government source",
                "materiality": "material",
            }
        ],
        "answer_components": [
            {
                "component_id": COMPONENT_ID,
                "component_revision": "1",
                "user_facing_label": "Adult U.S. passport book renewal fee",
                "user_facing_question": USER_FACING_QUESTION,
                "requirement_posture": "required",
                "acceptance_criteria": [
                    "discover official/current government candidate results",
                    "do not answer from snippets or search candidates",
                ],
                "semantic_slot_ids": ["slot:passport-fee-currentness"],
                "source_obligation_candidate_ids": [SOURCE_OBLIGATION_ID],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": [
                    "SearchResultCandidate records are non-evidence."
                ],
                "prohibited_upgrades": [
                    "Do not claim source-obligation satisfaction from search snippets."
                ],
                "materiality": "material",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": SOURCE_OBLIGATION_ID,
                "obligation_kind": "official_current_government_source",
                "component_candidate_ids": [COMPONENT_ID],
                "strictness": "required",
            }
        ],
        "component_search_requirements": [
            {
                "component_id": COMPONENT_ID,
                "requirement_id": SEARCH_REQUIREMENT_ID,
                "requirement_summary": query,
                "source_obligation_candidate_ids": [SOURCE_OBLIGATION_ID],
                "preferred_source_kinds": ["official", "government"],
                "recency_requirement": "current",
            }
        ],
        "material_ambiguity_posture": "clear",
        "mandatory_caveats": [
            "This phase validates search candidates only and does not answer."
        ],
        "prohibited_upgrades": [
            "No fetch/read, EvidenceLedger, citations, Sufficiency, FAP, Author, or product-correctness claim."
        ],
        "normalization_obligations": [
            "Treat the query as search-candidate discovery only."
        ],
        "assumptions": [
            "The trusted-local broker supplies sanitized provider records separately."
        ],
        "unsupported_outputs": [
            "Final answer creation is outside AG-LIMITED-LIVE-SEARCH-CANDIDATE-01."
        ],
        "planner_model_metadata": {
            "provider": "deterministic_limited_live_candidate_adapter",
            "model_adapter_enabled": False,
            "raw_prompt_retained": False,
            "raw_model_response_retained": False,
            "provider_payload_retained": False,
            "prompt_hash": query_ref.get("digest"),
        },
    }


def _current_contract_caveat_record(
    kernel: RunKernel,
    accepted: Mapping[str, Any],
    *,
    query: str,
) -> ContractAmendmentRecord:
    operation = AmendmentOperation(
        operation_id="operation:add-ag-limited-live-candidate-caveat",
        operation_kind=AmendmentOperationKind.ADD_CAVEAT,
        operation_payload={
            "caveat": (
                "AG-LIMITED live search candidate validation records search "
                "candidates only; candidates are not evidence."
            ),
            "component_id": COMPONENT_ID,
        },
    )
    return ContractAmendmentRecord(
        amendment_record_id="amendment:ag-limited-live-search-candidate-01",
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        request_digest=_ordinary_query_digest(query),
        parent_contract_version=str(accepted["accepted_contract_version"]),
        parent_contract_digest=str(accepted["accepted_contract_digest"]),
        parent_question_meaning_record_id=accepted.get(
            "parent_question_meaning_record_id"
        ),
        parent_question_meaning_record_digest=accepted.get(
            "parent_question_meaning_record_digest"
        ),
        accepted_contract_ref=f"contract:{accepted['accepted_contract_version']}:accepted",
        trigger_refs=AmendmentTriggerRefs(
            gap_refs=("validation:search-candidate-acquisition-only",),
            currentness_refs=("validation:passport-fee-current-official-source",),
        ),
        operations=(operation,),
        materiality=MaterialityPosture.NON_MATERIAL,
        user_confirmation_posture="not_required",
        monotonicity=MonotonicityPosture.STRENGTHENS,
        weakening_posture=WeakeningPosture.NONE,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        required_caveats=("SearchResultCandidate records remain non-evidence.",),
        prohibited_upgrades=(
            "Do not use provider_preference_hint as live provider authority.",
        ),
        metadata={
            "phase": PHASE,
            "mode": MODE,
            "front_half_source": "deterministic_limited_live_candidate_harness",
        },
    )


def _selected_task_ids(kernel: RunKernel) -> list[str]:
    tasks = kernel.state.search_executor_handoff_state.get("search_task_records", [])
    return [str(task["search_task_id"]) for task in tasks if isinstance(task, Mapping)]


def _source_refs_from_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for component in contract.get("accepted_answer_component_refs", []) or []:
        mapping = _mapping(component)
        component_id = mapping.get("component_id")
        for candidate_id in mapping.get("source_obligation_candidate_ids", []) or []:
            refs.append(
                {
                    "candidate_id": candidate_id,
                    "component_candidate_ids": [component_id],
                    "obligation_kind": "official_current_government_source",
                    "strictness": "required",
                }
            )
    return refs


def _validate_provider_results_envelope(decoded: Mapping[str, Any]) -> dict[str, Any]:
    raw = _safe_mapping(decoded)
    _reject_forbidden_material(raw, context="provider results envelope")
    unknown = sorted(set(raw) - ALLOWED_PROVIDER_ENVELOPE_KEYS)
    if unknown:
        raise LimitedLiveSearchCandidateError(
            "provider results envelope contains unsupported fields: "
            + ", ".join(unknown)
        )
    _validate_false_retention(raw, context="provider results envelope")
    if (
        raw.get("schema_version") != EXPECTED_SEARCH_SCHEMA_VERSION
        or raw.get("proof_kind") != EXPECTED_SEARCH_PROOF_KIND
        or raw.get("status") != "ok"
        or raw.get("physical_attempt_count") != 1
        or raw.get("caller_authorized_cost_ceiling_usd")
        != EXPECTED_SEARCH_COST_CEILING_USD
    ):
        raise LimitedLiveSearchCandidateError(
            "provider results envelope proof attestation mismatch"
        )
    provider = _required_token(
        raw.get("provider"),
        "provider results envelope requires provider",
        80,
    )
    operation = _required_token(
        raw.get("operation"),
        "provider results envelope requires operation",
        80,
    )
    if provider != DEFAULT_PROVIDER:
        raise LimitedLiveSearchCandidateError("provider results provider mismatch")
    if operation != DEFAULT_OPERATION:
        raise LimitedLiveSearchCandidateError("provider results operation mismatch")
    result_count = _bounded_int(raw.get("result_count"), default=0)
    return {
        "schema_version": EXPECTED_SEARCH_SCHEMA_VERSION,
        "proof_kind": EXPECTED_SEARCH_PROOF_KIND,
        "provider": provider,
        "operation": operation,
        "status": "ok",
        "result_count": result_count,
        "physical_attempt_count": 1,
        "caller_authorized_cost_ceiling_usd": EXPECTED_SEARCH_COST_CEILING_USD,
        "raw_provider_payload_retained": False,
        "raw_request_material_retained": False,
        "raw_response_material_retained": False,
        "raw_search_response_retained": False,
    }


def _candidate_acquisition_result(
    *,
    sanitized_results: Sequence[Mapping[str, Any]],
    official_current: bool,
    candidate_packet_status: str,
) -> tuple[str, str | None]:
    if candidate_packet_status != "built_and_validated":
        return "candidate_acquisition_fail", "candidate_packet_reduction"
    if not sanitized_results:
        return "candidate_acquisition_fail", "provider_returned_no_results"
    if not official_current:
        return "candidate_acquisition_fail", "official_current_source_acquisition"
    return "candidate_acquisition_pass", None


def _candidate_packet_status(packet: Mapping[str, Any] | None) -> str:
    if not packet:
        return "not_built"
    if packet.get("packet_id") and packet.get("packet_digest"):
        return "built_and_validated"
    return "invalid_or_incomplete"


def _result_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rank": result.get("result_rank"),
        "title": result.get("title"),
        "url": result.get("url"),
        "domain": result.get("domain"),
        "snippet": result.get("snippet"),
        "published_or_observed_date": result.get("published_or_observed_date"),
        "appears_official_current_government_source": (
            appears_official_current_government_source(result)
        ),
    }


def _operator_command() -> str:
    return "\n".join(
        [
            "py scripts\\run_provider_proxy_broker_once.py `",
            "  --provider serper `",
            "  --operation search.query `",
            f'  --query "{DEFAULT_QUERY}" `',
            "  --max-results 5 `",
            "  --timeout-seconds 30 `",
            "  --retry-cap 0 `",
            "  --cost-ceiling-usd 0.05 `",
            "  --output output\\ag_limited_live_search_candidate_01\\sanitized_provider_results.json `",
            "  --broker-url http://127.0.0.1:8765/run `",
            "  --env-file <PRIVATE-ENV-FILE> `",
            "  --confirm-provider-call",
        ]
    )


def _request_markdown(packet: Mapping[str, Any]) -> str:
    non_proofs = "\n".join(f"- {item}" for item in packet["explicit_non_proofs"])
    return (
        f"# {PHASE} Request Prep\n\n"
        f"Mode: `{packet['mode']}`\n\n"
        f"Usable-answer verdict target: `{packet['usable_answer_verdict_target']}`\n\n"
        f"Query: `{packet['validation_search_query']}`\n\n"
        f"Provider: `{packet['provider_requested']}` / `{packet['provider_operation']}`\n\n"
        f"Max provider calls: `{MAX_PROVIDER_CALLS}`. Max results: `{MAX_RESULTS}`.\n\n"
        "This command does not call a provider. Only the separate trusted-local "
        "broker helper may perform the one licensed provider call.\n\n"
        "## Operator Command\n\n"
        "```powershell\n"
        f"{packet['operator_command']}\n"
        "```\n\n"
        "## Status\n\n"
        f"`{packet['likely_acquisition_result']}`: sanitized provider results have not been supplied yet.\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n"
    )


def _validation_markdown(packet: Mapping[str, Any]) -> str:
    summaries = "\n".join(
        "- rank {rank}: {title} ({domain}) official/current-like={official}".format(
            rank=item.get("rank"),
            title=item.get("title"),
            domain=item.get("domain"),
            official=item.get("appears_official_current_government_source"),
        )
        for item in packet["sanitized_provider_result_summaries"]
    )
    non_proofs = "\n".join(f"- {item}" for item in packet["explicit_non_proofs"])
    return (
        f"# {PHASE} Validation Packet\n\n"
        f"Mode: `{packet['mode']}`\n\n"
        f"Usable-answer verdict target: `{packet['usable_answer_verdict_target']}`\n\n"
        f"Query: `{packet['validation_search_query']}`\n\n"
        f"Provider calls attempted/completed: `{packet['provider_calls_attempted']}` / `{packet['provider_calls_completed']}`\n\n"
        f"Sanitized result count: `{packet['sanitized_provider_result_count']}`\n\n"
        f"Candidate acquisition verdict: `{packet['likely_acquisition_result']}`\n\n"
        f"Failure layer: `{packet['likely_failure_layer_if_not_pass']}`\n\n"
        "## Sanitized Result Summaries\n\n"
        f"{summaries or '- None'}\n\n"
        "## Candidate Packet\n\n"
        f"Status: `{packet['search_result_candidate_packet_status']}`\n\n"
        "## Explicit Non-Proofs\n\n"
        f"{non_proofs}\n"
    )


def _resolve_path(path: str | Path) -> Path:
    raw = Path(path)
    try:
        return raw.resolve()
    except OSError:
        return raw.absolute()


def _path_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        normalized_path = os.path.normcase(str(path))
        normalized_root = os.path.normcase(str(root))
        return normalized_path == normalized_root or normalized_path.startswith(
            normalized_root.rstrip("\\/") + os.sep
        )


def _phase_output_dir(path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    resolved = raw.resolve()
    _require_repo_output_path(resolved, error_prefix="output-dir")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _phase_output_path(path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    resolved = raw.resolve()
    _require_repo_output_path(resolved, error_prefix="provider/result/output paths")
    return resolved


def _require_repo_output_path(path: Path, *, error_prefix: str) -> None:
    allowed = OUTPUT_ROOT.resolve()
    try:
        path.relative_to(allowed)
    except ValueError as exc:
        raise LimitedLiveSearchCandidateError(
            f"{error_prefix} must stay under repo-local output/"
        ) from exc


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    resolved = _phase_output_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _normalize_query(query: str) -> str:
    normalized = " ".join(str(query or "").strip().split())
    if not normalized:
        raise LimitedLiveSearchCandidateError("query is required")
    return normalized


def _ordinary_query_digest(query: str) -> str:
    payload = {
        "phase": PHASE,
        "normalized_user_query_text": _normalize_query(query),
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _validate_false_retention(value: Mapping[str, Any], *, context: str) -> None:
    for key in (
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
        "raw_search_response_retained",
    ):
        if key in value and value.get(key) is not False:
            raise LimitedLiveSearchCandidateError(f"{context} must keep {key} false")


def _reject_forbidden_material(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(
        key
        for key in keys
        if key in RAW_OR_PRIVATE_KEYS
        or key in FORBIDDEN_AUTHORITY_KEYS
        or key.startswith("raw_")
    )
    for allowed_false_flag in (
        "raw_provider_payload_retained",
        "raw_request_material_retained",
        "raw_response_material_retained",
        "raw_search_response_retained",
    ):
        if allowed_false_flag in forbidden:
            forbidden.remove(allowed_false_flag)
    if forbidden:
        raise LimitedLiveSearchCandidateError(
            f"{context} contains forbidden raw/private or authority fields: "
            + ", ".join(forbidden)
        )
    markers = sorted(_private_value_markers(value))
    if markers:
        raise LimitedLiveSearchCandidateError(
            f"{context} contains private-looking values: " + ", ".join(markers)
        )


def _private_value_markers(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for item in value.values():
            found.update(_private_value_markers(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_private_value_markers(item))
    elif isinstance(value, str):
        lowered = value.casefold()
        for marker in PRIVATE_VALUE_MARKERS:
            if marker in lowered:
                found.add(marker)
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        return []
    return list(value)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _required_url(value: Any) -> str:
    url = _required_token(value, "provider result requires url", 700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LimitedLiveSearchCandidateError("provider result requires http(s) url")
    return url


def _required_token(value: Any, message: str, limit: int) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise LimitedLiveSearchCandidateError(message)
    return text


def _clean_token(value: Any, *, limit: int = 160) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        raise LimitedLiveSearchCandidateError("provider result values must be scalar")
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in PRIVATE_VALUE_MARKERS):
        raise LimitedLiveSearchCandidateError("provider result contains private-looking value")
    return text[:limit]


def _clean_domain(value: Any) -> str | None:
    text = _clean_token(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _domain_from_url(value: str) -> str | None:
    return urlparse(value).netloc.lower() or None


def _positive_int(value: Any, message: str) -> int:
    parsed = _bounded_int(value, default=0)
    if parsed <= 0:
        raise LimitedLiveSearchCandidateError(message)
    return parsed


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed >= 0 else 0


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _file_digest(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _rel(path: str | Path) -> str:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    try:
        return str(raw.resolve().relative_to(ROOT))
    except ValueError:
        return str(raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare and reduce AG-LIMITED-LIVE-SEARCH-CANDIDATE-01 packets. "
            "This script never calls providers, brokers, models, fetch/read, "
            "retrieval, EvidenceLedger, citation, Sufficiency, FAP, or Author."
        )
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    prepare = subparsers.add_parser("prepare-request")
    prepare.add_argument("--query", default=DEFAULT_QUERY)
    prepare.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    reduce = subparsers.add_parser("reduce-results")
    reduce.add_argument("--query", default=DEFAULT_QUERY)
    reduce.add_argument("--provider-results", required=True)
    reduce.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    preflight = subparsers.add_parser("preflight-retained-artifacts")
    preflight.add_argument(
        "--artifact-dir",
        default=None,
        help=(
            "Defaults to output/ag_live_ordinary_search_candidate_01b under "
            "--repo-root."
        ),
    )
    preflight.add_argument("--repo-root", default=str(ROOT))
    preflight.add_argument(
        "--alternate-repo-root",
        action="append",
        default=[],
        help=(
            "Optional alternate checkout root used only for sanitized "
            "existence/readability metadata; contents are not read."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.operation == "prepare-request":
            packet = prepare_request(query=args.query, output_dir=args.output_dir)
        elif args.operation == "reduce-results":
            packet = reduce_results(
                query=args.query,
                provider_results_path=args.provider_results,
                output_dir=args.output_dir,
            )
        else:
            packet = preflight_retained_live_artifacts(
                artifact_dir=args.artifact_dir,
                repo_root=args.repo_root,
                alternate_repo_roots=args.alternate_repo_root,
            )
    except (
        LimitedLiveSearchCandidateError,
        ValueError,
        KeyError,
    ) as exc:
        print(
            f"refusing AG-LIMITED live search candidate operation: {exc}",
            file=sys.stderr,
        )
        return 2

    if args.operation == "preflight-retained-artifacts":
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0 if packet.get("decision") == RETAINED_ARTIFACT_PREFLIGHT_PASS else 2

    summary = {
        "phase": PHASE,
        "operation": args.operation,
        "output_dir": str(Path(args.output_dir)),
        "likely_acquisition_result": packet.get("likely_acquisition_result"),
        "sanitized_provider_result_count": packet.get(
            "sanitized_provider_result_count"
        ),
        "provider_calls_attempted": packet.get("provider_calls_attempted"),
        "provider_calls_completed": packet.get("provider_calls_completed"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
