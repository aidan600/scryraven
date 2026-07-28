"""Friend-shareable MVP output for the ordinary D-prime status path.

This module prepares a deterministic offline retained-artifact input for the
existing ``build_live_semantic_coverage_status`` product path, then renders a
compact human view plus a sanitized review packet. It does not call providers,
brokers, models, fetch/read, retrieval, or old Author execution.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from core.dprime_model_review_assessment import DPrimeModelReviewLicense
from core.fetch_read_content_reference import (
    build_fetch_read_content_packet_from_candidate_packet,
)
from core.mvp_supported_query_class_boundary import (
    MVP_SUPPORTED_QUERY_CLASS_ID,
    build_mvp_supported_query_class_boundary_status,
)
from core.product_model_route_config import MVP_DEMO_FLAG, MVP_LIVE_DOGFOOD_STATUS_FLAG
from core.search_result_candidate_packet import (
    SearchResultCandidatePacket,
    SearchResultCandidateRecord,
    validate_search_result_candidate_packet,
)
from proplex.live_acquisition_readability_status import (
    FETCH_READ_ARTIFACT_DIR,
    FETCH_READ_CONTENT_PACKET_NAME,
    LIVE_SOURCE_SURVIVAL_SUMMARY_NAME,
    SANITIZED_PROVIDER_RESULTS_NAME,
    SEARCH_ARTIFACT_DIR,
    SEARCH_CANDIDATE_PACKET_NAME,
    SEARCH_RESULT_CANDIDATE_PACKET_NAME,
)
from proplex.live_semantic_coverage_status import (
    LiveSemanticCoverageStatusResult,
    build_live_semantic_coverage_status,
    output_hygiene_passes,
)

PHASE_NAME = "LICENSED-LIVE-DOGFOOD-AND-MVP-POLISH-01"
MODE = "BUILD"
PASS_DECISION = "PASS"
DEFAULT_MVP_QUERY = "What is the current adult U.S. passport book renewal fee by mail?"
BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED = "BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED"
BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING = (
    "BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING"
)
DEFAULT_MVP_OUTPUT_DIR = Path("output") / "mvp_demo_01"
DEFAULT_MVP_LIVE_OUTPUT_DIR = Path("output") / "mvp_live_dogfood_01"
MVP_PACKET_NAME = "mvp_output_packet.json"

MVP_COMPONENT_ID = "component:adult-us-passport-book-renewal-fee-by-mail"
MVP_SOURCE_OBLIGATION_ID = "obligation:official-current-passport-fee-source"
MVP_SOURCE_TITLE = "U.S. Department of State Passport Fees"
MVP_SOURCE_URL = "https://travel.state.gov/en/passports/apply/help/fees.html"
MVP_SOURCE_DOMAIN = "travel.state.gov"
MVP_DEMO_BOUNDED_TEXT = (
    "The U.S. Department of State passport fees page lists the adult passport "
    "book renewal by mail fee as $130."
)

EXPLICIT_NON_PROOFS = (
    "product correctness",
    "live source acquisition quality for the offline demo",
    "source-obligation satisfaction beyond the consumed D-prime lane",
    "multi-component answer handling",
    "full Scrutineer remediation",
    "Economist or Specialist routing",
    "old Author execution",
)

RAW_FALSE_FLAGS = {
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
    "private_logs_retained": False,
}


@dataclass(frozen=True, slots=True)
class MvpFriendOutputResult:
    decision: str
    output: str
    packet: Mapping[str, Any]
    packet_path: Path
    retained_artifact_root: Path | None = None

    @property
    def return_code(self) -> int:
        return 0 if self.decision == PASS_DECISION else 2


def build_mvp_demo_output(
    *,
    query: str = DEFAULT_MVP_QUERY,
    repo_root: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> MvpFriendOutputResult:
    """Build a no-secrets offline MVP demo through the product status path."""

    root = Path(repo_root).resolve()
    query = _normalize_query(query)
    run_id = _run_id(run_id, prefix="mvp-demo")
    run_dir = _run_output_dir(root, output_dir or DEFAULT_MVP_OUTPUT_DIR, run_id)
    if query != DEFAULT_MVP_QUERY:
        return _unsupported_mvp_demo_query_result(
            query=query,
            run_dir=run_dir,
            run_id=run_id,
        )
    retained_root = run_dir / "retained_status_repo"
    _write_demo_retained_artifacts(retained_root=retained_root, query=query, run_id=run_id)

    status = build_live_semantic_coverage_status(
        query=query,
        repo_root=retained_root,
        dprime_model_review_license=_offline_demo_license(),
        dprime_model_review_callable=_offline_demo_model_review,
    )
    packet = _mvp_packet(
        status=status,
        run_id=run_id,
        command_harness_used=f"python -m proplex {MVP_DEMO_FLAG}",
        provider_broker_posture="offline_demo_no_provider_or_broker",
        retained_artifact_root=retained_root,
        live_execution=False,
    )
    packet_path = run_dir / MVP_PACKET_NAME
    _write_json(packet_path, packet)
    output = format_mvp_friend_output(
        packet,
        packet_path=packet_path,
        output_title="ScryRaven MVP demo",
        output_kind="offline demo",
    )
    if not output_hygiene_passes(output):
        packet = {
            **packet,
            "decision": "BLOCKED_MVP_OUTPUT_NOT_FRIEND_READABLE",
            "answer_or_blocker_text": "MVP output hygiene failed.",
            "caps_exhausted": False,
        }
        _write_json(packet_path, packet)
        output = format_mvp_friend_output(
            packet,
            packet_path=packet_path,
            output_title="ScryRaven MVP demo blocked",
            output_kind="offline demo",
        )
    return MvpFriendOutputResult(
        decision=str(packet["decision"]),
        output=output,
        packet=packet,
        packet_path=packet_path,
        retained_artifact_root=retained_root,
    )


def _unsupported_mvp_demo_query_result(
    *,
    query: str,
    run_dir: Path,
    run_id: str,
) -> MvpFriendOutputResult:
    del query
    safe_query_label = "unsupported MVP demo query (not retained)"
    blocker_detail = _unsupported_mvp_demo_query_blocker_detail()
    packet = {
        "phase_name": PHASE_NAME,
        "mode": MODE,
        "query": safe_query_label,
        "unsupported_query_retained": False,
        "supported_demo_query": DEFAULT_MVP_QUERY,
        "run_id": run_id,
        "packet_id": f"mvp-output-packet:{run_id}",
        "ordinary_entrypoint": "python -m proplex",
        "status_flag": MVP_DEMO_FLAG,
        "command_harness_used": f"python -m proplex {MVP_DEMO_FLAG}",
        "runtime_consumer": "fixed_mvp_demo_query_gate",
        "ordinary_product_path_consumed": False,
        "provider_broker_posture": "offline_demo_query_gate_no_provider_or_broker",
        "provider_calls_attempted": 0,
        "provider_calls_completed": 0,
        "search_tasks_attempted": 0,
        "search_tasks_completed": 0,
        "fetch_read_attempts": 0,
        "fetch_read_completed": 0,
        "evidence_ledger_admissions": 0,
        "dprime_model_review_call_count": 0,
        "followup_loop_count": 0,
        "answer_or_blocker_text": (
            f"Blocked before answer: {BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED}. "
            f"{blocker_detail}"
        ),
        "product_answer_text": "",
        "answer_text_present": False,
        "source_display_entries": [],
        "scrutineer_status": "not invoked; unsupported demo query",
        "multi_source_status": "not reached; unsupported demo query",
        "followup_status": "not reached; unsupported demo query",
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_logs_retained": False,
        "product_correctness_claimed": False,
        "caps_exhausted": False,
        "decision_made_by_the_run": "mvp_demo_query_not_supported_blocker_recorded",
        "decision": BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED,
        "status_decision": BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED,
        "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
        "supported_query_class_boundary": (
            build_mvp_supported_query_class_boundary_status(
                status="unsupported_query_blocked_before_boundary_entry",
                fixed_query_example=False,
                product_path_slice="offline_fixed_fixture_demo_query_gate",
                product_path_consumed=False,
            )
        ),
        "retained_artifact_root": None,
        "status_payload": {},
        "blocker_detail": blocker_detail,
    }
    _reject_packet_forbidden_material(packet)
    packet_path = run_dir / MVP_PACKET_NAME
    _write_json(packet_path, packet)
    output = format_mvp_friend_output(
        packet,
        packet_path=packet_path,
        output_title="ScryRaven MVP demo blocked",
        output_kind="offline fixed fixture demo",
    )
    return MvpFriendOutputResult(
        decision=BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED,
        output=output,
        packet=packet,
        packet_path=packet_path,
    )


def _unsupported_mvp_demo_query_blocker_detail() -> str:
    return (
        "The offline MVP demo is a fixed deterministic fixture. It currently "
        f'only supports: "{DEFAULT_MVP_QUERY}". Arbitrary query answering '
        "is not supported yet; the documented supported-query-class boundary "
        f"is {MVP_SUPPORTED_QUERY_CLASS_ID}, and the next product milestone is "
        "query-to-relation planning. "
        "The fixed live dogfood slice is not friend-level or general MVP, "
        "and product correctness remains unclaimed."
    )


def build_mvp_live_dogfood_status_output(
    *,
    query: str = DEFAULT_MVP_QUERY,
    repo_root: str | Path,
    retained_artifact_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> MvpFriendOutputResult:
    """Consume live-retained artifacts through the MVP status view.

    This function does not perform provider, broker, fetch/read, or model calls.
    It only consumes already-retained sanitized artifacts through the ordinary
    product status builder and records the resulting answer or blocker.
    """

    root = Path(repo_root).resolve()
    run_id = _run_id(run_id, prefix="mvp-live")
    run_dir = _run_output_dir(root, output_dir or DEFAULT_MVP_LIVE_OUTPUT_DIR, run_id)
    status_root = (
        Path(retained_artifact_root).resolve()
        if retained_artifact_root is not None
        else root
    )
    status = build_live_semantic_coverage_status(query=query, repo_root=status_root)
    packet = _mvp_packet(
        status=status,
        run_id=run_id,
        command_harness_used=f"python -m proplex {MVP_LIVE_DOGFOOD_STATUS_FLAG}",
        provider_broker_posture=(
            "existing_product_status_consumer_over_retained_live_artifacts"
        ),
        retained_artifact_root=status_root,
        live_execution=True,
    )
    packet_path = run_dir / "live_dogfood_packet.json"
    _write_json(packet_path, packet)
    output = format_mvp_friend_output(
        packet,
        packet_path=packet_path,
        output_title="ScryRaven MVP live dogfood status",
        output_kind="live dogfood status",
    )
    return MvpFriendOutputResult(
        decision=str(packet["decision"]),
        output=output,
        packet=packet,
        packet_path=packet_path,
        retained_artifact_root=status_root,
    )


def build_mvp_live_dogfood_status_output_from_semantic_status(
    *,
    semantic_status: LiveSemanticCoverageStatusResult,
    repo_root: str | Path,
    retained_artifact_root: str | Path,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    command_harness_used: str,
    provider_broker_posture: str,
) -> MvpFriendOutputResult:
    """Wrap an already-produced semantic status without running live calls here."""

    root = Path(repo_root).resolve()
    run_id = _run_id(run_id, prefix="mvp-live")
    run_dir = _run_output_dir(root, output_dir or DEFAULT_MVP_LIVE_OUTPUT_DIR, run_id)
    status_root = Path(retained_artifact_root).resolve()
    packet = _mvp_packet(
        status=semantic_status,
        run_id=run_id,
        command_harness_used=command_harness_used,
        provider_broker_posture=provider_broker_posture,
        retained_artifact_root=status_root,
        live_execution=True,
    )
    packet_path = run_dir / "live_dogfood_packet.json"
    _write_json(packet_path, packet)
    output = format_mvp_friend_output(
        packet,
        packet_path=packet_path,
        output_title="ScryRaven MVP live dogfood status",
        output_kind="live dogfood status",
    )
    return MvpFriendOutputResult(
        decision=str(packet["decision"]),
        output=output,
        packet=packet,
        packet_path=packet_path,
        retained_artifact_root=status_root,
    )


def format_mvp_friend_output(
    packet: Mapping[str, Any],
    *,
    packet_path: Path,
    output_title: str,
    output_kind: str,
) -> str:
    """Render compact default CLI text for a friend/reviewer."""

    answer_or_blocker = _clean_text(packet.get("answer_or_blocker_text"), limit=1_400)
    sources = _source_display_entries(packet)
    scrutineer = _clean_text(packet.get("scrutineer_status"), limit=220) or "not invoked"
    followup = _clean_text(packet.get("followup_status"), limit=220) or "not requested"
    relation = _clean_text(packet.get("multi_source_status"), limit=220) or "single source lane"
    boundary = _supported_query_class_boundary_line(packet)
    lines = [
        output_title,
        f"Question: {_clean_text(packet.get('query'), limit=500)}",
        f"Decision: {packet.get('decision')}",
        "",
        "Answer",
        answer_or_blocker or "No answer text is available.",
        "",
        "Sources",
    ]
    if sources:
        lines.extend(f"- {entry}" for entry in sources)
    else:
        lines.append("- No source display is available yet.")
    lines.extend(
        [
            "",
            "Challenge State",
            f"Scrutineer: {scrutineer}",
            f"Multi-source posture: {relation}",
            f"Follow-up: {followup}",
            "",
            "Caveats",
            "- Product correctness claimed: false.",
            f"- Supported-query class: {boundary}.",
            f"- Output kind: {output_kind}.",
            f"- Provider/broker posture: {packet.get('provider_broker_posture')}.",
            "- Raw/private retained: false.",
            "- Source display shows consumed source-display state when available; it is not a correctness claim.",
            f"- Review packet: {_display_path(packet_path)}",
        ]
    )
    return "\n".join(lines)


def _write_demo_retained_artifacts(
    *,
    retained_root: Path,
    query: str,
    run_id: str,
) -> None:
    search_dir = retained_root / SEARCH_ARTIFACT_DIR
    fetch_dir = retained_root / FETCH_READ_ARTIFACT_DIR
    search_dir.mkdir(parents=True, exist_ok=True)
    fetch_dir.mkdir(parents=True, exist_ok=True)

    request_id = f"request:{run_id}"
    contract_ref = _contract_ref(query=query)
    handoff_ref = _handoff_ref(contract_ref=contract_ref, query=query)
    candidate_digest = _digest_json(
        {
            "phase": PHASE_NAME,
            "query": query,
            "url": MVP_SOURCE_URL,
            "component_id": MVP_COMPONENT_ID,
        }
    )
    candidate = SearchResultCandidateRecord(
        run_id=run_id,
        request_id=request_id,
        current_answer_contract_ref=contract_ref,
        search_executor_handoff_ref=handoff_ref,
        search_task_id="search-task:mvp-demo-passport-fee",
        provider_authorized="serper",
        provider_used="serper",
        provider_call_index=1,
        result_rank=1,
        title=MVP_SOURCE_TITLE,
        url=MVP_SOURCE_URL,
        domain=MVP_SOURCE_DOMAIN,
        candidate_id="search-result-candidate:mvp-demo-passport-fee",
        candidate_digest=candidate_digest,
        validation_id="validation:mvp-demo-offline",
        parent_live_search_validation_ref={
            "validation_id": "validation:mvp-demo-offline",
            "candidate_count": 1,
        },
        query_intent_id="query-intent:mvp-demo-passport-fee",
        component_id=MVP_COMPONENT_ID,
        source_obligation_candidate_ids=(MVP_SOURCE_OBLIGATION_ID,),
        snippet="Official passport fee page lists adult renewal by mail fee.",
        published_or_observed_date="offline-demo-current-fixture",
    ).to_dict()
    candidate_packet = SearchResultCandidatePacket(
        run_id=run_id,
        request_id=request_id,
        current_answer_contract_ref=contract_ref,
        search_executor_handoff_ref=handoff_ref,
        candidate_records=[candidate],
        selected_search_task_ids=["search-task:mvp-demo-passport-fee"],
        provider_authorized="serper",
        provider_used="serper",
        parent_live_search_validation_ref={
            "validation_id": "validation:mvp-demo-offline",
            "candidate_count": 1,
        },
    ).to_dict()
    validate_search_result_candidate_packet(candidate_packet)
    provider_result = {
        "title": MVP_SOURCE_TITLE,
        "url": MVP_SOURCE_URL,
        "domain": MVP_SOURCE_DOMAIN,
        "snippet": "Official passport fee page lists adult renewal by mail fee.",
        "published_or_observed_date": "offline-demo-current-fixture",
        "result_rank": 1,
        "provider_call_index": 1,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }
    fetch_packet = build_fetch_read_content_packet_from_candidate_packet(
        candidate_packet,
        [_demo_fetch_read_material(candidate_packet)],
    )
    _write_json(
        search_dir / SANITIZED_PROVIDER_RESULTS_NAME,
        {
            "schema_version": "2",
            "proof_kind": "scryraven_search_query_proof_v2",
            "provider": "serper",
            "operation": "search.query",
            "status": "ok",
            "result_count": 1,
            "results": [provider_result],
            "physical_attempt_count": 1,
            "caller_authorized_cost_ceiling_usd": "0.00",
            "raw_provider_payload_retained": False,
            "raw_request_material_retained": False,
            "raw_response_material_retained": False,
            "raw_search_response_retained": False,
        },
    )
    _write_json(search_dir / SEARCH_CANDIDATE_PACKET_NAME, candidate_packet)
    _write_json(search_dir / SEARCH_RESULT_CANDIDATE_PACKET_NAME, candidate_packet)
    _write_json(fetch_dir / FETCH_READ_CONTENT_PACKET_NAME, fetch_packet)
    _write_json(fetch_dir / LIVE_SOURCE_SURVIVAL_SUMMARY_NAME, _fetch_summary(fetch_packet))


def _demo_fetch_read_material(candidate_packet: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _safe_mapping(candidate_packet["candidate_records"][0])
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "run_id": candidate_packet["run_id"],
        "request_id": candidate_packet["request_id"],
        "current_answer_contract_digest": candidate_packet[
            "current_answer_contract_digest"
        ],
        "search_executor_handoff_digest": candidate_packet[
            "search_executor_handoff_digest"
        ],
        "search_result_candidate_packet_id": candidate_packet["packet_id"],
        "search_result_candidate_packet_digest": candidate_packet["packet_digest"],
        "fetch_read_status": "readable",
        "attempted_url": candidate["url"],
        "resolved_url": candidate["url"],
        "resolved_domain": candidate["domain"],
        "content_type": "text/html",
        "http_status": 200,
        "retrieved_or_observed_at": "offline-demo",
        "content_title": candidate["title"],
        "bounded_text": MVP_DEMO_BOUNDED_TEXT,
        "bounded_text_sanitized": True,
        "bounded_text_bounded": True,
        "bounded_text_char_count": len(MVP_DEMO_BOUNDED_TEXT),
        "raw_page_content_retained": False,
        "raw_headers_retained": False,
    }


def _fetch_summary(fetch_packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "decision": PASS_DECISION,
        "readable_content_handoff_created": True,
        "retention_flags": {
            "headers_retained": False,
            "page_content_retained": False,
            "page_html_retained": False,
            "page_text_retained": False,
            "private_material_retained": False,
            "prompt_retained": False,
            "provider_payload_retained": False,
            "search_response_retained": False,
            "unbounded_page_material_retained": False,
        },
        "closed_downstream_surfaces": {
            "answer_text": False,
            "author_or_authorprose": False,
            "citation_eligibility_or_rendering": False,
            "component_coverage": False,
            "evidence_ledger_admission": False,
            "final_answer_packet": False,
            "product_correctness_claim": False,
            "semantic_observation": False,
            "source_obligation_satisfaction": False,
            "sufficiency_readiness": False,
        },
        "fetch_read_content_packet_ref": {
            "packet_id": fetch_packet["packet_id"],
            "packet_digest": fetch_packet["packet_digest"],
            "reference_count": fetch_packet["reference_count"],
            "schema_version": fetch_packet["schema_version"],
        },
    }


def _offline_demo_license() -> DPrimeModelReviewLicense:
    return DPrimeModelReviewLicense(
        license_id="mvp-demo-offline-dprime-review:test-only",
        enabled=True,
        test_only=True,
        callable_kind="fake_test",
        max_model_review_calls=1,
    )


def _offline_demo_model_review(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {
        "source_proposition": (
            "The structured proposition states the adult U.S. passport book "
            "renewal by mail fee as $130 for the current fee component."
        ),
        "answer_component_claim": {
            "component_id": MVP_COMPONENT_ID,
            "claim": "Adult U.S. passport book renewal by mail fee is $130.",
        },
        "support_relation": "directly_supports",
        "required_qualifiers": [
            "adult",
            "passport book",
            "renewal by mail",
            "current fee",
        ],
        "observed_qualifiers": [
            "adult",
            "passport book",
            "renewal by mail",
            "current fee",
        ],
        "missing_qualifiers": [],
        "scope_check": {"status": "passed"},
        "currentness_check": {"status": "current"},
        "contradiction_check": {"status": "absent"},
        "evidential_adequacy_notes": (
            "The structured proposition maps to the same component and current "
            "fee claim in the offline MVP demo input."
        ),
        "non_support_reason_when_not_direct": "",
        "producer_abstained": False,
        "challenge_recommended": False,
        "closed_surface_flags": {
            "model_review_licensed": False,
            "assessment_created": False,
            "validated_support_proposal_created": False,
            "run_kernel_support_admission_request_created": False,
            "semantic_observation_created": False,
            "component_coverage_bound": False,
            "citation_eligibility_claimed": False,
            "source_obligation_satisfaction_claimed": False,
            "answer_text_created": False,
            "product_correctness_claimed": False,
        },
    }


def _mvp_packet(
    *,
    status: LiveSemanticCoverageStatusResult,
    run_id: str,
    command_harness_used: str,
    provider_broker_posture: str,
    retained_artifact_root: Path,
    live_execution: bool,
) -> dict[str, Any]:
    payload = _safe_mapping(status.payload)
    answer_path = _safe_mapping(payload.get("dprime_answer_path_ref"))
    dprime = _safe_mapping(payload.get("dprime_status"))
    followup = _safe_mapping(payload.get("dprime_followup_search_reentry_ref"))
    scrutineer = _safe_mapping(payload.get("dprime_scrutineer_challenge_ref"))
    multi = _safe_mapping(payload.get("dprime_multi_source_support_posture_ref"))
    answer_text = _clean_text(answer_path.get("answer_text"), limit=2_000)
    blocker_detail = _clean_text(payload.get("blocker_detail"), limit=800)
    source_entries = _source_entries_from_status_payload(payload)
    count_summary = _count_summary(payload)
    status_decision = str(status.decision)
    decision = _mvp_decision(
        status_decision=status_decision,
        live_execution=live_execution,
        count_summary=count_summary,
    )
    blocker_detail = _mvp_blocker_detail(
        decision=decision,
        status_decision=status_decision,
        original_detail=blocker_detail,
    )
    friend_answer = _friend_answer_from_payload(payload, answer_text=answer_text)
    packet = {
        "phase_name": PHASE_NAME,
        "mode": MODE,
        "query": payload.get("user_style_query") or DEFAULT_MVP_QUERY,
        "run_id": run_id,
        "packet_id": f"mvp-output-packet:{run_id}",
        "ordinary_entrypoint": "python -m proplex",
        "status_flag": payload.get("status_flag"),
        "command_harness_used": command_harness_used,
        "runtime_consumer": (
            "proplex.live_semantic_coverage_status.build_live_semantic_coverage_status"
        ),
        "ordinary_product_path_consumed": True,
        "provider_broker_posture": provider_broker_posture,
        "provider_calls_attempted": count_summary["provider_calls_attempted"],
        "provider_calls_completed": count_summary["provider_calls_completed"],
        "search_tasks_attempted": count_summary["search_tasks_attempted"],
        "search_tasks_completed": count_summary["search_tasks_completed"],
        "fetch_read_attempts": count_summary["fetch_read_attempts"],
        "fetch_read_completed": count_summary["fetch_read_completed"],
        "evidence_ledger_admissions": count_summary["evidence_ledger_admissions"],
        "dprime_model_review_call_count": _bounded_int(
            dprime.get("model_review_call_count")
        ),
        "followup_loop_count": _followup_loop_count(followup),
        "answer_or_blocker_text": (
            friend_answer
            if friend_answer
            else f"Blocked before answer: {decision}. {blocker_detail or ''}".strip()
        ),
        "product_answer_text": answer_text,
        "answer_text_present": bool(answer_text),
        "source_display_entries": source_entries,
        "scrutineer_status": _scrutineer_status(scrutineer),
        "multi_source_status": _multi_source_status(multi),
        "followup_status": _followup_status(followup),
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "private_logs_retained": False,
        "product_correctness_claimed": False,
        "caps_exhausted": False,
        "decision_made_by_the_run": (
            "live_status_product_path_blocker_recorded"
            if live_execution and decision != PASS_DECISION
            else "mvp_product_path_answer_output_consumed"
            if decision == PASS_DECISION
            else "mvp_product_path_blocker_recorded"
        ),
        "decision": decision,
        "status_decision": status_decision,
        "explicit_non_proofs": list(EXPLICIT_NON_PROOFS),
        "supported_query_class_boundary": (
            build_mvp_supported_query_class_boundary_status(
                status="fixed_dogfood_example_only",
                fixed_query_example=True,
                product_path_slice=(
                    "fixed_live_dogfood_status_slice"
                    if live_execution
                    else "offline_fixed_fixture_demo"
                ),
                product_path_consumed=True,
            )
        ),
        "retained_artifact_root": _display_path(retained_artifact_root),
        "status_payload": _packet_safe_payload(payload),
    }
    if blocker_detail:
        packet["blocker_detail"] = blocker_detail
    _reject_packet_forbidden_material(packet)
    return packet


def _mvp_decision(
    *,
    status_decision: str,
    live_execution: bool,
    count_summary: Mapping[str, int],
) -> str:
    if (
        live_execution
        and status_decision != PASS_DECISION
        and count_summary.get("provider_calls_completed", 0) == 0
        and count_summary.get("fetch_read_completed", 0) == 0
    ):
        return "BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING"
    return status_decision


def _mvp_blocker_detail(
    *,
    decision: str,
    status_decision: str,
    original_detail: str | None,
) -> str | None:
    if decision == BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING:
        return (
            "No ordinary live product/private-broker entrypoint produced retained "
            "sanitized live artifacts for the MVP status consumer within this run; "
            f"underlying status decision: {status_decision}."
        )
    return original_detail


def _friend_answer_from_payload(
    payload: Mapping[str, Any],
    *,
    answer_text: str | None,
) -> str | None:
    if str(payload.get("decision") or "") != PASS_DECISION:
        return None
    dprime = _safe_mapping(payload.get("dprime_status"))
    material = _safe_mapping(dprime.get("assessment_material_ref"))
    claim = _clean_text(
        _safe_mapping(material.get("answer_component_claim")).get("claim"),
        limit=1_000,
    )
    return claim or answer_text


def _count_summary(payload: Mapping[str, Any]) -> dict[str, int]:
    selected = _safe_mapping(payload.get("selected_candidate"))
    source = _safe_mapping(payload.get("source_evidence_admission_ref"))
    retained_count = _bounded_int(payload.get("retained_search_candidate_count"))
    rank = _bounded_int(selected.get("rank"))
    readable = str(payload.get("fetch_read_handoff_status") or "") == (
        "retained_packet_verified"
    )
    return {
        "provider_calls_attempted": 1 if retained_count else 0,
        "provider_calls_completed": 1 if rank else 0,
        "search_tasks_attempted": 1 if retained_count else 0,
        "search_tasks_completed": 1 if rank else 0,
        "fetch_read_attempts": 1 if readable else 0,
        "fetch_read_completed": 1 if readable else 0,
        "evidence_ledger_admissions": (
            1 if source.get("status") == "custody_created" else 0
        ),
    }


def _source_entries_from_status_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    answer_path = _safe_mapping(payload.get("dprime_answer_path_ref"))
    display = _safe_mapping(answer_path.get("citation_source_display"))
    entries = []
    for entry in display.get("citation_source_entries") or []:
        safe = _safe_mapping(entry)
        text = _clean_text(safe.get("display_text"), limit=700)
        if text:
            entries.append(
                {
                    "display_text": text,
                    "url": _clean_text(safe.get("url"), limit=700),
                    "domain": _clean_text(safe.get("domain"), limit=260),
                    "product_correctness_claimed": False,
                }
            )
    return entries


def _source_display_entries(packet: Mapping[str, Any]) -> list[str]:
    return [
        str(entry.get("display_text"))
        for entry in packet.get("source_display_entries") or []
        if isinstance(entry, Mapping) and entry.get("display_text")
    ]


def _supported_query_class_boundary_line(packet: Mapping[str, Any]) -> str:
    boundary = _safe_mapping(packet.get("supported_query_class_boundary"))
    label = (
        _clean_text(boundary.get("profile_label"), limit=160)
        or "not recorded"
    )
    status = _clean_text(boundary.get("status"), limit=120) or "unknown"
    planning = boundary.get("arbitrary_query_planning_supported")
    planning_text = "false" if planning is False else "unknown"
    return f"{label}; status={status}; arbitrary query planning={planning_text}"


def _scrutineer_status(scrutineer: Mapping[str, Any]) -> str:
    if not scrutineer:
        return "not invoked; single-source lane"
    status = _clean_text(scrutineer.get("status"), limit=120) or "unknown"
    challenge = _clean_text(scrutineer.get("challenge_kind"), limit=120) or "none"
    return f"{status}; challenge={challenge}"


def _multi_source_status(multi: Mapping[str, Any]) -> str:
    if not multi:
        return "single-source lane"
    return (
        f"sources={_bounded_int(multi.get('source_count'))}; "
        f"conflict={_clean_text(multi.get('conflict_posture'), limit=120) or 'unknown'}; "
        f"currentness={_clean_text(multi.get('currentness_posture'), limit=120) or 'unknown'}"
    )


def _followup_status(followup: Mapping[str, Any]) -> str:
    if not followup:
        return "not requested"
    return _clean_text(followup.get("status"), limit=220) or "unknown"


def _followup_loop_count(followup: Mapping[str, Any]) -> int:
    if not followup:
        return 0
    status = str(followup.get("status") or "")
    return 1 if status and status != "not reached" else 0


def _packet_safe_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    safe = _json_safe(payload)
    _reject_packet_forbidden_material(safe)
    return safe


def _reject_packet_forbidden_material(value: Any) -> None:
    forbidden_keys = {
        "api_key",
        "auth",
        "authorization",
        "bounded_text",
        "cache_row",
        "cookie",
        "db_row",
        "env",
        "full_trace",
        "headers",
        "model_response",
        "page_content",
        "page_text",
        "password",
        "private_log",
        "prompt",
        "provider_payload",
        "raw_html",
        "raw_model_response",
        "raw_page_content",
        "raw_page_text",
        "raw_prompt",
        "raw_provider_payload",
        "raw_search_response",
        "secret",
        "token",
        "unbounded_text",
    }
    found = sorted(key for key in _collect_keys(value) if key in forbidden_keys)
    if found:
        raise ValueError("MVP packet contains forbidden material: " + ", ".join(found))
    lowered = json.dumps(_json_safe(value), sort_keys=True).casefold()
    for marker in ("api_key", "bearer ", "private_sentinel", "secret", "sk-"):
        if marker in lowered:
            raise ValueError("MVP packet contains private-looking material")
    for key, expected in RAW_FALSE_FLAGS.items():
        if isinstance(value, Mapping) and key in value and value.get(key) is not expected:
            raise ValueError(f"MVP packet must keep {key}=false")


def _contract_ref(*, query: str) -> dict[str, str]:
    digest = _digest_json({"phase": PHASE_NAME, "query": query, "kind": "contract"})
    return {
        "source": "current_answer_contract",
        "contract_version": "mvp-demo-current-contract-v1",
        "contract_digest": digest,
    }


def _handoff_ref(*, contract_ref: Mapping[str, Any], query: str) -> dict[str, Any]:
    digest = _digest_json(
        {
            "phase": PHASE_NAME,
            "query": query,
            "contract_digest": contract_ref.get("contract_digest"),
            "kind": "handoff",
        }
    )
    return {
        "handoff_id": "search-executor-handoff:mvp-demo-passport-fee",
        "handoff_digest": digest,
        "schema_version": "mvp-demo-search-executor-handoff-v1",
        "contract_parent_kind": "current_answer_contract",
        "parent_current_contract_ref": dict(contract_ref),
    }


def _run_id(value: str | None, *, prefix: str) -> str:
    if value:
        return _clean_run_id(value)
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _run_output_dir(root: Path, output_dir: str | Path, run_id: str) -> Path:
    raw = Path(output_dir)
    if not raw.is_absolute():
        raw = root / raw
    output_root = root / "output"
    resolved = raw.resolve()
    try:
        resolved.relative_to(output_root.resolve())
    except ValueError as exc:
        raise ValueError("MVP output dir must stay under repo-local output/") from exc
    target = resolved / _clean_run_id(run_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _clean_run_id(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in "-_:" else "-" for ch in value.strip())
    return text[:120] or f"mvp-{uuid.uuid4().hex[:12]}"


def _clean_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[:limit] if text else None


def _normalize_query(value: Any) -> str:
    return " ".join(str(value or "").split())


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _bounded_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed >= 0 else 0


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key).casefold() for key in value}
        for child in value.values():
            keys.update(_collect_keys(child))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for child in value:
            keys.update(_collect_keys(child))
        return keys
    return set()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(child) for key, child in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(child) for child in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _digest_json(value: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _path_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        normalized_path = os.path.normcase(str(path))
        normalized_root = os.path.normcase(str(root))
        return normalized_path == normalized_root or normalized_path.startswith(
            normalized_root.rstrip("\\/") + os.sep
        )


__all__ = [
    "BLOCKED_MVP_DEMO_QUERY_NOT_SUPPORTED",
    "BLOCKED_MVP_LIVE_DOGFOOD_ENTRYPOINT_MISSING",
    "DEFAULT_MVP_LIVE_OUTPUT_DIR",
    "DEFAULT_MVP_OUTPUT_DIR",
    "DEFAULT_MVP_QUERY",
    "MvpFriendOutputResult",
    "build_mvp_demo_output",
    "build_mvp_live_dogfood_status_output",
    "build_mvp_live_dogfood_status_output_from_semantic_status",
    "format_mvp_friend_output",
]
