"""AG-93C offline end-to-end replay review packet.

The packet consumes AG-93B golden tasks, normalized observed-run snapshots, and
AG-93B evaluation results. It is an offline review/export surface only: it does
not call providers, search, models, prompts, retrieval, persistence, or runtime
orchestration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.offline_golden_harness import (
    GoldenEvaluationResult,
    GoldenEvaluationStatus,
    OfflineGoldenTaskEvaluator,
    OfflineObservedRunSnapshot,
    evaluate_golden_task,
    load_observed_run_snapshots,
    normalize_observed_run_snapshot,
)
from core.offline_golden_tasks import GoldenTask, load_golden_tasks

OFFLINE_REPLAY_REVIEW_PACKET_SCHEMA_VERSION = "offline_replay_review_packet_ag93c_v1"
OFFLINE_REPLAY_REVIEW_PACKET_PHASE = "AG-93C"

_MAX_TEXT_CHARS = 1400
_MAX_RENDERED_ANSWER_CHARS = 700
_ACCEPTED_DISPOSITIONS = {"accepted", "partially_accepted"}
_NON_SATISFYING_DISPOSITIONS = {
    "rejected",
    "contextual",
    "lower_tier",
    "unreadable",
    "unfetchable",
    "dropped",
    "helper_assessed",
    "proposed",
}
_STRONG_SOURCE_CLASSES = {
    "official_current_rules",
    "legal_or_regulatory_text",
    "current_primary_or_official",
    "primary_source_documents",
    "archival_primary_text",
    "historical_legal_text",
}
_STRONG_SOURCE_TIERS = {"official", "primary", "canonical"}
_WEAK_SOURCE_CLASSES = {
    "reputable_secondary",
    "secondary",
    "secondary_only",
    "secondary_analysis",
    "social_signal",
    "social_or_forum",
    "community",
    "context",
}
_WEAK_SOURCE_TIERS = {
    "secondary",
    "trusted_community",
    "social_or_forum",
    "context",
    "analysis",
    "low_trust_commercial",
    "content_mill",
}
_BAD_CURRENTNESS = {"stale", "outdated", "historical_only", "off_topic", "not_current"}
_FORBIDDEN_KEY_MARKERS = (
    "api_key",
    "cache_blob",
    "credential",
    "db_row",
    "env",
    "full_raw_trace",
    "full_trace",
    "private_log",
    "provider_payload",
    "raw_",
    "secret",
    "token",
)
_FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "api_key",
        "cache",
        "cache_blob",
        "db_row",
        "full_raw_trace",
        "full_trace",
        "private_log",
        "raw_prompt",
        "raw_provider_payload",
        "secret",
    }
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)\b(api[_ -]?key|secret|token|password)\b\s*[:=]\s*[^,\s;]+"),
)


@dataclass(frozen=True, slots=True)
class PacketPrivacyReport:
    blocked_field_count: int = 0
    redacted_value_count: int = 0

    @property
    def warning(self) -> str | None:
        total = self.blocked_field_count + self.redacted_value_count
        if total <= 0:
            return None
        return f"{total} forbidden/private field or value item(s) blocked from packet output"

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked_or_redacted": bool(self.warning),
            "blocked_field_count": self.blocked_field_count,
            "redacted_value_count": self.redacted_value_count,
            "warning": self.warning,
        }


@dataclass(frozen=True, slots=True)
class OfflineReplayReviewPacket:
    task_id: str
    metadata: Mapping[str, Any]
    golden_expectations: Mapping[str, Any]
    corpus_availability: Mapping[str, Any]
    observed_contract: Mapping[str, Any]
    observed_evidence_ledger: Mapping[str, Any]
    observed_search_judgment: Mapping[str, Any]
    observed_sufficiency_judgment: Mapping[str, Any]
    observed_final_answer_packet: Mapping[str, Any]
    final_answer: Mapping[str, Any]
    evaluation: Mapping[str, Any]
    privacy: PacketPrivacyReport = field(default_factory=PacketPrivacyReport)
    schema_version: str = OFFLINE_REPLAY_REVIEW_PACKET_SCHEMA_VERSION
    phase: str = OFFLINE_REPLAY_REVIEW_PACKET_PHASE

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "task_id": self.task_id,
            "metadata": self.metadata,
            "golden_expectations": self.golden_expectations,
            "corpus_availability": self.corpus_availability,
            "observed_contract": self.observed_contract,
            "observed_evidence_ledger": self.observed_evidence_ledger,
            "observed_search_judgment": self.observed_search_judgment,
            "observed_sufficiency_judgment": self.observed_sufficiency_judgment,
            "observed_final_answer_packet": self.observed_final_answer_packet,
            "final_answer": self.final_answer,
            "ag93b_evaluation": self.evaluation,
            "privacy": self.privacy.to_dict(),
        }
        return _sanitize_payload(payload)[0]

    def human_summary(self) -> str:
        return render_offline_replay_review_packet_markdown(self)

    def to_markdown(self) -> str:
        return self.human_summary()


def build_offline_replay_review_packet(
    task: GoldenTask,
    observed: Mapping[str, Any] | OfflineObservedRunSnapshot | Any,
    evaluation_result: GoldenEvaluationResult | None = None,
) -> OfflineReplayReviewPacket:
    """Build one compact AG-93C review packet for a golden task replay."""

    snapshot = normalize_observed_run_snapshot(observed)
    result = evaluation_result or evaluate_golden_task(task, snapshot)
    privacy = _privacy_report(task, observed, result)
    packet = OfflineReplayReviewPacket(
        task_id=task.task_id,
        metadata=_metadata(task, result, privacy),
        golden_expectations=_golden_expectations(task),
        corpus_availability=_corpus_availability(task),
        observed_contract=_contract_summary(task, snapshot),
        observed_evidence_ledger=_ledger_summary(task, snapshot),
        observed_search_judgment=_search_summary(task, snapshot),
        observed_sufficiency_judgment=_sufficiency_summary(task, snapshot),
        observed_final_answer_packet=_final_packet_summary(task, snapshot),
        final_answer=_final_answer_summary(task, snapshot, result),
        evaluation=_evaluation_summary(result),
        privacy=privacy,
    )
    return packet


def render_offline_replay_review_packet_markdown(
    packet: OfflineReplayReviewPacket,
) -> str:
    payload = packet.to_dict()
    metadata = payload["metadata"]
    evaluation = payload["ag93b_evaluation"]
    ledger = payload["observed_evidence_ledger"]
    search = payload["observed_search_judgment"]
    sufficiency = payload["observed_sufficiency_judgment"]
    final_packet = payload["observed_final_answer_packet"]
    final_answer = payload["final_answer"]

    lines: list[str] = [
        f"# AG-93C Offline Replay Review Packet: {packet.task_id}",
        "",
        "## Metadata",
        f"- Status: {metadata.get('evaluation_status')} ({'PASS' if metadata.get('passed') else 'FAIL'})",
        f"- Family: {metadata.get('task_family')}",
        f"- Query: {metadata.get('query')}",
        f"- Failure statuses: {_join_or_none(metadata.get('failing_statuses'))}",
    ]
    if metadata.get("privacy_warning"):
        lines.append(f"- Privacy/output hygiene: {metadata['privacy_warning']}")

    lines.extend(
        [
            "",
            "## Golden Expectations",
            f"- Ingredients: {_render_items(payload['golden_expectations']['expected_answer_ingredients'], 'ingredient_id')}",
            f"- Source obligations: {_render_items(payload['golden_expectations']['expected_source_obligations'], 'requirement_id')}",
            f"- Search bounds: {payload['golden_expectations']['expected_search']}",
            f"- Sufficiency bounds: {payload['golden_expectations']['expected_sufficiency']}",
            f"- Final packet caveats: {_join_or_none(payload['golden_expectations']['expected_final_packet'].get('required_caveats'))}",
            f"- Prohibited upgrades: {_join_or_none(payload['golden_expectations']['expected_final_packet'].get('prohibited_upgrades'))}",
            "",
            "## Corpus / Sources",
            _render_sources(payload["corpus_availability"].get("sources", [])),
            "",
            "## Contract / Ledger",
            f"- Contract requirements carried: {_render_items(payload['observed_contract'].get('source_requirements', []), 'requirement_id')}",
            f"- Contract mismatches: {_render_items(payload['observed_contract'].get('mismatches', []), 'requirement_id')}",
            f"- Ledger candidates: {_render_items(ledger.get('candidate_records', []), 'source_id')}",
            f"- Admitted: {_join_or_none(ledger.get('admitted_source_ids'))}",
            f"- Rejected/non-satisfying: {_join_or_none(ledger.get('rejected_or_non_satisfying_source_ids'))}",
            f"- Satisfied requirements: {_join_or_none(ledger.get('satisfied_requirement_ids'))}",
            f"- Unsatisfied/partial requirements: {_join_or_none(ledger.get('unsatisfied_or_partial_requirement_ids'))}",
            f"- Custody gaps: {_render_items(ledger.get('custody_gaps', []), 'gap_type')}",
            f"- Source posture/custody warnings: {_render_warnings(ledger.get('warnings', []))}",
            "",
            "## Search / Sufficiency / Final Packet",
            f"- Search: {search.get('decision')} | attempts {search.get('search_attempt_count')} ({search.get('search_count_status')}); recovery {search.get('recovery_attempt_count')} ({search.get('recovery_count_status')})",
            f"- Search warnings: {_render_warnings(search.get('warnings', []))}",
            f"- Sufficiency: {sufficiency.get('decision')} -> {sufficiency.get('final_answer_posture')} ({sufficiency.get('posture_status')})",
            f"- Sufficiency warnings: {_render_warnings(sufficiency.get('warnings', []))}",
            f"- Final packet allowed evidence: {_join_or_none(final_packet.get('allowed_evidence_source_ids'))}",
            f"- Citation eligible: {_join_or_none(final_packet.get('citation_eligible_source_ids'))}",
            f"- Final evidence/citation custody: {final_packet.get('final_evidence_citation_custody_status')} ({'complete' if final_packet.get('final_evidence_citation_custody_complete') else 'incomplete'})",
            f"- Missing caveats/upgrades: {_join_or_none(final_packet.get('missing_caveats') + final_packet.get('missing_prohibited_upgrades'))}",
            f"- Final packet warnings: {_render_warnings(final_packet.get('warnings', []))}",
            "",
            "## Final Answer",
            f"> {_truncate(final_answer.get('text') or '', _MAX_RENDERED_ANSWER_CHARS)}",
            f"- Observed ingredients: {_join_or_none(final_answer.get('observed_ingredient_ids'))}",
            f"- Missing expected ingredients: {_join_or_none(final_answer.get('missing_expected_ingredient_ids'))}",
            f"- Observed claims: {_join_or_none(final_answer.get('observed_claim_ids'))}",
            f"- Unsupported claims: {_render_items(final_answer.get('visible_unsupported_claims', []), 'claim_id')}",
            f"- Citation alignment findings: {_render_items(final_answer.get('citation_alignment_findings', []), 'ingredient_id')}",
            "",
            "## AG-93B Evaluation Findings",
        ]
    )
    failing = evaluation.get("failing_findings", [])
    prose = evaluation.get("prose_style_notes", [])
    lines.append(
        "- Evidence/posture failures: "
        + (
            "; ".join(f"{item.get('status')}:{item.get('code')} - {item.get('message')}" for item in failing)
            if failing
            else "none"
        )
    )
    lines.append(
        "- Prose style notes (non-failing): "
        + ("; ".join(str(item.get("message")) for item in prose) if prose else "none")
    )
    sanitized_lines = _sanitize_payload(lines)[0]
    return "\n".join("" if item is None else str(item) for item in sanitized_lines)


def build_offline_replay_review_packets_from_fixture_paths(
    task_path: str | PathLike[str],
    snapshot_path: str | PathLike[str],
) -> dict[str, OfflineReplayReviewPacket]:
    tasks = {task.task_id: task for task in load_golden_tasks(task_path)}
    snapshots = load_observed_run_snapshots(snapshot_path)
    evaluator = OfflineGoldenTaskEvaluator()
    return {
        task_id: build_offline_replay_review_packet(
            task,
            snapshots[task_id],
            evaluator.evaluate(task, snapshots[task_id]),
        )
        for task_id, task in tasks.items()
        if task_id in snapshots
    }


def write_offline_replay_review_packet_json(
    packet: OfflineReplayReviewPacket,
    path: str | PathLike[str],
) -> None:
    Path(path).write_text(
        json.dumps(packet.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _metadata(
    task: GoldenTask,
    result: GoldenEvaluationResult,
    privacy: PacketPrivacyReport,
) -> dict[str, Any]:
    failing = [item for item in result.findings if item.failing]
    return {
        "schema_version": OFFLINE_REPLAY_REVIEW_PACKET_SCHEMA_VERSION,
        "phase": OFFLINE_REPLAY_REVIEW_PACKET_PHASE,
        "task_id": task.task_id,
        "task_family": task.family,
        "query": _clean_text(task.query),
        "evaluation_status": result.status.value,
        "passed": result.passed,
        "evaluation_statuses": list(result.statuses),
        "failing_statuses": list(dict.fromkeys(item.status.value for item in failing)),
        "failing_codes": list(dict.fromkeys(item.code for item in failing)),
        "prose_style_note_count": len(
            [item for item in result.findings if item.status is GoldenEvaluationStatus.PROSE_STYLE_NOTE]
        ),
        "privacy_warning": privacy.warning,
    }


def _golden_expectations(task: GoldenTask) -> dict[str, Any]:
    return {
        "expected_answer_ingredients": [item.to_dict() for item in task.expected_answer_ingredients],
        "expected_source_obligations": [item.to_dict() for item in task.source_obligations],
        "expected_contract_requirements": [item.to_dict() for item in task.expected_contract_requirements],
        "expected_ledger": task.expected_ledger.to_dict(),
        "expected_search": task.expected_search.to_dict(),
        "expected_sufficiency": task.expected_sufficiency.to_dict(),
        "expected_final_packet": task.expected_final_packet.to_dict(),
        "expected_citation_alignment": [item.to_dict() for item in task.citation_alignment],
    }


def _corpus_availability(task: GoldenTask) -> dict[str, Any]:
    return {
        "fixture_source_ids": [source.source_id for source in task.source_refs],
        "sources": [
            {
                "source_id": source.source_id,
                "title": source.title,
                "source_class": source.source_class,
                "source_tier": source.source_tier,
                "currentness": source.currentness,
                "supports_ingredient_ids": list(source.supports_ingredient_ids),
                "expected_roles": _source_expected_roles(task, source.source_id),
                "citation_eligible": source.citation_eligible,
            }
            for source in task.source_refs
        ],
    }


def _contract_summary(
    task: GoldenTask,
    snapshot: OfflineObservedRunSnapshot,
) -> dict[str, Any]:
    observed = _mapping_list(snapshot.contract_obligations.get("source_requirements"))
    by_id = {str(item.get("requirement_id") or ""): item for item in observed if item.get("requirement_id")}
    mismatches: list[dict[str, Any]] = []
    missing: list[str] = []
    for expected in task.expected_contract_requirements:
        record = by_id.get(expected.requirement_id)
        if record is None:
            missing.append(expected.requirement_id)
            continue
        deltas = {}
        for key, expected_value in (
            ("required_source_class", expected.required_source_class),
            ("required_source_tier", expected.required_source_tier),
            ("required_currentness", expected.required_currentness),
        ):
            if expected_value and record.get(key) != expected_value:
                deltas[key] = {"expected": expected_value, "observed": record.get(key)}
        if deltas:
            mismatches.append({"requirement_id": expected.requirement_id, "mismatches": deltas})
    return {
        "source_requirements": [_requirement_view(item) for item in observed],
        "required_source_classes": _unique(item.get("required_source_class") for item in observed),
        "required_source_tiers": _unique(item.get("required_source_tier") for item in observed),
        "required_currentness": _unique(item.get("required_currentness") for item in observed),
        "missing_expected_requirement_ids": missing,
        "mismatches": mismatches,
    }


def _ledger_summary(
    task: GoldenTask,
    snapshot: OfflineObservedRunSnapshot,
) -> dict[str, Any]:
    candidates = [_candidate_view(item) for item in _mapping_list(snapshot.evidence_ledger.get("candidate_records"))]
    requirements = [
        _requirement_view(item) for item in _mapping_list(snapshot.evidence_ledger.get("source_requirements"))
    ]
    gaps = [
        {
            "gap_type": _clean_text(item.get("gap_type")),
            "requirement_id": _clean_text(item.get("requirement_id")),
            "candidate_id": _clean_text(item.get("candidate_id")),
        }
        for item in _mapping_list(snapshot.evidence_ledger.get("custody_gaps"))
    ]
    satisfied = [
        item["requirement_id"]
        for item in requirements
        if item.get("status") == "satisfied" and item.get("requirement_id")
    ]
    unsatisfied_or_partial = [
        item["requirement_id"]
        for item in requirements
        if item.get("status") in {"unsatisfied", "partially_satisfied"} and item.get("requirement_id")
    ]
    admitted = [item["source_id"] for item in candidates if item.get("fact_disposition") in _ACCEPTED_DISPOSITIONS]
    rejected = [
        item["source_id"] for item in candidates if item.get("fact_disposition") in _NON_SATISFYING_DISPOSITIONS
    ]
    return {
        "candidate_records": candidates,
        "source_requirements": requirements,
        "admitted_source_ids": admitted,
        "rejected_or_non_satisfying_source_ids": rejected,
        "satisfied_requirement_ids": satisfied,
        "unsatisfied_or_partial_requirement_ids": unsatisfied_or_partial,
        "custody_gaps": gaps,
        "warnings": _ledger_warnings(task, snapshot),
    }


def _search_summary(
    task: GoldenTask,
    snapshot: OfflineObservedRunSnapshot,
) -> dict[str, Any]:
    expected = task.expected_search
    search_status = _bounds_status(
        snapshot.search_attempt_count,
        expected.min_attempts,
        expected.max_attempts,
    )
    recovery_status = _bounds_status(
        snapshot.recovery_attempt_count,
        expected.min_recovery_attempts,
        expected.max_recovery_attempts,
    )
    warnings: list[dict[str, Any]] = []
    missing_requirements = _missing_ledger_requirement_ids(snapshot)
    decision = str(snapshot.search_judgment.get("decision") or "")
    if decision == "stop_satisfied" and missing_requirements:
        warnings.append(
            {
                "code": "STOPPED_SATISFIED_WITH_LEDGER_GAPS",
                "missing_requirement_ids": missing_requirements,
            }
        )
    if search_status != "within_bounds":
        warnings.append(
            {
                "code": "SEARCH_COUNT_OUT_OF_BOUNDS",
                "observed": snapshot.search_attempt_count,
                "expected_min": expected.min_attempts,
                "expected_max": expected.max_attempts,
            }
        )
    if recovery_status != "within_bounds":
        warnings.append(
            {
                "code": "RECOVERY_COUNT_OUT_OF_BOUNDS",
                "observed": snapshot.recovery_attempt_count,
                "expected_min": expected.min_recovery_attempts,
                "expected_max": expected.max_recovery_attempts,
            }
        )
    return {
        "decision": decision,
        "classifications": _strings(snapshot.search_judgment.get("classifications")),
        "target_source_classes": _strings(snapshot.search_judgment.get("target_source_classes")),
        "search_attempt_count": snapshot.search_attempt_count,
        "recovery_attempt_count": snapshot.recovery_attempt_count,
        "expected_bounds": expected.to_dict(),
        "search_count_status": search_status,
        "recovery_count_status": recovery_status,
        "stop_continue_recover_posture": _search_plausibility(decision, missing_requirements),
        "warnings": warnings,
    }


def _sufficiency_summary(
    task: GoldenTask,
    snapshot: OfflineObservedRunSnapshot,
) -> dict[str, Any]:
    expected = task.expected_sufficiency
    decision = str(snapshot.sufficiency_judgment.get("decision") or "")
    posture = str(snapshot.sufficiency_judgment.get("final_answer_posture") or "")
    missing = _missing_ledger_requirement_ids(snapshot)
    warnings: list[dict[str, Any]] = []
    if (decision == "ready_direct" or posture == "direct_answer") and missing:
        warnings.append(
            {
                "code": "DIRECT_POSTURE_WITH_MISSING_OBLIGATIONS",
                "missing_requirement_ids": missing,
            }
        )
    status = "matches_expected_bounds"
    if expected.allowed_decisions and decision not in expected.allowed_decisions:
        status = "decision_out_of_bounds"
    if expected.allowed_postures and posture not in expected.allowed_postures:
        status = "posture_out_of_bounds"
    return {
        "decision": decision,
        "final_answer_posture": posture,
        "expected_decisions": list(expected.allowed_decisions),
        "expected_postures": list(expected.allowed_postures),
        "posture_status": status,
        "missing_or_partial_requirement_ids": missing,
        "mandatory_caveats": _strings(snapshot.sufficiency_judgment.get("mandatory_caveats")),
        "prohibited_upgrades": _strings(snapshot.sufficiency_judgment.get("prohibited_upgrades")),
        "warnings": warnings,
    }


def _final_packet_summary(
    task: GoldenTask,
    snapshot: OfflineObservedRunSnapshot,
) -> dict[str, Any]:
    expected = task.expected_final_packet
    caveats = _strings(snapshot.final_answer_packet.get("mandatory_caveats"))
    upgrades = _strings(snapshot.final_answer_packet.get("prohibited_upgrades"))
    allowed = snapshot.final_packet_evidence_source_ids("evidence_allowed")
    citation_eligible = snapshot.final_packet_evidence_source_ids("citation_eligible")
    missing_caveats = [item for item in expected.required_caveats if item not in caveats]
    missing_upgrades = [item for item in expected.prohibited_upgrades if item not in upgrades]
    missing_allowed = [item for item in expected.allowed_evidence_source_ids if item not in allowed]
    missing_citation = [item for item in expected.citation_eligible_source_ids if item not in citation_eligible]
    custody = _mapping(snapshot.final_evidence_citation_custody)
    warnings = [{"code": "MANDATORY_CAVEAT_MISSING", "caveat": item} for item in missing_caveats]
    warnings.extend(
        {"code": "PROHIBITED_UPGRADE_GUARDRAIL_MISSING", "prohibited_upgrade": item} for item in missing_upgrades
    )
    warnings.extend({"code": "ALLOWED_EVIDENCE_SOURCE_MISSING", "source_id": item} for item in missing_allowed)
    warnings.extend({"code": "CITATION_ELIGIBLE_SOURCE_MISSING", "source_id": item} for item in missing_citation)
    if custody.get("status") == "legacy_gap_observed":
        warnings.append(
            {
                "code": "FINAL_EVIDENCE_CITATION_LEGACY_GAP_OBSERVED",
                "legacy_gap_types": custody.get("legacy_controller_custody", {}).get("legacy_gap_types", []),
            }
        )
    return {
        "readiness_status": _clean_text(snapshot.final_answer_packet.get("readiness_status")),
        "allowed_evidence_source_ids": list(allowed),
        "citation_eligible_source_ids": list(citation_eligible),
        "final_evidence_citation_custody_status": _clean_text(custody.get("status")) or "not_observed",
        "final_evidence_citation_custody_complete": bool(custody.get("custody_complete")),
        "final_evidence_citation_custody": custody,
        "mandatory_caveats": list(caveats),
        "prohibited_upgrades": list(upgrades),
        "missing_caveats": missing_caveats,
        "missing_prohibited_upgrades": missing_upgrades,
        "missing_allowed_evidence_source_ids": missing_allowed,
        "missing_citation_eligible_source_ids": missing_citation,
        "packet_guardrails": {
            "mandatory_caveats_present": not missing_caveats,
            "prohibited_upgrades_present": not missing_upgrades,
            "allowed_evidence_sources_present": not missing_allowed,
            "citation_eligible_sources_present": not missing_citation,
        },
        "warnings": warnings,
    }


def _final_answer_summary(
    task: GoldenTask,
    snapshot: OfflineObservedRunSnapshot,
    result: GoldenEvaluationResult,
) -> dict[str, Any]:
    observed_ingredients = set(snapshot.final_answer_ingredient_ids)
    missing = [
        ingredient.ingredient_id
        for ingredient in task.expected_answer_ingredients
        if ingredient.required_in_final_answer
        and ingredient.ingredient_id not in observed_ingredients
        and not _all_phrases_present(snapshot.final_answer_text, ingredient.required_phrases)
    ]
    visible_unsupported = []
    for claim in task.forbidden_unsupported_claims:
        if claim.claim_id in snapshot.final_answer_claim_ids or any(
            _contains(snapshot.final_answer_text, phrase) for phrase in claim.phrases
        ):
            visible_unsupported.append(claim.to_dict())
    citation_findings = []
    observed_citations = snapshot.citation_source_ids_by_ingredient()
    for expected in task.citation_alignment:
        observed = list(observed_citations.get(expected.ingredient_id, ()))
        if not set(expected.source_ids).issubset(set(observed)):
            citation_findings.append(
                {
                    "ingredient_id": expected.ingredient_id,
                    "expected_source_ids": list(expected.source_ids),
                    "observed_source_ids": observed,
                }
            )
    eval_citation_findings = [
        item.to_dict() for item in result.findings if item.status is GoldenEvaluationStatus.CITATION_ALIGNMENT_FAILED
    ]
    return {
        "text": _clean_text(snapshot.final_answer_text),
        "observed_ingredient_ids": list(snapshot.final_answer_ingredient_ids),
        "observed_claim_ids": list(snapshot.final_answer_claim_ids),
        "missing_expected_ingredient_ids": missing,
        "visible_unsupported_claims": visible_unsupported,
        "citations": [_sanitize_payload(dict(item))[0] for item in snapshot.final_citations],
        "citation_source_ids_by_ingredient": {key: list(value) for key, value in observed_citations.items()},
        "citation_alignment_findings": citation_findings,
        "ag93b_citation_alignment_findings": eval_citation_findings,
    }


def _evaluation_summary(result: GoldenEvaluationResult) -> dict[str, Any]:
    findings = [_sanitize_payload(item.to_dict())[0] for item in result.findings]
    failing = [item for item in findings if item.get("failing")]
    prose = [item for item in findings if item.get("status") == GoldenEvaluationStatus.PROSE_STYLE_NOTE.value]
    return {
        "status": result.status.value,
        "passed": result.passed,
        "finding_count": len(findings),
        "failing_finding_count": len(failing),
        "findings": findings,
        "failing_findings": failing,
        "prose_style_notes": prose,
    }


def _ledger_warnings(
    task: GoldenTask,
    snapshot: OfflineObservedRunSnapshot,
) -> list[dict[str, Any]]:
    candidates = snapshot.source_candidate_by_id()
    refs = task.source_ref_by_id
    requirements = snapshot.ledger_requirement_by_id()
    warnings: list[dict[str, Any]] = []
    for obligation in task.source_obligations:
        requirement = requirements.get(obligation.requirement_id)
        if not requirement:
            continue
        for source_id in _strings(requirement.get("linked_candidate_ids")):
            candidate = candidates.get(source_id, {})
            ref = refs.get(source_id)
            observed_class = candidate.get("source_class") or getattr(ref, "source_class", None)
            observed_tier = candidate.get("source_tier") or getattr(ref, "source_tier", None)
            observed_currentness = (
                candidate.get("currentness_signal") or candidate.get("currentness") or getattr(ref, "currentness", None)
            )
            if source_id in obligation.forbidden_source_ids:
                warnings.append(
                    {
                        "code": "FORBIDDEN_SOURCE_SATISFIED_OBLIGATION",
                        "requirement_id": obligation.requirement_id,
                        "source_id": source_id,
                    }
                )
            if _strong_obligation(obligation) and (
                observed_class in _WEAK_SOURCE_CLASSES
                or observed_tier in _WEAK_SOURCE_TIERS
                or observed_currentness in _BAD_CURRENTNESS
            ):
                warnings.append(
                    {
                        "code": "LOWER_TIER_WEAK_STALE_OR_OFF_TOPIC_SOURCE_SATISFIED_STRONGER_OBLIGATION",
                        "requirement_id": obligation.requirement_id,
                        "source_id": source_id,
                        "observed_source_class": observed_class,
                        "observed_source_tier": observed_tier,
                        "observed_currentness": observed_currentness,
                    }
                )
            mismatches = {}
            for key, expected, observed in (
                ("source_class", obligation.required_source_class, observed_class),
                ("source_tier", obligation.required_source_tier, observed_tier),
                ("currentness", obligation.required_currentness, observed_currentness),
            ):
                if expected and expected != "not_applicable" and observed != expected:
                    mismatches[key] = {"expected": expected, "observed": observed}
            if mismatches and not obligation.lower_tier_allowed:
                warnings.append(
                    {
                        "code": "SOURCE_POSTURE_MISMATCH",
                        "requirement_id": obligation.requirement_id,
                        "source_id": source_id,
                        "mismatches": mismatches,
                    }
                )
    return warnings


def _source_expected_roles(task: GoldenTask, source_id: str) -> list[str]:
    roles: list[str] = []
    for obligation in task.source_obligations:
        if source_id in obligation.satisfying_source_ids:
            roles.append("expected_satisfying")
        if source_id in obligation.forbidden_source_ids:
            roles.append("rejected_or_forbidden")
    if source_id in task.expected_ledger.rejected_source_ids:
        roles.append("expected_rejected")
    if source_id in task.expected_ledger.non_satisfying_source_ids:
        roles.append("expected_non_satisfying")
    ref = task.source_ref_by_id.get(source_id)
    if ref is not None:
        if ref.currentness in _BAD_CURRENTNESS:
            roles.append("stale")
        if ref.source_class in _WEAK_SOURCE_CLASSES or ref.source_tier in _WEAK_SOURCE_TIERS:
            roles.append("weak_or_contextual")
    return list(dict.fromkeys(roles or ["contextual"]))


def _privacy_report(
    task: GoldenTask,
    observed: Any,
    result: GoldenEvaluationResult,
) -> PacketPrivacyReport:
    blocked = 0
    redacted = 0
    for value in (task.to_dict(), _project_observed_for_privacy(observed), result.to_dict()):
        _, report = _sanitize_payload(value)
        blocked += report.blocked_field_count
        redacted += report.redacted_value_count
    return PacketPrivacyReport(blocked_field_count=blocked, redacted_value_count=redacted)


def _project_observed_for_privacy(observed: Any) -> Any:
    if isinstance(observed, Mapping):
        return dict(observed)
    if isinstance(observed, OfflineObservedRunSnapshot):
        return {
            "task_id": observed.task_id,
            "contract": dict(observed.contract_obligations),
            "ledger": dict(observed.evidence_ledger),
            "search": dict(observed.search_judgment),
            "sufficiency": dict(observed.sufficiency_judgment),
            "final_packet": dict(observed.final_answer_packet),
            "final_answer": {
                "text": observed.final_answer_text,
                "ingredient_ids": list(observed.final_answer_ingredient_ids),
                "claim_ids": list(observed.final_answer_claim_ids),
                "citations": list(observed.final_citations),
            },
        }
    if hasattr(observed, "to_dict"):
        return observed.to_dict()
    return {}


def _sanitize_payload(value: Any) -> tuple[Any, PacketPrivacyReport]:
    blocked = 0
    redacted = 0

    def walk(item: Any) -> Any:
        nonlocal blocked, redacted
        if item is None or isinstance(item, (bool, int, float)):
            return item
        if isinstance(item, str):
            text = _clean_text(item)
            if any(pattern.search(text or "") for pattern in _SECRET_VALUE_PATTERNS):
                redacted += 1
                return "[redacted private value]"
            return text
        if isinstance(item, Mapping):
            out: dict[str, Any] = {}
            for key, child in item.items():
                key_text = str(key or "")
                if _is_forbidden_key(key_text):
                    blocked += 1
                    continue
                out[key_text] = walk(child)
            return out
        if isinstance(item, (list, tuple, set, frozenset)):
            ordered = list(item)
            if isinstance(item, (set, frozenset)):
                ordered = sorted(ordered, key=str)
            return [walk(child) for child in ordered[:80]]
        return _clean_text(item)

    sanitized = walk(value)
    return sanitized, PacketPrivacyReport(blocked, redacted)


def _is_forbidden_key(key: str) -> bool:
    lowered = key.strip().casefold()
    return lowered in _FORBIDDEN_EXACT_KEYS or any(marker in lowered for marker in _FORBIDDEN_KEY_MARKERS)


def _candidate_view(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_id": _source_id(record),
        "source_class": _clean_text(record.get("source_class")),
        "source_tier": _clean_text(record.get("source_tier")),
        "currentness": _clean_text(record.get("currentness_signal") or record.get("currentness")),
        "fact_disposition": _clean_text(record.get("fact_disposition") or record.get("disposition")),
        "eligible_for_stronger_obligation": bool(record.get("eligible_for_stronger_obligation")),
    }


def _requirement_view(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": _clean_text(record.get("requirement_id")),
        "status": _clean_text(record.get("status")),
        "required_source_class": _clean_text(record.get("required_source_class")),
        "required_source_tier": _clean_text(record.get("required_source_tier")),
        "required_currentness": _clean_text(record.get("required_currentness")),
        "linked_candidate_ids": _strings(record.get("linked_candidate_ids")),
    }


def _missing_ledger_requirement_ids(snapshot: OfflineObservedRunSnapshot) -> list[str]:
    return [
        str(item.get("requirement_id"))
        for item in snapshot.ledger_requirement_by_id().values()
        if item.get("status") in {"unsatisfied", "partially_satisfied"} and item.get("requirement_id")
    ]


def _bounds_status(observed: int, minimum: int, maximum: int | None) -> str:
    if observed < minimum:
        return "under_minimum"
    if maximum is not None and observed > maximum:
        return "over_maximum"
    return "within_bounds"


def _search_plausibility(decision: str, missing_requirement_ids: Sequence[str]) -> str:
    if decision == "stop_satisfied" and missing_requirement_ids:
        return "implausible_stop_with_ledger_gaps"
    if decision in {"stop_insufficient", "recovery_required_but_exhausted"} and missing_requirement_ids:
        return "plausible_insufficient_or_recovery_exhausted"
    if decision in {"continue_targeted_search", "recover_missing_official_current"} and missing_requirement_ids:
        return "plausible_recovery_against_gaps"
    return "no_obvious_mismatch"


def _strong_obligation(obligation: Any) -> bool:
    return (
        obligation.required_source_class in _STRONG_SOURCE_CLASSES
        or obligation.required_source_tier in _STRONG_SOURCE_TIERS
        or obligation.required_currentness == "current"
    )


def _source_id(record: Mapping[str, Any]) -> str:
    for key in ("source_id", "candidate_id", "evidence_id", "citation_id"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        return [dict(value)]
    if isinstance(value, (list, tuple)):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        raw = list(value)
    else:
        raw = [value]
    out: list[str] = []
    for item in raw:
        text = _clean_text(item, limit=180)
        if text and text not in out:
            out.append(text)
    return out


def _unique(values: Any) -> list[str]:
    out: list[str] = []
    for item in values:
        text = _clean_text(item, limit=180)
        if text and text not in out:
            out.append(text)
    return out


def _clean_text(value: Any, *, limit: int = _MAX_TEXT_CHARS) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    return text[:limit]


def _contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def _all_phrases_present(text: str, phrases: Sequence[str]) -> bool:
    return bool(phrases) and all(_contains(text, phrase) for phrase in phrases)


def _truncate(text: str, limit: int) -> str:
    clean = _clean_text(text, limit=limit + 1) or ""
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _join_or_none(values: Any) -> str:
    items = _strings(values)
    return ", ".join(items) if items else "none"


def _render_items(items: Any, key: str) -> str:
    if not items:
        return "none"
    rendered = []
    for item in items:
        if isinstance(item, Mapping):
            rendered.append(str(item.get(key) or item.get("code") or item))
        else:
            rendered.append(str(item))
    return ", ".join(rendered[:12]) if rendered else "none"


def _render_sources(sources: Sequence[Mapping[str, Any]]) -> str:
    if not sources:
        return "- none"
    lines = []
    for source in sources:
        lines.append(
            "- "
            f"{source.get('source_id')}: {source.get('source_class')}/"
            f"{source.get('source_tier')}/{source.get('currentness')} "
            f"supports={_join_or_none(source.get('supports_ingredient_ids'))} "
            f"roles={_join_or_none(source.get('expected_roles'))}"
        )
    return "\n".join(lines)


def _render_warnings(warnings: Any) -> str:
    if not warnings:
        return "none"
    rendered = []
    for item in warnings:
        if isinstance(item, Mapping):
            code = item.get("code") or "warning"
            target = item.get("requirement_id") or item.get("source_id") or item.get("caveat")
            rendered.append(f"{code}{f' ({target})' if target else ''}")
        else:
            rendered.append(str(item))
    return "; ".join(rendered[:12])


__all__ = [
    "OFFLINE_REPLAY_REVIEW_PACKET_PHASE",
    "OFFLINE_REPLAY_REVIEW_PACKET_SCHEMA_VERSION",
    "OfflineReplayReviewPacket",
    "PacketPrivacyReport",
    "build_offline_replay_review_packet",
    "build_offline_replay_review_packets_from_fixture_paths",
    "render_offline_replay_review_packet_markdown",
    "write_offline_replay_review_packet_json",
]
