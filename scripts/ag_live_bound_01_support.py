from __future__ import annotations

import subprocess
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.cap_enforcement import RunCapPolicy
from core.multicomponent_component_admission import (
    component_analyst_input_binding_mismatch_from_exception,
    project_component_analyst_input_binding_mismatch_v1,
)
from core.searchos_slice_a_product_runtime import (
    SEARCHOS_SLICE_A_TRACE_KEY,
    build_bounded_searchos_n1_causal_projection,
)
from core.validation_observability import (
    build_subject_budget_summary,
    build_validation_observability,
    extract_cited_urls_from_text,
)
from core.validation_profiles import (
    AG_LIVE_BOUND_BACKUP_QUERY,
    AG_LIVE_BOUND_PRIMARY_QUERY,
    AG_LIVE_SMOKE,
    PRODUCT_CAP_POLICY_SURFACE,
    PRODUCT_RUNTIME_CONSUMER,
    PRODUCT_SOURCE_CUSTODY_POLICY_SURFACE,
    get_validation_profile,
)

PHASE_ID = "AG-LIVE-BRIDGE-01"
LIVE_PHASE_ID = "AG-LIVE-EXEC-01"
DEFAULT_PROFILE_NAME = AG_LIVE_SMOKE
_DEFAULT_PROFILE = get_validation_profile(DEFAULT_PROFILE_NAME)
SCHEMA_VERSION = _DEFAULT_PROFILE.packet_schema
PACKET_MARKER = "LOCAL/UNTRACKED — DO NOT COMMIT"
PROOF_SURFACE = "ordinary_product_pipeline"
DEFAULT_OUTPUT = "output/ag_live_bound_01_packet.json"

PRIMARY_QUERY = AG_LIVE_BOUND_PRIMARY_QUERY
BACKUP_QUERY = AG_LIVE_BOUND_BACKUP_QUERY
REQUIRED_MODE = _DEFAULT_PROFILE.required_mode
REQUIRED_DOMAIN = _DEFAULT_PROFILE.required_include_domains[0]

LIVE_PACKET_SUCCESS = "success"
LIVE_PACKET_CAP_OVERFLOW = "cap_overflow"
LIVE_PACKET_PIPELINE_FAILURE = "pipeline_failure"
LIVE_PACKET_PRECHECK_FAILURE = "precheck_failure"
LIVE_PACKET_UNEXPECTED_FAILURE = "unexpected_failure"
FAILURE_OBSERVABILITY_SCHEMA_VERSION = "ag_live_failure_observability_v1"
MAX_SAFE_ERROR_MESSAGE_CHARS = 240

