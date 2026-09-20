"""Decode-only records for historical Research -> Analyst -> Author sessions.

These types validate saved data. They never run a model, control new research,
or supply generated judgments as Evidence or as context for a new turn.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scryraven.errors import RunError
from scryraven.sources import Evidence


class _Output(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class Finding(_Output):
    text: str
    support_refs: list[str] = Field(min_length=1)

class ComponentAssessment(_Output):
    need: str
    status: Literal["supported", "qualified", "unresolved"]
    findings: list[Finding]
    limitation: str

class Analysis(_Output):
    decision: Literal["supported", "research_needed", "unable"]
    coverage: list[ComponentAssessment]
    active_evidence_refs: list[str]
    explanation: str
    next_need: str | None
    next_need_ref: str | None
    new_need_reason: str | None

    @property
    def findings(self) -> list[Finding]:
        return [finding for component in self.coverage for finding in component.findings]

    @property
    def support_refs(self) -> list[str]:
        return list(dict.fromkeys(ref for finding in self.findings for ref in finding.support_refs))


def validate_historical_analysis(analysis: Analysis, evidence: list[Evidence], trace: list[dict]) -> None:
    known = {item.source_id for item in evidence}
    if any(ref not in known for ref in [*analysis.support_refs, *analysis.active_evidence_refs]):
        raise RunError("analyst", "invalid_evidence_reference", trace)
    if any(not item.text.strip() or not item.support_refs for item in analysis.findings):
        raise RunError("analyst", "finding_missing_support", trace)
    if not analysis.coverage or any(not item.need.strip() for item in analysis.coverage):
        raise RunError("analyst", "coverage_missing", trace)
    if any(item.status != "unresolved" and not item.findings for item in analysis.coverage):
        raise RunError("analyst", "component_missing_support", trace)
    if any(item.status == "unresolved" and not item.limitation.strip() for item in analysis.coverage):
        raise RunError("analyst", "component_limitation_missing", trace)
    if analysis.decision == "supported" and any(item.status == "unresolved" for item in analysis.coverage):
        raise RunError("analyst", "supported_with_unresolved_component", trace)
    if analysis.decision == "supported" and not analysis.findings:
        raise RunError("analyst", "supported_without_findings", trace)
    if analysis.decision == "research_needed" and not (analysis.next_need or "").strip():
        raise RunError("analyst", "research_need_missing", trace)
    if analysis.decision != "research_needed" and analysis.next_need is not None:
        raise RunError("analyst", "unexpected_research_need", trace)
    if analysis.decision != "research_needed" and (analysis.next_need_ref is not None or analysis.new_need_reason is not None):
        raise RunError("analyst", "unexpected_research_need", trace)
