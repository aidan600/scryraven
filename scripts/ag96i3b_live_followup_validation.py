from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.followup_authorization_runtime import (
    execute_followup_authorization_consumption_action,
)
from core.followup_deliberation import (
    GapType,
    build_followup_deliberation_checkpoint,
)
from core.followup_evidence_intake_runtime import (
    execute_followup_evidence_intake_action,
)
from core.followup_final_answer_packet_runtime import (
    execute_followup_final_answer_packet_prepare_action,
)
from core.followup_provider_job_live_validation_runtime import (
    AG96I3B_EXACT_VALIDATION_QUERY,
    execute_live_gated_followup_provider_job_validation_action,
)
from core.followup_sufficiency_recheck_runtime import (
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import RunKernel
from tests.helpers.followup_fixture_spine import followup_fixture_gap

RUN_ID = "ag96i3b-live-followup-official-current-validation"
OUTPUT_PACKET = Path("output/ag96i3b_live_followup_official_current_validation_packet.md")
QUERY_REF = "query.ref.ag96i3b.official.current.validation"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the AG-96I3B live-gated follow-up validation once.",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PACKET),
        help="Ignored local validation packet path.",
    )
    args = parser.parse_args()
    output_path = Path(args.output)

    ignore_status = _git_check_ignore(output_path)
    if ignore_status is None:
        print(f"refusing to write non-ignored output packet: {output_path}")
        return 2

    kernel = _authorized_kernel()
    action = kernel.authorize_followup_provider_job_execution(
        candidate_id="auth.candidate.001"
    )
    live_result = execute_live_gated_followup_provider_job_validation_action(
        action,
        live_validation_authorized=True,
    )
    validation = live_result.validation_record.to_dict()
    stop_reason = str(validation.get("stop_reason") or "unknown")
    intake_state: Mapping[str, Any] = {}
    recheck_state: Mapping[str, Any] = {}
    packet_state: Mapping[str, Any] = {}
    final_authority: Mapping[str, Any] = {}

    if live_result.provider_job_action_result is not None:
        kernel.reduce(live_result.provider_job_action_result.observation)
        intake_result = execute_followup_evidence_intake_action(
            kernel.authorize_followup_evidence_intake(),
            followup_execution_state=kernel.state.followup_execution_state,
            evidence_ledger_projection=(
                kernel.state.evidence_ledger.to_projection().to_dict()
            ),
        )
        kernel.reduce(intake_result.observation)
        intake_state = dict(kernel.state.followup_evidence_intake_state)

        recheck_result = execute_followup_sufficiency_recheck_action(
            kernel.authorize_followup_sufficiency_recheck(),
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
            evidence_ledger_projection=(
                kernel.state.evidence_ledger.to_projection().to_dict()
            ),
            prior_sufficiency_judgment_projection=(
                kernel.state.sufficiency_judgment_projection
            ),
            sufficiency_handoff=kernel.state.followup_authorization_state.get(
                "sufficiency_handoff",
                {},
            ),
        )
        kernel.reduce(recheck_result.observation)
        recheck_state = dict(kernel.state.followup_sufficiency_recheck_state)

        packet_result = execute_followup_final_answer_packet_prepare_action(
            kernel.authorize_followup_final_answer_packet_prepare(),
            followup_sufficiency_recheck_state=(
                kernel.state.followup_sufficiency_recheck_state
            ),
            sufficiency_judgment_projection=(
                kernel.state.sufficiency_judgment_projection
            ),
            evidence_ledger_projection=(
                kernel.state.evidence_ledger.to_projection().to_dict()
            ),
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        )
        kernel.reduce(packet_result.observation)
        packet_state = dict(kernel.state.followup_final_answer_packet_state)
        final_authority = dict(kernel.state.final_answer_authority_projection)
        stop_reason = "validation_reducer_spine_completed"

    packet = _render_packet(
        ignore_status=ignore_status,
        validation=validation,
        kernel=kernel,
        intake_state=intake_state,
        recheck_state=recheck_state,
        packet_state=packet_state,
        final_authority=final_authority,
        stop_reason=stop_reason,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(packet, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"live_validation_status={_live_validation_status(validation)}")
    return 0


def _authorized_kernel() -> RunKernel:
    kernel = RunKernel.start(run_id=RUN_ID, request_id="request-1")
    action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": "after-first-pass"}
    )
    result = execute_followup_authorization_consumption_action(
        action,
        checkpoint=_checkpoint(),
    )
    kernel.reduce(result.observation)
    return kernel


