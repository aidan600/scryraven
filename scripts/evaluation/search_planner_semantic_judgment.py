"""Provider-neutral, teacher-free SearchPlanner semantic judgment contract."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

SEMANTIC_JUDGMENT_CONTRACT_VERSION = "search_planner_semantic_judgment_contract_v1"
SEMANTIC_STATUSES = frozenset({"MET", "NOT_MET", "REVIEW_REQUIRED"})
_MECHANICAL_POSTURES = frozenset({"PASS", "FAIL", "NOT_REACHED", "REVIEW_REQUIRED"})
_ISSUE_KINDS = frozenset({"MISSING", "INCORRECT", "UNSUPPORTED", "MISINTERPRETED", "AUTHORITY_UPGRADE"})
_REQUIREMENT_KINDS = frozenset(
    {
        "FACT",
        "RELATIONSHIP",
        "AUTHORITY",
        "ANSWER_CAPABILITY",
        "OTHER",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "answer_key",
        "api_key",
        "authorization_header",
        "chain_of_thought",
        "credential",
        "expected_answer",
        "expected_component_ids",
        "fixture_aliases",
        "full_prompt",
        "model_response",
        "private_log",
        "prompt_text",
        "provider_payload",
        "raw_model_response",
        "raw_prompt",
        "raw_provider_payload",
        "reasoning_trace",
        "secret",
        "teacher_answer",
        "teacher_ids",
        "teacher_payload",
    }
)


class SemanticJudgmentContractError(ValueError):
    """Raised when a semantic request or supplied judgment is not lawful."""


@dataclass(frozen=True, slots=True)
class EssentialRequirement:
    requirement_id: str
    normalized_requirement: str
    requirement_kind: str = "OTHER"

    def __post_init__(self) -> None:
        _bounded_text(self.requirement_id, "requirement_id", 160)
        _bounded_text(
            self.normalized_requirement,
            "normalized_requirement",
            1000,
        )
        if self.requirement_kind not in _REQUIREMENT_KINDS:
            raise SemanticJudgmentContractError("requirement_kind is unsupported")


@dataclass(frozen=True, slots=True)
class SemanticJudgmentRequest:
    request_id: str
    judge_contract_version: str
    normalized_user_request_digest: str
    input_packet_digest: str
    proposal_digest: str
    deterministic_result_ref: str
    evaluation_budget_identity: str
    normalized_user_request: str
    planner_input: Mapping[str, Any]
    essential_requirements: tuple[EssentialRequirement, ...]
    proposed_plan: Mapping[str, Any]
    mechanical_validation_summary: Mapping[str, Any]
    essential_architecture_constraints: tuple[str, ...]
    prohibited_upgrades_or_shortcuts: tuple[str, ...]
    diagnostic_mode: bool = False

    def __post_init__(self) -> None:
        if self.judge_contract_version != SEMANTIC_JUDGMENT_CONTRACT_VERSION:
            raise SemanticJudgmentContractError("semantic contract version is unsupported")
        _bounded_text(self.request_id, "request_id", 160)
        for value, label in (
            (
                self.normalized_user_request_digest,
                "normalized_user_request_digest",
            ),
            (self.input_packet_digest, "input_packet_digest"),
            (self.proposal_digest, "proposal_digest"),
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise SemanticJudgmentContractError(f"{label} must be one SHA-256 digest")
        if self.request_id != f"semantic-judgment:{self.input_packet_digest}":
            raise SemanticJudgmentContractError("request identity must bind the input packet digest")
        if not re.fullmatch(
            r"mechanical-result:[0-9a-f]{64}",
            self.deterministic_result_ref,
        ):
            raise SemanticJudgmentContractError("deterministic_result_ref is invalid")
        _bounded_text(
            self.evaluation_budget_identity,
            "evaluation_budget_identity",
            240,
        )
        _bounded_text(
            self.normalized_user_request,
            "normalized_user_request",
            4000,
        )
        if self.normalized_user_request_digest != _digest(self.normalized_user_request):
            raise SemanticJudgmentContractError(
                "normalized request digest does not cover the supplied request"
            )
        if self.proposal_digest != _digest(self.proposed_plan):
            raise SemanticJudgmentContractError(
                "proposal digest does not cover the supplied proposal"
            )
        ids = [item.requirement_id for item in self.essential_requirements]
        if not ids or len(ids) != len(set(ids)):
            raise SemanticJudgmentContractError("essential requirements must be nonempty and unique")
        for value in (
            self.planner_input,
            self.proposed_plan,
            self.mechanical_validation_summary,
        ):
            _reject_forbidden_material(value)
        for label, values in (
            (
                "essential_architecture_constraints",
                self.essential_architecture_constraints,
            ),
            (
                "prohibited_upgrades_or_shortcuts",
                self.prohibited_upgrades_or_shortcuts,
            ),
        ):
            if not values:
                raise SemanticJudgmentContractError(f"{label} must be explicit")
            for item in values:
                _bounded_text(item, label, 1000)
        mechanical = str(self.mechanical_validation_summary.get("overall_posture") or "")
        if mechanical not in _MECHANICAL_POSTURES:
            raise SemanticJudgmentContractError(
                "mechanical validation summary posture is unsupported"
            )
        deterministic_result_ref = str(
            self.mechanical_validation_summary.get("result_id") or ""
        )
        if deterministic_result_ref != self.deterministic_result_ref:
            raise SemanticJudgmentContractError(
                "mechanical validation summary result identity differs"
            )
        if (
            self.mechanical_validation_summary.get("owner")
            != "CanonicalSearchPlannerMechanicalAuthority"
        ):
            raise SemanticJudgmentContractError(
                "mechanical validation summary owner is invalid"
            )
        if (
            self.mechanical_validation_summary.get("product_proposal_digest")
            != self.proposal_digest
        ):
            raise SemanticJudgmentContractError(
                "semantic proposal differs from the canonical mechanical proposal"
            )
        if mechanical != "PASS" and not self.diagnostic_mode:
            raise SemanticJudgmentContractError(
                "semantic judgment requires mechanical PASS unless explicitly diagnostic"
            )
        if self.input_packet_digest != _digest(_request_material(self)):
            raise SemanticJudgmentContractError(
                "semantic input packet digest does not cover the request contract"
            )

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RequirementMapping:
    requirement_id: str
    proposal_paths: tuple[str, ...]
    bounded_explanation: str


@dataclass(frozen=True, slots=True)
class SemanticIssue:
    requirement_id: str
    issue_kind: str
    proposal_paths: tuple[str, ...]
    answer_blocking: bool
    bounded_explanation: str


@dataclass(frozen=True, slots=True)
class SemanticAmbiguity:
    requirement_id: str
    precise_ambiguity: str
    competing_interpretations: tuple[str, ...]
    proposal_paths: tuple[str, ...]
    smallest_review_action: str


@dataclass(frozen=True, slots=True)
class SemanticPassJudgment:
    status: str
    requirement_mappings: tuple[RequirementMapping, ...] = ()
    issues: tuple[SemanticIssue, ...] = ()
    ambiguities: tuple[SemanticAmbiguity, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticRequirementFinding:
    requirement_id: str
    requirement_kind: str
    status: str
    proposal_paths: tuple[str, ...]
    issue_kind: str | None
    bounded_explanation: str
    competing_interpretations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.requirement_kind not in _REQUIREMENT_KINDS:
            raise SemanticJudgmentContractError("semantic finding requirement kind is unsupported")
        if self.status not in SEMANTIC_STATUSES:
            raise SemanticJudgmentContractError("semantic finding status is unsupported")
        _bounded_text(
            self.bounded_explanation,
            "semantic finding explanation",
            1000,
        )
        if not self.proposal_paths:
            raise SemanticJudgmentContractError(
                "semantic findings must cite proposal evidence"
            )
        if self.status == "NOT_MET" and self.issue_kind not in _ISSUE_KINDS:
            raise SemanticJudgmentContractError(
                "NOT_MET findings require an exact issue kind"
            )
        if self.status != "NOT_MET" and self.issue_kind is not None:
            raise SemanticJudgmentContractError(
                "only NOT_MET findings may carry an issue kind"
            )


@dataclass(frozen=True, slots=True)
class SemanticEvidenceRef:
    requirement_id: str
    proposal_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        _bounded_text(self.requirement_id, "evidence requirement_id", 160)
        if not self.proposal_paths:
            raise SemanticJudgmentContractError(
                "semantic evidence must cite proposal material"
            )


@dataclass(frozen=True, slots=True)
class AnswerCapabilityFinding:
    status: str
    requirement_ids: tuple[str, ...]
    bounded_explanation: str

    def __post_init__(self) -> None:
        if self.status not in SEMANTIC_STATUSES:
            raise SemanticJudgmentContractError("answer capability status is unsupported")
        _bounded_text(
            self.bounded_explanation,
            "answer capability explanation",
            1000,
        )


@dataclass(frozen=True, slots=True)
class SemanticJudgmentResult:
    judge_contract_version: str
    owner: str
    request_id: str
    input_packet_digest: str
    proposal_digest: str
    deterministic_result_ref: str
    final_status: str
    requirement_mappings: tuple[RequirementMapping, ...]
    issues: tuple[SemanticIssue, ...]
    ambiguities: tuple[SemanticAmbiguity, ...]
    primary_judgment: SemanticPassJudgment
    adversarial_challenge: SemanticPassJudgment
    requirement_findings: tuple[SemanticRequirementFinding, ...]
    necessary_fact_findings: tuple[SemanticRequirementFinding, ...]
    necessary_relationship_findings: tuple[SemanticRequirementFinding, ...]
    authority_findings: tuple[SemanticRequirementFinding, ...]
    answer_capability: AnswerCapabilityFinding
    bounded_evidence: tuple[SemanticEvidenceRef, ...]
    mechanical_posture_seen: str
    diagnostic_only: bool
    provider_selected: bool = False
    model_selected: bool = False
    live_call_count: int = 0

    def __post_init__(self) -> None:
        if self.judge_contract_version != SEMANTIC_JUDGMENT_CONTRACT_VERSION:
            raise SemanticJudgmentContractError("semantic result contract version is unsupported")
        if self.owner != "SearchPlannerSemanticJudgment":
            raise SemanticJudgmentContractError("semantic result owner is invalid")
        if self.request_id != f"semantic-judgment:{self.input_packet_digest}":
            raise SemanticJudgmentContractError("semantic result request identity is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.input_packet_digest):
            raise SemanticJudgmentContractError("semantic result input digest is invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.proposal_digest):
            raise SemanticJudgmentContractError("semantic result proposal digest is invalid")
        if not re.fullmatch(
            r"mechanical-result:[0-9a-f]{64}",
            self.deterministic_result_ref,
        ):
            raise SemanticJudgmentContractError("semantic result mechanical reference is invalid")
        if self.final_status not in SEMANTIC_STATUSES:
            raise SemanticJudgmentContractError("semantic result status is unsupported")
        if (
            self.primary_judgment.status not in SEMANTIC_STATUSES
            or self.adversarial_challenge.status not in SEMANTIC_STATUSES
        ):
            raise SemanticJudgmentContractError(
                "semantic pass status is unsupported"
            )
        _validate_result_pass_shape(
            self.primary_judgment,
            label="primary",
        )
        _validate_result_pass_shape(
            self.adversarial_challenge,
            label="adversarial",
        )
        passes_agree = _materially_agree(
            self.primary_judgment,
            self.adversarial_challenge,
        )
        expected_status = (
            self.primary_judgment.status
            if passes_agree
            else "REVIEW_REQUIRED"
        )
        if self.final_status != expected_status:
            raise SemanticJudgmentContractError(
                "semantic final status does not preserve the two-pass decision"
            )
        if passes_agree:
            expected_projection = (
                self.primary_judgment.requirement_mappings,
                self.primary_judgment.issues,
                self.primary_judgment.ambiguities,
            )
        else:
            expected_projection = (
                (),
                (),
                self.ambiguities,
            )
            if (
                len(self.ambiguities) != 1
                or self.ambiguities[0].requirement_id
                != "two_pass_disagreement"
            ):
                raise SemanticJudgmentContractError(
                    "two-pass disagreement requires one explicit ambiguity"
                )
        if (
            self.requirement_mappings,
            self.issues,
            self.ambiguities,
        ) != expected_projection:
            raise SemanticJudgmentContractError(
                "semantic result projection differs from its two passes"
            )
        if self.mechanical_posture_seen not in _MECHANICAL_POSTURES:
            raise SemanticJudgmentContractError(
                "semantic result mechanical posture is unsupported"
            )
        if self.diagnostic_only != (self.mechanical_posture_seen != "PASS"):
            raise SemanticJudgmentContractError(
                "semantic diagnostic label must preserve mechanical non-pass"
            )
        if not self.requirement_findings or not self.bounded_evidence:
            raise SemanticJudgmentContractError(
                "semantic result requires bounded findings and evidence"
            )
        _validate_result_findings(self)
        if self.provider_selected or self.model_selected or self.live_call_count:
            raise SemanticJudgmentContractError("offline semantic result cannot select or call a model")

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


class ScriptedSemanticJudgeAdapter:
    """Test-only two-pass adapter; it executes no provider or model code."""

    test_only = True

    def __init__(
        self,
        *,
        primary: SemanticPassJudgment,
        adversarial: SemanticPassJudgment,
    ) -> None:
        self._primary = primary
        self._adversarial = adversarial
        self.invocation_count = 0

    def judge(self, request: SemanticJudgmentRequest) -> SemanticJudgmentResult:
        request.__post_init__()
        self.invocation_count += 1
        primary = _validate_pass(request, self._primary, label="primary")
        adversarial = _validate_pass(request, self._adversarial, label="adversarial")
        mechanical = str(request.mechanical_validation_summary.get("overall_posture") or "")
        if not _materially_agree(primary, adversarial):
            result_status = "REVIEW_REQUIRED"
            mappings: tuple[RequirementMapping, ...] = ()
            issues: tuple[SemanticIssue, ...] = ()
            evidence_paths = _pass_evidence_paths(primary, adversarial)
            ambiguities = (
                SemanticAmbiguity(
                    requirement_id="two_pass_disagreement",
                    precise_ambiguity=(
                        "Primary and adversarial semantic passes reached materially different postures."
                    ),
                    competing_interpretations=(
                        f"primary:{primary.status}:{_pass_identity(primary)}",
                        f"adversarial:{adversarial.status}:{_pass_identity(adversarial)}",
                    ),
                    proposal_paths=evidence_paths,
                    smallest_review_action=(
                        "Obtain one independent decision on the conflicting "
                        "requirement-to-proposal evidence."
                    ),
                ),
            )
        else:
            result_status = primary.status
            mappings = primary.requirement_mappings
            issues = primary.issues
            ambiguities = primary.ambiguities
        findings = _build_requirement_findings(
            request=request,
            status=result_status,
            mappings=mappings,
            issues=issues,
            ambiguities=ambiguities,
        )
        answer_findings = tuple(item for item in findings if item.requirement_kind == "ANSWER_CAPABILITY")
        evidence = tuple(
            SemanticEvidenceRef(
                requirement_id=item.requirement_id,
                proposal_paths=item.proposal_paths,
            )
            for item in findings
        )
        return SemanticJudgmentResult(
            judge_contract_version=SEMANTIC_JUDGMENT_CONTRACT_VERSION,
            owner="SearchPlannerSemanticJudgment",
            request_id=request.request_id,
            input_packet_digest=request.input_packet_digest,
            proposal_digest=request.proposal_digest,
            deterministic_result_ref=request.deterministic_result_ref,
            final_status=result_status,
            requirement_mappings=mappings,
            issues=issues,
            ambiguities=ambiguities,
            primary_judgment=primary,
            adversarial_challenge=adversarial,
            requirement_findings=findings,
            necessary_fact_findings=tuple(item for item in findings if item.requirement_kind == "FACT"),
            necessary_relationship_findings=tuple(item for item in findings if item.requirement_kind == "RELATIONSHIP"),
            authority_findings=tuple(item for item in findings if item.requirement_kind == "AUTHORITY"),
            answer_capability=AnswerCapabilityFinding(
                status=(answer_findings[0].status if answer_findings else result_status),
                requirement_ids=tuple(item.requirement_id for item in answer_findings),
                bounded_explanation=(
                    answer_findings[0].bounded_explanation
                    if answer_findings
                    else "Overall semantic posture governs answer capability."
                ),
            ),
            bounded_evidence=evidence,
            mechanical_posture_seen=mechanical,
            diagnostic_only=request.diagnostic_mode and mechanical != "PASS",
        )


def build_semantic_judgment_request(
    *,
    normalized_user_request: str,
    planner_input: Mapping[str, Any],
    essential_requirements: Sequence[EssentialRequirement],
    proposed_plan: Mapping[str, Any],
    mechanical_validation_summary: Mapping[str, Any],
    evaluation_budget_identity: str,
    essential_architecture_constraints: Sequence[str],
    prohibited_upgrades_or_shortcuts: Sequence[str],
    diagnostic_mode: bool = False,
) -> SemanticJudgmentRequest:
    """Build a request ID from a sanitized, provider-neutral packet."""

    deterministic_result_ref = str(mechanical_validation_summary.get("result_id") or "")
    if not re.fullmatch(r"mechanical-result:[0-9a-f]{64}", deterministic_result_ref):
        raise SemanticJudgmentContractError("mechanical validation summary requires one exact result_id")
    normalized_request_digest = _digest(normalized_user_request)
    proposal_digest = _digest(proposed_plan)
    material = {
        "judge_contract_version": SEMANTIC_JUDGMENT_CONTRACT_VERSION,
        "normalized_user_request_digest": normalized_request_digest,
        "normalized_user_request": normalized_user_request,
        "planner_input": planner_input,
        "essential_requirements": [asdict(item) for item in essential_requirements],
        "proposed_plan": proposed_plan,
        "mechanical_validation_summary": mechanical_validation_summary,
        "deterministic_result_ref": deterministic_result_ref,
        "evaluation_budget_identity": evaluation_budget_identity,
        "essential_architecture_constraints": list(essential_architecture_constraints),
        "prohibited_upgrades_or_shortcuts": list(prohibited_upgrades_or_shortcuts),
        "diagnostic_mode": diagnostic_mode,
    }
    _reject_forbidden_material(material)
    digest = _digest(material)
    return SemanticJudgmentRequest(
        request_id=f"semantic-judgment:{digest}",
        judge_contract_version=SEMANTIC_JUDGMENT_CONTRACT_VERSION,
        normalized_user_request_digest=normalized_request_digest,
        input_packet_digest=digest,
        proposal_digest=proposal_digest,
        deterministic_result_ref=deterministic_result_ref,
        evaluation_budget_identity=evaluation_budget_identity,
        normalized_user_request=normalized_user_request,
        planner_input=dict(planner_input),
        essential_requirements=tuple(essential_requirements),
        proposed_plan=dict(proposed_plan),
        mechanical_validation_summary=dict(mechanical_validation_summary),
        essential_architecture_constraints=tuple(essential_architecture_constraints),
        prohibited_upgrades_or_shortcuts=tuple(prohibited_upgrades_or_shortcuts),
        diagnostic_mode=diagnostic_mode,
    )


def _request_material(
    request: SemanticJudgmentRequest,
) -> dict[str, Any]:
    return {
        "judge_contract_version": request.judge_contract_version,
        "normalized_user_request_digest": (
            request.normalized_user_request_digest
        ),
        "normalized_user_request": request.normalized_user_request,
        "planner_input": request.planner_input,
        "essential_requirements": [
            asdict(item) for item in request.essential_requirements
        ],
        "proposed_plan": request.proposed_plan,
        "mechanical_validation_summary": (
            request.mechanical_validation_summary
        ),
        "deterministic_result_ref": request.deterministic_result_ref,
        "evaluation_budget_identity": request.evaluation_budget_identity,
        "essential_architecture_constraints": list(
            request.essential_architecture_constraints
        ),
        "prohibited_upgrades_or_shortcuts": list(
            request.prohibited_upgrades_or_shortcuts
        ),
        "diagnostic_mode": request.diagnostic_mode,
    }


def _validate_pass(
    request: SemanticJudgmentRequest,
    judgment: SemanticPassJudgment,
    *,
    label: str,
) -> SemanticPassJudgment:
    if judgment.status not in SEMANTIC_STATUSES:
        raise SemanticJudgmentContractError(f"{label} semantic status is unsupported")
    known = {item.requirement_id for item in request.essential_requirements}
    if judgment.status == "MET":
        mapped = [item.requirement_id for item in judgment.requirement_mappings]
        if set(mapped) != known or len(mapped) != len(set(mapped)):
            raise SemanticJudgmentContractError(f"{label} MET must map every essential requirement exactly once")
        if judgment.issues or judgment.ambiguities:
            raise SemanticJudgmentContractError(f"{label} MET cannot include issues or ambiguities")
        for mapping in judgment.requirement_mappings:
            _bounded_text(
                mapping.bounded_explanation,
                "mapping explanation",
                1000,
            )
            if not mapping.proposal_paths or not all(
                _path_exists(request.proposed_plan, path) for path in mapping.proposal_paths
            ):
                raise SemanticJudgmentContractError(f"{label} MET mapping must cite existing proposal material")
    elif judgment.status == "NOT_MET":
        if (
            not judgment.issues
            or judgment.requirement_mappings
            or judgment.ambiguities
        ):
            raise SemanticJudgmentContractError(f"{label} NOT_MET requires exact issues and no success mappings")
        for issue in judgment.issues:
            if issue.requirement_id not in known:
                raise SemanticJudgmentContractError(f"{label} NOT_MET cites an unknown requirement")
            if issue.issue_kind not in _ISSUE_KINDS:
                raise SemanticJudgmentContractError(f"{label} NOT_MET issue kind is unsupported")
            if not isinstance(issue.answer_blocking, bool):
                raise SemanticJudgmentContractError(
                    f"{label} NOT_MET answer-blocking posture must be boolean"
                )
            if not issue.proposal_paths or not all(
                _path_exists(request.proposed_plan, path)
                for path in issue.proposal_paths
            ):
                raise SemanticJudgmentContractError(
                    f"{label} NOT_MET must cite exact proposal evidence"
                )
            _bounded_text(
                issue.bounded_explanation,
                "issue explanation",
                1000,
            )
    else:
        if (
            not judgment.ambiguities
            or judgment.requirement_mappings
            or judgment.issues
        ):
            raise SemanticJudgmentContractError(f"{label} REVIEW_REQUIRED needs precise ambiguity")
        for ambiguity in judgment.ambiguities:
            if ambiguity.requirement_id not in known and ambiguity.requirement_id != "whole_plan":
                raise SemanticJudgmentContractError(f"{label} REVIEW_REQUIRED cites an unknown requirement")
            _bounded_text(
                ambiguity.precise_ambiguity,
                "precise ambiguity",
                1000,
            )
            if len(ambiguity.competing_interpretations) < 2:
                raise SemanticJudgmentContractError(f"{label} REVIEW_REQUIRED needs competing interpretations")
            if len(set(ambiguity.competing_interpretations)) < 2:
                raise SemanticJudgmentContractError(
                    f"{label} REVIEW_REQUIRED needs distinct competing interpretations"
                )
            for interpretation in ambiguity.competing_interpretations:
                _bounded_text(
                    interpretation,
                    "competing interpretation",
                    1000,
                )
            if not ambiguity.proposal_paths or not all(
                _path_exists(request.proposed_plan, path)
                for path in ambiguity.proposal_paths
            ):
                raise SemanticJudgmentContractError(
                    f"{label} REVIEW_REQUIRED must cite exact proposal evidence"
                )
            _bounded_text(
                ambiguity.smallest_review_action,
                "smallest review action",
                1000,
            )
    return judgment


def _validate_result_pass_shape(
    judgment: SemanticPassJudgment,
    *,
    label: str,
) -> None:
    if judgment.status == "MET":
        if (
            not judgment.requirement_mappings
            or judgment.issues
            or judgment.ambiguities
        ):
            raise SemanticJudgmentContractError(
                f"{label} MET result pass shape is invalid"
            )
        for mapping in judgment.requirement_mappings:
            _bounded_text(
                mapping.requirement_id,
                f"{label} mapping requirement_id",
                160,
            )
            _bounded_text(
                mapping.bounded_explanation,
                f"{label} mapping explanation",
                1000,
            )
            if not mapping.proposal_paths:
                raise SemanticJudgmentContractError(
                    f"{label} MET result requires proposal evidence"
                )
    elif judgment.status == "NOT_MET":
        if (
            not judgment.issues
            or judgment.requirement_mappings
            or judgment.ambiguities
        ):
            raise SemanticJudgmentContractError(
                f"{label} NOT_MET result pass shape is invalid"
            )
        for issue in judgment.issues:
            if (
                issue.issue_kind not in _ISSUE_KINDS
                or not issue.proposal_paths
                or not isinstance(issue.answer_blocking, bool)
            ):
                raise SemanticJudgmentContractError(
                    f"{label} NOT_MET result issue is invalid"
                )
            _bounded_text(
                issue.bounded_explanation,
                f"{label} issue explanation",
                1000,
            )
    else:
        if (
            not judgment.ambiguities
            or judgment.requirement_mappings
            or judgment.issues
        ):
            raise SemanticJudgmentContractError(
                f"{label} REVIEW_REQUIRED result pass shape is invalid"
            )
        for ambiguity in judgment.ambiguities:
            if (
                not ambiguity.proposal_paths
                or len(set(ambiguity.competing_interpretations)) < 2
            ):
                raise SemanticJudgmentContractError(
                    f"{label} REVIEW_REQUIRED result ambiguity is invalid"
                )
            _bounded_text(
                ambiguity.precise_ambiguity,
                f"{label} precise ambiguity",
                1000,
            )
            _bounded_text(
                ambiguity.smallest_review_action,
                f"{label} smallest review action",
                1000,
            )


def _validate_result_findings(
    result: SemanticJudgmentResult,
) -> None:
    expected: list[
        tuple[
            str,
            str,
            tuple[str, ...],
            str | None,
            str,
            tuple[str, ...],
        ]
    ] = []
    for mapping in result.requirement_mappings:
        expected.append(
            (
                mapping.requirement_id,
                "MET",
                mapping.proposal_paths,
                None,
                mapping.bounded_explanation,
                (),
            )
        )
    for issue in result.issues:
        expected.append(
            (
                issue.requirement_id,
                "NOT_MET",
                issue.proposal_paths,
                issue.issue_kind,
                issue.bounded_explanation,
                (),
            )
        )
    for ambiguity in result.ambiguities:
        expected.append(
            (
                ambiguity.requirement_id,
                "REVIEW_REQUIRED",
                ambiguity.proposal_paths,
                None,
                ambiguity.precise_ambiguity,
                ambiguity.competing_interpretations,
            )
        )
    observed = [
        (
            finding.requirement_id,
            finding.status,
            finding.proposal_paths,
            finding.issue_kind,
            finding.bounded_explanation,
            finding.competing_interpretations,
        )
        for finding in result.requirement_findings
    ]
    if observed != expected:
        raise SemanticJudgmentContractError(
            "semantic requirement findings differ from the owner result"
        )
    expected_evidence = tuple(
        SemanticEvidenceRef(
            requirement_id=item.requirement_id,
            proposal_paths=item.proposal_paths,
        )
        for item in result.requirement_findings
    )
    if result.bounded_evidence != expected_evidence:
        raise SemanticJudgmentContractError(
            "semantic bounded evidence differs from the findings"
        )
    for kind, subset in (
        ("FACT", result.necessary_fact_findings),
        ("RELATIONSHIP", result.necessary_relationship_findings),
        ("AUTHORITY", result.authority_findings),
    ):
        if subset != tuple(
            item
            for item in result.requirement_findings
            if item.requirement_kind == kind
        ):
            raise SemanticJudgmentContractError(
                f"semantic {kind.casefold()} findings are inconsistent"
            )
    answer_findings = tuple(
        item
        for item in result.requirement_findings
        if item.requirement_kind == "ANSWER_CAPABILITY"
    )
    expected_answer_status = (
        answer_findings[0].status
        if answer_findings
        else result.final_status
    )
    if (
        result.answer_capability.status != expected_answer_status
        or result.answer_capability.requirement_ids
        != tuple(item.requirement_id for item in answer_findings)
    ):
        raise SemanticJudgmentContractError(
            "semantic answer-capability finding is inconsistent"
        )


def _build_requirement_findings(
    *,
    request: SemanticJudgmentRequest,
    status: str,
    mappings: Sequence[RequirementMapping],
    issues: Sequence[SemanticIssue],
    ambiguities: Sequence[SemanticAmbiguity],
) -> tuple[SemanticRequirementFinding, ...]:
    kinds = {item.requirement_id: item.requirement_kind for item in request.essential_requirements}
    findings: list[SemanticRequirementFinding] = []
    for mapping in mappings:
        findings.append(
            SemanticRequirementFinding(
                requirement_id=mapping.requirement_id,
                requirement_kind=kinds[mapping.requirement_id],
                status="MET",
                proposal_paths=mapping.proposal_paths,
                issue_kind=None,
                bounded_explanation=mapping.bounded_explanation,
            )
        )
    for issue in issues:
        findings.append(
            SemanticRequirementFinding(
                requirement_id=issue.requirement_id,
                requirement_kind=kinds[issue.requirement_id],
                status="NOT_MET",
                proposal_paths=issue.proposal_paths,
                issue_kind=issue.issue_kind,
                bounded_explanation=issue.bounded_explanation,
            )
        )
    for ambiguity in ambiguities:
        findings.append(
            SemanticRequirementFinding(
                requirement_id=ambiguity.requirement_id,
                requirement_kind=kinds.get(ambiguity.requirement_id, "OTHER"),
                status="REVIEW_REQUIRED",
                proposal_paths=ambiguity.proposal_paths,
                issue_kind=None,
                bounded_explanation=ambiguity.precise_ambiguity,
                competing_interpretations=(ambiguity.competing_interpretations),
            )
        )
    if not findings:
        raise SemanticJudgmentContractError(f"{status} semantic result has no bounded findings")
    return tuple(findings)


def _materially_agree(
    primary: SemanticPassJudgment,
    adversarial: SemanticPassJudgment,
) -> bool:
    if primary.status != adversarial.status:
        return False
    if primary.status == "MET":
        return {
            (item.requirement_id, item.proposal_paths)
            for item in primary.requirement_mappings
        } == {
            (item.requirement_id, item.proposal_paths)
            for item in adversarial.requirement_mappings
        }
    if primary.status == "NOT_MET":
        return {(item.requirement_id, item.issue_kind) for item in primary.issues} == {
            (item.requirement_id, item.issue_kind) for item in adversarial.issues
        }
    return {
        (
            item.requirement_id,
            frozenset(item.competing_interpretations),
            item.proposal_paths,
        )
        for item in primary.ambiguities
    } == {
        (
            item.requirement_id,
            frozenset(item.competing_interpretations),
            item.proposal_paths,
        )
        for item in adversarial.ambiguities
    }


def _pass_evidence_paths(
    *judgments: SemanticPassJudgment,
) -> tuple[str, ...]:
    paths: list[str] = []
    for judgment in judgments:
        for item in judgment.requirement_mappings:
            paths.extend(item.proposal_paths)
        for item in judgment.issues:
            paths.extend(item.proposal_paths)
        for item in judgment.ambiguities:
            paths.extend(item.proposal_paths)
    return tuple(dict.fromkeys(paths))


def _pass_identity(judgment: SemanticPassJudgment) -> str:
    return _digest(asdict(judgment))[:16]


def _path_exists(value: Mapping[str, Any], path: str) -> bool:
    if not path.startswith("/"):
        return False
    current: Any = value
    for token in path.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping) and token in current:
            current = current[token]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            try:
                current = current[int(token)]
            except (IndexError, TypeError, ValueError):
                return False
        else:
            return False
    return True


def _reject_forbidden_material(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = (
                str(key).strip().casefold().replace("-", "_")
            )
            if normalized in _FORBIDDEN_KEYS or normalized.startswith("teacher_"):
                raise SemanticJudgmentContractError(f"semantic packet contains forbidden key: {normalized}")
            _reject_forbidden_material(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_forbidden_material(item)


def _bounded_text(value: str, label: str, limit: int) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        raise SemanticJudgmentContractError(f"{label} must be explicit")
    if len(normalized) > limit:
        raise SemanticJudgmentContractError(f"{label} exceeds its bound")
    return normalized


def _digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(rendered.encode("utf-8")).hexdigest()


__all__ = [
    "AnswerCapabilityFinding",
    "EssentialRequirement",
    "RequirementMapping",
    "SEMANTIC_JUDGMENT_CONTRACT_VERSION",
    "SEMANTIC_STATUSES",
    "ScriptedSemanticJudgeAdapter",
    "SemanticAmbiguity",
    "SemanticEvidenceRef",
    "SemanticIssue",
    "SemanticJudgmentContractError",
    "SemanticJudgmentRequest",
    "SemanticJudgmentResult",
    "SemanticPassJudgment",
    "SemanticRequirementFinding",
    "build_semantic_judgment_request",
]
