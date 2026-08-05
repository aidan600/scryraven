"""Run-scoped cap enforcement for bounded physical external dispatch."""

from __future__ import annotations

import hashlib
import re
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

_SAFE_IDENTITY = re.compile(r"[A-Za-z0-9_.:-]{1,120}\Z")
_ZERO = Decimal("0")

# Mechanical per-request bounds used when constructing AttemptReservation max_usage /
# transport timeouts. These are not live-run product profile defaults.
MODEL_OUTPUT_TOKEN_LIMIT = 16_384
MODEL_REASONING_TOKEN_LIMIT = 16_384
DEFAULT_EXTERNAL_TIMEOUT_SECONDS = 30.0


class RunCapExceeded(RuntimeError):
    """Sanitized terminal raised before or after a bounded cap violation."""

    terminal_code = "bounded_run_cap_reached"

    def __init__(
        self,
        reason_code: str,
        *,
        family: ExternalCallFamily | None = None,
        internal_message: str | None = None,
    ) -> None:
        super().__init__(internal_message or self.terminal_code)
        self.reason_code = _safe_identity(reason_code, prefix="reason")
        self.family = family

    def terminal_payload(self) -> dict[str, str]:
        payload = {
            "code": self.terminal_code,
            "message": "The bounded run stopped at its configured safety envelope.",
            "reason": self.reason_code,
        }
        if self.family is not None:
            payload["family"] = self.family.value
        return payload


class ExternalCallFamily(str, Enum):
    """Physical external request families governed by the run ledger."""

    MODEL = "model"
    EMBEDDING = "embedding"
    SEARCH = "search"
    READ = "read"


