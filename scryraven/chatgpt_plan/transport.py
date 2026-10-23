"""Completed Responses objects for the explicitly selected ChatGPT-plan route.

All stream items, including opaque reasoning/function continuation items, remain
in memory. Only the ordinary model entrypoint interprets the completed result.
No request, output envelope, credential or reasoning is written to disk here.
"""
from __future__ import annotations

import copy

import requests

from scryraven.model import _counter

from .auth import Auth, Deadline
from .http import RESPONSES, PlanError, failure, response_deadline
from .streaming import _headerless_chunks, _nonstream_diagnostics, events


def plan_payload(payload):
    """Preserve native text/schema/tools; adapt only documented transport fields.

    `additional_tools` is the documented alternative to namespaced tools. It
    keeps production tools' exact unnamespaced names and strict schemas.
    Its position remains before the first response item across continuations.
    """
    body = copy.deepcopy(payload)
    for name in ("max_output_tokens", "service_tier", "prompt_cache_key", "prompt_cache_options"):
        body.pop(name, None)
    body["store"], body["stream"] = False, True
    for item in body["input"]:
        content = item.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block.pop("prompt_cache_breakpoint", None)
    tools = body.pop("tools", None)
    if tools:
        item = {"type": "additional_tools", "role": "developer", "tools": tools}
        position = next((i for i, value in enumerate(body["input"])
                         if value.get("type") in {"reasoning", "function_call", "function_call_output"}
                         or value.get("role") == "assistant"), len(body["input"]))
        body["input"].insert(position, item)
    return body


def _safe_usage(body):
    """Only known integer counters may survive a failed physical request."""
    usage = {}
    for name in ("input_tokens", "output_tokens", "total_tokens"):
        value = _counter(body, "usage", name)
        if value is not None:
            usage[name] = value
    for group, names in (("input_tokens_details", ("cached_tokens", "cache_write_tokens")),
                         ("output_tokens_details", ("reasoning_tokens",))):
        counters = {name: value for name in names
                    if (value := _counter(body, "usage", group, name)) is not None}
        if counters:
            usage[group] = counters
    return usage


