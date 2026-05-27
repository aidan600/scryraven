from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_POLICY_STATE: dict[str, Any] = {
    # Keep phase-1 policy limited to deterministic thresholds only.
    "thresholds": {
        "utilization_threshold": 0.25,
        "synth_skip_utilization_threshold": 0.25,
    }
}


def load_policy_state(policy_path: Path | str) -> dict[str, Any]:
    """Load policy JSON, returning defaults when file is missing/invalid."""
    p = Path(policy_path)
    if not p.exists():
        return json.loads(json.dumps(DEFAULT_POLICY_STATE))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT_POLICY_STATE))
    except Exception:
        return json.loads(json.dumps(DEFAULT_POLICY_STATE))
    merged = json.loads(json.dumps(DEFAULT_POLICY_STATE))
    if isinstance(data.get("thresholds"), dict):
        merged["thresholds"].update(data["thresholds"])
    return merged


def apply_policy_to_run_config(run_config: dict[str, Any], policy_state: dict[str, Any]) -> dict[str, Any]:
    """Apply threshold-only policy knobs to run configuration."""
    out = dict(run_config or {})
    thresholds = (policy_state or {}).get("thresholds") or {}
    if not isinstance(thresholds, dict):
        return out
    for key in ("utilization_threshold", "synth_skip_utilization_threshold"):
        v = thresholds.get(key)
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if 0.0 <= fv <= 1.0:
            out[key] = fv
    return out