def _checkpoint() -> Any:
    gap = followup_fixture_gap(
        GapType.OFFICIAL_CURRENT_GAP.value,
        authorized_query_ref=QUERY_REF,
        authorized_query=AG96I3B_EXACT_VALIDATION_QUERY,
    )
    return build_followup_deliberation_checkpoint(
        {
            "run_id": RUN_ID,
            "checkpoint_id": "after-first-pass",
            "mode": "balanced",
            "components": [
                {
                    "component_id": "component-rule",
                    "central": True,
                    "served_minimum": True,
                    "minimum_provider_calls": 1,
                    "minimum_fetches": 1,
                    "minimum_read_units": 1,
                }
            ],
            "budget_ledger": {
                "cost_points_remaining": 8,
                "provider_calls_remaining": 1,
                "fetches_remaining": 1,
                "read_units_remaining": 1,
                "followup_rounds_remaining": 1,
                "meso_authorizations_remaining": 1,
                "macro_hops_remaining": 0,
            },
            "gaps": [gap],
            "sufficiency_handoff": {
                "satisfied_obligations": [],
                "missing_obligations": ["obligation-official-current"],
                "recommended_final_posture": "answer_with_caveats",
                "mandatory_caveats": ["prior_missing_official_current_caveat"],
                "prohibited_upgrades": ["prior_do_not_upgrade_fixture_gap"],
            },
        }
    )


