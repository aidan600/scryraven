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
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Ensure the project root is on sys.path when run as "python -m proplex" from
# outside the repo root (e.g. installed as a script).
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.product_model_route_config import (  # noqa: E402
    CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
    LIVE_ACQUISITION_READABILITY_STATUS_FLAG,
    LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG,
    LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
    LIVE_SOURCE_EVIDENCE_ADMISSION_STATUS_FLAG,
    MVP_DEMO_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
    MVP_LIVE_DOGFOOD_STATUS_FLAG,
    MVP_QUERY_PLAN_STATUS_FLAG,
    MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
    ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG,
    initialize_product_model_route_config,
)

PRODUCT_MODEL_ROUTE_CONFIG_INITIALIZATION = initialize_product_model_route_config(
    sys.argv[1:],
    load_dotenv_func=load_dotenv,
)

import core.pipeline_orchestrator as pipeline_orchestrator  # noqa: E402
from core.cost_accounting import CostAccumulator  # noqa: E402
from core.generic_query_to_relation_planning import (  # noqa: E402
    MVP_QUERY_PLANNING_OUTPUT_DIR,
    build_generic_query_plan_status_output,
)
from core.llm import ask_model, compute_similarities, embed_texts  # noqa: E402
from core.official_canonical_recovery_visibility_export import (  # noqa: E402
    append_official_canonical_recovery_diagnostics_section,
)
from core.pipeline import (  # noqa: E402
    QUANT_REPORT_TYPES,
    fetch_linkup_precision_block,
    process_search_queries,
    run_economist_step,
    run_scout,
    should_skip_quant_scout,
)
from core.pipeline_orchestrator import PipelineError, run_pipeline  # noqa: E402
from core.prompts import DEFAULT_SYSTEM  # noqa: E402
from core.protocols import NullStatusWriter  # noqa: E402
from core.provider_validation import missing_required_api_keys  # noqa: E402
from core.retrieval import (  # noqa: E402
    ACADEMIC_DOMAINS,
    NEWS_PREFERRED_DOMAINS,
    anchor_query_to_topic,
    filter_top_evidence,
    is_plausible_domain,
)
from core.run_config import RunConfig, RunDeps  # noqa: E402
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
    DEFAULT_PRIVATE_BROKER_PATH,
    build_mvp_live_dogfood_run_output,
)
from proplex.mvp_single_relation_live_dogfood_run import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as DEFAULT_MVP_SINGLE_RELATION_LIVE_OUTPUT_DIR,
)
from proplex.mvp_single_relation_live_dogfood_run import (
    build_generic_single_relation_live_dogfood_run_output,
)
from proplex.ordinary_live_entrypoint_dry_run import (  # noqa: E402
    OrdinaryLiveEntrypointDryRunDeps,
    build_ordinary_live_entrypoint_dry_run_config,
    format_ordinary_live_entrypoint_dry_run_status,
)

OUTPUT_DIR = _ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _build_logger(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.WARNING
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    try:
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
            "Run the ScryRaven research pipeline headlessly. "
            "Legacy entrypoint python -m proplex remains supported."
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
            "private broker boundary and retained-artifact status consumer."
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
        CONFIRM_LIVE_DOGFOOD_FLAG,
        action="store_true",
        dest="confirm_live_dogfood",
        help="Confirm the single live MVP dogfood attempt.",
    )
    p.add_argument(
        CONFIRM_LIVE_DPRIME_REVIEW_FLAG,
        action="store_true",
        dest="confirm_live_dprime_review",
        help="Confirm one D-prime product-route model-review attempt for live dogfood.",
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
        "--mvp-live-private-broker-path",
        default=str(DEFAULT_PRIVATE_BROKER_PATH),
        metavar="PATH",
        help="Private broker helper path for --mvp-live-dogfood-run.",
    )
    p.add_argument(
        "--mvp-live-env-file",
        action="append",
        default=None,
        metavar="PATH",
        help=(
            "Env file path passed to the private broker helper for "
            "--mvp-live-dogfood-run. May be provided more than once."
        ),
    )
    p.add_argument(
        "--mvp-retained-artifact-root",
        default=None,
        metavar="DIR",
        help=(
            "For --mvp-live-dogfood-status, consume retained status artifacts "
            "from DIR instead of the repository root."
        ),
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print DEBUG log to stderr",
    )
    args = p.parse_args(argv)
    if args.query and args.query_option and args.query != args.query_option:
        p.error("query positional argument and --query must match when both are provided")
    if args.query_option:
        args.query = args.query_option
    if not args.query and (
        args.mvp_demo
        or args.mvp_live_dogfood_run
        or args.mvp_live_dogfood_status
    ):
        args.query = DEFAULT_MVP_QUERY
    if not args.query:
        p.error("the following arguments are required: query")
    return args


