from __future__ import annotations

import argparse
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ag_live_bound_01_support import (  # noqa: E402
    DEFAULT_OUTPUT,
    LIVE_PACKET_CAP_OVERFLOW,
    LIVE_PACKET_PIPELINE_FAILURE,
    LIVE_PACKET_PRECHECK_FAILURE,
    LIVE_PACKET_UNEXPECTED_FAILURE,
    AgLiveBoundPreflightError,
    build_dry_run_packet,
    build_live_failure_packet,
    build_live_success_packet,
    build_preflight_context,
    parse_domains,
    resolve_output_path,
    validate_caps_requested,
    write_packet,
)

LIVE_SPEND_WARNING = (
    "AG-LIVE-BOUND-01 may spend live provider/model/search/fetch calls when enabled."
)
OUTPUT_DIR = ROOT / "output"


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        caps = validate_caps_requested(_caps_from_args(args))
        output_path = resolve_output_path(ROOT, args.output)
        context = build_preflight_context(
            root=ROOT,
            query=args.query,
            mode=args.mode,
            include_domains=parse_domains(args.include_domains),
            output_path=output_path,
            caps=caps,
            run_id=args.run_id,
            confirm_live_product_run=args.confirm_live_product_run,
            approved_backup_query=args.approved_backup_query,
        )
    except AgLiveBoundPreflightError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.confirm_live_product_run:
        return _run_confirmed_live(context)

    packet = build_dry_run_packet(context)
    write_packet(context.output_path, packet)
    print(f"wrote sanitized AG-LIVE-BOUND dry-run packet to {context.output_path}")
    return 0


def _run_confirmed_live(context) -> int:
    print(LIVE_SPEND_WARNING, file=sys.stderr)
    cap_policy = context.caps.to_run_cap_policy()
    run_pipeline_call_count = 0
    try:
        _load_live_environment()
        _validate_live_model_keys()
        config = _build_live_run_config(context, cap_policy=cap_policy)
        deps = _build_live_run_deps()
        status, accumulator = _live_runtime_helpers()
        run_pipeline_call_count = 1
        with _suppress_ordinary_retention_for_bounded_runner():
            outcome = _call_run_pipeline_once(config, deps, status, accumulator)
    except AgLiveBoundPreflightError as exc:
        packet = build_live_failure_packet(
            context,
            cap_policy=cap_policy,
            classification=LIVE_PACKET_PRECHECK_FAILURE,
            failure_reason=str(exc),
            run_pipeline_call_count=run_pipeline_call_count,
        )
        write_packet(context.output_path, packet)
        print(f"refusing live product execution: {exc}", file=sys.stderr)
        return 2
    except _run_cap_exceeded_type() as exc:
        packet = build_live_failure_packet(
            context,
            cap_policy=cap_policy,
            classification=LIVE_PACKET_CAP_OVERFLOW,
            failure_reason=str(exc),
            run_pipeline_call_count=run_pipeline_call_count,
        )
        write_packet(context.output_path, packet)
        print(f"bounded live product run exceeded caps: {exc}", file=sys.stderr)
        return 2
    except _pipeline_error_type() as exc:
        packet = build_live_failure_packet(
            context,
            cap_policy=cap_policy,
            classification=LIVE_PACKET_PIPELINE_FAILURE,
            failure_reason=str(exc),
            run_pipeline_call_count=run_pipeline_call_count,
        )
        write_packet(context.output_path, packet)
        print(f"bounded live product run failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        packet = build_live_failure_packet(
            context,
            cap_policy=cap_policy,
            classification=LIVE_PACKET_UNEXPECTED_FAILURE,
            failure_reason=type(exc).__name__,
            run_pipeline_call_count=run_pipeline_call_count,
        )
        write_packet(context.output_path, packet)
        print(
            "bounded live product run failed unexpectedly; sanitized packet written",
            file=sys.stderr,
        )
        return 2

    packet = build_live_success_packet(
        context,
        outcome=outcome,
        cap_policy=cap_policy,
    )
    write_packet(context.output_path, packet)
    print(f"wrote sanitized AG-LIVE-BOUND live packet to {context.output_path}")
    return 0


def _load_live_environment() -> None:
    from dotenv import load_dotenv

    load_dotenv()


def _validate_live_model_keys() -> None:
    from core.provider_validation import missing_required_api_keys

    model_config = _live_model_config()
    missing = missing_required_api_keys(
        fast_provider=model_config["fast_provider"],
        smart_provider=model_config["smart_provider"],
        embed_provider=model_config["embed_provider"],
        active_search_providers=None,
    )
    if missing:
        raise AgLiveBoundPreflightError(
            "missing required live environment variable(s): " + ", ".join(missing)
        )


