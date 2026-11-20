"""Opt-in AID-10 comparison using ScryRaven's ordinary local research session."""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from scryraven import research
from scryraven.errors import RunError
from scryraven.model import OpenAIModel
from scryraven.run_settings import RunSettings
from scryraven.session import ResearchSession

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "8ecf38816a0aea2f146c5af0b600e28decc2a66f"  # pragma: allowlist secret
CASE_DIGEST = "2d19f8b89fa1c23aedda269bbba53644bd2066eea807afeafa1c241487d5a470"  # pragma: allowlist secret
ARMS = ("control", "hardened")
PHASES = ("diagnostic-development", "diagnostic-reserved", "luna-reserved", "luna-repeat")

RESEARCH_GUIDANCE = """\

# Before handing off
For each material part of the question, connect the finding in the briefing to
the exact original text that establishes it. When a plausible lookalike,
condition, exception or version could change the conclusion, check the
applicable source text and select the passage that resolves the distinction
alongside the result. If the current material only points to a decisive source,
follow that lead when it can resolve the gap. Carry the specific unresolved
part and its best available support forward when it cannot be resolved.
"""

ANSWER_GUIDANCE = """\

# Before finalizing
Check that the response covers each material requested part. For decisive
external claims, confirm that the cited passage supports the claim for the
same entity, version, conditions and quantitative basis. Keep qualifications
next to the claims they change. If a supporting passage is missing, inspect
the retained original or delegate the specific need when it is recoverable.
Where a gap remains, give the established result at its warranted scope and
identify the requested part that the evidence leaves open.
"""

FATAL_CONFIGURATION_CODES = {
    "model_access_denied",
    "model_authentication_failed",
    "model_backend_incompatible",
    "model_configuration_missing",
    "model_contract_incompatible",
    "model_request_rejected",
    "model_unavailable",
}
TIMEOUT_CODES = {"deadline", "model_request_timed_out"}


def case_digest(manifest: bytes) -> str:
    return sha256(manifest).hexdigest()


def load_cases(path: Path) -> list[dict]:
    manifest = path.read_bytes()
    if case_digest(manifest) != CASE_DIGEST:
        raise ValueError("case manifest does not match the AID-10 freeze")
    return json.loads(manifest)["cases"]


def phase_cases(cases: list[dict], phase: str) -> list[dict]:
    if phase == "diagnostic-development":
        return [case for case in cases if case["split"] == "development"]
    reserved = [case for case in cases if case["split"] == "reserved"]
    if phase == "diagnostic-reserved":
        return [case for case in reserved if case["diagnostic"]]
    if phase == "luna-repeat":
        return [case for case in reserved if case["repeat"]]
    return reserved


def settings(phase: str) -> RunSettings:
    luna_only = phase.startswith("luna-")
    return RunSettings(
        backend="openai",
        research_model="gpt-6-luna",
        research_reasoning="high",
        answer_model="gpt-6-luna" if luna_only else "gpt-6.2-sol",
        answer_reasoning="medium",
        api_processing="standard",
        physical_request_limit=40,
    )


def prompts(phase: str, arm: str) -> dict[str, str]:
    ordinary = {
        "RESEARCH_PROMPT": research.RESEARCH_PROMPT,
        "DELEGATED_RESEARCH_PROMPT": research.DELEGATED_RESEARCH_PROMPT,
        "ANSWER_PROMPT": research.ANSWER_PROMPT,
    }
    if arm == "hardened":
        ordinary["RESEARCH_PROMPT"] += RESEARCH_GUIDANCE
        ordinary["DELEGATED_RESEARCH_PROMPT"] += RESEARCH_GUIDANCE
        if phase.startswith("luna-"):
            ordinary["ANSWER_PROMPT"] += ANSWER_GUIDANCE
    return ordinary