PLANNED_CAPS: dict[str, int] = _DEFAULT_PROFILE.cap_policy.as_requested_dict()

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
SENSITIVE_FAILURE_MESSAGE_MARKERS = (
    ".env",
    "api_key",
    "bearer",
    "cache",
    "db_row",
    "exa_api_key",
    "full_trace",
    "linkup_api_key",
    "model_response",
    "openai_api_key",
    "openrouter_api_key",
    "private_log",
    "prompt_text",
    "provider_payload",
    "raw_model",
    "raw_payload",
    "raw_prompt",
    "raw_provider",
    "raw_response",
    "secret",
    "sk-",
    "tavily_api_key",
    "token",
    "traceback",
)
BLOCKED_FAP_SUMMARY_KEYS = (
    "schema_version",
    "blocked_fap",
    "packet_id",
    "status",
    "readiness_status",
    "readiness_reasons",
    "author_input_deferred",
    "blocked_before_author_input",
    "final_answer_allowed",
    "final_answer_posture",
    "sufficiency_decision",
    "missing_source_obligation_count",
    "partial_source_obligation_count",
    "satisfied_source_obligation_count",
    "source_bound_numeric_unknown_count",
    "mandatory_caveat_count",
    "prohibited_upgrade_count",
    "claim_postures",
    "component_blocked_summary",
)
BLOCKED_FAP_BOOLEAN_KEYS = frozenset(
    {
        "blocked_fap",
        "author_input_deferred",
        "blocked_before_author_input",
        "final_answer_allowed",
    }
)
BLOCKED_FAP_COUNT_KEYS = frozenset(
    {
        "missing_source_obligation_count",
        "partial_source_obligation_count",
        "satisfied_source_obligation_count",
        "source_bound_numeric_unknown_count",
        "mandatory_caveat_count",
        "prohibited_upgrade_count",
    }
)
BLOCKED_FAP_LIST_KEYS = frozenset({"readiness_reasons", "claim_postures"})
COMPONENT_BLOCKED_SUMMARY_KEYS = (
    "schema_version",
    "component_summary_available",
    "expected_component_count",
    "expected_answerable_component_count",
    "supported_component_count",
    "citation_bound_component_count",
    "evidence_bound_component_count",
    "source_obligation_satisfied_component_count",
    "missing_component_count",
    "expected_answerable_missing_component_count",
    "unsupported_component_count",
    "unclear_component_count",
    "entangled_component_count",
    "source_bound_numeric_unknown_component_count",
    "full_component_success",
    "partial_user_answer_candidate",
    "semantic_partial_coverage_observed",
    "hard_block_candidate",
    "components",
)
COMPONENT_BLOCKED_SUMMARY_BOOLEAN_KEYS = frozenset(
    {
        "component_summary_available",
        "full_component_success",
        "partial_user_answer_candidate",
        "semantic_partial_coverage_observed",
        "hard_block_candidate",
    }
)
COMPONENT_BLOCKED_SUMMARY_COUNT_KEYS = frozenset(
    {
        "expected_component_count",
        "expected_answerable_component_count",
        "supported_component_count",
        "citation_bound_component_count",
        "evidence_bound_component_count",
        "source_obligation_satisfied_component_count",
        "missing_component_count",
        "expected_answerable_missing_component_count",
        "unsupported_component_count",
        "unclear_component_count",
        "entangled_component_count",
        "source_bound_numeric_unknown_component_count",
    }
)
COMPONENT_BLOCKED_ENTRY_KEYS = (
    "component_id",
    "component_digest",
    "safe_label",
    "status",
    "expected_answerable",
    "answered_or_answerable_from_evidence",
    "blocker_reason_codes",
    "satisfied_source_obligation_count",
    "missing_source_obligation_count",
    "partial_source_obligation_count",
    "citation_binding_available",
    "evidence_binding_available",
)
COMPONENT_BLOCKED_ENTRY_BOOLEAN_KEYS = frozenset(
    {
        "expected_answerable",
        "answered_or_answerable_from_evidence",
        "citation_binding_available",
        "evidence_binding_available",
    }
)
COMPONENT_BLOCKED_ENTRY_COUNT_KEYS = frozenset(
    {
        "satisfied_source_obligation_count",
        "missing_source_obligation_count",
        "partial_source_obligation_count",
    }
)
COMPONENT_BLOCKED_ENTRY_LIST_KEYS = frozenset({"blocker_reason_codes"})


class AgLiveBoundPreflightError(ValueError):
    """Raised when AG-LIVE-BOUND preflight validation fails."""


class AgLiveBoundPacketError(ValueError):
    """Raised when a packet contains forbidden material."""


