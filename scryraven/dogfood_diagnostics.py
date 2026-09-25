"""Explicit local, body-free Reading Room turn diagnostics.

This is a projection of selected safe facts, never a serialization of a research
trace or a product session. Unknown event fields and strings are discarded.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from threading import Lock
from time import monotonic

from scryraven.errors import RunError
from scryraven.session_store import SessionStoreError

_SESSION_ID = re.compile(r"[0-9a-f]{32}\Z")
_EVIDENCE_REF = re.compile(r"E[1-9][0-9]*(?:@[0-9]+:[0-9]+)?\Z")
_MODEL_NAME = re.compile(r"(?:gpt|o[1-9])[-a-zA-Z0-9._]{1,70}\Z")
_CACHE_FAMILY = re.compile(r"sr-v1:(?:research|answer):(?:research|answer):[0-9a-f]{32}\Z")
_CONTRACTS = {"research", "answer"}
_POSTURES = {"supported", "partial", "unable"}
_STOP_REASONS = {"supported", "not_established", "research_bound"}
_PROVIDERS = {"exa", "serper", "linkup", "local"}
_KINDS = {"search", "search_lexical", "read", "find"}
_READ_MODES = {"auto", "local", "full", "refresh"}
_BREAKPOINTS = {"instructions", "history", "research_context"}
_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
_SERVICE_TIERS = {"default", "fast", "priority"}
_CODES = {
    "malformed_model_response", "unexposed_reference_or_action_shape",
    "attention_packet_too_large", "supported_with_missing_information",
    "basis_user_premises_has_evidence", "basis_user_premises_has_readings",
    "basis_user_premises_unable", "basis_none_requires_unable",
    "basis_evidence_missing_packet", "reading_passage_not_in_source",
    "unselected_reading_reference", "required_source_reading_missing",
    "missing_citation", "cited_source_without_reading", "deadline",
    "semantic_attempts", "external_attempts", "answer_deadline_reserve",
    "empty_question", "invalid_selected_material", "duplicate_selected_material",
    "empty_answer", "invalid_citation_reference", "malformed_citation_reference",
    "unknown_or_unselected_alias", "unresolved_answer_link", "answer_link_or_image",
    "exa_configuration_missing", "serper_configuration_missing",
    "linkup_configuration_missing", "linkup_material_unavailable",
    "invalid_request", "invalid_request_kind", "invalid_request_field",
    "invalid_read_mode", "invalid_find_scope", "invalid_exact_range",
    "empty_query", "empty_target", "invalid_public_url",
    "invalid_search_response", "unusable_acquisition", "unusable_fetch_material",
    "unknown_target", "unobserved_url", "unknown_exposure_reference",
    "local_material_unavailable",
    "search_failed", "read_failed", "model_configuration_missing",
    "model_request_timed_out", "model_request_rejected",
    "model_authentication_failed", "model_access_denied", "model_unavailable",
    "model_rate_limited", "model_transport_failed", "model_response_incomplete",
    "model_response_incomplete_content_filter",
    "model_response_incomplete_max_output_tokens", "model_refused",
    "model_response_empty", "model_execution_failed", "session_not_found", "session_conflict",
    "session_store_unavailable", "invalid_session_data", "incompatible_session_store",
    "unexpected_failure",
}
_SIZE_FIELDS = (
    "prior_conversation_turns", "conversation_characters", "current_question_characters",
    "retained_acquisition_count", "total_retained_source_characters",
    "prior_provenance_citations",
)
_CALL_SIZE_FIELDS = (
    "catalog_characters", "current_evidence_characters", "conversation_characters",
    "conversation_packet_characters",
)
_TOKEN_FIELDS = (
    "input_tokens", "cached_input_tokens", "cache_write_tokens",
    "ordinary_uncached_tokens", "output_tokens", "reasoning_tokens",
)


def _nonnegative_int(value):
    return value if type(value) is int and value >= 0 else None


def _seconds(value):
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        return None
    return round(float(value), 6)


def _one_of(value, choices):
    return value if type(value) is str and value in choices else None


def _code(value):
    return _one_of(value, _CODES) or "unexpected_failure"


def _model_name(value):
    return value if type(value) is str and _MODEL_NAME.fullmatch(value) else None


def _session_id(value):
    return value if type(value) is str and _SESSION_ID.fullmatch(value) else None


class DogfoodLog:
    """One explicitly chosen append target; write failure disables only diagnostics."""

    def __init__(self, path: str | Path, *, session_database: Path | None = None):
        try:
            self.path = Path(path).expanduser().resolve()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8"):
                pass
        except (OSError, ValueError, RuntimeError):
            raise OSError("dogfood_log_unavailable") from None
        self.session_database = session_database
        self._lock = Lock()
        self._enabled = True

    def append(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n"
        with self._lock:
            if not self._enabled:
                return
            try:
                with self.path.open("a", encoding="utf-8") as target:
                    if self.session_database is not None and self.session_database.exists():
                        diagnostic_file = os.fstat(target.fileno())
                        session_file = self.session_database.stat()
                        if (diagnostic_file.st_ino
                                and (diagnostic_file.st_dev, diagnostic_file.st_ino)
                                == (session_file.st_dev, session_file.st_ino)):
                            raise OSError("dogfood_log_matches_session_database")
                    target.write(line)
            except OSError:
                self._enabled = False
                print("Reading Room dogfood diagnostics stopped: the local log could not be written.",
                      file=sys.stderr, flush=True)


class TurnDiagnostics:
    """Per-attempt safe event projection, independent of session persistence."""

    def __init__(self, *, started_at: float | None = None, clock=monotonic):
        self.clock = clock
        self.started_at = clock() if started_at is None else started_at
        self.research_completed_at = None
        self.sizes = {key: None for key in _SIZE_FIELDS}
        self.models: list[dict] = []
        self._model_by_attempt: dict[tuple[str, int], dict] = {}
        self.acquisitions: list[dict] = []
        self.corrections: dict[str, Counter[str]] = {
            "research": Counter(), "answer": Counter(),
        }
        self.reading_rejections: list[dict] = []
        self.answer_returns = 0
        self.no_progress_commits = 0
        self.calculator_calls = 0
        self.calculator_failures = 0
        self.calculator_seconds = 0.0
        self.research_bounds: Counter[str] = Counter()
        self.semantic_attempts = None
        self.external_attempts = None

    def _budget(self, event):
        budget = event.get("budget")
        if isinstance(budget, dict):
            semantic = _nonnegative_int(budget.get("semantic_attempts"))
            external = _nonnegative_int(budget.get("external_attempts"))
            if semantic is not None:
                self.semantic_attempts = semantic
            if external is not None:
                self.external_attempts = external

    def observe(self, event: dict) -> None:
        """Ignore unknown and source-bearing events, including their nested data."""
        if not isinstance(event, dict) or event.get("stage") != "research":
            return
        action = event.get("action")
        if action == "started":
            for key in _SIZE_FIELDS:
                self.sizes[key] = _nonnegative_int(event.get(key))
        elif action == "model_started":
            contract = _one_of(event.get("contract"), _CONTRACTS)
            attempt = _nonnegative_int(event.get("attempt"))
            if contract is None or attempt is None:
                return
            row = {
                "contract": contract, "semantic_attempt": attempt,
                "start_elapsed_seconds": _seconds(event.get("started_elapsed_seconds")),
                "end_elapsed_seconds": None, "duration_seconds": None,
                "status": "started", "code": None,
                "model": _model_name(event.get("model")),
                "reasoning_effort": _one_of(event.get("reasoning_effort"), _REASONING_EFFORTS),
                "requested_service_tier": _one_of(event.get("requested_service_tier"), _SERVICE_TIERS),
                "returned_service_tier": None,
                "response_characters": None,
                **{key: _nonnegative_int(event.get(key)) for key in _CALL_SIZE_FIELDS},
                **{key: None for key in _TOKEN_FIELDS},
                "usage_incomplete": None,
                "cache_family": None, "breakpoints": [],
            }
            self.models.append(row)
            self._model_by_attempt[contract, attempt] = row
        elif action in {"model_returned", "model_failed"}:
            contract = _one_of(event.get("contract"), _CONTRACTS)
            attempt = _nonnegative_int(event.get("attempt"))
            row = self._model_by_attempt.get((contract, attempt))
            if row is None:
                return
            row["end_elapsed_seconds"] = _seconds(event.get("ended_elapsed_seconds"))
            row["duration_seconds"] = _seconds(event.get("duration_seconds"))
            row["status"] = "returned" if action == "model_returned" else "failed"
            row["code"] = _code(event.get("code")) if action == "model_failed" else None
            if action == "model_returned":
                row["response_characters"] = _nonnegative_int(event.get("response_characters"))
            usage = event.get("usage")
            if isinstance(usage, dict):
                row["requested_service_tier"] = _one_of(
                    usage.get("requested_service_tier"), _SERVICE_TIERS,
                ) or row["requested_service_tier"]
                row["returned_service_tier"] = _one_of(
                    usage.get("returned_service_tier"), _SERVICE_TIERS,
                )
                for key in _TOKEN_FIELDS:
                    row[key] = _nonnegative_int(usage.get(key))
                row["usage_incomplete"] = (usage.get("usage_incomplete")
                                           if type(usage.get("usage_incomplete")) is bool else None)
                family = usage.get("cache_family")
                row["cache_family"] = family if type(family) is str and _CACHE_FAMILY.fullmatch(family) else None
                labels = usage.get("breakpoints")
                if isinstance(labels, (list, tuple)):
                    row["breakpoints"] = [label for label in labels
                                          if type(label) is str and label in _BREAKPOINTS]
        elif action == "acquisition_timing":
            row = {
                "route_index": _nonnegative_int(event.get("route_index")),
                "request_index": _nonnegative_int(event.get("request_index")),
                "kind": _one_of(event.get("kind"), _KINDS),
                "read_mode": _one_of(event.get("mode"), _READ_MODES),
                "provider": _one_of(event.get("provider"), _PROVIDERS),
                "external": event.get("external") if type(event.get("external")) is bool else None,
                "start_elapsed_seconds": _seconds(event.get("started_elapsed_seconds")),
                "end_elapsed_seconds": _seconds(event.get("ended_elapsed_seconds")),
                "duration_seconds": _seconds(event.get("duration_seconds")),
                "status": _one_of(event.get("status"), {"ok", "error"}),
                "code": _code(event.get("code")) if event.get("status") == "error" else None,
                "returned_material_count": _nonnegative_int(event.get("returned_material_count")),
                "new_acquisition_count": _nonnegative_int(event.get("new_acquisition_count")),
                "returned_material_characters": _nonnegative_int(event.get("returned_material_characters")),
                "reused_retained_material": (
                    event.get("reused_retained_material")
                    if type(event.get("reused_retained_material")) is bool else None
                ),
            }
            self.acquisitions.append(row)
        elif action in {"response_rejected", "decision_rejected"}:
            code = _one_of(event.get("code"), _CODES)
            if code is not None:
                contract = (_one_of(event.get("contract"), _CONTRACTS)
                            if action == "response_rejected" else "research")
                if contract is not None:
                    self.corrections[contract][code] += 1
        elif action == "answer_reading_rejected":
            code = _one_of(event.get("code"), {
                "reading_passage_not_in_source", "unselected_reading_reference",
            })
            if code is not None:
                ref = event.get("evidence_ref")
                self.reading_rejections.append({
                    "code": code,
                    "evidence_ref": ref if type(ref) is str and _EVIDENCE_REF.fullmatch(ref) else None,
                    "reading_index": _nonnegative_int(event.get("reading_index")),
                    "passage_index": _nonnegative_int(event.get("passage_index")),
                })
        elif action == "answer_returned_to_research":
            self.answer_returns += 1
        elif action == "answer_committed_no_progress":
            self.no_progress_commits += 1
        elif action == "calculator_used":
            if event.get("contract") == "answer" and type(event.get("success")) is bool:
                self.calculator_calls += 1
                if not event["success"]:
                    self.calculator_failures += 1
                duration = _seconds(event.get("duration_seconds"))
                if duration is not None:
                    self.calculator_seconds += duration
        elif action == "research_bound":
            code = _one_of(event.get("code"), {
                "deadline", "semantic_attempts", "external_attempts", "answer_deadline_reserve",
            })
            if code is not None:
                self.research_bounds[code] += 1
        elif action == "completed":
            self.research_completed_at = self.clock()
        self._budget(event)

    def record(self, *, session_id: str | None, revision_before: int,
               revision_after: int | None, result=None, error: Exception | None = None) -> dict:
        finished_at = self.clock()
        if error is None:
            failure = None
        elif isinstance(error, RunError):
            failure = {"stage": _one_of(error.stage, {"research", "answer", "citations"}) or "research",
                       "code": _code(error.code)}
        elif isinstance(error, SessionStoreError):
            failure = {"stage": "session", "code": _code(error.code)}
        else:
            failure = {"stage": "reading_room", "code": "unexpected_failure"}
        completed_at = self.research_completed_at
        if completed_at is None and result is not None:
            completed_at = finished_at
        return {
            "schema_version": 1,
            "session_id": _session_id(session_id),
            "attempted_turn": revision_before + 1,
            "revision_before": revision_before,
            "revision_after": _nonnegative_int(revision_after),
            "outcome": "completed" if error is None else "failed",
            "turn_elapsed_seconds": _seconds(finished_at - self.started_at),
            "research_completed_elapsed_seconds": (
                _seconds(completed_at - self.started_at) if completed_at is not None else None
            ),
            "post_research_seconds": (
                _seconds(finished_at - completed_at) if completed_at is not None else None
            ),
            "posture": _one_of(getattr(result, "posture", None), _POSTURES),
            "stop_reason": _one_of(getattr(result, "stop_reason", None), _STOP_REASONS),
            "failure": failure,
            "semantic_attempts": self.semantic_attempts,
            "external_attempts": self.external_attempts,
            "sizes": self.sizes,
            "model_calls": self.models,
            "acquisitions": self.acquisitions,
            "corrections": {contract: dict(counts) for contract, counts in self.corrections.items()},
            "reading_rejections": self.reading_rejections,
            "answer_to_research_returns": self.answer_returns,
            "no_progress_commits": self.no_progress_commits,
            "calculator": {
                "calls": self.calculator_calls,
                "failures": self.calculator_failures,
                "duration_seconds": _seconds(self.calculator_seconds),
            },
            "research_bounds": dict(self.research_bounds),
            "retained_reuse_without_external": (
                any(item["reused_retained_material"] for item in self.acquisitions)
                and not any(item["external"] for item in self.acquisitions)
            ),
        }
