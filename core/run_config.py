"""RunConfig, RunDeps, and RunOutcome — the boundary contracts for run_pipeline().

RunConfig  — pure data describing one pipeline invocation (no callables).
RunDeps    — injected callables and constants the orchestrator needs.
RunOutcome — everything produced by a completed pipeline run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping

from core.acquisition_adapters import AcquisitionTransports


@dataclass
class RunConfig:
    """All per-run settings.  Constructed by the Streamlit page or the CLI."""

    query: str
    mode: str = "Balanced"          # "Fast" | "Balanced" | "Deep"
    current_date: str = ""

    # Identity — if None the orchestrator generates fresh UUIDs.
    session_id: str | None = None
    run_id: str | None = None

    # Retrieval focus flags
    focus_academic: bool = False
    force_intent_news: bool = False

    # Domain allow/deny lists (already split by the caller)
    include_domains: list[str] = field(default_factory=list)
    exclude_domains: list[str] = field(default_factory=list)

    # Model routing
    fast_provider: str = "OpenAI"
    fast_model: str = "gpt-5.4-mini"
    smart_provider: str = "OpenAI"
    smart_model: str = "gpt-5.4"
    embed_provider: str = "OpenAI"
    embed_model: str = "text-embedding-3-small"
    local_url: str = "http://localhost:1234/v1"
    or_api_key: str = ""
    use_reasoning: bool = True
    run_authority_contract_smart_model: bool = False
    run_authority_search_judgment_smart_model: bool = False
    run_authority_sufficiency_smart_model: bool = False

    # Optional bounded planning-only context supplied alongside the utterance.
    # Future document/page ingestion may pass safe references or summaries here;
    # this field does not admit evidence or authorize retrieval.
    search_planner_supplied_context: Mapping[str, Any] = field(default_factory=dict)

    # Provider / corpus-state overrides (from UI failure-card controls)
    provider_override: list[str] | None = None
    forced_corpus_state: str | None = None

    # Thread-continuation data (passed in for "append to existing thread" flows).
    # The Streamlit layer resolves append_meta from session state and populates these.
    prior_run_history: list[dict[str, Any]] = field(default_factory=list)
    prior_snapshot_for_history: dict[str, Any] | None = None
    prior_title: str | None = None

    # Optional Streamlit hook: receives the author's token stream iterator (same-thread).
    author_stream_display: Callable[[Any], Any] | None = None

    # Optional bounded-validation policy. None preserves ordinary CLI/UI behavior.
    cap_policy: Any | None = None

    # Optional ordinary-path candidate handoff repair. Defaults preserve CLI/UI behavior.
    enable_ordinary_live_candidate_handoff: bool = False
    ordinary_live_candidate_handoff_results: (
        list[dict[str, Any]] | dict[str, Any]
    ) = field(default_factory=list)
    ordinary_live_candidate_handoff_provider: str = "offline-fake-search"

    # Optional ordinary-path source-custody repair. Defaults preserve CLI/UI behavior.
    enable_ordinary_live_source_custody: bool = False
    ordinary_live_source_custody_anchor_groups: tuple[Any, ...] = field(
        default_factory=tuple
    )

    # Optional ordinary-path semantic coverage repair. Defaults preserve behavior.
    enable_ordinary_live_semantic_coverage: bool = False

    # Optional ordinary-path authority consolidation precondition. Defaults preserve behavior.
    enable_ordinary_live_authority_consolidation: bool = False

    # Optional ordinary main RunKernel coverage repair. Defaults preserve behavior.
    enable_ordinary_live_main_runkernel_coverage: bool = False


@dataclass
class RunDeps:
    """Injected dependencies: callables, constants, and filesystem paths.

    The Streamlit layer wires these from UIContext + environment.
    The CLI wires them directly from core imports.
    """

    # LLM / embedding / search callables
    ask_model: Callable[..., Any]
    embed_texts: Callable[..., Any]
    compute_similarities: Callable[..., Any]
    process_search_queries: Callable[..., Any]
    filter_top_evidence: Callable[..., Any]
    is_plausible_domain: Callable[..., Any]
    anchor_query_to_topic: Callable[..., Any]
    clean_json_response: Callable[..., Any]

    # Prompt bundles and search constants
    DEFAULT_SYSTEM: dict[str, Any]
    NEWS_PREFERRED_DOMAINS: list[str]
    ACADEMIC_DOMAINS: list[str]
    QUANT_REPORT_TYPES: set[str]

    # Observability
    logger: logging.Logger

    # Output paths — typed as Path but accepted as Any for flexibility
    execution_log_path: Any          # Path
    feedback_log_path: Any           # Path
    kb_triggers_path: Any            # Path
    policy_state_path: Any           # Path
    policy_journal_path: Any         # Path

    # Optional isolated compatibility fields. Current ordinary composition and
    # runtime neither require, read, nor invoke these retired callables.
    fetch_linkup_precision_block: Callable[..., Any] | None = None
    run_scout: Callable[..., Any] | None = None
    should_skip_quant_scout: Callable[..., Any] | None = None

    # Optional isolated legacy compatibility field. Current ordinary runtime
    # neither reads nor invokes this callable.
    run_economist_step: Callable[..., Any] | None = None

    # Optional offline-only adapter for authorized component-gap recovery.
    component_gap_recovery_adapter: Callable[..., Any] | None = None

    # Typed semantic-planning composition seams. Ordinary execution composes
    # the selected fast-model SearchPlanner when no planner adapter is supplied;
    # Scout and revision remain unavailable unless explicitly injected.
    search_planner_adapter: Any | None = None
    scout_disambiguation_adapter: Any | None = None
    search_planner_revision_adapter: Any | None = None

    # Typed Linkup/Tavily exact-URL transports retained for a future licensed
    # post-selection proposal path selected by core.routing.
    ordinary_live_source_acquisition_transports: AcquisitionTransports | None = None

    # Neutral ordinary main-RunKernel READ transports. Product composition may
    # use installed providers; offline proof injects response-only callables.
    searchos_read_acquisition_transports: AcquisitionTransports | None = None

    # Optional explicit provider-availability facts for offline composition.
    # Normal product composition derives the same boolean snapshot from
    # configured credential presence; callables never imply availability.
    provider_availability: Mapping[str, object] | None = None

    # Optional Phase 5A strict one-shot SmartModel transport. When absent, the
    # ordinary multi-component runtime composes the repository-owned default.
    strict_one_shot_smart_model_transport: Callable[..., Any] | None = None

    # Optional S0 generic Specialist dependency injection.  Ordinary CLI/UI
    # construction leaves both unset, preserving the closed production policy.
    # Capability adapters remain on the registry object and are never retained
    # in RunKernel state.
    specialist_capability_registry: Any | None = None
    specialist_execution_policy: Any | None = None


@dataclass
class RunOutcome:
    """Everything a completed pipeline run produces.

    The Streamlit layer renders this (report, failure_card, KB warning, …)
    and saves new_session via save_session().
    The CLI writes the report to stdout and exits.
    """

    session_id: str
    run_id: str
    session_title: str
    query: str
    core_topic: str

    # The final report text (accumulated from the author step, streaming or not).
    report: str

    # Evidence and retrieval artefacts
    top_passages: list[dict[str, Any]]
    seen_urls: list[str]
    collected_images: list[str]

    # Rich diagnostics
    execution_trace: dict[str, Any]
    failure_card: dict[str, Any]

    # Session blob — pass directly to save_session()
    new_session: dict[str, Any]

    # Cost and timing
    cost_snapshot: dict[str, Any]
    latency_seconds: float

    # Routing metadata (useful for display / logging in the caller)
    intent: str
    complexity: str
    corpus_state: str
    pipeline_config: dict[str, Any]

    # KB review instrumentation — Streamlit stashes this in session_state
    kb_instrumentation: dict[str, Any] | None = None

    # Non-empty when the KB agent produced a "likely-recurring" hint the UI
    # should surface as a warning banner.
    kb_warning: str | None = None

    # True when the UI wired author_stream_display so the report was streamed live.
    author_streamed: bool = False


def compose_component_gap_recovery_deps(
    deps: RunDeps,
    *,
    enabled: bool = False,
    offline_recovery_adapter: Callable[..., Any] | None = None,
) -> RunDeps:
    """Return product dependencies with one-cycle recovery explicitly composed."""

    if not enabled:
        return replace(deps, component_gap_recovery_adapter=None)
    if offline_recovery_adapter is None:
        raise ValueError(
            "component-gap recovery composition requires an offline adapter"
        )
    return replace(deps, component_gap_recovery_adapter=offline_recovery_adapter)
