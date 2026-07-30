"""Non-overriding coordinator and passive sanitized evaluation reporting."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

from scripts.evaluation.model_origination_experiment_authority import (
    ATTRIBUTION_STATUSES,
    AttributionResult,
)
from scripts.evaluation.search_planner_mechanical_validation import (
    MechanicalValidationResult,
)
from scripts.evaluation.search_planner_product_boundary_observer import (
    ProductBoundaryObservation,
)
from scripts.evaluation.search_planner_semantic_judgment import (
    SemanticJudgmentResult,
)

EVALUATION_REPORT_SCHEMA_VERSION = "model_origination_evaluation_report_v1"
COMBINED_POSTURES = frozenset({"PASS", "FAIL", "REVIEW_REQUIRED", "NOT_REACHED", "INCOMPLETE"})
_PRODUCT_POSTURES = frozenset({"PASS", "FAIL", "REVIEW_REQUIRED", "NOT_REACHED"})
_SEMANTIC_POSTURES = frozenset({"MET", "NOT_MET", "REVIEW_REQUIRED", "NOT_RUN"})
_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization_header",
        "chain_of_thought",
        "credential",
        "full_trace",
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
        "token_value",
    }
)


class EvaluationReportingError(ValueError):
    """Raised when reporting would alter or expose an owner result."""


@dataclass(frozen=True, slots=True)
class CombinedEvaluationResult:
    owner: str
    overall_posture: str
    product_status: str
    mechanical_status: str
    semantic_status: str
    experiment_status: str
    contributor_owners: Mapping[str, str]
    contributor_result_digests: Mapping[str, str]
    bounded_reasons: tuple[str, ...]
    causal_language_allowed: bool
    prompt_quality_winner: str | None

    def __post_init__(self) -> None:
        if self.owner != "ModelOriginationEvaluationDecisionCoordinator":
            raise EvaluationReportingError("combined result owner is invalid")
        if self.overall_posture not in COMBINED_POSTURES:
            raise EvaluationReportingError("combined posture is unsupported")
        if self.product_status not in _PRODUCT_POSTURES:
            raise EvaluationReportingError("combined product status is unsupported")
        if self.mechanical_status not in _PRODUCT_POSTURES:
            raise EvaluationReportingError("combined mechanical status is unsupported")
        if self.semantic_status not in _SEMANTIC_POSTURES:
            raise EvaluationReportingError("combined semantic status is unsupported")
        if self.experiment_status not in {
            *ATTRIBUTION_STATUSES,
            "NOT_APPLICABLE",
        }:
            raise EvaluationReportingError("combined experiment status is unsupported")
        required_contributors = {
            "product",
            "mechanical",
            "semantic",
            "experiment",
            "combined",
        }
        if set(self.contributor_owners) != required_contributors:
            raise EvaluationReportingError("combined result contributor owners are incomplete")
        if set(self.contributor_result_digests) != (required_contributors - {"combined"}):
            raise EvaluationReportingError("combined result contributor identities are incomplete")
        for label, value in self.contributor_result_digests.items():
            if value not in {"NOT_RUN", "NOT_APPLICABLE"} and not _is_digest(
                value
            ):
                raise EvaluationReportingError(
                    f"combined contributor identity is invalid: {label}"
                )
        if not self.bounded_reasons or any(
            not str(reason or "").strip() or len(reason) > 240
            for reason in self.bounded_reasons
        ):
            raise EvaluationReportingError(
                "combined reasons must be explicit and bounded"
            )
        if self.prompt_quality_winner is not None:
            raise EvaluationReportingError("the coordinator cannot manufacture a prompt-quality winner")
        if self.causal_language_allowed != (
            self.experiment_status == "CAUSAL_SUPPORT_ESTABLISHED"
        ):
            raise EvaluationReportingError("causal language must follow the attribution owner")

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SanitizedEvaluationReport:
    schema_version: str
    owner: str
    report_id: str
    combined_result: Mapping[str, Any]
    product_boundary_result: Mapping[str, Any]
    mechanical_validation_result: Mapping[str, Any]
    semantic_judgment_result: Mapping[str, Any] | None
    experiment_attribution_result: Mapping[str, Any] | None
    safe_usage_and_cost_metadata: Mapping[str, Any]
    execution_references: tuple[Mapping[str, Any], ...]
    raw_prompt_retained: bool = False
    raw_response_retained: bool = False
    raw_provider_payload_retained: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != EVALUATION_REPORT_SCHEMA_VERSION:
            raise EvaluationReportingError("evaluation report schema is unsupported")
        if self.owner != "ModelOriginationEvaluationReportAssembler":
            raise EvaluationReportingError("evaluation report owner is invalid")
        if self.report_id != f"evaluation-report:{_digest(_report_material(self))}":
            raise EvaluationReportingError(
                "evaluation report identity does not cover the report"
            )
        if any(
            (
                self.raw_prompt_retained,
                self.raw_response_retained,
                self.raw_provider_payload_retained,
            )
        ):
            raise EvaluationReportingError("report cannot retain raw material")
        _assert_report_packet_consistency(self)
        _reject_forbidden_material(_report_material(self))

    def to_packet(self) -> dict[str, Any]:
        self.__post_init__()
        return asdict(self)


class ModelOriginationEvaluationDecisionCoordinator:
    """Combine exact owner statuses without parsing or rescoring their evidence."""

    owner = "ModelOriginationEvaluationDecisionCoordinator"

    def coordinate(
        self,
        *,
        product: ProductBoundaryObservation,
        mechanical: MechanicalValidationResult,
        semantic: SemanticJudgmentResult | None,
        attribution: AttributionResult | None,
    ) -> CombinedEvaluationResult:
        product_digest = _digest(product.to_packet())
        if mechanical.product_observation_digest != product_digest:
            raise EvaluationReportingError("mechanical result does not bind the supplied product observation")
        if semantic is not None and semantic.deterministic_result_ref != mechanical.result_id:
            raise EvaluationReportingError("semantic result does not bind the supplied mechanical result")
        if (
            semantic is not None
            and semantic.mechanical_posture_seen
            != mechanical.overall_posture
        ):
            raise EvaluationReportingError(
                "semantic result does not preserve the mechanical posture"
            )
        if (
            semantic is not None
            and semantic.proposal_digest
            != mechanical.product_proposal_digest
        ):
            raise EvaluationReportingError(
                "semantic result does not bind the canonical product proposal"
            )
        product_status = product.boundary_status
        mechanical_status = mechanical.overall_posture
        semantic_status = (
            semantic.final_status if semantic is not None else "NOT_RUN"
        )
        experiment_status = attribution.status if attribution is not None else "NOT_APPLICABLE"
        reasons: list[str] = []
        if not product.product_boundary_reached:
            overall = "NOT_REACHED"
            reasons.append("The canonical product boundary was not reached.")
        elif product.incomplete_generation_posture != "COMPLETE":
            overall = "INCOMPLETE"
            reasons.append("Generation was incomplete; parser and semantic success are unavailable.")
        elif product_status != "PASS":
            overall = "FAIL"
            reasons.append("The product boundary did not accept the proposal.")
        elif mechanical_status == "FAIL":
            overall = "FAIL"
            reasons.append("A blocking mechanical rule failed.")
        elif mechanical_status != "PASS":
            overall = "REVIEW_REQUIRED"
            reasons.append("Mechanical validation was not fully established.")
        elif semantic is None:
            overall = "REVIEW_REQUIRED"
            reasons.append("No semantic owner result was supplied.")
        elif semantic.diagnostic_only:
            overall = "FAIL"
            reasons.append("A diagnostic semantic result cannot override mechanical authority.")
        elif semantic_status == "NOT_MET":
            overall = "FAIL"
            reasons.append("The semantic owner found an unmet requirement.")
        elif semantic_status == "REVIEW_REQUIRED":
            overall = "REVIEW_REQUIRED"
            reasons.append("The semantic owner requires review.")
        elif experiment_status in {
            "CONFOUNDED",
            "INSUFFICIENT_EVIDENCE",
            "REVIEW_REQUIRED",
        }:
            overall = "REVIEW_REQUIRED"
            reasons.append("The experiment owner did not establish a comparable conclusion.")
        else:
            overall = "PASS"
            reasons.append("Each required owner returned a compatible posture.")
        contributors = {
            "product": product.owner,
            "mechanical": mechanical.owner,
            "semantic": (semantic.owner if semantic is not None else "SearchPlannerSemanticJudgment:NOT_RUN"),
            "experiment": (
                attribution.owner if attribution is not None else "ModelOriginationExperimentAuthority:NOT_APPLICABLE"
            ),
            "combined": self.owner,
        }
        contributor_digests = {
            "product": product_digest,
            "mechanical": _digest(mechanical.to_packet()),
            "semantic": (_digest(semantic.to_packet()) if semantic is not None else "NOT_RUN"),
            "experiment": (_digest(attribution.to_packet()) if attribution is not None else "NOT_APPLICABLE"),
        }
        return CombinedEvaluationResult(
            owner=self.owner,
            overall_posture=overall,
            product_status=product_status,
            mechanical_status=mechanical_status,
            semantic_status=semantic_status,
            experiment_status=experiment_status,
            contributor_owners=contributors,
            contributor_result_digests=contributor_digests,
            bounded_reasons=tuple(reason[:240] for reason in reasons),
            causal_language_allowed=(attribution.causal_language_allowed if attribution is not None else False),
            prompt_quality_winner=None,
        )


class ModelOriginationEvaluationReportAssembler:
    """Serialize owner results without changing any status or conclusion."""

    owner = "ModelOriginationEvaluationReportAssembler"

    def assemble(
        self,
        *,
        combined: CombinedEvaluationResult,
        product: ProductBoundaryObservation,
        mechanical: MechanicalValidationResult,
        semantic: SemanticJudgmentResult | None,
        attribution: AttributionResult | None,
        safe_usage_and_cost_metadata: Mapping[str, Any],
        execution_references: Sequence[Mapping[str, Any]],
    ) -> SanitizedEvaluationReport:
        _assert_exact_contributors(
            combined=combined,
            product=product,
            mechanical=mechanical,
            semantic=semantic,
            attribution=attribution,
        )
        material = {
            "combined_result": combined.to_packet(),
            "product_boundary_result": product.to_packet(),
            "mechanical_validation_result": mechanical.to_packet(),
            "semantic_judgment_result": (semantic.to_packet() if semantic is not None else None),
            "experiment_attribution_result": (attribution.to_packet() if attribution is not None else None),
            "safe_usage_and_cost_metadata": dict(safe_usage_and_cost_metadata),
            "execution_references": tuple(
                dict(item) for item in execution_references
            ),
        }
        _reject_forbidden_material(material)
        report_id = (
            "evaluation-report:"
            + sha256(
                json.dumps(
                    material,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ).encode("utf-8")
            ).hexdigest()
        )
        return SanitizedEvaluationReport(
            schema_version=EVALUATION_REPORT_SCHEMA_VERSION,
            owner=self.owner,
            report_id=report_id,
            **material,
        )


def _assert_exact_contributors(
    *,
    combined: CombinedEvaluationResult,
    product: ProductBoundaryObservation,
    mechanical: MechanicalValidationResult,
    semantic: SemanticJudgmentResult | None,
    attribution: AttributionResult | None,
) -> None:
    expected = (
        product.boundary_status,
        mechanical.overall_posture,
        semantic.final_status if semantic is not None else "NOT_RUN",
        attribution.status if attribution is not None else "NOT_APPLICABLE",
    )
    observed = (
        combined.product_status,
        combined.mechanical_status,
        combined.semantic_status,
        combined.experiment_status,
    )
    if observed != expected:
        raise EvaluationReportingError("combined result does not preserve exact contributor statuses")
    expected_owners = {
        "product": product.owner,
        "mechanical": mechanical.owner,
        "semantic": (semantic.owner if semantic is not None else "SearchPlannerSemanticJudgment:NOT_RUN"),
        "experiment": (
            attribution.owner if attribution is not None else "ModelOriginationExperimentAuthority:NOT_APPLICABLE"
        ),
        "combined": "ModelOriginationEvaluationDecisionCoordinator",
    }
    if dict(combined.contributor_owners) != expected_owners:
        raise EvaluationReportingError("combined result does not preserve exact contributor owners")
    expected_digests = {
        "product": _digest(product.to_packet()),
        "mechanical": _digest(mechanical.to_packet()),
        "semantic": (_digest(semantic.to_packet()) if semantic is not None else "NOT_RUN"),
        "experiment": (_digest(attribution.to_packet()) if attribution is not None else "NOT_APPLICABLE"),
    }
    if dict(combined.contributor_result_digests) != expected_digests:
        raise EvaluationReportingError("combined result does not preserve exact contributor identities")
    if combined.causal_language_allowed and (
        attribution is None
        or attribution.status != "CAUSAL_SUPPORT_ESTABLISHED"
    ):
        raise EvaluationReportingError("report cannot upgrade attribution into causation")


def _report_material(
    report: SanitizedEvaluationReport,
) -> dict[str, Any]:
    return {
        "combined_result": report.combined_result,
        "product_boundary_result": report.product_boundary_result,
        "mechanical_validation_result": (
            report.mechanical_validation_result
        ),
        "semantic_judgment_result": report.semantic_judgment_result,
        "experiment_attribution_result": (
            report.experiment_attribution_result
        ),
        "safe_usage_and_cost_metadata": (
            report.safe_usage_and_cost_metadata
        ),
        "execution_references": list(report.execution_references),
    }


def _assert_report_packet_consistency(
    report: SanitizedEvaluationReport,
) -> None:
    combined = dict(report.combined_result)
    product = dict(report.product_boundary_result)
    mechanical = dict(report.mechanical_validation_result)
    semantic = (
        dict(report.semantic_judgment_result)
        if report.semantic_judgment_result is not None
        else None
    )
    attribution = (
        dict(report.experiment_attribution_result)
        if report.experiment_attribution_result is not None
        else None
    )
    statuses = {
        "product_status": product.get("boundary_status"),
        "mechanical_status": mechanical.get("overall_posture"),
        "semantic_status": (
            semantic.get("final_status")
            if semantic is not None
            else "NOT_RUN"
        ),
        "experiment_status": (
            attribution.get("status")
            if attribution is not None
            else "NOT_APPLICABLE"
        ),
    }
    if any(combined.get(key) != value for key, value in statuses.items()):
        raise EvaluationReportingError(
            "report packet does not preserve contributor statuses"
        )
    if not product.get("product_boundary_reached"):
        expected_overall = "NOT_REACHED"
    elif product.get("incomplete_generation_posture") != "COMPLETE":
        expected_overall = "INCOMPLETE"
    elif statuses["product_status"] != "PASS":
        expected_overall = "FAIL"
    elif statuses["mechanical_status"] == "FAIL":
        expected_overall = "FAIL"
    elif statuses["mechanical_status"] != "PASS":
        expected_overall = "REVIEW_REQUIRED"
    elif semantic is None:
        expected_overall = "REVIEW_REQUIRED"
    elif semantic.get("diagnostic_only") is True:
        expected_overall = "FAIL"
    elif statuses["semantic_status"] == "NOT_MET":
        expected_overall = "FAIL"
    elif statuses["semantic_status"] == "REVIEW_REQUIRED":
        expected_overall = "REVIEW_REQUIRED"
    elif statuses["experiment_status"] in {
        "CONFOUNDED",
        "INSUFFICIENT_EVIDENCE",
        "REVIEW_REQUIRED",
    }:
        expected_overall = "REVIEW_REQUIRED"
    else:
        expected_overall = "PASS"
    if combined.get("overall_posture") != expected_overall:
        raise EvaluationReportingError(
            "report packet does not preserve combined precedence"
        )
    owners = {
        "product": product.get("owner"),
        "mechanical": mechanical.get("owner"),
        "semantic": (
            semantic.get("owner")
            if semantic is not None
            else "SearchPlannerSemanticJudgment:NOT_RUN"
        ),
        "experiment": (
            attribution.get("owner")
            if attribution is not None
            else "ModelOriginationExperimentAuthority:NOT_APPLICABLE"
        ),
        "combined": "ModelOriginationEvaluationDecisionCoordinator",
    }
    if dict(combined.get("contributor_owners") or {}) != owners:
        raise EvaluationReportingError(
            "report packet does not preserve contributor owners"
        )
    digests = {
        "product": _digest(product),
        "mechanical": _digest(mechanical),
        "semantic": (
            _digest(semantic) if semantic is not None else "NOT_RUN"
        ),
        "experiment": (
            _digest(attribution)
            if attribution is not None
            else "NOT_APPLICABLE"
        ),
    }
    if dict(combined.get("contributor_result_digests") or {}) != digests:
        raise EvaluationReportingError(
            "report packet does not preserve contributor identities"
        )
    if combined.get("prompt_quality_winner") is not None:
        raise EvaluationReportingError(
            "report packet cannot manufacture a prompt-quality winner"
        )
    causal_allowed = bool(
        attribution
        and attribution.get("status")
        == "CAUSAL_SUPPORT_ESTABLISHED"
        and attribution.get("causal_language_allowed") is True
    )
    if combined.get("causal_language_allowed") is not causal_allowed:
        raise EvaluationReportingError(
            "report packet does not preserve causal-language authority"
        )


def _is_digest(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _reject_forbidden_material(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = (
                str(key).strip().casefold().replace("-", "_")
            )
            if normalized in _FORBIDDEN_KEYS:
                raise EvaluationReportingError(f"report contains forbidden material key: {normalized}")
            _reject_forbidden_material(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_forbidden_material(item)


def _digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(rendered.encode("utf-8")).hexdigest()


__all__ = [
    "COMBINED_POSTURES",
    "EVALUATION_REPORT_SCHEMA_VERSION",
    "CombinedEvaluationResult",
    "EvaluationReportingError",
    "ModelOriginationEvaluationDecisionCoordinator",
    "ModelOriginationEvaluationReportAssembler",
    "SanitizedEvaluationReport",
]