class _Output:
    """Reconcile indexed output items/deltas without inventing message boundaries."""
    def __init__(self):
        self.items, self.ids, self.text, self.arguments = {}, {}, {}, {}
        self.closed, self.verified, self.done_text, self.done_arguments = set(), set(), set(), set()
        self.sequence = -1

    @staticmethod
    def invalid():
        raise PlanError("malformed_model_response", reason="conflicting_stream_output")

    @staticmethod
    def index(value):
        if type(value) is not int or value < 0:
            raise PlanError("malformed_model_response", reason="invalid_output_location")
        return value

    def item(self, index, identity=None):
        index = self.index(index)
        item = self.items.setdefault(index, {})
        if identity is not None:
            if not isinstance(identity, str) or not identity:
                self.invalid()
            if item.get("id", identity) != identity or self.ids.get(identity, index) != index:
                self.invalid()
            self.ids[identity] = index
            item["id"] = identity
        return item

    def snapshot_text(self, index, part, kind, value, *, done=True):
        if not isinstance(value, str):
            self.invalid()
        key = (index, self.index(part), kind)
        if any(number == index and location == part and other != kind
               for number, location, other in self.text):
            self.invalid()
        old = self.text.get(key)
        if old is not None and old != value:
            self.invalid()
        self.text[key] = value
        if done:
            self.done_text.add(key)

    def snapshot_arguments(self, index, value, *, done=True):
        if not isinstance(value, str) or index in self.arguments and self.arguments[index] != value:
            self.invalid()
        self.arguments[index] = value
        if done:
            self.done_arguments.add(index)

    def snapshot(self, index, value, *, final):
        if not isinstance(value, dict):
            self.invalid()
        if index in self.closed and not final:
            self.invalid()
        item = self.item(index, value.get("id"))
        if value.get("id") is not None:
            self.verified.add(index)
        for key in ("type", "role", "phase", "name", "call_id", "namespace"):
            if key in value and key in item and item[key] != value[key]:
                self.invalid()
        if value.get("type") not in {"message", "reasoning", "function_call"}:
            self.invalid()
        # Empty added snapshots are normal. Final snapshots must agree with
        # actual streamed text/arguments rather than append a duplicate copy.
        if value.get("type") == "message":
            if value.get("role") != "assistant":
                self.invalid()
            content = value.get("content", [])
            if not isinstance(content, list):
                self.invalid()
            for number, part in enumerate(content):
                if not isinstance(part, dict):
                    self.invalid()
                kind = part.get("type")
                if kind in {"output_text", "refusal"}:
                    text = part.get("text" if kind == "output_text" else "refusal")
                    if final or text:
                        self.snapshot_text(index, number, kind, text, done=final)
            if final and any(number == index and part >= len(content) for number, part, _kind in self.text):
                self.invalid()
        elif value.get("type") == "function_call" and (final or value.get("arguments")):
            self.snapshot_arguments(index, value.get("arguments"), done=final)
        item.update(copy.deepcopy(value))
        if final:
            self.closed.add(index)

    def observe(self, event):
        if "sequence_number" in event:
            sequence = self.index(event["sequence_number"])
            if sequence <= self.sequence:
                self.invalid()
            self.sequence = sequence
        kind = event["type"]
        if kind in {"response.output_item.added", "response.output_item.done"}:
            self.snapshot(self.index(event.get("output_index")), event.get("item"),
                          final=kind.endswith(".done"))
        elif kind in {"response.output_text.delta", "response.refusal.delta"}:
            index = self.index(event.get("output_index"))
            if index in self.closed:
                self.invalid()
            item = self.item(index, event.get("item_id"))
            if item.get("type", "message") != "message":
                self.invalid()
            item.setdefault("type", "message")
            item.setdefault("role", "assistant")
            part_kind = "output_text" if "output_text" in kind else "refusal"
            key = (index, self.index(event.get("content_index")), part_kind)
            if key in self.done_text or any(number == index and part == key[1] and other != part_kind
                                           for number, part, other in self.text):
                self.invalid()
            delta = event.get("delta")
            if not isinstance(delta, str):
                self.invalid()
            self.text[key] = self.text.get(key, "") + delta
        elif kind in {"response.output_text.done", "response.refusal.done"}:
            index = self.index(event.get("output_index"))
            if index in self.closed:
                self.invalid()
            item = self.item(index, event.get("item_id"))
            item.setdefault("type", "message")
            item.setdefault("role", "assistant")
            part_kind = "output_text" if "output_text" in kind else "refusal"
            self.snapshot_text(index, event.get("content_index"), part_kind,
                               event.get("text" if part_kind == "output_text" else "refusal"))
        elif kind in {"response.content_part.added", "response.content_part.done"}:
            index = self.index(event.get("output_index"))
            if index in self.closed:
                self.invalid()
            self.item(index, event.get("item_id"))
            part = event.get("part")
            if not isinstance(part, dict):
                self.invalid()
            part_kind = part.get("type")
            if part_kind in {"output_text", "refusal"}:
                value = part.get("text" if part_kind == "output_text" else "refusal")
                if kind.endswith(".done") or value:
                    self.snapshot_text(index, event.get("content_index"), part_kind, value,
                                       done=kind.endswith(".done"))
        elif kind in {"response.function_call_arguments.delta", "response.function_call_arguments.done"}:
            index = self.index(event.get("output_index"))
            if index in self.closed or kind.endswith(".delta") and index in self.done_arguments:
                self.invalid()
            item = self.item(index, event.get("item_id"))
            if item.get("type", "function_call") != "function_call":
                self.invalid()
            item.setdefault("type", "function_call")
            if kind.endswith(".done"):
                self.snapshot_arguments(index, event.get("arguments"))
            else:
                delta = event.get("delta")
                if not isinstance(delta, str):
                    self.invalid()
                self.arguments[index] = self.arguments.get(index, "") + delta

    def completed(self, response, model, *, allowed_names):
        if (not isinstance(response, dict) or response.get("status") != "completed"
                or response.get("model") != model or not isinstance(response.get("output"), list)
                or response.get("error") is not None or response.get("incomplete_details") is not None):
            raise PlanError("malformed_model_response", reason="invalid_completed_response")
        for index, item in enumerate(response["output"]):
            self.snapshot(index, item, final=True)
        if response["output"] and any(index >= len(response["output"]) for index in self.items):
            self.invalid()
        if not response["output"] and (any(index not in self.verified or index not in self.closed for index in self.items)
                                       or any(key not in self.done_text for key in self.text)):
            self.invalid()
        if self.items and set(self.items) != set(range(max(self.items) + 1)):
            self.invalid()
        output = []
        for index, value in sorted(self.items.items()):
            item = copy.deepcopy(value)
            if item.get("type") == "message":
                parts = {part: (kind, text) for (number, part, kind), text in self.text.items() if number == index}
                if parts:
                    if set(parts) != set(range(max(parts) + 1)):
                        self.invalid()
                    original = item.get("content", [])
                    content = []
                    for number, (kind, text) in sorted(parts.items()):
                        part = copy.deepcopy(original[number]) if number < len(original) else {"type": kind}
                        part.update(type=kind, **{"text" if kind == "output_text" else "refusal": text})
                        content.append(part)
                    item["content"] = content
                item.setdefault("content", [])
            elif item.get("type") == "function_call":
                if (item.get("name") not in allowed_names
                        or item.get("namespace") not in (None, "")):
                    raise PlanError("malformed_model_response", reason="undeclared_function_call")
                if index in self.arguments:
                    item["arguments"] = self.arguments[index]
            elif item.get("type") != "reasoning":
                self.invalid()
            output.append(item)
        return {**response, "output": output}


