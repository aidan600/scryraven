"""Thin coordinator for AG-LIVE-S1-PRODUCT-CONVERGENCE-01.

``--init`` is offline. Live execution is delegated one query at a time to the
existing bounded ordinary-product runner; this coordinator has no semantic,
acquisition, calculation, FAP, or Author implementation.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cost_accounting import (  # noqa: E402
    MODEL_PRICING_USD_PER_1M,
    PROVIDER_PRICING_USD_PER_CALL,
)
from core.validation_profiles import (  # noqa: E402
    AG_LIVE_S1_BLOCK_A_OPERATIONAL_BUDGET,
    AG_LIVE_S1_BLOCK_B_OPERATIONAL_BUDGET,
    AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET,
    AG_LIVE_S1_FIXED_QUERIES,
    AG_LIVE_S1_PER_RUN_CAP_POLICY,
    AG_LIVE_S1_PRODUCT_CONVERGENCE,
    get_validation_profile,
)
from scripts.ag_live_s1_product_convergence_01_support import (  # noqa: E402
    CAMPAIGN_MARKER,
    CAMPAIGN_ROOT_RELATIVE,
    CAMPAIGN_SCHEMA,
    CONFIG_NAME,
    LEDGER_NAME,
    MANIFEST_NAME,
    CampaignBudgetGuard,
    CampaignSafetyError,
    consume_campaign_counters,
    initial_budget_ledger,
    read_sanitized_json,
    utc_now,
    validate_campaign_root,
    validate_sanitized_value,
    write_sanitized_json,
)

PHASE_ID = "AG-LIVE-S1-PRODUCT-CONVERGENCE-01"
EXPECTED_STARTING_SHA = "10683322b1e115410ba082faf89caa494de1eb55"
EXPECTED_BRANCH = "codex/live-s1-product-convergence-01"
RUNNER_RELATIVE = Path("scripts/ag_live_bound_01_bounded_product_runner.py")
QUERY_ORDER = tuple(query_id for query_id, _query in AG_LIVE_S1_FIXED_QUERIES)
EXPECTED_DISPOSITIONS = {
    "A_NO_QUANT": "ordinary final output with no Specialist work",
    "B_COMPONENT_CALC": "one component-origin difference consumed by component D-prime",
    "C_SYNTHESIS_CALC": "one synthesis-origin difference with two-hop binding",
    "D_CONVERSION_NEGATIVE": "no unsupported converted mile result presented as supported",
}
WAVE_1_EXTENSION_QUERY_ID = "D_CONVERSION_NEGATIVE"
WAVE_1_EXTENSION_ATTEMPT = 2
WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING = 375_000
WAVE_1_EXTENSION_PREVIOUS_TOKEN_TOTAL = 254_911
WAVE_1_EXTENSION_ADDITIONAL_TOKEN_LIMIT = 120_089
WAVE_1_EXTENSION_COMBINED_TOKEN_CEILING = 400_000
WAVE_1_EXTENSION_ATTEMPT_REASON = "operator_authorized_wave_1_completion"
WAVE_1_EXTENSION_AUTHORITY = "explicit_operator_budget_extension"


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise CampaignSafetyError(
            "git baseline inspection failed: "
            + (completed.stderr.strip() or completed.stdout.strip())[:500]
        )
    return completed.stdout.strip()


def _resolve_nonsecret_product_configuration() -> dict[str, Any]:
    from scripts.ag_live_bound_01_bounded_product_runner import (
        _live_model_config,
        _load_live_environment,
    )

    _load_live_environment()
    model_config = _live_model_config()
    credential_names = (
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "TAVILY_API_KEY",
        "LINKUP_API_KEY",
        "EXA_API_KEY",
    )
    presence = {name: bool(os.getenv(name)) for name in credential_names}
    active_search_providers = ["tavily"]
    for provider, credential_name in (
        ("linkup", "LINKUP_API_KEY"),
        ("exa", "EXA_API_KEY"),
    ):
        if presence[credential_name]:
            active_search_providers.append(provider)
    return {
        key: model_config[key]
        for key in (
            "fast_provider",
            "fast_model",
            "smart_provider",
            "smart_model",
            "embed_provider",
            "embed_model",
        )
    } | {
        "active_search_providers": active_search_providers,
        "credential_presence": presence,
        "credential_values_retained": False,
    }


def _query_packets() -> list[dict[str, Any]]:
    profile = get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE)
    digests = profile.fixed_query_digests()
    return [
        {
            "query_id": query_id,
            "query": query,
            "query_digest": digests[query_id],
            "expected_disposition": EXPECTED_DISPOSITIONS[query_id],
        }
        for query_id, query in AG_LIVE_S1_FIXED_QUERIES
    ]


def _per_run_operational_budget() -> dict[str, int]:
    caps = AG_LIVE_S1_PER_RUN_CAP_POLICY
    return {
        "full_scryraven_runs": 1,
        "search_dispatches": caps.max_search_dispatches,
        "external_provider_search_calls": 5,
        "retrieval_fetch_read_operations": caps.max_fetch_read_operations,
        "author_model_calls": caps.max_author_model_calls,
        "smart_search_judgment_model_calls": (
            caps.max_smart_search_judgment_model_calls
        ),
        "generative_plus_embedding_calls": 15,
        "campaign_added_retries": caps.max_retries,
    }


def _repository_pricing_observation(
    nonsecret_config: dict[str, Any],
) -> dict[str, Any]:
    pricing_identities = [
        str(nonsecret_config[field])
        for field in ("fast_model", "smart_model", "embed_model")
    ]
    pricing_identities.extend(
        str(item) for item in nonsecret_config.get("active_search_providers", ())
    )
    pricing_known = {
        identity: (
            identity.casefold() in MODEL_PRICING_USD_PER_1M
            or identity.casefold() in PROVIDER_PRICING_USD_PER_CALL
        )
        for identity in pricing_identities
    }
    pricing_unknown = [
        identity for identity, known in pricing_known.items() if not known
    ]
    return {
        "identity_availability": pricing_known,
        "pricing_status": "pricing_unknown" if pricing_unknown else "pricing_known",
        "pricing_unknown_identities": pricing_unknown,
        "actual_provider_cost_not_observed": True,
    }


def _campaign_config(nonsecret_config: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    profile = get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE)
    return {
        "campaign_schema": CAMPAIGN_SCHEMA,
        "phase_id": PHASE_ID,
        "created_at": created_at,
        "starting_main_sha": EXPECTED_STARTING_SHA,
        "branch": EXPECTED_BRANCH,
        "mode": "Balanced",
        "domain_allowlist": ["nasa.gov"],
        "fixed_queries": _query_packets(),
        "query_order": list(QUERY_ORDER),
        "query_strings_and_digests_immutable": True,
        "sanitized_packet_schema": profile.packet_schema,
        "source_custody_requirements": (
            profile.source_custody_policy.as_requested_dict()
            if profile.source_custody_policy is not None
            else None
        ),
        "per_run_cap_policy": AG_LIVE_S1_PER_RUN_CAP_POLICY.as_requested_dict(),
        "per_run_hard_operational_budget": _per_run_operational_budget(),
        "hard_operational_budget": {
            "block_a": AG_LIVE_S1_BLOCK_A_OPERATIONAL_BUDGET.as_dict(),
            "block_b": AG_LIVE_S1_BLOCK_B_OPERATIONAL_BUDGET.as_dict(),
            "combined": AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET.as_dict(),
        },
        "observed_token_accounting": "post_response_prospective_stop",
        "cost_accounting": "observational_repository_estimate",
        "actual_provider_cost_not_observed": True,
        "monetary_stop_authority": False,
        "pricing_unknown_posture": "pricing_unknown",
        "repository_pricing_observation": _repository_pricing_observation(
            nonsecret_config
        ),
        "ordinary_resolved_product_configuration": nonsecret_config,
        "ordinary_configuration_locked_at_campaign_start": True,
        "alternate_smart_provider": None,
        "alternate_smart_model": None,
        "alternate_model_comparison": "alternate_model_comparison_not_run",
        "alternate_model_comparison_reason": (
            "separately scoped future portability checkpoint"
        ),
        "broker_authorized": False,
        "broker_used": False,
        "campaign_added_retries": 0,
        "manual_operator_oracles_enter_product_inputs": False,
        "retention_posture": "sanitized_local_ignored_packets_only",
        "product_provider_failure_observability": {
            "classifications": [
                "provider_rate_limit",
                "provider_capacity",
                "provider_quota_or_usage_limit",
                "provider_authentication_failure",
                "provider_transport_failure",
                "unknown_provider_failure",
            ],
            "full_response_headers_retained": False,
            "request_payloads_retained": False,
            "raw_provider_responses_retained": False,
            "campaign_added_retries": 0,
            "rate_limit_disposition": "write_packet_stop_run_preserve_remaining",
        },
    }


def _manifest(*, created_at: str) -> dict[str, Any]:
    return {
        "campaign_schema": CAMPAIGN_SCHEMA,
        "phase_id": PHASE_ID,
        "created_at": created_at,
        "starting_main_sha": EXPECTED_STARTING_SHA,
        "branch": EXPECTED_BRANCH,
        "initial_execution_order": list(QUERY_ORDER),
        "initial_wave_complete": False,
        "live_contact_started": False,
        "next_initial_query_id": QUERY_ORDER[0],
        "attempts": {query_id: 0 for query_id in QUERY_ORDER},
        "runs": [],
        "active_repair_pair": None,
        "completed_repair_pairs": [],
        "instruction_amendments": [
            {
                "recorded_at": created_at,
                "name": "mid_campaign_monetary_configuration_broker_amendment",
                "monetary_accounting": "observational_telemetry_only",
                "alternate_model_execution": "closed",
                "broker_execution": "closed",
            },
            {
                "recorded_at": created_at,
                "name": "mid_session_recovery_and_configuration_clarification",
                "codex_host_model_identity": "unavailable",
                "live_campaign_budget_consumed_before_interruption": False,
                "classification": "codex_host_capacity_interruption",
                "product_failure": False,
            },
            {
                "recorded_at": created_at,
                "name": "immediate_capacity_interruption_and_product_failure_observability",
                "interruption_class": "codex_host_capacity_interruption",
                "codex_host_model_identity": "unavailable",
                "scryraven_product_failure": False,
                "live_campaign_budget_consumed": False,
                "product_provider_failure_taxonomy": [
                    "provider_rate_limit",
                    "provider_capacity",
                    "provider_quota_or_usage_limit",
                    "provider_authentication_failure",
                    "provider_transport_failure",
                    "unknown_provider_failure",
                ],
                "campaign_added_retries": 0,
                "rate_limit_disposition": (
                    "write_packet_stop_run_no_resend_preserve_remaining"
                ),
            },
        ],
        "exact_campaign_commands": {
            "init": (
                "py scripts\\ag_live_s1_product_convergence_01.py --init "
                "--output-root output\\live_validation\\s1_product_convergence"
            ),
            "block_a": (
                "py scripts\\ag_live_s1_product_convergence_01.py --run-block A "
                "--config output\\live_validation\\s1_product_convergence\\"
                "campaign_config.sanitized.json"
            ),
            "block_b": (
                "py scripts\\ag_live_s1_product_convergence_01.py --run-block B "
                "--config output\\live_validation\\s1_product_convergence\\"
                "campaign_config.sanitized.json"
            ),
        },
    }


def _matrix_packet(kind: str) -> dict[str, Any]:
    return {
        "campaign_schema": CAMPAIGN_SCHEMA,
        "phase_id": PHASE_ID,
        "matrix_kind": kind,
        "wave_1_complete": False,
        "entries": [
            {
                "query_id": query_id,
                "status": "not_run",
                "primary_failure_class": None,
                "candidate_current_owner": None,
            }
            for query_id in QUERY_ORDER
        ]
        if kind == "failure_matrix"
        else [],
    }


def _placeholder_run(query_id: str, query: str, digest: str) -> dict[str, Any]:
    return {
        "campaign_schema": CAMPAIGN_SCHEMA,
        "phase_id": PHASE_ID,
        "query_id": query_id,
        "query": query,
        "query_digest": digest,
        "attempt": 1,
        "status": "not_run",
        "live_campaign_budget_consumed": False,
        "final_answer_text": "",
        "retention_and_redaction": {
            "sanitized": True,
            "credential_values_retained": False,
            "private_material_retained": False,
        },
    }


def initialize_campaign(output_root: Path) -> int:
    root = validate_campaign_root(ROOT, output_root)
    if root.exists() and any(root.iterdir()):
        raise CampaignSafetyError(
            "campaign root already contains state; refusing to recreate or restart it"
        )
    branch = _git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise CampaignSafetyError(f"campaign must run on {EXPECTED_BRANCH}")
    if _git("rev-parse", EXPECTED_STARTING_SHA) != EXPECTED_STARTING_SHA:
        raise CampaignSafetyError("required starting SHA is unavailable")
    if _git("rev-parse", "HEAD") != EXPECTED_STARTING_SHA:
        raise CampaignSafetyError("campaign branch HEAD differs from the starting SHA")
    created_at = utc_now()
    nonsecret_config = _resolve_nonsecret_product_configuration()
    config = _campaign_config(nonsecret_config, created_at=created_at)
    validate_sanitized_value(config)
    root.mkdir(parents=True, exist_ok=True)
    write_sanitized_json(root / CONFIG_NAME, config, root=root)
    write_sanitized_json(root / MANIFEST_NAME, _manifest(created_at=created_at), root=root)
    write_sanitized_json(root / LEDGER_NAME, initial_budget_ledger(config), root=root)
    write_sanitized_json(root / "failure_matrix.json", _matrix_packet("failure_matrix"), root=root)
    write_sanitized_json(root / "repair_matrix.json", _matrix_packet("repair_matrix"), root=root)
    write_sanitized_json(
        root / "manual_source_checks.json",
        {
            "campaign_schema": CAMPAIGN_SCHEMA,
            "phase_id": PHASE_ID,
            "checks": [],
            "operator_oracles_entered_product_inputs": False,
        },
        root=root,
    )
    write_sanitized_json(
        root / "campaign_summary.json",
        {
            "campaign_schema": CAMPAIGN_SCHEMA,
            "phase_id": PHASE_ID,
            "disposition": None,
            "alternate_model_comparison": "alternate_model_comparison_not_run",
            "broker_used": False,
            "actual_provider_cost_not_observed": True,
        },
        root=root,
    )
    query_packets = _query_packets()
    for item in query_packets:
        write_sanitized_json(
            root / "runs" / f"run_{item['query_id']}_01.sanitized.json",
            _placeholder_run(
                str(item["query_id"]),
                str(item["query"]),
                str(item["query_digest"]),
            ),
            root=root,
        )
    review = (
        f"{CAMPAIGN_MARKER}\n\n"
        f"# {PHASE_ID} local campaign review\n\n"
        "Initialized offline. No ScryRaven provider/model/search/fetch/read call "
        "has occurred. Monetary telemetry is observational only; broker and "
        "alternate-model execution are closed.\n"
    )
    (root / "review.md").write_text(review, encoding="utf-8")
    print(f"initialized offline campaign state at {root}")
    return 0


def refresh_offline_campaign_state(config_path: Path) -> int:
    """Idempotently refresh observational schema before any live contact."""

    resolved_config = config_path.resolve()
    root = resolved_config.parent
    validate_campaign_root(ROOT, root)
    config = read_sanitized_json(resolved_config, root=root)
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    ledger = read_sanitized_json(root / LEDGER_NAME, root=root)
    if manifest.get("live_contact_started") is not False:
        raise CampaignSafetyError("offline refresh is closed after live contact")
    if ledger.get("runs") or any(
        int(value) != 0 for value in ledger.get("consumed_combined", {}).values()
    ):
        raise CampaignSafetyError("offline refresh requires zero consumed counters")

    configured = dict(config["ordinary_resolved_product_configuration"])
    config["repository_pricing_observation"] = _repository_pricing_observation(
        configured
    )
    estimate = ledger["observational_repository_cost_estimate"]
    estimate.pop("status", None)
    estimate["estimate_kind"] = "observational_repository_estimate"
    unknown = list(estimate.get("pricing_unknown_identities") or ())
    estimate["pricing_status"] = "pricing_unknown" if unknown else "pricing_known"
    amendments = manifest.setdefault("instruction_amendments", [])
    if not any(
        item.get("name") == "offline_gate0_observational_schema_refresh"
        for item in amendments
        if isinstance(item, dict)
    ):
        amendments.append(
            {
                "recorded_at": utc_now(),
                "name": "offline_gate0_observational_schema_refresh",
                "live_campaign_budget_consumed": False,
                "actual_provider_cost_not_observed": True,
                "pricing_status": config["repository_pricing_observation"][
                    "pricing_status"
                ],
            }
        )
    write_sanitized_json(resolved_config, config, root=root)
    write_sanitized_json(root / LEDGER_NAME, ledger, root=root)
    write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)
    print(f"refreshed offline campaign telemetry at {root}")
    return 0


def reconcile_sanitized_campaign_observability(config_path: Path) -> int:
    """Repair campaign accounting from sanitized product-owned cap facts only."""

    resolved_config = config_path.resolve()
    root = resolved_config.parent
    validate_campaign_root(ROOT, root)
    config = read_sanitized_json(resolved_config, root=root)
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    if manifest.get("initial_wave_complete") is not True:
        raise CampaignSafetyError(
            "sanitized observability reconciliation requires completed Wave 1"
        )

    repair_id = "campaign_observability_fetch_and_source_custody_repair_01"
    profile = get_validation_profile(AG_LIVE_S1_PRODUCT_CONVERGENCE)
    source_custody_requirements = (
        profile.source_custody_policy.as_requested_dict()
        if profile.source_custody_policy is not None
        else None
    )
    config["sanitized_packet_schema"] = profile.packet_schema
    config["source_custody_requirements"] = source_custody_requirements
    write_sanitized_json(resolved_config, config, root=root)
    consume_campaign_counters(
        config_path=resolved_config,
        block="A",
        increments={"root_cause_repair_clusters": 1},
        event_id=repair_id,
    )
    ledger = read_sanitized_json(root / LEDGER_NAME, root=root)
    for run_key, run in ledger.get("runs", {}).items():
        if not isinstance(run, dict):
            continue
        query_id, separator, attempt_text = str(run_key).rpartition(":")
        if not separator:
            raise CampaignSafetyError("campaign ledger run key is invalid")
        attempt = int(attempt_text)
        packet_path = root / "runs" / f"run_{query_id}_{attempt:02d}.sanitized.json"
        packet = read_sanitized_json(packet_path, root=root)
        caps_observed = packet.get("caps_observed")
        if not isinstance(caps_observed, dict):
            raise CampaignSafetyError("run packet lacks sanitized product cap facts")
        guard = CampaignBudgetGuard(
            config_path=resolved_config,
            query_id=query_id,
            attempt=attempt,
            block=str(run["block"]),
        )
        guard.reconcile_product_cap_observation_counts(caps_observed)

        custody = (
            packet.get("validation_observability", {}).get(
                "source_custody_summary"
            )
        )
        if isinstance(custody, dict) and source_custody_requirements:
            custody["source_custody_expected"] = True
            custody["fetch_read_required"] = True
            custody["profile_policy_reconciled"] = True
            write_sanitized_json(packet_path, packet, root=root)

    amendments = manifest.setdefault("instruction_amendments", [])
    if not any(
        item.get("name") == repair_id
        for item in amendments
        if isinstance(item, dict)
    ):
        amendments.append(
            {
                "recorded_at": utc_now(),
                "name": repair_id,
                "classification": "campaign_observability_repair",
                "owners": [
                    "CampaignBudgetGuard",
                    "core.validation_observability",
                ],
                "live_rerun_not_run_reason": "block_a_observed_token_cap_exhausted",
            }
        )
    write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)

    repairs = read_sanitized_json(root / "repair_matrix.json", root=root)
    entries = repairs.setdefault("entries", [])
    if not any(item.get("repair_cluster_id") == repair_id for item in entries):
        entries.append(
            {
                "repair_cluster_id": repair_id,
                "status": "completed_offline",
                "classification": "campaign_observability_repair",
                "owners": [
                    "CampaignBudgetGuard",
                    "core.validation_observability",
                ],
                "deterministic_offline_reproduction": (
                    "test_product_cap_reconciliation_and_s1_source_custody_profile"
                ),
                "live_rerun": "not_run_block_a_observed_token_cap_exhausted",
            }
        )
    write_sanitized_json(root / "repair_matrix.json", repairs, root=root)
    print(f"reconciled sanitized campaign observability at {root}")
    return 0


def finalize_budget_exhausted_campaign(
    *,
    config_path: Path,
    live_runtime_sha: str,
    recommendation: str,
) -> int:
    """Finalize the terminal campaign from sanitized state only."""

    resolved_config = config_path.resolve()
    root = resolved_config.parent
    validate_campaign_root(ROOT, root)
    config = read_sanitized_json(resolved_config, root=root)
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    ledger = read_sanitized_json(root / LEDGER_NAME, root=root)
    if manifest.get("initial_wave_complete") is not True:
        raise CampaignSafetyError("terminal finalization requires completed Wave 1")
    if (
        ledger.get("outbound_blocked_by_block", {}).get("A") is not True
        or ledger.get("outbound_block_reason_by_block", {}).get("A")
        != "observed_token_ceiling_reached"
    ):
        raise CampaignSafetyError(
            "BUDGET_EXHAUSTED requires the observed Block A token stop"
        )
    sha = str(live_runtime_sha or "").strip().casefold()
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
        raise CampaignSafetyError("live runtime SHA must be an exact 40-hex identity")
    if recommendation != "core_integration_reassessment":
        raise CampaignSafetyError(
            "terminal campaign recommendation must be core_integration_reassessment"
        )
    if manifest.get("attempts") != {query_id: 1 for query_id in QUERY_ORDER}:
        raise CampaignSafetyError(
            "terminal finalization requires exactly one Wave 1 attempt per query"
        )

    packets = {
        query_id: read_sanitized_json(
            root / "runs" / f"run_{query_id}_01.sanitized.json",
            root=root,
        )
        for query_id in QUERY_ORDER
    }
    expected_classifications = {
        "A_NO_QUANT": "success",
        "B_COMPONENT_CALC": "success",
        "C_SYNTHESIS_CALC": "success",
        "D_CONVERSION_NEGATIVE": "cap_overflow",
    }
    for query_id, expected in expected_classifications.items():
        packet = packets[query_id]
        if (
            packet.get("query_id") != query_id
            or packet.get("attempt") != 1
            or packet.get("success_classification") != expected
        ):
            raise CampaignSafetyError(
                f"terminal packet classification drifted for {query_id}"
            )
        if packet.get("product_provider_failure") is not None:
            raise CampaignSafetyError(
                f"terminal packet unexpectedly records a product failure for {query_id}"
            )

    live_started_at = str(ledger.get("live_contact_started_at") or "")
    live_completed_values = [
        str(item.get("completed_at") or "")
        for item in ledger.get("runs", {}).values()
        if isinstance(item, dict)
    ]
    if not live_started_at or len(live_completed_values) != len(QUERY_ORDER) or any(
        not value for value in live_completed_values
    ):
        raise CampaignSafetyError(
            "terminal finalization requires complete live-contact timestamps"
        )
    live_ended_at = max(live_completed_values)
    live_elapsed_seconds = round(
        (
            datetime.fromisoformat(live_ended_at)
            - datetime.fromisoformat(live_started_at)
        ).total_seconds(),
        6,
    )

    consumed = dict(ledger["consumed_combined"])
    tokens = ledger["observed_token_telemetry"]
    estimate = ledger["observational_repository_cost_estimate"]
    configured = config["ordinary_resolved_product_configuration"]
    exercised_calls = {
        key: value
        for key, value in ledger["calls_by_model_and_provider"].items()
        if not key.endswith(":reserved")
    }
    run_dispositions = [
        {
            "query_id": "A_NO_QUANT",
            "runner_classification": "success",
            "observed_disposition": (
                "reviewable ordinary final output with no Specialist work; "
                "requested facts remained incomplete"
            ),
        },
        {
            "query_id": "B_COMPONENT_CALC",
            "runner_classification": "success",
            "observed_disposition": (
                "reviewable arithmetic final output with no Specialist proposal, "
                "result, or component D-prime consumption"
            ),
        },
        {
            "query_id": "C_SYNTHESIS_CALC",
            "runner_classification": "success",
            "observed_disposition": (
                "reviewable insufficient-evidence final output with no Specialist "
                "proposal, result, two-hop binding, or synthesis D-prime consumption"
            ),
        },
        {
            "query_id": "D_CONVERSION_NEGATIVE",
            "runner_classification": "cap_overflow",
            "observed_disposition": (
                "cap overflow before final output; negative-control posture not proved"
            ),
        },
    ]
    summary = {
        "campaign_schema": CAMPAIGN_SCHEMA,
        "phase_id": PHASE_ID,
        "disposition": "BUDGET_EXHAUSTED",
        "terminal_reason": (
            "Block A observed-token cap was exceeded after a response; subsequent "
            "outbound work stopped prospectively and Block B was not authorized."
        ),
        "live_runtime_sha": sha,
        "baseline_product_configuration": {
            key: configured[key]
            for key in (
                "fast_provider",
                "fast_model",
                "smart_provider",
                "smart_model",
                "embed_provider",
                "embed_model",
            )
        }
        | {
            "active_configured_search_providers": list(
                configured["active_search_providers"]
            )
        },
        "calls_by_model_and_provider": exercised_calls,
        "operational_budget_requested": config["hard_operational_budget"],
        "budget_consumed": consumed
        | {
            "input_tokens": tokens["input_tokens"],
            "cached_input_tokens": tokens["cached_input_tokens"],
            "output_tokens": tokens["output_tokens"],
            "embedding_tokens": tokens["embedding_tokens"],
            "total_observed_tokens": tokens["total_observed_tokens"],
        },
        "block_a_stop": {
            "observed_token_ceiling": config["hard_operational_budget"]["block_a"][
                "observed_model_plus_embedding_tokens"
            ],
            "observed_token_total_after_last_response": tokens[
                "total_observed_tokens"
            ],
            "posture": "post_response_prospective_stop",
            "reason": "observed_token_ceiling_reached",
        },
        "live_contact": {
            "started_at": live_started_at,
            "ended_at": live_ended_at,
            "elapsed_seconds": live_elapsed_seconds,
        },
        "observational_repository_cost_estimate": {
            "usd": estimate["usd"],
            "pricing_status": estimate["pricing_status"],
        },
        "actual_provider_cost_not_observed": True,
        "product_provider_failure_count": sum(
            1 for packet in packets.values() if packet.get("product_provider_failure")
        ),
        "run_dispositions": run_dispositions,
        "alternate_model_comparison": "alternate_model_comparison_not_run",
        "alternate_model_comparison_reason": (
            "separately scoped future portability checkpoint"
        ),
        "broker_used": False,
        "explicit_nonproofs": [
            "S1 quantitative Specialist live convergence was not proved.",
            "Component or synthesis D-prime consumption was not observed.",
            "Two-hop synthesis source binding was not proved.",
            (
                "The conversion-negative final-answer posture was not observed "
                "because Run D stopped before final output."
            ),
            "Model portability was not run.",
            "Actual provider billing was not observed.",
        ],
        "selected_next_recommendation": recommendation,
    }
    write_sanitized_json(root / "campaign_summary.json", summary, root=root)

    failure = read_sanitized_json(root / "failure_matrix.json", root=root)
    attributions = {
        "A_NO_QUANT": (
            "partial_acquisition_or_custody_gap",
            "ordinary product acquisition and source-custody integration",
        ),
        "B_COMPONENT_CALC": (
            "partial_role_or_authority_gap",
            "ordinary multicomponent Specialist proposal and consumption path",
        ),
        "C_SYNTHESIS_CALC": (
            "partial_acquisition_and_role_gap",
            "acquisition/custody and ordinary multicomponent Specialist integration",
        ),
        "D_CONVERSION_NEGATIVE": (
            "observed_token_budget_exhausted",
            "campaign operational budget",
        ),
    }
    for entry in failure["entries"]:
        failure_class, owner = attributions[str(entry["query_id"])]
        entry["primary_failure_class"] = failure_class
        entry["candidate_current_owner"] = owner
    write_sanitized_json(root / "failure_matrix.json", failure, root=root)
    repairs = read_sanitized_json(root / "repair_matrix.json", root=root)
    repairs["wave_1_complete"] = True
    write_sanitized_json(root / "repair_matrix.json", repairs, root=root)

    manifest["terminal_disposition"] = "BUDGET_EXHAUSTED"
    manifest["live_runtime_sha"] = sha
    manifest["selected_next_recommendation"] = recommendation
    write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)

    exercised_search = [
        key.split(":", 2)[1]
        for key in exercised_calls
        if key.startswith("search:") and key.endswith(":observed")
    ]
    review = (
        f"{CAMPAIGN_MARKER}\n\n"
        f"# {PHASE_ID} local campaign review\n\n"
        "Terminal disposition: `BUDGET_EXHAUSTED`.\n\n"
        f"Wave 1 ran A, B, C, and D in order at live runtime SHA `{sha}`. "
        f"Configured search identities were {', '.join(configured['active_search_providers'])}; "
        f"observed search identities were {', '.join(exercised_search)}. Broker use "
        "was false and alternate-model comparison was not run.\n\n"
        "A reached reviewable output without Specialist work but remained incomplete. "
        "B presented arithmetic without Specialist or component D-prime consumption. "
        "C returned insufficient evidence without Specialist, two-hop, or synthesis "
        "D-prime consumption. D stopped before final output at the Block A token cap.\n\n"
        f"Consumed telemetry: {consumed['full_scryraven_runs']} runs, "
        f"{consumed['generative_plus_embedding_calls']} model/embedding calls, "
        f"{consumed['external_provider_search_calls']} provider/search calls, "
        f"{consumed['retrieval_fetch_read_operations']} fetch/read operations, and "
        f"{tokens['total_observed_tokens']} observed tokens. The stop is post-response "
        f"and prospective. Live contact elapsed {live_elapsed_seconds} seconds.\n\n"
        f"Repository-estimated cost is USD {estimate['usd']}. This is not actual billed "
        "cost; actual provider billing was not observed. No product-provider failure "
        "was recorded and campaign-added retries remained zero.\n\n"
        "One offline campaign-observability repair was completed without a live rerun. "
        f"The selected next recommendation is `{recommendation}` and is not started here.\n"
    )
    (root / "review.md").write_text(review, encoding="utf-8")
    print(f"finalized terminal campaign state at {root}")
    return 0


def authorize_wave_1_completion_extension(config_path: Path) -> int:
    """Record the operator's one-run D completion extension offline."""

    resolved_config = config_path.resolve()
    root = resolved_config.parent
    validate_campaign_root(ROOT, root)
    config = read_sanitized_json(resolved_config, root=root)
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    ledger = read_sanitized_json(root / LEDGER_NAME, root=root)
    summary_path = root / "campaign_summary.json"
    summary = read_sanitized_json(summary_path, root=root)

    existing = manifest.get("wave_1_completion_extension")
    if isinstance(existing, dict):
        if existing.get("status") != "authorized":
            raise CampaignSafetyError(
                "Wave 1 completion extension is no longer in its authorization state"
            )
        if (
            config["hard_operational_budget"]["block_a"][
                "observed_model_plus_embedding_tokens"
            ]
            != WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING
            or ledger["hard_operational_budget"]["block_a"][
                "observed_model_plus_embedding_tokens"
            ]
            != WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING
            or (root / "runs" / "run_D_CONVERSION_NEGATIVE_02.sanitized.json").exists()
        ):
            raise CampaignSafetyError("authorized completion extension state drifted")
        print(f"Wave 1 completion extension already authorized at {root}")
        return 0

    if manifest.get("initial_wave_complete") is not True:
        raise CampaignSafetyError("completion extension requires the original Wave 1")
    if manifest.get("attempts") != {
        "A_NO_QUANT": 1,
        "B_COMPONENT_CALC": 1,
        "C_SYNTHESIS_CALC": 1,
        "D_CONVERSION_NEGATIVE": 1,
    }:
        raise CampaignSafetyError("completion extension requires only A01 through D01")
    if (
        manifest.get("terminal_disposition") != "BUDGET_EXHAUSTED"
        or summary.get("disposition") != "BUDGET_EXHAUSTED"
    ):
        raise CampaignSafetyError(
            "completion extension requires the preserved BUDGET_EXHAUSTED terminal packet"
        )
    if int(config.get("campaign_added_retries", -1)) != 0 or int(
        ledger["consumed_combined"].get("campaign_added_retries", -1)
    ) != 0:
        raise CampaignSafetyError("campaign-added retries must remain zero")

    expected_block_a = AG_LIVE_S1_BLOCK_A_OPERATIONAL_BUDGET.as_dict()
    if (
        config["hard_operational_budget"]["block_a"] != expected_block_a
        or ledger["hard_operational_budget"]["block_a"] != expected_block_a
    ):
        raise CampaignSafetyError(
            "completion extension may replace only the original Block A token ceiling"
        )
    combined_config = config["hard_operational_budget"]["combined"]
    combined_ledger = ledger["hard_operational_budget"]["combined"]
    if (
        combined_config != AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET.as_dict()
        or combined_ledger != AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET.as_dict()
        or int(combined_config["observed_model_plus_embedding_tokens"])
        != WAVE_1_EXTENSION_COMBINED_TOKEN_CEILING
    ):
        raise CampaignSafetyError("combined campaign budget must remain unchanged")
    combined_tokens = int(
        ledger["observed_token_telemetry"]["total_observed_tokens"]
    )
    block_a_tokens = int(
        ledger["observed_token_telemetry_by_block"]["A"][
            "total_observed_tokens"
        ]
    )
    if (
        combined_tokens != WAVE_1_EXTENSION_PREVIOUS_TOKEN_TOTAL
        or block_a_tokens != WAVE_1_EXTENSION_PREVIOUS_TOKEN_TOTAL
    ):
        raise CampaignSafetyError(
            "completion extension token baseline differs from the operator decision"
        )
    if (
        ledger.get("outbound_blocked_by_block", {}).get("A") is not True
        or ledger.get("outbound_block_reason_by_block", {}).get("A")
        != "observed_token_ceiling_reached"
    ):
        raise CampaignSafetyError("original Block A token stop is not preserved")
    d02_path = root / "runs" / "run_D_CONVERSION_NEGATIVE_02.sanitized.json"
    if d02_path.exists():
        raise CampaignSafetyError("D attempt 02 already has a packet")

    prior_packet_path = root / "campaign_summary.pre_extension.sanitized.json"
    if prior_packet_path.exists():
        raise CampaignSafetyError("preserved pre-extension terminal packet already exists")
    original_packet_timestamp = datetime.fromtimestamp(
        summary_path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat()
    write_sanitized_json(prior_packet_path, summary, root=root)
    authorized_at = utc_now()
    amendment = {
        "recorded_at": authorized_at,
        "name": "operator_authorized_wave_1_completion_extension",
        "query_id": WAVE_1_EXTENSION_QUERY_ID,
        "attempt": WAVE_1_EXTENSION_ATTEMPT,
        "attempt_reason": WAVE_1_EXTENSION_ATTEMPT_REASON,
        "campaign_added_retries": 0,
        "superseded_for_wave_1_completion": True,
        "superseding_authority": WAVE_1_EXTENSION_AUTHORITY,
        "original_terminal_packet_timestamp": original_packet_timestamp,
        "original_consumed_combined": dict(ledger["consumed_combined"]),
        "original_observed_token_telemetry": dict(
            ledger["observed_token_telemetry"]
        ),
        "absolute_cumulative_block_a_token_ceiling": (
            WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING
        ),
        "maximum_additional_observed_tokens": (
            WAVE_1_EXTENSION_ADDITIONAL_TOKEN_LIMIT
        ),
        "combined_token_ceiling_unchanged": (
            WAVE_1_EXTENSION_COMBINED_TOKEN_CEILING
        ),
        "non_token_budgets_extended": False,
    }

    config["hard_operational_budget"]["block_a"][
        "observed_model_plus_embedding_tokens"
    ] = WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING
    config["wave_1_completion_extension"] = {
        **amendment,
        "exact_live_command": (
            "py scripts\\ag_live_s1_product_convergence_01.py "
            "--run-d-completion-extension --config "
            "output\\live_validation\\s1_product_convergence\\"
            "campaign_config.sanitized.json"
        ),
    }
    ledger["hard_operational_budget"]["block_a"][
        "observed_model_plus_embedding_tokens"
    ] = WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING
    ledger["outbound_blocked_by_block"]["A"] = False
    ledger["outbound_block_reason_by_block"]["A"] = None
    ledger.setdefault("operational_budget_amendments", []).append(amendment)

    manifest.setdefault("instruction_amendments", []).append(amendment)
    manifest["terminal_disposition_superseded_for_wave_1_completion"] = True
    manifest["superseding_authority"] = WAVE_1_EXTENSION_AUTHORITY
    manifest["wave_1_completion_extension"] = {
        "status": "authorized",
        **amendment,
        "mandatory_pause_after_attempt": True,
    }
    summary.setdefault("disposition_history", []).append(
        {
            "disposition": "BUDGET_EXHAUSTED",
            "terminal_reason": summary.get("terminal_reason"),
            "original_terminal_packet_timestamp": original_packet_timestamp,
            "original_consumed_combined": dict(ledger["consumed_combined"]),
            "original_observed_token_telemetry": dict(
                ledger["observed_token_telemetry"]
            ),
            "superseded_for_wave_1_completion": True,
            "superseding_authority": WAVE_1_EXTENSION_AUTHORITY,
            "preserved_packet": prior_packet_path.name,
        }
    )
    summary["superseded_for_wave_1_completion"] = True
    summary["superseding_authority"] = WAVE_1_EXTENSION_AUTHORITY
    summary["campaign_status"] = "wave_1_completion_extension_authorized"

    write_sanitized_json(resolved_config, config, root=root)
    write_sanitized_json(root / LEDGER_NAME, ledger, root=root)
    write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)
    write_sanitized_json(summary_path, summary, root=root)
    print(f"authorized offline Wave 1 completion extension at {root}")
    return 0


