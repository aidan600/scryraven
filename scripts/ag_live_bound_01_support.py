from __future__ import annotations

import subprocess
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.cap_enforcement import RunCapPolicy

PHASE_ID = "AG-LIVE-BRIDGE-01"
LIVE_PHASE_ID = "AG-LIVE-EXEC-01"
SCHEMA_VERSION = "ag_live_bound_01_bounded_product_runner_v1"
PACKET_MARKER = "LOCAL/UNTRACKED — DO NOT COMMIT"
PROOF_SURFACE = "ordinary_product_pipeline"
DEFAULT_OUTPUT = "output/ag_live_bound_01_packet.json"

PRIMARY_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for rel_tol and abs_tol in math.isclose()?"
)
BACKUP_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for start and step in itertools.count()?"
)
REQUIRED_MODE = "Balanced"
REQUIRED_DOMAIN = "docs.python.org"

LIVE_PACKET_SUCCESS = "success"
LIVE_PACKET_CAP_OVERFLOW = "cap_overflow"
LIVE_PACKET_PIPELINE_FAILURE = "pipeline_failure"
LIVE_PACKET_PRECHECK_FAILURE = "precheck_failure"
LIVE_PACKET_UNEXPECTED_FAILURE = "unexpected_failure"

PLANNED_CAPS: dict[str, int] = {
    "max_scryraven_runs": 1,
    "max_search_dispatches": 2,
    "max_fetch_read_operations": 3,
    "max_author_model_calls": 1,
    "max_smart_search_judgment_model_calls": 0,
    "max_independent_manual_source_checks": 1,
    "max_retries": 0,
}

FORBIDDEN_PACKET_KEYS = frozenset(
    """
    prompt raw_prompt prompt_text request_text raw_request_text model_request_text
    provider_payload raw_provider_payload raw_payload model_response
    raw_model_response raw_response private_log db_row cache full_trace secret
    api_key token execution_trace
    """.split()
)

AUTHOR_MODEL_PHASES = frozenset({"author", "author_handoff"})
SMART_SEARCH_JUDGMENT_PHASE_MARKERS = ("search_judgment", "smart_search_judgment")


class AgLiveBoundPreflightError(ValueError):
    """Raised when AG-LIVE-BOUND preflight validation fails."""


class AgLiveBoundPacketError(ValueError):
    """Raised when a packet contains forbidden material."""


@dataclass(frozen=True, slots=True)
class AgLiveBoundCaps:
    max_scryraven_runs: int = 1
    max_search_dispatches: int = 2
    max_fetch_read_operations: int = 3
    max_author_model_calls: int = 1
    max_smart_search_judgment_model_calls: int = 0
    max_independent_manual_source_checks: int = 1
    max_retries: int = 0

    def as_requested_dict(self) -> dict[str, int]:
        return {
            "max_scryraven_runs": self.max_scryraven_runs,
            "max_search_dispatches": self.max_search_dispatches,
            "max_fetch_read_operations": self.max_fetch_read_operations,
            "max_author_model_calls": self.max_author_model_calls,
            "max_smart_search_judgment_model_calls": (
                self.max_smart_search_judgment_model_calls
            ),
            "max_independent_manual_source_checks": (
                self.max_independent_manual_source_checks
            ),
            "max_retries": self.max_retries,
        }

    def to_run_cap_policy(self) -> RunCapPolicy:
        return RunCapPolicy(
            max_search_dispatches=self.max_search_dispatches,
            max_fetch_read_operations=self.max_fetch_read_operations,
            max_author_model_calls=self.max_author_model_calls,
            max_smart_search_judgment_model_calls=(
                self.max_smart_search_judgment_model_calls
            ),
            max_retries=self.max_retries,
        )

    @classmethod
    def from_requested(cls, requested: Mapping[str, int]) -> AgLiveBoundCaps:
        return cls(
            max_scryraven_runs=int(requested["max_scryraven_runs"]),
            max_search_dispatches=int(requested["max_search_dispatches"]),
            max_fetch_read_operations=int(requested["max_fetch_read_operations"]),
            max_author_model_calls=int(requested["max_author_model_calls"]),
            max_smart_search_judgment_model_calls=int(
                requested["max_smart_search_judgment_model_calls"]
            ),
            max_independent_manual_source_checks=int(
                requested["max_independent_manual_source_checks"]
            ),
            max_retries=int(requested["max_retries"]),
        )


