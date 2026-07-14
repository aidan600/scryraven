from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from core.validation_observability import build_validation_observability
from core.validation_profiles import (
    AG_LIVE_S1_BLOCK_A_OPERATIONAL_BUDGET,
    AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET,
    AG_LIVE_S1_FIXED_QUERIES,
    AG_LIVE_S1_PRODUCT_CONVERGENCE,
    get_validation_profile,
)
from scripts import ag_live_bound_01_bounded_product_runner as bounded_runner
from scripts import ag_live_bound_01_support as bound_support
from scripts import ag_live_s1_product_convergence_01 as campaign
from scripts import ag_live_s1_product_convergence_01_support as support


def _nonsecret_configuration() -> dict[str, Any]:
    return {
        "fast_provider": "OpenAI",
        "fast_model": "gpt-5.4-mini",
        "smart_provider": "OpenAI",
        "smart_model": "gpt-5.4",
        "embed_provider": "OpenAI",
        "embed_model": "text-embedding-3-small",
        "active_search_providers": ["tavily", "linkup", "exa"],
        "credential_presence": {
            "OPENAI_API_KEY": True,
            "OPENROUTER_API_KEY": True,
            "TAVILY_API_KEY": True,
            "LINKUP_API_KEY": True,
            "EXA_API_KEY": True,
        },
        "credential_values_retained": False,
    }


def _initialize_temp_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(
        campaign,
        "_git",
        lambda *args: (
            campaign.EXPECTED_BRANCH
            if args[:2] == ("branch", "--show-current")
            else campaign.EXPECTED_STARTING_SHA
        ),
    )
    monkeypatch.setattr(
        campaign,
        "_resolve_nonsecret_product_configuration",
        _nonsecret_configuration,
    )
    root = tmp_path / support.CAMPAIGN_ROOT_RELATIVE
    assert campaign.initialize_campaign(root) == 0
    return root


def _campaign_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> support.CampaignBudgetGuard:
    root = tmp_path / "campaign"
    config = campaign._campaign_config(
        _nonsecret_configuration(),
        created_at="2026-07-14T00:00:00+00:00",
    )
    support.write_sanitized_json(root / support.CONFIG_NAME, config, root=root)
    support.write_sanitized_json(
        root / support.LEDGER_NAME,
        support.initial_budget_ledger(config),
        root=root,
    )
    monkeypatch.setattr(
        support,
        "validate_campaign_root",
        lambda _repo_root, candidate: candidate.resolve(),
    )
    return support.CampaignBudgetGuard(
        config_path=root / support.CONFIG_NAME,
        query_id="A_NO_QUANT",
        attempt=1,
        block="A",
    )


def test_profile_locks_exact_queries_and_operational_budgets() -> None:
    profile = get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE)
    assert profile.fixed_queries == AG_LIVE_S1_FIXED_QUERIES
    assert list(profile.fixed_query_map()) == [
        "A_NO_QUANT",
        "B_COMPONENT_CALC",
        "C_SYNTHESIS_CALC",
        "D_CONVERSION_NEGATIVE",
    ]
    assert all(len(value) == 64 for value in profile.fixed_query_digests().values())
    assert profile.required_include_domains == ("nasa.gov",)
    assert AG_LIVE_S1_BLOCK_A_OPERATIONAL_BUDGET.generative_plus_embedding_calls == 90
    assert AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET.full_scryraven_runs == 10
    assert AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET.campaign_added_retries == 0

    query_id, query = AG_LIVE_S1_FIXED_QUERIES[0]
    assert bound_support.validate_query_lock(
        query,
        approved_backup_query=False,
        profile_name=profile.name,
        requested_query_id=query_id,
    ) == query_id
    with pytest.raises(bound_support.AgLiveBoundPreflightError, match="query ID"):
        bound_support.validate_query_lock(
            query,
            approved_backup_query=False,
            profile_name=profile.name,
            requested_query_id="B_COMPONENT_CALC",
        )


