"""Dependency-injected executor for active source-class recovery actions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from core.authority_lifecycle_execution import (
    record_authority_lifecycle_executor_entrypoint_reached,
    source_class_recovery_execution_blocked_if_needed,
    sync_authority_lifecycle_execution_from_source_class_trace,
)
from core.canonical_technical_docs_policy import (
    is_academic_literature_domain_filter,
    is_canonical_technical_documentation_context,
)
from core.controller_recovery_decision import (
    build_controller_recovery_decision,
    controller_recovery_executor_allows_attempt,
)
from core.official_canonical_recovery_candidate_acquisition import (
    build_official_canonical_recovery_candidate_acquisition_trace,
)
from core.run_controller import RunController
from core.source_class_recovery import build_recovery_source_quality_diagnostics


def _normalize_domain_constraint(value: Any) -> str:
    domain = " ".join(str(value or "").strip().casefold().split())
    if not domain:
        return ""
    domain = re.sub(r"^https?://", "", domain).split("/", 1)[0].rstrip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain):
        return ""
    return domain if "." in domain else ""


def _copy_domain_constraints(value: Any) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    values = value if isinstance(value, (list, tuple)) else []
    for item in values:
        domain = _normalize_domain_constraint(item)
        if domain and domain not in seen:
            domains.append(domain)
            seen.add(domain)
    return domains


def _merge_domain_constraints(*domain_lists: Any) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for domain_list in domain_lists:
        for domain in _copy_domain_constraints(domain_list):
            if domain not in seen:
                merged.append(domain)
                seen.add(domain)
    return merged


def _action_source_classes(action: Any) -> list[str]:
    classes: list[str] = []
    for container in (
        getattr(action, "signals", None),
        getattr(action, "metadata", None),
    ):
        if not isinstance(container, Mapping):
            continue
        for key in (
            "active_source_class_recovery_missing_classes",
            "missing_expected_source_classes",
            "source_class_recovery_candidate_v2_classes",
        ):
            values = container.get(key)
            if not isinstance(values, (list, tuple, set)):
                continue
            for value in values:
                text = str(value or "").strip()
                if text and text not in classes:
                    classes.append(text)
    return classes


def _canonical_technical_documentation_recovery_action(
    action: Any,
    queries: list[str],
) -> bool:
    signals = getattr(action, "signals", None)
    metadata = getattr(action, "metadata", None)
    text_parts: list[Any] = [
        getattr(action, "reason", ""),
        " ".join(str(query or "") for query in queries),
    ]
    for container in (signals, metadata):
        if not isinstance(container, Mapping):
            continue
        for key in (
            "active_source_class_recovery_reason",
            "query",
            "query_preview",
            "core_topic",
            "primary_entity",
        ):
            text_parts.append(container.get(key))
    return is_canonical_technical_documentation_context(
        *text_parts,
        required_source_classes=_action_source_classes(action),
    )


def _source_class_recovery_action(
    controller: RunController,
    *,
    error_type: type[Exception] = RuntimeError,
) -> Any | None:
    """Return the active controller-approved source-class recovery action."""
    state = controller.state
    if not state.active_source_class_recovery_eligible:
        return None
    actions = list(state.recovery_action_records) + list(controller.ledger.retrieval_actions)
    for action in actions:
        if getattr(action, "name", None) == "source_class_recovery":
            if getattr(action, "active", None) is not True or getattr(action, "shadow", None) is not False:
                raise error_type(
                    "source_class_recovery action must be controller-approved"
                )
            return action
    return None


def _validate_controller_action_envelope(
    action: Any,
    *,
    error_type: type[Exception],
) -> None:
    metadata = getattr(action, "metadata", None)
    envelope = (
        metadata.get("controller_action_envelope")
        if isinstance(metadata, Mapping)
        else None
    )
    if not isinstance(envelope, Mapping):
        raise error_type("source_class_recovery action missing controller envelope")
    if envelope.get("action_type") != "recover_missing_source_class":
        raise error_type("source_class_recovery action has unexpected action envelope")
    if envelope.get("allowed_action") is not True:
        raise error_type("source_class_recovery action envelope is not approved")
    required_classes = envelope.get("required_source_class")
    if not isinstance(required_classes, list) or not required_classes:
        raise error_type("source_class_recovery action envelope has no required class")


def _mark_source_class_recovery_executed(
    controller: RunController,
    *,
    result_count: int,
    new_url_count: int,
) -> None:
    state = controller.state
    state.active_source_class_recovery_used = True
    state.active_source_class_recovery_execution_attempted = True
    state.active_source_class_recovery_result_count = max(0, int(result_count))
    state.active_source_class_recovery_new_url_count = max(0, int(new_url_count))
    state.active_source_class_recovery_attempt_count = min(
        1,
        max(1, int(state.active_source_class_recovery_attempt_count or 0)),
    )

    metadata = {
        "execution": "orchestrator_adapter_executed",
        "result_count": state.active_source_class_recovery_result_count,
        "new_url_count": state.active_source_class_recovery_new_url_count,
    }
    for action in list(state.recovery_action_records) + list(controller.ledger.retrieval_actions):
        if getattr(action, "name", None) == "source_class_recovery":
            action.metadata.update(metadata)


def execute_source_class_recovery_action(
    controller: RunController,
    *,
    lifecycle_trace: dict[str, Any],
    process_search_queries: Any,
    all_passages: list[dict[str, Any]],
    intent: str,
    complexity: str,
    results_per_query: int,
    include_domains: list[str],
    exclude_domains: list[str],
    query_embedding: Any,
    seen_urls: set[str],
    collected_images: set[str],
    embed_provider: str,
    embed_model: str,
    local_url: str,
    embed_texts: Any,
    compute_similarities: Any,
    status_container: Any,
    search_providers: list[str],
    exa_domain_filter: list[str] | None,
    entity_hint: str | None,
    provider_diagnostics: list[dict[str, Any]],
    retrieval_pass_records: list[dict[str, Any]],
    error_type: type[Exception] = RuntimeError,
) -> dict[str, int | bool]:
    """Execute one controller-approved source-class recovery action additively."""
    if controller.state.active_source_class_recovery_used:
        return {
            "attempted": False,
            "result_count": int(
                controller.state.active_source_class_recovery_result_count or 0
            ),
            "new_url_count": int(
                controller.state.active_source_class_recovery_new_url_count or 0
            ),
        }

    action = _source_class_recovery_action(controller, error_type=error_type)
    if action is None:
        return {"attempted": False, "result_count": 0, "new_url_count": 0}
    _validate_controller_action_envelope(action, error_type=error_type)

    queries = list(getattr(action, "queries", None) or [])
    search_depth = getattr(action, "search_depth", None)
    provider_role = getattr(action, "provider_role", None) or "source_class_recovery"
    action_metadata = getattr(action, "metadata", None)
    official_domain_constraints = _copy_domain_constraints(
        action_metadata.get("official_domain_constraints")
        if isinstance(action_metadata, dict)
        else []
    )
    if provider_role != "source_class_recovery":
        raise error_type("source_class_recovery action has unexpected provider role")
    if not queries or search_depth is None:
        return {"attempted": False, "result_count": 0, "new_url_count": 0}

    controller_recovery_decision = build_controller_recovery_decision(
        {
            **lifecycle_trace,
            "required_source_classes": _action_source_classes(action),
            "recovery_query_count": len(queries),
            "recovery_slot_available": (
                controller.state.active_source_class_recovery_used is not True
            ),
        }
    )
    lifecycle_trace.update(controller_recovery_decision.to_executor_trace_fields())
    if not controller_recovery_executor_allows_attempt(
        controller_recovery_decision
    ):
        lifecycle_trace["active_source_class_recovery_skip_reason"] = (
            "controller_recovery_decision_denied_executor_action"
        )
        lifecycle_trace.setdefault(
            "active_source_class_recovery_blockers",
            [],
        )
        lifecycle_trace["active_source_class_recovery_blockers"] = list(
            lifecycle_trace.get("active_source_class_recovery_blockers") or []
        ) + [controller_recovery_decision.decision]
        return {"attempted": False, "result_count": 0, "new_url_count": 0}

    recovery_include_domains = list(include_domains)
    recovery_exa_domain_filter = exa_domain_filter
    if official_domain_constraints:
        recovery_include_domains = _merge_domain_constraints(
            include_domains,
            official_domain_constraints,
        )
        recovery_exa_domain_filter = _merge_domain_constraints(
            exa_domain_filter or [],
            official_domain_constraints,
        )
    elif (
        is_academic_literature_domain_filter(recovery_exa_domain_filter)
        and _canonical_technical_documentation_recovery_action(action, queries)
    ):
        recovery_exa_domain_filter = None

    lifecycle_trace["active_source_class_recovery_attempt_count"] = min(
        1,
        max(1, int(lifecycle_trace.get("active_source_class_recovery_attempt_count") or 0)),
    )
    if "authority_lifecycle" not in lifecycle_trace:
        lifecycle_trace["active_source_class_recovery_used"] = True
        lifecycle_trace["active_source_class_recovery_execution_attempted"] = True
    record_authority_lifecycle_executor_entrypoint_reached(
        lifecycle_trace,
        explanation="source_class_recovery_executor_entrypoint_reached",
    )
    seen_before = len(seen_urls)
    recovered_passages = process_search_queries(
        queries,
        intent,
        complexity,
        str(search_depth),
        results_per_query,
        recovery_include_domains,
        exclude_domains,
        query_embedding,
        seen_urls,
        collected_images,
        embed_provider,
        embed_model,
        local_url,
        embed_texts,
        compute_similarities,
        status_container=status_container,
        search_providers=list(search_providers),
        exa_domain_filter=recovery_exa_domain_filter,
        entity_hint=entity_hint,
        provider_diagnostics=provider_diagnostics,
        provider_role=provider_role,
    )
    new_url_count = max(0, len(seen_urls) - seen_before)
    usable_passages: list[dict[str, Any]] = []
    for passage in recovered_passages or []:
        if not isinstance(passage, dict):
            continue
        recovered = dict(passage)
        recovered.setdefault("_provider_role", provider_role)
        recovered.setdefault("retrieval_stage", provider_role)
        usable_passages.append(recovered)

    if usable_passages:
        all_passages.extend(usable_passages)

    result_count = len(usable_passages)
    lifecycle_trace.update(
        build_recovery_source_quality_diagnostics(usable_passages)
    )
    lifecycle_trace["active_source_class_recovery_result_count"] = result_count
    lifecycle_trace["active_source_class_recovery_new_url_count"] = new_url_count
    lifecycle_trace.update(
        build_official_canonical_recovery_candidate_acquisition_trace(
            lifecycle_trace=lifecycle_trace,
            provider_diagnostics=provider_diagnostics,
            execution_result={
                "attempted": True,
                "result_count": result_count,
                "new_url_count": new_url_count,
            },
        )
    )
    sync_authority_lifecycle_execution_from_source_class_trace(lifecycle_trace)
    _mark_source_class_recovery_executed(
        controller,
        result_count=result_count,
        new_url_count=new_url_count,
    )
    pass_record: dict[str, Any] = {
        "stage": "source_class_recovery",
        "iteration": None,
        "queries": list(queries),
        "providers": list(search_providers),
        "provider_role": provider_role,
        "search_depth": str(search_depth),
        "results_per_query": results_per_query,
    }
    if official_domain_constraints:
        pass_record["include_domains"] = list(recovery_include_domains)
        pass_record["official_domain_constraints"] = list(
            official_domain_constraints
        )
    retrieval_pass_records.append(pass_record)
    for name, value in (
        ("execution_attempted", True),
        ("result_count", result_count),
        ("new_url_count", new_url_count),
        ("provider_role", provider_role),
        ("search_depth", str(search_depth)),
    ):
        controller.ledger.record_fact(
            stage="source_class_recovery",
            name=name,
            value=value,
            metadata={"source": "orchestrator_adapter"},
        )
    return {
        "attempted": True,
        "result_count": result_count,
        "new_url_count": new_url_count,
    }


def record_source_class_recovery_execution_blocked_if_needed(
    lifecycle_trace: dict[str, Any],
    *,
    authorized_for_executor: bool,
    blocker_reason: str = "source_class_recovery_executor_dispatch_not_authorized",
) -> dict[str, Any]:
    """Project non-dispatch into AuthorityLifecycle execution state."""

    return source_class_recovery_execution_blocked_if_needed(
        lifecycle_trace,
        authorized_for_executor=authorized_for_executor,
        blocker_reason=blocker_reason,
    )