@dataclass
class CappedDispatchCounter:
    name: str
    max_calls: int
    count: int = 0

    def mark(self, *, amount: int = 1) -> None:
        self.count += amount
        if self.count > self.max_calls:
            raise RuntimeError(f"{self.name} budget exceeded")


@dataclass
class CappedDepsCounters:
    search_dispatches: CappedDispatchCounter
    fetch_read_operations: CappedDispatchCounter
    author_model_calls: CappedDispatchCounter
    smart_search_judgment_model_calls: CappedDispatchCounter
    retries: CappedDispatchCounter

    @classmethod
    def from_caps(cls, caps: AgLiveBoundCaps) -> CappedDepsCounters:
        return cls(
            search_dispatches=CappedDispatchCounter(
                "search_dispatch",
                caps.max_search_dispatches,
            ),
            fetch_read_operations=CappedDispatchCounter(
                "fetch_read_operation",
                caps.max_fetch_read_operations,
            ),
            author_model_calls=CappedDispatchCounter(
                "author_model_call",
                caps.max_author_model_calls,
            ),
            smart_search_judgment_model_calls=CappedDispatchCounter(
                "smart_search_judgment_model_call",
                caps.max_smart_search_judgment_model_calls,
            ),
            retries=CappedDispatchCounter("retry", caps.max_retries),
        )

    def observed_dict(self, *, enforcement: str) -> dict[str, Any]:
        return {
            "scryraven_runs": 0,
            "search_dispatches": self.search_dispatches.count,
            "fetch_read_operations": self.fetch_read_operations.count,
            "author_model_calls": self.author_model_calls.count,
            "smart_search_judgment_model_calls": (
                self.smart_search_judgment_model_calls.count
            ),
            "independent_manual_source_checks": 0,
            "retries": self.retries.count,
            "enforcement": enforcement,
        }

    def not_executed_dict(self) -> dict[str, Any]:
        return {
            "scryraven_runs": 0,
            "search_dispatches": 0,
            "fetch_read_operations": 0,
            "author_model_calls": 0,
            "smart_search_judgment_model_calls": 0,
            "independent_manual_source_checks": 0,
            "retries": 0,
            "enforcement": "not_executed",
        }


@dataclass(frozen=True, slots=True)
class WrappedRunCallables:
    process_search_queries: Callable[..., Any]
    fetch_linkup_precision_block: Callable[..., Any]
    ask_model: Callable[..., Any]
    counters: CappedDepsCounters


@dataclass(frozen=True, slots=True)
class PreflightContext:
    root: Path
    query: str
    query_lock: str
    mode: str
    include_domains: list[str]
    output_path: Path
    caps: AgLiveBoundCaps
    run_id: str
    confirm_live_product_run: bool


def resolve_repo_root(start: Path) -> Path:
    return start.resolve().parents[1] if start.name.endswith(".py") else start.resolve()


def resolve_output_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def is_gitignored(root: Path, path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(path)],
        check=False,
        capture_output=True,
        cwd=root,
        text=True,
    )
    return result.returncode == 0


def is_allowed_output_path(root: Path, path: Path) -> bool:
    output_dir = (root / "output").resolve()
    try:
        path.relative_to(output_dir)
    except ValueError:
        return False
    return is_gitignored(root, path)


