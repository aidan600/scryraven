"""Development-only frozen Answer screen; invoke live only through the doorman.

This adapter compiles the current ordinary Answer closures directly from
research.py. It replaces only their initial packet construction with a deepcopy
of the frozen packet. The ordinary transport, calculator, deadlines, correction
loop, reading validation and citation finalization remain the production code.
No Research decision or acquisition route executes. Evaluation obligations stay
outside the packet and are never model input.

The packet's historical budget is immutable input. The direct execution has a
fresh ordinary 120-second Answer stage and one validation correction, with every
semantic attempt and underlying Responses request counted in the phase ledger.
This is Answer-stage development evidence, not an ordinary PRODUCT observation.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scryraven import research
from scryraven.acquisition import AcquisitionLibrary
from scryraven.model import ModelConfig, ModelRole, OpenAIModel
from scryraven.presentation import answer_html, render_cli
from scryraven.results import resolve_citations
from scryraven.sources import Evidence

MAX_SEMANTIC_ATTEMPTS = 24
MAX_PROVIDER_REQUESTS = 40
_FUNCTIONS = ("ask", "finish", "finish_answer_validation_failure", "answer_from_sources")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


class ScreenStop(BaseException):
    """A hard operator cap must escape transport's ordinary Exception handling."""


class Journal:
    """One append-only, fsynced phase ledger, shared across all controls/treatments."""

    def __init__(self, path: Path, label: str):
        self.path, self.label = path, label
        self.counts = {"semantic_submitted": 0, "provider_submitted": 0}
        self.prior_labels = set()
        if path.exists():
            # Invalid/truncated journals fail closed; never infer a lower count.
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                kind = record["kind"]
                if kind in self.counts:
                    self.counts[kind] += 1
                if kind == "case_started":
                    self.prior_labels.add(record["label"])

    def append(self, kind: str, **fields: object) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        value = {"kind": kind, "label": self.label, **fields}
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical(value).decode("utf-8") + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def reserve(self, kind: str) -> None:
        cap = {"semantic_submitted": MAX_SEMANTIC_ATTEMPTS,
               "provider_submitted": MAX_PROVIDER_REQUESTS}[kind]
        if self.counts[kind] >= cap:
            self.append("cap_reached", counter=kind, cap=cap)
            raise ScreenStop(kind + "_cap_reached")
        # A durable reservation survives interruption and is never silently retried.
        self.append(kind, ordinal=self.counts[kind] + 1)
        self.counts[kind] += 1


def _forbid_acquisition(*_args, **_kwargs):
    raise ScreenStop("acquisition_forbidden")


def load_packet(path: Path) -> tuple[dict, dict]:
    raw = path.read_bytes()
    envelope = json.loads(raw)
    if not isinstance(envelope, dict) or not isinstance(envelope.get("packet_id"), str):
        raise ValueError("invalid_packet_envelope")
    packet = envelope["packet"]
    required = {"question", "conversation_context", "evidence", "current_date", "phase",
                "acquisition_limitations", "budget"}
    if (set(packet) != required or packet["phase"] != "answer"
            or not isinstance(packet["question"], str) or not packet["question"].strip()
            or not isinstance(packet["evidence"], list)
            or not isinstance(packet["conversation_context"], list)):
        raise ValueError("invalid_frozen_answer_packet")
    info = {"packet_id": envelope["packet_id"], "packet_file_sha256": digest(raw),
            "packet_sha256": digest(canonical(packet)),
            "acquisitions_sha256": digest(canonical(envelope["acquisitions"])),
            "evidence_order": [item["id"] for item in packet["evidence"]],
            "evidence_bodies": [{"id": item["id"], "characters": len(item["content"]),
                                  "sha256": digest(item["content"].encode("utf-8"))}
                                 for item in packet["evidence"]]}
    return envelope, info


def _library(envelope: dict) -> AcquisitionLibrary:
    acquired = [Evidence(**item) for item in envelope["acquisitions"]]
    selected = [Evidence(**item) for item in envelope["packet"]["evidence"]]
    if (len({item.id for item in acquired}) != len(acquired)
            or any(item.acquisition == "targeted_view" for item in acquired)):
        raise ValueError("invalid_frozen_acquisitions")
    # Original IDs may be sparse. Do not renumber them or import unrelated parents
    # to satisfy the ordinary growing library's sequential-allocation constructor.
    library = AcquisitionLibrary(search=_forbid_acquisition,
                                 lexical_search=_forbid_acquisition, fetch=_forbid_acquisition)
    library.acquisitions = acquired
    library.materials = {item.id: item for item in acquired}
    # This production custody check also verifies selected views against exact
    # retained parents and validates canonical source identities.
    resolve_citations("Frozen packet custody check.", selected, acquired, [], require_citation=False)
    library.materials.update({item.id: item for item in selected})
    return library


