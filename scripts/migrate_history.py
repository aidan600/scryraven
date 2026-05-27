#!/usr/bin/env python3
"""
Normalize execution_log.jsonl and session history files to current schema.
Dry-run by default. Use --apply to write changes (creates .bak backups first).

Fields backfilled:
  execution_log.jsonl: providers_used, retrieval_yield_chunks, timing, mode
  history.json: last_report_mode; pipeline_config.mode (copied from last_report_mode when missing)
  *_passages.json: source_id (sha256(url + date field).hexdigest()[:16]) only when missing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output"

DEFAULT_PROVIDERS_USED = ["exa"]
DEFAULT_MODE = "Balanced"


def passage_source_id(url: str, date_val: str | None) -> str:
    raw = f"{url or ''}{date_val or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _passage_date(p: dict[str, Any]) -> str:
    for key in ("date", "published_date", "pub_date", "retrieved_at"):
        v = p.get(key)
        if v is not None:
            return str(v)
    return ""


def migrate_execution_log_content(text: str) -> tuple[str, dict[str, int]]:
    """Return updated JSONL text and per-field increment counts."""
    stats = {
        "providers_used": 0,
        "retrieval_yield_chunks": 0,
        "timing": 0,
        "mode": 0,
        "lines_touched": 0,
    }
    out_lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            out_lines.append(line)
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            out_lines.append(line)
            continue
        changed = False
        if "providers_used" not in obj:
            obj["providers_used"] = list(DEFAULT_PROVIDERS_USED)
            stats["providers_used"] += 1
            changed = True
        if "retrieval_yield_chunks" not in obj:
            obj["retrieval_yield_chunks"] = 0
            stats["retrieval_yield_chunks"] += 1
            changed = True
        if "timing" not in obj:
            obj["timing"] = {}
            stats["timing"] += 1
            changed = True
        if "mode" not in obj:
            obj["mode"] = DEFAULT_MODE
            stats["mode"] += 1
            changed = True
        if changed:
            stats["lines_touched"] += 1
        out_lines.append(json.dumps(obj, ensure_ascii=True))
    if not out_lines:
        return "", stats
    joined = "\n".join(out_lines)
    if text.endswith("\n"):
        joined += "\n"
    return joined, stats


def migrate_history_sessions(sessions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {"last_report_mode": 0, "pipeline_config.mode": 0}
    out: list[dict[str, Any]] = []
    for session in sessions:
        s = dict(session)
        if "last_report_mode" not in s:
            s["last_report_mode"] = DEFAULT_MODE
            stats["last_report_mode"] += 1
        pconf = dict(s.get("pipeline_config") or {})
        if "mode" not in pconf:
            pconf["mode"] = s.get("last_report_mode", DEFAULT_MODE)
            stats["pipeline_config.mode"] += 1
        s["pipeline_config"] = pconf
        out.append(s)
    return out, stats


def migrate_passages_list(passages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {"source_id": 0}
    out: list[dict[str, Any]] = []
    for p in passages:
        row = dict(p)
        if "source_id" not in row:
            url = str(row.get("url") or "")
            row["source_id"] = passage_source_id(url, _passage_date(row))
            stats["source_id"] += 1
        out.append(row)
    return out, stats


def run_migration(output_dir: Path, apply: bool) -> dict[str, Any]:
    summary: dict[str, Any] = {"output_dir": str(output_dir), "apply": apply, "files": {}}

    exec_path = output_dir / "execution_log.jsonl"
    if exec_path.exists():
        text = exec_path.read_text(encoding="utf-8")
        new_text, st = migrate_execution_log_content(text)
        changed = bool(st.get("lines_touched", 0))
        summary["files"]["execution_log.jsonl"] = {"stats": st, "changed": changed}
        if apply and changed:
            shutil.copy2(exec_path, exec_path.with_suffix(exec_path.suffix + ".bak"))
            exec_path.write_text(new_text, encoding="utf-8")
    else:
        summary["files"]["execution_log.jsonl"] = {"skipped": "missing"}

    hist_path = output_dir / "history.json"
    if hist_path.exists():
        data = json.loads(hist_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            summary["files"]["history.json"] = {"error": "not a list"}
        else:
            new_sessions, st = migrate_history_sessions(data)
            changed = bool(st.get("last_report_mode", 0) or st.get("pipeline_config.mode", 0))
            summary["files"]["history.json"] = {"stats": st, "changed": changed}
            if apply and changed:
                shutil.copy2(hist_path, hist_path.with_suffix(hist_path.suffix + ".bak"))
                hist_path.write_text(json.dumps(new_sessions, indent=2), encoding="utf-8")
    else:
        summary["files"]["history.json"] = {"skipped": "missing"}

    passage_stats: dict[str, Any] = {}
    for pfile in sorted(output_dir.glob("*_passages.json")):
        raw = pfile.read_text(encoding="utf-8")
        try:
            passages = json.loads(raw)
        except json.JSONDecodeError:
            passage_stats[pfile.name] = {"error": "invalid json"}
            continue
        if not isinstance(passages, list):
            passage_stats[pfile.name] = {"error": "not a list"}
            continue
        new_passages, st = migrate_passages_list(passages)
        changed = bool(st.get("source_id", 0))
        passage_stats[pfile.name] = {"stats": st, "changed": changed}
        if apply and changed:
            shutil.copy2(pfile, pfile.with_suffix(pfile.suffix + ".bak"))
            pfile.write_text(json.dumps(new_passages, indent=2), encoding="utf-8")

    if passage_stats:
        summary["files"]["*_passages.json"] = passage_stats

    return summary


def format_summary(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    mode = "APPLY" if summary.get("apply") else "DRY-RUN"
    lines.append(f"migrate_history ({mode}) — {summary.get('output_dir')}")
    for name, info in summary.get("files", {}).items():
        if name == "*_passages.json":
            for pf, meta in info.items():
                if "stats" in meta:
                    lines.append(f"  {pf}: {meta['stats']} changed={meta.get('changed')}")
                else:
                    lines.append(f"  {pf}: {meta}")
            continue
        if "skipped" in info:
            lines.append(f"  {name}: skipped ({info['skipped']})")
            continue
        if "error" in info:
            lines.append(f"  {name}: ERROR {info['error']}")
            continue
        lines.append(f"  {name}: stats={info.get('stats')} changed={info.get('changed')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory containing execution_log.jsonl, history.json, *_passages.json (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (creates .bak backups). Default is dry-run only.",
    )
    args = parser.parse_args(argv)

    out_dir = args.output_dir.resolve()
    if not out_dir.is_dir():
        print(f"Output directory does not exist: {out_dir}", file=sys.stderr)
        return 2

    summary = run_migration(out_dir, apply=args.apply)
    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