@dataclass(frozen=True, slots=True)
class AgLiveBoundCaps:
    max_scryraven_runs: int = 1
    # None means this ordinary runner records the observation without adding a
    # logical role cap. Explicit resource experiments may supply an integer.
    max_search_dispatches: int | None = None
    max_fetch_read_operations: int | None = None
    max_author_model_calls: int | None = None
    max_smart_search_judgment_model_calls: int | None = None
    max_independent_manual_source_checks: int | None = None
    # Retry/replacement authority is separate from role observations. Ordinary
    # dogfood explicitly authorizes no retry unless a resource experiment says
    # otherwise.
    max_retries: int = 0

    def as_requested_dict(self) -> dict[str, int]:
        values: dict[str, int] = {
            "max_scryraven_runs": self.max_scryraven_runs,
        }
        for field_name in (
            "max_search_dispatches",
            "max_fetch_read_operations",
            "max_author_model_calls",
            "max_smart_search_judgment_model_calls",
            "max_independent_manual_source_checks",
            "max_retries",
        ):
            value = getattr(self, field_name)
            if value is not None:
                values[field_name] = value
        return values

    def to_run_cap_policy(self) -> RunCapPolicy:
        logical_overrides: dict[str, int] = {}
        for field_name in (
            "max_search_dispatches",
            "max_fetch_read_operations",
            "max_author_model_calls",
            "max_smart_search_judgment_model_calls",
            "max_retries",
        ):
            value = getattr(self, field_name)
            if value is not None:
                logical_overrides[field_name] = value
        return RunCapPolicy(**logical_overrides)

    @classmethod
    def from_requested(cls, requested: Mapping[str, int]) -> AgLiveBoundCaps:
        def optional_int(field_name: str) -> int | None:
            value = requested.get(field_name)
            return int(value) if value is not None else None

        return cls(
            max_scryraven_runs=int(requested["max_scryraven_runs"]),
            max_search_dispatches=optional_int("max_search_dispatches"),
            max_fetch_read_operations=optional_int("max_fetch_read_operations"),
            max_author_model_calls=optional_int("max_author_model_calls"),
            max_smart_search_judgment_model_calls=optional_int(
                "max_smart_search_judgment_model_calls"
            ),
            max_independent_manual_source_checks=optional_int(
                "max_independent_manual_source_checks"
            ),
            max_retries=(
                int(requested["max_retries"])
                if "max_retries" in requested
                else 0
            ),
        )


@dataclass
class CappedDispatchCounter:
    name: str
    max_calls: int | None
    count: int = 0

    def mark(self, *, amount: int = 1) -> None:
        self.count += amount
        if self.max_calls is not None and self.count > self.max_calls:
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
    profile_name: str
    query: str
    query_lock: str
    mode: str
    include_domains: list[str]
    output_path: Path
    caps: AgLiveBoundCaps
    run_id: str
    confirm_live_product_run: bool
    output_path_gitignored: bool = True
    output_path_external_confined: bool = False


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


def is_allowed_output_path(
    root: Path,
    path: Path,
    *,
    external_output_root: Path | None = None,
) -> bool:
    output_dir = (root / "output").resolve()
    try:
        path.relative_to(output_dir)
    except ValueError:
        pass
    else:
        return is_gitignored(root, path)
    if external_output_root is None:
        return False
    external_root = external_output_root.resolve()
    if not external_root.is_dir():
        return False
    try:
        external_root.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        return False
    try:
        path.relative_to(external_root)
    except ValueError:
        return False
    return path != external_root and path.parent.is_dir()


def parse_domains(raw: str) -> list[str]:
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def validate_caps_requested(
    requested: Mapping[str, int],
    *,
    profile_name: str = DEFAULT_PROFILE_NAME,
) -> AgLiveBoundCaps:
    profile = get_validation_profile(profile_name)
    planned_caps = profile.cap_policy.as_requested_dict()
    known_caps = {
        "max_scryraven_runs",
        "max_search_dispatches",
        "max_fetch_read_operations",
        "max_author_model_calls",
        "max_smart_search_judgment_model_calls",
        "max_independent_manual_source_checks",
        "max_retries",
    }
    unknown = sorted(set(requested).difference(known_caps))
    if unknown:
        raise AgLiveBoundPreflightError(
            f"refusing run: unknown cap fields: {', '.join(unknown)}"
        )
    invalid = [
        key
        for key, value in requested.items()
        if isinstance(value, bool) or not isinstance(value, int) or value < 0
    ]
    if invalid:
        raise AgLiveBoundPreflightError(
            f"refusing run: cap fields must be non-negative integers: "
            f"{', '.join(sorted(invalid))}"
        )
    missing = [key for key in planned_caps if key not in requested]
    if missing:
        raise AgLiveBoundPreflightError(
            f"refusing run: missing required cap fields: {', '.join(missing)}"
        )
    mismatched = [
        key
        for key, expected in planned_caps.items()
        if int(requested[key]) != expected
    ]
    if mismatched:
        raise AgLiveBoundPreflightError(
            f"refusing run: caps must match {profile.name} planned values exactly"
        )
    return AgLiveBoundCaps.from_requested(requested)


