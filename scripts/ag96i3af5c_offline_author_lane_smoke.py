from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_ag96i3af5a_author_execution_from_af4d import (  # noqa: E402
    FakeAF5AAdapter,
    _execute_af5a,
    _kernel_through_af4d,
)
from tests.test_ag96i3af5b_author_response_finalization import (  # noqa: E402
    _execute_af5b,
)

DEFAULT_ANSWER_TEXT = (
    "AF5C offline Author lane smoke answer from the AF5A fake adapter candidate."
)
FALSE_BOUNDARY_FLAGS = (
    "model_execution_allowed",
    "live_provider_call_allowed",
    "real_model_called",
    "ask_model_called",
    "execute_author_action_called",
    "author_executor_invoked",
    "model_response_retained",
    "provider_payload_retained",
    "prompt_text_retained",
    "request_text_retained",
    "search_executed",
    "retrieval_executed",
    "fetch_executed",
    "provider_search_changed",
    "retrieval_ranking_filtering_changed",
    "evidence_reselected",
    "citation_rendering_changed",
    "citation_formatter_invoked",
    "citation_reselection_changed",
)


@dataclass(frozen=True, slots=True)
class OfflineAuthorLaneSmokeResult:
    kernel: Any
    summary: dict[str, Any]


def run_offline_author_lane_smoke(
    *,
    answer_text: str = DEFAULT_ANSWER_TEXT,
) -> OfflineAuthorLaneSmokeResult:
    kernel = _kernel_through_af4d()

    af5a_action = kernel.authorize_followup_author_execution_from_af4d()
    af5a_result = _execute_af5a(
        kernel,
        action=af5a_action,
        adapter=FakeAF5AAdapter(answer_text),
    )
    kernel.reduce(af5a_result.observation)

    af5b_action = kernel.authorize_followup_author_response_finalization()
    af5b_result = _execute_af5b(kernel, action=af5b_action)
    kernel.reduce(af5b_result.observation)

    return OfflineAuthorLaneSmokeResult(
        kernel=kernel,
        summary=build_smoke_summary(kernel),
    )


def build_smoke_summary(kernel: Any) -> dict[str, Any]:
    outcome = dict(kernel.state.final_answer_outcome)
    output = dict(outcome.get("final_answer_output") or {})
    finalization = dict(kernel.state.followup_author_response_finalization_state)
    packet_ref = dict(outcome.get("final_answer_packet_ref") or {})
    source_refs = dict(outcome.get("source_refs") or {})
    citation_refs = dict(outcome.get("citation_refs") or {})
    caveat_refs = dict(outcome.get("caveat_refs") or {})
    boundary_flags = _boundary_flags(outcome)

    return {
        "answer_text": output.get("answer_text") or outcome.get("final_answer_text"),
        "final_answer_outcome_id": outcome.get("final_answer_outcome_id"),
        "final_answer_outcome_digest": finalization.get("final_answer_outcome_digest"),
        "packet_id": output.get("packet_id") or outcome.get("packet_id") or packet_ref.get("packet_id"),
        "source_ref_count": _ref_count(source_refs),
        "citation_ref_count": _ref_count(citation_refs),
        "caveat_ref_count": _ref_count(caveat_refs),
        "boundary_flags": boundary_flags,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the AG-96I3AF5C offline Author-lane E2E smoke harness.",
    )
    parser.add_argument(
        "--answer-text",
        default=DEFAULT_ANSWER_TEXT,
        help="Bounded fake-adapter answer candidate for the offline smoke.",
    )
    args = parser.parse_args(argv)

    result = run_offline_author_lane_smoke(answer_text=args.answer_text)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    return 0


def _boundary_flags(surface: dict[str, Any]) -> dict[str, bool | None]:
    flags: dict[str, bool | None] = {}
    for flag in FALSE_BOUNDARY_FLAGS:
        flags[flag] = surface.get(flag) if flag in surface else None
    return flags


def _ref_count(refs: dict[str, Any]) -> int:
    total = 0
    for value in refs.values():
        if isinstance(value, list):
            total += len(value)
        elif value not in (None, "", [], {}):
            total += 1
    return total


if __name__ == "__main__":
    raise SystemExit(main())
