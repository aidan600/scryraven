"""Passive Scrutineer/remediation handoff representation contract.

AG-76D-SCR records facts the legacy Scrutineer/remediation path has already
computed or would expose to a future Controller-owned handoff. The module is
purely representational: it does not call prompts, providers, search, retrieval,
Analyst, Author, citation, persistence, cache, or orchestration code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from core.controller_handoff_serialization import (
    compact_text as _text,
    deduped_text_tuple as _text_tuple,
    enum_value as _enum_value,
    json_safe as _json_safe,
    json_safe_mapping as _mapping,
)

SCRUTINEER_REMEDIATION_HANDOFF_SCHEMA_VERSION = "AG76D-SCR.v1"
SCRUTINEER_REMEDIATION_HANDOFF_TRACE_KEY = "scrutineer_remediation_handoff"
SCRUTINEER_REMEDIATION_HANDOFF_CONSUMER = (
    "future_controller_owned_scrutineer_remediation_handoff"
)

NO_BEHAVIOR_CHANGE_FLAGS: Mapping[str, bool] = {
    "prompt_behavior_changed": False,
    "provider_behavior_changed": False,
    "search_behavior_changed": False,
    "query_behavior_changed": False,
    "retrieval_behavior_changed": False,
    "scrutineer_behavior_changed": False,
    "remediation_behavior_changed": False,
    "analyst_behavior_changed": False,
    "author_behavior_changed": False,
    "author_prompt_behavior_changed": False,
    "author_prose_behavior_changed": False,
    "citation_behavior_changed": False,
    "db_session_runoutcome_behavior_changed": False,
    "cache_behavior_changed": False,
    "pipeline_orchestrator_behavior_changed": False,
    "live_validation_behavior_changed": False,
}


class ScrutineerRunPosture(str, Enum):
    """Stable posture for the legacy Scrutineer stage."""

    SKIPPED = "skipped"
    RUNNING = "running"
    COMPLETED = "completed"


class RemediationFilterPosture(str, Enum):
    """Stable posture for remediation query novelty/filter results."""

    ADMITTED = "admitted"
    REJECTED_DUPLICATE = "rejected_duplicate"
    REJECTED_EMPTY = "rejected_empty"
    REJECTED_NOT_NOVEL = "rejected_not_novel"
    NOT_EVALUATED = "not_evaluated"


class RemediationDispatchPosture(str, Enum):
    """Stable posture for remediation dispatch authorization."""

    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"
    SKIPPED = "skipped"
    COMPLETED = "completed"


class ResynthesisAdmissionPosture(str, Enum):
    """Stable posture for re-analysis / re-synthesis admission."""

    ADMITTED = "admitted"
    NOT_ADMITTED = "not_admitted"
    TRIGGERED = "triggered"
    SKIPPED = "skipped"


class AuthorDirectiveKind(str, Enum):
    """Stable identities for Scrutineer-originating Author directives."""

    HEDGE = "hedge"
    OMIT = "omit"
    CAVEAT = "caveat"
    PASS_FLAGS_DIRECTLY = "pass_flags_directly"



@dataclass(frozen=True)
class ScrutineerAdmissionDescriptor:
    """Run eligibility and legacy gate facts for Scrutineer admission."""

    eligible: bool
    run_gate: str
    complexity: str | None = None
    mode_allowed: bool | None = None
    contract_allowed: bool | None = None
    requested: bool | None = None
    needed: bool | None = None
    skip_reason: str | None = None
    already_computed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "eligible": self.eligible,
                "run_gate": _text(self.run_gate, limit=160),
                "complexity": _text(self.complexity, limit=80),
                "mode_allowed": self.mode_allowed,
                "contract_allowed": self.contract_allowed,
                "requested": self.requested,
                "needed": self.needed,
                "skip_reason": _text(self.skip_reason, limit=240),
                "already_computed": self.already_computed,
                "changes_scrutineer_behavior": False,
            }
        )


@dataclass(frozen=True)
class ScrutineerFlagDescriptor:
    """Identity and posture of a Scrutineer flag, without adjudicating it."""

    flag_id: str
    category: str
    severity: str
    challenge: str | None = None
    searchable: bool | None = None
    source_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_ids", _text_tuple(self.source_ids, limit=120))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "flag_id": _text(self.flag_id, limit=120),
                "category": _text(self.category, limit=120),
                "severity": _text(self.severity, limit=80),
                "challenge": _text(self.challenge, limit=500),
                "searchable": self.searchable,
                "source_ids": list(self.source_ids),
                "metadata": _mapping(self.metadata),
            }
        )


@dataclass(frozen=True)
class RemediationQueryDescriptor:
    """Identity of a remediation query and the Scrutineer flags that produced it."""

    query_id: str
    query_text: str
    source_flag_ids: tuple[str, ...]
    filter_posture: RemediationFilterPosture | str = RemediationFilterPosture.NOT_EVALUATED
    novelty_score: float | None = None
    rejection_reason: str | None = None
    already_computed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_flag_ids", _text_tuple(self.source_flag_ids, limit=120))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "query_id": _text(self.query_id, limit=120),
                "query_text": _text(self.query_text, limit=300),
                "source_flag_ids": list(self.source_flag_ids),
                "filter_posture": _enum_value(self.filter_posture),
                "novelty_score": self.novelty_score,
                "rejection_reason": _text(self.rejection_reason, limit=240),
                "already_computed": self.already_computed,
                "changes_query_filtering_behavior": False,
            }
        )


@dataclass(frozen=True)
class RemediationDispatchDescriptor:
    """Remediation dispatch authorization and already-computed provider/depth facts."""

    dispatch_posture: RemediationDispatchPosture | str
    authorized: bool
    provider_role: str | None = None
    providers: tuple[str, ...] = ()
    search_depth: str | None = None
    linkup_depth_override: str | None = None
    results_per_query: int | None = None
    protected_legacy_provider_depth_posture: bool = True
    already_computed: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "providers", _text_tuple(self.providers, limit=120))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "dispatch_posture": _enum_value(self.dispatch_posture),
                "authorized": self.authorized,
                "provider_role": _text(self.provider_role, limit=120),
                "providers": list(self.providers),
                "search_depth": _text(self.search_depth, limit=80),
                "linkup_depth_override": _text(self.linkup_depth_override, limit=80),
                "results_per_query": self.results_per_query,
                "protected_legacy_provider_depth_posture": (
                    self.protected_legacy_provider_depth_posture
                ),
                "already_computed": self.already_computed,
                "changes_provider_search_depth_behavior": False,
            }
        )


@dataclass(frozen=True)
class RemediationEvidenceDescriptor:
    """Identity of remediation evidence and the final evidence bundle, when known."""

    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    urls: tuple[str, ...] = ()
    final_evidence_bundle_id: str | None = None
    final_evidence_ref: Mapping[str, Any] = field(default_factory=dict)
    evidence_count: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", _text_tuple(self.evidence_ids, limit=120))
        object.__setattr__(self, "source_ids", _text_tuple(self.source_ids, limit=120))
        object.__setattr__(self, "urls", _text_tuple(self.urls, limit=500))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "evidence_ids": list(self.evidence_ids),
                "source_ids": list(self.source_ids),
                "urls": list(self.urls),
                "final_evidence_bundle_id": _text(self.final_evidence_bundle_id, limit=160),
                "final_evidence_ref": _mapping(self.final_evidence_ref),
                "evidence_count": self.evidence_count,
                "changes_retrieval_or_evidence_behavior": False,
            }
        )


@dataclass(frozen=True)
class RemediationResynthesisDescriptor:
    """Re-synthesis / re-analysis admission posture, not an Analyst executor."""

    posture: ResynthesisAdmissionPosture | str
    reanalysis_triggered: bool = False
    trigger_reason: str | None = None
    analyst_pass_ref: Mapping[str, Any] = field(default_factory=dict)
    analysis_ref: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "posture": _enum_value(self.posture),
                "reanalysis_triggered": self.reanalysis_triggered,
                "trigger_reason": _text(self.trigger_reason, limit=240),
                "analyst_pass_ref": _mapping(self.analyst_pass_ref),
                "analysis_ref": _mapping(self.analysis_ref),
                "changes_analyst_behavior": False,
            }
        )


@dataclass(frozen=True)
class ScrutineerAuthorDirectiveDescriptor:
    """Identity of Scrutineer-originating Author directives without prompt/prose edits."""

    directive_id: str
    kind: AuthorDirectiveKind | str
    source_flag_ids: tuple[str, ...] = ()
    hedge: bool = False
    omit: bool = False
    caveat: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_flag_ids", _text_tuple(self.source_flag_ids, limit=120))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "directive_id": _text(self.directive_id, limit=120),
                "kind": _enum_value(self.kind),
                "source_flag_ids": list(self.source_flag_ids),
                "hedge": self.hedge,
                "omit": self.omit,
                "caveat": self.caveat,
                "metadata": _mapping(self.metadata),
                "prompt_text_included": False,
                "changes_author_prompt_or_prose_behavior": False,
            }
        )


@dataclass(frozen=True)
class ScrutineerRemediationExecutionEnvelope:
    """Mechanical execution envelope for a future Controller-owned consumer."""

    consumer: str = SCRUTINEER_REMEDIATION_HANDOFF_CONSUMER
    trace_key: str = SCRUTINEER_REMEDIATION_HANDOFF_TRACE_KEY
    mechanical_executor_boundary: bool = True
    runtime_wiring_active: bool = False
    behavior_change_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(
            {
                "consumer": self.consumer,
                "trace_key": self.trace_key,
                "mechanical_executor_boundary": self.mechanical_executor_boundary,
                "runtime_wiring_active": self.runtime_wiring_active,
                "behavior_change_authorized": self.behavior_change_authorized,
            }
        )


@dataclass(frozen=True)
class ScrutineerRemediationHandoffState:
    """Controller-owned passive Scrutineer/remediation handoff representation."""

    run_id: str
    admission: ScrutineerAdmissionDescriptor
    run_posture: ScrutineerRunPosture | str
    flags: tuple[ScrutineerFlagDescriptor, ...] = ()
    high_severity_flag_threshold: int | None = None
    searchable_categories: tuple[str, ...] = ()
    non_searchable_categories: tuple[str, ...] = ()
    remediation_queries: tuple[RemediationQueryDescriptor, ...] = ()
    dispatch: RemediationDispatchDescriptor | None = None
    remediation_evidence: RemediationEvidenceDescriptor | None = None
    resynthesis: RemediationResynthesisDescriptor | None = None
    author_directives: tuple[ScrutineerAuthorDirectiveDescriptor, ...] = ()
    answer_contract_ref: Mapping[str, Any] = field(default_factory=dict)
    analyst_author_handoff_ref: Mapping[str, Any] = field(default_factory=dict)
    citation_source_handoff_ref: Mapping[str, Any] = field(default_factory=dict)
    execution_envelope: ScrutineerRemediationExecutionEnvelope = field(
        default_factory=ScrutineerRemediationExecutionEnvelope
    )
    schema_version: str = SCRUTINEER_REMEDIATION_HANDOFF_SCHEMA_VERSION
    trace_key: str = SCRUTINEER_REMEDIATION_HANDOFF_TRACE_KEY
    controller_owned: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "flags", tuple(self.flags or ()))
        object.__setattr__(self, "searchable_categories", _text_tuple(self.searchable_categories, limit=120))
        object.__setattr__(
            self,
            "non_searchable_categories",
            _text_tuple(self.non_searchable_categories, limit=120),
        )
        object.__setattr__(self, "remediation_queries", tuple(self.remediation_queries or ()))
        object.__setattr__(self, "author_directives", tuple(self.author_directives or ()))

    def to_controller_state(self) -> dict[str, Any]:
        flag_dicts = [flag.to_dict() for flag in self.flags]
        high_count = sum(
            1
            for flag in flag_dicts
            if str(flag.get("severity") or "").strip().casefold() == "high"
        )
        return _json_safe(
            {
                "schema_version": self.schema_version,
                "trace_key": self.trace_key,
                "controller_owned": self.controller_owned,
                "consumer": SCRUTINEER_REMEDIATION_HANDOFF_CONSUMER,
                "run_id": _text(self.run_id, limit=160),
                "admission": self.admission.to_dict(),
                "run_posture": _enum_value(self.run_posture),
                "flag_posture": {
                    "flag_count": len(flag_dicts),
                    "high_severity_flag_count": high_count,
                    "high_severity_flag_threshold": self.high_severity_flag_threshold,
                    "searchable_categories": list(self.searchable_categories),
                    "non_searchable_categories": list(self.non_searchable_categories),
                    "flags": flag_dicts,
                    "threshold_represents_posture_only": True,
                    "category_filter_represents_posture_only": True,
                },
                "remediation_queries": [query.to_dict() for query in self.remediation_queries],
                "remediation_dispatch": (
                    self.dispatch.to_dict() if self.dispatch is not None else None
                ),
                "remediation_evidence": (
                    self.remediation_evidence.to_dict()
                    if self.remediation_evidence is not None
                    else None
                ),
                "resynthesis": self.resynthesis.to_dict() if self.resynthesis is not None else None,
                "author_directives": [directive.to_dict() for directive in self.author_directives],
                "handoff_refs": {
                    "answer_contract_ref": _mapping(self.answer_contract_ref),
                    "analyst_author_handoff_ref": _mapping(self.analyst_author_handoff_ref),
                    "citation_source_handoff_ref": _mapping(self.citation_source_handoff_ref),
                },
                "execution_envelope": self.execution_envelope.to_dict(),
                "no_behavior_change_flags": dict(NO_BEHAVIOR_CHANGE_FLAGS),
            }
        )

    def to_trace_fragment(self) -> dict[str, Any]:
        return {self.trace_key: self.to_controller_state()}