def _live_model_config() -> dict[str, str]:
    from proplex.env_aliases import get_env_alias

    return {
        "fast_provider": get_env_alias(
            "SCRYRAVEN_FAST_PROVIDER",
            "PROPLEX_FAST_PROVIDER",
            "OpenAI",
        ),
        "fast_model": get_env_alias(
            "SCRYRAVEN_FAST_MODEL",
            "PROPLEX_FAST_MODEL",
            "gpt-5.4-mini",
        ),
        "smart_provider": get_env_alias(
            "SCRYRAVEN_SMART_PROVIDER",
            "PROPLEX_SMART_PROVIDER",
            "OpenAI",
        ),
        "smart_model": get_env_alias(
            "SCRYRAVEN_SMART_MODEL",
            "PROPLEX_SMART_MODEL",
            "gpt-5.4",
        ),
        "embed_provider": get_env_alias(
            "SCRYRAVEN_EMBED_PROVIDER",
            "PROPLEX_EMBED_PROVIDER",
            "OpenAI",
        ),
        "embed_model": get_env_alias(
            "SCRYRAVEN_EMBED_MODEL",
            "PROPLEX_EMBED_MODEL",
            "text-embedding-3-small",
        ),
        "local_url": get_env_alias(
            "SCRYRAVEN_LOCAL_URL",
            "PROPLEX_LOCAL_URL",
            "http://localhost:1234/v1",
        ),
    }


def _build_live_run_config(context: Any, *, cap_policy: Any) -> Any:
    from core.run_config import RunConfig

    model_config = _live_model_config()
    return RunConfig(
        query=context.query,
        mode=context.mode,
        current_date=datetime.now().strftime("%B %d, %Y"),
        run_id=context.run_id,
        include_domains=list(context.include_domains),
        fast_provider=model_config["fast_provider"],
        fast_model=model_config["fast_model"],
        smart_provider=model_config["smart_provider"],
        smart_model=model_config["smart_model"],
        embed_provider=model_config["embed_provider"],
        embed_model=model_config["embed_model"],
        local_url=model_config["local_url"],
        or_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        use_reasoning=True,
        run_authority_search_judgment_smart_model=False,
        cap_policy=cap_policy,
    )


def _build_live_run_deps() -> Any:
    from core.llm import ask_model, compute_similarities, embed_texts
    from core.pipeline import (
        QUANT_REPORT_TYPES,
        fetch_linkup_precision_block,
        process_search_queries,
        run_economist_step,
        run_scout,
        should_skip_quant_scout,
    )
    from core.prompts import DEFAULT_SYSTEM
    from core.retrieval import (
        ACADEMIC_DOMAINS,
        NEWS_PREFERRED_DOMAINS,
        anchor_query_to_topic,
        filter_top_evidence,
        is_plausible_domain,
    )
    from core.run_config import RunDeps
    from core.text_utils import clean_json_response

    OUTPUT_DIR.mkdir(exist_ok=True)
    log = _build_live_logger()
    return RunDeps(
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
        execution_log_path=OUTPUT_DIR / "ag_live_bound_01_execution_log.jsonl",
        feedback_log_path=OUTPUT_DIR / "ag_live_bound_01_feedback.jsonl",
        kb_triggers_path=OUTPUT_DIR / "ag_live_bound_01_kb_triggers.jsonl",
        policy_state_path=OUTPUT_DIR / "ag_live_bound_01_policy_state.json",
        policy_journal_path=OUTPUT_DIR / "ag_live_bound_01_policy_journal.jsonl",
    )


def _build_live_logger() -> logging.Logger:
    log = logging.getLogger("ag_live_bound_01.product_runner")
    log.setLevel(logging.WARNING)
    if not log.handlers:
        log.addHandler(logging.StreamHandler(sys.stderr))
    return log


def _live_runtime_helpers() -> tuple[Any, Any]:
    from core.cost_accounting import CostAccumulator
    from core.protocols import NullStatusWriter

    return NullStatusWriter(), CostAccumulator()


def _call_run_pipeline_once(
    config: Any,
    deps: Any,
    status: Any,
    accumulator: Any,
) -> Any:
    import core.pipeline_orchestrator as orchestrator

    return orchestrator.run_pipeline(config, deps, status, accumulator)


