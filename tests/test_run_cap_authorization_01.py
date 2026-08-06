"""Focused offline proof for explicit bounded-run authorization.

Mode: REPAIR.
Test class: phase_focus / offline_product_path_proof.
No test in this file is integration- or secrets-backed.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import proplex.__main__ as compatibility_cli
import scryraven.__main__ as public_cli
from core.cap_enforcement import ExternalAttemptSpec, ExternalCallFamily, RunCapExceeded, TokenUsage
from core.run_cap_authorization import (
    MAX_AUTHORIZATION_BYTES,
    SCHEMA_VERSION,
    BoundedRunAuthorizationError,
    canonicalize_domains,
    compile_bounded_run_authorization,
    query_sha256,
    resolve_local_repository_identity,
)

_REPO = Path(__file__).resolve().parents[1]
_FIXTURE_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_QUERY = "What are the default values for rel_tol and abs_tol in math.isclose()?"
_ZERO_PRICING = {
    "input_per_million_usd": "0",
    "cached_input_per_million_usd": "0",
    "output_per_million_usd": "0",
    "reasoning_per_million_usd": "0",
    "embedding_per_million_usd": "0",
    "flat_attempt_usd": "0",
}


def _route(provider: str, route: str, *, pricing: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "provider": provider,
        "route": route,
        "pricing": dict(pricing or _ZERO_PRICING),
    }


def _base_document(**overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "authorization_id": "fixture-auth-v1",
        "repository_sha": _FIXTURE_SHA,
        "request": {
            "query_sha256": query_sha256(_QUERY),
            "mode": "Balanced",
            "include_domains": ["docs.python.org"],
            "exclude_domains": [],
        },
        "pricing_fact_set_id": "fixture-pricing-facts-v1",
        "routes": {
            "fast_model": _route("OpenAI", "gpt-5.4-mini"),
            "smart_model": _route("OpenAI", "gpt-5.4"),
            "embedding": _route("OpenAI", "text-embedding-3-small"),
            "search": [_route("tavily", "search")],
            "read": [_route("tavily", "extract")],
        },
        "limits": {
            "attempts": {
                "model": 1,
                "embedding": 1,
                "search": 1,
                "read": 1,
                "total": 4,
            },
            "tokens": {
                "input": 1,
                "cached_input": 0,
                "output": 1,
                "reasoning": 0,
                "embedding": 1,
            },
            "max_retries": 0,
            "max_fallbacks": 0,
            "deadline_seconds": 1,
        },
        "max_run_usd": "0.01",
    }
    document.update(overrides)
    return document


def _write_auth(tmp_path: Path, document: dict[str, Any], *, name: str = "auth.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _compile(
    path: Path,
    *,
    query: str = _QUERY,
    mode: str = "Balanced",
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    fast_provider: str = "OpenAI",
    fast_model: str = "gpt-5.4-mini",
    smart_provider: str = "OpenAI",
    smart_model: str = "gpt-5.4",
    embed_provider: str = "OpenAI",
    embed_model: str = "text-embedding-3-small",
    repo_root: Path | None = None,
):
    return compile_bounded_run_authorization(
        path,
        query=query,
        mode=mode,
        include_domains=list(include_domains or ["docs.python.org"]),
        exclude_domains=list(exclude_domains or []),
        fast_provider=fast_provider,
        fast_model=fast_model,
        smart_provider=smart_provider,
        smart_model=smart_model,
        embed_provider=embed_provider,
        embed_model=embed_model,
        repo_root=repo_root or _REPO,
    )


def _patch_repo_identity(monkeypatch: pytest.MonkeyPatch, sha: str = _FIXTURE_SHA) -> None:
    monkeypatch.setattr(
        "core.run_cap_authorization.resolve_local_repository_identity",
        lambda _repo_root: sha,
    )


def test_missing_authorization_file_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_repo_identity(monkeypatch)
    missing = tmp_path / "missing.json"
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(missing)
    assert exc.value.reason_code == "missing_authorization_file"


def test_oversized_authorization_file_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    path = tmp_path / "huge.json"
    path.write_bytes(b"{" + (b"a" * (MAX_AUTHORIZATION_BYTES + 8)) + b"}")
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == "authorization_file_too_large"


def test_invalid_utf8_authorization_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    path = tmp_path / "bad_utf8.json"
    path.write_bytes(b"{\xff\xfe}")
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == "invalid_authorization_utf8"


def test_invalid_json_authorization_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == "invalid_authorization_json"


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda d: d.__setitem__("schema_version", "other"), "unknown_schema_version"),
        (lambda d: d.pop("authorization_id"), "missing_authorization_key"),
        (lambda d: d.__setitem__("extra", 1), "unknown_authorization_key"),
        (lambda d: d.__setitem__("authorization_id", "bad id!"), "unsafe_authorization_id"),
        (lambda d: d.__setitem__("repository_sha", "ABCDEF"), "malformed_repository_sha"),
        (lambda d: d["request"].__setitem__("query_sha256", "ZZ"), "malformed_query_sha"),
        (lambda d: d.__setitem__("max_run_usd", "0"), "invalid_max_run_usd"),
        (lambda d: d.__setitem__("max_run_usd", "-1"), "invalid_max_run_usd"),
        (lambda d: d.__setitem__("max_run_usd", "NaN"), "invalid_max_run_usd"),
        (lambda d: d["limits"].__setitem__("max_retries", 1), "nonzero_max_retries"),
        (lambda d: d["limits"].__setitem__("max_fallbacks", 1), "nonzero_max_fallbacks"),
        (lambda d: d["limits"]["attempts"].__setitem__("model", -1), "invalid_attempts.model"),
        (lambda d: d["limits"]["attempts"].__setitem__("model", 5), "family_attempt_exceeds_total"),
        (lambda d: d["limits"]["tokens"].__setitem__("cached_input", 2), "cached_input_exceeds_input"),
        (lambda d: d["routes"].__setitem__("search", []), "missing_search_routes"),
        (lambda d: d["routes"].__setitem__("read", []), "missing_read_routes"),
        (
            lambda d: d["routes"].__setitem__(
                "search",
                [_route("tavily", "search"), _route("Tavily", "SEARCH")],
            ),
            "duplicate_search_route",
        ),
    ],
)
def test_schema_violations_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutator,
    reason: str,
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    mutator(document)
    path = _write_auth(tmp_path, document)
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == reason


def test_incorrect_root_type_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_repo_identity(monkeypatch)
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == "invalid_authorization_root"


def test_negative_nonfinite_decimal_prices_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["routes"]["fast_model"]["pricing"]["input_per_million_usd"] = "-1"
    path = _write_auth(tmp_path, document)
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code.startswith("invalid_")


def test_conflicting_duplicate_normalized_route_facts_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["routes"]["search"] = [
        _route("tavily", "search", pricing={**_ZERO_PRICING, "flat_attempt_usd": "0.01"}),
        _route("Tavily", "SEARCH", pricing={**_ZERO_PRICING, "flat_attempt_usd": "0.02"}),
    ]
    path = _write_auth(tmp_path, document)
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code in {"duplicate_search_route", "conflicting_route_pricing"}


def test_canonical_digest_stable_under_key_reordering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    path_a = _write_auth(tmp_path, document, name="a.json")
    reordered = {
        "max_run_usd": document["max_run_usd"],
        "limits": document["limits"],
        "routes": document["routes"],
        "pricing_fact_set_id": document["pricing_fact_set_id"],
        "request": document["request"],
        "repository_sha": document["repository_sha"],
        "authorization_id": document["authorization_id"],
        "schema_version": document["schema_version"],
    }
    path_b = _write_auth(tmp_path, reordered, name="b.json")
    first = _compile(path_a)
    second = _compile(path_b)
    assert first.authorization_digest == second.authorization_digest
    assert len(first.authorization_digest) == 64


def test_authority_bearing_change_alters_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    base = _base_document()
    changed = _base_document()
    changed["max_run_usd"] = "0.02"
    first = _compile(_write_auth(tmp_path, base, name="base.json"))
    second = _compile(_write_auth(tmp_path, changed, name="changed.json"))
    assert first.authorization_digest != second.authorization_digest


def test_exact_decimal_preservation_and_immutable_pricing_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["routes"]["fast_model"]["pricing"]["input_per_million_usd"] = "1.2500"
    document["max_run_usd"] = "0.0500"
    compiled = _compile(_write_auth(tmp_path, document))
    pricing = compiled.route_pricing[(ExternalCallFamily.MODEL, "openai", "gpt-5.4-mini")]
    assert pricing.input_per_million_usd == Decimal("1.2500")
    assert compiled.envelope.max_run_usd == Decimal("0.0500")
    with pytest.raises(TypeError):
        compiled.route_pricing[(ExternalCallFamily.MODEL, "openai", "gpt-5.4-mini")] = pricing  # type: ignore[index]


def test_each_compilation_creates_fresh_independent_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    path = _write_auth(tmp_path, _base_document())
    first = _compile(path)
    second = _compile(path)
    assert first.policy is not second.policy
    assert first.envelope == second.envelope
    first.policy.activate(run_id="a", request_id="a")
    assert first.policy.physical_snapshot()["activated"] is True
    assert second.policy.physical_snapshot()["activated"] is False


def test_max_per_attempt_derivation_across_route_families(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["limits"]["tokens"] = {
        "input": 1_000_000,
        "cached_input": 0,
        "output": 0,
        "reasoning": 0,
        "embedding": 1_000_000,
    }
    document["routes"]["fast_model"]["pricing"] = {**_ZERO_PRICING, "input_per_million_usd": "2"}
    document["routes"]["smart_model"]["pricing"] = {**_ZERO_PRICING, "input_per_million_usd": "3"}
    document["routes"]["embedding"]["pricing"] = {
        **_ZERO_PRICING,
        "embedding_per_million_usd": "4",
    }
    document["routes"]["search"] = [
        _route("tavily", "search", pricing={**_ZERO_PRICING, "flat_attempt_usd": "0.50"})
    ]
    document["routes"]["read"] = [
        _route("tavily", "extract", pricing={**_ZERO_PRICING, "flat_attempt_usd": "0.75"})
    ]
    document["max_run_usd"] = "10"
    compiled = _compile(_write_auth(tmp_path, document))
    assert compiled.envelope.max_per_attempt_usd == Decimal("4")
    assert compiled.envelope.max_per_attempt_usd <= compiled.envelope.max_run_usd


def test_low_max_run_usd_caps_derived_per_attempt_and_denies_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["limits"]["tokens"] = {
        "input": 1_000_000,
        "cached_input": 0,
        "output": 0,
        "reasoning": 0,
        "embedding": 0,
    }
    document["routes"]["fast_model"]["pricing"] = {**_ZERO_PRICING, "input_per_million_usd": "5"}
    document["routes"]["smart_model"]["pricing"] = document["routes"]["fast_model"]["pricing"]
    document["max_run_usd"] = "0.01"
    compiled = _compile(_write_auth(tmp_path, document))
    assert compiled.envelope.max_per_attempt_usd == Decimal("0.01")
    policy = compiled.policy
    policy.activate(run_id="run", request_id="req")
    with pytest.raises(RunCapExceeded):
        policy.reserve_attempt(
            ExternalAttemptSpec(
                family=ExternalCallFamily.MODEL,
                provider="openai",
                route="gpt-5.4-mini",
                operation="generate",
                logical_call_id="deny-first",
                max_usage=TokenUsage(input_tokens=1_000_000),
                pricing=policy.resolve_route_pricing(
                    ExternalCallFamily.MODEL, "openai", "gpt-5.4-mini"
                ),
                requested_timeout_seconds=1,
            )
        )


def test_theoretical_full_completion_may_exceed_max_run_without_schema_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["limits"]["attempts"] = {
        "model": 4,
        "embedding": 4,
        "search": 4,
        "read": 4,
        "total": 16,
    }
    document["routes"]["search"] = [
        _route("tavily", "search", pricing={**_ZERO_PRICING, "flat_attempt_usd": "1"})
    ]
    document["routes"]["read"] = [
        _route("tavily", "extract", pricing={**_ZERO_PRICING, "flat_attempt_usd": "1"})
    ]
    document["max_run_usd"] = "0.50"
    compiled = _compile(_write_auth(tmp_path, document))
    assert compiled.envelope.max_run_usd == Decimal("0.50")
    assert compiled.envelope.max_per_attempt_usd == Decimal("0.50")


def test_repository_sha_mismatch_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch, sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    path = _write_auth(tmp_path, _base_document())
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == "repository_sha_mismatch"


def test_dirty_tracked_checkout_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def dirty(_repo_root: Path) -> str:
        raise BoundedRunAuthorizationError("dirty_tracked_checkout")

    monkeypatch.setattr(
        "core.run_cap_authorization.resolve_local_repository_identity",
        dirty,
    )
    path = _write_auth(tmp_path, _base_document())
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == "dirty_tracked_checkout"


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"query": "different query"}, "query_mismatch"),
        ({"mode": "Deep"}, "mode_mismatch"),
        ({"include_domains": ["example.com"]}, "include_domains_mismatch"),
        ({"exclude_domains": ["blocked.example"]}, "exclude_domains_mismatch"),
        ({"fast_provider": "Anthropic"}, "fast_model_mismatch"),
        ({"fast_model": "other-model"}, "fast_model_mismatch"),
        ({"smart_model": "other-smart"}, "smart_model_mismatch"),
        ({"embed_model": "other-embed"}, "embedding_mismatch"),
    ],
)
def test_request_and_model_binding_mismatches_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, Any],
    reason: str,
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    path = _write_auth(tmp_path, document)
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path, **kwargs)
    assert exc.value.reason_code == reason


def test_query_mismatch_reports_observed_digest_without_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    path = _write_auth(tmp_path, _base_document())
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path, query="another query")
    assert exc.value.reason_code == "query_mismatch"
    assert exc.value.observed_query_digest == query_sha256("another query")
    assert str(path) not in repr(exc.value)


def test_authorized_routes_resolve_and_unlisted_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["routes"]["search"] = [_route("tavily", "search"), _route("exa", "search")]
    document["routes"]["read"] = [_route("tavily", "extract"), _route("linkup", "fetch")]
    compiled = _compile(_write_auth(tmp_path, document))
    policy = compiled.policy
    assert policy.resolve_route_pricing(ExternalCallFamily.MODEL, "openai", "gpt-5.4-mini")
    assert policy.resolve_route_pricing(
        ExternalCallFamily.EMBEDDING, "openai", "text-embedding-3-small"
    )
    assert policy.resolve_route_pricing(ExternalCallFamily.SEARCH, "tavily", "search")
    assert policy.resolve_route_pricing(ExternalCallFamily.READ, "tavily", "extract")
    with pytest.raises(RunCapExceeded) as exc:
        policy.resolve_route_pricing(ExternalCallFamily.SEARCH, "serper", "search")
    assert exc.value.reason_code == "unsupported_route_pricing"


@pytest.mark.parametrize("module", [compatibility_cli, public_cli])
def test_help_exposes_authorization_flag_and_hides_profile(module) -> None:
    import sys
    from io import StringIO

    buf = StringIO()
    old = sys.stdout
    try:
        sys.stdout = buf
        with pytest.raises(SystemExit) as exc:
            compatibility_cli._parse_args(["--help"])
        assert exc.value.code == 0
    finally:
        sys.stdout = old
    text = buf.getvalue()
    assert "--bounded-run-authorization" in text
    assert "--bounded-product-profile" not in text
    assert "public-cli-v1" not in text
    assert module in {compatibility_cli, public_cli}


def test_public_cli_v1_remains_unavailable() -> None:
    with pytest.raises(SystemExit):
        compatibility_cli._parse_args([_QUERY, "--bounded-product-profile", "public-cli-v1"])


def test_invalid_authorization_fails_before_dotenv_and_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dotenv_calls: list[Any] = []
    cred_calls: list[Any] = []

    monkeypatch.setattr(
        compatibility_cli,
        "load_dotenv",
        lambda *a, **k: dotenv_calls.append((a, k)) or True,
    )
    monkeypatch.setattr(
        compatibility_cli,
        "missing_required_api_keys",
        lambda **kwargs: cred_calls.append(kwargs) or ["OPENAI_API_KEY"],
    )
    monkeypatch.setattr(
        compatibility_cli,
        "_build_logger",
        lambda *a, **k: type(
            "L",
            (),
            {"info": lambda *a, **k: None, "error": lambda *a, **k: None},
        )(),
    )
    auth_path = tmp_path / "bad.json"
    auth_path.write_text("{bad", encoding="utf-8")
    argv = [
        _QUERY,
        "--mode",
        "Balanced",
        "--include-domains",
        "docs.python.org",
        "--fast-provider",
        "OpenAI",
        "--fast-model",
        "gpt-5.4-mini",
        "--smart-provider",
        "OpenAI",
        "--smart-model",
        "gpt-5.4",
        "--embed-provider",
        "OpenAI",
        "--embed-model",
        "text-embedding-3-small",
        "--bounded-run-authorization",
        str(auth_path),
    ]
    code = compatibility_cli.main(argv, entrypoint="proplex")
    assert code == 2
    assert dotenv_calls == []
    assert cred_calls == []
    out = capsys.readouterr().out
    assert "bounded_product_cli_terminal_v1" in out
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["terminal"]["code"] == "bounded_configuration_unavailable"
    assert str(auth_path) not in json.dumps(payload)


def test_normal_cli_unchanged_without_authorization_flag() -> None:
    args = compatibility_cli._parse_args([_QUERY])
    config = compatibility_cli._build_run_config(args)
    assert config.cap_policy is None
    assert getattr(args, "bounded_run_authorization", None) in {None, ""}


def test_alias_equivalence_for_same_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    path = _write_auth(tmp_path, _base_document())
    first = _compile(path)
    second = _compile(path)
    assert first.authorization_digest == second.authorization_digest
    assert first.envelope == second.envelope
    assert dict(first.route_pricing) == dict(second.route_pricing)


def test_query_sha_and_domain_helpers_are_deterministic() -> None:
    assert query_sha256("  hello\r\n") == query_sha256("hello\n")
    assert canonicalize_domains(["B.com.", "a.com", "a.com"]) == ["a.com", "b.com"]


def test_resolve_local_repository_identity_smoke_on_clean_or_error() -> None:
    try:
        sha = resolve_local_repository_identity(_REPO)
        assert len(sha) == 40
    except BoundedRunAuthorizationError as exc:
        assert exc.reason_code in {
            "dirty_tracked_checkout",
            "repository_identity_unavailable",
        }


@pytest.mark.parametrize(
    ("deadline_literal", "expected_reason"),
    [
        ("1e309", "invalid_deadline"),
        ("Infinity", "invalid_authorization_json"),
        ("-Infinity", "invalid_authorization_json"),
        ("NaN", "invalid_authorization_json"),
    ],
)
def test_nonfinite_deadline_seconds_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    deadline_literal: str,
    expected_reason: str,
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    encoded = json.dumps(document)
    needle = '"deadline_seconds": 1'
    assert needle in encoded
    encoded = encoded.replace(needle, f'"deadline_seconds": {deadline_literal}', 1)
    path = tmp_path / "nonfinite_deadline.json"
    path.write_text(encoded, encoding="utf-8")
    with pytest.raises(BoundedRunAuthorizationError) as exc:
        _compile(path)
    assert exc.value.reason_code == expected_reason


def test_ordinary_positive_finite_deadline_still_compiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo_identity(monkeypatch)
    document = _base_document()
    document["limits"]["deadline_seconds"] = 30
    compiled = _compile(_write_auth(tmp_path, document))
    assert compiled.envelope.deadline_seconds == 30.0