def test_offline_init_writes_only_marked_confined_campaign_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _initialize_temp_campaign(tmp_path, monkeypatch)

    expected = {
        support.CONFIG_NAME,
        support.MANIFEST_NAME,
        support.LEDGER_NAME,
        "failure_matrix.json",
        "repair_matrix.json",
        "manual_source_checks.json",
        "campaign_summary.json",
        "review.md",
    }
    assert expected <= {path.name for path in root.iterdir()}
    assert len(list((root / "runs").glob("run_*_01.sanitized.json"))) == 4
    for packet_path in root.rglob("*.json"):
        packet = support.read_sanitized_json(packet_path, root=root)
        assert packet["campaign_marker"] == support.CAMPAIGN_MARKER
    assert (root / "review.md").read_text(encoding="utf-8").startswith(
        support.CAMPAIGN_MARKER
    )
    manifest = support.read_sanitized_json(root / support.MANIFEST_NAME, root=root)
    latest = manifest["instruction_amendments"][-1]
    assert latest["interruption_class"] == "codex_host_capacity_interruption"
    assert latest["codex_host_model_identity"] == "unavailable"
    assert latest["scryraven_product_failure"] is False
    assert latest["live_campaign_budget_consumed"] is False
    assert latest["campaign_added_retries"] == 0
    ledger = support.read_sanitized_json(root / support.LEDGER_NAME, root=root)
    assert ledger["consumed_combined"]["full_scryraven_runs"] == 0
    assert ledger["live_contact_started_at"] is None