def validate_query_lock(
    query: str,
    *,
    approved_backup_query: bool,
    profile_name: str = DEFAULT_PROFILE_NAME,
    requested_query_id: str | None = None,
) -> str:
    profile = get_validation_profile(profile_name)
    if not profile.supports_direct_runner():
        raise AgLiveBoundPreflightError(
            f"refusing run: profile {profile.name!r} is not direct-runner ready"
        )
    normalized = query.strip()
    if not normalized:
        raise AgLiveBoundPreflightError("refusing run: empty query")
    fixed_query_id = profile.query_id_for(normalized)
    if fixed_query_id is not None:
        if requested_query_id is not None and requested_query_id != fixed_query_id:
            raise AgLiveBoundPreflightError(
                "refusing run: query ID does not match the immutable fixed query"
            )
        return fixed_query_id
    if profile.fixed_queries:
        raise AgLiveBoundPreflightError(
            f"refusing run: query must match one immutable {profile.name} query exactly"
        )
    if requested_query_id is not None:
        raise AgLiveBoundPreflightError(
            "refusing run: --query-id is valid only for a fixed-query profile"
        )
    if normalized == profile.primary_query:
        return "primary"
    if normalized == profile.backup_query and approved_backup_query:
        return "backup"
    raise AgLiveBoundPreflightError(
        f"refusing run: query must match the {profile.name} primary query exactly "
        "or the approved backup query with --approved-backup-query"
    )


def validate_mode(mode: str, *, profile_name: str = DEFAULT_PROFILE_NAME) -> None:
    profile = get_validation_profile(profile_name)
    if mode != profile.required_mode:
        raise AgLiveBoundPreflightError(
            f"refusing run: mode must be {profile.required_mode!r}"
        )


def validate_domain_allowlist(
    include_domains: list[str],
    *,
    profile_name: str = DEFAULT_PROFILE_NAME,
) -> None:
    profile = get_validation_profile(profile_name)
    missing = [
        domain for domain in profile.required_include_domains if domain not in include_domains
    ]
    if missing:
        raise AgLiveBoundPreflightError(
            "refusing run: --include-domains must include "
            + ", ".join(repr(domain) for domain in missing)
        )


