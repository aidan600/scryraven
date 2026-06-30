from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import ag_live_semantic_support_coverage_01 as semantic_harness  # noqa: E402
from scripts import ag_live_source_survival_fetch_read_custody_01 as source_harness  # noqa: E402

PHASE = "AG-LIVE-ANSWER-BEARING-BOUNDING-REPAIR-01"
MODE = "REPAIR"
REPAIR_VERDICT_TARGET = "YES"
PROOF_CLASS = "live_component_proof with offline phase-focus regression guards"
PRODUCT_FACING_PROGRESS_TYPE = "product-path repair of bounded source-content selection"
NAMED_DEFECT = (
    "PR #359 failed at gate_5_evidence_relative_analysis_proposal with "
    "semantic_support_fail_source_content_insufficient because the #358 bounded "
    "readable content retained a prefix rather than a coherent answer-bearing "
    "window for the target component."
)
TARGET_COMPONENT = "adult U.S. passport book renewal fee"
TARGET_CLAIM_UNDER_TEST = "adult U.S. passport book renewal fee is $130"
SELECTED_URL = "https://travel.state.gov/en/passports/apply/help/fees.html"
SELECTED_DOMAIN = "travel.state.gov"
OLD_359_FAILURE_GATE = "gate_5_evidence_relative_analysis_proposal"
OLD_359_FAILURE_RESULT = "semantic_support_fail_source_content_insufficient"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "ag_live_answer_bearing_bounding_repair_01"
DEFAULT_OLD_SOURCE_PACKET = (
    ROOT / "output" / "ag_live_source_survival_fetch_read_custody_01" / "source_survival_packet.json"
)
DEFAULT_OLD_SEMANTIC_PACKET = (
    ROOT / "output" / "ag_live_semantic_support_coverage_01" / "semantic_support_coverage_packet.json"
)
REPAIR_PACKET_NAME = "repair_packet.json"
REPAIR_MARKDOWN_NAME = "repair_packet.md"

OPENED_SURFACES = [
    "bounded readable-content selection / excerpting for fetched source content",
    "#358 source-survival harness where needed to use the repaired selector",
    "#359 semantic-support harness as validation of the repaired bounded content",
    "focused docs/tests for this repair",
]

CLOSED_SURFACES = [
    "provider search / Serper / broker",
    "broad retrieval",
    "ranking/filtering of search candidates",
    "prompt behavior",
    "model calls",
    "raw HTML/raw headers/raw cookies/raw page text retention",
    "semantic-support permissiveness",
    "direct RunKernel state mutation",
    "source-obligation satisfaction",
    "citation eligibility/rendering",
    "SufficiencyReadiness",
    "FinalAnswerPacket",
    "Author/AuthorProse",
    "answer text",
    "product correctness claims",
]

EXPLICIT_NON_PROOFS = [
    "no final answer text",
    "no answer correctness or product correctness",
    "no source-obligation satisfaction",
    "no citation eligibility or citation rendering",
    "no SufficiencyReadiness",
    "no FinalAnswerPacket",
    "no Author or AuthorProse behavior",
    "no provider/search/broker/model behavior",
]

MANDATORY_NEXT_CHECKPOINT = "AG-LIVE-SEMANTIC-SUPPORT-COVERAGE-REPLAY-01"

RAW_RETENTION_FLAGS = {
    "raw_html_retained": False,
    "raw_response_headers_retained": False,
    "raw_cookies_retained": False,
    "raw_page_text_retained": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
}

_SAFE_FALSE_KEYS = frozenset(RAW_RETENTION_FLAGS)
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "answer",
        "answer_text",
        "author",
        "author_input",
        "author_material",
        "authorization",
        "body",
        "cache",
        "citations",
        "cookie",
        "cookies",
        "db_row",
        "env",
        "fap",
        "final_answer",
        "final_answer_packet",
        "full_prompt",
        "full_trace",
        "header",
        "headers",
        "html",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_content",
        "raw_headers",
        "raw_html",
        "raw_model_response",
        "raw_page_text",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "raw_text",
        "raw_trace",
        "secret",
        "secrets",
        "source_obligation_satisfaction",
        "token",
        "unbounded_content",
        "unbounded_text",
    }
)
_DANGEROUS_TRUE_KEYS = frozenset(
    {
        "author_input_created",
        "citation_created",
        "citation_eligible",
        "final_answer_packet_created",
        "product_correctness_claimed",
        "source_obligation_satisfied",
        "sufficiency_decided",
    }
)


