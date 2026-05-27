import json
from typing import Any


def parse_thin_quant_data_unavailable(text: str) -> tuple[bool, list[str]]:
    """Detect ``analyst_thin_quant`` DATA_UNAVAILABLE output; return flag and dataset hints."""
    s = (text or "").strip()
    if not s:
        return False, []
    first_line = s.split("\n", 1)[0].strip()
    prefix = "DATA_UNAVAILABLE:"
    if not first_line.startswith(prefix):
        return False, []
    payload = first_line[len(prefix) :].strip()
    if not payload:
        return True, []
    if payload.startswith("["):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, list):
                out = [str(x).strip() for x in parsed if str(x).strip()]
                return True, out
        except json.JSONDecodeError:
            pass
        inner = payload.strip()
        if inner.startswith("[") and inner.endswith("]"):
            inner = inner[1:-1].strip()
        parts = [p.strip().strip("'\"") for p in inner.split(",")]
        out = [p for p in parts if p]
        return True, out
    parts = [p.strip().strip("'\"") for p in payload.split(",")]
    out = [p for p in parts if p]
    return True, out if out else [payload]


def thin_quant_preflight_missing_entities(
    coverage: dict[str, Any], entities: list[str]
) -> list[str]:
    """Entities that do not map to JSON ``true`` in pre-flight cost-anchor coverage."""
    missing: list[str] = []
    for ent in entities:
        e = str(ent).strip()
        if not e:
            continue
        val = coverage.get(e)
        if val is None:
            ek = e.casefold()
            for k, v in coverage.items():
                if str(k).strip().casefold() == ek:
                    val = v
                    break
        if val is not True:
            missing.append(e)
    return missing