def _query_map(config: dict[str, Any]) -> dict[str, str]:
    return {
        str(item["query_id"]): str(item["query"])
        for item in config.get("fixed_queries", [])
        if isinstance(item, dict)
    }


def _runner_args(
    *,
    config_path: Path,
    query_id: str,
    query: str,
    attempt: int,
    block: str,
) -> list[str]:
    caps = AG_LIVE_S1_PER_RUN_CAP_POLICY
    output = CAMPAIGN_ROOT_RELATIVE / "runs" / f"run_{query_id}_{attempt:02d}.sanitized.json"
    return [
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
        str(output),
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
        str(config_path),
        "--campaign-block",
        block,
        "--campaign-attempt",
        str(attempt),
        "--confirm-live-product-run",
    ]


def _record_run(
    *,
    root: Path,
    query_id: str,
    attempt: int,
    packet: dict[str, Any],
    result_code: int,
    attempt_reason: str | None = None,
) -> None:
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    manifest["attempts"][query_id] = attempt
    manifest["live_contact_started"] = True
    run_record = {
        "query_id": query_id,
        "attempt": attempt,
        "result_code": result_code,
        "success_classification": packet.get("success_classification"),
        "stage_reached": packet.get("s1_runtime_summary", {}).get(
            "stage_reached"
        ),
        "product_provider_failure_classification": (
            packet.get("product_provider_failure") or {}
        ).get("classification"),
        "recorded_at": utc_now(),
    }
    if attempt_reason is not None:
        run_record["attempt_reason"] = attempt_reason
        run_record["campaign_added_retries"] = 0
    manifest["runs"].append(run_record)
    initial_done = all(int(manifest["attempts"].get(item, 0)) >= 1 for item in QUERY_ORDER)
    manifest["initial_wave_complete"] = initial_done
    manifest["next_initial_query_id"] = next(
        (item for item in QUERY_ORDER if int(manifest["attempts"].get(item, 0)) == 0),
        None,
    )
    write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)

    failure = read_sanitized_json(root / "failure_matrix.json", root=root)
    for entry in failure["entries"]:
        if entry.get("query_id") != query_id:
            continue
        classification = str(packet.get("success_classification") or "unknown")
        product_failure = packet.get("product_provider_failure") or {}
        entry.update(
            {
                "status": "completed" if result_code == 0 else "failed",
                "attempt": attempt,
                "runner_classification": classification,
                "primary_failure_class": (
                    product_failure.get("classification")
                    or (
                        None
                        if classification == "success"
                        else "pending_operator_attribution"
                    )
                ),
                "candidate_current_owner": None,
            }
        )
    failure["wave_1_complete"] = initial_done
    write_sanitized_json(root / "failure_matrix.json", failure, root=root)