def test_offline_state_refresh_is_idempotent_and_observational(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _initialize_temp_campaign(tmp_path, monkeypatch)
    config_path = root / support.CONFIG_NAME
    assert campaign.refresh_offline_campaign_state(config_path) == 0
    assert campaign.refresh_offline_campaign_state(config_path) == 0

    config = support.read_sanitized_json(config_path, root=root)
    observation = config["repository_pricing_observation"]
    assert observation["pricing_status"] == "pricing_known"
    assert all(observation["identity_availability"].values())
    assert observation["actual_provider_cost_not_observed"] is True
    ledger = support.read_sanitized_json(root / support.LEDGER_NAME, root=root)
    assert ledger["observational_repository_cost_estimate"] == {
        "estimate_kind": "observational_repository_estimate",
        "pricing_status": "pricing_known",
        "usd": 0.0,
        "pricing_unknown_identities": [],
    }
    manifest = support.read_sanitized_json(root / support.MANIFEST_NAME, root=root)
    refreshes = [
        item
        for item in manifest["instruction_amendments"]
        if item.get("name") == "offline_gate0_observational_schema_refresh"
    ]
    assert len(refreshes) == 1
    assert refreshes[0]["live_campaign_budget_consumed"] is False


def test_campaign_sanitizer_rejects_unsafe_or_unconfined_material(
    tmp_path: Path,
) -> None:
    with pytest.raises(support.CampaignSafetyError, match="forbidden campaign key"):
        support.validate_sanitized_value({"authorization": "redacted"})
    with pytest.raises(support.CampaignSafetyError, match="forbidden campaign sentinel"):
        support.validate_sanitized_value({"detail": "Bearer synthetic-secret"})
    with pytest.raises(support.CampaignSafetyError, match="exceeds bound"):
        support.validate_sanitized_value({"detail": "x" * 1_201})
    with pytest.raises(support.CampaignSafetyError, match="escaped"):
        support.validate_confined_path(tmp_path / "root", tmp_path / "outside.json")


def test_guard_fails_closed_before_per_run_model_cap_is_exceeded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _campaign_guard(tmp_path, monkeypatch)
    guard.begin_run()
    for index in range(15):
        guard.before_model_call(
            model=f"fixture-model-{index}",
            provider="FixtureProvider",
            embedding=False,
            product_phase="fixture_model",
        )
    with pytest.raises(support.CampaignSafetyError, match="per-run model"):
        guard.before_model_call(
            model="blocked-model",
            provider="FixtureProvider",
            embedding=False,
            product_phase="fixture_model",
        )
    snapshot = guard.snapshot()
    assert snapshot["run"]["generative_calls"] == 15
    assert snapshot["consumed_combined"]["generative_plus_embedding_calls"] == 15


def test_aggregate_block_combined_token_and_elapsed_caps_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _campaign_guard(tmp_path, monkeypatch)
    ledger = support.read_sanitized_json(guard.ledger_path, root=guard.root)
    ledger["consumed_by_block"]["B"]["independent_manual_source_checks"] = 2
    ledger["consumed_combined"]["independent_manual_source_checks"] = 2
    support.write_sanitized_json(guard.ledger_path, ledger, root=guard.root)
    with pytest.raises(support.CampaignSafetyError, match="Block B"):
        support.consume_campaign_counters(
            config_path=guard.config_path,
            block="B",
            increments={"independent_manual_source_checks": 1},
            event_id="manual:B:overflow",
        )

    combined_guard = _campaign_guard(tmp_path / "combined", monkeypatch)
    ledger = support.read_sanitized_json(
        combined_guard.ledger_path,
        root=combined_guard.root,
    )
    ledger["consumed_combined"]["independent_manual_source_checks"] = 6
    support.write_sanitized_json(
        combined_guard.ledger_path,
        ledger,
        root=combined_guard.root,
    )
    with pytest.raises(support.CampaignSafetyError, match="combined"):
        support.consume_campaign_counters(
            config_path=combined_guard.config_path,
            block="A",
            increments={"independent_manual_source_checks": 1},
            event_id="manual:combined:overflow",
        )

    token_guard = _campaign_guard(tmp_path / "tokens", monkeypatch)
    token_guard.begin_run()
    token_guard.record_tokens(
        input_tokens=225_000,
        output_tokens=0,
        embedding=False,
    )
    with pytest.raises(support.CampaignSafetyError, match="outbound work is blocked"):
        token_guard.before_model_call(
            model="blocked-after-observed-token-ceiling",
            provider="FixtureProvider",
            embedding=False,
            product_phase="fixture_model",
        )

    elapsed_guard = _campaign_guard(tmp_path / "elapsed", monkeypatch)
    ledger = support.read_sanitized_json(
        elapsed_guard.ledger_path,
        root=elapsed_guard.root,
    )
    ledger["live_contact_started_at"] = "2000-01-01T00:00:00+00:00"
    ledger["live_contact_started_at_by_block"]["A"] = (
        "2000-01-01T00:00:00+00:00"
    )
    support.write_sanitized_json(
        elapsed_guard.ledger_path,
        ledger,
        root=elapsed_guard.root,
    )
    with pytest.raises(support.CampaignSafetyError, match="elapsed-time cap"):
        elapsed_guard.begin_run()


def test_unknown_pricing_is_telemetry_not_free_or_a_stop_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _campaign_guard(tmp_path, monkeypatch)
    guard.begin_run()
    accumulator = support.CampaignCostAccumulator(guard)
    accumulator.record_model_call(
        phase="fixture",
        model="future-model-without-repository-pricing",
        input_tokens=10,
        output_tokens=5,
    )

    estimate = guard.snapshot()["observational_repository_cost_estimate"]
    assert estimate == {
        "estimate_kind": "observational_repository_estimate",
        "pricing_status": "pricing_unknown",
        "usd": 0.0,
        "pricing_unknown_identities": [
            "future-model-without-repository-pricing"
        ],
    }
    assert guard.config["monetary_stop_authority"] is False
    assert guard.snapshot()["actual_provider_cost_not_observed"] is True


def test_product_cap_reconciliation_and_s1_source_custody_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _campaign_guard(tmp_path, monkeypatch)
    guard.begin_run()
    cap_policy = get_validation_profile(
        AG_LIVE_S1_PRODUCT_CONVERGENCE
    ).cap_policy.to_run_cap_policy()
    cap_policy.mark_fetch_read_operation()
    guard.reconcile_product_cap_observations(cap_policy)
    snapshot = guard.snapshot()
    assert snapshot["run"]["retrieval_fetch_read_operations"] == 1
    assert snapshot["consumed_combined"]["retrieval_fetch_read_operations"] == 1
    assert snapshot["run"]["product_cap_observations"][
        "fetch_read_operations"
    ] == 1

    profile = get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE)
    observability = build_validation_observability(
        validation_profile=profile,
        preflight_context=SimpleNamespace(profile_name=profile.name),
        run_config=None,
        outcome=SimpleNamespace(
            execution_trace={},
            top_passages=[],
            seen_urls=[],
            report="",
        ),
        cap_policy=cap_policy,
    )
    custody = observability["source_custody_summary"]
    assert custody["source_custody_expected"] is True
    assert custody["fetch_read_required"] is True