def parse_domains(raw: str) -> list[str]:
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def validate_caps_requested(requested: Mapping[str, int]) -> AgLiveBoundCaps:
    missing = [key for key in PLANNED_CAPS if key not in requested]
    if missing:
        raise AgLiveBoundPreflightError(
            f"refusing run: missing required cap fields: {', '.join(missing)}"
        )
    mismatched = [
        key
        for key, expected in PLANNED_CAPS.items()
        if int(requested[key]) != expected
    ]
    if mismatched:
        raise AgLiveBoundPreflightError(
            "refusing run: caps must match AG-LIVE-BOUND-01 planned values exactly"
        )
    return AgLiveBoundCaps.from_requested(requested)


def validate_query_lock(
    query: str,
    *,
    approved_backup_query: bool,
) -> str:
    normalized = query.strip()
    if not normalized:
        raise AgLiveBoundPreflightError("refusing run: empty query")
    if normalized == PRIMARY_QUERY:
        return "primary"
    if normalized == BACKUP_QUERY and approved_backup_query:
        return "backup"
    raise AgLiveBoundPreflightError(
        "refusing run: query must match the AG-LIVE-BOUND-01 primary query exactly "
        "or the approved backup query with --approved-backup-query"
    )


def validate_mode(mode: str) -> None:
    if mode != REQUIRED_MODE:
        raise AgLiveBoundPreflightError(
            f"refusing run: mode must be {REQUIRED_MODE!r}"
        )


def validate_domain_allowlist(include_domains: list[str]) -> None:
    if REQUIRED_DOMAIN not in include_domains:
        raise AgLiveBoundPreflightError(
            f"refusing run: --include-domains must include {REQUIRED_DOMAIN!r}"
        )


def build_preflight_context(
    *,
    root: Path,
    query: str,
    mode: str,
    include_domains: list[str],
    output_path: Path,
    caps: AgLiveBoundCaps,
    run_id: str | None,
    confirm_live_product_run: bool,
    approved_backup_query: bool,
) -> PreflightContext:
    query_lock = validate_query_lock(
        query,
        approved_backup_query=approved_backup_query,
    )
    validate_mode(mode)
    validate_domain_allowlist(include_domains)
    if not is_allowed_output_path(root, output_path):
        raise AgLiveBoundPreflightError(
            "refusing run: output path must be under ignored repo output/ and "
            "gitignored"
        )
    return PreflightContext(
        root=root,
        query=query.strip(),
        query_lock=query_lock,
        mode=mode,
        include_domains=include_domains,
        output_path=output_path,
        caps=caps,
        run_id=run_id or str(uuid.uuid4()),
        confirm_live_product_run=confirm_live_product_run,
    )