def _execute_one(
    *,
    config_path: Path,
    root: Path,
    block: str,
    query_id: str,
    query: str,
    attempt: int,
    attempt_reason: str | None = None,
) -> tuple[int, dict[str, Any]]:
    from scripts import ag_live_bound_01_bounded_product_runner as runner

    args = _runner_args(
        config_path=config_path,
        query_id=query_id,
        query=query,
        attempt=attempt,
        block=block,
    )
    printable = subprocess.list2cmdline(
        ["py", str(RUNNER_RELATIVE), *args]
    )
    print("exact bounded live command before outbound contact:")
    print(printable)
    result = runner.main(args)
    packet_path = root / "runs" / f"run_{query_id}_{attempt:02d}.sanitized.json"
    packet = read_sanitized_json(packet_path, root=root)
    if attempt_reason is not None:
        packet["attempt_reason"] = attempt_reason
        packet["campaign_added_retries"] = 0
        write_sanitized_json(packet_path, packet, root=root)
    _record_run(
        root=root,
        query_id=query_id,
        attempt=attempt,
        packet=packet,
        result_code=result,
        attempt_reason=attempt_reason,
    )
    return result, packet


def run_d_completion_extension(config_path: Path) -> int:
    """Execute only the operator-authorized D attempt 02 and then pause."""

    resolved_config = config_path.resolve()
    root = resolved_config.parent
    validate_campaign_root(ROOT, root)
    config = read_sanitized_json(resolved_config, root=root)
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    ledger = read_sanitized_json(root / LEDGER_NAME, root=root)
    extension = manifest.get("wave_1_completion_extension")
    if not isinstance(extension, dict) or extension.get("status") != "authorized":
        raise CampaignSafetyError(
            "D attempt 02 requires the offline operator-extension authorization"
        )
    if manifest.get("attempts") != {
        "A_NO_QUANT": 1,
        "B_COMPONENT_CALC": 1,
        "C_SYNTHESIS_CALC": 1,
        "D_CONVERSION_NEGATIVE": 1,
    }:
        raise CampaignSafetyError("D attempt 02 is the only authorized live run")
    if int(config.get("campaign_added_retries", -1)) != 0:
        raise CampaignSafetyError("campaign-added retries must remain zero")
    if (
        config["hard_operational_budget"]["block_a"][
            "observed_model_plus_embedding_tokens"
        ]
        != WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING
        or ledger["hard_operational_budget"]["block_a"][
            "observed_model_plus_embedding_tokens"
        ]
        != WAVE_1_EXTENSION_BLOCK_A_TOKEN_CEILING
        or config["hard_operational_budget"]["combined"][
            "observed_model_plus_embedding_tokens"
        ]
        != WAVE_1_EXTENSION_COMBINED_TOKEN_CEILING
        or ledger["hard_operational_budget"]["combined"][
            "observed_model_plus_embedding_tokens"
        ]
        != WAVE_1_EXTENSION_COMBINED_TOKEN_CEILING
    ):
        raise CampaignSafetyError("operator token-extension identity drifted")
    if int(ledger["observed_token_telemetry"]["total_observed_tokens"]) != (
        WAVE_1_EXTENSION_PREVIOUS_TOKEN_TOTAL
    ):
        raise CampaignSafetyError("outbound work occurred after extension authorization")
    if ledger.get("outbound_blocked") is True or ledger.get(
        "outbound_blocked_by_block", {}
    ).get("A") is True:
        raise CampaignSafetyError("campaign outbound work remains blocked")
    packet_path = root / "runs" / "run_D_CONVERSION_NEGATIVE_02.sanitized.json"
    if packet_path.exists():
        raise CampaignSafetyError("D attempt 02 cannot be repeated")

    query = _query_map(config)[WAVE_1_EXTENSION_QUERY_ID]
    try:
        result, packet = _execute_one(
            config_path=resolved_config,
            root=root,
            block="A",
            query_id=WAVE_1_EXTENSION_QUERY_ID,
            query=query,
            attempt=WAVE_1_EXTENSION_ATTEMPT,
            attempt_reason=WAVE_1_EXTENSION_ATTEMPT_REASON,
        )
    except Exception as exc:
        ledger = read_sanitized_json(root / LEDGER_NAME, root=root)
        ledger["outbound_blocked"] = True
        ledger["outbound_block_reason"] = (
            "wave_1_completion_extension_infrastructure_failure"
        )
        write_sanitized_json(root / LEDGER_NAME, ledger, root=root)
        manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
        extension = manifest["wave_1_completion_extension"]
        extension["status"] = "failed_before_trustworthy_packet"
        extension["exception_class"] = type(exc).__name__
        extension["mandatory_operator_review"] = True
        extension["completed_at"] = utc_now()
        write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)
        raise

    ledger = read_sanitized_json(root / LEDGER_NAME, root=root)
    block_a_token_stop = ledger.get("outbound_blocked_by_block", {}).get("A") is True
    combined_token_stop = ledger.get("outbound_blocked") is True
    if not combined_token_stop:
        ledger["outbound_blocked"] = True
        ledger["outbound_block_reason"] = (
            "observed_token_ceiling_reached"
            if block_a_token_stop
            else "mandatory_operator_review_after_d_attempt_02"
        )
    write_sanitized_json(root / LEDGER_NAME, ledger, root=root)

    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    extension = manifest["wave_1_completion_extension"]
    extension["status"] = "completed"
    extension["completed_at"] = utc_now()
    extension["result_code"] = result
    extension["runner_classification"] = packet.get("success_classification")
    extension["product_provider_failure_classification"] = (
        packet.get("product_provider_failure") or {}
    ).get("classification")
    extension["mandatory_operator_review"] = True
    extension["further_live_work_authorized"] = False
    write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)
    return result


