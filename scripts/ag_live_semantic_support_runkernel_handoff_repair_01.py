from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import ag_limited_live_search_candidate_01 as candidate_harness  # noqa: E402
from scripts import ag_live_answer_bearing_bounding_repair_01 as bounding_repair  # noqa: E402
from scripts import ag_live_semantic_support_coverage_01 as semantic_harness  # noqa: E402
from scripts import ag_live_source_survival_fetch_read_custody_01 as source_harness  # noqa: E402

PHASE = "AG-LIVE-SEMANTIC-SUPPORT-RUNKERNEL-HANDOFF-REPAIR-01"
MODE = "REPAIR"
REPAIR_VERDICT_TARGET = "YES"
PROOF_CLASS = "live_component_proof with offline phase-focus regression guards"
PRODUCT_FACING_PROGRESS_TYPE = "product-path repair of RunKernel replay/handoff seam"
NAMED_DEFECT = (
    "After #360 repaired answer-bearing bounded content, the standalone #359 "
    "semantic-support replay still failed at gate_6_semantic_observation_admission "
    "because packet/projection-only replay did not preserve the live RunKernel "
    "state required by the existing SemanticObservation bridge and ComponentCoverage "
    "reducer."
)
SELECTED_URL = "https://travel.state.gov/en/passports/apply/help/fees.html"
SELECTED_DOMAIN = "travel.state.gov"
TARGET_COMPONENT = "adult U.S. passport book renewal fee"
TARGET_COMPONENT_ID = semantic_harness.TARGET_COMPONENT_ID
TARGET_CLAIM_UNDER_TEST = "adult U.S. passport book renewal fee is $130"
DEFAULT_OUTPUT_DIR = (
    ROOT / "output" / "ag_live_semantic_support_runkernel_handoff_repair_01"
)
REPAIR_PACKET_NAME = "repair_packet.json"
REPAIR_MARKDOWN_NAME = "repair_packet.md"
MANDATORY_NEXT_CHECKPOINT = "AG-LIVE-SUFFICIENCY-FAP-AUTHORPROSE-01"

REPLAY_RESULTS = frozenset(
    {
        "runkernel_handoff_repair_pass",
        "runkernel_handoff_repair_partial",
        "runkernel_handoff_repair_fail_candidate_replay",
        "runkernel_handoff_repair_fail_source_survival",
        "runkernel_handoff_repair_fail_analysis_packet",
        "runkernel_handoff_repair_fail_semantic_observation_admission",
        "runkernel_handoff_repair_fail_component_coverage",
        "validation_not_run_operator_blocked",
        "validation_inconclusive",
    }
)

OPENED_SURFACES = [
    "RunKernel in-process replay/handoff for live candidate/source-survival to semantic-support boundary",
    "#357 current-path candidate acquisition replay from existing sanitized provider results only",
    "#360 repaired bounded fetch/read content selection",
    "SemanticObservation admission through existing bridge",
    "ComponentCoverage reduction through existing RunKernel authorization/reducer",
    "small harness/script/tests/docs needed to validate this seam",
]

CLOSED_SURFACES = [
    "provider search / Serper / broker",
    "broad retrieval",
    "ranking/filtering of search candidates",
    "prompt behavior",
    "model calls",
    "raw HTML/raw headers/raw cookies/raw page text retention",
    "projection-to-RunKernel rehydration",
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
    "no product-quality prose",
]

