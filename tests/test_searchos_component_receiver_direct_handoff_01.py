"""SEAM-DIAGNOSTIC: SearchOS receiver selector-boundary compatibility.

Proof class: OFFLINE_COMPONENT_PROOF. Validation bucket: phase_focus. Surface:
the selected-lane branch that distinguishes direct SearchOS handoff plumbing
from retained non-SearchOS passage selection. Runtime path: isolated receiver
entry with no provider or model calls. Expected cost: sub-second. Promotion
posture: keep phase-focused; retire if the legacy selector is later retired for
all callers under a separately licensed phase. Not a fast_pr candidate because
this is a narrow implementation-detail sentinel.
"""

from __future__ import annotations

from typing import Any

import pytest

from core import ordinary_multicomponent_synthesis_runtime as multicomponent
from core.run_kernel import RunKernel


def test_non_searchos_selected_lane_retains_legacy_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SelectorReached(RuntimeError):
        pass

    kernel = RunKernel.start(
        run_id="run:non-searchos-selector-sentinel",
        request_id="request:non-searchos-selector-sentinel",
    )
    kernel.state.initial_answer_contract = {
        "accepted_contract_version": "1",
        "accepted_contract_digest": "a" * 64,
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Compare the two facts.",
        },
        "accepted_answer_component_refs": [
            {
                "component_id": f"component-{index}",
                "component_revision": "1",
                "component_digest": str(index) * 64,
                "allowed_support_kinds": ["direct"],
            }
            for index in (1, 2)
        ],
    }
    selector_calls = 0

    def selector_sentinel(*_args: Any, **_kwargs: Any) -> Any:
        nonlocal selector_calls
        selector_calls += 1
        raise SelectorReached

    monkeypatch.setattr(
        multicomponent,
        "select_bindable_final_passages_for_components",
        selector_sentinel,
    )

    with pytest.raises(SelectorReached):
        multicomponent._execute_selected_lane(
            run_kernel=kernel,
            runtime_scope={"final_top_evidence": []},
            requested_synthesis_directive="Compare the two facts.",
            allow_searchos_component_receiver=False,
        )

    assert selector_calls == 1

