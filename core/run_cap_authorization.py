"""Compile one explicit local bounded-run authorization into a run-scoped policy."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from core.cap_enforcement import (
    ExternalCallFamily,
    RoutePricing,
    RunCapEnvelope,
    RunCapPolicy,
    TokenUsage,
    normalize_route_key,
)

SCHEMA_VERSION = "scryraven_bounded_run_authorization_v1"
MAX_AUTHORIZATION_BYTES = 64 * 1024
_SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_IDENTITY = re.compile(r"[A-Za-z0-9_.:-]{1,120}\Z")
_ZERO = Decimal("0")

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "authorization_id",
        "repository_sha",
        "request",
        "pricing_fact_set_id",
        "routes",
        "limits",
        "max_run_usd",
    }
)
_REQUEST_KEYS = frozenset(
    {"query_sha256", "mode", "include_domains", "exclude_domains"}
)
_ROUTE_OBJECT_KEYS = frozenset({"provider", "route", "pricing"})
_PRICING_KEYS = frozenset(
    {
        "input_per_million_usd",
        "cached_input_per_million_usd",
        "output_per_million_usd",
        "reasoning_per_million_usd",
        "embedding_per_million_usd",
        "flat_attempt_usd",
    }
)
_ROUTES_KEYS = frozenset(
    {"fast_model", "smart_model", "embedding", "search", "read"}
)
_LIMITS_KEYS = frozenset(
    {"attempts", "tokens", "max_retries", "max_fallbacks", "deadline_seconds"}
)
_ATTEMPT_KEYS = frozenset({"model", "embedding", "search", "read", "total"})
_TOKEN_KEYS = frozenset(
    {"input", "cached_input", "output", "reasoning", "embedding"}
)


class BoundedRunAuthorizationError(Exception):
    """Sanitized pre-activation rejection for one bounded authorization."""

    def __init__(
        self,
        reason_code: str,
        *,
        authorization_id: str | None = None,
        authorization_digest: str | None = None,
        observed_query_digest: str | None = None,
    ) -> None:
        super().__init__(reason_code)
        self.reason_code = _require_safe_identity(reason_code, field="reason_code")
        self.authorization_id = authorization_id
        self.authorization_digest = authorization_digest
        self.observed_query_digest = observed_query_digest


@dataclass(frozen=True, slots=True)
class CompiledRunCapAuthorization:
    """Immutable compiler result for one local bounded-run authorization."""

    authorization_id: str
    authorization_digest: str
    repository_sha: str
    pricing_fact_set_id: str
    envelope: RunCapEnvelope
    route_pricing: Mapping[tuple[ExternalCallFamily, str, str], RoutePricing]
    policy: RunCapPolicy


def query_sha256(query: str) -> str:
    """Return the binding digest for one query without mutating product input."""

    if "\x00" in query:
        raise BoundedRunAuthorizationError("invalid_query_nul")
    normalized = unicodedata.normalize("NFC", query)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def canonicalize_domains(domains: Iterable[str]) -> list[str]:
    """Return authorization-only canonical domain form for binding compares."""

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in domains:
        item = str(raw).strip().lower().rstrip(".")
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    cleaned.sort()
    return cleaned


def authorization_digest_for(document: Mapping[str, Any]) -> str:
    """Compute the canonical SHA-256 digest for one authority-bearing document."""

    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def resolve_local_repository_identity(repo_root: Path) -> str:
    """Return HEAD SHA when the tracked worktree/index is clean; else fail closed."""

    root = Path(repo_root)
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise BoundedRunAuthorizationError("repository_identity_unavailable") from exc
    if head.returncode != 0:
        raise BoundedRunAuthorizationError("repository_identity_unavailable")
    sha = str(head.stdout or "").strip().lower()
    if not _SHA1_RE.fullmatch(sha):
        raise BoundedRunAuthorizationError("repository_identity_unavailable")
    try:
        status = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise BoundedRunAuthorizationError("repository_identity_unavailable") from exc
    if status.returncode != 0:
        raise BoundedRunAuthorizationError("repository_identity_unavailable")
    if str(status.stdout or "").strip():
        raise BoundedRunAuthorizationError("dirty_tracked_checkout")
    return sha


def compile_bounded_run_authorization(
    path: str | Path,
    *,
    query: str,
    mode: str,
    include_domains: list[str],
    exclude_domains: list[str],
    fast_provider: str,
    fast_model: str,
    smart_provider: str,
    smart_model: str,
    embed_provider: str,
    embed_model: str,
    repo_root: Path,
) -> CompiledRunCapAuthorization:
    """Parse, bind, and compile one local authorization into one fresh policy."""

    authorization_id: str | None = None
    authorization_digest: str | None = None
    try:
        raw_bytes = _read_authorization_bytes(path)
        document = _parse_json_object(raw_bytes)
        parsed = _validate_schema(document)
        authorization_id = parsed["authorization_id"]
        authorization_digest = authorization_digest_for(parsed["canonical"])
        _bind_repository(parsed["repository_sha"], repo_root=repo_root)
        _bind_request(
            parsed["request"],
            query=query,
            mode=mode,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            authorization_id=authorization_id,
            authorization_digest=authorization_digest,
        )
        _bind_model_routes(
            parsed["routes"],
            fast_provider=fast_provider,
            fast_model=fast_model,
            smart_provider=smart_provider,
            smart_model=smart_model,
            embed_provider=embed_provider,
            embed_model=embed_model,
        )
        route_pricing = _compile_route_pricing(parsed["routes"])
        max_run_usd = _parse_positive_decimal_string(parsed["max_run_usd"], field="max_run_usd")
        max_per_attempt_usd = _derive_max_per_attempt(
            route_pricing=route_pricing,
            token_limits=parsed["limits"]["tokens"],
            max_run_usd=max_run_usd,
        )
        envelope = RunCapEnvelope(
            profile_name=parsed["authorization_id"],
            profile_digest=authorization_digest,
            pricing_version=parsed["pricing_fact_set_id"],
            deadline_seconds=float(parsed["limits"]["deadline_seconds"]),
            max_total_attempts=int(parsed["limits"]["attempts"]["total"]),
            max_attempts_by_family={
                ExternalCallFamily.MODEL: int(parsed["limits"]["attempts"]["model"]),
                ExternalCallFamily.EMBEDDING: int(
                    parsed["limits"]["attempts"]["embedding"]
                ),
                ExternalCallFamily.SEARCH: int(parsed["limits"]["attempts"]["search"]),
                ExternalCallFamily.READ: int(parsed["limits"]["attempts"]["read"]),
            },
            max_tokens=TokenUsage(
                input_tokens=int(parsed["limits"]["tokens"]["input"]),
                cached_input_tokens=int(parsed["limits"]["tokens"]["cached_input"]),
                output_tokens=int(parsed["limits"]["tokens"]["output"]),
                reasoning_tokens=int(parsed["limits"]["tokens"]["reasoning"]),
                embedding_tokens=int(parsed["limits"]["tokens"]["embedding"]),
            ),
            max_tokens_by_family={
                ExternalCallFamily.MODEL: TokenUsage(
                    input_tokens=int(parsed["limits"]["tokens"]["input"]),
                    cached_input_tokens=int(parsed["limits"]["tokens"]["cached_input"]),
                    output_tokens=int(parsed["limits"]["tokens"]["output"]),
                    reasoning_tokens=int(parsed["limits"]["tokens"]["reasoning"]),
                ),
                ExternalCallFamily.EMBEDDING: TokenUsage(
                    embedding_tokens=int(parsed["limits"]["tokens"]["embedding"]),
                ),
                ExternalCallFamily.SEARCH: TokenUsage(),
                ExternalCallFamily.READ: TokenUsage(),
            },
            max_per_attempt_usd=max_per_attempt_usd,
            max_run_usd=max_run_usd,
            max_retries=int(parsed["limits"]["max_retries"]),
            max_fallbacks=int(parsed["limits"]["max_fallbacks"]),
            suppress_persistence=True,
        )
        policy = RunCapPolicy(
            max_search_dispatches=int(parsed["limits"]["attempts"]["search"]),
            max_fetch_read_operations=int(parsed["limits"]["attempts"]["read"]),
            max_author_model_calls=int(parsed["limits"]["attempts"]["model"]),
            max_smart_search_judgment_model_calls=int(
                parsed["limits"]["attempts"]["model"]
            ),
            max_retries=0,
            envelope=envelope,
            route_pricing=route_pricing,
        )
        return CompiledRunCapAuthorization(
            authorization_id=parsed["authorization_id"],
            authorization_digest=authorization_digest,
            repository_sha=parsed["repository_sha"],
            pricing_fact_set_id=parsed["pricing_fact_set_id"],
            envelope=envelope,
            route_pricing=MappingProxyType(dict(route_pricing)),
            policy=policy,
        )
    except BoundedRunAuthorizationError as exc:
        if authorization_id is not None and exc.authorization_id is None:
            exc.authorization_id = authorization_id
        if authorization_digest is not None and exc.authorization_digest is None:
            exc.authorization_digest = authorization_digest
        raise
    except (TypeError, ValueError, InvalidOperation, KeyError, json.JSONDecodeError):
        raise BoundedRunAuthorizationError(
            "invalid_authorization",
            authorization_id=authorization_id,
            authorization_digest=authorization_digest,
        ) from None


def _read_authorization_bytes(path: str | Path) -> bytes:
    try:
        file_path = Path(path)
    except TypeError as exc:
        raise BoundedRunAuthorizationError("missing_authorization_file") from exc
    try:
        if not file_path.is_file():
            raise BoundedRunAuthorizationError("missing_authorization_file")
        size = file_path.stat().st_size
        if size > MAX_AUTHORIZATION_BYTES:
            raise BoundedRunAuthorizationError("authorization_file_too_large")
        return file_path.read_bytes()
    except BoundedRunAuthorizationError:
        raise
    except OSError as exc:
        raise BoundedRunAuthorizationError("missing_authorization_file") from exc


def _reject_nonstandard_json_constant(name: str) -> None:
    """Fail closed for non-standard JSON numeric constants."""

    raise ValueError(f"nonstandard json constant: {name}")


def _parse_json_object(raw_bytes: bytes) -> dict[str, Any]:
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BoundedRunAuthorizationError("invalid_authorization_utf8") from exc
    try:
        document = json.loads(text, parse_constant=_reject_nonstandard_json_constant)
    except json.JSONDecodeError as exc:
        raise BoundedRunAuthorizationError("invalid_authorization_json") from exc
    except ValueError as exc:
        # Non-standard Infinity / -Infinity / NaN via parse_constant.
        raise BoundedRunAuthorizationError("invalid_authorization_json") from exc
    if not isinstance(document, dict):
        raise BoundedRunAuthorizationError("invalid_authorization_root")
    return document


def _validate_schema(document: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown_keys(document, _TOP_LEVEL_KEYS, reason="unknown_authorization_key")
    for key in _TOP_LEVEL_KEYS:
        if key not in document:
            raise BoundedRunAuthorizationError("missing_authorization_key")
    if document["schema_version"] != SCHEMA_VERSION:
        raise BoundedRunAuthorizationError("unknown_schema_version")
    authorization_id = _require_safe_identity(
        document["authorization_id"], field="authorization_id"
    )
    repository_sha = document["repository_sha"]
    if not isinstance(repository_sha, str) or not _SHA1_RE.fullmatch(repository_sha):
        raise BoundedRunAuthorizationError("malformed_repository_sha")
    pricing_fact_set_id = _require_safe_identity(
        document["pricing_fact_set_id"], field="pricing_fact_set_id"
    )
    if not isinstance(document["max_run_usd"], str):
        raise BoundedRunAuthorizationError("invalid_max_run_usd")
    request = _validate_request(document["request"])
    routes = _validate_routes(document["routes"])
    limits = _validate_limits(document["limits"], routes=routes)
    max_run_usd = document["max_run_usd"]
    _parse_positive_decimal_string(max_run_usd, field="max_run_usd")
    canonical_routes = {
        "fast_model": _route_public(routes["fast_model"]),
        "smart_model": _route_public(routes["smart_model"]),
        "embedding": _route_public(routes["embedding"]),
        "search": [_route_public(item) for item in routes["search"]],
        "read": [_route_public(item) for item in routes["read"]],
    }
    canonical = {
        "schema_version": SCHEMA_VERSION,
        "authorization_id": authorization_id,
        "repository_sha": repository_sha,
        "request": request,
        "pricing_fact_set_id": pricing_fact_set_id,
        "routes": canonical_routes,
        "limits": limits,
        "max_run_usd": max_run_usd,
    }
    return {
        "authorization_id": authorization_id,
        "repository_sha": repository_sha,
        "pricing_fact_set_id": pricing_fact_set_id,
        "request": request,
        "routes": routes,
        "limits": limits,
        "max_run_usd": max_run_usd,
        "canonical": canonical,
    }


def _validate_request(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BoundedRunAuthorizationError("invalid_request_type")
    _reject_unknown_keys(raw, _REQUEST_KEYS, reason="unknown_request_key")
    for key in _REQUEST_KEYS:
        if key not in raw:
            raise BoundedRunAuthorizationError("missing_request_key")
    query_sha = raw["query_sha256"]
    if not isinstance(query_sha, str) or not _SHA256_RE.fullmatch(query_sha):
        raise BoundedRunAuthorizationError("malformed_query_sha")
    mode = raw["mode"]
    if not isinstance(mode, str) or mode not in {"Fast", "Balanced", "Deep"}:
        raise BoundedRunAuthorizationError("invalid_mode")
    include_domains = _validate_domain_list(raw["include_domains"], field="include_domains")
    exclude_domains = _validate_domain_list(raw["exclude_domains"], field="exclude_domains")
    return {
        "query_sha256": query_sha,
        "mode": mode,
        "include_domains": include_domains,
        "exclude_domains": exclude_domains,
    }


def _validate_domain_list(raw: Any, *, field: str) -> list[str]:
    if not isinstance(raw, list):
        raise BoundedRunAuthorizationError(f"invalid_{field}_type")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise BoundedRunAuthorizationError(f"invalid_{field}_type")
        values.append(item)
    return values


def _validate_routes(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BoundedRunAuthorizationError("invalid_routes_type")
    _reject_unknown_keys(raw, _ROUTES_KEYS, reason="unknown_routes_key")
    for key in _ROUTES_KEYS:
        if key not in raw:
            raise BoundedRunAuthorizationError("missing_routes_key")
    return {
        "fast_model": _validate_route_object(raw["fast_model"], family="model"),
        "smart_model": _validate_route_object(raw["smart_model"], family="model"),
        "embedding": _validate_route_object(raw["embedding"], family="embedding"),
        "search": _validate_route_list(raw["search"], family="search"),
        "read": _validate_route_list(raw["read"], family="read"),
    }


def _validate_route_object(raw: Any, *, family: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BoundedRunAuthorizationError("invalid_route_type")
    _reject_unknown_keys(raw, _ROUTE_OBJECT_KEYS, reason="unknown_route_key")
    for key in _ROUTE_OBJECT_KEYS:
        if key not in raw:
            raise BoundedRunAuthorizationError("missing_route_key")
    provider = _require_safe_identity(raw["provider"], field="provider")
    route = _require_safe_identity(raw["route"], field="route")
    pricing = _validate_pricing(raw["pricing"])
    return {"provider": provider, "route": route, "pricing": pricing, "family": family}


def _validate_route_list(raw: Any, *, family: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise BoundedRunAuthorizationError("invalid_route_list_type")
    routes = [_validate_route_object(item, family=family) for item in raw]
    seen: set[tuple[str, str]] = set()
    for item in routes:
        key = normalize_route_key(family, item["provider"], item["route"])[1:]
        if key in seen:
            raise BoundedRunAuthorizationError(f"duplicate_{family}_route")
        seen.add(key)
    return routes


def _validate_pricing(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise BoundedRunAuthorizationError("invalid_pricing_type")
    _reject_unknown_keys(raw, _PRICING_KEYS, reason="unknown_pricing_key")
    for key in _PRICING_KEYS:
        if key not in raw:
            raise BoundedRunAuthorizationError("missing_pricing_key")
        if not isinstance(raw[key], str):
            raise BoundedRunAuthorizationError("invalid_pricing_type")
        _parse_nonnegative_decimal_string(raw[key], field=key)
    return {key: str(raw[key]) for key in sorted(_PRICING_KEYS)}


def _validate_limits(raw: Any, *, routes: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BoundedRunAuthorizationError("invalid_limits_type")
    _reject_unknown_keys(raw, _LIMITS_KEYS, reason="unknown_limits_key")
    for key in _LIMITS_KEYS:
        if key not in raw:
            raise BoundedRunAuthorizationError("missing_limits_key")
    attempts_raw = raw["attempts"]
    if not isinstance(attempts_raw, dict):
        raise BoundedRunAuthorizationError("invalid_attempts_type")
    _reject_unknown_keys(attempts_raw, _ATTEMPT_KEYS, reason="unknown_attempts_key")
    for key in _ATTEMPT_KEYS:
        if key not in attempts_raw:
            raise BoundedRunAuthorizationError("missing_attempts_key")
    attempts = {
        key: _require_nonnegative_int(attempts_raw[key], field=f"attempts.{key}")
        for key in _ATTEMPT_KEYS
    }
    if attempts["total"] <= 0:
        raise BoundedRunAuthorizationError("invalid_total_attempts")
    for family in ("model", "embedding", "search", "read"):
        if attempts[family] > attempts["total"]:
            raise BoundedRunAuthorizationError("family_attempt_exceeds_total")
    tokens_raw = raw["tokens"]
    if not isinstance(tokens_raw, dict):
        raise BoundedRunAuthorizationError("invalid_tokens_type")
    _reject_unknown_keys(tokens_raw, _TOKEN_KEYS, reason="unknown_tokens_key")
    for key in _TOKEN_KEYS:
        if key not in tokens_raw:
            raise BoundedRunAuthorizationError("missing_tokens_key")
    tokens = {
        key: _require_nonnegative_int(tokens_raw[key], field=f"tokens.{key}")
        for key in _TOKEN_KEYS
    }
    if tokens["cached_input"] > tokens["input"]:
        raise BoundedRunAuthorizationError("cached_input_exceeds_input")
    max_retries = _require_nonnegative_int(raw["max_retries"], field="max_retries")
    max_fallbacks = _require_nonnegative_int(raw["max_fallbacks"], field="max_fallbacks")
    if max_retries != 0:
        raise BoundedRunAuthorizationError("nonzero_max_retries")
    if max_fallbacks != 0:
        raise BoundedRunAuthorizationError("nonzero_max_fallbacks")
    deadline = raw["deadline_seconds"]
    if isinstance(deadline, bool) or not isinstance(deadline, (int, float)):
        raise BoundedRunAuthorizationError("invalid_deadline")
    if deadline <= 0 or not math.isfinite(deadline):
        raise BoundedRunAuthorizationError("invalid_deadline")
    if attempts["search"] > 0 and not routes["search"]:
        raise BoundedRunAuthorizationError("missing_search_routes")
    if attempts["read"] > 0 and not routes["read"]:
        raise BoundedRunAuthorizationError("missing_read_routes")
    return {
        "attempts": attempts,
        "tokens": tokens,
        "max_retries": max_retries,
        "max_fallbacks": max_fallbacks,
        "deadline_seconds": deadline,
    }


def _bind_repository(expected_sha: str, *, repo_root: Path) -> None:
    observed = resolve_local_repository_identity(repo_root)
    if observed != expected_sha:
        raise BoundedRunAuthorizationError("repository_sha_mismatch")


def _bind_request(
    request: Mapping[str, Any],
    *,
    query: str,
    mode: str,
    include_domains: list[str],
    exclude_domains: list[str],
    authorization_id: str,
    authorization_digest: str,
) -> None:
    observed_digest = query_sha256(query)
    if observed_digest != request["query_sha256"]:
        raise BoundedRunAuthorizationError(
            "query_mismatch",
            authorization_id=authorization_id,
            authorization_digest=authorization_digest,
            observed_query_digest=observed_digest,
        )
    if mode != request["mode"]:
        raise BoundedRunAuthorizationError("mode_mismatch")
    if canonicalize_domains(include_domains) != canonicalize_domains(
        request["include_domains"]
    ):
        raise BoundedRunAuthorizationError("include_domains_mismatch")
    if canonicalize_domains(exclude_domains) != canonicalize_domains(
        request["exclude_domains"]
    ):
        raise BoundedRunAuthorizationError("exclude_domains_mismatch")


def _bind_model_routes(
    routes: Mapping[str, Any],
    *,
    fast_provider: str,
    fast_model: str,
    smart_provider: str,
    smart_model: str,
    embed_provider: str,
    embed_model: str,
) -> None:
    checks = (
        ("fast_model_mismatch", routes["fast_model"], fast_provider, fast_model, "model"),
        ("smart_model_mismatch", routes["smart_model"], smart_provider, smart_model, "model"),
        ("embedding_mismatch", routes["embedding"], embed_provider, embed_model, "embedding"),
    )
    for reason, route_obj, provider, route, family in checks:
        expected = normalize_route_key(family, route_obj["provider"], route_obj["route"])
        observed = normalize_route_key(family, provider, route)
        if expected != observed:
            raise BoundedRunAuthorizationError(reason)



def _route_public(route_obj: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider": route_obj["provider"],
        "route": route_obj["route"],
        "pricing": route_obj["pricing"],
    }


def _compile_route_pricing(
    routes: Mapping[str, Any],
) -> dict[tuple[ExternalCallFamily, str, str], RoutePricing]:
    pricing_map: dict[tuple[ExternalCallFamily, str, str], RoutePricing] = {}

    def add(family: ExternalCallFamily, route_obj: Mapping[str, Any]) -> None:
        key = normalize_route_key(family, route_obj["provider"], route_obj["route"])
        pricing = _route_pricing_from_strings(
            key=f"{key[1]}.{key[2]}",
            pricing=route_obj["pricing"],
        )
        if key in pricing_map and pricing_map[key] != pricing:
            raise BoundedRunAuthorizationError("conflicting_route_pricing")
        pricing_map[key] = pricing

    add(ExternalCallFamily.MODEL, routes["fast_model"])
    add(ExternalCallFamily.MODEL, routes["smart_model"])
    add(ExternalCallFamily.EMBEDDING, routes["embedding"])
    for item in routes["search"]:
        add(ExternalCallFamily.SEARCH, item)
    for item in routes["read"]:
        add(ExternalCallFamily.READ, item)
    return pricing_map


def _route_pricing_from_strings(*, key: str, pricing: Mapping[str, str]) -> RoutePricing:
    try:
        return RoutePricing(
            pricing_key=key,
            input_per_million_usd=Decimal(pricing["input_per_million_usd"]),
            cached_input_per_million_usd=Decimal(
                pricing["cached_input_per_million_usd"]
            ),
            output_per_million_usd=Decimal(pricing["output_per_million_usd"]),
            reasoning_per_million_usd=Decimal(pricing["reasoning_per_million_usd"]),
            embedding_per_million_usd=Decimal(pricing["embedding_per_million_usd"]),
            flat_attempt_usd=Decimal(pricing["flat_attempt_usd"]),
        )
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BoundedRunAuthorizationError("invalid_route_pricing") from exc


def _derive_max_per_attempt(
    *,
    route_pricing: Mapping[tuple[ExternalCallFamily, str, str], RoutePricing],
    token_limits: Mapping[str, int],
    max_run_usd: Decimal,
) -> Decimal:
    model_usage = TokenUsage(
        input_tokens=int(token_limits["input"]),
        cached_input_tokens=int(token_limits["cached_input"]),
        output_tokens=int(token_limits["output"]),
        reasoning_tokens=int(token_limits["reasoning"]),
    )
    embedding_usage = TokenUsage(embedding_tokens=int(token_limits["embedding"]))
    largest = _ZERO
    for (family, _provider, _route), pricing in route_pricing.items():
        if family is ExternalCallFamily.MODEL:
            cost = pricing.cost_for(model_usage)
        elif family is ExternalCallFamily.EMBEDDING:
            cost = pricing.cost_for(embedding_usage)
        else:
            cost = pricing.cost_for(TokenUsage())
        if cost > largest:
            largest = cost
    derived = min(max_run_usd, largest)
    if derived < _ZERO:
        raise BoundedRunAuthorizationError("invalid_max_per_attempt_usd")
    return derived


def _parse_positive_decimal_string(raw: str, *, field: str) -> Decimal:
    value = _parse_nonnegative_decimal_string(raw, field=field)
    if value <= _ZERO:
        raise BoundedRunAuthorizationError(f"invalid_{field}")
    return value


def _parse_nonnegative_decimal_string(raw: str, *, field: str) -> Decimal:
    if not isinstance(raw, str):
        raise BoundedRunAuthorizationError(f"invalid_{field}")
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError) as exc:
        raise BoundedRunAuthorizationError(f"invalid_{field}") from exc
    if not value.is_finite() or value < _ZERO:
        raise BoundedRunAuthorizationError(f"invalid_{field}")
    return value


def _require_nonnegative_int(raw: Any, *, field: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise BoundedRunAuthorizationError(f"invalid_{field}")
    if raw < 0:
        raise BoundedRunAuthorizationError(f"invalid_{field}")
    return raw


def _require_safe_identity(raw: Any, *, field: str) -> str:
    if not isinstance(raw, str) or not _SAFE_IDENTITY.fullmatch(raw):
        raise BoundedRunAuthorizationError(f"unsafe_{field}")
    return raw


def _reject_unknown_keys(
    document: Mapping[str, Any],
    allowed: frozenset[str],
    *,
    reason: str,
) -> None:
    if set(document) - allowed:
        raise BoundedRunAuthorizationError(reason)


__all__ = [
    "BoundedRunAuthorizationError",
    "CompiledRunCapAuthorization",
    "MAX_AUTHORIZATION_BYTES",
    "SCHEMA_VERSION",
    "authorization_digest_for",
    "canonicalize_domains",
    "compile_bounded_run_authorization",
    "query_sha256",
    "resolve_local_repository_identity",
]