"""AG-93B offline golden-task evaluator.

The evaluator consumes fixture-backed golden tasks plus normalized observed-run
snapshots. It grades truth-throughput and source posture through the current
RunAuthority chain:

RunAuthorityContract -> EvidenceLedger -> SearchJudgment ->
SufficiencyJudgment -> FinalAnswerPacket -> AuthorExecutor.

It is intentionally deterministic and offline-only. It does not call providers,
models, search, prompts, retrieval, persistence, or the pipeline orchestrator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Mapping

from core.offline_golden_tasks import GoldenTask

OFFLINE_GOLDEN_HARNESS_SCHEMA_VERSION = "offline_golden_harness_ag93b_v1"


class GoldenEvaluationStatus(str, Enum):
    PASS = "PASS"
    ANSWER_INGREDIENT_FAILED = "ANSWER_INGREDIENT_FAILED"
    SOURCE_POSTURE_FAILED = "SOURCE_POSTURE_FAILED"
    LEDGER_CUSTODY_FAILED = "LEDGER_CUSTODY_FAILED"
    SEARCH_JUDGMENT_FAILED = "SEARCH_JUDGMENT_FAILED"
    SUFFICIENCY_POSTURE_FAILED = "SUFFICIENCY_POSTURE_FAILED"
    FINAL_PACKET_FAILED = "FINAL_PACKET_FAILED"
    FINAL_ANSWER_OMISSION = "FINAL_ANSWER_OMISSION"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    CITATION_ALIGNMENT_FAILED = "CITATION_ALIGNMENT_FAILED"
    SEARCH_COUNT_OUT_OF_BOUNDS = "SEARCH_COUNT_OUT_OF_BOUNDS"
    PROSE_STYLE_NOTE = "PROSE_STYLE_NOTE"


_FAILING_PRIORITY = (
    GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED,
    GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
    GoldenEvaluationStatus.LEDGER_CUSTODY_FAILED,
    GoldenEvaluationStatus.SEARCH_JUDGMENT_FAILED,
    GoldenEvaluationStatus.SUFFICIENCY_POSTURE_FAILED,
    GoldenEvaluationStatus.FINAL_PACKET_FAILED,
    GoldenEvaluationStatus.FINAL_ANSWER_OMISSION,
    GoldenEvaluationStatus.UNSUPPORTED_CLAIM,
    GoldenEvaluationStatus.CITATION_ALIGNMENT_FAILED,
    GoldenEvaluationStatus.SEARCH_COUNT_OUT_OF_BOUNDS,
)
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


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _strings(value: Any) -> tuple[str, ...]:
    out: list[str] = []
    for item in _list(value):
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return tuple(out)


def _projection(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_projection"):
        projected = value.to_projection()
        if hasattr(projected, "to_dict"):
            return _mapping(projected.to_dict())
        return _mapping(projected)
    if hasattr(value, "to_dict"):
        return _mapping(value.to_dict())
    return {}


def _first_projection(payload: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        if key in payload:
            projected = _projection(payload.get(key))
            if projected:
                return projected
    return {}


def _contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def _source_id(record: Mapping[str, Any]) -> str:
    for key in ("source_id", "candidate_id", "evidence_id", "citation_id"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _currentness(record: Mapping[str, Any]) -> str:
    return str(
        record.get("currentness")
        or record.get("currentness_signal")
        or record.get("required_currentness")
        or ""
    )


def _norm_status(value: GoldenEvaluationStatus | str) -> GoldenEvaluationStatus:
    if isinstance(value, GoldenEvaluationStatus):
        return value
    return GoldenEvaluationStatus(str(value))


@dataclass(frozen=True, slots=True)
class GoldenEvaluationFinding:
    status: GoldenEvaluationStatus | str
    code: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)
    failing: bool = True

    def __post_init__(self) -> None:
        status = _norm_status(self.status)
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "failing",
            bool(self.failing and status is not GoldenEvaluationStatus.PROSE_STYLE_NOTE),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
            "failing": self.failing,
        }


@dataclass(frozen=True, slots=True)
class GoldenEvaluationResult:
    task_id: str
    status: GoldenEvaluationStatus
    findings: tuple[GoldenEvaluationFinding, ...]

    @property
    def passed(self) -> bool:
        return self.status is GoldenEvaluationStatus.PASS

    @property
    def failing_findings(self) -> tuple[GoldenEvaluationFinding, ...]:
        return tuple(item for item in self.findings if item.failing)

    @property
    def statuses(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.status.value for item in self.findings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": OFFLINE_GOLDEN_HARNESS_SCHEMA_VERSION,
            "task_id": self.task_id,
            "status": self.status.value,
            "passed": self.passed,
            "finding_count": len(self.findings),
            "failing_finding_count": len(self.failing_findings),
            "findings": [item.to_dict() for item in self.findings],
        }

    def human_summary(self) -> str:
        if self.passed:
            notes = [
                item.message
                for item in self.findings
                if item.status is GoldenEvaluationStatus.PROSE_STYLE_NOTE
            ]
            suffix = f" ({len(notes)} prose note{'s' if len(notes) != 1 else ''})" if notes else ""
            return f"PASS {self.task_id}{suffix}"
        first = self.failing_findings[0]
        extra = len(self.failing_findings) - 1
        suffix = f"; +{extra} more failing finding{'s' if extra != 1 else ''}" if extra else ""
        return f"{self.status.value} {self.task_id}: {first.message}{suffix}"


@dataclass(frozen=True, slots=True)
class OfflineObservedRunSnapshot:
    task_id: str | None = None
    contract_obligations: Mapping[str, Any] = field(default_factory=dict)
    evidence_ledger: Mapping[str, Any] = field(default_factory=dict)
    search_judgment: Mapping[str, Any] = field(default_factory=dict)
    sufficiency_judgment: Mapping[str, Any] = field(default_factory=dict)
    final_answer_packet: Mapping[str, Any] = field(default_factory=dict)
    final_answer_text: str = ""
    final_answer_ingredient_ids: tuple[str, ...] = ()
    final_answer_claim_ids: tuple[str, ...] = ()
    final_citations: tuple[Mapping[str, Any], ...] = ()
    search_attempt_count: int = 0
    recovery_attempt_count: int = 0
    style_notes: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OfflineObservedRunSnapshot":
        final_answer = _mapping(payload.get("final_answer"))
        search = _first_projection(
            payload,
            "search",
            "search_judgment",
            "search_judgment_projection",
            "run_authority_search_judgment",
        )
        search_attempt_count = payload.get("search_attempt_count")
        if search_attempt_count is None:
            search_attempt_count = search.get("attempt_count") or search.get("search_attempt_count") or 0
        recovery_attempt_count = payload.get("recovery_attempt_count")
        if recovery_attempt_count is None:
            recovery_attempt_count = (
                search.get("recovery_attempt_count")
                or search.get("recovery_attempts")
                or search.get("budget", {}).get("recovery_attempts", 0)
            )
        citations = payload.get("final_citations")
        if citations is None:
            citations = final_answer.get("citations")
        return cls(
            task_id=payload.get("task_id"),
            contract_obligations=_first_projection(
                payload,
                "contract",
                "contract_projection",
                "run_contract_projection",
                "run_authority_contract",
            ),
            evidence_ledger=_first_projection(
                payload,
                "ledger",
                "evidence_ledger",
                "evidence_ledger_projection",
            ),
            search_judgment=search,
            sufficiency_judgment=_first_projection(
                payload,
                "sufficiency",
                "sufficiency_judgment",
                "sufficiency_judgment_projection",
            ),
            final_answer_packet=_first_projection(
                payload,
                "final_packet",
                "final_answer_packet",
                "final_answer_packet_projection",
            ),
            final_answer_text=str(
                payload.get("final_answer_text") or final_answer.get("text") or ""
            ),
            final_answer_ingredient_ids=_strings(
                payload.get("final_answer_ingredient_ids")
                or final_answer.get("ingredient_ids")
            ),
            final_answer_claim_ids=_strings(
                payload.get("final_answer_claim_ids") or final_answer.get("claim_ids")
            ),
            final_citations=tuple(
                dict(item) for item in _list(citations) if isinstance(item, Mapping)
            ),
            search_attempt_count=int(search_attempt_count or 0),
            recovery_attempt_count=int(recovery_attempt_count or 0),
            style_notes=_strings(payload.get("style_notes") or final_answer.get("style_notes")),
        )

    def source_candidate_by_id(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for item in _list(self.evidence_ledger.get("candidate_records")):
            if not isinstance(item, Mapping):
                continue
            record = dict(item)
            for key in ("candidate_id", "source_id"):
                value = record.get(key)
                if value not in (None, ""):
                    out[str(value)] = record
        return out

    def ledger_requirement_by_id(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for item in _list(self.evidence_ledger.get("source_requirements")):
            if isinstance(item, Mapping) and item.get("requirement_id"):
                out[str(item["requirement_id"])] = dict(item)
        return out

    def citation_source_ids_by_ingredient(self) -> dict[str, tuple[str, ...]]:
        out: dict[str, tuple[str, ...]] = {}
        for item in self.final_citations:
            ingredient_id = str(item.get("ingredient_id") or item.get("fact_id") or "")
            if ingredient_id:
                out[ingredient_id] = _strings(item.get("source_ids") or item.get("source_id"))
        return out

    def final_packet_evidence_source_ids(self, key: str) -> tuple[str, ...]:
        source_ids: list[str] = []
        for item in _list(self.final_answer_packet.get(key)):
            if isinstance(item, Mapping):
                source_id = _source_id(item)
                if source_id and source_id not in source_ids:
                    source_ids.append(source_id)
        return tuple(source_ids)


def normalize_observed_run_snapshot(value: Any) -> OfflineObservedRunSnapshot:
    if isinstance(value, OfflineObservedRunSnapshot):
        return value
    if isinstance(value, Mapping):
        return OfflineObservedRunSnapshot.from_mapping(value)
    if hasattr(value, "to_trace_projection"):
        return OfflineObservedRunSnapshot.from_mapping(value.to_trace_projection().to_dict())
    if hasattr(value, "to_trace_fragment"):
        fragment = _projection(value.to_trace_fragment())
        run_kernel = _mapping(fragment.get("run_kernel"))
        return OfflineObservedRunSnapshot.from_mapping(run_kernel or fragment)
    if hasattr(value, "to_dict"):
        return OfflineObservedRunSnapshot.from_mapping(value.to_dict())
    raise TypeError(f"unsupported observed run snapshot: {type(value)!r}")


def load_observed_run_snapshots(path: str | PathLike[str]) -> dict[str, OfflineObservedRunSnapshot]:
    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{fixture_path}: expected JSON object")
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, list):
        raise ValueError(f"{fixture_path}: expected snapshots list")
    out: dict[str, OfflineObservedRunSnapshot] = {}
    for item in snapshots:
        if not isinstance(item, Mapping):
            continue
        snapshot = OfflineObservedRunSnapshot.from_mapping(item)
        if not snapshot.task_id:
            raise ValueError(f"{fixture_path}: observed snapshot missing task_id")
        out[snapshot.task_id] = snapshot
    return out


class OfflineGoldenTaskEvaluator:
    """Deterministic truth-throughput evaluator for one golden task snapshot."""

    def evaluate(
        self,
        task: GoldenTask,
        observed: Mapping[str, Any] | OfflineObservedRunSnapshot,
    ) -> GoldenEvaluationResult:
        snapshot = normalize_observed_run_snapshot(observed)
        findings: list[GoldenEvaluationFinding] = []
        self._check_task_identity(task, snapshot, findings)
        self._check_contract_requirements(task, snapshot, findings)
        self._check_ingredients(task, snapshot, findings)
        self._check_ledger_expectations(task, snapshot, findings)
        self._check_source_posture(task, snapshot, findings)
        self._check_search(task, snapshot, findings)
        self._check_sufficiency(task, snapshot, findings)
        self._check_final_packet(task, snapshot, findings)
        self._check_final_answer(task, snapshot, findings)
        self._check_citation_alignment(task, snapshot, findings)
        self._check_prose_notes(task, snapshot, findings)
        return GoldenEvaluationResult(
            task_id=task.task_id,
            status=self._overall_status(findings),
            findings=tuple(findings),
        )

    def _add(
        self,
        findings: list[GoldenEvaluationFinding],
        status: GoldenEvaluationStatus,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
        *,
        failing: bool = True,
    ) -> None:
        findings.append(
            GoldenEvaluationFinding(
                status=status,
                code=code,
                message=message,
                details=dict(details or {}),
                failing=failing,
            )
        )

    def _overall_status(
        self,
        findings: list[GoldenEvaluationFinding],
    ) -> GoldenEvaluationStatus:
        failing = {item.status for item in findings if item.failing}
        for status in _FAILING_PRIORITY:
            if status in failing:
                return status
        return GoldenEvaluationStatus.PASS

    def _check_task_identity(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        if snapshot.task_id and snapshot.task_id != task.task_id:
            self._add(
                findings,
                GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED,
                "task_id_mismatch",
                "observed snapshot task_id does not match golden task",
                {"expected": task.task_id, "observed": snapshot.task_id},
            )

    def _check_contract_requirements(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        requirements = {
            str(item.get("requirement_id")): item
            for item in _list(snapshot.contract_obligations.get("source_requirements"))
            if isinstance(item, Mapping) and item.get("requirement_id")
        }
        for expected in task.expected_contract_requirements:
            observed = requirements.get(expected.requirement_id)
            if observed is None:
                self._add(
                    findings,
                    GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED,
                    "contract_requirement_missing",
                    "RunAuthorityContract did not carry an expected source requirement",
                    {"requirement_id": expected.requirement_id},
                )
                continue
            mismatches = {}
            for observed_key, expected_value in (
                ("required_source_class", expected.required_source_class),
                ("required_source_tier", expected.required_source_tier),
                ("required_currentness", expected.required_currentness),
            ):
                if expected_value and observed.get(observed_key) != expected_value:
                    mismatches[observed_key] = {
                        "expected": expected_value,
                        "observed": observed.get(observed_key),
                    }
            if mismatches:
                self._add(
                    findings,
                    GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
                    "contract_requirement_mismatch",
                    "RunAuthorityContract weakened or changed an expected source obligation",
                    {"requirement_id": expected.requirement_id, "mismatches": mismatches},
                )

    def _check_ingredients(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        source_refs = task.source_ref_by_id
        candidates = snapshot.source_candidate_by_id()
        for ingredient in task.expected_answer_ingredients:
            missing_from_corpus = [
                source_id for source_id in ingredient.source_ids if source_id not in source_refs
            ]
            if missing_from_corpus:
                self._add(
                    findings,
                    GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED,
                    "ingredient_source_unavailable",
                    "expected answer ingredient source is absent from the fixture corpus",
                    {
                        "ingredient_id": ingredient.ingredient_id,
                        "missing_source_ids": missing_from_corpus,
                    },
                )
            if ingredient.may_be_unknown or not ingredient.required_in_final_answer:
                continue
            admitted = [
                source_id
                for source_id in ingredient.source_ids
                if str(candidates.get(source_id, {}).get("fact_disposition")) in _ACCEPTED_DISPOSITIONS
            ]
            if ingredient.source_ids and not admitted:
                self._add(
                    findings,
                    GoldenEvaluationStatus.ANSWER_INGREDIENT_FAILED,
                    "ingredient_not_admitted",
                    "expected answer ingredient was available but not admitted by EvidenceLedger",
                    {
                        "ingredient_id": ingredient.ingredient_id,
                        "source_ids": list(ingredient.source_ids),
                    },
                )
            if ingredient.source_bound_numeric:
                citations = snapshot.citation_source_ids_by_ingredient().get(
                    ingredient.ingredient_id,
                    (),
                )
                eligible = set(ingredient.source_ids).intersection(citations)
                if ingredient.numeric_value and ingredient.ingredient_id in snapshot.final_answer_ingredient_ids:
                    if not eligible:
                        self._add(
                            findings,
                            GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
                            "source_bound_numeric_without_eligible_source",
                            "source-bound numeric ingredient is visible without eligible source support",
                            {
                                "ingredient_id": ingredient.ingredient_id,
                                "expected_source_ids": list(ingredient.source_ids),
                                "observed_citation_source_ids": list(citations),
                            },
                        )

    def _check_ledger_expectations(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        candidates = snapshot.source_candidate_by_id()
        requirements = snapshot.ledger_requirement_by_id()
        gap_types = {
            str(item.get("gap_type"))
            for item in _list(snapshot.evidence_ledger.get("custody_gaps"))
            if isinstance(item, Mapping) and item.get("gap_type")
        }
        for source_id in task.expected_ledger.admitted_source_ids:
            disposition = str(candidates.get(source_id, {}).get("fact_disposition"))
            if disposition not in _ACCEPTED_DISPOSITIONS:
                self._add(
                    findings,
                    GoldenEvaluationStatus.LEDGER_CUSTODY_FAILED,
                    "expected_source_not_admitted",
                    "EvidenceLedger did not admit an expected source",
                    {"source_id": source_id, "observed_disposition": disposition},
                )
        for requirement_id in task.expected_ledger.satisfied_requirement_ids:
            requirement = requirements.get(requirement_id)
            if requirement is None or requirement.get("status") != "satisfied":
                self._add(
                    findings,
                    GoldenEvaluationStatus.LEDGER_CUSTODY_FAILED,
                    "expected_requirement_not_satisfied",
                    "EvidenceLedger did not satisfy an expected requirement",
                    {
                        "requirement_id": requirement_id,
                        "observed_status": requirement.get("status") if requirement else None,
                    },
                )
        for gap_type in task.expected_ledger.expected_gap_types:
            if gap_type not in gap_types:
                self._add(
                    findings,
                    GoldenEvaluationStatus.LEDGER_CUSTODY_FAILED,
                    "expected_gap_missing",
                    "EvidenceLedger did not preserve an expected custody gap",
                    {"gap_type": gap_type},
                )
        for source_id in task.expected_ledger.rejected_source_ids:
            disposition = str(candidates.get(source_id, {}).get("fact_disposition"))
            if disposition not in _NON_SATISFYING_DISPOSITIONS:
                self._add(
                    findings,
                    GoldenEvaluationStatus.LEDGER_CUSTODY_FAILED,
                    "expected_rejection_missing",
                    "EvidenceLedger did not keep a rejected/non-satisfying source distinct",
                    {"source_id": source_id, "observed_disposition": disposition},
                )
        satisfied_links = self._satisfied_requirement_links(snapshot)
        for source_id in task.expected_ledger.non_satisfying_source_ids:
            if source_id in satisfied_links:
                self._add(
                    findings,
                    GoldenEvaluationStatus.LEDGER_CUSTODY_FAILED,
                    "non_satisfying_source_satisfied_requirement",
                    "EvidenceLedger let a non-satisfying source satisfy a requirement",
                    {"source_id": source_id, "requirement_ids": sorted(satisfied_links[source_id])},
                )

    def _check_source_posture(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        candidates = snapshot.source_candidate_by_id()
        source_refs = task.source_ref_by_id
        requirements = snapshot.ledger_requirement_by_id()
        for obligation in task.source_obligations:
            requirement = requirements.get(obligation.requirement_id)
            if requirement is None:
                if obligation.must_be_satisfied:
                    self._add(
                        findings,
                        GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
                        "source_obligation_missing_from_ledger",
                        "expected source obligation is missing from EvidenceLedger",
                        {"requirement_id": obligation.requirement_id},
                    )
                continue
            status = str(requirement.get("status") or "")
            linked_ids = _strings(requirement.get("linked_candidate_ids"))
            if obligation.must_be_satisfied and status != "satisfied":
                self._add(
                    findings,
                    GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
                    "required_source_obligation_unsatisfied",
                    "required source obligation is not satisfied",
                    {"requirement_id": obligation.requirement_id, "status": status},
                )
            satisfying = set(obligation.satisfying_source_ids)
            if obligation.must_be_satisfied and satisfying and not satisfying.intersection(linked_ids):
                self._add(
                    findings,
                    GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
                    "wrong_source_satisfied_obligation",
                    "source obligation was not satisfied by an expected eligible source",
                    {
                        "requirement_id": obligation.requirement_id,
                        "expected_source_ids": sorted(satisfying),
                        "linked_candidate_ids": list(linked_ids),
                    },
                )
            for source_id in linked_ids:
                candidate = candidates.get(source_id, {})
                source_ref = source_refs.get(source_id)
                if source_id in obligation.forbidden_source_ids:
                    self._add(
                        findings,
                        GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
                        "forbidden_source_satisfied_obligation",
                        "forbidden source was upgraded into satisfying a stronger obligation",
                        {"requirement_id": obligation.requirement_id, "source_id": source_id},
                    )
                self._check_source_matches_obligation(
                    obligation=obligation,
                    candidate=candidate,
                    source_ref=source_ref,
                    source_id=source_id,
                    findings=findings,
                )

    def _check_source_matches_obligation(
        self,
        *,
        obligation: Any,
        candidate: Mapping[str, Any],
        source_ref: Any,
        source_id: str,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        observed_class = candidate.get("source_class") or getattr(source_ref, "source_class", None)
        observed_tier = candidate.get("source_tier") or getattr(source_ref, "source_tier", None)
        observed_currentness = _currentness(candidate) or getattr(source_ref, "currentness", None)
        mismatches: dict[str, dict[str, Any]] = {}
        if obligation.required_source_class and observed_class != obligation.required_source_class:
            mismatches["source_class"] = {
                "expected": obligation.required_source_class,
                "observed": observed_class,
            }
        if obligation.required_source_tier and observed_tier != obligation.required_source_tier:
            mismatches["source_tier"] = {
                "expected": obligation.required_source_tier,
                "observed": observed_tier,
            }
        if (
            obligation.required_currentness
            and obligation.required_currentness != "not_applicable"
            and observed_currentness != obligation.required_currentness
        ):
            mismatches["currentness"] = {
                "expected": obligation.required_currentness,
                "observed": observed_currentness,
            }
        if mismatches and not obligation.lower_tier_allowed:
            self._add(
                findings,
                GoldenEvaluationStatus.SOURCE_POSTURE_FAILED,
                "source_posture_mismatch",
                "linked source does not satisfy required class/tier/currentness",
                {
                    "requirement_id": obligation.requirement_id,
                    "source_id": source_id,
                    "mismatches": mismatches,
                },
            )

    def _check_search(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        expected = task.expected_search
        decision = str(snapshot.search_judgment.get("decision") or "")
        if expected.allowed_decisions and decision not in expected.allowed_decisions:
            self._add(
                findings,
                GoldenEvaluationStatus.SEARCH_JUDGMENT_FAILED,
                "unexpected_search_decision",
                "SearchJudgment decision does not match expected posture",
                {"expected": list(expected.allowed_decisions), "observed": decision},
            )
        if snapshot.search_attempt_count < expected.min_attempts:
            self._add_search_count_failure(
                findings,
                "search_attempts_below_minimum",
                snapshot.search_attempt_count,
                expected.min_attempts,
                "min_attempts",
            )
        if expected.max_attempts is not None and snapshot.search_attempt_count > expected.max_attempts:
            self._add_search_count_failure(
                findings,
                "search_attempts_above_maximum",
                snapshot.search_attempt_count,
                expected.max_attempts,
                "max_attempts",
            )
        if snapshot.recovery_attempt_count < expected.min_recovery_attempts:
            self._add_search_count_failure(
                findings,
                "recovery_attempts_below_minimum",
                snapshot.recovery_attempt_count,
                expected.min_recovery_attempts,
                "min_recovery_attempts",
            )
        if (
            expected.max_recovery_attempts is not None
            and snapshot.recovery_attempt_count > expected.max_recovery_attempts
        ):
            self._add_search_count_failure(
                findings,
                "recovery_attempts_above_maximum",
                snapshot.recovery_attempt_count,
                expected.max_recovery_attempts,
                "max_recovery_attempts",
            )
        target_classes = set(_strings(snapshot.search_judgment.get("target_source_classes")))
        missing_targets = [
            item for item in expected.required_target_source_classes if item not in target_classes
        ]
        if missing_targets:
            self._add(
                findings,
                GoldenEvaluationStatus.SEARCH_JUDGMENT_FAILED,
                "search_target_missing",
                "SearchJudgment did not target an expected missing source class",
                {"missing_target_source_classes": missing_targets},
            )
        if decision == "stop_satisfied":
            missing_requirements = [
                item
                for item in snapshot.ledger_requirement_by_id().values()
                if item.get("status") in {"unsatisfied", "partially_satisfied"}
            ]
            if missing_requirements:
                self._add(
                    findings,
                    GoldenEvaluationStatus.SEARCH_JUDGMENT_FAILED,
                    "stopped_satisfied_with_ledger_gaps",
                    "SearchJudgment stopped satisfied while EvidenceLedger requirements were missing",
                    {
                        "missing_requirement_ids": [
                            item.get("requirement_id") for item in missing_requirements
                        ]
                    },
                )

    def _add_search_count_failure(
        self,
        findings: list[GoldenEvaluationFinding],
        code: str,
        observed: int,
        expected: int,
        bound: str,
    ) -> None:
        self._add(
            findings,
            GoldenEvaluationStatus.SEARCH_COUNT_OUT_OF_BOUNDS,
            code,
            "search/recovery count is outside expected bounds",
            {"observed": observed, bound: expected},
        )

    def _check_sufficiency(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        expected = task.expected_sufficiency
        decision = str(snapshot.sufficiency_judgment.get("decision") or "")
        posture = str(snapshot.sufficiency_judgment.get("final_answer_posture") or "")
        if expected.allowed_decisions and decision not in expected.allowed_decisions:
            self._add(
                findings,
                GoldenEvaluationStatus.SUFFICIENCY_POSTURE_FAILED,
                "unexpected_sufficiency_decision",
                "SufficiencyJudgment decision does not match expected final posture",
                {"expected": list(expected.allowed_decisions), "observed": decision},
            )
        if expected.allowed_postures and posture not in expected.allowed_postures:
            self._add(
                findings,
                GoldenEvaluationStatus.SUFFICIENCY_POSTURE_FAILED,
                "unexpected_sufficiency_posture",
                "SufficiencyJudgment final answer posture does not match expectation",
                {"expected": list(expected.allowed_postures), "observed": posture},
            )
        if decision == "ready_direct" or posture == "direct_answer":
            missing_requirements = [
                item
                for item in snapshot.ledger_requirement_by_id().values()
                if item.get("status") in {"unsatisfied", "partially_satisfied"}
            ]
            if missing_requirements:
                self._add(
                    findings,
                    GoldenEvaluationStatus.SUFFICIENCY_POSTURE_FAILED,
                    "direct_posture_with_missing_obligations",
                    "SufficiencyJudgment allowed direct posture with missing required evidence",
                    {
                        "missing_requirement_ids": [
                            item.get("requirement_id") for item in missing_requirements
                        ]
                    },
                )

    def _check_final_packet(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        expected = task.expected_final_packet
        caveats = set(_strings(snapshot.final_answer_packet.get("mandatory_caveats")))
        upgrades = set(_strings(snapshot.final_answer_packet.get("prohibited_upgrades")))
        for caveat in expected.required_caveats:
            if caveat not in caveats:
                self._add(
                    findings,
                    GoldenEvaluationStatus.FINAL_PACKET_FAILED,
                    "mandatory_caveat_missing",
                    "FinalAnswerPacket dropped a mandatory caveat",
                    {"caveat": caveat},
                )
        for upgrade in expected.prohibited_upgrades:
            if upgrade not in upgrades:
                self._add(
                    findings,
                    GoldenEvaluationStatus.FINAL_PACKET_FAILED,
                    "prohibited_upgrade_missing",
                    "FinalAnswerPacket dropped a prohibited-upgrade guardrail",
                    {"prohibited_upgrade": upgrade},
                )
        allowed_sources = set(snapshot.final_packet_evidence_source_ids("evidence_allowed"))
        missing_allowed = [
            item for item in expected.allowed_evidence_source_ids if item not in allowed_sources
        ]
        if missing_allowed:
            self._add(
                findings,
                GoldenEvaluationStatus.FINAL_PACKET_FAILED,
                "allowed_evidence_missing",
                "FinalAnswerPacket allowed-evidence list is missing expected source ids",
                {"missing_source_ids": missing_allowed},
            )
        citation_sources = set(snapshot.final_packet_evidence_source_ids("citation_eligible"))
        missing_citation = [
            item for item in expected.citation_eligible_source_ids if item not in citation_sources
        ]
        if missing_citation:
            self._add(
                findings,
                GoldenEvaluationStatus.FINAL_PACKET_FAILED,
                "citation_eligibility_missing",
                "FinalAnswerPacket citation eligibility is missing expected source ids",
                {"missing_source_ids": missing_citation},
            )

    def _check_final_answer(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        ingredient_ids = set(snapshot.final_answer_ingredient_ids)
        for ingredient in task.expected_answer_ingredients:
            if not ingredient.required_in_final_answer:
                continue
            if ingredient.ingredient_id in ingredient_ids:
                continue
            if ingredient.required_phrases and all(
                _contains(snapshot.final_answer_text, phrase)
                for phrase in ingredient.required_phrases
            ):
                continue
            self._add(
                findings,
                GoldenEvaluationStatus.FINAL_ANSWER_OMISSION,
                "ingredient_missing_from_final_answer",
                "final answer omitted an expected answer ingredient",
                {"ingredient_id": ingredient.ingredient_id},
            )
        claim_ids = set(snapshot.final_answer_claim_ids)
        for claim in task.forbidden_unsupported_claims:
            phrase_hit = any(_contains(snapshot.final_answer_text, phrase) for phrase in claim.phrases)
            if claim.claim_id in claim_ids or phrase_hit:
                self._add(
                    findings,
                    GoldenEvaluationStatus.UNSUPPORTED_CLAIM,
                    "forbidden_unsupported_claim_visible",
                    "final answer included a forbidden unsupported claim",
                    {"claim_id": claim.claim_id},
                )

    def _check_citation_alignment(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        citations = snapshot.citation_source_ids_by_ingredient()
        for expected in task.citation_alignment:
            observed = set(citations.get(expected.ingredient_id, ()))
            required = set(expected.source_ids)
            if not required.issubset(observed):
                self._add(
                    findings,
                    GoldenEvaluationStatus.CITATION_ALIGNMENT_FAILED,
                    "citation_sources_misaligned",
                    "final citation refs do not align with the fact they support",
                    {
                        "ingredient_id": expected.ingredient_id,
                        "expected_source_ids": sorted(required),
                        "observed_source_ids": sorted(observed),
                    },
                )

    def _check_prose_notes(
        self,
        task: GoldenTask,
        snapshot: OfflineObservedRunSnapshot,
        findings: list[GoldenEvaluationFinding],
    ) -> None:
        for note in (*task.prose_style_notes, *snapshot.style_notes):
            self._add(
                findings,
                GoldenEvaluationStatus.PROSE_STYLE_NOTE,
                "prose_style_note",
                str(note),
                failing=False,
            )

    def _satisfied_requirement_links(
        self,
        snapshot: OfflineObservedRunSnapshot,
    ) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for requirement in snapshot.ledger_requirement_by_id().values():
            if requirement.get("status") != "satisfied":
                continue
            req_id = str(requirement.get("requirement_id") or "")
            for source_id in _strings(requirement.get("linked_candidate_ids")):
                out.setdefault(source_id, set()).add(req_id)
        return out


def evaluate_golden_task(
    task: GoldenTask,
    observed: Mapping[str, Any] | OfflineObservedRunSnapshot,
) -> GoldenEvaluationResult:
    return OfflineGoldenTaskEvaluator().evaluate(task, observed)


__all__ = [
    "OFFLINE_GOLDEN_HARNESS_SCHEMA_VERSION",
    "GoldenEvaluationFinding",
    "GoldenEvaluationResult",
    "GoldenEvaluationStatus",
    "OfflineGoldenTaskEvaluator",
    "OfflineObservedRunSnapshot",
    "evaluate_golden_task",
    "load_observed_run_snapshots",
    "normalize_observed_run_snapshot",
]
