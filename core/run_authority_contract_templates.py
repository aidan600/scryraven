"""Deterministic RunAuthority contract templates for AG-92A."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from core.run_authority_contract import (
    ContractSynthesisMode,
    RunAuthorityContract,
    RunContractRequirementKind,
    RunContractSourceRequirement,
    RunContractStrictness,
    clean_token,
    query_ref,
    safe_json,
    stable_hash,
)

CURRENT_OFFICIAL_NUMERIC_OR_RULE = "current_official_numeric_or_rule"
LEGAL_OR_REGULATORY_CURRENT_PRIMARY = "legal_or_regulatory_current_primary"
CANONICAL_TECHNICAL_DOCS = "canonical_technical_docs"
ACADEMIC_LITERATURE = "academic_literature"
ORDINARY_EXPLAINER = "ordinary_explainer"
USER_DOCUMENT_OR_PERSONAL_CORPUS = "user_document_or_personal_corpus"
INDIRECT_INFERENCE = "indirect_inference"
CONFLICT_SENSITIVE = "conflict_sensitive"

_WEAK_CANNOT_SATISFY = (
    "reputable_secondary",
    "secondary_analysis",
    "trusted_community",
    "social_signal",
    "social_or_forum",
    "community",
    "aggregate_count_only",
    "helper_assessment_only",
)


@dataclass(frozen=True, slots=True)
class RunContractTemplate:
    template_id: str
    question_type: str
    claim_type: str
    source_requirements: tuple[RunContractSourceRequirement, ...] = ()
    inference_policy: Mapping[str, Any] = None
    conflict_policy: Mapping[str, Any] = None
    numeric_policy: Mapping[str, Any] = None
    recovery_policy: Mapping[str, Any] = None
    final_posture_policy: Mapping[str, Any] = None
    downstream_hints: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "inference_policy", dict(self.inference_policy or {}))
        object.__setattr__(self, "conflict_policy", dict(self.conflict_policy or {}))
        object.__setattr__(self, "numeric_policy", dict(self.numeric_policy or {}))
        object.__setattr__(self, "recovery_policy", dict(self.recovery_policy or {}))
        object.__setattr__(
            self,
            "final_posture_policy",
            dict(self.final_posture_policy or {}),
        )
        object.__setattr__(self, "downstream_hints", dict(self.downstream_hints or {}))


def _req(
    requirement_id: str,
    *,
    requirement_kind: RunContractRequirementKind,
    strictness: RunContractStrictness,
    required_source_class: str,
    required_source_tier: str | None,
    required_currentness: str | None,
    satisfaction_rule: str,
    allowed_lower_tier_use: str,
    cannot_satisfy_with: Sequence[str] = _WEAK_CANNOT_SATISFY,
    rationale: str | None = None,
) -> RunContractSourceRequirement:
    return RunContractSourceRequirement(
        requirement_id=requirement_id,
        requirement_kind=requirement_kind,
        strictness=strictness,
        required_source_class=required_source_class,
        required_source_tier=required_source_tier,
        required_currentness=required_currentness,
        satisfaction_rule=satisfaction_rule,
        allowed_lower_tier_use=allowed_lower_tier_use,
        cannot_satisfy_with=tuple(cannot_satisfy_with),
        rationale=rationale,
    )


TEMPLATE_REGISTRY: dict[str, RunContractTemplate] = {
    CURRENT_OFFICIAL_NUMERIC_OR_RULE: RunContractTemplate(
        template_id=CURRENT_OFFICIAL_NUMERIC_OR_RULE,
        question_type="current_official_numeric_or_rule",
        claim_type="source_bound_current_fact",
        source_requirements=(
            _req(
                "run-contract:official_current_rules",
                requirement_kind=RunContractRequirementKind.OFFICIAL_CURRENT,
                strictness=RunContractStrictness.REQUIRED,
                required_source_class="official_current_rules",
                required_source_tier="official",
                required_currentness="current",
                satisfaction_rule="direct official/current source required for current rule or threshold claims",
                allowed_lower_tier_use="leads_or_context_only",
                rationale="current official numeric/rule questions require source-bound official evidence",
            ),
            _req(
                "run-contract:source_bound_numeric",
                requirement_kind=RunContractRequirementKind.SOURCE_BOUND_NUMERIC,
                strictness=RunContractStrictness.REQUIRED,
                required_source_class="official_current_rules",
                required_source_tier="official",
                required_currentness="current",
                satisfaction_rule="numeric values must be bound to an identified current official or primary source",
                allowed_lower_tier_use="leads_or_context_only",
                rationale="unsupported numeric values remain unknown",
            ),
        ),
        numeric_policy={
            "source_bound_required": True,
            "calculations_allowed_from_sourced_values": True,
            "unsupported_values_unknown": True,
        },
        recovery_policy={
            "recover_missing_official_current": True,
            "stop_when_budget_exhausted": True,
        },
        final_posture_policy={
            "definitive_allowed_if": "required official/current source-bound values satisfied",
            "partial_allowed_if": "some required values missing but caveated",
            "insufficient_required_if": "required official/current source-bound value is missing",
            "mandatory_caveats": (
                "missing_official_current_source_must_be_caveated",
                "missing_source_bound_numeric_value_remains_unknown",
            ),
            "prohibited_upgrades": (
                "do_not_treat_secondary_or_aggregate_counts_as_official_current_satisfaction",
                "do_not_present_unsupported_numeric_values_as_sourced",
            ),
        },
        downstream_hints={
            "query_strategy_hints": (
                {
                    "hint_id": "official-current-source",
                    "requirement_id": "run-contract:official_current_rules",
                    "query_hint": "prefer official current source",
                },
                {
                    "hint_id": "source-bound-numeric",
                    "requirement_id": "run-contract:source_bound_numeric",
                    "query_hint": "bind numeric values to official source",
                },
            ),
            "evidence_ledger_requirement_hints": (
                "official_current_rules",
                "current_primary_or_official",
            ),
            "final_answer_packet_hints": (
                "missing official/current source-bound values require caveats",
            ),
        },
    ),
    LEGAL_OR_REGULATORY_CURRENT_PRIMARY: RunContractTemplate(
        template_id=LEGAL_OR_REGULATORY_CURRENT_PRIMARY,
        question_type="legal_or_regulatory_current_primary",
        claim_type="current_legal_or_regulatory_claim",
        source_requirements=(
            _req(
                "run-contract:legal_or_regulatory_text",
                requirement_kind=RunContractRequirementKind.LEGAL_PRIMARY,
                strictness=RunContractStrictness.REQUIRED,
                required_source_class="legal_or_regulatory_text",
                required_source_tier="primary",
                required_currentness="current",
                satisfaction_rule="current primary legal/regulatory or official jurisdictional source required",
                allowed_lower_tier_use="secondary_explainers_context_only",
                rationale="legal/regulatory answers cannot be grounded only in explainers",
            ),
        ),
        recovery_policy={
            "recover_missing_legal_primary": True,
            "stop_when_budget_exhausted": True,
        },
        final_posture_policy={
            "definitive_allowed_if": "current primary legal/regulatory source satisfies jurisdictional obligation",
            "partial_allowed_if": "primary source absent but limitation is explicit",
            "insufficient_required_if": "legal/current-primary source is missing",
            "mandatory_caveats": ("missing_legal_primary_source_must_be_caveated",),
            "prohibited_upgrades": (
                "do_not_treat_secondary_explainers_as_legal_primary_satisfaction",
            ),
        },
        downstream_hints={
            "query_strategy_hints": (
                {
                    "hint_id": "legal-primary-source",
                    "requirement_id": "run-contract:legal_or_regulatory_text",
                    "query_hint": "prefer current primary legal or regulatory source",
                },
            ),
            "evidence_ledger_requirement_hints": ("legal_or_regulatory_text",),
            "final_answer_packet_hints": (
                "missing current primary legal source requires caveat",
            ),
        },
    ),
    CANONICAL_TECHNICAL_DOCS: RunContractTemplate(
        template_id=CANONICAL_TECHNICAL_DOCS,
        question_type="canonical_technical_docs",
        claim_type="current_canonical_product_or_api_behavior",
        source_requirements=(
            _req(
                "run-contract:canonical_docs",
                requirement_kind=RunContractRequirementKind.CANONICAL_DOCS,
                strictness=RunContractStrictness.REQUIRED,
                required_source_class="primary_source_documents",
                required_source_tier="canonical",
                required_currentness="current",
                satisfaction_rule="official/project/canonical docs, changelog, or release notes required for current behavior",
                allowed_lower_tier_use="community_posts_context_only",
                rationale="current technical behavior needs canonical source authority",
            ),
        ),
        recovery_policy={
            "recover_missing_canonical": True,
            "stop_when_budget_exhausted": True,
        },
        final_posture_policy={
            "definitive_allowed_if": "canonical docs or release notes support the behavior",
            "partial_allowed_if": "canonical source absent but lower-tier context is clearly labeled",
            "insufficient_required_if": "canonical source for current behavior is missing",
            "mandatory_caveats": ("missing_canonical_docs_must_be_caveated",),
            "prohibited_upgrades": (
                "do_not_treat_forum_or_blog_context_as_canonical_current_docs",
            ),
        },
        downstream_hints={
            "query_strategy_hints": (
                {
                    "hint_id": "canonical-technical-docs",
                    "requirement_id": "run-contract:canonical_docs",
                    "query_hint": "prefer official docs changelog release notes",
                },
            ),
            "evidence_ledger_requirement_hints": ("primary_source_documents",),
            "final_answer_packet_hints": (
                "missing canonical docs require caveat for current technical behavior",
            ),
        },
    ),
    ACADEMIC_LITERATURE: RunContractTemplate(
        template_id=ACADEMIC_LITERATURE,
        question_type="academic_literature",
        claim_type="academic_or_benchmark_claim",
        source_requirements=(
            _req(
                "run-contract:academic_primary_literature",
                requirement_kind=RunContractRequirementKind.ACADEMIC,
                strictness=RunContractStrictness.REQUIRED,
                required_source_class="academic_primary_literature",
                required_source_tier="academic",
                required_currentness="as_requested",
                satisfaction_rule="paper, benchmark, dataset, or primary literature required when academic support is requested",
                allowed_lower_tier_use="context_only",
                cannot_satisfy_with=("blog", "forum", "press_release_only"),
                rationale="academic claims need academic or primary literature",
            ),
        ),
        downstream_hints={
            "query_strategy_hints": (
                {
                    "hint_id": "academic-primary-literature",
                    "requirement_id": "run-contract:academic_primary_literature",
                    "query_hint": "prefer papers datasets benchmarks primary literature",
                },
            ),
            "evidence_ledger_requirement_hints": ("academic_primary_literature",),
        },
    ),
    ORDINARY_EXPLAINER: RunContractTemplate(
        template_id=ORDINARY_EXPLAINER,
        question_type="ordinary_explainer",
        claim_type="general_explanation",
        source_requirements=(
            _req(
                "run-contract:reputable_secondary",
                requirement_kind=RunContractRequirementKind.REPUTABLE_SECONDARY,
                strictness=RunContractStrictness.PREFERRED,
                required_source_class="reputable_secondary",
                required_source_tier="secondary",
                required_currentness="not_stale_for_claim",
                satisfaction_rule="reputable secondary sources may satisfy ordinary explanation needs",
                allowed_lower_tier_use="may_satisfy_when_no_stronger_obligation_applies",
                cannot_satisfy_with=("social_signal", "unverifiable_forum_only"),
                rationale="ordinary explainers should not over-require official sources",
            ),
        ),
        final_posture_policy={
            "definitive_allowed_if": "ordinary evidence is adequate for the claim",
            "partial_allowed_if": "evidence is thin or context-only",
            "insufficient_required_if": "evidence is absent",
            "mandatory_caveats": (),
            "prohibited_upgrades": (
                "do_not_upgrade_context_only_sources_to_stronger_authority",
            ),
        },
    ),
    USER_DOCUMENT_OR_PERSONAL_CORPUS: RunContractTemplate(
        template_id=USER_DOCUMENT_OR_PERSONAL_CORPUS,
        question_type="user_document_or_personal_corpus",
        claim_type="document_bound_claim",
        source_requirements=(
            _req(
                "run-contract:user_document",
                requirement_kind=RunContractRequirementKind.USER_DOCUMENT,
                strictness=RunContractStrictness.REQUIRED,
                required_source_class="user_document",
                required_source_tier="user_document",
                required_currentness="as_provided",
                satisfaction_rule="claims framed as based on the user's file/corpus require document evidence",
                allowed_lower_tier_use="web_or_model_context_only",
                cannot_satisfy_with=("web_secondary", "model_memory", "general_knowledge"),
                rationale="document-bound requests must not launder web/model inference as document evidence",
            ),
        ),
        final_posture_policy={
            "definitive_allowed_if": "document evidence directly supports the claim",
            "partial_allowed_if": "document support is partial and caveated",
            "insufficient_required_if": "requested document evidence is unavailable",
            "mandatory_caveats": ("missing_user_document_evidence_must_be_caveated",),
            "prohibited_upgrades": (
                "do_not_present_model_inference_as_document_evidence",
            ),
        },
    ),
    INDIRECT_INFERENCE: RunContractTemplate(
        template_id=INDIRECT_INFERENCE,
        question_type="indirect_inference",
        claim_type="inferred_from_sourced_premises",
        inference_policy={
            "policy": "inferred_from_sourced_premises_allowed",
            "direct_sourcing_required_for_premises": True,
            "inferred_conclusion_must_be_labeled": True,
        },
        final_posture_policy={
            "mandatory_caveats": ("inferred_conclusion_must_not_be_presented_as_directly_sourced",),
            "prohibited_upgrades": ("do_not_launder_inference_as_direct_source_claim",),
        },
    ),
    CONFLICT_SENSITIVE: RunContractTemplate(
        template_id=CONFLICT_SENSITIVE,
        question_type="conflict_sensitive",
        claim_type="conflict_or_disputed_claim",
        conflict_policy={
            "detect": True,
            "preserve": True,
            "arbitrate": True,
            "block_overconfident_claim": True,
        },
        final_posture_policy={
            "mandatory_caveats": ("credible_conflicts_must_be_preserved_or_arbitrated",),
            "prohibited_upgrades": ("do_not_flatten_conflicting_sources_into_unqualified_claim",),
        },
    ),
}

_CURRENT_TOKENS = {
    "current",
    "latest",
    "today",
    "now",
    "2026",
    "fee",
    "fees",
    "rate",
    "rates",
    "threshold",
    "thresholds",
    "rule",
    "rules",
    "policy",
    "status",
    "release",
    "price",
    "eligibility",
}
_OFFICIAL_TOKENS = {
    "official",
    "government",
    "agency",
    "irs",
    "ssa",
    "fda",
    "sec",
    "uscis",
    "regulation",
    "regulated",
}
_LEGAL_TOKENS = {
    "law",
    "legal",
    "regulation",
    "regulatory",
    "statute",
    "court",
    "jurisdiction",
    "eligibility",
    "procedure",
    "tax",
    "visa",
    "compliance",
}
_TECH_TOKENS = {
    "api",
    "sdk",
    "package",
    "library",
    "docs",
    "documentation",
    "changelog",
    "release notes",
    "version",
    "openai",
    "python",
    "npm",
}
_ACADEMIC_TOKENS = {
    "paper",
    "papers",
    "literature",
    "study",
    "studies",
    "benchmark",
    "dataset",
    "peer reviewed",
    "academic",
}
_USER_DOC_TOKENS = {
    "my file",
    "my document",
    "attached",
    "uploaded",
    "this file",
    "this document",
    "personal corpus",
    "my corpus",
}
_INFERENCE_TOKENS = {"infer", "inference", "deduce", "imply", "implied", "estimate from"}
_CONFLICT_TOKENS = {
    "conflict",
    "conflicting",
    "disagree",
    "disputed",
    "controversy",
    "different sources",
    "versus",
    "vs.",
}


def _text_blob(*values: Any) -> str:
    return " ".join(str(value or "").casefold() for value in values)


def _has_any(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def select_contract_template_ids(
    *,
    query: str,
    route_facts: Mapping[str, Any] | None = None,
    mode: str | None = None,
) -> tuple[str, ...]:
    """Select deterministic baseline templates from sanitized route/request facts."""

    facts = dict(route_facts or {})
    text = _text_blob(
        query,
        mode,
        facts.get("intent"),
        facts.get("report_type"),
        facts.get("query_type"),
        facts.get("core_topic"),
        facts.get("primary_entity"),
    )
    selected: list[str] = []
    if _has_any(text, _USER_DOC_TOKENS):
        selected.append(USER_DOCUMENT_OR_PERSONAL_CORPUS)
    if bool(facts.get("is_academic")) or _has_any(text, _ACADEMIC_TOKENS):
        selected.append(ACADEMIC_LITERATURE)
    if _has_any(text, _LEGAL_TOKENS):
        selected.append(LEGAL_OR_REGULATORY_CURRENT_PRIMARY)
    if _has_any(text, _TECH_TOKENS):
        selected.append(CANONICAL_TECHNICAL_DOCS)
    if (
        _has_any(text, _CURRENT_TOKENS)
        and (_has_any(text, _OFFICIAL_TOKENS) or _has_any(text, _LEGAL_TOKENS))
    ) or "quantitative" in text:
        selected.append(CURRENT_OFFICIAL_NUMERIC_OR_RULE)
    if _has_any(text, _INFERENCE_TOKENS):
        selected.append(INDIRECT_INFERENCE)
    if _has_any(text, _CONFLICT_TOKENS):
        selected.append(CONFLICT_SENSITIVE)
    if not selected:
        selected.append(ORDINARY_EXPLAINER)
    elif selected == [INDIRECT_INFERENCE] or selected == [CONFLICT_SENSITIVE]:
        selected.insert(0, ORDINARY_EXPLAINER)
    return tuple(dict.fromkeys(selected))


def _merge_tuple(existing: tuple[Any, ...], incoming: Sequence[Any] | None) -> tuple[Any, ...]:
    out = list(existing)
    for item in incoming or ():
        if item not in out:
            out.append(item)
    return tuple(out)


def _merge_mapping(base: dict[str, Any], update: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in update.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = _merge_mapping(dict(out[key]), value)
        elif isinstance(value, (list, tuple)) and isinstance(out.get(key), (list, tuple)):
            out[key] = _merge_tuple(tuple(out[key]), value)
        else:
            out[key] = value
    return out


def _dedupe_requirements(
    requirements: Sequence[RunContractSourceRequirement],
) -> tuple[RunContractSourceRequirement, ...]:
    by_key: dict[tuple[str | None, str | None], RunContractSourceRequirement] = {}
    for requirement in requirements:
        key = (
            requirement.required_source_class,
            requirement.requirement_kind.value,
        )
        existing = by_key.get(key)
        if existing is None or requirement.strictness_rank > existing.strictness_rank:
            by_key[key] = requirement
            continue
        if existing.strictness_rank == requirement.strictness_rank:
            by_key[key] = replace(
                existing,
                cannot_satisfy_with=_merge_tuple(
                    existing.cannot_satisfy_with,
                    requirement.cannot_satisfy_with,
                ),
            )
    return tuple(by_key.values())


def build_deterministic_contract(
    *,
    query: str,
    mode: str | None,
    route_facts: Mapping[str, Any] | None = None,
    selected_template_ids: Sequence[str] | None = None,
) -> RunAuthorityContract:
    template_ids = tuple(
        selected_template_ids
        or select_contract_template_ids(query=query, route_facts=route_facts, mode=mode)
    )
    templates = [
        TEMPLATE_REGISTRY[template_id]
        for template_id in template_ids
        if template_id in TEMPLATE_REGISTRY
    ]
    if not templates:
        templates = [TEMPLATE_REGISTRY[ORDINARY_EXPLAINER]]
        template_ids = (ORDINARY_EXPLAINER,)
    requirements: list[RunContractSourceRequirement] = []
    inference_policy: dict[str, Any] = {"policy": "direct_only"}
    conflict_policy: dict[str, Any] = {
        "detect": True,
        "preserve": False,
        "arbitrate": False,
        "block_overconfident_claim": False,
    }
    numeric_policy: dict[str, Any] = {
        "source_bound_required": False,
        "calculations_allowed_from_sourced_values": True,
        "unsupported_values_unknown": True,
    }
    recovery_policy: dict[str, Any] = {
        "recover_missing_official_current": False,
        "recover_missing_legal_primary": False,
        "recover_missing_canonical": False,
        "stop_when_budget_exhausted": True,
    }
    final_posture_policy: dict[str, Any] = {
        "definitive_allowed_if": "contract obligations satisfied",
        "partial_allowed_if": "required obligations missing but authorized with caveats",
        "insufficient_required_if": "required evidence unavailable",
        "mandatory_caveats": (),
        "prohibited_upgrades": (),
    }
    downstream_hints: dict[str, Any] = {
        "query_strategy_hints": (),
        "evidence_ledger_requirement_hints": (),
        "final_answer_packet_hints": (),
    }
    for template in templates:
        requirements.extend(template.source_requirements)
        inference_policy = _merge_mapping(inference_policy, template.inference_policy)
        conflict_policy = _merge_mapping(conflict_policy, template.conflict_policy)
        numeric_policy = _merge_mapping(numeric_policy, template.numeric_policy)
        recovery_policy = _merge_mapping(recovery_policy, template.recovery_policy)
        final_posture_policy = _merge_mapping(
            final_posture_policy,
            template.final_posture_policy,
        )
        downstream_hints = _merge_mapping(downstream_hints, template.downstream_hints)
    route_projection = {
        "intent": clean_token((route_facts or {}).get("intent")),
        "report_type": clean_token((route_facts or {}).get("report_type")),
        "query_type": clean_token((route_facts or {}).get("query_type")),
        "is_academic": bool((route_facts or {}).get("is_academic")),
        "core_topic_hash": stable_hash((route_facts or {}).get("core_topic")),
        "primary_entity_hash": stable_hash((route_facts or {}).get("primary_entity")),
    }
    question_type = templates[0].question_type
    claim_type = templates[0].claim_type
    contract_id = "run-contract-" + stable_hash(
        {
            "query_ref": query_ref(query),
            "mode": mode,
            "route_facts": route_projection,
            "templates": template_ids,
        }
    )[:16]
    return RunAuthorityContract(
        contract_id=contract_id,
        synthesis_mode=ContractSynthesisMode.DETERMINISTIC_TEMPLATE,
        selected_template_ids=tuple(template_ids),
        user_query_ref=query_ref(query),
        selected_depth=mode,
        route_facts_used=safe_json(route_projection),
        question_type=question_type,
        claim_type=claim_type,
        source_requirements=_dedupe_requirements(requirements),
        inference_policy=inference_policy,
        conflict_policy=conflict_policy,
        numeric_policy=numeric_policy,
        recovery_policy=recovery_policy,
        final_posture_policy=final_posture_policy,
        downstream_hints=downstream_hints,
    )


__all__ = [
    "ACADEMIC_LITERATURE",
    "CANONICAL_TECHNICAL_DOCS",
    "CONFLICT_SENSITIVE",
    "CURRENT_OFFICIAL_NUMERIC_OR_RULE",
    "INDIRECT_INFERENCE",
    "LEGAL_OR_REGULATORY_CURRENT_PRIMARY",
    "ORDINARY_EXPLAINER",
    "TEMPLATE_REGISTRY",
    "USER_DOCUMENT_OR_PERSONAL_CORPUS",
    "RunContractTemplate",
    "build_deterministic_contract",
    "select_contract_template_ids",
]
