"""Reusable validation profiles for bounded live/product validation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from core.cap_enforcement import RunCapPolicy

AG_LIVE_SMOKE = "AG-LIVE-SMOKE"
AG_LIVE_SOURCE_CUSTODY = "AG-LIVE-SOURCE-CUSTODY"
AG_LIVE_MULTI_COMPONENT = "AG-LIVE-MULTI-COMPONENT"
AG_LIVE_DISAMBIG = "AG-LIVE-DISAMBIG"
AG_LIVE_XAXIS_SEARCH_CANDIDATES = "AG-LIVE-XAXIS-SEARCH-CANDIDATES"
AG_LIVE_S1_PRODUCT_CONVERGENCE = "AG-LIVE-S1-PRODUCT-CONVERGENCE"

DIRECT_HUMAN_PRIVATE_SHELL = "direct_human_private_shell"
BROKER_PRIVATE_ADAPTER = "broker_private_adapter"

LIVE_STATUS_SUCCEEDED_ONCE_DIRECT_HUMAN = "succeeded_once_direct_human_private_shell"
LIVE_STATUS_NOT_RUN = "not_run"
LIVE_STATUS_RETIRED_NON_EXECUTABLE = "retired_non_executable"

AG_LIVE_S1_QUERY_A_NO_QUANT = (
    "Using only NASA's official Earth and Mars facts pages, answer two separate "
    "components:\n\n"
    "1. Report Earth's stated length of day and number of moons.\n"
    "2. Report Mars's stated length of day and number of moons.\n\n"
    "Then compare those stated facts qualitatively. Do not calculate totals, "
    "differences, ratios, averages, percentages, or converted values."
)
AG_LIVE_S1_QUERY_B_COMPONENT_CALC = (
    "Using NASA's official Earth facts page, answer two separately supported "
    "components:\n\n"
    "1. Calculate the absolute difference between Earth's stated equatorial and "
    "polar diameters, using the exact source-visible kilometer literals.\n"
    "2. Report Earth's stated length of day.\n\n"
    "Do not round or convert units."
)
AG_LIVE_S1_QUERY_C_SYNTHESIS_CALC = (
    "Using NASA's official Earth facts page and Mars facts page as separate answer "
    "components:\n\n"
    "1. Report Earth's stated equatorial diameter in kilometers.\n"
    "2. Report Mars's stated equatorial diameter in kilometers.\n\n"
    "Then calculate the absolute difference between those admitted component values, "
    "using the exact source-visible literals. Do not round or convert units."
)
AG_LIVE_S1_QUERY_D_CONVERSION_NEGATIVE = (
    "Using NASA's official Earth facts page and Mars facts page as separate answer "
    "components:\n\n"
    "1. Report Earth's stated equatorial diameter in kilometers.\n"
    "2. Report Mars's stated equatorial diameter in kilometers.\n\n"
    "Then convert both diameters to miles and calculate their difference in miles. "
    "Use only the source-visible kilometer literals."
)
AG_LIVE_S1_FIXED_QUERIES: tuple[tuple[str, str], ...] = (
    ("A_NO_QUANT", AG_LIVE_S1_QUERY_A_NO_QUANT),
    ("B_COMPONENT_CALC", AG_LIVE_S1_QUERY_B_COMPONENT_CALC),
    ("C_SYNTHESIS_CALC", AG_LIVE_S1_QUERY_C_SYNTHESIS_CALC),
    ("D_CONVERSION_NEGATIVE", AG_LIVE_S1_QUERY_D_CONVERSION_NEGATIVE),
)

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
PRODUCT_SOURCE_CUSTODY_POLICY_SURFACE = (
    "ValidationProfile.source_custody_policy_non_executable_expectation"
)
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
    max_search_dispatches: int | None = None
    max_fetch_read_operations: int | None = None
    max_author_model_calls: int | None = None
    max_smart_search_judgment_model_calls: int | None = None
    max_independent_manual_source_checks: int | None = None
    max_retries: int | None = None

    def as_requested_dict(self) -> dict[str, int]:
        values: dict[str, int] = {
            "max_scryraven_runs": self.max_scryraven_runs,
        }
        for field_name in (
            "max_search_dispatches",
            "max_fetch_read_operations",
            "max_author_model_calls",
            "max_smart_search_judgment_model_calls",
            "max_independent_manual_source_checks",
            "max_retries",
        ):
            value = getattr(self, field_name)
            if value is not None:
                values[field_name] = value
        return values

    def to_run_cap_policy(self) -> RunCapPolicy:
        logical_overrides: dict[str, int] = {}
        for field_name in (
            "max_search_dispatches",
            "max_fetch_read_operations",
            "max_author_model_calls",
            "max_smart_search_judgment_model_calls",
            "max_retries",
        ):
            value = getattr(self, field_name)
            if value is not None:
                logical_overrides[field_name] = value
        return RunCapPolicy(**logical_overrides)


@dataclass(frozen=True, slots=True)
class CampaignOperationalBudgetSpec:
    """Hard operational limits for the bounded S1 convergence campaign."""

    full_scryraven_runs: int
    generative_plus_embedding_calls: int
    external_provider_search_calls: int
    retrieval_fetch_read_operations: int
    observed_model_plus_embedding_tokens: int
    independent_manual_source_checks: int
    root_cause_repair_clusters: int
    repeated_failed_query_reruns: int
    live_contact_elapsed_seconds: int
    campaign_added_retries: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "full_scryraven_runs": self.full_scryraven_runs,
            "generative_plus_embedding_calls": (
                self.generative_plus_embedding_calls
            ),
            "external_provider_search_calls": self.external_provider_search_calls,
            "retrieval_fetch_read_operations": (
                self.retrieval_fetch_read_operations
            ),
            "observed_model_plus_embedding_tokens": (
                self.observed_model_plus_embedding_tokens
            ),
            "independent_manual_source_checks": (
                self.independent_manual_source_checks
            ),
            "root_cause_repair_clusters": self.root_cause_repair_clusters,
            "repeated_failed_query_reruns": self.repeated_failed_query_reruns,
            "live_contact_elapsed_seconds": self.live_contact_elapsed_seconds,
            "campaign_added_retries": self.campaign_added_retries,
        }


@dataclass(frozen=True, slots=True)
class ValidationSourceCustodyPolicySpec:
    """Non-executable historical source-custody expectation metadata."""

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
class SearchCandidateValidationProfile:
    """Narrow search-only validation profile for AG-LIVE-XAXIS PR2."""

    name: str = AG_LIVE_XAXIS_SEARCH_CANDIDATES
    purpose: str = "Search-only candidate discovery for one handoff task."
    max_selected_tasks: int = 1
    provider_call_cap: int = 1
    results_per_task_cap: int = 2
    retry_cap: int = 0
    fetch_read_cap: int = 0
    retrieval_cap: int = 0
    evidence_ledger_admission_cap: int = 0
    citation_eligibility_cap: int = 0
    sufficiency_cap: int = 0
    final_answer_packet_cap: int = 0
    author_cap: int = 0
    raw_provider_payload_retained: bool = False
    raw_search_response_retained: bool = False
    output_root: str = "output/"
    live_status: str = LIVE_STATUS_NOT_RUN

    def broker_request_caps(self) -> dict[str, int]:
        return {
            "provider_call_cap": self.provider_call_cap,
            "results_per_task_cap": self.results_per_task_cap,
            "retry_cap": self.retry_cap,
            "fetch_read_cap": self.fetch_read_cap,
            "retrieval_cap": self.retrieval_cap,
            "evidence_ledger_admission_cap": self.evidence_ledger_admission_cap,
            "citation_eligibility_cap": self.citation_eligibility_cap,
            "sufficiency_cap": self.sufficiency_cap,
            "final_answer_packet_cap": self.final_answer_packet_cap,
            "author_cap": self.author_cap,
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
    fixed_queries: tuple[tuple[str, str], ...] = ()

    def supports_direct_runner(self) -> bool:
        return (
            DIRECT_HUMAN_PRIVATE_SHELL in self.allowed_invocation_modes
            and (self.primary_query is not None or bool(self.fixed_queries))
        )

    def fixed_query_map(self) -> dict[str, str]:
        return {query_id: query for query_id, query in self.fixed_queries}

    def fixed_query_digests(self) -> dict[str, str]:
        return {
            query_id: hashlib.sha256(query.encode("utf-8")).hexdigest()
            for query_id, query in self.fixed_queries
        }

    def query_id_for(self, query: str) -> str | None:
        normalized = str(query or "").strip()
        for query_id, fixed_query in self.fixed_queries:
            if normalized == fixed_query:
                return query_id
        return None

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
            "source_custody_policy_enabled": False,
            "source_custody_policy_expectation_recorded": (
                self.source_custody_policy is not None
            ),
            "subject_budget_policy": (
                self.subject_budget.as_requested_dict()
                if self.subject_budget is not None
                else None
            ),
            "subject_budget_enabled": bool(
                self.subject_budget
                and self.subject_budget.subject_budget_enabled
            ),
            "fixed_query_digests": self.fixed_query_digests(),
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


# Ordinary dogfood owns only the experimental PRODUCT-run authority. Logical
# role counts remain observations unless an experiment explicitly requests a
# cap; omitted fields intentionally flow through RunCapPolicy compatibility
# defaults rather than becoming phase-local product policy.
ORDINARY_DOGFOOD_CAP_POLICY = ValidationCapPolicySpec(max_scryraven_runs=1)

AG_LIVE_S1_PER_RUN_CAP_POLICY = ValidationCapPolicySpec(
    max_scryraven_runs=1,
    max_search_dispatches=4,
    max_fetch_read_operations=8,
    max_author_model_calls=1,
    max_smart_search_judgment_model_calls=0,
    max_independent_manual_source_checks=1,
    max_retries=0,
)

AG_LIVE_S1_BLOCK_A_OPERATIONAL_BUDGET = CampaignOperationalBudgetSpec(
    full_scryraven_runs=6,
    generative_plus_embedding_calls=90,
    external_provider_search_calls=30,
    retrieval_fetch_read_operations=60,
    observed_model_plus_embedding_tokens=225_000,
    independent_manual_source_checks=4,
    root_cause_repair_clusters=2,
    repeated_failed_query_reruns=2,
    live_contact_elapsed_seconds=4 * 60 * 60,
)

AG_LIVE_S1_BLOCK_B_OPERATIONAL_BUDGET = CampaignOperationalBudgetSpec(
    full_scryraven_runs=4,
    generative_plus_embedding_calls=60,
    external_provider_search_calls=20,
    retrieval_fetch_read_operations=40,
    observed_model_plus_embedding_tokens=175_000,
    independent_manual_source_checks=2,
    root_cause_repair_clusters=1,
    repeated_failed_query_reruns=0,
    live_contact_elapsed_seconds=2 * 60 * 60,
)

AG_LIVE_S1_COMBINED_OPERATIONAL_BUDGET = CampaignOperationalBudgetSpec(
    full_scryraven_runs=10,
    generative_plus_embedding_calls=150,
    external_provider_search_calls=50,
    retrieval_fetch_read_operations=100,
    observed_model_plus_embedding_tokens=400_000,
    independent_manual_source_checks=6,
    root_cause_repair_clusters=3,
    repeated_failed_query_reruns=2,
    live_contact_elapsed_seconds=6 * 60 * 60,
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

AG_LIVE_XAXIS_SEARCH_CANDIDATE_PROFILE = SearchCandidateValidationProfile()

VALIDATION_PROFILES: dict[str, ValidationProfile] = {
    AG_LIVE_S1_PRODUCT_CONVERGENCE: ValidationProfile(
        name=AG_LIVE_S1_PRODUCT_CONVERGENCE,
        purpose=(
            "Characterize and converge the ordinary bounded multi-component "
            "quantitative Specialist product path."
        ),
        proof_target="bounded live S1 ordinary product-path convergence",
        allowed_invocation_modes=(DIRECT_HUMAN_PRIVATE_SHELL,),
        live_status=LIVE_STATUS_NOT_RUN,
        query_intent="fixed NASA official-facts bounded S1 matrix",
        required_mode=BALANCED_MODE,
        required_include_domains=("nasa.gov",),
        cap_policy=AG_LIVE_S1_PER_RUN_CAP_POLICY,
        expected_packet_criteria=(
            "ordinary run_pipeline executes exactly once per requested run",
            "ordinary S1 product registry and execution policy are composed",
            "source custody remains explicit and is not favorably upgraded",
            "sanitized packet retains no raw or private material",
        ),
        fixed_queries=AG_LIVE_S1_FIXED_QUERIES,
        source_custody_policy=ValidationSourceCustodyPolicySpec(
            require_official_full_fetch_read=True,
            max_forced_fetch_reads=2,
            preferred_domains=("nasa.gov",),
            required_source_class="primary_source_documents",
            required_source_tier="official",
            required_currentness="current",
            requirement_id="ag-live-s1-product-convergence:nasa-official-full-read",
        ),
    ),
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
        cap_policy=ORDINARY_DOGFOOD_CAP_POLICY,
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
            "Historical pre-selection official-doc fetch/read validation metadata; "
            "retired from executable composition."
        ),
        proof_target="none; retained only as a non-executable historical expectation",
        allowed_invocation_modes=(),
        live_status=LIVE_STATUS_RETIRED_NON_EXECUTABLE,
        query_intent="official documentation fact requiring fetch/read custody",
        primary_query=AG_LIVE_BOUND_PRIMARY_QUERY,
        backup_query=AG_LIVE_BOUND_BACKUP_QUERY,
        required_mode=BALANCED_MODE,
        required_include_domains=(PYTHON_DOCS_DOMAIN,),
        cap_policy=ORDINARY_DOGFOOD_CAP_POLICY,
        expected_packet_criteria=(
            "historical expectation only",
            "not selectable by the direct runner or broker",
            "no initial-discovery exact-URL transport authority",
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
        cap_policy=ORDINARY_DOGFOOD_CAP_POLICY,
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
        cap_policy=ORDINARY_DOGFOOD_CAP_POLICY,
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
    return tuple(
        name
        for name, profile in VALIDATION_PROFILES.items()
        if profile.allowed_invocation_modes
    )


def get_search_candidate_validation_profile() -> SearchCandidateValidationProfile:
    return AG_LIVE_XAXIS_SEARCH_CANDIDATE_PROFILE
