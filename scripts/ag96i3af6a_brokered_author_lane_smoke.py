from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ag96i3af5c_offline_author_lane_smoke import (  # noqa: E402
    FALSE_BOUNDARY_FLAGS,
    build_smoke_summary,
)
from tests.test_ag96i3af5a_author_execution_from_af4d import (  # noqa: E402
    FakeAF5AAdapter,
    _execute_af5a,
    _kernel_through_af4d,
)
from tests.test_ag96i3af5b_author_response_finalization import (  # noqa: E402
    _execute_af5b,
)

JOB_ID = "ag96i3af6a-live-author-lane-smoke-once"
SCHEMA_VERSION = "ag96i3af6a_brokered_author_lane_smoke_v1"
DEFAULT_OUTPUT = Path("output/ag96i3af6a_live_author_lane_smoke_packet.json")
DEFAULT_FAKE_ANSWER = "AF6A fake Author-lane smoke answer."
FORBIDDEN_PACKET_KEYS = frozenset(
    """
    prompt raw_prompt prompt_text request_text raw_request_text model_request_text
    provider_payload raw_provider_payload raw_payload model_response
    raw_model_response raw_response private_log db_row cache full_trace secret
    api_key token
    """.split()
)


class AF6AFailClosed(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AF6ASmokeResult:
    kernel: Any
    packet: dict[str, Any]


def run_af6a_smoke(
    *,
    job_id: str,
    broker_live_mode: bool,
    confirm_live_provider_call: bool,
    fake_mode: bool = False,
    fake_answer: str = DEFAULT_FAKE_ANSWER,
) -> AF6ASmokeResult:
    if fake_mode:
        model_adapter: Any = FakeAF5AAdapter(fake_answer)
        adapter_calls = 0
        mode = "fake"
    else:
        _reject_broker_live_until_truthful_custody_exists(
            job_id=job_id,
            broker_live_mode=broker_live_mode,
            confirm_live_provider_call=confirm_live_provider_call,
        )

    kernel = _kernel_through_af4d()
    af5a_action = kernel.authorize_followup_author_execution_from_af4d()
    af5a_result = _execute_af5a(kernel, action=af5a_action, adapter=model_adapter)
    kernel.reduce(af5a_result.observation)

    af5b_action = kernel.authorize_followup_author_response_finalization()
    af5b_result = _execute_af5b(kernel, action=af5b_action)
    kernel.reduce(af5b_result.observation)

    packet = _sanitized_packet(
        kernel,
        job_id=job_id,
        mode=mode,
        adapter_calls=adapter_calls,
    )
    _reject_forbidden_packet(packet)
    return AF6ASmokeResult(kernel=kernel, packet=packet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the AG-96I3AF6A broker-aligned Author-lane smoke.",
    )
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--broker-live-mode", action="store_true")
    parser.add_argument("--confirm-live-provider-call", action="store_true")
    parser.add_argument("--fake-mode", action="store_true")
    parser.add_argument("--fake-answer", default=DEFAULT_FAKE_ANSWER)
    args = parser.parse_args(argv)

    try:
        result = run_af6a_smoke(
            job_id=args.job_id,
            broker_live_mode=args.broker_live_mode,
            confirm_live_provider_call=args.confirm_live_provider_call,
            fake_mode=args.fake_mode,
            fake_answer=args.fake_answer,
        )
        output_path = _output_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result.packet, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except AF6AFailClosed as exc:
        print(f"AF6A fail closed: {exc}", file=sys.stderr)
        return 2
    print(f"wrote sanitized AF6A smoke packet to {output_path}")
    return 0


def _sanitized_packet(
    kernel: Any,
    *,
    job_id: str,
    mode: str,
    adapter_calls: int,
) -> dict[str, Any]:
    summary = build_smoke_summary(kernel)
    af5a_state = dict(kernel.state.followup_author_execution_from_af4d_state)
    af5b_state = dict(kernel.state.followup_author_response_finalization_state)
    candidate = dict(af5a_state.get("bounded_sanitized_author_response_candidate") or {})
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "ag96i3af6a_brokered_author_lane_smoke_packet",
        "job_id": job_id,
        "mode": mode,
        "status": "completed",
        "chain": ["AF4B2", "AF4C", "AF4D", "AF5A", "AF5B"],
        "budget": {
            "max_model_calls": 0,
            "model_calls_used": adapter_calls,
            "max_provider_search_calls": 0,
            "max_fetch_read_attempts": 0,
            "max_retrieval_calls": 0,
            "retries_allowed": False,
        },
        "final_answer_text": summary["answer_text"],
        "final_answer_outcome_id": summary["final_answer_outcome_id"],
        "final_answer_outcome_digest": summary["final_answer_outcome_digest"],
        "packet_id": summary["packet_id"],
        "source_ref_count": summary["source_ref_count"],
        "citation_ref_count": summary["citation_ref_count"],
        "caveat_ref_count": summary["caveat_ref_count"],
        "af5a_execution_id": af5a_state.get("author_execution_from_af4d_id"),
        "af5b_finalization_id": af5b_state.get("author_response_finalization_id"),
        "author_response_candidate_ref_id": candidate.get(
            "author_response_candidate_ref_id"
        ),
        "author_response_candidate_digest": candidate.get(
            "author_response_candidate_digest"
        ),
        "closed_surface_flags": {
            **{flag: summary["boundary_flags"].get(flag) for flag in FALSE_BOUNDARY_FLAGS},
            "raw_prompt_retained": False,
            "raw_provider_payload_retained": False,
            "raw_model_response_retained": False,
            "private_logs_retained": False,
            "db_cache_rows_retained": False,
            "full_trace_retained": False,
            "search_fetch_retrieval_executed": False,
        },
    }


def _reject_broker_live_until_truthful_custody_exists(
    *,
    job_id: str,
    broker_live_mode: bool,
    confirm_live_provider_call: bool,
) -> None:
    if job_id != JOB_ID:
        raise AF6AFailClosed(f"unknown AF6A job id: {job_id}")
    if not broker_live_mode:
        raise AF6AFailClosed("broker live mode is required")
    if not confirm_live_provider_call:
        raise AF6AFailClosed("live model-call confirmation is required")
    raise AF6AFailClosed("AF6A broker-live model adapter deferred until truthful live-call custody fields exist")


def _output_path(output: str) -> Path:
    candidate = Path(output)
    candidate = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    output_root = (ROOT / "output").resolve()
    if candidate != output_root and output_root not in candidate.parents:
        raise AF6AFailClosed("refusing to write AF6A packet outside output/")
    if candidate.suffix.lower() != ".json":
        raise AF6AFailClosed("AF6A output must be JSON")
    return candidate


def _reject_forbidden_packet(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_PACKET_KEYS:
                raise AF6AFailClosed(f"forbidden AF6A packet field: {key}")
            _reject_forbidden_packet(child)
    elif isinstance(value, list | tuple | set):
        for child in value:
            _reject_forbidden_packet(child)


if __name__ == "__main__":
    raise SystemExit(main())