def run_block(
    *,
    block: str,
    config_path: Path,
    rerun_query_id: str | None,
    control_query_id: str | None,
) -> int:
    resolved_config = config_path.resolve()
    root = resolved_config.parent
    validate_campaign_root(ROOT, root)
    config = read_sanitized_json(resolved_config, root=root)
    if config.get("phase_id") != PHASE_ID:
        raise CampaignSafetyError("campaign config phase mismatch")
    query_map = _query_map(config)
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    if rerun_query_id is None:
        if block != "A":
            raise CampaignSafetyError("initial fixed Wave 1 must execute in Block A")
        query_ids = [
            item for item in QUERY_ORDER if int(manifest["attempts"].get(item, 0)) == 0
        ]
    else:
        if not manifest.get("initial_wave_complete"):
            raise CampaignSafetyError("repair reruns are closed until Wave 1 is complete")
        if rerun_query_id not in query_map or control_query_id not in query_map:
            raise CampaignSafetyError("campaign cannot execute an unknown query ID")
        active_pair = manifest.get("active_repair_pair")
        if active_pair:
            if (
                active_pair.get("block") != block
                or active_pair.get("triggering_query_id") != rerun_query_id
                or active_pair.get("control_query_id") != control_query_id
            ):
                raise CampaignSafetyError(
                    "a different repair rerun pair is already pending"
                )
        else:
            pair_id = (
                f"repair-pair:{block}:{rerun_query_id}:"
                f"{int(manifest['attempts'].get(rerun_query_id, 0)) + 1}:"
                f"{control_query_id}:"
                f"{int(manifest['attempts'].get(control_query_id, 0)) + 1}"
            )
            consume_campaign_counters(
                config_path=resolved_config,
                block=block,
                increments={
                    "root_cause_repair_clusters": 1,
                    "repeated_failed_query_reruns": 1,
                },
                event_id=pair_id,
            )
            active_pair = {
                "pair_id": pair_id,
                "block": block,
                "triggering_query_id": rerun_query_id,
                "control_query_id": control_query_id,
                "remaining_query_ids": [rerun_query_id, control_query_id],
                "started_at": utc_now(),
            }
            manifest["active_repair_pair"] = active_pair
            write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)
        query_ids = list(active_pair.get("remaining_query_ids") or ())
    if not query_ids:
        print("requested campaign block has no pending run")
        return 0
    for query_id in query_ids:
        attempt = int(manifest["attempts"].get(query_id, 0)) + 1
        result, packet = _execute_one(
            config_path=resolved_config,
            root=root,
            block=block,
            query_id=query_id,
            query=query_map[query_id],
            attempt=attempt,
        )
        manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
        active_pair = manifest.get("active_repair_pair")
        if active_pair and query_id in active_pair.get("remaining_query_ids", []):
            active_pair["remaining_query_ids"].remove(query_id)
            if not active_pair["remaining_query_ids"]:
                active_pair["completed_at"] = utc_now()
                manifest["completed_repair_pairs"].append(active_pair)
                manifest["active_repair_pair"] = None
            write_sanitized_json(root / MANIFEST_NAME, manifest, root=root)
        classification = str(packet.get("success_classification") or "")
        product_failure = packet.get("product_provider_failure") or {}
        if product_failure.get("classification"):
            return result or 3
        if result != 0 and classification not in {"pipeline_failure"}:
            return result
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--init", action="store_true", help="Initialize offline state.")
    action.add_argument(
        "--refresh-offline-state",
        action="store_true",
        help="Refresh observational schema before any live contact.",
    )
    action.add_argument(
        "--reconcile-sanitized-observability",
        action="store_true",
        help="Repair accounting from sanitized completed-run facts only.",
    )
    action.add_argument(
        "--finalize-budget-exhausted",
        action="store_true",
        help="Finalize a sanitized Block A token-exhausted campaign.",
    )
    action.add_argument(
        "--authorize-wave-1-completion-extension",
        action="store_true",
        help="Record the operator-authorized D02 token extension offline.",
    )
    action.add_argument(
        "--run-d-completion-extension",
        action="store_true",
        help="Run only operator-authorized D attempt 02, then pause.",
    )
    action.add_argument("--run-block", choices=["A", "B"])
    parser.add_argument(
        "--output-root",
        default=str(CAMPAIGN_ROOT_RELATIVE),
        help="Exact ignored campaign root for --init.",
    )
    parser.add_argument("--config", help="Sanitized campaign config for live runs.")
    parser.add_argument("--rerun-query-id", choices=list(QUERY_ORDER))
    parser.add_argument("--control-query-id", choices=list(QUERY_ORDER))
    parser.add_argument("--live-runtime-sha")
    parser.add_argument(
        "--recommendation",
        choices=["core_integration_reassessment"],
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.init:
            return initialize_campaign(Path(args.output_root))
        if args.refresh_offline_state:
            if not args.config:
                raise CampaignSafetyError("--refresh-offline-state requires --config")
            return refresh_offline_campaign_state(Path(args.config))
        if args.reconcile_sanitized_observability:
            if not args.config:
                raise CampaignSafetyError(
                    "--reconcile-sanitized-observability requires --config"
                )
            return reconcile_sanitized_campaign_observability(Path(args.config))
        if args.finalize_budget_exhausted:
            if not args.config or not args.live_runtime_sha or not args.recommendation:
                raise CampaignSafetyError(
                    "terminal finalization requires config, live runtime SHA, and recommendation"
                )
            return finalize_budget_exhausted_campaign(
                config_path=Path(args.config),
                live_runtime_sha=args.live_runtime_sha,
                recommendation=args.recommendation,
            )
        if args.authorize_wave_1_completion_extension:
            if not args.config:
                raise CampaignSafetyError(
                    "--authorize-wave-1-completion-extension requires --config"
                )
            return authorize_wave_1_completion_extension(Path(args.config))
        if args.run_d_completion_extension:
            if not args.config:
                raise CampaignSafetyError(
                    "--run-d-completion-extension requires --config"
                )
            return run_d_completion_extension(Path(args.config))
        if not args.config:
            raise CampaignSafetyError("--run-block requires --config")
        if bool(args.rerun_query_id) != bool(args.control_query_id):
            raise CampaignSafetyError(
                "repair execution requires both --rerun-query-id and --control-query-id"
            )
        return run_block(
            block=args.run_block,
            config_path=Path(args.config),
            rerun_query_id=args.rerun_query_id,
            control_query_id=args.control_query_id,
        )
    except (CampaignSafetyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"refusing S1 campaign operation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