class PlanResponses:
    """One physical streaming request; no retry, fallback, publication or logging."""
    def __init__(self, account="personal", *, auth=None):
        self.account = account
        self.auth = auth if auth is not None else Auth()
        self.physical_requests = 0

    def request(self, payload, *, timeout, before_dispatch=None):
        body, deadline = plan_payload(payload), Deadline(timeout)
        response, last_body = None, None
        try:
            row = self.auth.access(self.account, timeout=deadline.left())
            headers = {"Authorization": "Bearer " + row["access_token"], "Accept": "text/event-stream"}
            request = self.auth.http.request
            request_timeout = deadline.left()
            if before_dispatch is not None:
                request_timeout = min(request_timeout, before_dispatch())
            self.physical_requests += 1
            response = request(
                "POST", RESPONSES, timeout=request_timeout, stream=True,
                headers=headers,
                json=body,
            )
            with response_deadline(response, deadline.left()):
                if response.status_code != 200:
                    error = failure(response.status_code, None)
                    error.diagnostic.update(_nonstream_diagnostics(response, deadline))
                    raise error
                media = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                chunks = None
                if not media:
                    chunks = _headerless_chunks(response, deadline, {})
                elif media != "text/event-stream":
                    raise PlanError("malformed_model_response", reason="expected_event_stream")
                stream = _Output()
                for event in events(response, deadline, chunks=chunks):
                    kind = event["type"]
                    if isinstance(event.get("response"), dict):
                        last_body = event["response"]
                    # Terminal events share the same verified monotonic sequence
                    # as deltas and item snapshots, including empty-output stops.
                    stream.observe(event)
                    if kind == "response.completed":
                        return stream.completed(last_body, body["model"], allowed_names={
                            tool["name"] for tool in payload.get("tools", []) if tool.get("type") == "function"})
                    if kind == "response.incomplete":
                        if not isinstance(last_body, dict) or last_body.get("status") != "incomplete":
                            raise PlanError("malformed_model_response", reason="invalid_incomplete_response")
                        return last_body
                    if kind in {"response.failed", "error"}:
                        raise failure(None, {"error": event} if kind == "error" else last_body)
        except requests.Timeout:
            raise PlanError("model_request_timed_out") from None
        except requests.RequestException:
            raise PlanError("model_transport_failed") from None
        except PlanError as error:
            error.usage = _safe_usage(last_body)
            raise
        finally:
            if response is not None:
                response.close()