def extracted_functions() -> tuple[object, dict]:
    path = Path(research.__file__)
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source, filename=str(path))
    owners = [item for item in module.body
              if isinstance(item, ast.FunctionDef) and item.name == "_run_turn"]
    if len(owners) != 1:
        raise ValueError("answer_owner_not_found")
    functions = {item.name: item for item in owners[0].body
                 if isinstance(item, ast.FunctionDef) and item.name in _FUNCTIONS}
    if set(functions) != set(_FUNCTIONS):
        raise ValueError("answer_function_shape_changed")
    hashes = {name: digest(ast.dump(functions[name], include_attributes=False).encode("utf-8"))
              for name in _FUNCTIONS}
    answer = functions["answer_from_sources"]
    initial = answer.body[0]
    if (not isinstance(initial, ast.Assign) or len(initial.targets) != 1
            or not isinstance(initial.targets[0], ast.Name)
            or initial.targets[0].id != "packet" or not isinstance(initial.value, ast.Dict)):
        raise ValueError("answer_packet_constructor_changed")
    keys = {key.value for key in initial.value.keys if isinstance(key, ast.Constant)}
    if keys != {"phase", "evidence", "acquisition_limitations", "budget"}:
        raise ValueError("answer_packet_constructor_changed")
    # The sole production AST edit: fixed inputs replace run-built inputs.
    initial.value = ast.Call(func=ast.Name(id="deepcopy", ctx=ast.Load()),
                             args=[ast.Name(id="frozen_packet", ctx=ast.Load())], keywords=[])
    extracted = ast.Module(body=[functions[name] for name in _FUNCTIONS], type_ignores=[])
    ast.fix_missing_locations(extracted)
    return compile(extracted, str(path), "exec"), {
        "research_file_sha256": digest(path.read_bytes()),
        "production_function_ast_sha256": hashes,
        "adapter_edit": "answer_from_sources initial packet = deepcopy(frozen_packet)",
    }


