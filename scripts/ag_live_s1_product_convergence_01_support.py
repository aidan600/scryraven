"""Offline-safe support for the bounded live S1 convergence campaign.

This module owns campaign-local accounting, confinement, and sanitization only.
It does not understand queries, select providers/models, acquire evidence, run a
semantic role, calculate an answer, or call ``run_pipeline``.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.cap_enforcement import RunCapExceeded
from core.cost_accounting import (
    MODEL_PRICING_USD_PER_1M,
    PROVIDER_PRICING_USD_PER_CALL,
    CostAccumulator,
)

CAMPAIGN_MARKER = "LOCAL/IGNORED — DO NOT COMMIT"
CAMPAIGN_SCHEMA = "ag_live_s1_product_convergence_campaign_v1"
CAMPAIGN_ROOT_RELATIVE = Path("output/live_validation/s1_product_convergence")
CONFIG_NAME = "campaign_config.sanitized.json"
MANIFEST_NAME = "campaign_manifest.json"
LEDGER_NAME = "budget_ledger.json"
MAX_GENERAL_STRING = 1_200
MAX_FINAL_ANSWER_STRING = 12_000
MAX_PROVIDER_FACT_STRING = 240

PROVIDER_RATE_LIMIT = "provider_rate_limit"
PROVIDER_CAPACITY = "provider_capacity"
PROVIDER_QUOTA_OR_USAGE_LIMIT = "provider_quota_or_usage_limit"
PROVIDER_AUTHENTICATION_FAILURE = "provider_authentication_failure"
PROVIDER_TRANSPORT_FAILURE = "provider_transport_failure"
UNKNOWN_PROVIDER_FAILURE = "unknown_provider_failure"
PRODUCT_PROVIDER_FAILURE_CLASSES = frozenset(
    {
        PROVIDER_RATE_LIMIT,
        PROVIDER_CAPACITY,
        PROVIDER_QUOTA_OR_USAGE_LIMIT,
        PROVIDER_AUTHENTICATION_FAILURE,
        PROVIDER_TRANSPORT_FAILURE,
        UNKNOWN_PROVIDER_FAILURE,
    }
)

_ALLOWLISTED_RATE_LIMIT_HEADERS = (
    "retry-after",
    "x-ratelimit-limit",
    "x-ratelimit-limit-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset",
    "x-ratelimit-reset-requests",
    "x-ratelimit-reset-tokens",
)

_FORBIDDEN_KEYS = frozenset(
    {
        ".env",
        "api_key",
        "authorization",
        "authorization_header",
        "cache",
        "chain_of_thought",
        "credential",
        "db_row",
        "execution_trace",
        "full_trace",
        "model_request",
        "model_response",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_model_request",
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "secret",
        "token",
    }
)
_FORBIDDEN_STRING_MARKERS = (
    "authorization: bearer",
    "api_key=",
    "bearer ",
    "openai_api_key=",
    "openrouter_api_key=",
    "raw_prompt",
    "raw_provider_payload",
    "sk-",
)

_CAMPAIGN_LEDGER_LOCK = threading.RLock()


class CampaignSafetyError(RunCapExceeded):
    """Raised before unsafe output or an outbound operation can proceed."""


def _bounded_provider_fact(value: Any) -> str | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    rendered = str(value).strip()
    if not rendered or len(rendered) > MAX_PROVIDER_FACT_STRING:
        return None
    try:
        validate_sanitized_value(rendered, path="$.product_provider_failure.fact")
    except CampaignSafetyError:
        return None
    return rendered


def _exception_status(exc: BaseException) -> int | str | None:
    response = getattr(exc, "response", None)
    for candidate in (
        getattr(exc, "status_code", None),
        getattr(exc, "http_status", None),
        getattr(response, "status_code", None),
    ):
        safe = _bounded_provider_fact(candidate)
        if safe is not None:
            try:
                return int(safe)
            except (TypeError, ValueError):
                return safe
    return None


def _exception_provider_code(exc: BaseException) -> str | int | None:
    for candidate in (
        getattr(exc, "code", None),
        getattr(exc, "error_code", None),
    ):
        if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
            safe = _bounded_provider_fact(candidate)
            if safe is not None:
                return safe
    return None


def _allowlisted_rate_limit_facts(exc: BaseException) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        headers = getattr(exc, "headers", None)
    if not hasattr(headers, "get"):
        return {"retry_after": None, "x_ratelimit": {}}
    retry_after = _bounded_provider_fact(headers.get("retry-after"))
    x_ratelimit: dict[str, str | int] = {}
    for header in _ALLOWLISTED_RATE_LIMIT_HEADERS[1:]:
        value = _bounded_provider_fact(headers.get(header))
        if value is not None:
            x_ratelimit[header] = value
    return {"retry_after": retry_after, "x_ratelimit": x_ratelimit}


def _provider_failure_classification(
    *,
    exception_class: str,
    http_status: int | str | None,
    provider_error_code: str | int | None,
) -> str:
    class_key = exception_class.casefold()
    code_key = str(provider_error_code or "").casefold()
    try:
        status = int(http_status) if http_status is not None else None
    except (TypeError, ValueError):
        status = None

    if status in {401, 403} or any(
        marker in class_key or marker in code_key
        for marker in ("authentication", "permissiondenied", "invalid_api_key")
    ):
        return PROVIDER_AUTHENTICATION_FAILURE
    if status == 402 or any(
        marker in code_key
        for marker in (
            "insufficient_quota",
            "quota_exceeded",
            "usage_limit",
            "billing_hard_limit",
        )
    ):
        return PROVIDER_QUOTA_OR_USAGE_LIMIT
    if status == 503 or any(
        marker in class_key or marker in code_key
        for marker in ("capacity", "overloaded", "serviceunavailable")
    ):
        return PROVIDER_CAPACITY
    if status == 429 or "ratelimit" in class_key or "rate_limit" in code_key:
        return PROVIDER_RATE_LIMIT
    if (status is not None and 500 <= status <= 599) or any(
        marker in class_key
        for marker in (
            "connection",
            "network",
            "timeout",
            "transport",
        )
    ):
        return PROVIDER_TRANSPORT_FAILURE
    return UNKNOWN_PROVIDER_FAILURE


def build_sanitized_product_provider_failure(
    *,
    exc: BaseException | None,
    product_phase: str,
    provider_identity: str,
    requested_model_identity: str | None,
    request_submitted: bool | None,
    campaign_counters_consumed: Mapping[str, Any],
    exception_class: str | None = None,
) -> dict[str, Any]:
    """Build an allowlisted product-side failure fact packet.

    Provider bodies, request data, full headers, and exception messages are not
    inspected. The retained message is campaign-authored from the taxonomy.
    """

    resolved_exception_class = (
        str(exception_class or type(exc).__name__)[:160]
        if exc is not None or exception_class
        else "UnknownProviderException"
    )
    http_status = _exception_status(exc) if exc is not None else None
    provider_error_code = _exception_provider_code(exc) if exc is not None else None
    rate_limit_facts = (
        _allowlisted_rate_limit_facts(exc)
        if exc is not None
        else {"retry_after": None, "x_ratelimit": {}}
    )
    classification = _provider_failure_classification(
        exception_class=resolved_exception_class,
        http_status=http_status,
        provider_error_code=provider_error_code,
    )
    messages = {
        PROVIDER_RATE_LIMIT: "The product provider reported a rate limit.",
        PROVIDER_CAPACITY: "The product provider reported unavailable capacity.",
        PROVIDER_QUOTA_OR_USAGE_LIMIT: (
            "The product provider reported a quota or usage limit."
        ),
        PROVIDER_AUTHENTICATION_FAILURE: (
            "The product provider rejected authentication."
        ),
        PROVIDER_TRANSPORT_FAILURE: (
            "The product provider request failed at the transport boundary."
        ),
        UNKNOWN_PROVIDER_FAILURE: (
            "The product provider request failed without a safely classifiable cause."
        ),
    }
    packet = {
        "classification": classification,
        "product_phase": str(product_phase or "unknown")[:160],
        "provider_identity": str(provider_identity or "unknown")[:160],
        "requested_model_identity": (
            str(requested_model_identity)[:160]
            if requested_model_identity
            else None
        ),
        "exception_class": resolved_exception_class,
        "http_status": http_status,
        "provider_error_code": provider_error_code,
        "retry_after": rate_limit_facts["retry_after"],
        "x_ratelimit": rate_limit_facts["x_ratelimit"],
        "sanitized_error_message": messages[classification],
        "request_submitted": (
            request_submitted if isinstance(request_submitted, bool) else None
        ),
        "campaign_counters_consumed": dict(campaign_counters_consumed),
    }
    validate_sanitized_value(packet)
    return packet


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def campaign_root(repo_root: Path) -> Path:
    return (repo_root / CAMPAIGN_ROOT_RELATIVE).resolve()


def validate_campaign_root(repo_root: Path, candidate: Path) -> Path:
    expected = campaign_root(repo_root)
    resolved = candidate.resolve()
    if resolved != expected:
        raise CampaignSafetyError(
            "campaign output must use output/live_validation/s1_product_convergence"
        )
    return resolved


def validate_confined_path(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CampaignSafetyError("campaign output path escaped ignored root") from exc
    return resolved


def validate_sanitized_value(value: Any, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if key in _FORBIDDEN_KEYS:
                raise CampaignSafetyError(f"forbidden campaign key at {path}: {raw_key}")
            validate_sanitized_value(child, path=f"{path}.{raw_key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            validate_sanitized_value(child, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        limit = MAX_FINAL_ANSWER_STRING if path.endswith("final_answer_text") else MAX_GENERAL_STRING
        if len(value) > limit:
            raise CampaignSafetyError(f"campaign string exceeds bound at {path}")
        lowered = value.casefold()
        if any(marker in lowered for marker in _FORBIDDEN_STRING_MARKERS):
            raise CampaignSafetyError(f"forbidden campaign sentinel at {path}")


def read_sanitized_json(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if root is not None:
        validate_confined_path(root, path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CampaignSafetyError("campaign JSON root must be an object")
    if value.get("campaign_marker") != CAMPAIGN_MARKER:
        raise CampaignSafetyError("campaign JSON is missing local ignored marker")
    validate_sanitized_value(value)
    return value


def write_sanitized_json(path: Path, value: Mapping[str, Any], *, root: Path) -> None:
    validate_confined_path(root, path)
    packet = dict(value)
    packet["campaign_marker"] = CAMPAIGN_MARKER
    validate_sanitized_value(packet)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    validate_confined_path(root, temporary)
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)


def _counter_template() -> dict[str, int]:
    return {
        "full_scryraven_runs": 0,
        "generative_plus_embedding_calls": 0,
        "external_provider_search_calls": 0,
        "retrieval_fetch_read_operations": 0,
        "independent_manual_source_checks": 0,
        "root_cause_repair_clusters": 0,
        "repeated_failed_query_reruns": 0,
        "campaign_added_retries": 0,
    }


def _token_telemetry_template() -> dict[str, Any]:
    return {
        "input_tokens": 0,
        "cached_input_tokens": None,
        "cached_input_tokens_status": "not_observed_by_repository_accounting",
        "output_tokens": 0,
        "embedding_tokens": 0,
        "total_observed_tokens": 0,
        "prospective_stop_only": True,
    }


def initial_budget_ledger(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "campaign_schema": CAMPAIGN_SCHEMA,
        "hard_operational_budget": dict(config["hard_operational_budget"]),
        "consumed_by_block": {"A": _counter_template(), "B": _counter_template()},
        "consumed_combined": _counter_template(),
        "observed_token_telemetry": _token_telemetry_template(),
        "observed_token_telemetry_by_block": {
            "A": _token_telemetry_template(),
            "B": _token_telemetry_template(),
        },
        "calls_by_model_and_provider": {},
        "observational_repository_cost_estimate": {
            "estimate_kind": "observational_repository_estimate",
            "pricing_status": "pricing_known",
            "usd": 0.0,
            "pricing_unknown_identities": [],
        },
        "actual_provider_cost_not_observed": True,
        "outbound_blocked": False,
        "outbound_block_reason": None,
        "outbound_blocked_by_block": {"A": False, "B": False},
        "outbound_block_reason_by_block": {"A": None, "B": None},
        "live_contact_started_at": None,
        "live_contact_started_at_by_block": {"A": None, "B": None},
        "campaign_counter_events": {},
        "runs": {},
    }


def consume_campaign_counters(
    *,
    config_path: Path,
    block: str,
    increments: Mapping[str, int],
    event_id: str,
) -> None:
    """Idempotently consume non-run campaign counters before their activity."""

    root = config_path.resolve().parent
    repo_root = Path(__file__).resolve().parents[1]
    validate_campaign_root(repo_root, root)
    normalized_block = str(block).upper()
    if normalized_block not in {"A", "B"}:
        raise CampaignSafetyError("campaign counter block must be A or B")
    allowed = {
        "independent_manual_source_checks",
        "root_cause_repair_clusters",
        "repeated_failed_query_reruns",
    }
    if not increments or any(field not in allowed for field in increments):
        raise CampaignSafetyError("unsupported campaign counter reservation")
    safe_event_id = str(event_id or "").strip()
    if not safe_event_id or len(safe_event_id) > 240:
        raise CampaignSafetyError("campaign counter event ID is invalid")

    ledger_path = root / LEDGER_NAME
    with _CAMPAIGN_LEDGER_LOCK:
        config = read_sanitized_json(config_path, root=root)
        ledger = read_sanitized_json(ledger_path, root=root)
        events = ledger.setdefault("campaign_counter_events", {})
        if safe_event_id in events:
            return
        budgets = ledger["hard_operational_budget"]
        block_limits = budgets[f"block_{normalized_block.lower()}"]
        combined_limits = budgets["combined"]
        normalized: dict[str, int] = {}
        for field, raw_amount in increments.items():
            amount = int(raw_amount)
            if amount < 1:
                raise CampaignSafetyError("campaign counter increment must be positive")
            normalized[field] = amount
            block_used = int(ledger["consumed_by_block"][normalized_block][field])
            combined_used = int(ledger["consumed_combined"][field])
            if block_used + amount > int(block_limits[field]):
                raise CampaignSafetyError(
                    f"Block {normalized_block} {field} cap would be exceeded"
                )
            if combined_used + amount > int(combined_limits[field]):
                raise CampaignSafetyError(f"combined {field} cap would be exceeded")
        for field, amount in normalized.items():
            ledger["consumed_by_block"][normalized_block][field] += amount
            ledger["consumed_combined"][field] += amount
        events[safe_event_id] = {
            "block": normalized_block,
            "increments": normalized,
            "recorded_at": utc_now(),
        }
        if config.get("campaign_added_retries") != 0:
            raise CampaignSafetyError("campaign-added retry posture drifted")
        write_sanitized_json(ledger_path, ledger, root=root)


class CampaignBudgetGuard:
    """Fail-closed shared operational accounting for one campaign run."""

    def __init__(
        self,
        *,
        config_path: Path,
        query_id: str,
        attempt: int,
        block: str,
    ) -> None:
        self.root = config_path.resolve().parent
        repo_root = Path(__file__).resolve().parents[1]
        validate_campaign_root(repo_root, self.root)
        self.config_path = validate_confined_path(self.root, config_path)
        self.config = read_sanitized_json(self.config_path, root=self.root)
        self.ledger_path = self.root / LEDGER_NAME
        self.query_id = str(query_id)
        self.attempt = int(attempt)
        self.block = str(block).upper()
        self.run_key = f"{self.query_id}:{self.attempt}"
        self._lock = _CAMPAIGN_LEDGER_LOCK
        self._validate_identity()

    def _validate_identity(self) -> None:
        if self.block not in {"A", "B"}:
            raise CampaignSafetyError("campaign run block must be A or B")
        query_map = {
            str(item["query_id"]): str(item["query"])
            for item in self.config.get("fixed_queries", [])
            if isinstance(item, Mapping)
        }
        if self.query_id not in query_map:
            raise CampaignSafetyError("campaign cannot execute an unknown query ID")
        if self.attempt < 1:
            raise CampaignSafetyError("campaign attempt must be positive")
        if self.config.get("broker_authorized") is not False:
            raise CampaignSafetyError("campaign broker posture must remain false")
        if self.config.get("alternate_model_comparison") != (
            "alternate_model_comparison_not_run"
        ):
            raise CampaignSafetyError("alternate-model execution is closed")
        if self.config.get("alternate_smart_provider") is not None or self.config.get(
            "alternate_smart_model"
        ) is not None:
            raise CampaignSafetyError("alternate-model identity must remain null")
        if int(self.config.get("campaign_added_retries", -1)) != 0:
            raise CampaignSafetyError("campaign-added retries must remain zero")

    def _load(self) -> dict[str, Any]:
        return read_sanitized_json(self.ledger_path, root=self.root)

    def _write(self, ledger: Mapping[str, Any]) -> None:
        write_sanitized_json(self.ledger_path, ledger, root=self.root)

    def _limits(self, ledger: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        budgets = ledger["hard_operational_budget"]
        return budgets[f"block_{self.block.lower()}"], budgets["combined"]

    def _assert_open(self, ledger: Mapping[str, Any]) -> None:
        if ledger.get("outbound_blocked") is True:
            raise CampaignSafetyError(
                "campaign outbound work is blocked: "
                + str(ledger.get("outbound_block_reason") or "unknown")
            )
        if ledger.get("outbound_blocked_by_block", {}).get(self.block) is True:
            raise CampaignSafetyError(
                f"Block {self.block} campaign outbound work is blocked: "
                + str(
                    ledger.get("outbound_block_reason_by_block", {}).get(
                        self.block
                    )
                    or "unknown"
                )
            )
        self._assert_elapsed_allowance(ledger)

    def _assert_elapsed_allowance(self, ledger: Mapping[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        block_limit, combined_limit = self._limits(ledger)
        starts = (
            (
                ledger.get("live_contact_started_at_by_block", {}).get(self.block),
                int(block_limit["live_contact_elapsed_seconds"]),
                f"Block {self.block}",
            ),
            (
                ledger.get("live_contact_started_at"),
                int(combined_limit["live_contact_elapsed_seconds"]),
                "combined",
            ),
        )
        for raw_start, limit, label in starts:
            if not raw_start:
                continue
            try:
                started = datetime.fromisoformat(str(raw_start))
            except ValueError as exc:
                raise CampaignSafetyError(
                    "campaign live-contact timestamp is invalid"
                ) from exc
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if (now - started).total_seconds() >= limit:
                raise CampaignSafetyError(
                    f"{label} live-contact elapsed-time cap has been reached"
                )

    def _check_increment(
        self,
        ledger: Mapping[str, Any],
        *,
        field: str,
        amount: int,
    ) -> None:
        block_limit, combined_limit = self._limits(ledger)
        block_used = ledger["consumed_by_block"][self.block][field]
        combined_used = ledger["consumed_combined"][field]
        if block_used + amount > int(block_limit[field]):
            raise CampaignSafetyError(f"Block {self.block} {field} cap would be exceeded")
        if combined_used + amount > int(combined_limit[field]):
            raise CampaignSafetyError(f"combined {field} cap would be exceeded")

    def _increment(self, ledger: dict[str, Any], *, field: str, amount: int) -> None:
        self._check_increment(ledger, field=field, amount=amount)
        ledger["consumed_by_block"][self.block][field] += amount
        ledger["consumed_combined"][field] += amount

    def begin_run(self) -> None:
        with self._lock:
            ledger = self._load()
            self._assert_open(ledger)
            if self.run_key in ledger["runs"]:
                raise CampaignSafetyError("campaign run attempt already exists")
            per_run = self.config["per_run_hard_operational_budget"]
            for field in (
                "generative_plus_embedding_calls",
                "external_provider_search_calls",
                "retrieval_fetch_read_operations",
            ):
                self._check_increment(ledger, field=field, amount=int(per_run[field]))
            self._increment(ledger, field="full_scryraven_runs", amount=1)
            if not ledger.get("live_contact_started_at"):
                ledger["live_contact_started_at"] = utc_now()
            block_starts = ledger.setdefault(
                "live_contact_started_at_by_block", {"A": None, "B": None}
            )
            if not block_starts.get(self.block):
                block_starts[self.block] = utc_now()
            ledger["runs"][self.run_key] = {
                "query_id": self.query_id,
                "attempt": self.attempt,
                "block": self.block,
                "started_at": utc_now(),
                "completed_at": None,
                "generative_calls": 0,
                "embedding_calls": 0,
                "search_dispatches": 0,
                "external_provider_search_calls_reserved": 0,
                "external_provider_search_calls_observed": 0,
                "retrieval_fetch_read_operations": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "embedding_tokens": 0,
                "repository_cost_estimate_usd": 0.0,
                "last_outbound_operation": None,
                "product_provider_failure": None,
            }
            self._write(ledger)

    def _before_outbound(self, ledger: Mapping[str, Any]) -> None:
        self._assert_open(ledger)
        tokens = ledger["observed_token_telemetry"]
        _, combined = self._limits(ledger)
        if int(tokens["total_observed_tokens"]) >= int(
            combined["observed_model_plus_embedding_tokens"]
        ):
            raise CampaignSafetyError("observed token ceiling has been reached")

    @staticmethod
    def _set_outbound_operation(
        run: dict[str, Any],
        *,
        product_phase: str,
        provider_identity: str,
        requested_model_identity: str | None,
    ) -> None:
        run["last_outbound_operation"] = {
            "product_phase": str(product_phase or "unknown")[:160],
            "provider_identity": str(provider_identity or "unknown")[:160],
            "requested_model_identity": (
                str(requested_model_identity)[:160]
                if requested_model_identity
                else None
            ),
            "request_submitted": None,
        }

    def before_model_call(
        self,
        *,
        model: str,
        provider: str,
        embedding: bool,
        product_phase: str,
    ) -> None:
        with self._lock:
            ledger = self._load()
            self._before_outbound(ledger)
            run = ledger["runs"][self.run_key]
            per_run_limit = int(
                self.config["per_run_hard_operational_budget"][
                    "generative_plus_embedding_calls"
                ]
            )
            used = int(run["generative_calls"]) + int(run["embedding_calls"])
            if used + 1 > per_run_limit:
                raise CampaignSafetyError("per-run model/embedding call cap would be exceeded")
            self._increment(
                ledger,
                field="generative_plus_embedding_calls",
                amount=1,
            )
            run["embedding_calls" if embedding else "generative_calls"] += 1
            self._set_outbound_operation(
                run,
                product_phase=product_phase,
                provider_identity=provider,
                requested_model_identity=model,
            )
            identities = ledger["calls_by_model_and_provider"]
            key = (
                f"model:{str(provider or 'unknown_provider')[:80]}:"
                f"{str(model or 'unknown_model')[:120]}"
            )
            identities[key] = int(identities.get(key, 0)) + 1
            self._write(ledger)

    def before_search_dispatch(self, *, providers: Sequence[str], query_count: int) -> None:
        with self._lock:
            ledger = self._load()
            self._before_outbound(ledger)
            run = ledger["runs"][self.run_key]
            run["search_dispatches"] += 1
            if run["search_dispatches"] > int(
                self.config["per_run_hard_operational_budget"]["search_dispatches"]
            ):
                raise CampaignSafetyError("per-run search dispatch cap would be exceeded")
            reserved = max(1, int(query_count)) * max(1, len(providers))
            if run["external_provider_search_calls_reserved"] + reserved > int(
                self.config["per_run_hard_operational_budget"][
                    "external_provider_search_calls"
                ]
            ):
                raise CampaignSafetyError(
                    "per-run external provider/search call cap would be exceeded"
                )
            self._increment(
                ledger,
                field="external_provider_search_calls",
                amount=reserved,
            )
            run["external_provider_search_calls_reserved"] += reserved
            self._set_outbound_operation(
                run,
                product_phase="search_provider_dispatch",
                provider_identity="search:" + ",".join(providers)[:140],
                requested_model_identity=None,
            )
            identities = ledger["calls_by_model_and_provider"]
            for provider in providers:
                key = f"search:{str(provider)[:120]}:reserved"
                identities[key] = int(identities.get(key, 0)) + max(1, query_count)
            self._write(ledger)

    def before_fetch_read(self) -> None:
        with self._lock:
            ledger = self._load()
            self._before_outbound(ledger)
            run = ledger["runs"][self.run_key]
            if run["retrieval_fetch_read_operations"] + 1 > int(
                self.config["per_run_hard_operational_budget"][
                    "retrieval_fetch_read_operations"
                ]
            ):
                raise CampaignSafetyError("per-run fetch/read cap would be exceeded")
            self._increment(
                ledger,
                field="retrieval_fetch_read_operations",
                amount=1,
            )
            run["retrieval_fetch_read_operations"] += 1
            self._set_outbound_operation(
                run,
                product_phase="retrieval_fetch_read",
                provider_identity="linkup",
                requested_model_identity=None,
            )
            self._write(ledger)

    def record_request_submitted(self, submitted: bool | None) -> None:
        with self._lock:
            ledger = self._load()
            operation = ledger["runs"][self.run_key].get("last_outbound_operation")
            if isinstance(operation, dict):
                operation["request_submitted"] = (
                    submitted if isinstance(submitted, bool) else None
                )
                self._write(ledger)

    def record_product_provider_failure(
        self,
        *,
        exc: BaseException | None,
        request_submitted: bool | None,
        exception_class: str | None = None,
    ) -> None:
        with self._lock:
            ledger = self._load()
            run = ledger["runs"][self.run_key]
            operation = run.get("last_outbound_operation")
            if not isinstance(operation, Mapping):
                return
            operation["request_submitted"] = (
                request_submitted if isinstance(request_submitted, bool) else None
            )
            counters = {
                "block": self.block,
                "block_consumed": dict(ledger["consumed_by_block"][self.block]),
                "combined_consumed": dict(ledger["consumed_combined"]),
                "run_consumed": {
                    key: run.get(key)
                    for key in (
                        "generative_calls",
                        "embedding_calls",
                        "search_dispatches",
                        "external_provider_search_calls_reserved",
                        "external_provider_search_calls_observed",
                        "retrieval_fetch_read_operations",
                        "input_tokens",
                        "output_tokens",
                        "embedding_tokens",
                    )
                },
            }
            run["product_provider_failure"] = build_sanitized_product_provider_failure(
                exc=exc,
                product_phase=str(operation.get("product_phase") or "unknown"),
                provider_identity=str(
                    operation.get("provider_identity") or "unknown"
                ),
                requested_model_identity=(
                    str(operation["requested_model_identity"])
                    if operation.get("requested_model_identity")
                    else None
                ),
                request_submitted=request_submitted,
                campaign_counters_consumed=counters,
                exception_class=exception_class,
            )
            self._write(ledger)

    def record_tokens(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        embedding: bool,
    ) -> None:
        with self._lock:
            ledger = self._load()
            run = ledger["runs"][self.run_key]
            observed = ledger["observed_token_telemetry"]
            block_observed = ledger["observed_token_telemetry_by_block"][self.block]
            input_value = max(0, int(input_tokens or 0))
            output_value = max(0, int(output_tokens or 0))
            if embedding:
                run["embedding_tokens"] += input_value
                observed["embedding_tokens"] += input_value
                block_observed["embedding_tokens"] += input_value
            else:
                run["input_tokens"] += input_value
                run["output_tokens"] += output_value
                observed["input_tokens"] += input_value
                observed["output_tokens"] += output_value
                block_observed["input_tokens"] += input_value
                block_observed["output_tokens"] += output_value
            observed["total_observed_tokens"] = (
                int(observed["input_tokens"])
                + int(observed["output_tokens"])
                + int(observed["embedding_tokens"])
            )
            block_observed["total_observed_tokens"] = (
                int(block_observed["input_tokens"])
                + int(block_observed["output_tokens"])
                + int(block_observed["embedding_tokens"])
            )
            block_limit, combined = self._limits(ledger)
            if int(block_observed["total_observed_tokens"]) >= int(
                block_limit["observed_model_plus_embedding_tokens"]
            ):
                ledger["outbound_blocked_by_block"][self.block] = True
                ledger["outbound_block_reason_by_block"][self.block] = (
                    "observed_token_ceiling_reached"
                )
            if int(observed["total_observed_tokens"]) >= int(
                combined["observed_model_plus_embedding_tokens"]
            ):
                ledger["outbound_blocked"] = True
                ledger["outbound_block_reason"] = "observed_token_ceiling_reached"
            self._write(ledger)

    def record_provider_observation(self, *, provider: str) -> None:
        with self._lock:
            ledger = self._load()
            run = ledger["runs"][self.run_key]
            run["external_provider_search_calls_observed"] += 1
            key = f"search:{str(provider or 'unknown')[:120]}:observed"
            identities = ledger["calls_by_model_and_provider"]
            identities[key] = int(identities.get(key, 0)) + 1
            if (
                run["external_provider_search_calls_observed"]
                > run["external_provider_search_calls_reserved"]
            ):
                ledger["outbound_blocked"] = True
                ledger["outbound_block_reason"] = (
                    "provider_calls_exceeded_conservative_reservation"
                )
            self._write(ledger)

    def record_repository_cost_estimate(
        self,
        *,
        total_usd: float,
        pricing_identity: str,
        pricing_known: bool,
    ) -> None:
        with self._lock:
            ledger = self._load()
            run = ledger["runs"][self.run_key]
            run["repository_cost_estimate_usd"] = round(max(0.0, float(total_usd)), 6)
            total = sum(
                float(item.get("repository_cost_estimate_usd") or 0.0)
                for item in ledger["runs"].values()
                if isinstance(item, Mapping)
            )
            estimate = ledger["observational_repository_cost_estimate"]
            estimate["usd"] = round(total, 6)
            if not pricing_known:
                identity = str(pricing_identity or "unknown")[:160]
                unknown = estimate["pricing_unknown_identities"]
                if identity not in unknown:
                    unknown.append(identity)
                estimate["pricing_status"] = "pricing_unknown"
            self._write(ledger)

    def reconcile_product_cap_observations(self, cap_policy: Any) -> None:
        """Reconcile product-owned cap facts not visible at dependency wrappers."""

        self.reconcile_product_cap_observation_counts(cap_policy.observed_counts())

    def reconcile_product_cap_observation_counts(
        self,
        observed: Mapping[str, Any],
    ) -> None:
        """Apply an already-sanitized product cap observation mapping."""

        if int(observed.get("retries") or 0) != 0:
            raise CampaignSafetyError("campaign-added retry count must remain zero")
        product_fetch_reads = max(
            0,
            int(observed.get("fetch_read_operations") or 0),
        )
        with self._lock:
            ledger = self._load()
            run = ledger["runs"][self.run_key]
            wrapper_observed = int(run["retrieval_fetch_read_operations"])
            delta = max(0, product_fetch_reads - wrapper_observed)
            if delta:
                self._increment(
                    ledger,
                    field="retrieval_fetch_read_operations",
                    amount=delta,
                )
                run["retrieval_fetch_read_operations"] += delta
            run["product_cap_observations"] = {
                "search_dispatches": int(observed.get("search_dispatches") or 0),
                "fetch_read_operations": product_fetch_reads,
                "author_model_calls": int(
                    observed.get("author_model_calls") or 0
                ),
                "smart_search_judgment_model_calls": int(
                    observed.get("smart_search_judgment_model_calls") or 0
                ),
                "retries": 0,
            }
            self._write(ledger)

    def complete_run(self) -> None:
        with self._lock:
            ledger = self._load()
            ledger["runs"][self.run_key]["completed_at"] = utc_now()
            self._write(ledger)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            ledger = self._load()
            return {
                "hard_operational_budget": ledger["hard_operational_budget"],
                "consumed_by_block": ledger["consumed_by_block"],
                "consumed_combined": ledger["consumed_combined"],
                "observed_token_telemetry": ledger["observed_token_telemetry"],
                "observed_token_telemetry_by_block": ledger[
                    "observed_token_telemetry_by_block"
                ],
                "calls_by_model_and_provider": ledger[
                    "calls_by_model_and_provider"
                ],
                "observational_repository_cost_estimate": ledger[
                    "observational_repository_cost_estimate"
                ],
                "actual_provider_cost_not_observed": True,
                "run": ledger["runs"].get(self.run_key, {}),
                "outbound_blocked": ledger["outbound_blocked"],
                "outbound_block_reason": ledger["outbound_block_reason"],
                "outbound_blocked_by_block": ledger[
                    "outbound_blocked_by_block"
                ],
                "outbound_block_reason_by_block": ledger[
                    "outbound_block_reason_by_block"
                ],
                "live_contact_started_at": ledger["live_contact_started_at"],
                "live_contact_started_at_by_block": ledger[
                    "live_contact_started_at_by_block"
                ],
            }


class CampaignCostAccumulator(CostAccumulator):
    """Ordinary CostAccumulator with campaign-only sanitized telemetry hooks."""

    def __init__(self, guard: CampaignBudgetGuard) -> None:
        super().__init__()
        self.guard = guard

    def record_model_call(
        self,
        *,
        phase: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        super().record_model_call(
            phase=phase,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.guard.record_tokens(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            embedding=False,
        )
        self.guard.record_repository_cost_estimate(
            total_usd=self.snapshot()["total_cost_usd"],
            pricing_identity=model,
            pricing_known=(model or "").casefold() in MODEL_PRICING_USD_PER_1M,
        )

    def record_embedding_call(
        self,
        *,
        phase: str,
        model: str,
        input_tokens: int = 0,
    ) -> None:
        CostAccumulator.record_model_call(
            self,
            phase=phase or "embedding",
            model=model,
            input_tokens=input_tokens,
            output_tokens=0,
        )
        self.guard.record_tokens(
            input_tokens=input_tokens,
            output_tokens=0,
            embedding=True,
        )
        self.guard.record_repository_cost_estimate(
            total_usd=self.snapshot()["total_cost_usd"],
            pricing_identity=model,
            pricing_known=(model or "").casefold() in MODEL_PRICING_USD_PER_1M,
        )

    def record_search_call(self, *, phase: str, provider: str, calls: int = 1) -> None:
        super().record_search_call(phase=phase, provider=provider, calls=calls)
        for _ in range(max(1, int(calls or 1))):
            self.guard.record_provider_observation(provider=provider)
        self.guard.record_repository_cost_estimate(
            total_usd=self.snapshot()["total_cost_usd"],
            pricing_identity=provider,
            pricing_known=(
                (provider or "").casefold() in PROVIDER_PRICING_USD_PER_CALL
            ),
        )


def _search_providers_from_call(args: Sequence[Any], kwargs: Mapping[str, Any]) -> list[str]:
    raw = kwargs.get("search_providers")
    if raw is None and len(args) > 16:
        raw = args[16]
    if raw:
        return [str(item).strip().lower() for item in raw if str(item).strip()]
    intent = str(kwargs.get("intent") or (args[1] if len(args) > 1 else ""))
    complexity = str(
        kwargs.get("complexity") or (args[2] if len(args) > 2 else "")
    )
    providers = ["tavily"]
    if os.getenv("LINKUP_API_KEY") and complexity.casefold() == "high":
        providers.append("linkup")
    if os.getenv("EXA_API_KEY") and intent.casefold() == "general":
        providers.append("exa")
    return providers


def compose_campaign_accounted_deps(
    deps: Any,
    *,
    guard: CampaignBudgetGuard,
    run_config: Any,
) -> Any:
    """Wrap existing injected dependencies without changing product semantics."""

    validate_s1_product_equivalence(deps)

    from core.strict_one_shot_model_transport import (
        build_strict_one_shot_smart_model_transport,
        normalize_canonical_model_provider,
    )

    base_ask_model = deps.ask_model
    base_embed_texts = deps.embed_texts
    base_search = deps.process_search_queries
    base_fetch = deps.fetch_linkup_precision_block
    strict_transport = build_strict_one_shot_smart_model_transport(
        smart_provider=normalize_canonical_model_provider(run_config.smart_provider),
        smart_model=str(run_config.smart_model),
        local_url=str(run_config.local_url or "") or None,
        openrouter_api_key=str(run_config.or_api_key or "") or None,
    )

    def call_with_failure_observation(call: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            result = call(*args, **kwargs)
        except Exception as exc:
            request_submitted = (
                True
                if getattr(exc, "response", None) is not None
                or _exception_status(exc) is not None
                else None
            )
            guard.record_product_provider_failure(
                exc=exc,
                request_submitted=request_submitted,
            )
            raise
        guard.record_request_submitted(True)
        return result

    def ask_model_accounted(*args: Any, **kwargs: Any) -> Any:
        provider = str(
            kwargs.get("provider")
            or (args[2] if len(args) > 2 else run_config.fast_provider)
        )
        model = str(
            kwargs.get("model")
            or (args[3] if len(args) > 3 else run_config.fast_model)
        )
        guard.before_model_call(
            model=model,
            provider=provider,
            embedding=False,
            product_phase=str(kwargs.get("cost_phase") or "fast_model"),
        )
        return call_with_failure_observation(base_ask_model, *args, **kwargs)

    def embed_texts_accounted(*args: Any, **kwargs: Any) -> Any:
        texts = kwargs.get("texts") if "texts" in kwargs else (args[0] if args else ())
        if not texts:
            return base_embed_texts(*args, **kwargs)
        provider = str(
            kwargs.get("provider")
            or (args[1] if len(args) > 1 else run_config.embed_provider)
        )
        model = str(
            kwargs.get("model")
            or (args[2] if len(args) > 2 else run_config.embed_model)
        )
        guard.before_model_call(
            model=model,
            provider=provider,
            embedding=True,
            product_phase=str(kwargs.get("cost_phase") or "embedding"),
        )
        return call_with_failure_observation(base_embed_texts, *args, **kwargs)

    def search_accounted(*args: Any, **kwargs: Any) -> Any:
        providers = _search_providers_from_call(args, kwargs)
        raw_queries = kwargs.get("queries_list") or (args[0] if args else ())
        query_count = len(raw_queries) if isinstance(raw_queries, Sequence) else 1
        guard.before_search_dispatch(providers=providers, query_count=query_count)
        return call_with_failure_observation(base_search, *args, **kwargs)

    def fetch_accounted(*args: Any, **kwargs: Any) -> Any:
        guard.before_fetch_read()
        return call_with_failure_observation(base_fetch, *args, **kwargs)

    def strict_transport_accounted(*args: Any, **kwargs: Any) -> Any:
        guard.before_model_call(
            model=str(run_config.smart_model),
            provider=str(run_config.smart_provider),
            embedding=False,
            product_phase="strict_one_shot_smart_model",
        )
        result = strict_transport(*args, **kwargs)
        attempted = int(getattr(result, "provider_request_attempt_count", 0) or 0)
        guard.record_request_submitted(attempted > 0)
        if attempted > 0 and bool(getattr(result, "provider_request_failed", False)):
            guard.record_product_provider_failure(
                exc=None,
                request_submitted=True,
                exception_class=type(result).__name__,
            )
        return result

    return replace(
        deps,
        ask_model=ask_model_accounted,
        embed_texts=embed_texts_accounted,
        process_search_queries=search_accounted,
        fetch_linkup_precision_block=fetch_accounted,
        strict_one_shot_smart_model_transport=strict_transport_accounted,
    )


def product_equivalence_summary(deps: Any) -> dict[str, Any]:
    registry = deps.specialist_capability_registry.projection()
    policy = deps.specialist_execution_policy.projection()
    descriptors = list(registry.get("capability_descriptors") or [])
    return {
        "classification": "UPGRADE",
        "runtime_consumer": "run_pipeline",
        "composition_owner": "compose_quantitative_specialist_product_deps",
        "capability_count": registry.get("capability_count"),
        "capability_ids": [item.get("capability_id") for item in descriptors],
        "specialist_work_item_limit": policy.get("specialist_work_item_limit"),
        "parallelism": policy.get("parallelism"),
        "recursion": policy.get("recursion"),
        "registry_duplicated": False,
        "execution_policy_duplicated": False,
    }


def validate_s1_product_equivalence(deps: Any) -> dict[str, Any]:
    summary = product_equivalence_summary(deps)
    expected = {
        "capability_count": 1,
        "capability_ids": ["specialist.source_bound_calculation"],
        "specialist_work_item_limit": 1,
        "parallelism": False,
        "recursion": False,
    }
    mismatched = [
        key for key, expected_value in expected.items() if summary.get(key) != expected_value
    ]
    if mismatched:
        raise CampaignSafetyError(
            "ordinary S1 product dependency composition mismatch: "
            + ", ".join(mismatched)
        )
    return summary


def _safe_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_ref(value: Any) -> dict[str, Any]:
    raw = _safe_mapping(value)
    allowed = (
        "action_id",
        "artifact_id",
        "component_id",
        "component_revision",
        "digest",
        "disposition_id",
        "graph_id",
        "handoff_id",
        "node_digest",
        "node_id",
        "node_revision",
        "packet_id",
        "proposal_id",
        "result_id",
        "synthesis_key",
        "work_id",
    )
    return {
        key: raw[key]
        for key in allowed
        if key in raw and raw[key] not in (None, "", [], {})
    }


def _sanitized_result(value: Any) -> dict[str, Any]:
    raw = _safe_mapping(value)
    bounded = _safe_mapping(raw.get("bounded_result"))
    alignment = _safe_mapping(bounded.get("claim_alignment"))
    literal_refs = []
    for item in bounded.get("literal_binding_refs") or ():
        ref = _safe_mapping(item)
        literal_refs.append(
            {
                key: ref.get(key)
                for key in (
                    "source_local_key",
                    "source_numeric_literal",
                    "underlying_evidence_match_posture",
                )
                if ref.get(key) not in (None, "")
            }
        )
    return {
        **_safe_ref(raw),
        "capability_id": raw.get("capability_id"),
        "execution_posture": raw.get("execution_posture"),
        "validator_consumption": raw.get("validator_consumption"),
        "calculation_status": bounded.get("calculation_status"),
        "calculation_kind": bounded.get("calculation_kind"),
        "numeric_value_text": bounded.get("numeric_value_text"),
        "derived_unit": bounded.get("derived_unit"),
        "claim_alignment_posture": alignment.get("posture"),
        "literal_binding_refs": literal_refs,
        "blockers": [str(item)[:240] for item in raw.get("blockers") or ()],
    }


def sanitized_s1_runtime_summary(outcome: Any) -> dict[str, Any]:
    trace = _safe_mapping(getattr(outcome, "execution_trace", None))
    run_kernel = _safe_mapping(trace.get("run_kernel"))
    projections = _safe_mapping(run_kernel.get("projections"))
    plane = _safe_mapping(projections.get("specialist_work_plane"))
    scheduler = _safe_mapping(projections.get("multicomponent_graph_scheduler"))
    graph = _safe_mapping(projections.get("multicomponent_component_work_graph_v1"))
    dispositions = []
    for item in plane.get("proposal_dispositions") or ():
        raw = _safe_mapping(item)
        dispositions.append(
            {
                **_safe_ref(raw),
                "execution_availability_posture": raw.get(
                    "execution_availability_posture"
                ),
                "validator_consumption": raw.get("validator_consumption"),
                "required_posture": raw.get("required_posture"),
            }
        )
    handoffs = []
    for item in plane.get("need_handoffs") or ():
        raw = _safe_mapping(item)
        handoffs.append(
            {
                **_safe_ref(raw),
                "availability_posture": raw.get("availability_posture"),
                "validator_consumption": raw.get("validator_consumption"),
                "target_kind": _safe_mapping(raw.get("target_ref")).get(
                    "target_kind"
                ),
            }
        )
    results = [_sanitized_result(item) for item in plane.get("result_artifacts") or ()]
    pool = _safe_mapping(scheduler.get("specialist_compatibility_pool"))
    summary = {
        "stage_reached": "run_outcome" if getattr(outcome, "report", None) is not None else "pipeline",
        "multicomponent_graph_status": graph.get("graph_status"),
        "specialist": {
            "proposal_count": plane.get("proposal_count", len(dispositions)),
            "result_count": plane.get("result_artifact_count", len(results)),
            "dispositions": dispositions,
            "handoffs": handoffs,
            "results": results,
            "specialist_spent": pool.get("specialist_spent", 0),
            "specialist_remaining": pool.get("specialist_remaining"),
            "provider_request_attempt_count": plane.get(
                "provider_request_attempt_count", 0
            ),
            "model_call_count": plane.get("model_call_count", 0),
        },
        "two_hop_source_binding_proved": any(
            ref.get("underlying_evidence_match_posture")
            == "exact_literal_found_in_underlying_evidence"
            for result in results
            for ref in result.get("literal_binding_refs") or ()
        ),
        "component_dprime_consumed": any(
            item.get("validator_consumption") == "consumed_by_component_dprime"
            for item in results + handoffs
        ),
        "synthesis_dprime_consumed": any(
            item.get("validator_consumption") == "consumed_by_synthesis_dprime"
            for item in results + handoffs
        ),
    }
    validate_sanitized_value(summary)
    return summary