RAW_RETENTION_FLAGS = {
    "raw_html_retained": False,
    "raw_response_headers_retained": False,
    "raw_cookies_retained": False,
    "raw_page_text_retained": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
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
        "citation",
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


class RunKernelHandoffRepairError(ValueError):
    """Raised when the repair replay must fail closed."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


def verify_live_runkernel_handoff(
    *,
    sanitized_provider_results_path: str | Path = candidate_harness.DEFAULT_PROVIDER_RESULTS,
    candidate_packet_cross_check_path: str | Path | None = None,
    validation_packet_cross_check_path: str | Path | None = None,
    answer_bearing_repair_packet_cross_check_path: str | Path | None = (
        bounding_repair.DEFAULT_OUTPUT_DIR / bounding_repair.REPAIR_PACKET_NAME
    ),
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    confirm_fetch_read_runkernel_handoff: bool = False,
    fetcher: Callable[[str], source_harness.FetchReadResult] | None = None,
) -> dict[str, Any]:
    """Run the licensed one-fetch in-process RunKernel handoff repair."""

    if not confirm_fetch_read_runkernel_handoff:
        raise RunKernelHandoffRepairError(
            "confirm_fetch_read_runkernel_handoff_required",
            "verify-live-runkernel-handoff requires --confirm-fetch-read-runkernel-handoff",
        )
    target = _phase_output_dir(output_dir)
    provider_results_path = _input_path(sanitized_provider_results_path)
    source_dir = (
        source_harness.DEFAULT_OUTPUT_DIR
        / "ag_live_semantic_support_runkernel_handoff_repair_01"
    )
    semantic_dir = target / "semantic_support_replay"
    candidate_handoff = candidate_harness.reduce_existing_sanitized_provider_results_in_process(
        query=candidate_harness.DEFAULT_QUERY,
        provider_results_path=provider_results_path,
        output_dir=candidate_harness.DEFAULT_OUTPUT_DIR
        / "ag_live_semantic_support_runkernel_handoff_repair_01",
    )
    candidate_cross_check = _cross_check_packet(
        candidate_packet_cross_check_path,
        expected_url=SELECTED_URL,
        expected_domain=SELECTED_DOMAIN,
    )
    validation_cross_check = _cross_check_packet(
        validation_packet_cross_check_path,
        expected_url=SELECTED_URL,
        expected_domain=SELECTED_DOMAIN,
    )
    source_handoff = source_harness.fetch_read_custody_in_process(
        candidate_handoff=candidate_handoff,
        output_dir=source_dir,
        confirm_fetch_read=True,
        fetcher=fetcher,
    )
    semantic_packet = semantic_harness.reduce_semantic_coverage(
        source_survival_packet_path=source_dir / source_harness.SOURCE_PACKET_NAME,
        fetch_read_content_packet_path=source_dir / source_harness.FETCH_READ_PACKET_NAME,
        sanitized_content_reference_path=source_dir / source_harness.CONTENT_REFERENCE_NAME,
        evidence_ledger_projection_path=source_dir / source_harness.LEDGER_PROJECTION_NAME,
        output_dir=semantic_dir,
        confirm_semantic_coverage=True,
        run_kernel=source_handoff.run_kernel,
    )
    packet = build_repair_packet(
        candidate_handoff=candidate_handoff,
        source_handoff=source_handoff,
        semantic_packet=semantic_packet,
        sanitized_provider_results_path=provider_results_path,
        candidate_packet_cross_check=candidate_cross_check,
        validation_packet_cross_check=validation_cross_check,
        answer_bearing_repair_packet_cross_check=_cross_check_packet(
            answer_bearing_repair_packet_cross_check_path,
            expected_url=SELECTED_URL,
            expected_domain=SELECTED_DOMAIN,
            optional=True,
        ),
        output_dir=target,
        source_output_dir=source_dir,
        semantic_output_dir=semantic_dir,
    )
    write_repair_packet(packet, output_dir=target)
    return packet


def build_repair_packet(
    *,
    candidate_handoff: candidate_harness.InProcessLiveCandidateHandoff,
    source_handoff: source_harness.InProcessSourceSurvivalHandoff,
    semantic_packet: Mapping[str, Any],
    sanitized_provider_results_path: str | Path,
    candidate_packet_cross_check: Mapping[str, Any] | None = None,
    validation_packet_cross_check: Mapping[str, Any] | None = None,
    answer_bearing_repair_packet_cross_check: Mapping[str, Any] | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    source_output_dir: str | Path | None = None,
    semantic_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    source_packet = source_handoff.source_survival_packet
    selector = _safe_mapping(source_packet.get("bounded_text_selection"))
    analysis_ref = _safe_mapping(
        semantic_packet.get("evidence_relative_analysis_proposal_ref")
    )
    semantic_ref = _safe_mapping(semantic_packet.get("semantic_observation_ref"))
    coverage_ref = _safe_mapping(semantic_packet.get("component_coverage_ref"))
    replay_result = _replay_result(semantic_packet)
    packet = _without_empty(
        {
            "phase": PHASE,
            "mode": MODE,
            "repair_verdict_target": REPAIR_VERDICT_TARGET,
            "proof_class": PROOF_CLASS,
            "product_facing_progress_type": PRODUCT_FACING_PROGRESS_TYPE,
            "named_defect": NAMED_DEFECT,
            "prior_357_358_359_360_refs_and_digests": {
                "input_357_sanitized_provider_results": _input_ref(
                    sanitized_provider_results_path
                ),
                "optional_357_candidate_packet_cross_check": _safe_mapping(
                    candidate_packet_cross_check
                ),
                "optional_357_validation_packet_cross_check": _safe_mapping(
                    validation_packet_cross_check
                ),
                "optional_360_repair_packet_cross_check": _safe_mapping(
                    answer_bearing_repair_packet_cross_check
                ),
            },
            "selected_url": SELECTED_URL,
            "selected_domain": SELECTED_DOMAIN,
            "target_component": TARGET_COMPONENT,
            "target_component_id": TARGET_COMPONENT_ID,
            "target_claim_under_test": TARGET_CLAIM_UNDER_TEST,
            "input_357_sanitized_provider_results_ref": _input_ref(
                sanitized_provider_results_path
            ),
            "candidate_packet_json_used_only_as_cross_check_not_state_source": True,
            "optional_cross_check_inputs": {
                "candidate_packet": _safe_mapping(candidate_packet_cross_check),
                "validation_packet": _safe_mapping(validation_packet_cross_check),
                "answer_bearing_repair_packet": _safe_mapping(
                    answer_bearing_repair_packet_cross_check
                ),
            },
            "fetch_read_calls_attempted": source_packet.get("fetch_read_calls_attempted"),
            "fetch_read_calls_completed": source_packet.get("fetch_read_calls_completed"),
            "provider_search_calls": 0,
            "broker_calls": 0,
            "model_calls": 0,
            "retrieval_calls": 0,
            **RAW_RETENTION_FLAGS,
            "repaired_bounded_content_selector_metadata": selector,
            "evidence_relative_analysis_packet_id": analysis_ref.get("packet_id"),
            "evidence_relative_analysis_packet_digest": analysis_ref.get(
                "packet_digest"
            ),
            "evidence_relative_analysis_packet_ref": analysis_ref,
            "semantic_observation_attempted_count": semantic_packet.get(
                "semantic_observation_attempted_count",
                0,
            ),
            "semantic_observation_admitted_count": semantic_packet.get(
                "semantic_observation_admitted_count",
                0,
            ),
            "semantic_observation_id": semantic_ref.get("observation_id"),
            "semantic_observation_digest": semantic_ref.get("observation_digest"),
            "semantic_observation_ref": semantic_ref,
            "component_coverage_attempted_count": semantic_packet.get(
                "component_coverage_attempted_count",
                0,
            ),
            "component_coverage_reduced_count": semantic_packet.get(
                "component_coverage_reduced_count",
                0,
            ),
            "component_coverage_id": coverage_ref.get("coverage_record_id"),
            "component_coverage_digest": coverage_ref.get("coverage_record_digest"),
            "component_coverage_ref": coverage_ref,
            "replay_result": replay_result,
            "first_failed_gate": semantic_packet.get("first_failed_gate"),
            "runkernel_replayed_from_357_sanitized_provider_results": True,
            "runkernel_preserved_in_process_not_rehydrated": (
                source_handoff.run_kernel is candidate_handoff.run_kernel
            ),
            "projection_rehydration_avoided": True,
            "direct_state_mutation_avoided": True,
            "serialized_candidate_packet_used_as_state_source": False,
            "handoff_objects_serialized": False,
            "opened_surfaces": list(OPENED_SURFACES),
            "closed_surfaces": list(CLOSED_SURFACES),
            "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
            "mandatory_next_checkpoint": MANDATORY_NEXT_CHECKPOINT,
            "output_paths": {
                "repair_packet": _rel(Path(output_dir) / REPAIR_PACKET_NAME),
                "repair_markdown": _rel(Path(output_dir) / REPAIR_MARKDOWN_NAME),
                "source_survival_replay_dir": (
                    _rel(source_output_dir) if source_output_dir else None
                ),
                "semantic_support_replay_dir": (
                    _rel(semantic_output_dir) if semantic_output_dir else None
                ),
            },
            "existing_machinery_reused": [
                "#357 ordinary-query front-half and RunKernel live_search_validation reducer",
                "SearchResultCandidatePacket builder/validator",
                "#360 repaired answer-bearing bounded content selector",
                "FetchReadContentPacket / SanitizedContentReference builder and validator",
                "EvidenceLedger candidate/content custody reducer",
                "EvidenceRelativeAnalysisPacket builder/validator",
                "SemanticObservation admission bridge",
                "RunKernel ComponentCoverage reducer",
            ],
            "new_machinery_introduced": [
                "in-memory candidate/source handoff dataclasses",
                "scripts/ag_live_semantic_support_runkernel_handoff_repair_01.py",
                "tests/test_ag_live_semantic_support_runkernel_handoff_repair_01.py",
                "docs/architecture/AG_LIVE_SEMANTIC_SUPPORT_RUNKERNEL_HANDOFF_REPAIR_01.md",
            ],
            "why_not_reinventing_existing_surface": (
                "The repair keeps the same RunKernel lineage alive for existing "
                "admission and coverage reducers instead of creating a projection "
                "rehydration path or parallel semantic authority."
            ),
            "old_path_treatment": (
                "Standalone packet/projection-only #359 replay remains fail-closed "
                "at gate 6; it is not upgraded to impersonate RunKernel state."
            ),
            "live_validation_status": (
                "one public fetch/read verification completed"
                if source_packet.get("fetch_read_calls_completed") == 1
                else "not completed"
            ),
        }
    )
    return validate_repair_packet(packet)


def validate_repair_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_mapping(packet)
    if safe.get("phase") != PHASE or safe.get("mode") != MODE:
        raise RunKernelHandoffRepairError("repair_packet_phase_mismatch")
    if safe.get("repair_verdict_target") != REPAIR_VERDICT_TARGET:
        raise RunKernelHandoffRepairError("repair_packet_verdict_mismatch")
    if safe.get("replay_result") not in REPLAY_RESULTS:
        raise RunKernelHandoffRepairError("repair_packet_replay_result_mismatch")
    if safe.get("provider_search_calls") != 0 or safe.get("broker_calls") != 0:
        raise RunKernelHandoffRepairError("repair_packet_opens_provider_surface")
    if safe.get("model_calls") != 0 or safe.get("retrieval_calls") != 0:
        raise RunKernelHandoffRepairError("repair_packet_opens_model_or_retrieval")
    if safe.get("fetch_read_calls_attempted", 0) > 1:
        raise RunKernelHandoffRepairError("repair_packet_fetch_read_budget_exceeded")
    if safe.get("semantic_observation_attempted_count", 0) > 1:
        raise RunKernelHandoffRepairError("repair_packet_semantic_budget_exceeded")
    if safe.get("component_coverage_attempted_count", 0) > 1:
        raise RunKernelHandoffRepairError("repair_packet_coverage_budget_exceeded")
    if safe.get("projection_rehydration_avoided") is not True:
        raise RunKernelHandoffRepairError("repair_packet_projection_rehydration_opened")
    if safe.get("direct_state_mutation_avoided") is not True:
        raise RunKernelHandoffRepairError("repair_packet_direct_mutation_opened")
    if safe.get("handoff_objects_serialized") is not False:
        raise RunKernelHandoffRepairError("repair_packet_serializes_handoff")
    for key, expected in RAW_RETENTION_FLAGS.items():
        if safe.get(key) is not expected:
            raise RunKernelHandoffRepairError("repair_packet_retains_raw_material")
    _reject_forbidden_packet_material(safe)
    return safe


def write_repair_packet(
    packet: Mapping[str, Any],
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> None:
    target = _phase_output_dir(output_dir)
    validated = validate_repair_packet(packet)
    _write_json(target / REPAIR_PACKET_NAME, validated)
    (target / REPAIR_MARKDOWN_NAME).write_text(
        _repair_markdown(validated),
        encoding="utf-8",
    )


def _replay_result(semantic_packet: Mapping[str, Any]) -> str:
    result = semantic_packet.get("semantic_support_result")
    if result == "semantic_support_coverage_pass":
        return "runkernel_handoff_repair_pass"
    if result == "semantic_support_fail_analysis_packet":
        return "runkernel_handoff_repair_fail_analysis_packet"
    if result == "semantic_support_fail_semantic_observation_admission":
        return "runkernel_handoff_repair_fail_semantic_observation_admission"
    if result == "semantic_support_fail_component_coverage":
        return "runkernel_handoff_repair_fail_component_coverage"
    if result == "semantic_support_fail_source_content_insufficient":
        return "runkernel_handoff_repair_fail_analysis_packet"
    if result == "semantic_support_partial":
        return "runkernel_handoff_repair_partial"
    if result in {"validation_not_run_operator_blocked", "validation_inconclusive"}:
        return str(result)
    return "validation_inconclusive"


def _cross_check_packet(
    path: str | Path | None,
    *,
    expected_url: str,
    expected_domain: str,
    optional: bool = False,
) -> dict[str, Any]:
    if path is None:
        return {}
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    if not raw.exists():
        if optional:
            return {}
        raise RunKernelHandoffRepairError(
            "cross_check_packet_missing",
            f"missing cross-check packet: {_rel(raw)}",
        )
    decoded = json.loads(raw.read_text(encoding="utf-8"))
    if not isinstance(decoded, Mapping):
        raise RunKernelHandoffRepairError("cross_check_packet_must_be_object")
    selected = _selected_source_summary(decoded)
    if selected:
        if selected.get("url") != expected_url or selected.get("domain") != expected_domain:
            raise RunKernelHandoffRepairError("cross_check_selected_source_mismatch")
    return _without_empty(
        {
            "path": _rel(raw),
            "digest": _file_digest(raw),
            "packet_id": decoded.get("packet_id"),
            "packet_digest": decoded.get("packet_digest"),
            "phase": decoded.get("phase"),
            "selected_source": selected,
            "used_only_for_cross_check": True,
            "used_as_runkernel_state_source": False,
        }
    )


def _selected_source_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    selected = _safe_mapping(packet.get("selected_candidate"))
    if selected:
        return _without_empty(
            {
                "url": selected.get("url"),
                "domain": selected.get("domain"),
                "rank": selected.get("rank") or selected.get("result_rank"),
            }
        )
    records = [
        _safe_mapping(item)
        for item in packet.get("candidate_records", [])
        if isinstance(item, Mapping)
    ]
    if records:
        first = records[0]
        return _without_empty(
            {
                "url": first.get("url"),
                "domain": first.get("domain"),
                "rank": first.get("result_rank"),
            }
        )
    summaries = [
        _safe_mapping(item)
        for item in packet.get("sanitized_provider_result_summaries", [])
        if isinstance(item, Mapping)
    ]
    if summaries:
        first = summaries[0]
        return _without_empty(
            {
                "url": first.get("url"),
                "domain": first.get("domain"),
                "rank": first.get("rank"),
            }
        )
    return {}


def _input_ref(path: str | Path) -> dict[str, Any]:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    return {
        "path": _rel(raw),
        "digest": _file_digest(raw),
    }


def _input_path(path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    resolved = raw.resolve()
    if not resolved.exists():
        raise RunKernelHandoffRepairError(
            "input_357_sanitized_provider_results_missing",
            f"missing input: {_rel(resolved)}",
        )
    return resolved


def _phase_output_dir(path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        raw = ROOT / raw
    resolved = raw.resolve()
    allowed = DEFAULT_OUTPUT_DIR.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise RunKernelHandoffRepairError(
            "output_dir_outside_phase_scope",
            f"output-dir must stay under {_rel(allowed)}",
        ) from exc
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _repair_markdown(packet: Mapping[str, Any]) -> str:
    return (
        f"# {PHASE} Repair Packet\n\n"
        f"Mode: `{MODE}`\n\n"
        f"Replay result: `{packet.get('replay_result')}`\n\n"
        f"First failed gate: `{packet.get('first_failed_gate')}`\n\n"
        "SemanticObservation attempted/admitted: "
        f"`{packet.get('semantic_observation_attempted_count')}` / "
        f"`{packet.get('semantic_observation_admitted_count')}`\n\n"
        "ComponentCoverage attempted/reduced: "
        f"`{packet.get('component_coverage_attempted_count')}` / "
        f"`{packet.get('component_coverage_reduced_count')}`\n\n"
        "RunKernel preserved in process: "
        f"`{packet.get('runkernel_preserved_in_process_not_rehydrated')}`\n\n"
        f"Mandatory next checkpoint: `{MANDATORY_NEXT_CHECKPOINT}`\n"
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
        raise RunKernelHandoffRepairError(
            "repair_packet_contains_raw_or_closed_fields",
            ", ".join(raw_or_closed),
        )
    dangerous = sorted(_dangerous_true_claims(value))
    if dangerous:
        raise RunKernelHandoffRepairError(
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


def _file_digest(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


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
            "Run AG-LIVE SemanticSupport RunKernel handoff repair verification. "
            "Only verify-live-runkernel-handoff with confirmation may make the "
            "single licensed public URL fetch/read call."
        )
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    live = subparsers.add_parser("verify-live-runkernel-handoff")
    live.add_argument(
        "--sanitized-provider-results",
        default=str(candidate_harness.DEFAULT_PROVIDER_RESULTS),
    )
    live.add_argument("--candidate-packet-cross-check")
    live.add_argument("--validation-packet-cross-check")
    live.add_argument(
        "--answer-bearing-repair-packet-cross-check",
        default=str(bounding_repair.DEFAULT_OUTPUT_DIR / bounding_repair.REPAIR_PACKET_NAME),
    )
    live.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    live.add_argument("--confirm-fetch-read-runkernel-handoff", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        packet = verify_live_runkernel_handoff(
            sanitized_provider_results_path=args.sanitized_provider_results,
            candidate_packet_cross_check_path=args.candidate_packet_cross_check,
            validation_packet_cross_check_path=args.validation_packet_cross_check,
            answer_bearing_repair_packet_cross_check_path=(
                args.answer_bearing_repair_packet_cross_check
            ),
            output_dir=args.output_dir,
            confirm_fetch_read_runkernel_handoff=(
                args.confirm_fetch_read_runkernel_handoff
            ),
        )
    except RunKernelHandoffRepairError as exc:
        print(exc.code, file=sys.stderr)
        return 2
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        candidate_harness.LimitedLiveSearchCandidateError,
        source_harness.SourceSurvivalError,
        semantic_harness.SemanticSupportCoverageError,
    ) as exc:
        print(f"refusing AG-LIVE RunKernel handoff repair: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "phase": PHASE,
                "operation": args.operation,
                "output_dir": str(Path(args.output_dir)),
                "replay_result": packet.get("replay_result"),
                "first_failed_gate": packet.get("first_failed_gate"),
                "semantic_observation_attempted_count": packet.get(
                    "semantic_observation_attempted_count"
                ),
                "semantic_observation_admitted_count": packet.get(
                    "semantic_observation_admitted_count"
                ),
                "component_coverage_attempted_count": packet.get(
                    "component_coverage_attempted_count"
                ),
                "component_coverage_reduced_count": packet.get(
                    "component_coverage_reduced_count"
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
