"""Product model-route config and credential initialization boundary.

This module owns the shared environment initialization posture for product
model-route consumers. It loads dotenv through the same boundary ordinary CLI
model execution uses, while preserving status dry-run skips that must not
activate live credential posture.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG = (
    "--ordinary-live-main-runkernel-coverage-dry-run"
)
LIVE_ACQUISITION_READABILITY_STATUS_FLAG = (
    "--live-acquisition-readability-status-dry-run"
)
LIVE_SOURCE_EVIDENCE_ADMISSION_STATUS_FLAG = (
    "--live-source-evidence-admission-status-dry-run"
)
LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG = (
    "--live-citation-source-obligation-readiness-status-dry-run"
)
LIVE_SEMANTIC_COVERAGE_STATUS_FLAG = "--live-semantic-coverage-status-dry-run"
MVP_DEMO_FLAG = "--mvp-demo"
MVP_LIVE_DOGFOOD_RUN_FLAG = "--mvp-live-dogfood-run"
MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG = (
    "--mvp-single-relation-live-dogfood-run"
)
MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG = (
    "--mvp-current-source-of-record-single-fact-run"
)
MVP_LIVE_DOGFOOD_STATUS_FLAG = "--mvp-live-dogfood-status"
MVP_QUERY_PLAN_STATUS_FLAG = "--mvp-query-plan-status"
CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG = (
    "--confirm-current-source-of-record-single-fact-run"
)
CONFIRM_LIVE_DPRIME_REVIEW_FLAG = "--confirm-live-dprime-review"

PRODUCT_STATUS_DRY_RUN_FLAGS = (
    ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG,
    LIVE_ACQUISITION_READABILITY_STATUS_FLAG,
    LIVE_SOURCE_EVIDENCE_ADMISSION_STATUS_FLAG,
    LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG,
    LIVE_SEMANTIC_COVERAGE_STATUS_FLAG,
    MVP_DEMO_FLAG,
    MVP_LIVE_DOGFOOD_RUN_FLAG,
    MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG,
    MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG,
    MVP_LIVE_DOGFOOD_STATUS_FLAG,
    MVP_QUERY_PLAN_STATUS_FLAG,
)


@dataclass(frozen=True, slots=True)
class ProductModelRouteConfigInitialization:
    """Secret-free product config initialization status."""

    boundary: str = "core.product_model_route_config.initialize_product_model_route_config"
    dotenv_helper_invoked: bool = False
    dotenv_skipped_for_status_dry_run: bool = False
    dotenv_result: bool | None = None
    openai_api_key_present: bool = False

    def to_safe_status(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "dotenv_helper_invoked": self.dotenv_helper_invoked,
            "dotenv_skipped_for_status_dry_run": (
                self.dotenv_skipped_for_status_dry_run
            ),
            "dotenv_result": self.dotenv_result,
            "OPENAI_API_KEY_present": self.openai_api_key_present,
        }


def argv_requests_product_status_dry_run(argv: Sequence[str] | None = None) -> bool:
    """Return true when argv selects a no-live status dry-run entrypoint."""

    raw = sys.argv[1:] if argv is None else list(argv)
    if CONFIRM_LIVE_DPRIME_REVIEW_FLAG in raw and (
        MVP_LIVE_DOGFOOD_RUN_FLAG in raw
        or MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG in raw
        or MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG in raw
    ):
        return False
    return any(flag in raw for flag in PRODUCT_STATUS_DRY_RUN_FLAGS)


def initialize_product_model_route_config(
    argv: Sequence[str] | None = None,
    *,
    load_dotenv_func: Callable[[], Any] | None = None,
    environ: Mapping[str, str] | None = None,
    skip_for_status_dry_run: bool = True,
) -> ProductModelRouteConfigInitialization:
    """Initialize product model-route config without exposing credential values."""

    skipped = skip_for_status_dry_run and argv_requests_product_status_dry_run(argv)
    dotenv_result: bool | None = None
    invoked = False
    if not skipped:
        invoked = True
        if load_dotenv_func is None:
            from dotenv import load_dotenv

            dotenv_result = bool(load_dotenv(encoding="utf-8-sig"))
        else:
            dotenv_result = bool(load_dotenv_func())
    env = os.environ if environ is None else environ
    return ProductModelRouteConfigInitialization(
        dotenv_helper_invoked=invoked,
        dotenv_skipped_for_status_dry_run=skipped,
        dotenv_result=dotenv_result,
        openai_api_key_present=bool(env.get("OPENAI_API_KEY")),
    )


__all__ = [
    "CONFIRM_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG",
    "CONFIRM_LIVE_DPRIME_REVIEW_FLAG",
    "LIVE_ACQUISITION_READABILITY_STATUS_FLAG",
    "LIVE_CITATION_SOURCE_OBLIGATION_READINESS_STATUS_FLAG",
    "LIVE_SEMANTIC_COVERAGE_STATUS_FLAG",
    "LIVE_SOURCE_EVIDENCE_ADMISSION_STATUS_FLAG",
    "MVP_DEMO_FLAG",
    "MVP_CURRENT_SOURCE_OF_RECORD_SINGLE_FACT_RUN_FLAG",
    "MVP_LIVE_DOGFOOD_RUN_FLAG",
    "MVP_SINGLE_RELATION_LIVE_DOGFOOD_RUN_FLAG",
    "MVP_LIVE_DOGFOOD_STATUS_FLAG",
    "MVP_QUERY_PLAN_STATUS_FLAG",
    "ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG",
    "PRODUCT_STATUS_DRY_RUN_FLAGS",
    "ProductModelRouteConfigInitialization",
    "argv_requests_product_status_dry_run",
    "initialize_product_model_route_config",
]