def test_post_wave_reconciliation_uses_sanitized_packets_only_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _initialize_temp_campaign(tmp_path, monkeypatch)
    monkeypatch.setattr(
        support,
        "validate_campaign_root",
        lambda _repo_root, candidate: candidate.resolve(),
    )
    config_path = root / support.CONFIG_NAME
    guard = support.CampaignBudgetGuard(
        config_path=config_path,
        query_id="A_NO_QUANT",
        attempt=1,
        block="A",
    )
    guard.begin_run()
    packet_path = root / "runs" / "run_A_NO_QUANT_01.sanitized.json"
    support.write_sanitized_json(
        packet_path,
        {
            "campaign_schema": support.CAMPAIGN_SCHEMA,
            "query_id": "A_NO_QUANT",
            "attempt": 1,
            "caps_observed": {
                "search_dispatches": 1,
                "fetch_read_operations": 1,
                "author_model_calls": 1,
                "smart_search_judgment_model_calls": 0,
                "retries": 0,
            },
            "validation_observability": {
                "source_custody_summary": {
                    "source_custody_expected": False,
                    "fetch_read_required": False,
                    "fetch_read_operations": 1,
                }
            },
        },
        root=root,
    )
    manifest = support.read_sanitized_json(root / support.MANIFEST_NAME, root=root)
    manifest["initial_wave_complete"] = True
    support.write_sanitized_json(
        root / support.MANIFEST_NAME,
        manifest,
        root=root,
    )

    assert campaign.reconcile_sanitized_campaign_observability(config_path) == 0
    assert campaign.reconcile_sanitized_campaign_observability(config_path) == 0

    ledger = support.read_sanitized_json(root / support.LEDGER_NAME, root=root)
    assert ledger["consumed_combined"]["retrieval_fetch_read_operations"] == 1
    assert ledger["consumed_combined"]["root_cause_repair_clusters"] == 1
    packet = support.read_sanitized_json(packet_path, root=root)
    custody = packet["validation_observability"]["source_custody_summary"]
    assert custody["source_custody_expected"] is True
    assert custody["fetch_read_required"] is True
    assert custody["profile_policy_reconciled"] is True
    repairs = support.read_sanitized_json(root / "repair_matrix.json", root=root)
    assert len(repairs["entries"]) == 1
    assert repairs["entries"][0]["status"] == "completed_offline"


def test_unknown_query_broker_alternate_and_retry_postures_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _campaign_guard(tmp_path, monkeypatch)
    with pytest.raises(support.CampaignSafetyError, match="unknown query ID"):
        support.CampaignBudgetGuard(
            config_path=guard.config_path,
            query_id="UNKNOWN_QUERY",
            attempt=1,
            block="A",
        )

    for field, value, message in (
        ("broker_authorized", True, "broker posture"),
        ("alternate_smart_model", "alternate-model", "identity must remain null"),
        ("campaign_added_retries", 1, "retries must remain zero"),
    ):
        config = support.read_sanitized_json(guard.config_path, root=guard.root)
        config[field] = value
        support.write_sanitized_json(guard.config_path, config, root=guard.root)
        with pytest.raises(support.CampaignSafetyError, match=message):
            support.CampaignBudgetGuard(
                config_path=guard.config_path,
                query_id="A_NO_QUANT",
                attempt=1,
                block="A",
            )
        config[field] = (
            False
            if field == "broker_authorized"
            else 0
            if field == "campaign_added_retries"
            else None
        )
        support.write_sanitized_json(guard.config_path, config, root=guard.root)