def execute(envelope: dict, journal: Journal, *, post=None, clock=time.monotonic) -> dict:
    """Run exactly one frozen case; injected post is for offline transport tests."""
    packet = deepcopy(envelope["packet"])
    initial_hash = digest(canonical(packet))
    library = _library(envelope)
    compiled, integrity = extracted_functions()
    trace, events, usage, decisions = [], [], [], []
    request_durations = []
    real_post = post
    if real_post is None:
        import requests
        real_post = requests.post

    class ScreenBudget(research._Budget):
        def before_model(self):
            super().before_model()
            journal.reserve("semantic_submitted")

    # The model sees the exact historical budget in the frozen packet. Execution
    # gets one fresh ordinary 120-second Answer allowance and its one correction;
    # these are separate from the phase-wide submission caps.
    limits = research.RunLimits(semantic_attempts=2, external_attempts=0,
                                seconds=research.ANSWER_STAGE_SECONDS)
    budget = ScreenBudget(limits, clock)

    def gated_post(url, **kwargs):
        payload = kwargs["json"]
        if (url != "https://api.openai.com/v1/responses"
                or payload.get("model") != "gpt-6-sol"
                or payload.get("reasoning") != {"effort": "medium"}
                or payload.get("service_tier") != "fast"
                or payload.get("text", {}).get("format", {}).get("name") != "answer"):
            raise ScreenStop("unexpected_provider_route")
        journal.reserve("provider_submitted")
        started = clock()
        try:
            return real_post(url, **kwargs)
        finally:
            request_durations.append(max(0.0, clock() - started))

    role = ModelRole("gpt-6-sol", "medium", "fast")
    model = OpenAIModel(ModelConfig(answer=role), post=gated_post,
                        usage_observer=lambda item: usage.append(asdict(item)),
                        cache_namespace="scryraven", timeout_seconds=120)

    def emit(action, *, source_body=False, **fields):
        event = {"stage": "research", "action": action, **fields}
        if not source_body:
            trace.append(deepcopy(event))
        events.append({**deepcopy(event), "source_body": source_body})

    namespace = dict(vars(research))
    namespace.update(model=model, model_call_timeout=model.timeout_seconds,
                     budget=budget, limits=limits, clock=clock, emit=emit, trace=trace,
                     library=library, frozen_packet=packet)
    exec(compiled, namespace)
    production_ask = namespace["ask"]

    def observed_ask(stage, prompt, material, shape, **kwargs):
        if stage != "answer":
            raise ScreenStop("research_forbidden")
        observed_packet = {key: value for key, value in material.items()
                           if key != "output_correction"}
        if digest(canonical(observed_packet)) != initial_hash:
            raise ScreenStop("frozen_packet_changed")
        decision = production_ask(stage, prompt, material, shape, **kwargs)
        decisions.append({"attempt": budget.semantic,
                          "correction": deepcopy(material.get("output_correction")),
                          "decision": decision.model_dump() if decision is not None else None})
        return decision

    namespace["ask"] = observed_ask
    record = {"packet_id": envelope["packet_id"], "packet_sha256": initial_hash,
              "question": packet["question"], "model_profile": asdict(role),
              "integrity": integrity,
              "answer_prompt": research.ANSWER_PROMPT,
              "answer_schema": research.AnswerDecision.model_json_schema(),
              "prompt_sha256": digest(research.ANSWER_PROMPT.encode("utf-8")),
              "schema_sha256": digest(canonical(research.AnswerDecision.model_json_schema())),
              "structured_attempts": decisions, "events": events, "usage": usage,
              "provider_request_seconds": request_durations,
              "execution_scope": "direct frozen Answer development; no ordinary PRODUCT run",
              "execution_limits": {"answer_stage_seconds": research.ANSWER_STAGE_SECONDS,
                                   "semantic_attempts_per_packet": 2,
                                   "phase_semantic_attempts": MAX_SEMANTIC_ATTEMPTS,
                                   "phase_provider_requests": MAX_PROVIDER_REQUESTS},
              "ordinary_research_runs": 0, "acquisition_calls": 0}
    started = clock()
    before = dict(journal.counts)
    try:
        final = namespace["answer_from_sources"](
            [item["id"] for item in packet["evidence"]], packet["acquisition_limitations"])
        record["decision"] = final.model_dump()
        reason = "supported" if final.posture == "supported" else "not_established"
        result = namespace["finish"](final, [item["id"] for item in packet["evidence"]], reason)
        record.update(status="completed", result=asdict(result),
                      rendered_html=answer_html(result), rendered_cli=render_cli(result))
    except research._Bound as exc:
        result = namespace["finish_answer_validation_failure"]()
        record.update(status="validation_exhausted", code=exc.code, result=asdict(result),
                      rendered_html=answer_html(result), rendered_cli=render_cli(result))
    except research.RunError as exc:
        record.update(status="run_error", stage=exc.stage, code=exc.code, trace=exc.trace)
    except ScreenStop as exc:
        record.update(status="screen_stopped", code=str(exc))
    except Exception as exc:
        # Unexpected exception text may contain sensitive transport details.
        record.update(status="harness_error", code=type(exc).__name__)
    finally:
        record["seconds"] = max(0.0, clock() - started)
        record["submissions"] = {kind: journal.counts[kind] - before[kind] for kind in before}
        record["phase_totals"] = dict(journal.counts)
        record["packet_unchanged"] = digest(canonical(packet)) == initial_hash
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--preflight-readonly", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", args.label):
        raise ValueError("invalid_label")
    envelope, info = load_packet(args.packet)
    _library(envelope)
    _, integrity = extracted_functions()
    if args.preflight_readonly:
        print(json.dumps({"status": "preflight_valid", **info, "integrity": integrity,
                          "provider_requests": 0}, ensure_ascii=True), flush=True)
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.journal.parent.mkdir(parents=True, exist_ok=True)
    lock = args.journal.with_name(args.journal.name + ".lock")
    with lock.open("x", encoding="ascii") as handle:
        handle.write(str(os.getpid()) + "\n")
    try:
        journal = Journal(args.journal, args.label)
        output = args.output_dir / (args.label + ".json")
        if args.label in journal.prior_labels or output.exists():
            raise ValueError("label_already_submitted")
        journal.append("case_started", packet_id=envelope["packet_id"], **{
            key: info[key] for key in ("packet_file_sha256", "packet_sha256")})
        record = execute(envelope, journal)
        record.update(label=args.label, frozen_input=info,
                      harness_sha256=digest(Path(__file__).read_bytes()),
                      code_sha256={name: digest((REPO / name).read_bytes()) for name in (
                          "scryraven/research.py", "scryraven/model.py", "scryraven/calculator.py",
                          "scryraven/results.py", "scryraven/presentation.py")})
        revision = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                  check=True, capture_output=True, text=True).stdout.strip()
        record["revision"] = revision
        record["packet_file_unchanged"] = digest(args.packet.read_bytes()) == info["packet_file_sha256"]
        write_json(output, record)
        journal.append("case_finished", status=record["status"], output_sha256=digest(output.read_bytes()))
        print(json.dumps({"label": args.label, "status": record["status"],
                          "packet_id": envelope["packet_id"], "output": str(output.resolve()),
                          "submissions": record["submissions"], "phase_totals": record["phase_totals"]},
                         ensure_ascii=True), flush=True)
        return 0 if record["status"] == "completed" else 2
    finally:
        lock.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError):
        print('{"status":"harness_preflight_failed"}', flush=True)
        raise SystemExit(2) from None