def receipt_issues(usage: list, config: RunSettings) -> set[str]:
    issues = set()
    expected = {"research": config.research_model, "answer": config.answer_model}
    for call in usage:
        if call.backend != "api" or call.model != expected.get(call.stage):
            issues.add("unexpected_dispatch_role")
        if call.returned_model is None or call.returned_service_tier is None:
            issues.add("missing_model_or_tier_receipt")
        if call.returned_model is not None and call.returned_model != expected.get(call.stage):
            issues.add("returned_model_mismatch")
        if (call.requested_service_tier != "default"
                or call.returned_service_tier not in {None, "default"}):
            issues.add("standard_tier_mismatch")
    if not expected.keys() <= {call.stage for call in usage}:
        issues.add("missing_role_dispatch")
    return issues


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_case(question: str, phase: str, arm: str, *, post=None, **session_options) -> dict:
    config = settings(phase)
    selected_prompts = prompts(phase, arm)
    events, usage = [], []
    model = OpenAIModel(config.model_config(), post=post, usage_observer=usage.append)
    session = ResearchSession(model=model, limits=config.limits(), observe=events.append, **session_options)
    started_at = now()
    outcome, failure = None, None
    # A serial, isolated command supplies the prompt variant at the product seam.
    # Keep the actual OpenAIModel callable: it owns native tool continuations.
    with patch.multiple(research, **selected_prompts):
        try:
            result = session.ask(question)
            outcome = {
                "answer": result.answer,
                "posture": result.posture,
                "stop_reason": result.stop_reason,
                "citations": [asdict(citation) for citation in result.citations],
                "citation_uses": [asdict(use) for use in result.citation_uses],
            }
            # Some citation failures exist only in the returned trace.
            validation_events = [event for event in result.trace if event["stage"] == "citations"]
            events.extend(validation_events)
        except RunError as exc:
            failure = {"stage": exc.stage, "code": exc.code}
            events.extend(event for event in exc.trace if event["stage"] == "citations")
        except Exception:
            # The credentialed command logs only normalized data and fixed errors.
            failure = {"stage": "runtime", "code": "unexpected_runtime_failure"}

    model_issues = receipt_issues(usage, config)
    failures = {event.get("code") for event in events
                if event["action"] in {"model_failed", "research_bound", "research_returned"}}
    if failure:
        failures.add(failure["code"])
    gate_issues = set(model_issues)
    if failures & TIMEOUT_CODES:
        gate_issues.add("timeout")
    if outcome is None:
        gate_issues.add("no_completed_answer")
    elif outcome["posture"] != "supported":
        gate_issues.add(outcome["posture"])
    fatal = failures & FATAL_CONFIGURATION_CODES or model_issues & {
        "returned_model_mismatch", "standard_tier_mismatch", "unexpected_dispatch_role",
    }
    # A completed response with missing receipts cannot verify exact model/tier.
    if outcome and "missing_model_or_tier_receipt" in model_issues and not failures & TIMEOUT_CODES:
        fatal = True
    return {
        "started_at": started_at,
        "finished_at": now(),
        "settings": config.to_dict(),
        "prompt_hashes": {name: sha256(prompt.encode("utf-8")).hexdigest()
                          for name, prompt in selected_prompts.items()},
        "gate_issues": sorted(gate_issues),
        "configuration_stop": bool(fatal),
        "failure": failure,
        "outcome": outcome,
        "usage": [asdict(call) for call in usage],
        "events": events,
    }


def emit(kind: str, **data) -> None:
    print(json.dumps({"kind": kind, **data}, ensure_ascii=True), flush=True)


def clean_revision() -> str:
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tracked = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)
    is_descendant = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE, revision], cwd=ROOT, check=False).returncode == 0
    # Operator or broker credentials live outside this harness. A paid run
    # requires a reproducible checked-in runtime and explicit command approval.
    product_changes = subprocess.check_output(
        ["git", "diff", "--name-only", BASELINE, revision, "--", "scryraven", "core"],
        cwd=ROOT, text=True)
    if tracked or not is_descendant or product_changes:
        raise ValueError("use a clean AID-10 checkout with the frozen product runtime")
    return revision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument("--start", type=int, default=0, help="Zero-based index in the selected frozen phase.")
    parser.add_argument("--count", type=int, required=True, help="Number of consecutive paired cases to authorize.")
    parser.add_argument("--authorized-standard-run", action="store_true",
                        help="Attest this exact local API/provider run and spend were approved.")
    args = parser.parse_args(argv)
    if not args.authorized_standard_run:
        parser.error("paid execution requires explicit --authorized-standard-run")
    try:
        cases = phase_cases(load_cases(args.manifest), args.phase)
        revision = clean_revision()
    except (OSError, subprocess.CalledProcessError, ValueError):
        parser.error("use the frozen manifest and a clean checkout with the frozen product runtime")
    if not 0 <= args.start < args.start + args.count <= len(cases):
        parser.error("--start and --count must select a nonempty range of frozen pairs")

    emit("block_started", mode="live_standard", phase=args.phase, revision=revision, baseline=BASELINE,
         corpus_sha256=CASE_DIGEST, started_at=now(),
         case_ids=[case["id"] for case in cases[args.start:args.start + args.count]])
    for index in range(args.start, args.start + args.count):
        case = cases[index]
        arms = ARMS if (index + (args.phase == "luna-repeat")) % 2 == 0 else ARMS[::-1]
        for arm in arms:
            key = {"phase": args.phase, "case_id": case["id"], "arm": arm}
            emit("turn_started", **key)
            result = run_case(case["question"], args.phase, arm)
            emit("turn_finished", **key, **result)
            if result["configuration_stop"]:
                emit("block_stopped", reason="configuration_or_receipt", finished_at=now())
                return 1
    emit("block_finished", finished_at=now())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