class AnswerBearingBoundingRepairError(ValueError):
    """Raised when the repair packet or live verification must fail closed."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


def verify_live_repair(
    *,
    candidate_packet_path: str | Path = source_harness.DEFAULT_CANDIDATE_PACKET,
    validation_packet_path: str | Path = source_harness.DEFAULT_VALIDATION_PACKET,
    old_source_survival_packet_path: str | Path = DEFAULT_OLD_SOURCE_PACKET,
    old_semantic_support_packet_path: str | Path = DEFAULT_OLD_SEMANTIC_PACKET,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    confirm_fetch_read_repair: bool = False,
) -> dict[str, Any]:
    """Run the single licensed fetch/read repair verification."""

    if not confirm_fetch_read_repair:
        raise AnswerBearingBoundingRepairError(
            "confirm_fetch_read_repair_required",
            "verify-live-repair requires --confirm-fetch-read-repair",
        )
    target = _phase_output_dir(output_dir)
    source_dir = source_harness.DEFAULT_OUTPUT_DIR / PHASE.lower().replace("-", "_")
    semantic_dir = target / "semantic_support_repaired"
    source_packet = source_harness.fetch_read_custody(
        candidate_packet_path=candidate_packet_path,
        validation_packet_path=validation_packet_path,
        output_dir=source_dir,
        confirm_fetch_read=True,
    )
    semantic_packet = semantic_harness.reduce_semantic_coverage(
        source_survival_packet_path=source_dir / source_harness.SOURCE_PACKET_NAME,
        fetch_read_content_packet_path=source_dir / source_harness.FETCH_READ_PACKET_NAME,
        sanitized_content_reference_path=source_dir / source_harness.CONTENT_REFERENCE_NAME,
        evidence_ledger_projection_path=source_dir / source_harness.LEDGER_PROJECTION_NAME,
        output_dir=semantic_dir,
        confirm_semantic_coverage=True,
        run_kernel=None,
    )
    packet = build_repair_packet(
        source_packet=source_packet,
        semantic_packet=semantic_packet,
        old_source_packet=_optional_json(old_source_survival_packet_path),
        old_semantic_packet=_optional_json(old_semantic_support_packet_path),
        path_digests={
            "old_source_survival_packet": _optional_file_digest(old_source_survival_packet_path),
            "old_semantic_support_packet": _optional_file_digest(old_semantic_support_packet_path),
            "repaired_source_survival_packet": _file_digest(source_dir / source_harness.SOURCE_PACKET_NAME),
            "repaired_fetch_read_content_packet": _file_digest(source_dir / source_harness.FETCH_READ_PACKET_NAME),
            "repaired_sanitized_content_reference": _file_digest(source_dir / source_harness.CONTENT_REFERENCE_NAME),
            "repaired_semantic_support_packet": _file_digest(
                semantic_dir / semantic_harness.RESULT_PACKET_NAME
            ),
        },
        output_dir=target,
        source_output_dir=source_dir,
        semantic_output_dir=semantic_dir,
    )
    write_repair_packet(packet, output_dir=target)
    return packet


def build_repair_packet(
    *,
    source_packet: Mapping[str, Any],
    semantic_packet: Mapping[str, Any],
    old_source_packet: Mapping[str, Any] | None = None,
    old_semantic_packet: Mapping[str, Any] | None = None,
    path_digests: Mapping[str, Any] | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    source_output_dir: str | Path | None = None,
    semantic_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    repaired_ref = _safe_mapping(source_packet.get("sanitized_content_reference_ref"))
    old_ref = _safe_mapping(_safe_mapping(old_source_packet).get("sanitized_content_reference_ref"))
    selector = _safe_mapping(repaired_ref.get("bounded_text_selection"))
    missing_anchors = _safe_list(selector.get("missing_anchors"))
    matched_anchors = _safe_list(selector.get("matched_anchors"))
    answer_bearing_enough = (
        source_packet.get("selected_source_survived") == "source_survival_pass"
        and semantic_packet.get("semantic_support_result")
        != OLD_359_FAILURE_RESULT
        and not missing_anchors
        and bool(matched_anchors)
    )
    packet = _without_empty(
        {
            "phase": PHASE,
            "mode": MODE,
            "repair_verdict_target": REPAIR_VERDICT_TARGET,
            "proof_class": PROOF_CLASS,
            "product_facing_progress_type": PRODUCT_FACING_PROGRESS_TYPE,
            "named_defect": NAMED_DEFECT,
            "prior_357_358_359_refs_and_digests": _safe_mapping(path_digests),
            "selected_url": SELECTED_URL,
            "selected_domain": SELECTED_DOMAIN,
            "target_component": TARGET_COMPONENT,
            "target_claim_under_test": TARGET_CLAIM_UNDER_TEST,
            "old_359_result": _safe_mapping(old_semantic_packet).get(
                "semantic_support_result",
                OLD_359_FAILURE_RESULT,
            ),
            "old_failure_gate_from_359": _safe_mapping(old_semantic_packet).get(
                "first_failed_gate",
                OLD_359_FAILURE_GATE,
            ),
            "old_bounded_content_char_count": old_ref.get("bounded_text_char_count"),
            "old_bounded_content_digest": old_ref.get("bounded_text_digest"),
            "repaired_bounded_content_char_count": repaired_ref.get("bounded_text_char_count"),
            "repaired_bounded_content_digest": repaired_ref.get("bounded_text_digest"),
            "selector_strategy": selector.get("selection_strategy"),
            "matched_anchors": matched_anchors,
            "matched_anchor_count": selector.get("matched_anchor_count"),
            "missing_anchors": missing_anchors,
            "local_context_posture": selector.get("local_context_posture"),
            "anti_anchor_laundering_posture": {
                "single_coherent_source_window": selector.get("local_context_posture")
                == "single_contiguous_window",
                "anti_anchor_laundering_passed": selector.get(
                    "anti_anchor_laundering_passed"
                )
                is True,
                "stitched_distant_fragments": False,
            },
            "repaired_bounded_content_answer_bearing_enough_for_359_gate_5": (
                answer_bearing_enough
            ),
            "semantic_support_reduction_rerun": True,
            "post_repair_359_semantic_support_result": semantic_packet.get(
                "semantic_support_result"
            ),
            "first_failed_gate_after_repair": semantic_packet.get("first_failed_gate"),
            "provider_search_calls": 0,
            "broker_calls": 0,
            "model_calls": 0,
            "fetch_read_calls_attempted": source_packet.get("fetch_read_calls_attempted"),
            "fetch_read_calls_completed": source_packet.get("fetch_read_calls_completed"),
            **RAW_RETENTION_FLAGS,
            "opened_surfaces": list(OPENED_SURFACES),
            "closed_surfaces": list(CLOSED_SURFACES),
            "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
            "mandatory_next_checkpoint": MANDATORY_NEXT_CHECKPOINT,
            "output_paths": {
                "repair_packet": _rel(Path(output_dir) / REPAIR_PACKET_NAME),
                "repair_markdown": _rel(Path(output_dir) / REPAIR_MARKDOWN_NAME),
                "repaired_source_survival_dir": (
                    _rel(source_output_dir) if source_output_dir else None
                ),
                "repaired_semantic_support_dir": (
                    _rel(semantic_output_dir) if semantic_output_dir else None
                ),
            },
            "old_path_treatment": (
                "The old prefix bounding path is replaced for the #358 content "
                "builder call; semantic support remains fail-closed and is not loosened."
            ),
            "existing_machinery_reused": [
                "FetchReadContentPacket / SanitizedContentReference builder and validator",
                "#358 source-survival fetch/read custody harness",
                "#359 semantic-support coverage harness",
                "EvidenceRelativeAnalysisPacket proposal gate",
            ],
            "new_machinery_introduced": [
                "select_bounded_answer_bearing_text helper",
                "bounded_text_selection safe metadata",
                "AG-LIVE-ANSWER-BEARING-BOUNDING-REPAIR-01 review packet harness",
            ],
            "why_not_reinventing_existing_surface": (
                "The repair changes the bounded content selected before the "
                "existing FetchReadContentPacket handoff; it does not add a "
                "parallel evidence, semantic-support, citation, FAP, or Author path."
            ),
            "live_validation_status": (
                "single public fetch/read repair verification completed"
                if source_packet.get("fetch_read_calls_completed") == 1
                else "not completed"
            ),
        }
    )
    packet["matched_anchors"] = matched_anchors
    packet["missing_anchors"] = missing_anchors
    return validate_repair_packet(packet)


def validate_repair_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(packet)
    if safe.get("phase") != PHASE or safe.get("mode") != MODE:
        raise AnswerBearingBoundingRepairError("repair_packet_phase_mismatch")
    if safe.get("provider_search_calls") != 0 or safe.get("broker_calls") != 0:
        raise AnswerBearingBoundingRepairError("repair_packet_opens_provider_surface")
    if safe.get("model_calls") != 0:
        raise AnswerBearingBoundingRepairError("repair_packet_opens_model_surface")
    if safe.get("fetch_read_calls_attempted") not in (0, 1):
        raise AnswerBearingBoundingRepairError("repair_packet_fetch_read_budget_exceeded")
    for key, expected in RAW_RETENTION_FLAGS.items():
        if safe.get(key) is not expected:
            raise AnswerBearingBoundingRepairError("repair_packet_retains_raw_material")
    _reject_forbidden_packet_material(safe)
    return safe


def write_repair_packet(packet: Mapping[str, Any], *, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> None:
    target = _phase_output_dir(output_dir)
    validated = validate_repair_packet(packet)
    _write_json(target / REPAIR_PACKET_NAME, validated)
    (target / REPAIR_MARKDOWN_NAME).write_text(_repair_markdown(validated), encoding="utf-8")


def _repair_markdown(packet: Mapping[str, Any]) -> str:
    return (
        f"# {PHASE} Repair Packet\n\n"
        f"Mode: `{MODE}`\n\n"
        f"Named defect: {NAMED_DEFECT}\n\n"
        f"Selector strategy: `{packet.get('selector_strategy')}`\n\n"
        f"Matched anchors: `{packet.get('matched_anchors')}`\n\n"
        f"Missing anchors: `{packet.get('missing_anchors')}`\n\n"
        "Post-repair #359 result: "
        f"`{packet.get('post_repair_359_semantic_support_result')}`\n\n"
        f"First failed gate after repair: `{packet.get('first_failed_gate_after_repair')}`\n\n"
        f"Mandatory next checkpoint: `{MANDATORY_NEXT_CHECKPOINT}`\n"
    )


def _phase_output_dir(path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    resolved = raw.resolve()
    allowed = DEFAULT_OUTPUT_DIR.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise AnswerBearingBoundingRepairError(
            "output_dir_outside_phase_scope",
            f"output-dir must stay under {_rel(allowed)}",
        ) from exc
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _optional_json(path: str | Path) -> dict[str, Any] | None:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    if not raw.exists():
        return None
    decoded = json.loads(raw.read_text(encoding="utf-8"))
    if not isinstance(decoded, Mapping):
        raise AnswerBearingBoundingRepairError("json_packet_must_be_object")
    return dict(decoded)


def _optional_file_digest(path: str | Path) -> str | None:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    if not raw.exists():
        return None
    return _file_digest(raw)


def _file_digest(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reject_forbidden_packet_material(value: Any) -> None:
    keys = _collect_keys(value)
    raw_or_closed = sorted(
        key
        for key in keys
        if key not in _SAFE_FALSE_KEYS
        and (key.startswith("raw_") or key in _FORBIDDEN_KEYS)
    )
    if raw_or_closed:
        raise AnswerBearingBoundingRepairError(
            "repair_packet_contains_raw_or_closed_fields",
            ", ".join(raw_or_closed),
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise AnswerBearingBoundingRepairError(
            "repair_packet_opens_closed_surfaces",
            ", ".join(dangerous),
        )


def _dangerous_true_claims(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = _normalize_key(key)
            if token in _DANGEROUS_TRUE_KEYS and item is True:
                found.add(token)
            found.update(_dangerous_true_claims(item))
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            found.update(_dangerous_true_claims(item))
    return found


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, str | bytes) or not isinstance(value, list | tuple):
        return []
    return list(value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != {} and value != []
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def _rel(path: str | Path | None) -> str | None:
    if path is None:
        return None
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    try:
        return str(raw.resolve().relative_to(ROOT))
    except ValueError:
        return str(raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run AG-LIVE answer-bearing bounded-content repair verification. "
            "Only verify-live-repair with --confirm-fetch-read-repair may make "
            "the single licensed public URL fetch/read call."
        )
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    live = subparsers.add_parser("verify-live-repair")
    live.add_argument("--candidate-packet", default=str(source_harness.DEFAULT_CANDIDATE_PACKET))
    live.add_argument("--validation-packet", default=str(source_harness.DEFAULT_VALIDATION_PACKET))
    live.add_argument("--source-survival-packet", default=str(DEFAULT_OLD_SOURCE_PACKET))
    live.add_argument("--semantic-support-packet", default=str(DEFAULT_OLD_SEMANTIC_PACKET))
    live.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    live.add_argument("--confirm-fetch-read-repair", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        packet = verify_live_repair(
            candidate_packet_path=args.candidate_packet,
            validation_packet_path=args.validation_packet,
            old_source_survival_packet_path=args.source_survival_packet,
            old_semantic_support_packet_path=args.semantic_support_packet,
            output_dir=args.output_dir,
            confirm_fetch_read_repair=args.confirm_fetch_read_repair,
        )
    except AnswerBearingBoundingRepairError as exc:
        print(exc.code, file=sys.stderr)
        return 2
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        source_harness.SourceSurvivalError,
        semantic_harness.SemanticSupportCoverageError,
    ) as exc:
        print(f"refusing AG-LIVE answer-bearing bounding repair: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "phase": PHASE,
                "operation": args.operation,
                "output_dir": str(Path(args.output_dir)),
                "post_repair_359_semantic_support_result": packet.get(
                    "post_repair_359_semantic_support_result"
                ),
                "first_failed_gate_after_repair": packet.get(
                    "first_failed_gate_after_repair"
                ),
                "fetch_read_calls_attempted": packet.get(
                    "fetch_read_calls_attempted"
                ),
                "fetch_read_calls_completed": packet.get(
                    "fetch_read_calls_completed"
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
