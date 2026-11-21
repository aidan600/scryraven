"""Opt-in checks for registered prompt and pilot accounting."""

from hashlib import sha256

import pytest

from experiments.aid12.stopping import HANDOFF, STOPPING_INSTRUCTION, ordinary_research_prompt
from experiments.aid12.timing import profile_turn, stopping_bound
from scryraven.research import DELEGATED_RESEARCH_PROMPT, RESEARCH_PROMPT


def test_only_the_registered_prompt_is_patched_and_the_treatment_is_stable():
    candidate = ordinary_research_prompt(RESEARCH_PROMPT)
    assert candidate.count(STOPPING_INSTRUCTION) == 1
    assert candidate.replace(STOPPING_INSTRUCTION, "") == RESEARCH_PROMPT
    assert sha256(candidate.encode("utf-8")).hexdigest() == (
        "1ec71483e1b6d0c26c2ad621416e37731e996cd3340fc428c4cd95b72ae67092")  # pragma: allowlist secret


@pytest.mark.parametrize(
    "prompt",
    [
        RESEARCH_PROMPT.replace(HANDOFF, ""),
        RESEARCH_PROMPT + HANDOFF,
        RESEARCH_PROMPT + "\nDifferent release",
        ordinary_research_prompt(RESEARCH_PROMPT),
        DELEGATED_RESEARCH_PROMPT,
    ],
    ids=["missing-marker", "duplicate-marker", "drift", "already-patched", "delegated"],
)
def test_treatment_fails_closed_on_unregistered_prompt(prompt):
    with pytest.raises(ValueError, match="Unexpected ordinary Research prompt"):
        ordinary_research_prompt(prompt)


def acquisition(route, request, start, end, *, external=True, dispatched=True, **details):
    return {
        "route_index": route, "request_index": request, "start_elapsed_seconds": start,
        "end_elapsed_seconds": end, "external": external, "provider_dispatched": dispatched,
        **details,
    }


@pytest.fixture
def receipt():
    return {
        "turn_elapsed_seconds": 30,
        "physical_requests": 5,
        "physical_acquisition_dispatches": 4,
        "role_physical_requests": {"research": 3, "answer": 2},
        "physical_model_calls": [
            {"contract": "research", "duration_seconds": 2},
            {"contract": "research", "duration_seconds": 3},
            {"contract": "answer", "duration_seconds": 4},
            {"contract": "research", "duration_seconds": 6},  # Delegated.
            {"contract": "answer", "duration_seconds": 3, "continuation_index": 1},
        ],
        "model_calls": [{"contract": "answer", "duration_seconds": 18}],  # Encloses nested work.
        "research_tool_seconds": 9,
        "acquisitions": [
            acquisition(1, 1, 3, 6),
            acquisition(1, 2, 4, 8),
            acquisition(2, 1, 12, 15, read_provider_attempts=[
                {"provider": "linkup", "dispatched": True, "charged": True, "elapsed_seconds": 2.5},
                {"provider": "exa", "dispatched": True, "charged": True, "elapsed_seconds": 2.0},
            ]),
            acquisition(3, 1, 20, 22, external=False, dispatched=False),
            acquisition(3, 2, 22, 23, dispatched=False, suppressed=True),
        ],
    }


def test_aggregates_physical_model_time_and_only_dispatched_external_wall_time(receipt):
    assert profile_turn(receipt) == {
        "research_model_seconds": 11, "answer_model_seconds": 7,
        "external_path_seconds": 8, "worker_remainder_seconds": 4,
    }


def test_overlap_already_consumed_by_required_acquisition_cannot_be_saved(receipt):
    assert stopping_bound(
        receipt, browser_seconds=32, redundant_research_seconds=3, redundant_requests=[(1, 1)],
    ) == {"route_only_browser_seconds": 28, "optimistic_model_floor_seconds": 15}


def test_zero_avoidable_work_leaves_observed_route_time(receipt):
    assert stopping_bound(receipt, browser_seconds=32, redundant_research_seconds=0) == {
        "route_only_browser_seconds": 32, "optimistic_model_floor_seconds": 18,
    }


def test_incomplete_timing_cannot_support_a_bound(receipt):
    receipt["physical_model_calls"].pop()
    with pytest.raises(ValueError, match="Incomplete physical model timing"):
        stopping_bound(receipt, browser_seconds=32, redundant_research_seconds=0)


def test_invalid_interval_cannot_support_a_bound(receipt):
    receipt["acquisitions"][0]["end_elapsed_seconds"] = None
    with pytest.raises(ValueError, match="Missing or invalid duration"):
        stopping_bound(receipt, browser_seconds=32, redundant_research_seconds=0)


def test_missing_external_operation_cannot_support_a_bound(receipt):
    receipt["acquisitions"].pop(0)
    with pytest.raises(ValueError, match="Incomplete acquisition timing"):
        stopping_bound(receipt, browser_seconds=32, redundant_research_seconds=0)


def test_unobserved_acquisition_cannot_be_subtracted(receipt):
    with pytest.raises(ValueError, match="Redundant work exceeds observed work"):
        stopping_bound(receipt, browser_seconds=32, redundant_research_seconds=0, redundant_requests=[(3, 2)])


def test_browser_timing_cannot_be_shorter_than_measured_model_time(receipt):
    with pytest.raises(ValueError, match="Browser time is inconsistent"):
        stopping_bound(receipt, browser_seconds=10, redundant_research_seconds=0)
