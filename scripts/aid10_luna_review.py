"""Prepare independent blind review, then score complete AID-10 phase logs offline."""
from __future__ import annotations

import argparse
import json
import math
import secrets
from collections import Counter
from hashlib import sha256
from pathlib import Path

from scripts.aid10_luna import (
    ARMS,
    BASELINE,
    CASE_DIGEST,
    PHASES,
    load_cases,
    phase_cases,
    prompts,
    settings,
)

DEFECTS = {
    "unsupported_claim", "citation", "omission", "lookalike",
    "unwarranted_certainty", "inference_or_calculation", "other_material",
}
FAILURE_OWNERS = {
    "provider_access", "research_acquisition", "research_interpretation",
    "research_handoff", "answer_synthesis", "answer_citation", "runtime", "unknown",
}


def collect(cases: list[dict], phase: str, blocks: list[list[dict]]) -> tuple[str, dict]:
    case_ids = {case["id"] for case in cases}
    revisions = set()
    turns = {}
    for header, *records in blocks:
        scheduled = header.get("case_ids", [])
        if (header.get("kind") != "block_started" or header.get("mode") != "live_standard"
                or header.get("phase") != phase or header.get("baseline") != BASELINE
                or header.get("corpus_sha256") != CASE_DIGEST
                or not scheduled or not set(scheduled) <= case_ids):
            raise ValueError("block metadata does not match the frozen phase")
        revisions.add(header["revision"])
        for row in records:
            if row["kind"] in {"block_stopped", "block_finished"}:
                break
            key = row["case_id"], row["arm"]
            if row["phase"] != phase or key[0] not in scheduled or key[1] not in ARMS:
                raise ValueError("turn is outside the frozen block")
            if row["kind"] == "turn_started" and key not in turns:
                turns[key] = None
            elif row["kind"] == "turn_finished" and key in turns and turns[key] is None:
                expected_prompts = {name: sha256(value.encode("utf-8")).hexdigest()
                                    for name, value in prompts(phase, key[1]).items()}
                if row["settings"] != settings(phase).to_dict() or row["prompt_hashes"] != expected_prompts:
                    raise ValueError("turn provenance does not match the frozen settings and prompts")
                turns[key] = row
            else:
                raise ValueError("duplicate or unsolicited turn record")
    if len(revisions) != 1 or {case for case, _ in turns} != case_ids:
        raise ValueError("review requires one tested revision and all frozen pairs to have begun")
    return revisions.pop(), turns


def blind(cases: list[dict], turns: dict) -> tuple[list[dict], list[dict]]:
    packet, mapping = [], []
    for case in cases:
        for arm in ARMS:
            key = case["id"], arm
            turn = turns.get(key)
            outcome = turn["outcome"] if turn else None
            review_id = secrets.token_hex(16)
            mapping.append({
                "review_id": review_id,
                "case_id": key[0],
                "category": case["category"],
                "arm": arm,
                "gate_issues": turn["gate_issues"] if turn else ["interrupted_pair"],
                "needs_review": outcome is not None,
            })
            if outcome is not None:
                # Use human-visible fields and exact saved citation evidence.
                packet.append({
                    "review_id": review_id,
                    "question": case["question"],
                    "obligation": case["obligation"],
                    "primary_targets": case["primary_targets"],
                    "answer": outcome["answer"],
                    "posture": outcome["posture"],
                    "citations": outcome["citations"],
                    "citation_uses": outcome["citation_uses"],
                })
    secrets.SystemRandom().shuffle(packet)
    return packet, mapping


def interval(accepted: int, attempted: int) -> list[float]:
    z = 1.95996398454
    p = accepted / attempted
    scale = 1 + z * z / attempted
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * attempted)) / attempted)
    lower = (p + z * z / (2 * attempted) - margin) / scale
    upper = (p + z * z / (2 * attempted) + margin) / scale
    return [round(max(0, lower), 6), round(min(1, upper), 6)]


def aggregate(rows: list[dict]) -> dict:
    arms = {}
    for arm in ARMS:
        subset = [row for row in rows if row["arm"] == arm]
        passed = sum(row["passed"] for row in subset)
        failures = [row for row in subset if not row["passed"]]
        arms[arm] = {
            "accepted": passed,
            "attempted": len(subset),
            "interval_95_wilson": interval(passed, len(subset)),
            "defects": dict(Counter(flag for row in failures for flag in row["defects"])),
            "execution_issues": dict(Counter(flag for row in failures for flag in row["gate_issues"])),
            "failure_owners": dict(Counter(row["owner"] for row in failures)),
        }
    pairs = {row["case_id"]: {} for row in rows}
    for row in rows:
        pairs[row["case_id"]][row["arm"]] = row["passed"]
    improved = [case_id for case_id, pair in pairs.items() if pair["hardened"] and not pair["control"]]
    regressed = [case_id for case_id, pair in pairs.items() if pair["control"] and not pair["hardened"]]
    return {"arms": arms, "improved": improved, "regressed": regressed}


