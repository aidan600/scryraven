"""Reusable validation profiles for bounded live/product validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from core.cap_enforcement import RunCapPolicy
from core.run_config import SourceCustodyPolicy

AG_LIVE_SMOKE = "AG-LIVE-SMOKE"
AG_LIVE_SOURCE_CUSTODY = "AG-LIVE-SOURCE-CUSTODY"
AG_LIVE_MULTI_COMPONENT = "AG-LIVE-MULTI-COMPONENT"
AG_LIVE_DISAMBIG = "AG-LIVE-DISAMBIG"

DIRECT_HUMAN_PRIVATE_SHELL = "direct_human_private_shell"
BROKER_PRIVATE_ADAPTER = "broker_private_adapter"

LIVE_STATUS_SUCCEEDED_ONCE_DIRECT_HUMAN = "succeeded_once_direct_human_private_shell"
LIVE_STATUS_NOT_RUN = "not_run"

AG_LIVE_BOUND_PRIMARY_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for rel_tol and abs_tol in math.isclose()?"
)
AG_LIVE_BOUND_BACKUP_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for start and step in itertools.count()?"
)
AG_LIVE_MULTI_COMPONENT_PRIMARY_QUERY = (
    "Using official documentation, what are the default ports for PostgreSQL, "
    "MySQL, Redis, and MongoDB? Answer separately for each project with one "
    "official citation per project."
)
AG_LIVE_MULTI_COMPONENT_BACKUP_QUERY = (
    "Using official documentation, compare the default HTTP server port or "
    "documented default listen address/port behavior for Nginx, Apache HTTP "
    "Server, Caddy, and Traefik. Answer separately for each project with one "
    "official citation per project."
)

BALANCED_MODE = "Balanced"
PYTHON_DOCS_DOMAIN = "docs.python.org"
MULTI_COMPONENT_DOCS_DOMAINS = (
    "postgresql.org",
    "dev.mysql.com",
    "redis.io",
    "mongodb.com",
)
PACKET_SCHEMA = "ag_live_bound_01_bounded_product_runner_v1"
APPROVED_PRODUCT_ENTRYPOINT = "scripts/ag_live_bound_01_bounded_product_runner.py"
PRODUCT_RUNTIME_CONSUMER = "run_pipeline"
PRODUCT_CAP_POLICY_SURFACE = "RunConfig.cap_policy"
PRODUCT_SOURCE_CUSTODY_POLICY_SURFACE = "RunConfig.source_custody_policy"
RETENTION_POSTURE = "sanitized_packet_only_with_ordinary_retention_suppressed"
MAX_INITIAL_SELECTED_SUBJECTS = 5
SUBJECT_BUDGET_SCOPE_INITIAL_INDEPENDENT = "initial_independent_subjects_only"
SUBJECT_BUDGET_SELECTION_SOURCE = (
    "existing_component_order_or_existing_searchwork_order"
)
FOLLOWUP_BUDGET_POLICY = (
    "internal_followups_governed_by_existing_mode_and_resource_caps"
)


@dataclass(frozen=True, slots=True)
class ValidationCapPolicySpec:
    """Serializable cap-policy spec owned by product validation profiles."""

    max_scryraven_runs: int
    max_search_dispatches: int
    max_fetch_read_operations: int
    max_author_model_calls: int
    max_smart_search_judgment_model_calls: int
    max_independent_manual_source_checks: int
    max_retries: int

    def as_requested_dict(self) -> dict[str, int]:
        return {
            "max_scryraven_runs": self.max_scryraven_runs,
            "max_search_dispatches": self.max_search_dispatches,
            "max_fetch_read_operations": self.max_fetch_read_operations,
            "max_author_model_calls": self.max_author_model_calls,
            "max_smart_search_judgment_model_calls": (
                self.max_smart_search_judgment_model_calls
            ),
            "max_independent_manual_source_checks": (
                self.max_independent_manual_source_checks
            ),
            "max_retries": self.max_retries,
        }

    def to_run_cap_policy(self) -> RunCapPolicy:
        return RunCapPolicy(
            max_search_dispatches=self.max_search_dispatches,
            max_fetch_read_operations=self.max_fetch_read_operations,
            max_author_model_calls=self.max_author_model_calls,
            max_smart_search_judgment_model_calls=(
                self.max_smart_search_judgment_model_calls
            ),
            max_retries=self.max_retries,
        )


@dataclass(frozen=True, slots=True)
class ValidationSourceCustodyPolicySpec:
    """Serializable source-custody policy spec for validation profiles."""

    require_official_full_fetch_read: bool
    max_forced_fetch_reads: int
    preferred_domains: tuple[str, ...]
    required_source_class: str
    required_source_tier: str
    required_currentness: str
    requirement_id: str
    required_evidence_material_type: str = "full_page_fetched"
    admission_reason: str = "source_custody_policy_full_fetch_read"

    def as_requested_dict(self) -> dict[str, Any]:
        return {
            "require_official_full_fetch_read": bool(
                self.require_official_full_fetch_read
            ),
            "max_forced_fetch_reads": int(self.max_forced_fetch_reads),
            "preferred_domains": list(self.preferred_domains),
            "required_source_class": self.required_source_class,
            "required_source_tier": self.required_source_tier,
            "required_currentness": self.required_currentness,
            "requirement_id": self.requirement_id,
            "required_evidence_material_type": self.required_evidence_material_type,
            "admission_reason": self.admission_reason,
        }

    def to_run_policy(
        self,
        *,
        include_domains: Sequence[str] = (),
    ) -> SourceCustodyPolicy:
        preferred_domains = tuple(self.preferred_domains or tuple(include_domains))
        return SourceCustodyPolicy(
            require_official_full_fetch_read=self.require_official_full_fetch_read,
            max_forced_fetch_reads=self.max_forced_fetch_reads,
            preferred_domains=preferred_domains,
            required_source_class=self.required_source_class,
            required_source_tier=self.required_source_tier,
            required_currentness=self.required_currentness,
            requirement_id=self.requirement_id,
            required_evidence_material_type=self.required_evidence_material_type,
            admission_reason=self.admission_reason,
        )


@dataclass(frozen=True, slots=True)
class ValidationSubjectBudgetSpec:
    """Serializable passive subject-budget metadata for validation profiles."""

    subject_budget_enabled: bool
    max_initial_selected_subjects: int | None
    subject_budget_scope: str = SUBJECT_BUDGET_SCOPE_INITIAL_INDEPENDENT
    applies_to_internal_followups: bool = False
    same_source_evidence_allowed: bool | None = False
    subject_selection_source: str = SUBJECT_BUDGET_SELECTION_SOURCE
    followup_budget_policy: str = FOLLOWUP_BUDGET_POLICY
    policy_status: str = "planned_not_live_licensed"

    def as_requested_dict(self) -> dict[str, Any]:
        return {
            "subject_budget_enabled": bool(self.subject_budget_enabled),
            "max_initial_selected_subjects": self.max_initial_selected_subjects,
            "subject_budget_scope": self.subject_budget_scope,
            "applies_to_internal_followups": bool(
                self.applies_to_internal_followups
            ),
            "same_source_evidence_allowed": self.same_source_evidence_allowed,
            "subject_selection_source": self.subject_selection_source,
            "followup_budget_policy": self.followup_budget_policy,
            "policy_status": self.policy_status,
        }


@dataclass(frozen=True, slots=True)
class ValidationProfile:
    """Product-owned validation profile consumed by direct and broker paths."""

    name: str
    purpose: str
    proof_target: str
    allowed_invocation_modes: tuple[str, ...]
    live_status: str
    query_intent: str
    required_mode: str
    required_include_domains: tuple[str, ...]
    cap_policy: ValidationCapPolicySpec
    expected_packet_criteria: tuple[str, ...]
    retention_posture: str = RETENTION_POSTURE
    packet_schema: str = PACKET_SCHEMA
    primary_query: str | None = None
    backup_query: str | None = None
    approved_product_entrypoint: str = APPROVED_PRODUCT_ENTRYPOINT
    runtime_consumer: str = PRODUCT_RUNTIME_CONSUMER
    cap_policy_surface: str = PRODUCT_CAP_POLICY_SURFACE
    current_evidence: str = "none"
    source_custody_policy: ValidationSourceCustodyPolicySpec | None = None
    source_custody_policy_surface: str = PRODUCT_SOURCE_CUSTODY_POLICY_SURFACE
    subject_budget: ValidationSubjectBudgetSpec | None = None

    def supports_direct_runner(self) -> bool:
        return (
            DIRECT_HUMAN_PRIVATE_SHELL in self.allowed_invocation_modes
            and self.primary_query is not None
        )

    def packet_identity(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "proof_target": self.proof_target,
            "allowed_invocation_modes": list(self.allowed_invocation_modes),
            "live_status": self.live_status,
            "packet_schema": self.packet_schema,
            "retention_posture": self.retention_posture,
            "runtime_consumer": self.runtime_consumer,
            "cap_policy_surface": self.cap_policy_surface,
            "approved_product_entrypoint": self.approved_product_entrypoint,
            "source_custody_policy_surface": self.source_custody_policy_surface,
            "source_custody_policy_enabled": self.source_custody_policy is not None,
            "subject_budget_policy": (
                self.subject_budget.as_requested_dict()
                if self.subject_budget is not None
                else None
            ),
            "subject_budget_enabled": bool(
                self.subject_budget
                and self.subject_budget.subject_budget_enabled
            ),
        }

    def broker_request_shape(self) -> dict[str, Any]:
        return {
            "validation_profile": self.name,
            "approved_product_entrypoint": self.approved_product_entrypoint,
            "query_constraints": {
                "intent": self.query_intent,
                "primary_query": self.primary_query,
                "backup_query": self.backup_query,
                "mode": self.required_mode,
                "include_domains": list(self.required_include_domains),
            },
            "cap_policy": {
                "surface": self.cap_policy_surface,
                "values": self.cap_policy.as_requested_dict(),
            },
            "source_custody_policy": (
                {
                    "surface": self.source_custody_policy_surface,
                    "values": self.source_custody_policy.as_requested_dict(),
                }
                if self.source_custody_policy is not None
                else None
            ),
            "subject_budget_policy": (
                self.subject_budget.as_requested_dict()
                if self.subject_budget is not None
                else None
            ),
            "retention_posture": self.retention_posture,
            "packet_schema": self.packet_schema,
            "expected_packet_criteria": list(self.expected_packet_criteria),
        }


BOUND_CAP_POLICY = ValidationCapPolicySpec(
    max_scryraven_runs=1,
    max_search_dispatches=2,
    max_fetch_read_operations=3,
    max_author_model_calls=1,
    max_smart_search_judgment_model_calls=0,
    max_independent_manual_source_checks=1,
    max_retries=0,
)

AG_LIVE_SOURCE_CUSTODY_POLICY = ValidationSourceCustodyPolicySpec(
    require_official_full_fetch_read=True,
    max_forced_fetch_reads=1,
    preferred_domains=(PYTHON_DOCS_DOMAIN,),
    required_source_class="primary_source_documents",
    required_source_tier="official",
    required_currentness="current",
    requirement_id="ag-live-source-custody:official-doc-full-read",
)

AG_LIVE_MULTI_COMPONENT_SUBJECT_BUDGET = ValidationSubjectBudgetSpec(
    subject_budget_enabled=True,
    max_initial_selected_subjects=MAX_INITIAL_SELECTED_SUBJECTS,
    subject_budget_scope=SUBJECT_BUDGET_SCOPE_INITIAL_INDEPENDENT,
    applies_to_internal_followups=False,
    same_source_evidence_allowed=False,
    subject_selection_source=SUBJECT_BUDGET_SELECTION_SOURCE,
    followup_budget_policy=FOLLOWUP_BUDGET_POLICY,
    policy_status="planned_not_run_not_live_licensed",
)

VALIDATION_PROFILES: dict[str, ValidationProfile] = {
    AG_LIVE_SMOKE: ValidationProfile(
        name=AG_LIVE_SMOKE,
        purpose="Can one bounded live product run complete?",
        proof_target="ordinary product run completes under bounded caps",
        allowed_invocation_modes=(DIRECT_HUMAN_PRIVATE_SHELL, BROKER_PRIVATE_ADAPTER),
        live_status=LIVE_STATUS_SUCCEEDED_ONCE_DIRECT_HUMAN,
        current_evidence=(
            "Succeeded once by direct human private shell after local env was loaded "
            "into process env; not source-custody, multi-component, or disambiguation proof."
        ),
        query_intent="official Python documentation exact API defaults smoke query",
        primary_query=AG_LIVE_BOUND_PRIMARY_QUERY,
        backup_query=AG_LIVE_BOUND_BACKUP_QUERY,
        required_mode=BALANCED_MODE,
        required_include_domains=(PYTHON_DOCS_DOMAIN,),
        cap_policy=BOUND_CAP_POLICY,
        expected_packet_criteria=(
            "run_pipeline_call_count == 1 on live success",
            "planned_live_dispatch is true only after preflight passes",
            "sanitized packet contains final answer and cited URLs when available",
            "no raw prompt/provider/model/full-trace/private material serialized",
        ),
    ),
    AG_LIVE_SOURCE_CUSTODY: ValidationProfile(
        name=AG_LIVE_SOURCE_CUSTODY,
        purpose=(
            "Can an official-doc fact be fetched, read, and admitted into custody?"
        ),
        proof_target="official source custody reaches final answer citation",
        allowed_invocation_modes=(DIRECT_HUMAN_PRIVATE_SHELL, BROKER_PRIVATE_ADAPTER),
        live_status=LIVE_STATUS_NOT_RUN,
        query_intent="official documentation fact requiring fetch/read custody",
        primary_query=AG_LIVE_BOUND_PRIMARY_QUERY,
        backup_query=AG_LIVE_BOUND_BACKUP_QUERY,
        required_mode=BALANCED_MODE,
        required_include_domains=(PYTHON_DOCS_DOMAIN,),
        cap_policy=BOUND_CAP_POLICY,
        expected_packet_criteria=(
            "run_pipeline_call_count == 1",
            "fetch_read_operations > 0",
            "official source custody satisfied",
            "final answer cites admitted official source",
            "no awkward official-doc custody partial posture after admission",
        ),
        source_custody_policy=AG_LIVE_SOURCE_CUSTODY_POLICY,
    ),
    AG_LIVE_MULTI_COMPONENT: ValidationProfile(
        name=AG_LIVE_MULTI_COMPONENT,
        purpose=(
            "Can a bounded initial set of multi-subject answer components map "
            "to component obligations, evidence bindings, and packet-owned "
            "Author material?"
        ),
        proof_target=(
            "up to five initial independent subjects/components bind to "
            "FinalAnswerPacket evidence"
        ),
        allowed_invocation_modes=(DIRECT_HUMAN_PRIVATE_SHELL, BROKER_PRIVATE_ADAPTER),
        live_status=LIVE_STATUS_NOT_RUN,
        query_intent=(
            "planned four-component official documentation default-port answer"
        ),
        primary_query=AG_LIVE_MULTI_COMPONENT_PRIMARY_QUERY,
        backup_query=AG_LIVE_MULTI_COMPONENT_BACKUP_QUERY,
        required_mode=BALANCED_MODE,
        required_include_domains=MULTI_COMPONENT_DOCS_DOMAINS,
        cap_policy=BOUND_CAP_POLICY,
        expected_packet_criteria=(
            "detected initial independent subjects/components are visible",
            "selected initial subjects/components are capped at up to five",
            "omitted subjects/components are recorded when detected count exceeds five",
            "component coverage for selected answer components",
            "FinalAnswerPacket evidence binding for selected components",
            "search dispatch count interpreted by coverage rather than target count alone",
            "internal follow-ups remain governed by existing mode/resource caps",
            "packet-owned Author material reflects selected components",
        ),
        subject_budget=AG_LIVE_MULTI_COMPONENT_SUBJECT_BUDGET,
    ),
    AG_LIVE_DISAMBIG: ValidationProfile(
        name=AG_LIVE_DISAMBIG,
        purpose=(
            "Can ambiguous entities/components produce explicit disambiguation and "
            "search work without hidden provider or routing changes?"
        ),
        proof_target="visible disambiguation/search work under unchanged provider policy",
        allowed_invocation_modes=(DIRECT_HUMAN_PRIVATE_SHELL, BROKER_PRIVATE_ADAPTER),
        live_status=LIVE_STATUS_NOT_RUN,
        query_intent="future exact ambiguous public entity/component query",
        primary_query=None,
        backup_query=None,
        required_mode=BALANCED_MODE,
        required_include_domains=(),
        cap_policy=BOUND_CAP_POLICY,
        expected_packet_criteria=(
            "disambiguation/search work plan visible in sanitized packet or trace summary",
            "no provider bake-off",
            "no implicit provider policy change",
            "no routing/depth/query-generation behavior change",
        ),
    ),
}


def get_validation_profile(name: str) -> ValidationProfile:
    try:
        return VALIDATION_PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown validation profile: {name}") from exc


def validation_profile_names() -> tuple[str, ...]:
    return tuple(VALIDATION_PROFILES)
