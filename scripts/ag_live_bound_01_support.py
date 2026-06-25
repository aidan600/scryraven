from __future__ import annotations

import subprocess
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PHASE_ID = "AG-LIVE-BRIDGE-01"
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

LIVE_EXECUTION_STOP_REASON = "live_execution_not_enabled_in_ag_live_bridge_01"
UTILIZATION_RETRY_STOP_REASON = "orchestrator_utilization_retry_not_disableable"

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


def live_execution_blockers() -> list[str]:
    return [
        LIVE_EXECUTION_STOP_REASON,
        UTILIZATION_RETRY_STOP_REASON,
    ]


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


def build_fail_closed_live_packet(
    context: PreflightContext,
    *,
    stop_reasons: list[str],
) -> dict[str, Any]:
    packet = {
        "packet_marker": PACKET_MARKER,
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "proof_surface": PROOF_SURFACE,
        "dry_run": False,
        "confirm_live_product_run": True,
        "planned_live_dispatch": False,
        "run_id": context.run_id,
        "query": context.query,
        "mode": context.mode,
        "domain_allowlist": list(context.include_domains),
        "output_path": _relative_output_path(context),
        "caps_requested": context.caps.as_requested_dict(),
        "caps_observed": CappedDepsCounters.from_caps(context.caps).not_executed_dict(),
        "preflight": {
            "query_lock": context.query_lock,
            "output_path_safe": True,
            "output_path_gitignored": True,
            "domain_allowlist_present": True,
            "caps_valid": True,
            "live_path_armed": False,
        },
        "stop_reasons": list(stop_reasons),
        "primary_stop_reason": stop_reasons[0],
        "redaction_status": "sanitized_fail_closed",
        "forbidden_material_absent": forbidden_material_absent(),
        "live_only": None,
    }
    reject_forbidden_packet(packet)
    return packet


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