class AttemptLifecycle(str, Enum):
    """Auditable lifecycle of one admitted or denied physical attempt."""

    RESERVED = "reserved"
    DISPATCHED = "dispatched"
    SETTLED_OBSERVED = "settled_observed"
    SETTLED_CONSERVATIVE = "settled_conservative"
    CANCELLED_PRE_DISPATCH = "cancelled_pre_dispatch"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token quantities used for admission bounds and observed settlement."""

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    embedding_tokens: int = 0

    def __post_init__(self) -> None:
        for name, value in self.as_dict().items():
            if int(value) != value or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached_input_tokens cannot exceed input_tokens")

    def as_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "embedding_tokens": self.embedding_tokens,
        }

    def without_cached_dimension(self) -> dict[str, int]:
        values = self.as_dict()
        values.pop("cached_input_tokens")
        return values


@dataclass(frozen=True, slots=True)
class RoutePricing:
    """Immutable conservative price facts for one exact physical route."""

    pricing_key: str
    input_per_million_usd: Decimal = _ZERO
    cached_input_per_million_usd: Decimal = _ZERO
    output_per_million_usd: Decimal = _ZERO
    reasoning_per_million_usd: Decimal = _ZERO
    embedding_per_million_usd: Decimal = _ZERO
    flat_attempt_usd: Decimal = _ZERO

    def __post_init__(self) -> None:
        if not _SAFE_IDENTITY.fullmatch(self.pricing_key):
            raise ValueError("pricing_key must be a safe stable identifier")
        for value in (
            self.input_per_million_usd,
            self.cached_input_per_million_usd,
            self.output_per_million_usd,
            self.reasoning_per_million_usd,
            self.embedding_per_million_usd,
            self.flat_attempt_usd,
        ):
            if value < _ZERO:
                raise ValueError("pricing values must be non-negative")

    def cost_for(self, usage: TokenUsage) -> Decimal:
        uncached_input = usage.input_tokens - usage.cached_input_tokens
        variable = (
            Decimal(uncached_input) * self.input_per_million_usd
            + Decimal(usage.cached_input_tokens) * self.cached_input_per_million_usd
            + Decimal(usage.output_tokens) * self.output_per_million_usd
            + Decimal(usage.reasoning_tokens) * self.reasoning_per_million_usd
            + Decimal(usage.embedding_tokens) * self.embedding_per_million_usd
        ) / Decimal(1_000_000)
        return self.flat_attempt_usd + variable


@dataclass(frozen=True, slots=True)
class RunCapEnvelope:
    """Immutable physical-attempt, token, cost, retry, and deadline limits."""

    profile_name: str
    profile_digest: str
    pricing_version: str
    deadline_seconds: float
    max_total_attempts: int
    max_attempts_by_family: Mapping[ExternalCallFamily, int]
    max_tokens: TokenUsage
    max_tokens_by_family: Mapping[ExternalCallFamily, TokenUsage]
    max_per_attempt_usd: Decimal
    max_run_usd: Decimal
    max_retries: int = 0
    max_fallbacks: int = 0
    suppress_persistence: bool = True

    def __post_init__(self) -> None:
        for value, label in (
            (self.profile_name, "profile_name"),
            (self.profile_digest, "profile_digest"),
            (self.pricing_version, "pricing_version"),
        ):
            if not _SAFE_IDENTITY.fullmatch(value):
                raise ValueError(f"{label} must be a safe stable identifier")
        if self.deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive")
        if self.max_total_attempts <= 0:
            raise ValueError("max_total_attempts must be positive")
        if self.max_per_attempt_usd <= _ZERO or self.max_run_usd <= _ZERO:
            raise ValueError("cost caps must be positive")
        if self.max_retries < 0 or self.max_fallbacks < 0:
            raise ValueError("retry and fallback caps must be non-negative")
        attempt_caps = {ExternalCallFamily(key): int(value) for key, value in self.max_attempts_by_family.items()}
        token_caps = {ExternalCallFamily(key): value for key, value in self.max_tokens_by_family.items()}
        if set(attempt_caps) != set(ExternalCallFamily):
            raise ValueError("every external call family needs an attempt cap")
        if set(token_caps) != set(ExternalCallFamily):
            raise ValueError("every external call family needs a token cap")
        if any(value < 0 for value in attempt_caps.values()):
            raise ValueError("family attempt caps must be non-negative")
        object.__setattr__(
            self,
            "max_attempts_by_family",
            MappingProxyType(attempt_caps),
        )
        object.__setattr__(
            self,
            "max_tokens_by_family",
            MappingProxyType(token_caps),
        )


@dataclass(frozen=True, slots=True)
class ExternalAttemptSpec:
    """Admission request describing exactly one possible physical request."""

    family: ExternalCallFamily
    provider: str
    route: str
    operation: str
    logical_call_id: str
    max_usage: TokenUsage
    pricing: RoutePricing
    requested_timeout_seconds: float
    is_retry: bool = False
    is_fallback: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "family", ExternalCallFamily(self.family))
        for name in ("provider", "route", "operation", "logical_call_id"):
            value = getattr(self, name)
            if not _SAFE_IDENTITY.fullmatch(value):
                raise ValueError(f"{name} must be a safe stable identifier")
        if self.requested_timeout_seconds <= 0:
            raise ValueError("requested_timeout_seconds must be positive")


@dataclass(slots=True)
class _AttemptRecord:
    attempt_id: str
    ordinal: int
    spec: ExternalAttemptSpec
    lifecycle: AttemptLifecycle
    reserved_cost_usd: Decimal
    timeout_seconds: float
    observed_usage: TokenUsage | None = None
    settled_cost_usd: Decimal | None = None
    settlement_reason: str | None = None


class AttemptReservation:
    """Capability object that must surround exactly one physical dispatch."""

    __slots__ = ("_policy", "attempt_id")

    def __init__(self, policy: RunCapPolicy, attempt_id: str) -> None:
        self._policy = policy
        self.attempt_id = attempt_id

    @property
    def timeout_seconds(self) -> float:
        return self._policy._reservation_timeout(self.attempt_id)

    @property
    def remaining_seconds(self) -> float:
        return self._policy.remaining_seconds()

    @property
    def lifecycle(self) -> AttemptLifecycle:
        return self._policy._reservation_lifecycle(self.attempt_id)

    def mark_dispatched(self) -> None:
        self._policy._mark_dispatched(self.attempt_id)

    def settle_observed(self, usage: TokenUsage | None) -> None:
        if usage is None:
            self.settle_conservative("usage_unavailable")
            return
        self._policy._settle_observed(self.attempt_id, usage)

    def settle_conservative(self, reason: str = "outcome_ambiguous") -> None:
        self._policy._settle_conservative(self.attempt_id, reason)

    def cancel_pre_dispatch(self, reason: str = "dispatch_not_started") -> None:
        self._policy._cancel_pre_dispatch(self.attempt_id, reason)


class RunCapPolicy:
    """Thread-safe run ledger plus compatibility logical counters."""

    def __init__(
        self,
        max_search_dispatches: int = 2_147_483_647,
        max_fetch_read_operations: int = 2_147_483_647,
        max_author_model_calls: int = 2_147_483_647,
        max_smart_search_judgment_model_calls: int = 2_147_483_647,
        max_retries: int = 3,
        *,
        envelope: RunCapEnvelope | None = None,
        route_pricing: Mapping[
            tuple[ExternalCallFamily | str, str, str], RoutePricing
        ]
        | None = None,
    ) -> None:
        self.max_search_dispatches = max_search_dispatches
        self.max_fetch_read_operations = max_fetch_read_operations
        self.max_author_model_calls = max_author_model_calls
        self.max_smart_search_judgment_model_calls = max_smart_search_judgment_model_calls
        self.envelope = envelope
        self.max_retries = envelope.max_retries if envelope is not None else max_retries
        if envelope is not None and route_pricing is None:
            raise ValueError(
                "bounded RunCapPolicy requires an explicit immutable route_pricing map"
            )
        pricing_map: dict[tuple[ExternalCallFamily, str, str], RoutePricing] = {}
        for raw_key, pricing in dict(route_pricing or {}).items():
            if not isinstance(pricing, RoutePricing):
                raise TypeError("route_pricing values must be RoutePricing")
            if not isinstance(raw_key, tuple) or len(raw_key) != 3:
                raise ValueError("route_pricing keys must be (family, provider, route)")
            family, provider, route = raw_key
            normalized = (
                ExternalCallFamily(family),
                str(provider).strip().lower(),
                str(route).strip().lower(),
            )
            if not normalized[1] or not normalized[2]:
                raise ValueError("route_pricing provider and route must be nonempty")
            pricing_map[normalized] = pricing
        self._route_pricing = MappingProxyType(pricing_map)
        self.search_dispatches = 0
        self.fetch_read_operations = 0
        self.author_model_calls = 0
        self.smart_search_judgment_model_calls = 0
        self.retries = 0
        self.facts: list[str] = []
        self._lock = threading.RLock()
        self._run_id: str | None = None
        self._request_id: str | None = None
        self._started_monotonic: float | None = None
        self._deadline_monotonic: float | None = None
        self._closed_monotonic: float | None = None
        self._furthest_product_stage: str | None = None
        self._logical_sequence = 0
        self._ordinals: dict[str, int] = {}
        self._records: dict[str, _AttemptRecord] = {}
        self._denials: list[dict[str, Any]] = []
        self._admitted_by_family = {family: 0 for family in ExternalCallFamily}
        self._physical_by_family = {family: 0 for family in ExternalCallFamily}
        self._reserved_tokens = TokenUsage()
        self._committed_tokens = TokenUsage()
        self._observed_tokens = TokenUsage()
        self._reserved_cost_usd = _ZERO
        self._committed_cost_usd = _ZERO
        self._observed_cost_usd = _ZERO
        self._conservative_cost_usd = _ZERO
        self._retry_attempts = 0
        self._fallback_attempts = 0

    @property
    def bounded(self) -> bool:
        return self.envelope is not None

    @property
    def persistence_suppressed(self) -> bool:
        return bool(self.envelope and self.envelope.suppress_persistence)

    def resolve_route_pricing(
        self,
        family: ExternalCallFamily | str,
        provider: str,
        route: str,
    ) -> RoutePricing:
        """Return the immutable price fact for one exact physical route."""

        normalized_family = ExternalCallFamily(family)
        key = (
            normalized_family,
            str(provider).strip().lower(),
            str(route).strip().lower(),
        )
        try:
            return self._route_pricing[key]
        except KeyError as exc:
            raise RunCapExceeded(
                "unsupported_route_pricing",
                family=normalized_family,
            ) from exc

    def activate(self, *, run_id: str, request_id: str) -> None:
        """Bind the ledger once and start its monotonic whole-run deadline."""

        if not self.bounded:
            return
        safe_run_id = _safe_identity(run_id, prefix="run")
        safe_request_id = _safe_identity(request_id, prefix="request")
        with self._lock:
            if self._run_id is not None:
                if (self._run_id, self._request_id) != (
                    safe_run_id,
                    safe_request_id,
                ):
                    raise RunCapExceeded("ledger_reuse")
                return
            now = time.monotonic()
            self._run_id = safe_run_id
            self._request_id = safe_request_id
            self._started_monotonic = now
            assert self.envelope is not None
            self._deadline_monotonic = now + self.envelope.deadline_seconds
            self._furthest_product_stage = "pipeline_entry"

    def note_product_stage(self, stage: str) -> None:
        """Record the latest sanitized product stage reached by this run."""

        if not self.bounded:
            return
        safe_stage = _safe_identity(stage, prefix="stage")
        with self._lock:
            self._furthest_product_stage = safe_stage

    def remaining_seconds(self) -> float:
        if not self.bounded:
            return float("inf")
        with self._lock:
            self._require_active()
            assert self._deadline_monotonic is not None
            return max(0.0, self._deadline_monotonic - time.monotonic())

    def ensure_within_deadline(self) -> None:
        """Fail closed when the bounded run reaches its terminal after deadline."""

        if not self.bounded:
            return
        with self._lock:
            self._require_active()
            assert self._deadline_monotonic is not None
            terminal_monotonic = self._closed_monotonic or time.monotonic()
            if terminal_monotonic >= self._deadline_monotonic:
                raise RunCapExceeded("deadline_exhausted")

    def new_logical_call_id(self, stage: str) -> str:
        safe_stage = _safe_identity(stage, prefix="stage")
        with self._lock:
            self._furthest_product_stage = safe_stage
            self._logical_sequence += 1
            return f"{safe_stage}:{self._logical_sequence}"

    def reserve_attempt(self, spec: ExternalAttemptSpec) -> AttemptReservation:
        """Atomically admit and reserve worst-case tokens/cost before dispatch."""

        if not self.bounded:
            raise RuntimeError("physical reservations require a bounded envelope")
        with self._lock:
            self._require_active()
            assert self.envelope is not None
            ordinal = self._ordinals.get(spec.logical_call_id, 0) + 1
            self._ordinals[spec.logical_call_id] = ordinal
            attempt_id = f"{self._run_id}:{spec.family.value}:{spec.logical_call_id}:{ordinal}"
            cost = spec.pricing.cost_for(spec.max_usage)
            remaining = self.remaining_seconds()
            reason = self._admission_denial_reason(spec, cost, remaining)
            if reason is not None:
                self._denials.append(
                    {
                        "attempt_id": attempt_id,
                        "family": spec.family.value,
                        "provider": spec.provider,
                        "route": spec.route,
                        "operation": spec.operation,
                        "logical_call_id": spec.logical_call_id,
                        "physical_ordinal": ordinal,
                        "lifecycle": AttemptLifecycle.DENIED.value,
                        "reason": reason,
                    }
                )
                raise RunCapExceeded(reason, family=spec.family)
            timeout = min(spec.requested_timeout_seconds, remaining)
            record = _AttemptRecord(
                attempt_id=attempt_id,
                ordinal=ordinal,
                spec=spec,
                lifecycle=AttemptLifecycle.RESERVED,
                reserved_cost_usd=cost,
                timeout_seconds=timeout,
            )
            self._records[attempt_id] = record
            self._admitted_by_family[spec.family] += 1
            if spec.is_retry:
                self._retry_attempts += 1
            if spec.is_fallback:
                self._fallback_attempts += 1
            self._reserved_tokens = _add_usage(
                self._reserved_tokens,
                spec.max_usage,
            )
            self._committed_tokens = _add_usage(
                self._committed_tokens,
                spec.max_usage,
            )
            self._reserved_cost_usd += cost
            self._committed_cost_usd += cost
            return AttemptReservation(self, attempt_id)

    def finalize_active_attempts(self) -> None:
        """Fail closed by conservatively settling any still-active request."""

        if not self.bounded:
            return
        with self._lock:
            active = [
                record.attempt_id
                for record in self._records.values()
                if record.lifecycle in (AttemptLifecycle.RESERVED, AttemptLifecycle.DISPATCHED)
            ]
        for attempt_id in active:
            record = self._record(attempt_id)
            if record.lifecycle is AttemptLifecycle.RESERVED:
                self._cancel_pre_dispatch(attempt_id, "run_finalized_before_dispatch")
            else:
                self._settle_conservative(attempt_id, "run_finalized_ambiguous")
        with self._lock:
            if self._closed_monotonic is None:
                self._closed_monotonic = time.monotonic()

    def mark_search_dispatch(self) -> None:
        self._mark("search_dispatches", self.max_search_dispatches)

    def mark_fetch_read_operation(self) -> None:
        self._mark("fetch_read_operations", self.max_fetch_read_operations)

    def mark_author_model_call(self) -> None:
        self._mark("author_model_calls", self.max_author_model_calls)

    def mark_smart_search_judgment_model_call(self) -> None:
        self._mark(
            "smart_search_judgment_model_calls",
            self.max_smart_search_judgment_model_calls,
        )

    def mark_retry(self) -> None:
        self._mark("retries", self.max_retries)

    def should_disable_utilization_retry(self) -> bool:
        return self.max_retries == 0

    def should_disable_model_retry(self) -> bool:
        return self.bounded and self.max_retries == 0

    def should_disable_fallback(self) -> bool:
        return bool(self.envelope and self.envelope.max_fallbacks == 0)

    def record_fact(self, fact: str) -> None:
        clean = str(fact or "").strip()
        with self._lock:
            if clean and clean not in self.facts:
                self.facts.append(clean)

    def observed_counts(self, *, enforcement: str = "active") -> dict[str, Any]:
        with self._lock:
            return {
                "search_dispatches": self.search_dispatches,
                "fetch_read_operations": self.fetch_read_operations,
                "author_model_calls": self.author_model_calls,
                "smart_search_judgment_model_calls": (self.smart_search_judgment_model_calls),
                "retries": self.retries,
                "enforcement": enforcement,
            }

    def physical_snapshot(self) -> dict[str, Any]:
        """Return a sanitized, persistence-safe view of the physical ledger."""

        if not self.bounded:
            return {"enforcement": "logical_only"}
        with self._lock:
            assert self.envelope is not None
            lifecycle_counts = {item.value: 0 for item in AttemptLifecycle}
            attempts: list[dict[str, Any]] = []
            for record in self._records.values():
                lifecycle_counts[record.lifecycle.value] += 1
                attempts.append(
                    {
                        "attempt_id": record.attempt_id,
                        "family": record.spec.family.value,
                        "provider": record.spec.provider,
                        "route": record.spec.route,
                        "operation": record.spec.operation,
                        "logical_call_id": record.spec.logical_call_id,
                        "physical_ordinal": record.ordinal,
                        "lifecycle": record.lifecycle.value,
                        "retry": record.spec.is_retry,
                        "fallback": record.spec.is_fallback,
                    }
                )
            attempts.sort(key=lambda item: str(item["attempt_id"]))
            lifecycle_counts[AttemptLifecycle.DENIED.value] += len(self._denials)
            physical_total = sum(self._physical_by_family.values())
            logical_ids_by_family = {family: set() for family in ExternalCallFamily}
            for record in self._records.values():
                logical_ids_by_family[record.spec.family].add(record.spec.logical_call_id)
            for denial in self._denials:
                logical_ids_by_family[ExternalCallFamily(denial["family"])].add(str(denial["logical_call_id"]))
            logical_call_count = sum(len(values) for values in logical_ids_by_family.values())
            now = time.monotonic()
            remaining = (
                None
                if self._deadline_monotonic is None
                else round(
                    max(0.0, self._deadline_monotonic - now),
                    6,
                )
            )
            if self._deadline_monotonic is None:
                deadline_status = "not_activated"
            elif self._closed_monotonic is not None:
                deadline_status = (
                    "closed_within_deadline"
                    if self._closed_monotonic <= self._deadline_monotonic
                    else "closed_after_deadline"
                )
            elif remaining == 0:
                deadline_status = "exhausted"
            else:
                deadline_status = "active"
            denials = sorted(
                (dict(item) for item in self._denials),
                key=lambda item: str(item["attempt_id"]),
            )
            return {
                "enforcement": "physical_attempt_envelope",
                "profile_name": self.envelope.profile_name,
                "profile_digest": self.envelope.profile_digest,
                "pricing_version": self.envelope.pricing_version,
                "run_id": self._run_id,
                "request_id": self._request_id,
                "furthest_product_stage": self._furthest_product_stage or "configuration",
                "logical_calls": logical_call_count,
                "logical_calls_by_family": {
                    family.value: len(logical_ids_by_family[family]) for family in ExternalCallFamily
                },
                "physical_attempts": physical_total,
                "physical_attempts_by_family": {
                    family.value: self._physical_by_family[family] for family in ExternalCallFamily
                },
                "retry_attempts": self._retry_attempts,
                "fallback_attempts": self._fallback_attempts,
                "retry_posture": {
                    "maximum": self.envelope.max_retries,
                    "observed": self._retry_attempts,
                },
                "fallback_posture": {
                    "maximum": self.envelope.max_fallbacks,
                    "observed": self._fallback_attempts,
                },
                "lifecycle_counts": lifecycle_counts,
                "reserved_tokens": self._reserved_tokens.as_dict(),
                "observed_tokens": self._observed_tokens.as_dict(),
                "committed_tokens": self._committed_tokens.as_dict(),
                "reserved_cost_usd": _decimal_json(self._reserved_cost_usd),
                "observed_cost_usd": _decimal_json(self._observed_cost_usd),
                "conservative_cost_usd": _decimal_json(self._conservative_cost_usd),
                "committed_cost_usd": _decimal_json(self._committed_cost_usd),
                "activated": self._deadline_monotonic is not None,
                "deadline_seconds": self.envelope.deadline_seconds,
                "remaining_seconds": remaining,
                "deadline_posture": {
                    "status": deadline_status,
                    "configured_seconds": self.envelope.deadline_seconds,
                    "remaining_seconds": remaining,
                },
                "limits": {
                    "max_total_attempts": self.envelope.max_total_attempts,
                    "max_attempts_by_family": {
                        family.value: self.envelope.max_attempts_by_family[family] for family in ExternalCallFamily
                    },
                    "max_tokens": self.envelope.max_tokens.as_dict(),
                    "max_tokens_by_family": {
                        family.value: self.envelope.max_tokens_by_family[family].as_dict()
                        for family in ExternalCallFamily
                    },
                    "max_per_attempt_usd": _decimal_json(self.envelope.max_per_attempt_usd),
                    "max_run_usd": _decimal_json(self.envelope.max_run_usd),
                    "max_retries": self.envelope.max_retries,
                    "max_fallbacks": self.envelope.max_fallbacks,
                },
                "active_attempts": lifecycle_counts[AttemptLifecycle.RESERVED.value]
                + lifecycle_counts[AttemptLifecycle.DISPATCHED.value],
                "unreserved_dispatches": 0,
                "persistence_suppressed": self.persistence_suppressed,
                "attempts": attempts,
                "denials": denials,
            }

    def to_trace_fragment(self) -> dict[str, Any]:
        result = {
            "run_cap_enforcement": {
                **self.observed_counts(),
                "max_search_dispatches": self.max_search_dispatches,
                "max_fetch_read_operations": self.max_fetch_read_operations,
                "max_author_model_calls": self.max_author_model_calls,
                "max_smart_search_judgment_model_calls": (self.max_smart_search_judgment_model_calls),
                "max_retries": self.max_retries,
                "facts": list(self.facts),
            }
        }
        if self.bounded:
            result["run_cap_enforcement"]["physical"] = self.physical_snapshot()
        return result

    def _admission_denial_reason(
        self,
        spec: ExternalAttemptSpec,
        cost: Decimal,
        remaining: float,
    ) -> str | None:
        assert self.envelope is not None
        if remaining <= 0:
            return "deadline_exhausted"
        if spec.requested_timeout_seconds <= 0:
            return "invalid_timeout"
        admitted_total = sum(self._admitted_by_family.values())
        if admitted_total + 1 > self.envelope.max_total_attempts:
            return "total_attempt_cap"
        if self._admitted_by_family[spec.family] + 1 > self.envelope.max_attempts_by_family[spec.family]:
            return f"{spec.family.value}_attempt_cap"
        if spec.is_retry and self._retry_attempts + 1 > self.envelope.max_retries:
            return "retry_cap"
        if spec.is_fallback and self._fallback_attempts + 1 > self.envelope.max_fallbacks:
            return "fallback_cap"
        if cost > self.envelope.max_per_attempt_usd:
            return "per_attempt_cost_cap"
        if self._committed_cost_usd + cost > self.envelope.max_run_usd:
            return "run_cost_cap"
        if not _usage_within(
            _add_usage(self._committed_tokens, spec.max_usage),
            self.envelope.max_tokens,
        ):
            return "run_token_cap"
        family_committed = TokenUsage()
        for record in self._records.values():
            if record.spec.family is spec.family and record.lifecycle not in (
                AttemptLifecycle.CANCELLED_PRE_DISPATCH,
                AttemptLifecycle.SETTLED_OBSERVED,
            ):
                family_committed = _add_usage(
                    family_committed,
                    record.spec.max_usage,
                )
            elif (
                record.spec.family is spec.family
                and record.lifecycle is AttemptLifecycle.SETTLED_OBSERVED
                and record.observed_usage is not None
            ):
                family_committed = _add_usage(
                    family_committed,
                    record.observed_usage,
                )
        if not _usage_within(
            _add_usage(family_committed, spec.max_usage),
            self.envelope.max_tokens_by_family[spec.family],
        ):
            return f"{spec.family.value}_token_cap"
        return None

    def _reservation_timeout(self, attempt_id: str) -> float:
        with self._lock:
            return self._record(attempt_id).timeout_seconds

    def _reservation_lifecycle(self, attempt_id: str) -> AttemptLifecycle:
        with self._lock:
            return self._record(attempt_id).lifecycle

    def _mark_dispatched(self, attempt_id: str) -> None:
        with self._lock:
            record = self._record(attempt_id)
            if record.lifecycle is not AttemptLifecycle.RESERVED:
                raise RuntimeError("reservation is not dispatchable")
            if self.remaining_seconds() <= 0:
                self._cancel_pre_dispatch(attempt_id, "deadline_before_dispatch")
                raise RunCapExceeded(
                    "deadline_exhausted",
                    family=record.spec.family,
                )
            record.lifecycle = AttemptLifecycle.DISPATCHED
            self._physical_by_family[record.spec.family] += 1

    def _settle_observed(self, attempt_id: str, usage: TokenUsage) -> None:
        with self._lock:
            record = self._record(attempt_id)
            if record.lifecycle is not AttemptLifecycle.DISPATCHED:
                raise RuntimeError("only a dispatched attempt can settle")
            if not _usage_within(usage, record.spec.max_usage):
                record.lifecycle = AttemptLifecycle.SETTLED_CONSERVATIVE
                record.settlement_reason = "observed_usage_exceeded_reservation"
                self._conservative_cost_usd += record.reserved_cost_usd
                raise RunCapExceeded(
                    "observed_usage_exceeded_reservation",
                    family=record.spec.family,
                )
            actual_cost = record.spec.pricing.cost_for(usage)
            if actual_cost > record.reserved_cost_usd:
                record.lifecycle = AttemptLifecycle.SETTLED_CONSERVATIVE
                record.settlement_reason = "observed_cost_exceeded_reservation"
                self._conservative_cost_usd += record.reserved_cost_usd
                raise RunCapExceeded(
                    "observed_cost_exceeded_reservation",
                    family=record.spec.family,
                )
            record.lifecycle = AttemptLifecycle.SETTLED_OBSERVED
            record.observed_usage = usage
            record.settled_cost_usd = actual_cost
            self._committed_tokens = _subtract_usage(
                self._committed_tokens,
                record.spec.max_usage,
            )
            self._committed_tokens = _add_usage(self._committed_tokens, usage)
            self._observed_tokens = _add_usage(self._observed_tokens, usage)
            self._committed_cost_usd -= record.reserved_cost_usd
            self._committed_cost_usd += actual_cost
            self._observed_cost_usd += actual_cost

    def _settle_conservative(self, attempt_id: str, reason: str) -> None:
        with self._lock:
            record = self._record(attempt_id)
            if record.lifecycle is not AttemptLifecycle.DISPATCHED:
                raise RuntimeError("only a dispatched attempt can settle")
            record.lifecycle = AttemptLifecycle.SETTLED_CONSERVATIVE
            record.settlement_reason = _safe_identity(reason, prefix="settlement")
            record.settled_cost_usd = record.reserved_cost_usd
            self._conservative_cost_usd += record.reserved_cost_usd

    def _cancel_pre_dispatch(self, attempt_id: str, reason: str) -> None:
        with self._lock:
            record = self._record(attempt_id)
            if record.lifecycle is not AttemptLifecycle.RESERVED:
                raise RuntimeError("only an undispatched reservation can cancel")
            record.lifecycle = AttemptLifecycle.CANCELLED_PRE_DISPATCH
            record.settlement_reason = _safe_identity(reason, prefix="cancel")
            self._admitted_by_family[record.spec.family] -= 1
            if record.spec.is_retry:
                self._retry_attempts -= 1
            if record.spec.is_fallback:
                self._fallback_attempts -= 1
            self._committed_tokens = _subtract_usage(
                self._committed_tokens,
                record.spec.max_usage,
            )
            self._committed_cost_usd -= record.reserved_cost_usd

    def _record(self, attempt_id: str) -> _AttemptRecord:
        try:
            return self._records[attempt_id]
        except KeyError as exc:
            raise RuntimeError("unknown attempt reservation") from exc

    def _require_active(self) -> None:
        if self._run_id is None or self._deadline_monotonic is None:
            raise RunCapExceeded("ledger_not_active")

    def _mark(self, attr: str, maximum: int) -> None:
        with self._lock:
            next_value = int(getattr(self, attr)) + 1
            if next_value > int(maximum):
                raise RunCapExceeded(
                    f"{attr}_cap",
                    internal_message=f"{attr} cap exceeded",
                )
            setattr(self, attr, next_value)


def conservative_text_token_upper_bound(
    text: str,
    *,
    structural_overhead: int = 16,
) -> int:
    """Return a tokenizer-independent upper bound based on UTF-8 bytes."""

    if structural_overhead < 0:
        raise ValueError("structural_overhead must be non-negative")
    return len(str(text).encode("utf-8")) + structural_overhead


def model_usage_bound(prompt: str, system_prompt: str = "") -> TokenUsage:
    """Build a tokenizer-independent conservative per-attempt model bound."""

    input_bound = conservative_text_token_upper_bound(
        f"{system_prompt}\n{prompt}",
        structural_overhead=64,
    )
    return TokenUsage(
        input_tokens=input_bound,
        output_tokens=MODEL_OUTPUT_TOKEN_LIMIT,
        reasoning_tokens=MODEL_REASONING_TOKEN_LIMIT,
    )


def embedding_usage_bound(texts: Iterable[str]) -> TokenUsage:
    """Build a conservative aggregate embedding-token bound for one batch."""

    bound = sum(
        conservative_text_token_upper_bound(text, structural_overhead=8)
        for text in texts
    )
    return TokenUsage(embedding_tokens=bound)


def mark_cap_aware(transport: Callable[..., Any]) -> Callable[..., Any]:
    """Mark an injected fake or transport as owning physical reservations."""

    setattr(transport, "__scryraven_cap_aware__", True)
    return transport


def is_cap_aware(transport: Callable[..., Any]) -> bool:
    return bool(getattr(transport, "__scryraven_cap_aware__", False))


def _safe_identity(value: str, *, prefix: str) -> str:
    clean = str(value or "").strip()
    if _SAFE_IDENTITY.fullmatch(clean):
        return clean
    digest = hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _add_usage(left: TokenUsage, right: TokenUsage) -> TokenUsage:
    values = {key: left.as_dict()[key] + right.as_dict()[key] for key in left.as_dict()}
    return TokenUsage(**values)


def _subtract_usage(left: TokenUsage, right: TokenUsage) -> TokenUsage:
    values = {key: left.as_dict()[key] - right.as_dict()[key] for key in left.as_dict()}
    if any(value < 0 for value in values.values()):
        raise RuntimeError("ledger usage underflow")
    return TokenUsage(**values)


def _usage_within(value: TokenUsage, limit: TokenUsage) -> bool:
    return all(
        value.without_cached_dimension()[key] <= limit.without_cached_dimension()[key]
        for key in value.without_cached_dimension()
    )


def _decimal_json(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.000001")))
