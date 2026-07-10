"""Regression guards for selection-only multicomponent timing."""

from __future__ import annotations

from typing import Any

import pytest

import core.ordinary_multicomponent_synthesis_runtime as runtime
from core.run_kernel import RunKernel


def _accepted_contract(
    *,
    run_id: str,
    request_id: str,
    component_count: int,
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": run_id,
        "request_id": request_id,
        "accepted_contract_version": "0.1-passive",
        "accepted_contract_digest": f"digest:{component_count}",
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Explain how these facts relate.",
        },
        "accepted_answer_component_refs": [
            {
                "component_id": f"component:{index}",
                "component_revision": "1",
                "component_digest": f"component-digest:{index}",
                "user_facing_label": f"Fact {index}",
                "user_facing_question": f"What is fact {index}?",
            }
            for index in range(1, component_count + 1)
        ],
    }


@pytest.mark.parametrize("component_count", [1, 6])
def test_selection_only_near_miss_defers_direct_semantic_producer(
    monkeypatch: pytest.MonkeyPatch,
    component_count: int,
) -> None:
    kernel = RunKernel.start(
        run_id=f"run:selection-only:{component_count}",
        request_id=f"request:selection-only:{component_count}",
    )
    kernel.state.initial_answer_contract = _accepted_contract(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        component_count=component_count,
    )
    calls: list[tuple[Any, Any]] = []
    sentinel = object()

    def _direct(run_kernel: Any, runtime_scope: Any) -> object:
        calls.append((run_kernel, runtime_scope))
        return sentinel

    monkeypatch.setattr(
        runtime,
        "execute_ordinary_semantic_producer_handoff_from_scope",
        _direct,
    )
    early = runtime.execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
        kernel,
        {"query": "near miss"},
        execute_selected_lane=False,
    )
    assert early.status is runtime.OrdinaryMulticomponentStatus.NOT_QUALIFIED
    assert early.direct_handoff is None
    assert calls == []

    later = runtime.execute_ordinary_semantic_or_multicomponent_handoff_from_scope(
        kernel,
        {"query": "near miss"},
    )
    assert later.status is runtime.OrdinaryMulticomponentStatus.NOT_QUALIFIED
    assert later.direct_handoff is sentinel
    assert len(calls) == 1