def test_campaign_runner_composes_s1_and_calls_pipeline_once_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _campaign_guard(tmp_path, monkeypatch)
    query_id, query = AG_LIVE_S1_FIXED_QUERIES[0]
    output_path = guard.root / "runs" / "run_A_NO_QUANT_01.sanitized.json"
    model_config = _nonsecret_configuration()
    pipeline_calls = 0

    monkeypatch.setattr(bound_support, "is_allowed_output_path", lambda *_args: True)
    monkeypatch.setattr(bounded_runner, "_load_live_environment", lambda: None)
    monkeypatch.setattr(bounded_runner, "_validate_live_model_keys", lambda: None)
    monkeypatch.setattr(
        bounded_runner,
        "_validate_campaign_credential_presence",
        lambda _guard: None,
    )
    monkeypatch.setattr(
        bounded_runner,
        "_live_model_config",
        lambda: {
            key: model_config[key]
            for key in (
                "fast_provider",
                "fast_model",
                "smart_provider",
                "smart_model",
                "embed_provider",
                "embed_model",
            )
        }
        | {"local_url": "http://localhost:1234/v1"},
    )

    def fail_pipeline_once(*_args: Any, **_kwargs: Any) -> None:
        nonlocal pipeline_calls
        pipeline_calls += 1
        from core.pipeline_orchestrator import PipelineError

        raise PipelineError("synthetic offline pipeline stop")

    monkeypatch.setattr(
        bounded_runner,
        "_call_run_pipeline_once",
        fail_pipeline_once,
    )
    caps = get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE).cap_policy
    result = bounded_runner.main(
        [
            "--profile",
            AG_LIVE_S1_PRODUCT_CONVERGENCE,
            "--query-id",
            query_id,
            "--query",
            query,
            "--mode",
            "Balanced",
            "--include-domains",
            "nasa.gov",
            "--output",
            str(output_path),
            "--max-scryraven-runs",
            str(caps.max_scryraven_runs),
            "--max-search-dispatches",
            str(caps.max_search_dispatches),
            "--max-fetch-read-operations",
            str(caps.max_fetch_read_operations),
            "--max-author-model-calls",
            str(caps.max_author_model_calls),
            "--max-smart-search-judgment-model-calls",
            str(caps.max_smart_search_judgment_model_calls),
            "--max-independent-manual-source-checks",
            str(caps.max_independent_manual_source_checks),
            "--max-retries",
            str(caps.max_retries),
            "--campaign-config",
            str(guard.config_path),
            "--campaign-block",
            "A",
            "--campaign-attempt",
            "1",
            "--confirm-live-product-run",
        ]
    )

    assert result == 2
    assert pipeline_calls == 1
    packet = support.read_sanitized_json(output_path, root=guard.root)
    assert packet["run_pipeline_call_count"] == 1
    assert packet["s1_product_equivalence"] == {
        "classification": "UPGRADE",
        "runtime_consumer": "run_pipeline",
        "composition_owner": "compose_quantitative_specialist_product_deps",
        "capability_count": 1,
        "capability_ids": ["specialist.source_bound_calculation"],
        "specialist_work_item_limit": 1,
        "parallelism": False,
        "recursion": False,
        "registry_duplicated": False,
        "execution_policy_duplicated": False,
    }
    assert packet["campaign_budget"]["consumed_combined"][
        "full_scryraven_runs"
    ] == 1
    assert packet["product_provider_failure"] is None