@contextmanager
def _suppress_ordinary_retention_for_bounded_runner() -> Iterator[None]:
    import core.persistence_side_effects as persistence
    import core.pipeline_orchestrator as orchestrator

    originals = {
        "orchestrator_log_run_started": orchestrator.log_run_started,
        "orchestrator_log_run_failed": orchestrator.log_run_failed,
        "orchestrator_execute_persistence_side_effects": (
            orchestrator.execute_persistence_side_effects
        ),
        "orchestrator_db_enabled": orchestrator.DB_ENABLED,
        "persistence_append_jsonl": persistence.append_jsonl,
        "persistence_log_run_completed": persistence.log_run_completed,
    }

    def noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    def suppressed_persistence_side_effects(*_args: Any, **kwargs: Any) -> Any:
        return persistence.PersistenceSideEffectResult(
            execution_log_entry=dict(kwargs.get("execution_log_entry") or {}),
            kb_instrumentation=None,
            kb_warning=None,
            sqlite_row_written=False,
        )

    orchestrator.log_run_started = noop
    orchestrator.log_run_failed = noop
    orchestrator.execute_persistence_side_effects = suppressed_persistence_side_effects
    orchestrator.DB_ENABLED = False
    persistence.append_jsonl = noop
    persistence.log_run_completed = noop
    try:
        yield
    finally:
        orchestrator.log_run_started = originals["orchestrator_log_run_started"]
        orchestrator.log_run_failed = originals["orchestrator_log_run_failed"]
        orchestrator.execute_persistence_side_effects = originals[
            "orchestrator_execute_persistence_side_effects"
        ]
        orchestrator.DB_ENABLED = originals["orchestrator_db_enabled"]
        persistence.append_jsonl = originals["persistence_append_jsonl"]
        persistence.log_run_completed = originals["persistence_log_run_completed"]


def _run_cap_exceeded_type() -> type[Exception]:
    from core.cap_enforcement import RunCapExceeded

    return RunCapExceeded


def _pipeline_error_type() -> type[Exception]:
    from core.pipeline_orchestrator import PipelineError

    return PipelineError


def _caps_from_args(args: argparse.Namespace) -> dict[str, int]:
    return {
        "max_scryraven_runs": args.max_scryraven_runs,
        "max_search_dispatches": args.max_search_dispatches,
        "max_fetch_read_operations": args.max_fetch_read_operations,
        "max_author_model_calls": args.max_author_model_calls,
        "max_smart_search_judgment_model_calls": (
            args.max_smart_search_judgment_model_calls
        ),
        "max_independent_manual_source_checks": (
            args.max_independent_manual_source_checks
        ),
        "max_retries": args.max_retries,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run-first bounded ordinary product runner for AG-LIVE-BOUND-01. "
            "Confirmed live execution runs ordinary run_pipeline() once with "
            "RunConfig.cap_policy."
        ),
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Exact AG-LIVE-BOUND-01 query candidate.",
    )
    parser.add_argument(
        "--mode",
        default="Balanced",
        choices=["Balanced"],
        help="Pipeline mode (AG-LIVE-BOUND-01 requires Balanced).",
    )
    parser.add_argument(
        "--include-domains",
        required=True,
        metavar="DOMAINS",
        help="Comma-separated domain allowlist (must include docs.python.org).",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Sanitized packet output path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument("--run-id", help="Optional run id (UUID generated if omitted).")
    parser.add_argument(
        "--max-scryraven-runs",
        type=int,
        default=1,
        help="Planned cap: ScryRaven runs (must remain 1).",
    )
    parser.add_argument(
        "--max-search-dispatches",
        type=int,
        default=2,
        help="Planned cap: search dispatches (must remain 2).",
    )
    parser.add_argument(
        "--max-fetch-read-operations",
        type=int,
        default=3,
        help="Planned cap: fetch/read operations (must remain 3).",
    )
    parser.add_argument(
        "--max-author-model-calls",
        type=int,
        default=1,
        help="Planned cap: Author model calls (must remain 1).",
    )
    parser.add_argument(
        "--max-smart-search-judgment-model-calls",
        type=int,
        default=0,
        help="Planned cap: smart SearchJudgment model calls (must remain 0).",
    )
    parser.add_argument(
        "--max-independent-manual-source-checks",
        type=int,
        default=1,
        help="Planned cap: independent manual source checks (must remain 1).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=0,
        help="Planned cap: retries (must remain 0).",
    )
    parser.add_argument(
        "--approved-backup-query",
        action="store_true",
        help="Allow the AG-LIVE-PLAN-01 backup query candidate.",
    )
    parser.add_argument(
        "--confirm-live-product-run",
        action="store_true",
        help=(
            "Request one cap-enforced live ordinary product execution and write a "
            "sanitized packet."
        ),
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
