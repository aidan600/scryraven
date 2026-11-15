"""Project operational signals into compact owner-facing Reading Room activity."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from re import fullmatch
from threading import Lock

QUERY_CHARACTERS = 512
_INVESTIGATING = "Investigating your question"
_ANSWERING = "Preparing the answer"
_RETRIEVING = "Retrieving source text"
_INSPECTING = "Inspecting retained material"
_PROVIDERS = {"exa": "Exa", "serper": "Serper", "linkup": "LinkUp"}
_SEARCH_TYPES = {"lite": "Lite", "auto": "Auto", "lexical": "Lexical"}
_JOB_LABELS = {
    "queued": "Waiting to start",
    "researching": _INVESTIGATING,
    "completed": "Answer saved",
    "failed": "Research failed",
    "interrupted": "Research interrupted",
}
_STAGES = {
    "initial_research_handoff": ("Initial research returned to Answer", _ANSWERING),
    "research_invoked": ("Answer requested additional research", _INVESTIGATING),
    "research_returned": ("Additional research returned to Answer", _ANSWERING),
    "answer_validation_started": ("Checking citation references", "Checking citation references"),
}


def _utc_now():
    return datetime.now(timezone.utc)


def _elapsed(start, end):
    if start is None:
        return 0
    try:
        return max(0, (end - datetime.fromisoformat(start)).total_seconds())
    except (TypeError, ValueError):
        return 0


def _duration(event):
    value = event.get("duration_seconds")
    return {"elapsed_seconds": round(value, 3)} if (
        type(value) in (float, int) and 0 <= value <= 3600 and isfinite(value)
    ) else {}


def _count(event, key):
    value = event.get(key)
    return min(value, 10000) if type(value) is int and value >= 0 else 0


def _source_fields(event):
    fields = {}
    title = event.get("title")
    if isinstance(title, str):
        cleaned = " ".join(title[:512].split())[:160]
        if cleaned and "://" not in cleaned:
            fields["title"] = cleaned
    host = event.get("hostname")
    if isinstance(host, str) and len(host) <= 253 and fullmatch(r"[a-zA-Z0-9.-]+", host):
        fields["host"] = host.lower()
    return fields


def _amount(count, singular, plural):
    return f"{count} {singular if count == 1 else plural}"


class ActivityProjection:
    """Per-job presentation state. Dispatch callbacks can arrive in parallel."""

    def __init__(self, publish, *, created_at, started_at, clock=_utc_now):
        self._publish = publish
        self._clock = clock
        self._lock = Lock()
        self._current = ""
        self._current_since = None
        self._current_id = 0
        self._searches = {}
        self._stage("job_queued", "Question queued", _JOB_LABELS["queued"], at=created_at)
        self._stage("job_started", "Research started", _INVESTIGATING, at=started_at)

    def _record(self, kind, label, *, stage=None, at=None, **fields):
        at = at or self._clock().isoformat()
        if stage is not None and stage != self._current:
            self._current = stage
            self._current_since = at
            self._current_id += 1
        self._publish({
            "type": kind, "label": label, "at": at,
            "current": self._current, "current_since": self._current_since,
            "current_id": self._current_id, **fields,
        })

    def _stage(self, kind, label, stage, *, at=None):
        self._record(kind, label, stage=stage, at=at)

    def observe(self, event):
        """Consume only the phase markers from the existing diagnostic observer."""
        action = event.get("action")
        with self._lock:
            if action == "model_started":
                contract = event.get("contract")
                if contract == "research":
                    label = "Evaluating available material" if event.get("exposed") else _INVESTIGATING
                    self._stage("research_model", label, label)
                elif contract == "answer":
                    self._stage("answer_model", _ANSWERING, _ANSWERING)
            elif action in _STAGES:
                self._stage(action, *_STAGES[action])

    def receive(self, event):
        """Consume acquisition and validation signals kept out of diagnostics."""
        action = event.get("action")
        with self._lock:
            if action == "answer_validation_started":
                if self._current != _STAGES[action][1]:
                    self._stage(action, *_STAGES[action])
            elif action == "answer_dispatch_started":
                if self._current != _ANSWERING:
                    self._stage("answer_model", _ANSWERING, _ANSWERING)
            elif action in {"answer_inspection_started", "answer_inspection_finished"}:
                self._inspection(event, action)
            else:
                self._acquisition(event, action)

    def _inspection(self, event, action):
        if action.endswith("_started"):
            self._stage("answer_inspection", _INSPECTING, _INSPECTING)
        else:
            label = "Retained material unavailable"
            if event.get("status") == "ok":
                label = "Inspected retained material" if _count(event, "material_count") else "No retained matches"
            self._record("answer_inspection_result", label, stage=_ANSWERING, **_duration(event))

    def _acquisition(self, event, action):
        route = event.get("route_index")
        request = event.get("request_index")
        group = event.get("group_index")
        if type(route) is not int or (type(group) is not int and type(request) is not int):
            return
        activity_id = f"{route}:group:{group}" if type(group) is int else f"{route}:request:{request}"
        kind = event.get("kind")
        if kind in {"search", "search_lexical"} or action in {"search_batch_started", "search_batch_finished"}:
            self._search(event, action, activity_id)
        elif kind in {"read", "find"}:
            self._read(event, action, activity_id)

    def _search(self, event, action, activity_id):
        group = type(event.get("group_index")) is int
        stage = "Running parallel searches" if group else "Searching the web"
        if action == "search_batch_started":
            return  # The first actual dispatch is the first user-visible search.
        if action not in {"search_dispatched", "acquisition_finished", "search_batch_finished"}:
            return
        searches = self._searches.setdefault(activity_id, {})
        if action != "search_batch_finished":
            request = event["request_index"]
            previous = searches.get(request, {})
            provider = _PROVIDERS.get(event.get("provider"))
            if action == "search_dispatched":
                query = event.get("query")
                if not isinstance(query, str) or not query:
                    return
                mode = _SEARCH_TYPES.get(event.get("search_type"))
                previous = {
                    "label": f"{mode} search" if mode else "Web search",
                    "query": query[:QUERY_CHARACTERS], "query_truncated": len(query) > QUERY_CHARACTERS,
                    "outcome": "Searching",
                }
            else:
                previous = {
                    **previous,
                    "label": previous.get("label", "Web search"),
                    "outcome": self._search_outcome(event),
                    **_duration(event),
                }
                if event.get("status") == "ok":
                    previous.update(candidates=_count(event, "candidate_count"),
                                    highlights=_count(event, "highlight_count"))
            if provider:
                previous["provider"] = provider
            searches[request] = previous

        operations = list(dict(sorted(searches.items())).values())
        done = action == ("search_batch_finished" if group else "acquisition_finished")
        if done:
            self._searches.pop(activity_id)
        elif not any("query" in operation for operation in operations):
            return
        label = self._search_summary(operations, group) if done else stage
        self._record("search", label, stage=_INVESTIGATING if done else stage,
                     activity_id=activity_id, operations=operations, **_duration(event))

    @staticmethod
    def _search_outcome(event):
        if event.get("status") == "unavailable":
            return "Search unavailable"
        if event.get("status") != "ok":
            return "Search failed"
        if not _count(event, "new_candidate_count") and not _count(event, "new_material_count"):
            return "No new links or highlights"
        return "Search returned"

    @staticmethod
    def _search_summary(operations, group):
        successful = [operation for operation in operations if "candidates" in operation]
        if not successful:
            if not group and operations:
                return operations[0]["outcome"]
            return "Parallel searches could not complete"
        if not group and successful[0]["outcome"] == "No new links or highlights":
            return "Search returned no new links or highlights"
        candidates = sum(item["candidates"] for item in successful)
        highlights = sum(item["highlights"] for item in successful)
        lead = _amount(len(successful), "search returned", "searches returned") if group else "Search returned"
        label = f"{lead} {_amount(candidates, 'candidate link', 'candidate links')}"
        if highlights:
            label += f", with source highlights in {_amount(highlights, 'result', 'results')}"
        if len(successful) < len(operations):
            count = len(operations) - len(successful)
            label += f". {_amount(count, 'search could not complete', 'searches could not complete')}"
        return label

    def _read(self, event, action, activity_id):
        if action not in {"acquisition_started", "acquisition_finished"}:
            return
        external = event.get("external") is True
        fields = _source_fields(event)
        stage = _RETRIEVING if external else _INSPECTING
        started = action == "acquisition_started"
        if started:
            label = stage
        elif event.get("original_text_retrieved") is True:
            label = "Retrieved original source text"
        elif event.get("status") == "ok":
            label = "Inspected retained material" if _count(event, "material_count") else "No retained matches"
        elif external:
            label = "Source retrieval unavailable" if event.get("status") == "unavailable" else "Could not retrieve source"
        else:
            label = "Retained material unavailable"
        provider = _PROVIDERS.get(event.get("provider"))
        if provider and external:
            fields["provider"] = provider
        if event.get("read_providers") == ("linkup", "exa"):
            fields["provider"] = "LinkUp and Exa"
        self._record("retrieval" if external else "local_inspection", label,
                     stage=stage if started else _INVESTIGATING, activity_id=activity_id,
                     operations=[{"label": "Source retrieval" if external else "Retained material",
                                  "outcome": label, **fields, **_duration(event)}], **_duration(event))


def activity_response(snapshot, *, clock=_utc_now):
    """The saved job row owns terminal state, including after a restart."""
    state = snapshot["state"]
    last = snapshot["last_event"]
    label = _JOB_LABELS[state]
    since = snapshot["started_at"] or snapshot["created_at"]
    sequence = 0
    if state == "researching" and last and last.get("current"):
        label = last["current"]
        since = last.get("current_since") or since
        sequence = last.get("current_id", 0)
    end = clock()
    if snapshot["finished_at"] is not None:
        end = datetime.fromisoformat(snapshot["finished_at"])
    return {
        "state": state, "current": {"label": label, "elapsed_seconds": _elapsed(since, end), "sequence": sequence},
        "events": [
            {"sequence": row["seq"], **{key: row[key] for key in (
                "label", "activity_id", "operations", "elapsed_seconds",
            ) if key in row}}
            for row in snapshot["events"]
        ],
        **{key: snapshot[key] for key in ("cursor", "first_cursor", "reset", "truncated", "available")},
    }
