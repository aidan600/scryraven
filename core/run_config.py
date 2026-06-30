"""RunConfig, RunDeps, and RunOutcome — the boundary contracts for run_pipeline().

RunConfig  — pure data describing one pipeline invocation (no callables).
RunDeps    — injected callables and constants the orchestrator needs.
RunOutcome — everything produced by a completed pipeline run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class SourceCustodyPolicy:
    """Optional policy for custody-required official source full reads."""

    require_official_full_fetch_read: bool = False
    max_forced_fetch_reads: int = 1
    preferred_domains: tuple[str, ...] = ()
    required_source_class: str = "primary_source_documents"
    required_source_tier: str = "official"
    required_currentness: str = "current"
    requirement_id: str = "source-custody:official-full-fetch-read"
    required_evidence_material_type: str = "full_page_fetched"
    admission_reason: str = "source_custody_policy_full_fetch_read"

    def enabled(self) -> bool:
        return bool(
            self.require_official_full_fetch_read
            and int(self.max_forced_fetch_reads or 0) > 0
        )


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

    # Optional source-custody policy. None preserves ordinary CLI/UI behavior.
    source_custody_policy: SourceCustodyPolicy | None = None

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
    fetch_linkup_precision_block: Callable[..., Any]
    run_economist_step: Callable[..., Any]
    run_scout: Callable[..., Any]
    should_skip_quant_scout: Callable[..., Any]
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

    # Optional offline-only adapter for authorized component-gap recovery.
    component_gap_recovery_adapter: Callable[..., Any] | None = None

    # Optional offline/fake fetch-read adapter for ordinary source custody.
    ordinary_live_source_fetch_read: Callable[..., Any] | None = None


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