def _parse_domains(raw: str) -> list[str]:
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


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
        log.exception(
            "Unexpected live citation/source-obligation readiness status error"
        )
        print(
            "ERROR: Unexpected live citation/source-obligation readiness "
            f"status error - {exc}",
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
            private_broker_path=args.mvp_live_private_broker_path,
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
    output_dir = args.mvp_output_dir or DEFAULT_MVP_SINGLE_RELATION_LIVE_OUTPUT_DIR
    try:
        result = build_generic_single_relation_live_dogfood_run_output(
            query=args.query,
            repo_root=_ROOT,
            output_dir=output_dir,
            confirm_live_dogfood=args.confirm_live_dogfood,
            confirm_live_dprime_review=args.confirm_live_dprime_review,
            smart_provider=args.smart_provider,
            smart_model=args.smart_model,
        )
    except Exception as exc:
        print(
            "ERROR: Unexpected generic single-relation live dogfood run error "
            f"- {exc}",
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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else list(argv))
    log = _build_logger(args.verbose)

    if args.mvp_demo:
        return _run_mvp_demo(args=args, log=log)

    if args.mvp_live_dogfood_run:
        return _run_mvp_live_dogfood_run(args=args, log=log)

    if args.mvp_single_relation_live_dogfood_run:
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

    # Validate required model-provider keys early so the error message is clean.
    missing_keys = missing_required_api_keys(
        fast_provider=args.fast_provider,
        smart_provider=args.smart_provider,
        embed_provider=args.embed_provider,
        active_search_providers=None,
    )
    if "OPENAI_API_KEY" in missing_keys:
        print("ERROR: OPENAI_API_KEY is required for OpenAI models.", file=sys.stderr)
        return 1

    current_date = datetime.now().strftime("%B %d, %Y")
    or_api_key = os.getenv("OPENROUTER_API_KEY", "")

    config = RunConfig(
        query=args.query,
        mode=args.mode,
        current_date=current_date,
        focus_academic=args.academic,
        force_intent_news=args.news,
        include_domains=_parse_domains(args.include_domains),
        exclude_domains=_parse_domains(args.exclude_domains),
        fast_provider=args.fast_provider,
        fast_model=args.fast_model,
        smart_provider=args.smart_provider,
        smart_model=args.smart_model,
        embed_provider=args.embed_provider,
        embed_model=args.embed_model,
        local_url=args.local_url,
        or_api_key=or_api_key,
        use_reasoning=not args.no_reasoning,
    )

    deps = RunDeps(
        ask_model=ask_model,
        embed_texts=embed_texts,
        compute_similarities=compute_similarities,
        process_search_queries=process_search_queries,
        filter_top_evidence=filter_top_evidence,
        is_plausible_domain=is_plausible_domain,
        anchor_query_to_topic=anchor_query_to_topic,
        fetch_linkup_precision_block=fetch_linkup_precision_block,
        run_economist_step=run_economist_step,
        run_scout=run_scout,
        should_skip_quant_scout=should_skip_quant_scout,
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

    status = NullStatusWriter()
    accumulator = CostAccumulator()

    try:
        outcome = run_pipeline(config, deps, status, accumulator)
    except PipelineError as exc:
        print(f"ERROR: Pipeline failed — {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        log.exception("Unexpected pipeline error")
        print(f"ERROR: Unexpected error — {exc}", file=sys.stderr)
        return 1

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
