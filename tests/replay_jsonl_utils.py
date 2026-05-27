from __future__ import annotations

import json
from os import PathLike
from pathlib import Path
from typing import Any


def load_jsonl_dict_rows(path: str | PathLike[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    jsonl_path = Path(path)
    for line_number, raw_line in enumerate(
        jsonl_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw_line.strip():
            continue
        try:
            parsed = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{jsonl_path}: line {line_number}: invalid JSON"
            ) from exc
        if not isinstance(parsed, dict):
            raise ValueError(
                f"{jsonl_path}: line {line_number}: expected JSON object"
            )
        rows.append(parsed)
    return rows
