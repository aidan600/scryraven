"""Offline UX demo fixture loading for the Streamlit shell.

The data loaded here is intentionally separate from live runtime sessions. It is
canned product-review metadata only and must not import or call provider,
search, model, retrieval, pipeline, cache, DB, or prompt code.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

DEMO_FIXTURE_KIND = "scryraven_offline_ux_demo"
DEMO_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "demo"
    / "fixtures"
    / "offline_ux_scenarios.json"
)
DEMO_SESSION_MARKER = "offline_ux_demo_fixture"


class DemoFixtureError(ValueError):
    """Raised when offline demo fixtures are missing or malformed."""


def load_demo_fixture_catalog(path: Path = DEMO_FIXTURE_PATH) -> dict[str, Any]:
    """Load and validate the offline demo fixture catalog deterministically."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("fixture_kind") != DEMO_FIXTURE_KIND:
        raise DemoFixtureError("offline demo fixture catalog has the wrong fixture_kind")
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise DemoFixtureError("offline demo fixture catalog must contain scenarios")

    seen: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise DemoFixtureError("offline demo scenario must be an object")
        scenario_id = str(scenario.get("id") or "").strip()
        if not scenario_id:
            raise DemoFixtureError("offline demo scenario is missing id")
        if scenario_id in seen:
            raise DemoFixtureError(f"duplicate offline demo scenario id: {scenario_id}")
        seen.add(scenario_id)
        for required in ("title", "query", "report", "progress_steps", "top_passages"):
            if required not in scenario:
                raise DemoFixtureError(
                    f"offline demo scenario {scenario_id!r} is missing {required!r}"
                )

    default_scenario = str(data.get("default_scenario") or "").strip()
    if default_scenario and default_scenario not in seen:
        raise DemoFixtureError("default offline demo scenario does not exist")
    return data


def list_demo_scenarios(path: Path = DEMO_FIXTURE_PATH) -> list[dict[str, str]]:
    """Return stable scenario selector metadata for the Streamlit sidebar."""

    catalog = load_demo_fixture_catalog(path)
    return [
        {
            "id": str(scenario["id"]),
            "title": str(scenario.get("title") or scenario["id"]),
            "state_label": str(scenario.get("state_label") or "Offline demo"),
        }
        for scenario in catalog["scenarios"]
    ]


def get_demo_scenario(scenario_id: str, path: Path = DEMO_FIXTURE_PATH) -> dict[str, Any]:
    """Return a deep copy of one offline demo scenario by id."""

    catalog = load_demo_fixture_catalog(path)
    requested = str(scenario_id or catalog.get("default_scenario") or "").strip()
    if not requested:
        requested = str(catalog["scenarios"][0]["id"])
    for scenario in catalog["scenarios"]:
        if scenario.get("id") == requested:
            return copy.deepcopy(scenario)
    raise DemoFixtureError(f"unknown offline demo scenario id: {requested}")


def build_demo_session(scenario_id: str, path: Path = DEMO_FIXTURE_PATH) -> dict[str, Any]:
    """Project one fixture scenario into the existing thread-session shape.

    The projection is intentionally marked as demo-only and is not persisted to
    history. It carries only review-safe fields used by the Streamlit shell.
    """

    catalog = load_demo_fixture_catalog(path)
    scenario = get_demo_scenario(scenario_id, path)
    session_id = f"demo-{scenario['id']}"
    return {
        "id": session_id,
        "run_id": session_id,
        "title": scenario.get("title") or scenario["id"],
        "query": scenario.get("query") or scenario["title"],
        "timestamp": scenario.get("timestamp") or "Offline demo fixture",
        "report": scenario.get("report") or "",
        "top_passages": copy.deepcopy(scenario.get("top_passages") or []),
        "demo_fixture": {
            "marker": DEMO_SESSION_MARKER,
            "fixture_kind": catalog["fixture_kind"],
            "schema_version": catalog.get("schema_version"),
            "offline_notice": catalog.get("offline_notice"),
            "scenario": copy.deepcopy(scenario),
        },
    }


def is_demo_session(session: Any) -> bool:
    """Return whether a session object came from offline UX demo fixtures."""

    if not isinstance(session, dict):
        return False
    marker = (session.get("demo_fixture") or {}).get("marker")
    return marker == DEMO_SESSION_MARKER
