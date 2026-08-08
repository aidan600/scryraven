"""RunKernel-authorized router execution adapter.

This adapter contains the existing router model call shape and prompt assembly
behind an AuthorizedAction. It returns the normalized router/query-preparation
state for runtime consumers and a compact Observation for RunKernel reduction.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from core.entity_extraction import fallback_entities_from_query
from core.prompts import ROUTER_RETRY_USER_APPEND
from core.router_query_preparation_contract import (
    RouterQueryPreparationState,
    build_router_query_preparation_state,
)
from core.run_kernel import (
    ROUTE_REQUEST_STAGE,
    ActionType,
    AuthorizedAction,
    Observation,
    ObservationType,
    RunStageStatus,
    validate_authorized_action,
)


@dataclass(frozen=True, slots=True)
class RouteRequestRuntimeResult:
    """Router runtime result plus the kernel observation to reduce."""

    router_query_preparation_contract: RouterQueryPreparationState
    observation: Observation


def route_projection(contract: RouterQueryPreparationState) -> dict[str, Any]:
    """Return compact route facts without raw prompts or model payloads."""

    return {
        "intent": contract.intent,
        "report_type": contract.report_type,
        "image_mode": contract.image_mode,
        "core_topic": contract.core_topic,
        "is_academic": bool(contract.is_academic),
        "query_type": contract.query_type,
        "primary_entity": contract.primary_entity,
        "entity_count": len(contract.entities_list),
        "router_entity_retry_used": contract.router_entity_retry_used,
        "router_original_report_type": contract.router_original_report_type,
        "router_original_query_type": contract.router_original_query_type,
        "router_query_preparation_ref": contract.to_trace_fragment().get(
            "router_query_preparation_contract",
            {},
        ),
    }


def execute_route_request_action(
    action: AuthorizedAction,
    *,
    query: str,
    current_date: str,
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    default_system: Mapping[str, str],
    fast_provider: str,
    fast_model: str,
    local_url: str | None,
    api_key: str | None,
    use_reasoning: bool,
    measure_context_stage: Callable[..., Any],
    allow_model_retry: bool = True,
    effort: str = "medium",
) -> RouteRequestRuntimeResult:
    """Execute the existing router behavior after RunKernel authorization."""

    validate_authorized_action(
        action,
        action_type=ActionType.ROUTE_REQUEST,
        stage=ROUTE_REQUEST_STAGE,
        expected_observation_type=ObservationType.ROUTE_RESULT,
    )
    router_prompt = f"Today is {current_date}.\nUser Topic: {query}"
    measure_context_stage(
        "router",
        prompt=router_prompt,
        system_prompt=default_system["router"],
    )

    router_text = ask_model(
        router_prompt,
        default_system["router"],
        provider=fast_provider,
        model=fast_model,
        effort=effort,
        base_url=local_url,
        api_key=api_key,
        require_json=True,
        use_reasoning=use_reasoning,
    )
    router_text = clean_json_response(router_text)

    router_query_preparation_contract = build_router_query_preparation_state(
        query=query,
        router_text=router_text,
        fallback_entities=fallback_entities_from_query(query),
    )

    if not router_query_preparation_contract.entities and allow_model_retry:
        router_retry_prompt = f"Today is {current_date}.\nUser Topic: {query}\n\n{ROUTER_RETRY_USER_APPEND}"
        measure_context_stage(
            "router_retry",
            prompt=router_retry_prompt,
            system_prompt=default_system["router"],
        )
        retry_router_text = ask_model(
            router_retry_prompt,
            default_system["router"],
            provider=fast_provider,
            model=fast_model,
            effort=effort,
            base_url=local_url,
            api_key=api_key,
            require_json=True,
            use_reasoning=use_reasoning,
        )
        retry_router_text = clean_json_response(retry_router_text)
        router_query_preparation_contract = build_router_query_preparation_state(
            query=query,
            router_text=router_text,
            fallback_entities=fallback_entities_from_query(query),
            retry_router_text=retry_router_text,
            retry_attempted=True,
        )

    observation = Observation.from_action(
        action,
        observation_type=ObservationType.ROUTE_RESULT,
        status=RunStageStatus.COMPLETED,
        payload=route_projection(router_query_preparation_contract),
    )
    return RouteRequestRuntimeResult(
        router_query_preparation_contract=router_query_preparation_contract,
        observation=observation,
    )


__all__ = [
    "RouteRequestRuntimeResult",
    "execute_route_request_action",
    "route_projection",
]