def _render_packet(
    *,
    ignore_status: str,
    validation: Mapping[str, Any],
    kernel: RunKernel,
    intake_state: Mapping[str, Any],
    recheck_state: Mapping[str, Any],
    packet_state: Mapping[str, Any],
    final_authority: Mapping[str, Any],
    stop_reason: str,
) -> str:
    candidate = _mapping(validation.get("sanitized_candidate_facts"))
    diagnostics = _mapping(validation.get("provider_result_set_diagnostics"))
    sanitized_results = [
        _mapping(item) for item in diagnostics.get("sanitized_results", [])
    ]
    branch = _git_output(["git", "branch", "--show-current"]) or "unknown"
    head = _git_output(["git", "rev-parse", "--short", "HEAD"]) or "unknown"
    base_full = _git_output(["git", "merge-base", "main", "HEAD"]) or ""
    base = base_full[:7] if base_full else "unknown"
    provider_calls = validation.get("provider_search_call_count", 0)
    fetch_calls = validation.get("fetch_read_attempt_count", 0)
    lines = [
        "LOCAL/UNTRACKED \u2014 DO NOT COMMIT",
        "",
        "# AG-96I3B Live Follow-up Official/Current Validation Packet",
        "",
        "- phase_id: AG-96I3B",
        f"- exact_query: {AG96I3B_EXACT_VALIDATION_QUERY}",
        f"- run_id: {RUN_ID}",
        f"- branch: {branch}",
        f"- base: {base}",
        f"- head: {head}",
        f"- git_ignore_verification: {ignore_status}",
        "",
        "## Live Validation Budget",
        "",
        "- max_provider_search_calls: 1",
        "- max_fetch_read_attempts: 0",
        "- max_model_calls: 0",
        "- max_author_executor_calls: 0",
        "- retries_allowed: false",
        f"- provider_search_call_count: {provider_calls}",
        f"- fetch_read_attempt_count: {fetch_calls}",
        "",
        "## Gate Result",
        "",
        f"- live_validation_status: {_live_validation_status(validation)}",
        f"- provider_config_available: {validation.get('provider_config_available')}",
        f"- provider_search_call_occurred: {validation.get('provider_search_call_occurred')}",
        f"- fetch_read_occurred: {validation.get('fetch_read_occurred')}",
        f"- provider_name: {validation.get('provider_name')}",
        f"- result_status: {validation.get('result_status')}",
        f"- stop_reason: {stop_reason}",
        "",
        "## Sanitized Candidate",
        "",
        f"- url: {candidate.get('url') or 'none'}",
        f"- title: {candidate.get('title') or 'none'}",
        f"- domain: {candidate.get('domain') or 'none'}",
        f"- source_tier: {candidate.get('source_tier') or 'none'}",
        f"- source_class: {candidate.get('source_class') or 'none'}",
        f"- currentness_signal: {candidate.get('currentness_signal') or 'none'}",
        f"- fetchable_status: {candidate.get('fetchable_status') or 'none'}",
        f"- readable_status: {candidate.get('readable_status') or 'none'}",
        f"- authorized_query_ref: {candidate.get('authorized_query_ref') or 'none'}",
        "",
        "## Sanitized Result Set Diagnostics",
        "",
        f"- provider_result_count: {diagnostics.get('provider_result_count', 0)}",
        f"- sanitized_result_count: {diagnostics.get('sanitized_result_count', 0)}",
        f"- provider_surface_role: {diagnostics.get('provider_surface_role') or 'none'}",
        f"- provider_job_surface_alignment_status: {diagnostics.get('provider_job_surface_alignment_status') or 'none'}",
        f"- selected_candidate_rank: {diagnostics.get('selected_candidate_rank') or 'none'}",
        f"- selected_candidate_reason: {diagnostics.get('selected_candidate_reason') or 'none'}",
        f"- first_failure_layer: {diagnostics.get('first_failure_layer') or 'none'}",
        "",
        "### Sanitized Ranks",
        "",
        *[
            (
                f"- rank {item.get('rank')}: url={item.get('url') or 'none'}; "
                f"title={item.get('title') or 'none'}; "
                f"domain={item.get('domain') or 'none'}; "
                f"source_class={item.get('source_class') or 'none'}; "
                f"source_tier={item.get('source_tier') or 'none'}; "
                f"currentness_signal={item.get('currentness_signal') or 'none'}; "
                f"candidate_fit_status={item.get('candidate_fit_status') or 'none'}"
            )
            for item in sanitized_results
        ],
        "",
        "## EvidenceLedger / Sufficiency / Packet Posture",
        "",
        f"- followup_execution_state_reached: {bool(kernel.state.followup_execution_state)}",
        f"- evidence_ledger_intake_reached: {bool(intake_state)}",
        f"- evidence_ledger_intake_status: {intake_state.get('intake_status') or 'not_reached'}",
        f"- evidence_ledger_candidate_admitted: {intake_state.get('evidence_ledger_candidate_admitted', 'not_reached')}",
        f"- source_obligation_satisfied: {intake_state.get('source_obligation_satisfied', 'not_reached')}",
        f"- sufficiency_recheck_reached: {bool(recheck_state)}",
        f"- sufficiency_recheck_status: {recheck_state.get('recheck_status') or 'not_reached'}",
        f"- final_answer_allowed: {kernel.state.sufficiency_judgment_projection.get('final_answer_allowed', 'not_reached')}",
        f"- final_answer_packet_reached: {bool(packet_state)}",
        f"- final_answer_packet_status: {packet_state.get('packet_status') or 'not_reached'}",
        f"- author_activation_allowed: {final_authority.get('author_activation_allowed', False)}",
        "- author_executor_invoked: false",
        "- citation_rendering_changed: false",
        "- product_answer_behavior_changed: false",
        "",
        "## Redaction Posture",
        "",
        "- raw_provider_payload_retained: false",
        "- raw_page_text_retained: false",
        "- raw_snippets_retained: false",
        "- raw_prompts_retained: false",
        "- model_response_text_retained: false",
        "- api_keys_or_env_values_retained: false",
        "- db_rows_or_cache_rows_retained: false",
        "- private_logs_or_full_traces_retained: false",
    ]
    return "\n".join(lines) + "\n"


def _live_validation_status(validation: Mapping[str, Any]) -> str:
    if validation.get("result_status") == "config_missing_not_run":
        return "config_missing_not_run"
    if int(validation.get("provider_search_call_count") or 0) > 0:
        return "ran"
    return "stopped"


def _git_check_ignore(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "check-ignore", "-v", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return " ".join(result.stdout.strip().split())


def _git_output(args: list[str]) -> str | None:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


if __name__ == "__main__":
    raise SystemExit(main())
