"""Offline aggregation of existing Reading Room dogfood receipts for AID-12."""

from math import isfinite


def _seconds(value):
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError("Missing or invalid duration")
    return value


def _dispatched_intervals(receipt):
    intervals = {}
    charged_legs = 0
    for row in receipt["acquisitions"]:
        external, dispatched = row["external"], row["provider_dispatched"]
        if type(external) is not bool or type(dispatched) is not bool or (dispatched and not external):
            raise ValueError("Unknown acquisition dispatch status")
        if "read_provider_attempts" in row:
            charged_legs += sum(attempt["charged"] for attempt in row["read_provider_attempts"])
        else:
            charged_legs += int(dispatched)
        if not dispatched:
            continue
        key = (row["route_index"], row["request_index"])
        start = _seconds(row["start_elapsed_seconds"])
        end = _seconds(row["end_elapsed_seconds"])
        if any(type(index) is not int or index < 1 for index in key) or key in intervals or end < start:
            raise ValueError("Invalid acquisition interval")
        intervals[key] = (start, end)
    if charged_legs != receipt["physical_acquisition_dispatches"]:
        raise ValueError("Incomplete acquisition timing")
    return intervals


def _union_seconds(intervals):
    total = latest_end = 0.0
    for start, end in sorted(intervals):
        total += max(0.0, end - max(start, latest_end))
        latest_end = max(latest_end, end)
    return total


def profile_turn(receipt):
    """Count each physical request once and union external acquisition intervals."""
    model_seconds = {"research": 0.0, "answer": 0.0}
    counts = dict.fromkeys(model_seconds, 0)
    for row in receipt["physical_model_calls"]:
        contract = row["contract"]
        model_seconds[contract] += _seconds(row["duration_seconds"])
        counts[contract] += 1
    if counts != receipt["role_physical_requests"] or sum(counts.values()) != receipt["physical_requests"]:
        raise ValueError("Incomplete physical model timing")

    external = _union_seconds(_dispatched_intervals(receipt).values())
    worker_seconds = _seconds(receipt["turn_elapsed_seconds"])
    remainder = worker_seconds - sum(model_seconds.values()) - external
    return {
        "research_model_seconds": model_seconds["research"],
        "answer_model_seconds": model_seconds["answer"],
        "external_path_seconds": external,
        "worker_remainder_seconds": remainder,
    }


def stopping_bound(receipt, *, browser_seconds, redundant_research_seconds, redundant_requests=()):
    """Price fixed-cost request deletion after independent evidence adjudication."""
    profile = profile_turn(receipt)
    browser_seconds = _seconds(browser_seconds)
    redundant_research_seconds = _seconds(redundant_research_seconds)
    retained_research = profile["research_model_seconds"] - redundant_research_seconds
    intervals = _dispatched_intervals(receipt)
    removed = set(redundant_requests)
    if retained_research < 0 or not removed.issubset(intervals):
        raise ValueError("Redundant work exceeds observed work")
    retained_external = _union_seconds(
        interval for key, interval in intervals.items() if key not in removed)
    saved_external = profile["external_path_seconds"] - retained_external
    route_only = browser_seconds - redundant_research_seconds - saved_external
    model_floor = retained_research + profile["answer_model_seconds"]
    if route_only + 0.001 < model_floor:  # Allow submillisecond receipt rounding.
        raise ValueError("Browser time is inconsistent with physical model timing")
    return {
        "route_only_browser_seconds": route_only,
        "optimistic_model_floor_seconds": model_floor,
    }