def reject_forbidden_packet(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_PACKET_KEYS:
                raise AgLiveBoundPacketError(
                    f"forbidden AG-LIVE-BOUND packet field: {key}"
                )
            reject_forbidden_packet(child)
    elif isinstance(value, list | tuple | set):
        for child in value:
            reject_forbidden_packet(child)


def forbidden_material_absent() -> dict[str, bool]:
    return {
        "absent_env_contents": True,
        "absent_api_keys": True,
        "absent_broker_tokens": True,
        "absent_raw_provider_payloads": True,
        "absent_raw_prompts": True,
        "absent_raw_model_requests": True,
        "absent_raw_model_responses": True,
        "absent_private_logs": True,
        "absent_db_cache_rows": True,
        "absent_full_raw_traces": True,
    }


def no_retention_booleans() -> dict[str, bool]:
    return {
        "raw_provider_payloads_retained": False,
        "raw_prompts_retained": False,
        "raw_model_requests_retained": False,
        "raw_model_responses_retained": False,
        "private_logs_retained": False,
        "db_cache_rows_retained_in_packet": False,
        "full_raw_traces_retained": False,
    }


def build_dry_run_packet(context: PreflightContext) -> dict[str, Any]:
    packet = {
        "packet_marker": PACKET_MARKER,
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "proof_surface": PROOF_SURFACE,
        "dry_run": True,
        "confirm_live_product_run": False,
        "planned_live_dispatch": False,
        "run_id": context.run_id,
        "query": context.query,
        "mode": context.mode,
        "domain_allowlist": list(context.include_domains),
        "output_path": _relative_output_path(context),
        "caps_requested": context.caps.as_requested_dict(),
        "caps_observed": CappedDepsCounters.from_caps(context.caps).not_executed_dict(),
        "cap_enforcement_product_path": {
            "policy_surface": "RunConfig.cap_policy",
            "runtime_consumer": "run_pipeline",
            "script_owns_cap_authority": False,
            "product_policy_constructible": True,
        },
        "preflight": {
            "query_lock": context.query_lock,
            "output_path_safe": True,
            "output_path_gitignored": True,
            "domain_allowlist_present": True,
            "caps_valid": True,
            "live_path_armed": False,
        },
        "redaction_status": "sanitized_plan_only",
        "forbidden_material_absent": forbidden_material_absent(),
        "live_only": None,
    }
    reject_forbidden_packet(packet)
    return packet


def build_live_success_packet(
    context: PreflightContext,
    *,
    outcome: Any,
    cap_policy: RunCapPolicy,
) -> dict[str, Any]:
    trace = _mapping_or_empty(getattr(outcome, "execution_trace", None))
    cited_source_ids = _cited_source_ids(trace)
    packet = {
        **_live_packet_base(context, cap_policy=cap_policy),
        "success_classification": LIVE_PACKET_SUCCESS,
        "planned_live_dispatch": True,
        "run_pipeline_call_count": 1,
        "final_answer_text": str(getattr(outcome, "report", "") or ""),
        "cited_source_ids": cited_source_ids,
        "cited_urls": _cited_urls(outcome, cited_source_ids),
        "source_ids_available": bool(cited_source_ids),
        "sanitized_projection_summaries": _sanitized_projection_summaries(trace),
        "failure_summary": None,
        "live_only": {
            "ordinary_product_path": True,
            "runtime_consumer": "run_pipeline",
            "run_config_cap_policy": True,
        },
    }
    reject_forbidden_packet(packet)
    return packet


def build_live_failure_packet(
    context: PreflightContext,
    *,
    cap_policy: RunCapPolicy,
    classification: str,
    failure_reason: str,
    run_pipeline_call_count: int,
) -> dict[str, Any]:
    packet = {
        **_live_packet_base(context, cap_policy=cap_policy),
        "success_classification": classification,
        "planned_live_dispatch": run_pipeline_call_count > 0,
        "run_pipeline_call_count": run_pipeline_call_count,
        "final_answer_text": "",
        "cited_source_ids": [],
        "cited_urls": [],
        "source_ids_available": False,
        "sanitized_projection_summaries": {
            "component_binding": {"available": False},
            "component_coverage": {"available": False},
            "sufficiency": {"available": False},
            "final_answer_packet": {"available": False},
            "author_posture": {"available": False},
        },
        "failure_summary": {
            "reason": failure_reason,
            "classification": classification,
        },
        "live_only": {
            "ordinary_product_path": run_pipeline_call_count > 0,
            "runtime_consumer": "run_pipeline",
            "run_config_cap_policy": True,
        },
    }
    reject_forbidden_packet(packet)
    return packet


def caps_observed_from_policy(policy: RunCapPolicy) -> dict[str, Any]:
    observed = policy.observed_counts()
    return {
        "scryraven_runs": 1,
        "search_dispatches": observed["search_dispatches"],
        "fetch_read_operations": observed["fetch_read_operations"],
        "author_model_calls": observed["author_model_calls"],
        "smart_search_judgment_model_calls": (
            observed["smart_search_judgment_model_calls"]
        ),
        "independent_manual_source_checks": 0,
        "retries": observed["retries"],
        "enforcement": observed["enforcement"],
        "facts": list(policy.facts),
    }


def write_packet(path: Path, packet: Mapping[str, Any]) -> None:
    import json

    reject_forbidden_packet(packet)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(packet, indent=2, sort_keys=True)
    path.write_text(rendered + "\n", encoding="utf-8")


def _relative_output_path(context: PreflightContext) -> str:
    try:
        return str(context.output_path.relative_to(context.root))
    except ValueError:
        return str(context.output_path)


def _live_packet_base(
    context: PreflightContext,
    *,
    cap_policy: RunCapPolicy,
) -> dict[str, Any]:
    return {
        "packet_marker": PACKET_MARKER,
        "schema_version": SCHEMA_VERSION,
        "phase_id": LIVE_PHASE_ID,
        "proof_surface": PROOF_SURFACE,
        "dry_run": False,
        "confirm_live_product_run": True,
        "run_id": context.run_id,
        "query": context.query,
        "mode": context.mode,
        "domain_allowlist": list(context.include_domains),
        "output_path": _relative_output_path(context),
        "caps_requested": context.caps.as_requested_dict(),
        "caps_observed": caps_observed_from_policy(cap_policy),
        "cap_enforcement_product_path": {
            "policy_surface": "RunConfig.cap_policy",
            "runtime_consumer": "run_pipeline",
            "script_owns_cap_authority": False,
            "product_policy_constructible": True,
        },
        "preflight": {
            "query_lock": context.query_lock,
            "output_path_safe": True,
            "output_path_gitignored": True,
            "domain_allowlist_present": True,
            "caps_valid": True,
            "live_path_armed": True,
        },
        "redaction_status": "sanitized_live_result",
        "forbidden_material_absent": forbidden_material_absent(),
        "no_retention": no_retention_booleans(),
    }


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _cited_source_ids(trace: Mapping[str, Any]) -> list[str]:
    ids = _string_list(trace.get("final_answer_source_ids_used"))
    if ids:
        return ids
    packet = _mapping_or_empty(trace.get("final_answer_packet"))
    for key in ("citation_eligible_source_ids", "source_ids"):
        ids = _string_list(packet.get(key))
        if ids:
            return ids
    return []


def _cited_urls(outcome: Any, cited_source_ids: Sequence[str]) -> list[str]:
    cited_id_set = {str(item) for item in cited_source_ids}
    urls: list[str] = []
    for passage in getattr(outcome, "top_passages", []) or []:
        if not isinstance(passage, Mapping):
            continue
        source_id = str(passage.get("source_id") or "")
        if cited_id_set and source_id and source_id not in cited_id_set:
            continue
        url = str(passage.get("url") or "").strip()
        if url and url not in urls:
            urls.append(url)
    if urls:
        return urls
    return _string_list(getattr(outcome, "seen_urls", []) or [])


def _sanitized_projection_summaries(trace: Mapping[str, Any]) -> dict[str, Any]:
    packet = _mapping_or_empty(trace.get("final_answer_packet"))
    return {
        "component_binding": _component_binding_summary(packet),
        "component_coverage": _component_coverage_summary(packet),
        "sufficiency": _sufficiency_summary(trace, packet),
        "final_answer_packet": _final_answer_packet_summary(packet),
        "author_posture": _author_posture_summary(trace, packet),
    }


def _component_binding_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping_or_empty(packet.get("semantic_evidence_authority_manifest"))
    return {
        "available": bool(manifest),
        "semantic_packet_evidence_binding_available": manifest.get(
            "semantic_packet_evidence_binding_available"
        ),
        "semantic_packet_evidence_binding_count": manifest.get(
            "semantic_packet_evidence_binding_count"
        ),
        "content_refs_available": manifest.get("content_refs_available"),
        "coverage_refs_available": manifest.get("coverage_refs_available"),
    }


def _component_coverage_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    coverage = _mapping_or_empty(packet.get("semantic_content_coverage_ref"))
    return {
        "available": bool(coverage),
        "component_ref_count": coverage.get("component_ref_count"),
        "coverage_record_ref_count": coverage.get("coverage_record_ref_count"),
        "semantic_observation_ref_count": coverage.get("semantic_observation_ref_count"),
        "sanitized_content_ref_count": coverage.get("sanitized_content_ref_count"),
    }


def _sufficiency_summary(
    trace: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "available": any(
            key in trace
            for key in (
                "evidence_sufficient",
                "synth_was_insufficient",
                "synth_sufficient_first_pass",
            )
        )
        or "sufficiency_decision" in packet,
        "evidence_sufficient": trace.get("evidence_sufficient"),
        "synth_was_insufficient": trace.get("synth_was_insufficient"),
        "synth_sufficient_first_pass": trace.get("synth_sufficient_first_pass"),
        "sufficiency_decision": packet.get("sufficiency_decision"),
    }


def _final_answer_packet_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "available": bool(packet),
        "canonical_state": packet.get("canonical_state"),
        "trace_mode": packet.get("trace_mode"),
        "readiness_status": packet.get("readiness_status"),
        "author_payload_status": packet.get("author_payload_status"),
        "citation_eligible_source_ids": _string_list(
            packet.get("citation_eligible_source_ids")
        ),
    }