class _SyntheticResponse:
    status_code = 429
    headers = {
        "retry-after": "17",
        "x-ratelimit-limit-requests": "500",
        "x-ratelimit-remaining-requests": "0",
        "x-ratelimit-reset-requests": "17s",
        "authorization": "Bearer should-never-be-read",
        "x-private-provider-header": "private-value",
    }
    body = {"request_payload": "must-not-be-read"}


class _SyntheticRateLimitError(Exception):
    status_code = 429
    code = "rate_limit_exceeded"
    response = _SyntheticResponse()


@dataclass(frozen=True)
class _FixtureDeps:
    ask_model: Callable[..., Any]
    embed_texts: Callable[..., Any]
    process_search_queries: Callable[..., Any]
    fetch_linkup_precision_block: Callable[..., Any]
    strict_one_shot_smart_model_transport: Callable[..., Any] | None = None
    specialist_capability_registry: Any = None
    specialist_execution_policy: Any = None


def test_accounted_adapter_records_allowlisted_rate_limit_without_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = _campaign_guard(tmp_path, monkeypatch)
    guard.begin_run()
    calls = 0

    def fail_once(*_args: Any, **_kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        raise _SyntheticRateLimitError(
            "OPENAI_API_KEY=sk-synthetic raw provider response must not survive"
        )

    deps = _FixtureDeps(
        ask_model=fail_once,
        embed_texts=lambda *_args, **_kwargs: [],
        process_search_queries=lambda *_args, **_kwargs: [],
        fetch_linkup_precision_block=lambda *_args, **_kwargs: None,
        specialist_capability_registry=SimpleNamespace(
            projection=lambda: {
                "capability_count": 1,
                "capability_descriptors": [
                    {"capability_id": "specialist.source_bound_calculation"}
                ],
            }
        ),
        specialist_execution_policy=SimpleNamespace(
            projection=lambda: {
                "specialist_work_item_limit": 1,
                "parallelism": False,
                "recursion": False,
            }
        ),
    )
    run_config = SimpleNamespace(
        fast_provider="OpenAI",
        fast_model="gpt-5.4-mini",
        smart_provider="OpenAI",
        smart_model="gpt-5.4",
        embed_provider="OpenAI",
        embed_model="text-embedding-3-small",
        local_url="",
        or_api_key="",
    )
    accounted = support.compose_campaign_accounted_deps(
        deps,
        guard=guard,
        run_config=run_config,
    )

    with pytest.raises(_SyntheticRateLimitError):
        accounted.ask_model(
            "transient request input",
            "transient system input",
            provider="OpenAI",
            model="gpt-5.4-mini",
            cost_phase="query_planning",
        )

    assert calls == 1
    failure = guard.snapshot()["run"]["product_provider_failure"]
    assert failure["classification"] == support.PROVIDER_RATE_LIMIT
    assert failure["product_phase"] == "query_planning"
    assert failure["provider_identity"] == "OpenAI"
    assert failure["requested_model_identity"] == "gpt-5.4-mini"
    assert failure["http_status"] == 429
    assert failure["provider_error_code"] == "rate_limit_exceeded"
    assert failure["retry_after"] == "17"
    assert failure["x_ratelimit"] == {
        "x-ratelimit-limit-requests": "500",
        "x-ratelimit-remaining-requests": "0",
        "x-ratelimit-reset-requests": "17s",
    }
    assert failure["request_submitted"] is True
    rendered = json.dumps(failure, sort_keys=True)
    for forbidden in (
        "authorization",
        "should-never-be-read",
        "request_payload",
        "private-value",
        "sk-synthetic",
        "transient request input",
    ):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("exc", "expected"),
    (
        (_SyntheticRateLimitError("synthetic"), support.PROVIDER_RATE_LIMIT),
        (
            type(
                "SyntheticCapacityError",
                (Exception,),
                {"status_code": 503},
            )("synthetic"),
            support.PROVIDER_CAPACITY,
        ),
        (
            type(
                "SyntheticQuotaError",
                (Exception,),
                {"status_code": 429, "code": "insufficient_quota"},
            )("synthetic"),
            support.PROVIDER_QUOTA_OR_USAGE_LIMIT,
        ),
        (
            type(
                "SyntheticAuthenticationError",
                (Exception,),
                {"status_code": 401},
            )("synthetic"),
            support.PROVIDER_AUTHENTICATION_FAILURE,
        ),
        (TimeoutError("synthetic"), support.PROVIDER_TRANSPORT_FAILURE),
        (ValueError("synthetic"), support.UNKNOWN_PROVIDER_FAILURE),
    ),
)
def test_provider_failure_taxonomy(exc: BaseException, expected: str) -> None:
    packet = support.build_sanitized_product_provider_failure(
        exc=exc,
        product_phase="fixture_phase",
        provider_identity="FixtureProvider",
        requested_model_identity="fixture-model",
        request_submitted=None,
        campaign_counters_consumed={"combined_consumed": {}},
    )
    assert packet["classification"] == expected
    assert set(packet) == {
        "classification",
        "product_phase",
        "provider_identity",
        "requested_model_identity",
        "exception_class",
        "http_status",
        "provider_error_code",
        "retry_after",
        "x_ratelimit",
        "sanitized_error_message",
        "request_submitted",
        "campaign_counters_consumed",
    }


