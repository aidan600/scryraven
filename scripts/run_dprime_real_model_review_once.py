"""INTEGRATION-STAGING: D-prime real model-review launcher.

Harness label: INTEGRATION-STAGING
Ordinary product path guarded or fed: D-prime model-review status path via
product smart model route/config initialization.
Runtime consumer: DPRIME-REAL-MODEL-REVIEW-RUN-01B one approved product smart
model-review run.
Why ordinary product-path work cannot be done directly: this repair phase is not
licensed to perform the real model attempt; the launcher exposes a safe
credential preflight and keeps real invocation behind an explicit run flag.
Integration deadline: DPRIME-REAL-MODEL-REVIEW-RUN-01B.
Exit condition: convert the launcher test to PRODUCT-PATH-REGRESSION after the
real run consumes it, or retire it if the real-run operation moves elsewhere.
Why this is not a shadow product path: it calls the existing
proplex.live_semantic_coverage_status product status builder and the existing
DPrimeOneShotModelReviewAdapter, with product smart route settings.
Forbidden interpretation: credential preflight is not a model call, live
validation, semantic support, citation readiness, answer readiness, answer text,
or product correctness.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from core.dprime_one_shot_provider_boundary import (
    DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE,
    PROVIDER_MODEL_SELECTION_APPROVAL_REF_PRESENT,
)
from core.dprime_one_shot_provider_boundary import (
    default_closed_surface_flags as default_provider_closed_surface_flags,
)
from core.dprime_product_smart_one_shot_transport import (
    APPROVED_MODEL,
    APPROVED_PROVIDER,
    DPRIME_PRODUCT_SMART_ADAPTER_REF,
    DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF,
    PRODUCT_CONFIG_INITIALIZATION_BOUNDARY,
    build_dprime_product_smart_model_review_adapter,
    product_smart_model_route_ref,
)
from core.product_model_route_config import (
    ProductModelRouteConfigInitialization,
    initialize_product_model_route_config,
)
from proplex.env_aliases import get_env_alias
from proplex.live_semantic_coverage_status import build_live_semantic_coverage_status

ROOT = Path(__file__).resolve().parents[1]
PHASE = "DPRIME-PRODUCT-MODEL-ROUTE-CONFIG-REPAIR-01"
NEXT_PHASE = "DPRIME-REAL-MODEL-REVIEW-RUN-01B"

Initializer = Callable[
    [Sequence[str] | None],
    ProductModelRouteConfigInitialization,
]


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the D-prime single-attempt audited product smart transport."
        )
    )
    parser.add_argument("query", help="User-style query for the retained status path")
    parser.add_argument(
        "--smart-provider",
        default=get_env_alias(
            "SCRYRAVEN_SMART_PROVIDER",
            "PROPLEX_SMART_PROVIDER",
            APPROVED_PROVIDER,
        ),
        help="Product smart provider selected by ordinary config",
    )
    parser.add_argument(
        "--smart-model",
        default=get_env_alias(
            "SCRYRAVEN_SMART_MODEL",
            "PROPLEX_SMART_MODEL",
            APPROVED_MODEL,
        ),
        help="Product smart model selected by ordinary config",
    )
    parser.add_argument(
        "--credential-preflight-only",
        action="store_true",
        help="Print safe credential/config posture booleans and perform no model call",
    )
    parser.add_argument(
        "--no-secret-values",
        action="store_true",
        help="Required for preflight; only booleans/status refs may be printed",
    )
    parser.add_argument(
        "--run-real-model-review",
        action="store_true",
        help="Perform the one licensed D-prime model-review attempt",
    )
    return parser.parse_args(list(argv))


def main(
    argv: Sequence[str] | None = None,
    *,
    initialize_config: Initializer = initialize_product_model_route_config,
    openai_client_factory: Callable[[], Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    raw = sys.argv[1:] if argv is None else list(argv)
    init = initialize_config(raw)
    args = _parse_args(raw)
    env = os.environ if environ is None else environ
    if args.credential_preflight_only:
        if not args.no_secret_values:
            print(
                "ERROR: --credential-preflight-only requires --no-secret-values",
                file=sys.stderr,
            )
            return 2
        payload = build_credential_preflight_payload(
            args=args,
            init=init,
            environ=env,
        )
        print(format_credential_preflight_status(payload))
        return 0
    if not args.run_real_model_review:
        print(
            "ERROR: pass --credential-preflight-only --no-secret-values for safe "
            "preflight, or --run-real-model-review only in the licensed phase",
            file=sys.stderr,
        )
        return 2

    boundary = build_dprime_real_run_provider_boundary()
    adapter = build_dprime_product_smart_model_review_adapter(
        provider_boundary_ref=boundary["boundary_id"],
        openai_client_factory=openai_client_factory,
        smart_provider=args.smart_provider,
        smart_model=args.smart_model,
    )
    result = build_live_semantic_coverage_status(
        query=args.query,
        repo_root=ROOT,
        smart_provider=args.smart_provider,
        smart_model=args.smart_model,
        dprime_one_shot_provider_boundary=boundary,
        dprime_one_shot_model_review_adapter=adapter,
        dprime_model_review_license=build_dprime_real_run_license(),
    )
    print(result.output)
    return result.return_code


def build_credential_preflight_payload(
    *,
    args: argparse.Namespace,
    init: ProductModelRouteConfigInitialization,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    route_ref = product_smart_model_route_ref(
        smart_provider=args.smart_provider,
        smart_model=args.smart_model,
    )
    return {
        "phase": PHASE,
        "next_phase": NEXT_PHASE,
        "product_config_boundary": PRODUCT_CONFIG_INITIALIZATION_BOUNDARY,
        "dotenv_helper_invoked": init.dotenv_helper_invoked,
        "dotenv_skipped_for_status_dry_run": init.dotenv_skipped_for_status_dry_run,
        "OPENAI_API_KEY_present": bool(environ.get("OPENAI_API_KEY")),
        "product_model_role": route_ref["product_model_role"],
        "product_route_kind": route_ref["product_route_kind"],
        "configured_smart_provider": route_ref["configured_smart_provider"],
        "configured_smart_model": route_ref["configured_smart_model"],
        "provider_model_approval_ref": route_ref["provider_model_approval_ref"],
        "execution_policy": route_ref["execution_policy"],
        "max_provider_attempts": route_ref["max_provider_attempts"],
        "retry_policy": route_ref["retry_policy"],
        "fallback_policy": route_ref["fallback_policy"],
        "provider_switching_allowed": route_ref["provider_switching_allowed"],
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "provider_payload_retained": False,
        "real_model_call_performed": False,
    }


def format_credential_preflight_status(payload: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            "D-prime real model-review credential preflight",
            f"phase: {payload.get('phase')}",
            f"next phase: {payload.get('next_phase')}",
            f"product config boundary: {payload.get('product_config_boundary')}",
            f"dotenv helper invoked: {_bool_text(payload.get('dotenv_helper_invoked'))}",
            (
                "dotenv skipped for status dry-run: "
                f"{_bool_text(payload.get('dotenv_skipped_for_status_dry_run'))}"
            ),
            (
                "OPENAI_API_KEY present in current process: "
                f"{_bool_text(payload.get('OPENAI_API_KEY_present'))}"
            ),
            f"product_model_role: {payload.get('product_model_role')}",
            f"product_route_kind: {payload.get('product_route_kind')}",
            (
                "product smart route provider/model: "
                f"{payload.get('configured_smart_provider')} / "
                f"{payload.get('configured_smart_model')}"
            ),
            (
                "provider/model approval ref: "
                f"{payload.get('provider_model_approval_ref')}"
            ),
            f"execution policy: {payload.get('execution_policy')}",
            f"max provider attempts: {payload.get('max_provider_attempts')}",
            f"retry policy: {payload.get('retry_policy')}",
            f"fallback policy: {payload.get('fallback_policy')}",
            (
                "provider switching allowed: "
                f"{_bool_text(payload.get('provider_switching_allowed'))}"
            ),
            f"raw prompt retained: {_bool_text(payload.get('raw_prompt_retained'))}",
            (
                "raw model response retained: "
                f"{_bool_text(payload.get('raw_model_response_retained'))}"
            ),
            (
                "provider payload retained: "
                f"{_bool_text(payload.get('provider_payload_retained'))}"
            ),
            (
                "real model call performed: "
                f"{_bool_text(payload.get('real_model_call_performed'))}"
            ),
        )
    )


def build_dprime_real_run_provider_boundary() -> dict[str, Any]:
    return {
        "boundary_id": "dprime-one-shot-provider-boundary:product-smart-route:v1",
        "phase": DPRIME_ONE_SHOT_PROVIDER_BOUNDARY_PHASE,
        "enabled": True,
        "default_disabled": False,
        "test_only": False,
        "provider_model_selection_status": (
            PROVIDER_MODEL_SELECTION_APPROVAL_REF_PRESENT
        ),
        "provider_model_approval_ref": DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF,
        "max_provider_attempts": 1,
        "retry_policy": "forbidden",
        "fallback_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "raw_prompt_retention": False,
        "raw_model_response_retention": False,
        "provider_payload_retention": False,
        "real_call_authorized": True,
        "call_count": 0,
        "provider_switching_allowed": False,
        "one_shot_adapter_proven": True,
        "one_shot_adapter_ref": DPRIME_PRODUCT_SMART_ADAPTER_REF,
        "closed_surface_flags": default_provider_closed_surface_flags(),
    }


def build_dprime_real_run_license() -> dict[str, Any]:
    return {
        "license_id": DPRIME_PRODUCT_SMART_PROVIDER_MODEL_APPROVAL_REF,
        "enabled": True,
        "test_only": False,
        "callable_kind": "real_one_shot",
        "max_model_review_calls": 1,
        "retry_policy": "forbidden",
        "timeout_policy": "fail_closed",
        "one_shot_adapter_ref": DPRIME_PRODUCT_SMART_ADAPTER_REF,
    }


def _bool_text(value: Any) -> str:
    return "true" if value is True else "false"


if __name__ == "__main__":
    raise SystemExit(main())
