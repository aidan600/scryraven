"""Runtime adapter for passive Scrutineer/remediation handoff wiring.

AG-76D-SCR-R1 packages facts already computed by the legacy runtime path into
``ScrutineerRemediationHandoffState``. It is intentionally representational:
it does not choose whether Scrutineer runs, generate queries, filter queries,
select providers, dispatch search, re-run Analyst, alter Author directives, or
change citation behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from core.scrutineer_remediation_handoff_contract import (
    AuthorDirectiveKind,
    RemediationDispatchDescriptor,
    RemediationDispatchPosture,
    RemediationEvidenceDescriptor,
    RemediationFilterPosture,
    RemediationQueryDescriptor,
    RemediationResynthesisDescriptor,
    ResynthesisAdmissionPosture,
    ScrutineerAdmissionDescriptor,
    ScrutineerAuthorDirectiveDescriptor,
    ScrutineerFlagDescriptor,
    ScrutineerRemediationExecutionEnvelope,
    ScrutineerRemediationHandoffState,
    ScrutineerRunPosture,
)

SEARCHABLE_SCRUTINEER_REMEDIATION_CATEGORIES = ("SINGLE-SOURCE", "TEMPORAL DRIFT")
SCRUTINEER_HIGH_FLAG_THRESHOLD = 5


def _text(value: Any, *, limit: int = 500) -> str | None:
    text = " ".join(str(value or "").strip().split())
    return text[:limit] if text else None


def _dedupe_text(values: Sequence[Any] | None, *, limit: int = 240) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        text = _text(value, limit=limit)
        key = str(text or "").casefold()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return tuple(out)


def _flag_value(flag: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in flag:
            return flag.get(name)
    return None


def _flag_id(flag: Mapping[str, Any], index: int) -> str:
    return str(
        _flag_value(flag, "flag_id", "id", "source_flag_id")
        or f"scrutineer-flag-{index + 1}"
    )


def _normal_category(flag: Mapping[str, Any]) -> str:
    return str(_flag_value(flag, "category") or "uncategorized")


def _normal_severity(flag: Mapping[str, Any]) -> str:
    return str(_flag_value(flag, "severity") or "unknown").lower()


def _evidence_identity(item: Any, index: int) -> tuple[str, str | None, str | None]:
    if isinstance(item, Mapping):
        evidence_id = str(
            item.get("evidence_id")
            or item.get("id")
            or item.get("source_id")
            or item.get("url")
            or f"remediation-evidence-{index + 1}"
        )
        source_id = _text(item.get("source_id") or item.get("id"), limit=120)
        url = _text(item.get("url") or item.get("link"), limit=500)
        return evidence_id, source_id, url
    return f"remediation-evidence-{index + 1}", None, None


@dataclass(frozen=True)
class RuntimeRemediationQueryFact:
    """Already-computed remediation query identity and novelty posture."""

    query_text: str
    source_flag_ids: Sequence[Any] = ()
    filter_posture: RemediationFilterPosture | str = RemediationFilterPosture.NOT_EVALUATED
    rejection_reason: str | None = None
    query_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeScrutineerRemediationFacts:
    """Facts observed from the legacy Scrutineer/remediation runtime path."""

    run_id: str
    eligible: bool
    run_gate: str
    run_posture: ScrutineerRunPosture | str
    complexity: str | None = None
    mode_allowed: bool | None = None
    contract_allowed: bool | None = None
    requested: bool | None = None
    needed: bool | None = None
    skip_reason: str | None = None
    flags: Sequence[Mapping[str, Any]] = ()
    high_severity_flag_threshold: int = SCRUTINEER_HIGH_FLAG_THRESHOLD
    remediation_queries: Sequence[RuntimeRemediationQueryFact] = ()
    dispatch_authorized: bool = False
    dispatch_posture: RemediationDispatchPosture | str = RemediationDispatchPosture.SKIPPED
    provider_role: str | None = None
    providers: Sequence[Any] = ()
    search_depth: str | None = None
    linkup_depth_override: str | None = None
    remediation_evidence: Sequence[Any] = ()
    final_evidence_bundle_id: str | None = None
    final_evidence_ref: Mapping[str, Any] = field(default_factory=dict)
    resynthesis_posture: ResynthesisAdmissionPosture | str = ResynthesisAdmissionPosture.SKIPPED
    reanalysis_triggered: bool = False
    resynthesis_trigger_reason: str | None = None
    analyst_pass_ref: Mapping[str, Any] = field(default_factory=dict)
    analysis_ref: Mapping[str, Any] = field(default_factory=dict)
    pass_flags_directly_to_author: bool = False
    author_directive_metadata: Mapping[str, Any] = field(default_factory=dict)
    answer_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    analyst_author_handoff_ref: Mapping[str, Any] = field(default_factory=dict)
    citation_source_handoff_ref: Mapping[str, Any] = field(default_factory=dict)


def _flag_descriptors(
    flags: Sequence[Mapping[str, Any]],
) -> tuple[ScrutineerFlagDescriptor, ...]:
    descriptors: list[ScrutineerFlagDescriptor] = []
    searchable = set(SEARCHABLE_SCRUTINEER_REMEDIATION_CATEGORIES)
    for index, flag in enumerate(flags):
        category = _normal_category(flag)
        severity = _normal_severity(flag)
        descriptors.append(
            ScrutineerFlagDescriptor(
                flag_id=_flag_id(flag, index),
                category=category,
                severity=severity,
                challenge=_text(
                    _flag_value(flag, "challenge", "message", "description", "text"),
                    limit=500,
                ),
                searchable=severity == "high" and category in searchable,
                source_ids=_dedupe_text(
                    _flag_value(flag, "source_ids", "sources") or (),
                    limit=120,
                ),
                metadata={
                    "runtime_index": index,
                    "already_computed": True,
                },
            )
        )
    return tuple(descriptors)


def _query_descriptors(
    queries: Sequence[RuntimeRemediationQueryFact],
) -> tuple[RemediationQueryDescriptor, ...]:
    return tuple(
        RemediationQueryDescriptor(
            query_id=query.query_id or f"scrutineer-remediation-query-{index + 1}",
            query_text=query.query_text,
            source_flag_ids=_dedupe_text(query.source_flag_ids, limit=120),
            filter_posture=query.filter_posture,
            rejection_reason=query.rejection_reason,
        )
        for index, query in enumerate(queries)
    )


def _evidence_descriptor(
    facts: RuntimeScrutineerRemediationFacts,
) -> RemediationEvidenceDescriptor | None:
    if not facts.remediation_evidence and not facts.final_evidence_bundle_id and not facts.final_evidence_ref:
        return None
    evidence_ids: list[str] = []
    source_ids: list[str] = []
    urls: list[str] = []
    for index, item in enumerate(facts.remediation_evidence):
        evidence_id, source_id, url = _evidence_identity(item, index)
        evidence_ids.append(evidence_id)
        if source_id:
            source_ids.append(source_id)
        if url:
            urls.append(url)
    return RemediationEvidenceDescriptor(
        evidence_ids=_dedupe_text(evidence_ids, limit=120),
        source_ids=_dedupe_text(source_ids, limit=120),
        urls=_dedupe_text(urls, limit=500),
        final_evidence_bundle_id=facts.final_evidence_bundle_id,
        final_evidence_ref=facts.final_evidence_ref,
        evidence_count=len(facts.remediation_evidence),
    )


def _author_directives(
    facts: RuntimeScrutineerRemediationFacts,
    flags: tuple[ScrutineerFlagDescriptor, ...],
) -> tuple[ScrutineerAuthorDirectiveDescriptor, ...]:
    if not facts.pass_flags_directly_to_author:
        return ()
    return (
        ScrutineerAuthorDirectiveDescriptor(
            directive_id="scrutineer-pass-flags-directly-to-author",
            kind=AuthorDirectiveKind.PASS_FLAGS_DIRECTLY,
            source_flag_ids=tuple(flag.flag_id for flag in flags),
            metadata={
                "already_computed": True,
                "flag_count": len(flags),
                **dict(facts.author_directive_metadata),
            },
        ),
    )


def build_runtime_scrutineer_remediation_handoff(
    facts: RuntimeScrutineerRemediationFacts,
) -> ScrutineerRemediationHandoffState:
    """Build the passive handoff from legacy runtime facts without side effects."""
    flag_descriptors = _flag_descriptors(facts.flags)
    searchable_categories = tuple(
        category
        for category in SEARCHABLE_SCRUTINEER_REMEDIATION_CATEGORIES
        if any(flag.category == category and flag.searchable for flag in flag_descriptors)
    )
    non_searchable_categories = tuple(
        sorted(
            {
                flag.category
                for flag in flag_descriptors
                if not flag.searchable and flag.category
            }
        )
    )
    dispatch = RemediationDispatchDescriptor(
        dispatch_posture=facts.dispatch_posture,
        authorized=facts.dispatch_authorized,
        provider_role=facts.provider_role,
        providers=_dedupe_text(facts.providers, limit=120),
        search_depth=facts.search_depth,
        linkup_depth_override=facts.linkup_depth_override,
    )
    return ScrutineerRemediationHandoffState(
        run_id=facts.run_id,
        admission=ScrutineerAdmissionDescriptor(
            eligible=facts.eligible,
            run_gate=facts.run_gate,
            complexity=facts.complexity,
            mode_allowed=facts.mode_allowed,
            contract_allowed=facts.contract_allowed,
            requested=facts.requested,
            needed=facts.needed,
            skip_reason=facts.skip_reason,
        ),
        run_posture=facts.run_posture,
        flags=flag_descriptors,
        high_severity_flag_threshold=facts.high_severity_flag_threshold,
        searchable_categories=searchable_categories,
        non_searchable_categories=non_searchable_categories,
        remediation_queries=_query_descriptors(facts.remediation_queries),
        dispatch=dispatch,
        remediation_evidence=_evidence_descriptor(facts),
        resynthesis=RemediationResynthesisDescriptor(
            posture=facts.resynthesis_posture,
            reanalysis_triggered=facts.reanalysis_triggered,
            trigger_reason=facts.resynthesis_trigger_reason,
            analyst_pass_ref=facts.analyst_pass_ref,
            analysis_ref=facts.analysis_ref,
        ),
        author_directives=_author_directives(facts, flag_descriptors),
        answer_contract_ref=facts.answer_contract_ref,
        analyst_author_handoff_ref=facts.analyst_author_handoff_ref,
        citation_source_handoff_ref=facts.citation_source_handoff_ref,
        execution_envelope=ScrutineerRemediationExecutionEnvelope(
            runtime_wiring_active=True,
            behavior_change_authorized=False,
        ),
    )


def runtime_scrutineer_remediation_trace_fragment(
    facts: RuntimeScrutineerRemediationFacts,
) -> dict[str, Any]:
    """Return the JSON-safe trace fragment for runtime attachment."""
    return build_runtime_scrutineer_remediation_handoff(facts).to_trace_fragment()


__all__ = [
    "RuntimeRemediationQueryFact",
    "RuntimeScrutineerRemediationFacts",
    "SCRUTINEER_HIGH_FLAG_THRESHOLD",
    "SEARCHABLE_SCRUTINEER_REMEDIATION_CATEGORIES",
    "build_runtime_scrutineer_remediation_handoff",
    "runtime_scrutineer_remediation_trace_fragment",
]