def test_product_equivalence_summary_has_one_shared_capability_and_policy() -> None:
    deps = SimpleNamespace(
        specialist_capability_registry=SimpleNamespace(
            projection=lambda: {
                "capability_count": 1,
                "capability_descriptors": [
                    {"capability_id": "specialist.source_bound_calculation"}
                ],
            }
        ),
        specialist_execution_policy=SimpleNamespace(
            projection=lambda: {
                "specialist_work_item_limit": 1,
                "parallelism": False,
                "recursion": False,
            }
        ),
    )
    summary = support.product_equivalence_summary(deps)
    assert summary["runtime_consumer"] == "run_pipeline"
    assert summary["capability_count"] == 1
    assert summary["capability_ids"] == ["specialist.source_bound_calculation"]
    assert summary["specialist_work_item_limit"] == 1
    assert summary["registry_duplicated"] is False
    assert summary["execution_policy_duplicated"] is False


def test_runner_arguments_have_no_oracle_broker_or_alternate_input_surface(
    tmp_path: Path,
) -> None:
    query_id, query = AG_LIVE_S1_FIXED_QUERIES[0]
    args = campaign._runner_args(
        config_path=tmp_path / support.CONFIG_NAME,
        query_id=query_id,
        query=query,
        attempt=1,
        block="A",
    )
    rendered = " ".join(args).casefold()
    for forbidden in ("oracle", "broker", "openrouter", "alternate"):
        assert forbidden not in rendered


def test_product_failure_stops_wave_and_preserves_remaining_queries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _initialize_temp_campaign(tmp_path, monkeypatch)
    called: list[str] = []

    def exposed_rate_limit(**kwargs: Any) -> tuple[int, dict[str, Any]]:
        called.append(str(kwargs["query_id"]))
        return 2, {
            "success_classification": "pipeline_failure",
            "product_provider_failure": {
                "classification": support.PROVIDER_RATE_LIMIT
            },
        }

    monkeypatch.setattr(campaign, "_execute_one", exposed_rate_limit)
    result = campaign.run_block(
        block="A",
        config_path=root / support.CONFIG_NAME,
        rerun_query_id=None,
        control_query_id=None,
    )

    assert result == 2
    assert called == ["A_NO_QUANT"]
    manifest = support.read_sanitized_json(root / support.MANIFEST_NAME, root=root)
    assert manifest["attempts"] == {
        "A_NO_QUANT": 0,
        "B_COMPONENT_CALC": 0,
        "C_SYNTHESIS_CALC": 0,
        "D_CONVERSION_NEGATIVE": 0,
    }
