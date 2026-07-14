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
) -> None:
    manifest = read_sanitized_json(root / MANIFEST_NAME, root=root)
    manifest["attempts"][query_id] = attempt
    manifest["live_contact_started"] = True
    manifest["runs"].append(
        {
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
    )
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
    _record_run(
        root=root,
        query_id=query_id,
        attempt=attempt,
        packet=packet,
        result_code=result,
    )
    return result, packet


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
    action.add_argument("--run-block", choices=["A", "B"])
    parser.add_argument(
        "--output-root",
        default=str(CAMPAIGN_ROOT_RELATIVE),
        help="Exact ignored campaign root for --init.",
    )
    parser.add_argument("--config", help="Sanitized campaign config for live runs.")
    parser.add_argument("--rerun-query-id", choices=list(QUERY_ORDER))
    parser.add_argument("--control-query-id", choices=list(QUERY_ORDER))
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