def validate_review(review: dict, expected: set[str]) -> None:
    if set(review["verdicts"]) != expected or not review["reviewer"].strip():
        raise ValueError("review does not cover exactly its assigned IDs")
    for verdict in review["verdicts"].values():
        defects = verdict["defects"]
        if (type(verdict["acceptable"]) is not bool or not verdict["rationale"].strip()
                or not isinstance(defects, list) or not set(defects) <= DEFECTS
                or verdict["acceptable"] == bool(defects)):
            raise ValueError("invalid review verdict")


def score(mapping: list[dict], reviews: list[dict], ownership: dict) -> dict:
    expected = {row["review_id"] for row in mapping if row["needs_review"]}
    first, second, *adjudication = reviews
    if len({review["reviewer"] for review in reviews}) != len(reviews):
        raise ValueError("independent reviewers must have distinct identifiers")
    for review in (first, second):
        validate_review(review, expected)
    a, b = first["verdicts"], second["verdicts"]
    disputed = {key for key in expected if (a[key]["acceptable"] != b[key]["acceptable"]
                                           or set(a[key]["defects"]) != set(b[key]["defects"]))}
    decisions = {}
    if disputed or adjudication:
        if len(adjudication) != 1:
            raise ValueError("disputed reviews require a third blinded verdict")
        validate_review(adjudication[0], disputed)
        decisions = adjudication[0]["verdicts"]
    rows = []
    failures = set()
    for entry in mapping:
        key = entry["review_id"]
        verdict = decisions.get(key, a.get(key, {}))
        passed = verdict.get("acceptable", False) and not entry["gate_issues"]
        owner = ownership.get(key, {})
        if owner and (passed or owner.get("owner") not in FAILURE_OWNERS
                      or not owner.get("evidence", "").strip()):
            raise ValueError("failure ownership requires a valid owner and evidence reference")
        if not passed:
            failures.add(key)
        rows.append({**entry, "passed": passed, "defects": sorted(set(verdict.get("defects", []))),
                     "owner": owner.get("owner", "unknown") if not passed else None,
                     "ownership_evidence": owner.get("evidence")})
    if not ownership.keys() <= failures:
        raise ValueError("ownership references an unknown or accepted review ID")
    categories = sorted({row["category"] for row in rows})
    return {"overall": aggregate(rows),
            "categories": {name: aggregate([row for row in rows if row["category"] == name])
                           for name in categories},
            "reviewed_outcomes": len(expected), "disputed_outcomes": len(disputed), "rows": rows}


def read_block(path: Path) -> list[dict]:
    # A process killed while emitting a turn may leave an incomplete final line.
    complete, _, _ = path.read_text(encoding="utf-8").rpartition("\n")
    records = [json.loads(line) for line in complete.splitlines()]
    if not records:
        raise ValueError("block log has no complete header")
    return records


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    blinder = commands.add_parser("blind")
    blinder.add_argument("--manifest", type=Path, required=True)
    blinder.add_argument("--phase", choices=PHASES, required=True)
    blinder.add_argument("--logs", type=Path, nargs="+", required=True)
    blinder.add_argument("--packet", type=Path, required=True)
    blinder.add_argument("--key", type=Path, required=True)
    scorer = commands.add_parser("score")
    scorer.add_argument("--key", type=Path, required=True)
    scorer.add_argument("--reviews", type=Path, nargs="+", required=True)
    scorer.add_argument("--ownership", type=Path)
    scorer.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "blind":
            cases = phase_cases(load_cases(args.manifest), args.phase)
            blocks = [read_block(log) for log in args.logs]
            revision, turns = collect(cases, args.phase, blocks)
            packet, key = blind(cases, turns)
            if args.packet.resolve() == args.key.resolve() or args.packet.exists() or args.key.exists():
                raise ValueError("blind packet and private key require distinct new paths")
            save(args.packet, packet)
            save(args.key, {"revision": revision, "phase": args.phase, "key": key})
        else:
            if len(args.reviews) not in {2, 3}:
                raise ValueError("provide two reviewers and an adjudicator when required")
            key = read(args.key)
            reviews = [read(path) for path in args.reviews]
            ownership = read(args.ownership) if args.ownership else {}
            report = score(key["key"], reviews, ownership)
            save(args.report, {"revision": key["revision"], "phase": key["phase"], **report})
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