def _author_posture_summary(
    trace: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    failure_card = _mapping_or_empty(trace.get("failure_card"))
    return {
        "available": bool(trace or packet),
        "answer_class": trace.get("answer_class"),
        "response_displayable": trace.get("response_displayable"),
        "author_system_prompt_key": trace.get("author_system_prompt_key"),
        "failure_card_show": failure_card.get("show"),
        "failure_card_reason": failure_card.get("reason"),
        "final_answer_readiness_status": packet.get("readiness_status"),
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Sequence):
        values = [str(item) for item in value]
    else:
        values = []
    result: list[str] = []
    for item in values:
        clean = str(item or "").strip()
        if clean and clean not in result:
            result.append(clean)
    return result


def _is_smart_search_judgment_phase(cost_phase: str | None) -> bool:
    phase = (cost_phase or "").casefold()
    return any(marker in phase for marker in SMART_SEARCH_JUDGMENT_PHASE_MARKERS)


def _is_author_model_phase(cost_phase: str | None) -> bool:
    return (cost_phase or "").casefold() in AUTHOR_MODEL_PHASES


def compose_capped_run_callables(
    *,
    process_search_queries: Callable[..., Any],
    fetch_linkup_precision_block: Callable[..., Any],
    ask_model: Callable[..., Any],
    caps: AgLiveBoundCaps,
) -> WrappedRunCallables:
    counters = CappedDepsCounters.from_caps(caps)

    def wrapped_process_search_queries(*args: Any, **kwargs: Any) -> Any:
        counters.search_dispatches.mark()
        return process_search_queries(*args, **kwargs)

    def wrapped_fetch_linkup_precision_block(*args: Any, **kwargs: Any) -> Any:
        counters.fetch_read_operations.mark()
        return fetch_linkup_precision_block(*args, **kwargs)

    def wrapped_ask_model(*args: Any, **kwargs: Any) -> Any:
        cost_phase = kwargs.get("cost_phase")
        if _is_smart_search_judgment_phase(cost_phase):
            counters.smart_search_judgment_model_calls.mark()
        if _is_author_model_phase(cost_phase):
            counters.author_model_calls.mark()
        return ask_model(*args, **kwargs)

    return WrappedRunCallables(
        process_search_queries=wrapped_process_search_queries,
        fetch_linkup_precision_block=wrapped_fetch_linkup_precision_block,
        ask_model=wrapped_ask_model,
        counters=counters,
    )


def unwrap_no_retry_callable(fn: Callable[..., Any]) -> Callable[..., Any]:
    return getattr(fn, "__wrapped__", fn)
