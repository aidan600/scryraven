from __future__ import annotations

import argparse
import json
import os
import subprocess
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
BROKER_LIVE_DEFERRED_MAX_MODEL_CALLS = 1
FORBIDDEN_PACKET_KEYS = frozenset(
    """
    prompt raw_prompt prompt_text request_text raw_request_text model_request_text
    provider_payload raw_provider_payload raw_payload model_response
    raw_model_response raw_response private_log db_row cache full_trace secret
    api_key token
    """.split()
)


class AF6AFailClosed(RuntimeError):
    def __init__(self, message: str, *, packet: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.packet = packet


@dataclass(frozen=True, slots=True)
class AF6ASmokeResult:
    kernel: Any
    packet: dict[str, Any]


def _external_author_live_adapter(adapter_path: str) -> Any:
    resolved_adapter_path = _author_live_adapter_path(adapter_path)

    def call(
        request_text: str,
        *,
        request_digest: str,
        request_length: int,
        request_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        adapter_input = {
            "request_text": request_text,
            "request_digest": request_digest,
            "request_length": request_length,
            "request_metadata": request_metadata,
        }
        try:
            completed = subprocess.run(
                [sys.executable, str(resolved_adapter_path)],
                input=json.dumps(adapter_input),
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AF6AFailClosed("external Author live adapter failed") from exc
        try:
            adapter_output = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AF6AFailClosed("external Author live adapter returned invalid JSON") from exc
        if not isinstance(adapter_output, Mapping):
            raise AF6AFailClosed("external Author live adapter output must be a JSON object")
        metadata = dict(adapter_output.get("metadata") or {})
        metadata.update(
            {
                "adapter_kind": "external_live_model_adapter",
                "adapter_invocation_count": 1,
                "author_model_call_mode": "live_adapter",
                "request_digest_seen": request_digest,
                "request_length_seen": request_length,
            }
        )
        return {
            "candidate_text": adapter_output.get("candidate_text"),
            "metadata": metadata,
        }

    return call


def run_af6a_smoke(
    *,
    job_id: str,
    broker_live_mode: bool,
    confirm_live_provider_call: bool,
    fake_mode: bool = False,
    fake_answer: str = DEFAULT_FAKE_ANSWER,
    author_live_adapter_py: str | None = None,
) -> AF6ASmokeResult:
    if fake_mode:
        model_adapter: Any = FakeAF5AAdapter(fake_answer)
        mode = "fake"
    else:
        adapter_path = author_live_adapter_py or os.environ.get("SCRYRAVEN_AUTHOR_LIVE_ADAPTER_PY")
        _reject_broker_live_until_live_adapter_is_enabled(
            job_id=job_id,
            broker_live_mode=broker_live_mode,
            confirm_live_provider_call=confirm_live_provider_call,
            author_live_adapter_py=adapter_path,
        )
        model_adapter = _external_author_live_adapter(adapter_path or "")
        mode = "live_adapter"

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
        model_call_custody=_fake_model_call_custody() if fake_mode else _live_adapter_model_call_custody(),
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
    parser.add_argument("--author-live-adapter-py")
    args = parser.parse_args(argv)

    try:
        result = run_af6a_smoke(
            job_id=args.job_id,
            broker_live_mode=args.broker_live_mode,
            confirm_live_provider_call=args.confirm_live_provider_call,
            fake_mode=args.fake_mode,
            fake_answer=args.fake_answer,
            author_live_adapter_py=args.author_live_adapter_py,
        )
        output_path = _output_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result.packet, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except AF6AFailClosed as exc:
        if exc.packet is not None:
            output_path = _output_path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(exc.packet, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(f"wrote sanitized AF6A deferred packet to {output_path}", file=sys.stderr)
        print(f"AF6A fail closed: {exc}", file=sys.stderr)
        return 2
    print(f"wrote sanitized AF6A smoke packet to {output_path}")
    return 0


def _sanitized_packet(
    kernel: Any,
    *,
    job_id: str,
    mode: str,
    model_call_custody: Mapping[str, Any],
) -> dict[str, Any]:
    custody = dict(model_call_custody)
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
        "ok": True,
        **custody,
        "chain": ["AF4B2", "AF4C", "AF4D", "AF5A", "AF5B"],
        "budget": {
            "max_model_calls": custody["max_model_calls"],
            "model_calls_used": custody["model_calls_used"],
            "max_provider_search_calls": 0,
            "max_fetch_read_attempts": 0,
            "max_retrieval_calls": 0,
            "retries_allowed": False,
            "live_model_call_performed": custody["live_model_call_performed"],
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
        "author_response_candidate_ref_id": candidate.get("author_response_candidate_ref_id"),
        "author_response_candidate_digest": candidate.get("author_response_candidate_digest"),
        "closed_surface_flags": {
            **{flag: summary["boundary_flags"].get(flag) for flag in FALSE_BOUNDARY_FLAGS},
            "raw_prompt_retained": False,
            "raw_model_request_retained": False,
            "raw_provider_payload_retained": False,
            "raw_payload_retained": False,
            "raw_model_response_retained": False,
            "private_logs_retained": False,
            "db_cache_rows_retained": False,
            "full_trace_retained": False,
            "search_fetch_retrieval_executed": False,
        },
        **_top_level_false_retention_flags(),
    }


def _reject_broker_live_until_live_adapter_is_enabled(
    *,
    job_id: str,
    broker_live_mode: bool,
    confirm_live_provider_call: bool,
    author_live_adapter_py: str | None,
) -> None:
    if job_id != JOB_ID:
        raise AF6AFailClosed(f"unknown AF6A job id: {job_id}")
    if not broker_live_mode:
        raise AF6AFailClosed("broker live mode is required")
    if not confirm_live_provider_call:
        raise AF6AFailClosed("live model-call confirmation is required")
    if not author_live_adapter_py:
        raise AF6AFailClosed(
            "AF6A broker-live model adapter deferred; no live adapter path configured",
            packet=_deferred_broker_live_packet(job_id=job_id),
        )
    _author_live_adapter_path(author_live_adapter_py)


def _deferred_broker_live_packet(*, job_id: str) -> dict[str, Any]:
    custody = _broker_live_deferred_model_call_custody()
    packet = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "ag96i3af6a_brokered_author_lane_smoke_packet",
        "job_id": job_id,
        "mode": custody["author_model_call_mode"],
        "status": custody["author_model_call_status"],
        "ok": False,
        **custody,
        "chain": [],
        "deferred_reason": "broker_live_execution_not_enabled",
        "final_answer_created": False,
        "budget": {
            "max_model_calls": custody["max_model_calls"],
            "model_calls_used": custody["model_calls_used"],
            "max_provider_search_calls": 0,
            "max_fetch_read_attempts": 0,
            "max_retrieval_calls": 0,
            "retries_allowed": False,
            "live_model_call_performed": custody["live_model_call_performed"],
        },
        "closed_surface_flags": _closed_surface_flags(custody),
        **_top_level_false_retention_flags(),
    }
    _reject_forbidden_packet(packet)
    return packet


def _fake_model_call_custody() -> dict[str, Any]:
    return {
        "author_model_call_mode": "fake",
        "author_model_call_status": "completed_fake",
        "author_model_call_source": "injected_fake_model_adapter",
        "max_model_calls": 0,
        "model_calls_used": 0,
        "mock_model_adapter_calls_used": 0,
        "live_model_call_performed": False,
        "live_adapter_mocked": False,
        "fake_adapter_used": True,
        "broker_live_adapter_deferred": False,
        "broker_live_requested": False,
        "broker_live_execution_enabled": False,
        "prompt_raw_payload_retained": False,
        "model_request_raw_payload_retained": False,
        "provider_raw_payload_retained": False,
        "payload_raw_retained": False,
        "model_response_raw_payload_retained": False,
        "private_logs_retained": False,
        "db_cache_rows_retained": False,
        "full_trace_retained": False,
    }


def _broker_live_deferred_model_call_custody() -> dict[str, Any]:
    return {
        "author_model_call_mode": "broker_live_deferred",
        "author_model_call_status": "deferred",
        "author_model_call_source": "broker_live_adapter_deferred",
        "max_model_calls": BROKER_LIVE_DEFERRED_MAX_MODEL_CALLS,
        "model_calls_used": 0,
        "mock_model_adapter_calls_used": 0,
        "live_model_call_performed": False,
        "live_adapter_mocked": False,
        "fake_adapter_used": False,
        "broker_live_adapter_deferred": True,
        "broker_live_requested": True,
        "broker_live_execution_enabled": False,
        "prompt_raw_payload_retained": False,
        "model_request_raw_payload_retained": False,
        "provider_raw_payload_retained": False,
        "payload_raw_retained": False,
        "model_response_raw_payload_retained": False,
        "private_logs_retained": False,
        "db_cache_rows_retained": False,
        "full_trace_retained": False,
    }


def _live_adapter_model_call_custody() -> dict[str, Any]:
    custody = _broker_live_deferred_model_call_custody()
    custody.update(
        {
            "author_model_call_mode": "live_adapter",
            "author_model_call_status": "completed_live_adapter",
            "author_model_call_source": "external_live_model_adapter",
            "model_calls_used": 1,
            "live_model_call_performed": True,
            "broker_live_adapter_deferred": False,
            "broker_live_execution_enabled": True,
        }
    )
    return custody


def _closed_surface_flags(custody: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model_execution_allowed": False,
        "live_provider_call_allowed": False,
        "real_model_called": False,
        "ask_model_called": False,
        "execute_author_action_called": False,
        "author_executor_invoked": False,
        "model_response_retained": False,
        "provider_payload_retained": False,
        "prompt_text_retained": False,
        "request_text_retained": False,
        "search_executed": False,
        "retrieval_executed": False,
        "fetch_executed": False,
        "provider_search_changed": False,
        "retrieval_ranking_filtering_changed": False,
        "evidence_reselected": False,
        "citation_rendering_changed": False,
        "citation_formatter_invoked": False,
        "citation_reselection_changed": False,
        "raw_prompt_retained": custody["prompt_raw_payload_retained"],
        "raw_model_request_retained": custody["model_request_raw_payload_retained"],
        "raw_provider_payload_retained": custody["provider_raw_payload_retained"],
        "raw_payload_retained": custody["payload_raw_retained"],
        "raw_model_response_retained": custody["model_response_raw_payload_retained"],
        "private_logs_retained": custody["private_logs_retained"],
        "db_cache_rows_retained": custody["db_cache_rows_retained"],
        "full_trace_retained": custody["full_trace_retained"],
        "search_fetch_retrieval_executed": False,
    }


def _top_level_false_retention_flags() -> dict[str, bool]:
    return dict.fromkeys(
        "raw_prompt_retained raw_provider_payload_retained raw_model_response_retained private_logs_retained db_cache_rows_retained full_trace_retained secrets_returned".split(),
        False,
    )


def _author_live_adapter_path(adapter_path: str) -> Path:
    candidate = Path(adapter_path).expanduser().resolve()
    if not candidate.is_file():
        raise AF6AFailClosed("configured Author live adapter path is not a file")
    if candidate.suffix.casefold() != ".py":
        raise AF6AFailClosed("configured Author live adapter must be a Python file")
    return candidate


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