def build_preflight_context(
    *,
    root: Path,
    profile_name: str = DEFAULT_PROFILE_NAME,
    query: str,
    mode: str,
    include_domains: list[str],
    output_path: Path,
    caps: AgLiveBoundCaps,
    run_id: str | None,
    confirm_live_product_run: bool,
    approved_backup_query: bool,
    requested_query_id: str | None = None,
    external_output_root: Path | None = None,
) -> PreflightContext:
    profile = get_validation_profile(profile_name)
    query_lock = validate_query_lock(
        query,
        approved_backup_query=approved_backup_query,
        profile_name=profile.name,
        requested_query_id=requested_query_id,
    )
    validate_mode(mode, profile_name=profile.name)
    validate_domain_allowlist(include_domains, profile_name=profile.name)
    output_path_gitignored = is_allowed_output_path(root, output_path)
    output_path_external_confined = (
        external_output_root is not None
        and is_allowed_output_path(
            root,
            output_path,
            external_output_root=external_output_root,
        )
        and not output_path_gitignored
    )
    if not (output_path_gitignored or output_path_external_confined):
        raise AgLiveBoundPreflightError(
            "refusing run: output path must be under ignored repo output/ and "
            "gitignored, or confined under the explicit external output root"
        )
    return PreflightContext(
        root=root,
        profile_name=profile.name,
        query=query.strip(),
        query_lock=query_lock,
        mode=mode,
        include_domains=include_domains,
        output_path=output_path,
        output_path_gitignored=output_path_gitignored,
        output_path_external_confined=output_path_external_confined,
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


def build_failure_observability(
    *,
    safe_phase: str,
    exc: BaseException,
) -> dict[str, Any]:
    """Return a bounded no-raw exception envelope for runner boundary failures."""

    safe_error_type = type(exc).__name__
    safe_message, message_redacted = _safe_exception_message(exc)
    blocked_fap_summary = _blocked_fap_summary_from_exception(exc)
    observability = {
        "schema_version": FAILURE_OBSERVABILITY_SCHEMA_VERSION,
        "safe_phase": _safe_error_token(safe_phase) or "unexpected",
        "safe_error_type": safe_error_type,
        "safe_error_code": _safe_error_code(
            safe_phase=safe_phase,
            safe_error_type=safe_error_type,
        ),
        "safe_error_message": safe_message,
        "safe_error_message_redacted": message_redacted,
        "raw_traceback_retained": False,
        "raw_exception_repr_retained": False,
        "raw_provider_payload_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_logs_retained": False,
        "db_cache_rows_retained": False,
        "secrets_returned": False,
    }
    if blocked_fap_summary:
        observability["blocked_fap_summary"] = blocked_fap_summary
    mismatch_diagnostic = component_analyst_input_binding_mismatch_from_exception(
        exc
    )
    if mismatch_diagnostic:
        observability["component_analyst_input_binding_mismatch_v1"] = (
            mismatch_diagnostic
        )
    return observability


def _safe_summary_text(value: Any, *, limit: int = 240) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:limit]


def _safe_summary_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        values = ()
    result: list[str] = []
    for item in values:
        clean = _safe_summary_text(item)
        if clean and clean not in result:
            result.append(clean)
    return result


def _safe_summary_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _blocked_fap_summary_from_exception(exc: BaseException) -> dict[str, Any]:
    raw = getattr(exc, "blocked_fap_summary", None)
    if not isinstance(raw, Mapping):
        metadata = getattr(exc, "safe_metadata", None)
        if isinstance(metadata, Mapping):
            raw = metadata.get("blocked_fap_summary")
    if not isinstance(raw, Mapping) or raw.get("blocked_fap") is not True:
        return {}
    summary: dict[str, Any] = {}
    for key in BLOCKED_FAP_SUMMARY_KEYS:
        if key not in raw:
            continue
        value = raw.get(key)
        if key == "component_blocked_summary":
            component_summary = _component_blocked_summary_from_raw(value)
            if component_summary:
                summary[key] = component_summary
        elif key in BLOCKED_FAP_BOOLEAN_KEYS:
            if isinstance(value, bool):
                summary[key] = value
        elif key in BLOCKED_FAP_COUNT_KEYS:
            count = _safe_summary_int(value)
            if count is not None:
                summary[key] = count
        elif key in BLOCKED_FAP_LIST_KEYS:
            values = _safe_summary_text_list(value)
            if values:
                summary[key] = values
        else:
            text = _safe_summary_text(value)
            if text is not None:
                summary[key] = text
    return summary if summary.get("blocked_fap") is True else {}


def _component_blocked_summary_from_raw(value: Any) -> dict[str, Any]:
    raw = _mapping_or_empty(value)
    if raw.get("component_summary_available") is not True:
        return {}
    summary: dict[str, Any] = {}
    for key in COMPONENT_BLOCKED_SUMMARY_KEYS:
        if key not in raw:
            continue
        item = raw.get(key)
        if key == "components":
            components = _component_blocked_entries_from_raw(item)
            if components:
                summary[key] = components
        elif key in COMPONENT_BLOCKED_SUMMARY_BOOLEAN_KEYS:
            if isinstance(item, bool):
                summary[key] = item
        elif key in COMPONENT_BLOCKED_SUMMARY_COUNT_KEYS:
            count = _safe_summary_int(item)
            if count is not None:
                summary[key] = count
        else:
            text = _safe_summary_text(item)
            if text is not None:
                summary[key] = text
    return summary if summary.get("component_summary_available") is True else {}


