from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.provider_diagnostics import provider_diagnostics_payload

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXECUTION_LOG_PATH = ROOT / "output" / "execution_log.jsonl"
COMMIT_SHA_ENV_VARS = (
    "PROPLEX_COMMIT_SHA",
    "GIT_COMMIT_SHA",
    "GITHUB_SHA",
    "VERCEL_GIT_COMMIT_SHA",
    "COMMIT_SHA",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_code_version_metadata() -> dict[str, str]:
    """Best-effort code metadata for diagnostics; never required for a run."""
    for env_var in COMMIT_SHA_ENV_VARS:
        value = os.environ.get(env_var, "").strip()
        if value:
            return {"commit_sha": value}

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
    except Exception:
        return {}

    if result.returncode != 0:
        return {}
    commit_sha = result.stdout.strip()
    if not commit_sha:
        return {}
    return {"commit_sha": commit_sha}


def append_jsonl(path: Path, payload: dict[str, Any], logger: logging.Logger | None = None) -> None:
    """Best-effort JSONL append. Logging failures must never break the run path."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception as e:
        if logger is not None:
            logger.warning(f"Non-fatal logging failure ({path.name}): {e}")


def log_execution_event(
    payload: dict[str, Any],
    *,
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    event = dict(payload)
    event.setdefault("timestamp_utc", utc_now_iso())
    append_jsonl(path or DEFAULT_EXECUTION_LOG_PATH, event, logger=logger)


def log_run_started(
    *,
    run_id: str,
    session_id: str | None,
    phase: str,
    query: str,
    mode: str | None = None,
    parent_run_id: str | None = None,
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "run_started",
        "phase": phase,
        "run_id": run_id,
        "session_id": session_id,
        "query_preview": (query or "")[:300],
    }
    if mode:
        payload["mode"] = mode
    if parent_run_id:
        payload["parent_run_id"] = parent_run_id
    log_execution_event(payload, path=path, logger=logger)


def log_chat_followup_completed(
    *,
    run_id: str,
    session_id: str | None,
    parent_run_id: str | None,
    query_preview: str,
    mode: str | None,
    latency_seconds: float,
    cost: dict[str, Any] | None = None,
    timing: dict[str, Any] | None = None,
    followup_diagnostics: dict[str, Any] | None = None,
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "chat_followup",
        "phase": "chat_followup",
        "run_id": run_id,
        "session_id": session_id,
        "query_preview": (query_preview or "")[:300],
        "latency_seconds": latency_seconds,
    }
    if parent_run_id:
        payload["parent_run_id"] = parent_run_id
    if mode:
        payload["mode"] = mode
    if cost is not None:
        payload["cost"] = cost
    if timing is not None:
        payload["timing"] = timing
    if followup_diagnostics is not None:
        payload["followup_diagnostics"] = followup_diagnostics
        attempts = followup_diagnostics.get("provider_diagnostics")
        if isinstance(attempts, list):
            payload.update(provider_diagnostics_payload(attempts))
    log_execution_event(payload, path=path, logger=logger)


def log_run_completed(
    *,
    run_id: str,
    session_id: str | None,
    phase: str,
    latency_seconds: float,
    mode: str | None = None,
    parent_run_id: str | None = None,
    timing: dict[str, Any] | None = None,
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "run_completed",
        "phase": phase,
        "run_id": run_id,
        "session_id": session_id,
        "latency_seconds": latency_seconds,
        "error": None,
    }
    if mode:
        payload["mode"] = mode
    if parent_run_id:
        payload["parent_run_id"] = parent_run_id
    if timing is not None:
        payload["timing"] = timing
    log_execution_event(payload, path=path, logger=logger)


def log_run_failed(
    *,
    run_id: str,
    session_id: str | None,
    phase: str,
    latency_seconds: float,
    error: Exception | str,
    mode: str | None = None,
    parent_run_id: str | None = None,
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "run_failed",
        "phase": phase,
        "run_id": run_id,
        "session_id": session_id,
        "latency_seconds": latency_seconds,
        "error": str(error)[:1000],
    }
    if mode:
        payload["mode"] = mode
    if parent_run_id:
        payload["parent_run_id"] = parent_run_id
    log_execution_event(payload, path=path, logger=logger)


def log_retrieval_timeout(
    *,
    provider: str,
    query: str,
    timeout_seconds: float,
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    log_execution_event(
        {
            "event": "retrieval_timeout",
            "provider": provider,
            "query_preview": (query or "")[:200],
            "timeout_seconds": timeout_seconds,
        },
        path=path,
        logger=logger,
    )


def log_provider_error(
    *,
    provider: str,
    error: str,
    query_preview: str = "",
    run_id: str | None = None,
    session_id: str | None = None,
    phase: str | None = None,
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "provider_error",
        "provider": provider,
        "error": str(error)[:1000],
        "query_preview": (query_preview or "")[:200],
    }
    if run_id:
        payload["run_id"] = run_id
    if session_id:
        payload["session_id"] = session_id
    if phase:
        payload["phase"] = phase
    log_execution_event(payload, path=path, logger=logger)
