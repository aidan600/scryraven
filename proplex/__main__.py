"""Headless CLI for the ScryRaven research pipeline.

Usage
-----
    python -m scryraven "your query here" [--mode Fast|Balanced|Deep] [options]
    python -m proplex "your query here" [--mode Fast|Balanced|Deep] [options]

The CLI calls run_pipeline() directly — no Streamlit, no browser.
On success it prints the report to stdout and appends one record to
output/execution_log.jsonl.

Environment variables (same as the Streamlit app):
    OPENAI_API_KEY          required for OpenAI models
    TAVILY_API_KEY          required when Tavily is an active provider
    LINKUP_API_KEY          required when Linkup is an active provider
    EXA_API_KEY             required when Exa is an active provider
    BRAVE_API_KEY           required when Brave is an active provider
    OPENROUTER_API_KEY      optional (OpenRouter provider)

ScryRaven model configuration aliases are preferred. Legacy PROPLEX_* aliases
remain supported as a compatibility layer.
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Ensure the project root is on sys.path when run as "python -m proplex" from
# outside the repo root (e.g. installed as a script).
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.product_model_route_config import (  # noqa: E402
    CONFIRM_CURRENT_SOURCE_FOLLOWUP_REENTRY_FLAG,
    CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
    CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
    LIVE_ACQUISITION_READABILITY_STATUS_FLAG,
    LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG,
    LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
    LIVE_SOURCE_EVIDENCE_ADMISSION_STATUS_FLAG,
    MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
    MVP_DEMO_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
    MVP_LIVE_DOGFOOD_STATUS_FLAG,
    MVP_QUERY_PLAN_STATUS_FLAG,
    MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
    ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG,
    ProductModelRouteConfigInitialization,
    initialize_product_model_route_config,
)


def _argv_selects_bounded_authorization(raw_argv: list[str]) -> bool:
    return any(
        value == "--bounded-run-authorization"
        or value.startswith("--bounded-run-authorization=")
        for value in raw_argv
    )


_MODULE_IMPORT_ARGV = list(sys.argv[1:])
_PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZED = not _argv_selects_bounded_authorization(
    _MODULE_IMPORT_ARGV
)
PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZATION = (
    initialize_product_model_route_config(
        _MODULE_IMPORT_ARGV,
        load_dotenv_func=load_dotenv,
    )
    if _PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZED
    else ProductModelRouteConfigInitialization()
)

import core.pipeline_orchestrator as pipeline_orchestrator  # noqa: E402
from core.cap_enforcement import RunCapExceeded  # noqa: E402
from core.cost_accounting import CostAccumulator  # noqa: E402
from core.final_answer_packet_runtime import (  # noqa: E402
    BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE,
    BLOCKED_FAP_TERMINAL_SCHEMA_VERSION,
    BLOCKED_FAP_TERMINAL_TRACE_KEY,
)
from core.generic_query_to_relation_planning import (  # noqa: E402
    MVP_QUERY_PLANNING_OUTPUT_DIR,
    build_generic_query_plan_status_output,
)
from core.initial_query_strategy_failure import (  # noqa: E402
    INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY,
    InitialQueryStrategyFailureError,
    project_initial_query_strategy_failure_for_terminal,
)
from core.llm import ask_model, compute_similarities, embed_texts  # noqa: E402
from core.official_canonical_recovery_visibility_export import (  # noqa: E402
    append_official_canonical_recovery_diagnostics_section,
)
from core.pipeline import (  # noqa: E402
    QUANT_REPORT_TYPES,
    process_search_queries,
)
from core.pipeline_orchestrator import PipelineError, run_pipeline  # noqa: E402
from core.prompts import DEFAULT_SYSTEM  # noqa: E402
from core.protocols import NullStatusWriter  # noqa: E402
from core.provider_validation import missing_required_api_keys  # noqa: E402
from core.quantitative_specialist_product_activation import (  # noqa: E402
    compose_quantitative_specialist_product_deps,
)
from core.query_production_runtime import QueryStrategyConvergenceError  # noqa: E402
from core.retrieval import (  # noqa: E402
    ACADEMIC_DOMAINS,
    NEWS_PREFERRED_DOMAINS,
    anchor_query_to_topic,
    filter_top_evidence,
    is_plausible_domain,
)
from core.run_cap_authorization import (  # noqa: E402
    BoundedRunAuthorizationError,
    CompiledRunCapAuthorization,
    compile_bounded_run_authorization,
)
from core.run_config import RunConfig, RunDeps  # noqa: E402
from core.search_planner_model_adapter import SearchPlannerModelAdapterError  # noqa: E402
from core.search_planner_runtime import SearchPlannerRuntimeError  # noqa: E402
from core.searchos_slice_a_product_runtime import (  # noqa: E402
    SEARCHOS_SLICE_A_TRACE_KEY,
    build_bounded_searchos_n1_causal_projection,
)
from core.strict_accounted_model_route import (  # noqa: E402
    build_strict_accounted_fast_model_planning_route,
)
from core.text_utils import clean_json_response  # noqa: E402
from proplex.env_aliases import get_env_alias  # noqa: E402
from proplex.live_acquisition_readability_status import (  # noqa: E402
    build_live_acquisition_readability_status,
)
from proplex.live_citation_source_obligation_readiness_status import (  # noqa: E402
    build_live_citation_source_obligation_readiness_status,
)
from proplex.live_semantic_coverage_status import (  # noqa: E402
    build_live_semantic_coverage_status,
)
from proplex.live_source_evidence_admission_status import (  # noqa: E402
    build_live_source_evidence_admission_status,
)
from proplex.mvp_friend_shareable_output import (  # noqa: E402
    DEFAULT_MVP_LIVE_OUTPUT_DIR,
    DEFAULT_MVP_OUTPUT_DIR,
    DEFAULT_MVP_QUERY,
    build_mvp_demo_output,
    build_mvp_live_dogfood_status_output,
)
from proplex.mvp_live_dogfood_run import (  # noqa: E402
    CONFIRM_LIVE_DOGFOOD_FLAG,
    DEFAULT_BROKER_URL,
    build_mvp_live_dogfood_run_output,
)
from proplex.mvp_single_relation_live_dogfood_run import (  # noqa: E402
    CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG,
    DOGFOOD_ENTRYPOINT_KIND,
    DOGFOOD_ENTRYPOINT_SURFACE,
    DOGFOOD_SUPPORTED_QUERY_CLASS,
    PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND,
    PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE,
    PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS,
    build_generic_single_relation_live_dogfood_run_output,
)
from proplex.mvp_single_relation_live_dogfood_run import (
    DEFAULT_OUTPUT_DIR as DEFAULT_MVP_SINGLE_RELATION_LIVE_OUTPUT_DIR,
)
from proplex.ordinary_live_entrypoint_dry_run import (  # noqa: E402
    OrdinaryLiveEntrypointDryRunDeps,
    build_ordinary_live_entrypoint_dry_run_config,
    format_ordinary_live_entrypoint_dry_run_status,
)

OUTPUT_DIR = _ROOT / "output"
SOURCE_OF_RECORD_RECOVERY_PROVIDER_DECISION_FLAG = "--source-of-record-recovery-provider-decision"


def _build_logger(
    verbose: bool,
    *,
    persistent: bool = True,
) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.WARNING
    if not persistent:
        bounded_log = logging.getLogger("proplex.cli.bounded")
        bounded_log.handlers.clear()
        bounded_log.addHandler(logging.StreamHandler(sys.stderr))
        bounded_log.setLevel(level)
        bounded_log.propagate = False
        return bounded_log
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if persistent:
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            handlers.append(logging.FileHandler(OUTPUT_DIR / "app.log"))
        except OSError:
            pass
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("proplex.cli")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m scryraven",
        description=(
            "Run the ScryRaven research pipeline headlessly. Legacy entrypoint python -m proplex remains supported."
        ),
        epilog="Compatibility: python -m proplex remains supported for existing scripts.",
    )
    p.add_argument("query", nargs="?", help="Research query / topic")
    p.add_argument(
        "--query",
        dest="query_option",
        default=None,
        help=(
            "Research query / topic. For --mvp-demo, only the fixed MVP "
            "fixture query is supported. For --mvp-query-plan-status, a "
            "supported-class user query is required. For "
            "--mvp-single-relation-live-dogfood-run, the query is required."
        ),
    )
    p.add_argument(
        "--mode",
        choices=["Fast", "Balanced", "Deep"],
        default="Balanced",
        help="Pipeline mode (default: Balanced)",
    )
    p.add_argument(
        "--fast-provider",
        default=get_env_alias("SCRYRAVEN_FAST_PROVIDER", "PROPLEX_FAST_PROVIDER", "OpenAI"),
        metavar="PROVIDER",
        help="Fast-model provider (OpenAI | OpenRouter | Local (LM Studio))",
    )
    p.add_argument(
        "--fast-model",
        default=get_env_alias("SCRYRAVEN_FAST_MODEL", "PROPLEX_FAST_MODEL", "gpt-5.4-mini"),
        metavar="MODEL",
        help="Fast model name",
    )
    p.add_argument(
        "--smart-provider",
        default=get_env_alias("SCRYRAVEN_SMART_PROVIDER", "PROPLEX_SMART_PROVIDER", "OpenAI"),
        metavar="PROVIDER",
        help="Smart-model provider",
    )
    p.add_argument(
        "--smart-model",
        default=get_env_alias("SCRYRAVEN_SMART_MODEL", "PROPLEX_SMART_MODEL", "gpt-5.4"),
        metavar="MODEL",
        help="Smart model name",
    )
    p.add_argument(
        "--fast-reasoning-effort",
        default=get_env_alias(
            "SCRYRAVEN_FAST_REASONING_EFFORT",
            "PROPLEX_FAST_REASONING_EFFORT",
            "medium",
        ),
        choices=("low", "medium", "high"),
        metavar="EFFORT",
        help="Reasoning effort for the FAST model profile (low|medium|high)",
    )
    p.add_argument(
        "--smart-reasoning-effort",
        default=get_env_alias(
            "SCRYRAVEN_SMART_REASONING_EFFORT",
            "PROPLEX_SMART_REASONING_EFFORT",
            "medium",
        ),
        choices=("low", "medium", "high"),
        metavar="EFFORT",
        help="Reasoning effort for the SMART model profile (low|medium|high)",
    )
    p.add_argument(
        "--embed-provider",
        default=get_env_alias("SCRYRAVEN_EMBED_PROVIDER", "PROPLEX_EMBED_PROVIDER", "OpenAI"),
        metavar="PROVIDER",
    )
    p.add_argument(
        "--embed-model",
        default=get_env_alias(
            "SCRYRAVEN_EMBED_MODEL",
            "PROPLEX_EMBED_MODEL",
            "text-embedding-3-small",
        ),
        metavar="MODEL",
    )
    p.add_argument(
        "--local-url",
        default=get_env_alias(
            "SCRYRAVEN_LOCAL_URL",
            "PROPLEX_LOCAL_URL",
            "http://localhost:1234/v1",
        ),
        metavar="URL",
        help="Base URL for local LM Studio server",
    )
    p.add_argument(
        "--no-reasoning",
        action="store_true",
        help="Disable reasoning effort parameter (for non-reasoning models)",
    )
    p.add_argument(
        "--academic",
        action="store_true",
        help="Force academic / Exa-first retrieval mode",
    )
    p.add_argument(
        "--news",
        action="store_true",
        help="Force news intent (recent-events retrieval mode)",
    )
    p.add_argument(
        "--include-domains",
        default="",
        metavar="DOMAINS",
        help="Comma-separated allow-list of domains",
    )
    p.add_argument(
        "--exclude-domains",
        default="",
        metavar="DOMAINS",
        help="Comma-separated deny-list of domains",
    )
    p.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write report to FILE instead of stdout",
    )
    p.add_argument(
        ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG,
        action="store_true",
        dest="ordinary_live_main_runkernel_coverage_dry_run",
        help=(
            "Run a default-off offline dry-run that visibly reaches ordinary-live "
            "main RunKernel coverage without live calls."
        ),
    )
    p.add_argument(
        LIVE_ACQUISITION_READABILITY_STATUS_FLAG,
        action="store_true",
        dest="live_acquisition_readability_status_dry_run",
        help=(
            "Consume retained sanitized live acquisition/readability artifacts "
            "and print status without live calls or answer prose."
        ),
    )
    p.add_argument(
        LIVE_SOURCE_EVIDENCE_ADMISSION_STATUS_FLAG,
        action="store_true",
        dest="live_source_evidence_admission_status_dry_run",
        help=(
            "Consume retained sanitized live acquisition/readability artifacts "
            "and print source/evidence admission status without live calls or "
            "answer prose."
        ),
    )
    p.add_argument(
        LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG,
        action="store_true",
        dest="live_citation_source_obligation_readiness_status_dry_run",
        help=(
            "Consume retained source/evidence custody status and print citation/"
            "source-obligation readiness posture without live calls, citations, "
            "source-obligation satisfaction, or answer prose."
        ),
    )
    p.add_argument(
        LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
        action="store_true",
        dest="live_semantic_coverage_status_dry_run",
        help=(
            "Consume retained citation/source-obligation readiness status and "
            "print semantic support/component coverage status without live calls, "
            "citations, source-obligation satisfaction, or answer prose."
        ),
    )
    p.add_argument(
        MVP_DEMO_FLAG,
        action="store_true",
        dest="mvp_demo",
        help=(
            "Run the no-secrets offline fixed-fixture MVP demo through the "
            "existing D-prime semantic coverage and answer-output status path."
        ),
    )
    p.add_argument(
        MVP_LIVE_DOGFOOD_RUN_FLAG,
        action="store_true",
        dest="mvp_live_dogfood_run",
        help=(
            "Run one explicitly confirmed live MVP dogfood attempt through the "
            "tracked generic provider-execution broker boundary and "
            "retained-artifact status consumer."
        ),
    )
    p.add_argument(
        MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
        action="store_true",
        dest="mvp_single_relation_live_dogfood_run",
        help=(
            "Run one explicitly confirmed generic single-relation live dogfood "
            "attempt from the relation planner into retained-artifact status."
        ),
    )
    p.add_argument(
        MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
        action="store_true",
        dest="mvp_current_source_of_record_single_fact_run",
        help=(
            "Run the supported current source-of-record single-fact query CLI "
            "through the generic single-relation product path."
        ),
    )
    p.add_argument(
        CONFIRM_LIVE_DOGFOOD_FLAG,
        action="store_true",
        dest="confirm_live_dogfood",
        help="Confirm the single live MVP dogfood attempt.",
    )
    p.add_argument(
        CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
        action="store_true",
        dest="confirm_current_source_of_record_single_fact_run",
        help="Confirm the current source-of-record single-fact supported-query run.",
    )
    p.add_argument(
        CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
        action="store_true",
        dest="confirm_live_dprime_review",
        help="Confirm one D-prime product-route model-review attempt for live dogfood.",
    )
    p.add_argument(
        CONFIRM_CURRENT_SOURCE_FOLLOWUP_REENTRY_FLAG,
        action="store_true",
        dest="confirm_current_source_followup_reentry",
        help=(
            "Confirm one bounded current-source follow-up re-entry pass through "
            "ordinary provider acquisition and fetch/read."
        ),
    )
    p.add_argument(
        CONFIRM_LIVE_SOURCE_CHALLENGE_RECOVERY_FLAG,
        action="store_true",
        dest="confirm_live_source_challenge_recovery",
        help=("Confirm one additional generic single-relation source-challenge recovery acquisition attempt."),
    )
    p.add_argument(
        MVP_LIVE_DOGFOOD_STATUS_FLAG,
        action="store_true",
        dest="mvp_live_dogfood_status",
        help=(
            "Consume already-retained sanitized live dogfood artifacts through "
            "the MVP product status view without making live calls."
        ),
    )
    p.add_argument(
        MVP_QUERY_PLAN_STATUS_FLAG,
        action="store_true",
        dest="mvp_query_plan_status",
        help=(
            "Run a default-off no-live deterministic supported-query relation "
            "planning dry run and write a sanitized packet."
        ),
    )
    p.add_argument(
        SOURCE_OF_RECORD_RECOVERY_PROVIDER_DECISION_FLAG,
        action="store_true",
        dest="source_of_record_recovery_provider_decision",
        help=(
            "Run the default-off source-of-record recovery provider decision "
            "flow through the ordinary proplex credential boundary."
        ),
    )
    p.add_argument(
        "--confirm-live-provider-comparison",
        action="store_true",
        dest="confirm_live_provider_comparison",
        help="Confirm the one licensed live provider comparison job.",
    )
    p.add_argument(
        "--output-root",
        default=None,
        metavar="DIR",
        help=("Write source-of-record recovery provider decision packets under DIR."),
    )
    p.add_argument(
        "--provider-decision-run-id",
        default=None,
        metavar="ID",
        help="Optional run id for the source-of-record provider decision packet.",
    )
    p.add_argument(
        "--mvp-output-dir",
        default=None,
        metavar="DIR",
        help=(
            "Write MVP review packets under DIR. Defaults to output/mvp_demo_01 "
            "or output/mvp_live_dogfood_01; query planning defaults to "
            "output/mvp_query_plan_01; generic single-relation live dogfood "
            "defaults to output/mvp_single_relation_live_dogfood_01."
        ),
    )
    p.add_argument(
        "--mvp-live-broker-url",
        default=DEFAULT_BROKER_URL,
        metavar="URL",
        help="Loopback provider-proxy broker URL for --mvp-live-dogfood-run.",
    )
    p.add_argument(
        "--mvp-live-env-file",
        action="append",
        default=None,
        metavar="PATH",
        help=(
            "Private env-file path passed only to the tracked broker child for "
            "--mvp-live-dogfood-run. At most one path is accepted."
        ),
    )
    p.add_argument(
        "--mvp-retained-artifact-root",
        default=None,
        metavar="DIR",
        help=(
            "For --mvp-live-dogfood-status, consume retained status artifacts from DIR instead of the repository root."
        ),
    )
    p.add_argument(
        "--bounded-run-authorization",
        default=None,
        metavar="FILE",
        help=(
            "Path to one local explicit bounded-run authorization JSON file. "
            "When present, all routes, limits, price facts, deadline, and "
            "max_run_usd come from that file; repository defaults are not used."
        ),
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print DEBUG log to stderr",
    )
    args = p.parse_args(argv)
    if args.bounded_run_authorization:
        incompatible_flags = {
            "source_of_record_recovery_provider_decision": (
                args.source_of_record_recovery_provider_decision
            ),
            "mvp_demo": args.mvp_demo,
            "mvp_live_dogfood_run": args.mvp_live_dogfood_run,
            "mvp_single_relation_live_dogfood_run": (
                args.mvp_single_relation_live_dogfood_run
            ),
            "mvp_current_source_of_record_single_fact_run": (
                args.mvp_current_source_of_record_single_fact_run
            ),
            "mvp_live_dogfood_status": args.mvp_live_dogfood_status,
            "mvp_query_plan_status": args.mvp_query_plan_status,
            "ordinary_live_main_runkernel_coverage_dry_run": (
                args.ordinary_live_main_runkernel_coverage_dry_run
            ),
            "live_acquisition_readability_status_dry_run": (
                args.live_acquisition_readability_status_dry_run
            ),
            "live_source_evidence_admission_status_dry_run": (
                args.live_source_evidence_admission_status_dry_run
            ),
            "live_citation_source_obligation_readiness_status_dry_run": (
                args.live_citation_source_obligation_readiness_status_dry_run
            ),
            "live_semantic_coverage_status_dry_run": (
                args.live_semantic_coverage_status_dry_run
            ),
            "confirm_live_dogfood": args.confirm_live_dogfood,
            "confirm_live_dprime_review": args.confirm_live_dprime_review,
            "confirm_current_source_of_record_single_fact_run": (
                args.confirm_current_source_of_record_single_fact_run
            ),
            "confirm_current_source_followup_reentry": (
                args.confirm_current_source_followup_reentry
            ),
            "confirm_live_source_challenge_recovery": (
                args.confirm_live_source_challenge_recovery
            ),
            "confirm_live_provider_comparison": args.confirm_live_provider_comparison,
            "mvp_live_env_file": bool(args.mvp_live_env_file),
            "output_root": bool(args.output_root),
            "provider_decision_run_id": bool(args.provider_decision_run_id),
            "mvp_output_dir": bool(args.mvp_output_dir),
            "mvp_retained_artifact_root": bool(args.mvp_retained_artifact_root),
        }
        selected = sorted(name for name, enabled in incompatible_flags.items() if enabled)
        if selected:
            p.error(
                "--bounded-run-authorization cannot be combined with special "
                f"operator/status modes: {', '.join(selected)}"
            )
        if args.output:
            p.error("--bounded-run-authorization forbids persistent --output")
        if args.verbose:
            p.error("--bounded-run-authorization forbids verbose raw diagnostics")
        required_explicit = (
            "--mode",
            "--include-domains",
            "--fast-provider",
            "--fast-model",
            "--smart-provider",
            "--smart-model",
            "--embed-provider",
            "--embed-model",
        )
        raw = list(argv or [])
        missing = [
            name
            for name in required_explicit
            if not any(item == name or item.startswith(f"{name}=") for item in raw)
        ]
        if missing:
            p.error(
                "--bounded-run-authorization requires explicit CLI values for: "
                + ", ".join(missing)
            )
    if args.query and args.query_option and args.query != args.query_option:
        p.error("query positional argument and --query must match when both are provided")
    if args.query_option:
        args.query = args.query_option
    if not args.query and (args.mvp_demo or args.mvp_live_dogfood_run or args.mvp_live_dogfood_status):
        args.query = DEFAULT_MVP_QUERY
    if not args.query and not args.source_of_record_recovery_provider_decision:
        p.error("the following arguments are required: query")
    return args


def _parse_domains(raw: str) -> list[str]:
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def _build_run_config(
    args: argparse.Namespace,
    *,
    compiled_authorization: CompiledRunCapAuthorization | None = None,
) -> RunConfig:
    bounded = compiled_authorization is not None
    return RunConfig(
        query=args.query,
        mode=args.mode,
        current_date=datetime.now().strftime("%B %d, %Y"),
        focus_academic=args.academic,
        force_intent_news=args.news,
        include_domains=_parse_domains(args.include_domains),
        exclude_domains=_parse_domains(args.exclude_domains),
        fast_provider=args.fast_provider,
        fast_model=args.fast_model,
        smart_provider=args.smart_provider,
        smart_model=args.smart_model,
        fast_reasoning_effort=args.fast_reasoning_effort,
        smart_reasoning_effort=args.smart_reasoning_effort,
        embed_provider=args.embed_provider,
        embed_model=args.embed_model,
        local_url=args.local_url,
        or_api_key=("" if bounded else os.getenv("OPENROUTER_API_KEY", "")),
        use_reasoning=not args.no_reasoning,
        cap_policy=(
            compiled_authorization.policy if compiled_authorization is not None else None
        ),
    )


def _build_run_deps(log: logging.Logger) -> RunDeps:
    deps = RunDeps(
        ask_model=ask_model,
        embed_texts=embed_texts,
        compute_similarities=compute_similarities,
        process_search_queries=process_search_queries,
        filter_top_evidence=filter_top_evidence,
        is_plausible_domain=is_plausible_domain,
        anchor_query_to_topic=anchor_query_to_topic,
        clean_json_response=clean_json_response,
        DEFAULT_SYSTEM=DEFAULT_SYSTEM,
        NEWS_PREFERRED_DOMAINS=list(NEWS_PREFERRED_DOMAINS),
        ACADEMIC_DOMAINS=list(ACADEMIC_DOMAINS),
        QUANT_REPORT_TYPES=set(QUANT_REPORT_TYPES),
        logger=log,
        execution_log_path=OUTPUT_DIR / "execution_log.jsonl",
        feedback_log_path=OUTPUT_DIR / "feedback_log.jsonl",
        kb_triggers_path=OUTPUT_DIR / "kb_triggers.jsonl",
        policy_state_path=OUTPUT_DIR / "policy_state.json",
        policy_journal_path=OUTPUT_DIR / "policy_journal.jsonl",
    )
    return compose_quantitative_specialist_product_deps(deps)


class BoundedEntrypointSetupFailureCode(str, Enum):
    """Closed call-site-owned setup stages for the bounded ordinary CLI."""

    RUN_CONFIG_INITIALIZATION = "run_config_initialization"
    PROVIDER_PREREQUISITE_VALIDATION = "provider_prerequisite_validation"
    RUN_DEPS_COMPOSITION = "run_deps_composition"
    RUNTIME_SUPPORT_INITIALIZATION = "runtime_support_initialization"


_BOUNDED_ENTRYPOINT_SETUP_FAILURE_SCHEMA_VERSION = (
    "bounded_entrypoint_setup_failure_v1"
)
_BOUNDED_ENTRYPOINT_SETUP_FAILURE_BOUNDARY = "bounded_entrypoint_setup"


def _bounded_success_payload(
    *,
    entrypoint: str,
    config: RunConfig,
    outcome: Any,
    compiled_authorization: CompiledRunCapAuthorization,
    include_searchos_n1_causal_projection: bool = True,
) -> dict[str, object]:
    policy = config.cap_policy
    if policy is None or not policy.bounded:
        raise RuntimeError("bounded result requires an active bounded policy")
    report = str(outcome.report or "")
    terminal_status = str(outcome.terminal_status or "").strip()
    if terminal_status not in {"blocked", "completed"}:
        raise RuntimeError("bounded result requires a governed terminal status")
    execution_trace = dict(getattr(outcome, "execution_trace", {}) or {})
    blocked_terminal = dict(
        execution_trace.get(BLOCKED_FAP_TERMINAL_TRACE_KEY) or {}
    )
    if terminal_status == BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE:
        if (
            blocked_terminal.get("schema_version")
            != BLOCKED_FAP_TERMINAL_SCHEMA_VERSION
            or blocked_terminal.get("exported_terminal_posture")
            != BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE
            or blocked_terminal.get("author_called") is not False
        ):
            raise RuntimeError(
                "blocked bounded result requires the typed blocked FAP terminal"
            )
        answer = ""
        terminal_owner = "core.final_answer_packet_runtime"
    else:
        if blocked_terminal:
            raise RuntimeError(
                "completed bounded result cannot carry a blocked FAP terminal"
            )
        answer = report
        terminal_owner = "core.pipeline_orchestrator.run_pipeline"
    physical_envelope = policy.physical_snapshot()
    citation_count = len(
        re.findall(
            r"\[{1,2}[^\]\r\n]+\]\]?\(https?://[^)\s]+\)",
            answer,
        )
    )
    terminal: dict[str, object] = {
        "owner": terminal_owner,
        "classification": terminal_status,
    }
    payload: dict[str, object] = {
        "schema_version": "bounded_product_cli_result_v1",
        "status": terminal_status,
        "terminal_status": terminal_status,
        "terminal": terminal,
        "bounded_posture": True,
        "entrypoint": entrypoint,
        "ordinary_consumer": "core.pipeline_orchestrator.run_pipeline",
        "authorization_id": compiled_authorization.authorization_id,
        "authorization_digest": compiled_authorization.authorization_digest,
        "pricing_fact_set_id": compiled_authorization.pricing_fact_set_id,
        "repository_sha": compiled_authorization.repository_sha,
        "furthest_product_stage": physical_envelope["furthest_product_stage"],
        "run_id": outcome.run_id,
        "session_id": outcome.session_id,
        "answer": answer,
        "answer_present": bool(answer.strip()),
        "citation_count": citation_count,
        "citation_present": citation_count > 0,
        "physical_envelope": physical_envelope,
        "retention": {
            "raw_prompt": False,
            "raw_provider_payload": False,
            "raw_model_response": False,
            "execution_jsonl": False,
            "policy_journal": False,
            "knowledge_base": False,
            "database": False,
        },
    }
    if terminal_status == BLOCKED_FAP_TERMINAL_EXPORTED_POSTURE:
        terminal[BLOCKED_FAP_TERMINAL_TRACE_KEY] = blocked_terminal
        payload["terminal_report"] = report
    causal_projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(
            dict(getattr(outcome, "execution_trace", {}) or {}).get(
                SEARCHOS_SLICE_A_TRACE_KEY
            )
            or {}
        ),
        enabled=include_searchos_n1_causal_projection,
    )
    if causal_projection is not None:
        payload["searchos_n1_causal_projection"] = causal_projection
    return payload

def _bounded_terminal_payload(
    *,
    entrypoint: str,
    exc: (
        RunCapExceeded
        | BoundedRunAuthorizationError
        | SearchPlannerModelAdapterError
        | InitialQueryStrategyFailureError
        | QueryStrategyConvergenceError
        | SearchPlannerRuntimeError
        | None
    ),
    config: RunConfig | None,
    code: str | None = None,
    setup_failure_code: BoundedEntrypointSetupFailureCode | None = None,
    compiled_authorization: CompiledRunCapAuthorization | None = None,
    authorization_id: str | None = None,
    authorization_digest: str | None = None,
    pricing_fact_set_id: str | None = None,
    repository_sha: str | None = None,
    observed_query_digest: str | None = None,
) -> dict[str, object]:
    auth_error = isinstance(exc, BoundedRunAuthorizationError)
    configuration_failure = (
        auth_error
        or (exc is not None and config is None)
        or code == "bounded_configuration_unavailable"
    )
    if auth_error:
        assert isinstance(exc, BoundedRunAuthorizationError)
        terminal_core = {
            "code": "bounded_configuration_unavailable",
            "message": "The bounded-run authorization is incomplete or unsupported.",
            "reason": exc.reason_code,
        }
        authorization_id = authorization_id or exc.authorization_id
        authorization_digest = authorization_digest or exc.authorization_digest
        observed_query_digest = observed_query_digest or exc.observed_query_digest
    elif setup_failure_code is not None:
        terminal_core = {
            "code": "bounded_entrypoint_setup_failed",
            "message": (
                "The bounded entrypoint stopped during setup without retaining raw "
                "diagnostics."
            ),
        }
    elif exc is not None and config is None:
        assert isinstance(exc, RunCapExceeded)
        terminal_core = {
            "code": "bounded_configuration_unavailable",
            "message": "The bounded-run authorization is incomplete or unsupported.",
            "reason": exc.reason_code,
        }
        if exc.family is not None:
            terminal_core["family"] = exc.family.value
    else:
        terminal_core = (
            exc.terminal_payload()
            if isinstance(exc, RunCapExceeded)
            else {
                "code": code or "bounded_run_failed",
                "message": "The bounded run stopped without retaining raw diagnostics.",
            }
        )
    if compiled_authorization is not None:
        authorization_id = authorization_id or compiled_authorization.authorization_id
        authorization_digest = (
            authorization_digest or compiled_authorization.authorization_digest
        )
        pricing_fact_set_id = (
            pricing_fact_set_id or compiled_authorization.pricing_fact_set_id
        )
        repository_sha = repository_sha or compiled_authorization.repository_sha
    if setup_failure_code is not None:
        terminal_owner = "proplex.__main__.main"
        terminal_classification = "entrypoint_setup_failure"
    elif isinstance(exc, RunCapExceeded) and not configuration_failure:
        terminal_owner = "core.cap_enforcement.RunCapPolicy"
        terminal_classification = "cap_enforcement"
    elif configuration_failure:
        terminal_owner = "core.run_cap_authorization"
        terminal_classification = "configuration"
    else:
        terminal_owner = "core.pipeline_orchestrator.run_pipeline"
        terminal_classification = "pipeline_failure"
    terminal = {
        **terminal_core,
        "owner": terminal_owner,
        "classification": terminal_classification,
    }
    if setup_failure_code is not None:
        terminal["bounded_entrypoint_setup_failure"] = {
            "schema_version": _BOUNDED_ENTRYPOINT_SETUP_FAILURE_SCHEMA_VERSION,
            "boundary": _BOUNDED_ENTRYPOINT_SETUP_FAILURE_BOUNDARY,
            "failure_code": setup_failure_code.value,
        }
    if isinstance(exc, SearchPlannerModelAdapterError):
        terminal["search_planner_failure"] = {
            "failure_stage": exc.failure_stage.value,
            "failure_code": exc.failure_code.value,
            "mechanical_rule_id": exc.mechanical_rule_id,
            "predicate_registry_version": exc.predicate_registry_version,
            "predicate_id": (
                exc.predicate_id.value
                if exc.predicate_id is not None
                else None
            ),
            "provider_completion_posture": (
                exc.provider_completion_posture.value
                if exc.provider_completion_posture is not None
                else None
            ),
            "strict_parse_subtype": (
                exc.strict_parse_subtype.value
                if exc.strict_parse_subtype is not None
                else None
            ),
            "semantic_proposal_subtype": (
                exc.semantic_proposal_subtype.value
                if exc.semantic_proposal_subtype is not None
                else None
            ),
            "cleaner_modified": exc.cleaner_modified,
        }
    else:
        initial_planning_failure = project_initial_query_strategy_failure_for_terminal(
            exc
        )
        if initial_planning_failure is not None:
            terminal[INITIAL_QUERY_STRATEGY_FAILURE_TERMINAL_KEY] = (
                initial_planning_failure
            )
    policy = config.cap_policy if config is not None else None
    payload: dict[str, object] = {
        "schema_version": "bounded_product_cli_terminal_v1",
        "status": "stopped",
        "terminal_status": "stopped",
        "bounded_posture": True,
        "entrypoint": entrypoint,
        "ordinary_consumer": "core.pipeline_orchestrator.run_pipeline",
        "terminal": terminal,
        "answer_present": False,
        "citation_count": 0,
        "citation_present": False,
        "retention": {
            "raw_prompt": False,
            "raw_provider_payload": False,
            "raw_model_response": False,
            "execution_jsonl": False,
            "policy_journal": False,
            "knowledge_base": False,
            "database": False,
        },
    }
    if authorization_id:
        payload["authorization_id"] = authorization_id
    if authorization_digest:
        payload["authorization_digest"] = authorization_digest
    if pricing_fact_set_id:
        payload["pricing_fact_set_id"] = pricing_fact_set_id
    if repository_sha:
        payload["repository_sha"] = repository_sha
    if observed_query_digest:
        payload["observed_query_digest"] = observed_query_digest
    if policy is not None and policy.bounded and policy.envelope is not None:
        physical_envelope = policy.physical_snapshot()
        payload["authorization_id"] = (
            authorization_id or policy.envelope.authorization_id
        )
        payload["authorization_digest"] = (
            authorization_digest or policy.envelope.authorization_digest
        )
        payload["pricing_fact_set_id"] = (
            pricing_fact_set_id or policy.envelope.pricing_fact_set_id
        )
        payload["furthest_product_stage"] = physical_envelope["furthest_product_stage"]
        payload["physical_envelope"] = physical_envelope
    else:
        payload["furthest_product_stage"] = "configuration"
    return payload

def _print_bounded_payload(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, ensure_ascii=True))


def _print_bounded_entrypoint_setup_failure(
    *,
    entrypoint: str,
    config: RunConfig | None,
    compiled_authorization: CompiledRunCapAuthorization,
    failure_code: BoundedEntrypointSetupFailureCode,
) -> None:
    """Emit one sanitized bounded terminal for a known setup call site."""

    _print_bounded_payload(
        _bounded_terminal_payload(
            entrypoint=entrypoint,
            exc=None,
            config=config,
            setup_failure_code=failure_code,
            compiled_authorization=compiled_authorization,
        )
    )


def _argv_requests_ordinary_live_dry_run(argv: list[str] | None) -> bool:
    raw = sys.argv[1:] if argv is None else list(argv)
    return ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG in raw


def _run_ordinary_live_entrypoint_dry_run(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    current_date = datetime.now().strftime("%B %d, %Y")
    config = build_ordinary_live_entrypoint_dry_run_config(
        query=args.query,
        mode=args.mode,
        current_date=current_date,
        include_domains=_parse_domains(args.include_domains),
        exclude_domains=_parse_domains(args.exclude_domains),
    )
    dry_run_deps_builder = OrdinaryLiveEntrypointDryRunDeps(
        output_dir=OUTPUT_DIR,
        logger=log,
    )
    deps = dry_run_deps_builder.to_run_deps()

    status = NullStatusWriter()
    accumulator = CostAccumulator()
    original_db_enabled = pipeline_orchestrator.DB_ENABLED
    original_kb_review_agent = pipeline_orchestrator.kb_review_agent
    pipeline_orchestrator.DB_ENABLED = False
    pipeline_orchestrator.kb_review_agent = lambda *_args, **_kwargs: {}
    try:
        outcome = run_pipeline(config, deps, status, accumulator)
    except PipelineError as exc:
        print(f"ERROR: Pipeline failed during ordinary-live dry-run - {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log.exception("Unexpected ordinary-live dry-run error")
        print(f"ERROR: Unexpected ordinary-live dry-run error - {exc}", file=sys.stderr)
        return 1
    finally:
        pipeline_orchestrator.DB_ENABLED = original_db_enabled
        pipeline_orchestrator.kb_review_agent = original_kb_review_agent

    dry_run_output = format_ordinary_live_entrypoint_dry_run_status(
        execution_trace=outcome.execution_trace,
    )
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(dry_run_output, encoding="utf-8")
        print(f"Dry-run status written to {out_path}", file=sys.stderr)
    else:
        print(dry_run_output)
    return 0


def _run_live_acquisition_readability_status(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    try:
        result = build_live_acquisition_readability_status(
            query=args.query,
            repo_root=_ROOT,
        )
    except Exception as exc:
        log.exception("Unexpected live acquisition/readability status error")
        print(
            f"ERROR: Unexpected live acquisition/readability status error - {exc}",
            file=sys.stderr,
        )
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"Status written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_live_source_evidence_admission_status(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    try:
        result = build_live_source_evidence_admission_status(
            query=args.query,
            repo_root=_ROOT,
        )
    except Exception as exc:
        log.exception("Unexpected live source/evidence admission status error")
        print(
            f"ERROR: Unexpected live source/evidence admission status error - {exc}",
            file=sys.stderr,
        )
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"Status written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_live_citation_source_obligation_readiness_status(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    try:
        result = build_live_citation_source_obligation_readiness_status(
            query=args.query,
            repo_root=_ROOT,
        )
    except Exception as exc:
        log.exception("Unexpected live citation/source-obligation readiness status error")
        print(
            f"ERROR: Unexpected live citation/source-obligation readiness status error - {exc}",
            file=sys.stderr,
        )
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"Status written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_live_semantic_coverage_status(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    try:
        result = build_live_semantic_coverage_status(
            query=args.query,
            repo_root=_ROOT,
            smart_provider=args.smart_provider,
            smart_model=args.smart_model,
        )
    except Exception as exc:
        log.exception("Unexpected live semantic coverage status error")
        print(
            f"ERROR: Unexpected live semantic coverage status error - {exc}",
            file=sys.stderr,
        )
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"Status written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_mvp_demo(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    del log
    output_dir = args.mvp_output_dir or DEFAULT_MVP_OUTPUT_DIR
    try:
        result = build_mvp_demo_output(
            query=args.query,
            repo_root=_ROOT,
            output_dir=output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Unexpected MVP demo error - {exc}", file=sys.stderr)
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"MVP demo output written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_mvp_live_dogfood_run(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    del log
    output_dir = args.mvp_output_dir or DEFAULT_MVP_LIVE_OUTPUT_DIR
    try:
        result = build_mvp_live_dogfood_run_output(
            query=args.query,
            repo_root=_ROOT,
            output_dir=output_dir,
            confirm_live_dogfood=args.confirm_live_dogfood,
            confirm_live_dprime_review=args.confirm_live_dprime_review,
            broker_url=args.mvp_live_broker_url,
            env_file_paths=args.mvp_live_env_file,
            smart_provider=args.smart_provider,
            smart_model=args.smart_model,
        )
    except Exception as exc:
        print(f"ERROR: Unexpected MVP live dogfood run error - {exc}", file=sys.stderr)
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"MVP live dogfood run written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_mvp_single_relation_live_dogfood_run(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    del log
    product_entrypoint = bool(args.mvp_current_source_of_record_single_fact_run)
    confirm_single_relation_run = (
        bool(args.confirm_current_source_of_record_single_fact_run)
        if product_entrypoint
        else bool(args.confirm_live_dogfood)
    )
    output_dir = args.mvp_output_dir or DEFAULT_MVP_SINGLE_RELATION_LIVE_OUTPUT_DIR
    fast_model_planning_route = build_strict_accounted_fast_model_planning_route(
        fast_provider=args.fast_provider,
        fast_model=args.fast_model,
        local_url=args.local_url,
    )
    try:
        result = build_generic_single_relation_live_dogfood_run_output(
            query=args.query,
            repo_root=_ROOT,
            output_dir=output_dir,
            confirm_live_dogfood=confirm_single_relation_run,
            confirm_live_dprime_review=args.confirm_live_dprime_review,
            confirm_live_source_challenge_recovery=(args.confirm_live_source_challenge_recovery),
            confirm_current_source_followup_reentry=(args.confirm_current_source_followup_reentry),
            entrypoint_surface=(
                PRODUCT_SINGLE_FACT_ENTRYPOINT_SURFACE if product_entrypoint else DOGFOOD_ENTRYPOINT_SURFACE
            ),
            entrypoint_kind=(PRODUCT_SINGLE_FACT_ENTRYPOINT_KIND if product_entrypoint else DOGFOOD_ENTRYPOINT_KIND),
            diagnostic_dogfood_alias=not product_entrypoint,
            supported_query_class=(
                PRODUCT_SINGLE_FACT_SUPPORTED_QUERY_CLASS if product_entrypoint else DOGFOOD_SUPPORTED_QUERY_CLASS
            ),
            smart_provider=args.smart_provider,
            smart_model=args.smart_model,
            fast_provider=args.fast_provider,
            fast_model=args.fast_model,
            fast_model_local_url=args.local_url,
            fast_model_planner_callable=fast_model_planning_route,
            fast_model_planner_clean_json_response=clean_json_response,
            fast_model_planner_strict_route_ref=fast_model_planning_route.to_ref(),
            require_model_assisted_planning=True,
        )
    except Exception as exc:
        print(
            f"ERROR: Unexpected generic single-relation live dogfood run error - {exc}",
            file=sys.stderr,
        )
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(
            f"Generic single-relation live dogfood run written to {out_path}",
            file=sys.stderr,
        )
    else:
        print(result.output)
    return result.return_code


def _run_mvp_live_dogfood_status(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    del log
    output_dir = args.mvp_output_dir or DEFAULT_MVP_LIVE_OUTPUT_DIR
    try:
        result = build_mvp_live_dogfood_status_output(
            query=args.query,
            repo_root=_ROOT,
            retained_artifact_root=args.mvp_retained_artifact_root,
            output_dir=output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Unexpected MVP live dogfood status error - {exc}", file=sys.stderr)
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"MVP live dogfood status written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_mvp_query_plan_status(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    del log
    output_dir = args.mvp_output_dir or MVP_QUERY_PLANNING_OUTPUT_DIR
    try:
        result = build_generic_query_plan_status_output(
            query=args.query,
            repo_root=_ROOT,
            output_dir=output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Unexpected MVP query plan status error - {exc}", file=sys.stderr)
        return 1
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(result.output, encoding="utf-8")
        print(f"MVP query plan status written to {out_path}", file=sys.stderr)
    else:
        print(result.output)
    return result.return_code


def _run_source_of_record_recovery_provider_decision(
    *,
    args: argparse.Namespace,
    log: logging.Logger,
) -> int:
    del log
    decision_module = importlib.import_module("scripts.source_of_record_recovery_provider_decision_01")
    result = decision_module.run_source_of_record_recovery_provider_decision_comparison(
        repo_root=_ROOT,
        output_root=args.output_root,
        run_id=args.provider_decision_run_id,
        confirm_live_provider_comparison=args.confirm_live_provider_comparison,
        product_model_route_config_initialization=(PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZATION.to_safe_status()),
    )
    selected = result.selected_provider or "none"
    blocker = result.blocker or "none"
    print(f"provider_decision_packet: {result.packet_path}")
    print(f"selected_provider: {selected}")
    print(f"blocker: {blocker}")
    return result.return_code


def main(
    argv: list[str] | None = None,
    *,
    entrypoint: str = "proplex",
) -> int:
    if entrypoint not in {"scryraven", "proplex"}:
        raise ValueError("entrypoint must be scryraven or proplex")
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    args = _parse_args(raw_argv)
    bounded = bool(args.bounded_run_authorization)
    global PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZATION, _PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZED
    if bounded:
        PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZATION = ProductModelRouteConfigInitialization()
        _PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZED = False
    elif not _PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZED:
        PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZATION = initialize_product_model_route_config(
            raw_argv,
            load_dotenv_func=load_dotenv,
        )
        _PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZED = True
    log = _build_logger(args.verbose, persistent=False) if bounded else _build_logger(args.verbose)

    if args.source_of_record_recovery_provider_decision:
        return _run_source_of_record_recovery_provider_decision(args=args, log=log)

    if args.mvp_demo:
        return _run_mvp_demo(args=args, log=log)

    if args.mvp_live_dogfood_run:
        return _run_mvp_live_dogfood_run(args=args, log=log)

    if args.mvp_single_relation_live_dogfood_run or args.mvp_current_source_of_record_single_fact_run:
        return _run_mvp_single_relation_live_dogfood_run(args=args, log=log)

    if args.mvp_live_dogfood_status:
        return _run_mvp_live_dogfood_status(args=args, log=log)

    if args.mvp_query_plan_status:
        return _run_mvp_query_plan_status(args=args, log=log)

    if args.ordinary_live_main_runkernel_coverage_dry_run:
        return _run_ordinary_live_entrypoint_dry_run(args=args, log=log)

    if args.live_acquisition_readability_status_dry_run:
        return _run_live_acquisition_readability_status(args=args, log=log)

    if args.live_source_evidence_admission_status_dry_run:
        return _run_live_source_evidence_admission_status(args=args, log=log)

    if args.live_citation_source_obligation_readiness_status_dry_run:
        return _run_live_citation_source_obligation_readiness_status(
            args=args,
            log=log,
        )

    if args.live_semantic_coverage_status_dry_run:
        return _run_live_semantic_coverage_status(args=args, log=log)

    compiled: CompiledRunCapAuthorization | None = None
    if bounded:
        try:
            if (
                args.exclude_domains
                and not any(
                    item == "--exclude-domains" or item.startswith("--exclude-domains=")
                    for item in raw_argv
                )
            ):
                raise BoundedRunAuthorizationError("exclude_domains_not_explicit")
            compiled = compile_bounded_run_authorization(
                args.bounded_run_authorization,
                query=str(args.query or ""),
                mode=str(args.mode),
                include_domains=_parse_domains(args.include_domains),
                exclude_domains=_parse_domains(args.exclude_domains),
                fast_provider=str(args.fast_provider),
                fast_model=str(args.fast_model),
                smart_provider=str(args.smart_provider),
                smart_model=str(args.smart_model),
                embed_provider=str(args.embed_provider),
                embed_model=str(args.embed_model),
                repo_root=_ROOT,
            )
        except BoundedRunAuthorizationError as exc:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=exc,
                    config=None,
                )
            )
            return 2

    config: RunConfig | None = None
    try:
        config = _build_run_config(args, compiled_authorization=compiled)
    except (RunCapExceeded, BoundedRunAuthorizationError) as exc:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=exc,
                    config=None,
                    compiled_authorization=compiled,
                )
            )
            return 2
        raise
    except Exception:
        if bounded:
            assert compiled is not None
            _print_bounded_entrypoint_setup_failure(
                entrypoint=entrypoint,
                config=None,
                compiled_authorization=compiled,
                failure_code=(
                    BoundedEntrypointSetupFailureCode.RUN_CONFIG_INITIALIZATION
                ),
            )
            return 1
        raise

    # Validate required model-provider keys early so the error message is clean.
    # Bounded posture skips dotenv and inspects only process-environment presence.
    try:
        missing_keys = missing_required_api_keys(
            fast_provider=args.fast_provider,
            smart_provider=args.smart_provider,
            embed_provider=args.embed_provider,
            active_search_providers=None,
        )
        openai_prerequisite_missing = "OPENAI_API_KEY" in missing_keys
    except (RunCapExceeded, BoundedRunAuthorizationError) as exc:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=exc,
                    config=config,
                    compiled_authorization=compiled,
                )
            )
            return 2
        raise
    except Exception:
        if bounded:
            assert compiled is not None
            _print_bounded_entrypoint_setup_failure(
                entrypoint=entrypoint,
                config=config,
                compiled_authorization=compiled,
                failure_code=(
                    BoundedEntrypointSetupFailureCode.PROVIDER_PREREQUISITE_VALIDATION
                ),
            )
            return 1
        raise
    if openai_prerequisite_missing:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=None,
                    config=config,
                    code="bounded_configuration_unavailable",
                    compiled_authorization=compiled,
                )
            )
            return 2
        print("ERROR: OPENAI_API_KEY is required for OpenAI models.", file=sys.stderr)
        return 1

    try:
        deps = _build_run_deps(log)
    except (RunCapExceeded, BoundedRunAuthorizationError) as exc:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=exc,
                    config=config,
                    compiled_authorization=compiled,
                )
            )
            return 2
        raise
    except Exception:
        if bounded:
            assert compiled is not None
            _print_bounded_entrypoint_setup_failure(
                entrypoint=entrypoint,
                config=config,
                compiled_authorization=compiled,
                failure_code=BoundedEntrypointSetupFailureCode.RUN_DEPS_COMPOSITION,
            )
            return 1
        raise

    try:
        status = NullStatusWriter()
        accumulator = CostAccumulator()
    except (RunCapExceeded, BoundedRunAuthorizationError) as exc:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=exc,
                    config=config,
                    compiled_authorization=compiled,
                )
            )
            return 2
        raise
    except Exception:
        if bounded:
            assert compiled is not None
            _print_bounded_entrypoint_setup_failure(
                entrypoint=entrypoint,
                config=config,
                compiled_authorization=compiled,
                failure_code=(
                    BoundedEntrypointSetupFailureCode.RUNTIME_SUPPORT_INITIALIZATION
                ),
            )
            return 1
        raise

    try:
        outcome = run_pipeline(config, deps, status, accumulator)
    except RunCapExceeded as exc:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=exc,
                    config=config,
                    compiled_authorization=compiled,
                )
            )
            return 2
        raise
    except PipelineError as exc:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=None,
                    config=config,
                    compiled_authorization=compiled,
                )
            )
            return 1
        print(f"ERROR: Pipeline failed - {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if bounded:
            _print_bounded_payload(
                _bounded_terminal_payload(
                    entrypoint=entrypoint,
                    exc=(
                        exc
                        if isinstance(
                            exc,
                            (
                                SearchPlannerModelAdapterError,
                                InitialQueryStrategyFailureError,
                                QueryStrategyConvergenceError,
                                SearchPlannerRuntimeError,
                            ),
                        )
                        else None
                    ),
                    config=config,
                    compiled_authorization=compiled,
                )
            )
            return 1
        log.exception("Unexpected pipeline error")
        print(f"ERROR: Unexpected error - {exc}", file=sys.stderr)
        return 1

    if bounded:
        _print_bounded_payload(
            _bounded_success_payload(
                entrypoint=entrypoint,
                config=config,
                outcome=outcome,
                compiled_authorization=compiled,
            )
        )
        return 0

    # Output the report plus allowed-artifact diagnostics built from sanitized
    # in-memory runtime fields. The underlying final answer remains unchanged.
    report_output = append_official_canonical_recovery_diagnostics_section(
        outcome.report,
        outcome.execution_trace,
    )
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(report_output, encoding="utf-8")
        print(f"Report written to {out_path}", file=sys.stderr)
    else:
        print(report_output)

    # Print a brief cost summary to stderr
    snap = outcome.cost_snapshot
    print(
        f"\n[proplex] {outcome.latency_seconds:.1f}s | "
        f"{snap.get('total_calls', 0)} calls | "
        f"${snap.get('total_cost_usd', 0.0):.4f} | "
        f"execution_log.jsonl updated",
        file=sys.stderr,
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())