def _component_blocked_entries_from_raw(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    entries: list[dict[str, Any]] = []
    for raw_entry in value:
        entry_raw = _mapping_or_empty(raw_entry)
        if not entry_raw:
            continue
        entry: dict[str, Any] = {}
        for key in COMPONENT_BLOCKED_ENTRY_KEYS:
            if key not in entry_raw:
                continue
            item = entry_raw.get(key)
            if key in COMPONENT_BLOCKED_ENTRY_BOOLEAN_KEYS:
                if isinstance(item, bool):
                    entry[key] = item
            elif key in COMPONENT_BLOCKED_ENTRY_COUNT_KEYS:
                count = _safe_summary_int(item)
                if count is not None:
                    entry[key] = count
            elif key in COMPONENT_BLOCKED_ENTRY_LIST_KEYS:
                values = _safe_summary_text_list(item)
                if values:
                    entry[key] = values
            else:
                text = _safe_summary_text(item)
                if text is not None:
                    entry[key] = text
        if entry.get("component_id") and entry.get("status"):
            entries.append(entry)
    return entries


def source_custody_policy_request(profile_name: str) -> dict[str, Any] | None:
    profile = get_validation_profile(profile_name)
    if profile.source_custody_policy is None:
        return None
    return {
        "surface": profile.source_custody_policy_surface,
        "values": profile.source_custody_policy.as_requested_dict(),
    }


def source_custody_policy_product_path(profile_name: str) -> dict[str, Any]:
    profile = get_validation_profile(profile_name)
    return {
        "policy_surface": PRODUCT_SOURCE_CUSTODY_POLICY_SURFACE,
        "runtime_consumer": None,
        "expectation_recorded": profile.source_custody_policy is not None,
        "policy_enabled": False,
        "script_owns_source_custody_authority": False,
        "product_policy_constructible": False,
        "initial_discovery_transport_authority": False,
        "retirement_status": "historical_pre_selection_trigger_retired",
    }


def suppressed_ordinary_retention_posture(context: PreflightContext) -> dict[str, Any]:
    return {
        "ordinary_product_persistence": "suppressed_for_ag_live_bound_runner",
        "only_runner_artifact_written": True,
        "sanitized_packet_path": _relative_output_path(context),
        "ordinary_execution_jsonl_suppressed": True,
        "ordinary_kb_trigger_jsonl_suppressed": True,
        "ordinary_policy_journal_jsonl_suppressed": True,
        "sqlite_telemetry_suppressed": True,
        "ordinary_side_effect_paths_suppressed": [
            "output/ag_live_bound_01_execution_log.jsonl",
            "output/ag_live_bound_01_kb_triggers.jsonl",
            "output/ag_live_bound_01_policy_journal.jsonl",
            "proplex.db",
        ],
    }


def build_dry_run_packet(context: PreflightContext) -> dict[str, Any]:
    profile = get_validation_profile(context.profile_name)
    packet = {
        "packet_marker": PACKET_MARKER,
        "schema_version": profile.packet_schema,
        "phase_id": PHASE_ID,
        "validation_profile": profile.packet_identity(),
        "expected_packet_criteria": list(profile.expected_packet_criteria),
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
            "policy_surface": PRODUCT_CAP_POLICY_SURFACE,
            "runtime_consumer": PRODUCT_RUNTIME_CONSUMER,
            "script_owns_cap_authority": False,
            "product_policy_constructible": True,
        },
        "source_custody_policy_requested": source_custody_policy_request(
            context.profile_name
        ),
        "source_custody_policy_product_path": source_custody_policy_product_path(
            context.profile_name
        ),
        "subject_budget_summary": build_subject_budget_summary(
            validation_profile=profile,
            preflight_context=context,
            trace={},
        ),
        "preflight": {
            "query_lock": context.query_lock,
            "output_path_safe": True,
            "output_path_gitignored": context.output_path_gitignored,
            "output_path_external_confined": context.output_path_external_confined,
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
    run_config: Any | None = None,
) -> dict[str, Any]:
    trace = _mapping_or_empty(getattr(outcome, "execution_trace", None))
    final_answer_text = str(getattr(outcome, "report", "") or "")
    cited_source_ids = _cited_source_ids(trace)
    cited_urls = _cited_urls(outcome, cited_source_ids)
    if not cited_urls:
        cited_urls = extract_cited_urls_from_text(final_answer_text)
    profile = get_validation_profile(context.profile_name)
    sanitized_projection_summaries = _sanitized_projection_summaries(trace)
    causal_projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(
            trace.get(SEARCHOS_SLICE_A_TRACE_KEY) or {}
        ),
        enabled=True,
        expected_run_id=str(getattr(outcome, "run_id", "") or ""),
        expected_request_id=str(getattr(outcome, "session_id", "") or ""),
    )
    if causal_projection is not None:
        sanitized_projection_summaries["searchos_n1_causal_projection"] = (
            causal_projection
        )
    packet = {
        **_live_packet_base(context, cap_policy=cap_policy),
        "success_classification": LIVE_PACKET_SUCCESS,
        "planned_live_dispatch": True,
        "run_pipeline_call_count": 1,
        "final_answer_text": final_answer_text,
        "cited_source_ids": cited_source_ids,
        "cited_urls": cited_urls,
        "source_ids_available": bool(cited_source_ids),
        "sanitized_projection_summaries": sanitized_projection_summaries,
        "validation_observability": build_validation_observability(
            validation_profile=profile,
            preflight_context=context,
            run_config=run_config,
            outcome=outcome,
            cap_policy=cap_policy,
        ),
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
    run_config: Any | None = None,
    outcome: Any | None = None,
    failure_observability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    profile = get_validation_profile(context.profile_name)
    failure_summary: dict[str, Any] = {
        "reason": failure_reason,
        "classification": classification,
    }
    if failure_observability is not None:
        failure_summary.update(
            {
                "safe_phase": failure_observability.get("safe_phase"),
                "safe_error_type": failure_observability.get("safe_error_type"),
                "safe_error_code": failure_observability.get("safe_error_code"),
                "safe_error_message": failure_observability.get(
                    "safe_error_message"
                ),
                "safe_error_message_redacted": failure_observability.get(
                    "safe_error_message_redacted"
                ),
            }
        )
    blocked_fap_summary = (
        _mapping_or_empty(failure_observability.get("blocked_fap_summary"))
        if failure_observability is not None
        else {}
    )
    if blocked_fap_summary:
        failure_summary.update(
            {
                "blocked_fap": True,
                "blocked_fap_readiness_status": blocked_fap_summary.get(
                    "readiness_status"
                ),
                "blocked_fap_missing_source_obligation_count": (
                    blocked_fap_summary.get("missing_source_obligation_count")
                ),
            }
        )
    sanitized_projection_summaries = {
        "component_binding": {"available": False},
        "component_coverage": {"available": False},
        "sufficiency": {"available": False},
        "final_answer_packet": {"available": False},
        "author_posture": {"available": False},
    }
    if blocked_fap_summary:
        sanitized_projection_summaries["blocked_fap_summary"] = dict(
            blocked_fap_summary
        )
    mismatch_diagnostic = (
        project_component_analyst_input_binding_mismatch_v1(
            failure_observability.get("component_analyst_input_binding_mismatch_v1")
        )
        if failure_observability is not None
        else {}
    )
    if mismatch_diagnostic:
        sanitized_projection_summaries[
            "component_analyst_input_binding_mismatch_v1"
        ] = mismatch_diagnostic
    packet = {
        **_live_packet_base(context, cap_policy=cap_policy),
        "success_classification": classification,
        "planned_live_dispatch": run_pipeline_call_count > 0,
        "run_pipeline_call_count": run_pipeline_call_count,
        "final_answer_text": "",
        "cited_source_ids": [],
        "cited_urls": [],
        "source_ids_available": False,
        "sanitized_projection_summaries": sanitized_projection_summaries,
        "validation_observability": build_validation_observability(
            validation_profile=profile,
            preflight_context=context,
            run_config=run_config,
            outcome=outcome,
            cap_policy=cap_policy,
        ),
        "failure_summary": failure_summary,
        "live_only": {
            "ordinary_product_path": run_pipeline_call_count > 0,
            "runtime_consumer": "run_pipeline",
            "run_config_cap_policy": True,
        },
    }
    if failure_observability is not None:
        packet["failure_observability"] = dict(failure_observability)
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
    profile = get_validation_profile(context.profile_name)
    return {
        "packet_marker": PACKET_MARKER,
        "schema_version": profile.packet_schema,
        "phase_id": LIVE_PHASE_ID,
        "validation_profile": profile.packet_identity(),
        "expected_packet_criteria": list(profile.expected_packet_criteria),
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
            "policy_surface": PRODUCT_CAP_POLICY_SURFACE,
            "runtime_consumer": PRODUCT_RUNTIME_CONSUMER,
            "script_owns_cap_authority": False,
            "product_policy_constructible": True,
        },
        "source_custody_policy_requested": source_custody_policy_request(
            context.profile_name
        ),
        "source_custody_policy_product_path": source_custody_policy_product_path(
            context.profile_name
        ),
        "preflight": {
            "query_lock": context.query_lock,
            "output_path_safe": True,
            "output_path_gitignored": context.output_path_gitignored,
            "output_path_external_confined": context.output_path_external_confined,
            "domain_allowlist_present": True,
            "caps_valid": True,
            "live_path_armed": True,
        },
        "redaction_status": "sanitized_live_result",
        "forbidden_material_absent": forbidden_material_absent(),
        "no_retention": no_retention_booleans(),
        "retention_posture": suppressed_ordinary_retention_posture(context),
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
    if not cited_id_set:
        return []
    urls: list[str] = []
    for passage in getattr(outcome, "top_passages", []) or []:
        if not isinstance(passage, Mapping):
            continue
        source_id = str(passage.get("source_id") or "")
        if source_id and source_id not in cited_id_set:
            continue
        url = str(passage.get("url") or "").strip()
        if url and url not in urls:
            urls.append(url)
    return urls


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


def _safe_exception_message(exc: BaseException) -> tuple[str | None, bool]:
    message = " ".join(str(exc).split())
    if not message:
        return None, False
    lowered = message.casefold()
    if " at 0x" in lowered:
        return None, True
    if any(marker in lowered for marker in SENSITIVE_FAILURE_MESSAGE_MARKERS):
        return None, True
    if len(message) > MAX_SAFE_ERROR_MESSAGE_CHARS:
        message = message[: MAX_SAFE_ERROR_MESSAGE_CHARS - 3].rstrip() + "..."
    return message, False


def _safe_error_code(*, safe_phase: str, safe_error_type: str) -> str:
    phase = _safe_error_token(safe_phase)
    error_type = _safe_error_token(safe_error_type)
    if not phase or not error_type:
        return "unexpected_exception"
    return f"{phase}_{error_type}"


def _safe_error_token(value: str) -> str:
    token: list[str] = []
    previous_was_separator = True
    previous_was_lower_or_digit = False
    for char in str(value or ""):
        if char.isupper():
            if not previous_was_separator and previous_was_lower_or_digit:
                token.append("_")
            token.append(char.lower())
            previous_was_separator = False
            previous_was_lower_or_digit = False
        elif char.isalnum():
            token.append(char.lower())
            previous_was_separator = False
            previous_was_lower_or_digit = True
        elif not previous_was_separator:
            token.append("_")
            previous_was_separator = True
            previous_was_lower_or_digit = False
    return "".join(token).strip("_")


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
