"""Phase-focus proof for the canonical SearchPlanner boundary observer.

Proof class: PRODUCT-PATH-REGRESSION.
Surface guarded: ordinary SearchPlanner composition and sanitized observation.
High-custody surface: model-call prompt/response material remains transient.
Runtime path: ``core.pipeline_orchestrator.run_pipeline``.
Expected cost: bounded offline fake execution.
Promotion posture: remain phase_focus until a durable evaluator lane exists.
Retirement condition: only with a successor ordinary-boundary equivalence proof.
Fast-PR posture: not a sentinel candidate because the full ordinary fixture is
materially more expensive than the tiny fast_pr budget.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

import core.pipeline_orchestrator as orchestrator
from core.cost_accounting import CostAccumulator
from core.protocols import NullStatusWriter
from core.search_planner_model_prompt import SEARCH_PLANNER_MODEL_SYSTEM_PROMPT
from core.text_utils import clean_json_response
from scripts.evaluation.search_planner_product_boundary_observer import (
    CANONICAL_PRODUCT_BOUNDARY_REF,
    CanonicalProductSearchPlannerBoundaryObserver,
)
from tests.fixtures.searchos_analystos_offline_scenarios import (
    SCENARIOS,
    SearchOSAnalystOSHarness,
    planner_payload,
)
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_PACKET,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)

SCENARIO = SCENARIOS[0]
_PROMPT_MARKER = "Sanitized planner input JSON:\n"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _model_payload() -> dict[str, Any]:
    payload = planner_payload(SCENARIO)
    payload.pop("planner_model_metadata", None)
    for obligation in payload["source_obligation_candidates"]:
        obligation["obligation_kind"] = "official_current"
        obligation["strictness"] = "required"
    return payload


class _BoundaryHarness(SearchOSAnalystOSHarness):
    def __init__(
        self,
        tmp_path: Path,
        *,
        observed: bool,
        invalid: bool = False,
    ) -> None:
        super().__init__(tmp_path, SCENARIO)
        self.invalid = invalid
        self.safe_direct_call: dict[str, Any] = {}
        self.observer = CanonicalProductSearchPlannerBoundaryObserver(self._scripted_model_call) if observed else None

    def deps(self):
        return replace(
            super().deps(),
            ask_model=self.observer or self._scripted_model_call,
            clean_json_response=clean_json_response,
            search_planner_adapter=None,
        )

    def _scripted_model_call(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs: Any,
    ) -> str:
        if system_prompt != SEARCH_PLANNER_MODEL_SYSTEM_PROMPT:
            return super().ask_model(prompt, system_prompt, **kwargs)
        prefix, packet_text = prompt.split(_PROMPT_MARKER, 1)
        packet = json.loads(packet_text)
        planner_input = _canonical(packet["planner_input"])
        instruction = prefix + _PROMPT_MARKER
        response = (
            "not-json"
            if self.invalid
            else "synthetic-prefix\n" + json.dumps(_model_payload(), sort_keys=True) + "\nsynthetic-suffix"
        )
        self.safe_direct_call = {
            "semantic_input_digest": _digest(planner_input),
            "semantic_input_length": len(planner_input),
            "system_prompt_digest": _digest(system_prompt),
            "system_prompt_length": len(system_prompt),
            "instruction_digest": _digest(instruction),
            "instruction_length": len(instruction),
            "full_prompt_digest": _digest(prompt),
            "full_prompt_length": len(prompt),
            "keyword_names": tuple(sorted(kwargs)),
            "keyword_types": {key: type(value).__name__ for key, value in sorted(kwargs.items())},
            "require_json": kwargs.get("require_json") is True,
            "provider_present": bool(kwargs.get("provider")),
            "model_present": bool(kwargs.get("model")),
            "cost_accumulator_present": (kwargs.get("cost_accumulator") is not None),
            "cost_phase": kwargs.get("cost_phase"),
            "output_digest": _digest(response),
            "output_length": len(response),
        }
        return response


def _run(
    tmp_path: Path,
    *,
    observed: bool,
    invalid: bool = False,
) -> tuple[_BoundaryHarness, Any, Exception | None, dict[str, str]]:
    monkeypatch = MonkeyPatch()
    tmp_path.mkdir(parents=True, exist_ok=True)
    harness = _BoundaryHarness(
        tmp_path,
        observed=observed,
        invalid=invalid,
    )
    try:
        scrub_offline_runtime(monkeypatch)
        captured = install_handoff_capture(
            monkeypatch,
            capture_stages=(HANDOFF_PACKET,),
        )
        config = replace(
            offline_balanced_run_config(
                query=SCENARIO.root_query,
                current_date="2026-07-29",
                session_id="evaluation-split-equivalence",
                run_id="evaluation-split-equivalence",
                smart_search_judgment_model=True,
            ),
            mode=SCENARIO.mode,
        )
        failure = None
        outcome = None
        try:
            outcome = orchestrator.run_pipeline(
                config,
                harness.deps(),
                NullStatusWriter(),
                CostAccumulator(),
            )
        except Exception as exc:
            failure = exc
        kernel = captured.get("run_kernel")
        state = getattr(kernel, "state", None)
        state_digests = {
            "proposal": _digest(_canonical(getattr(state, "search_planner_proposal_state", None))),
            "acceptance": _digest(
                _canonical(
                    getattr(
                        state,
                        "initial_answer_contract_projection",
                        None,
                    )
                )
            ),
            "search_work_plan": _digest(_canonical(getattr(state, "search_work_plan", None))),
            "outcome": _digest(str(getattr(outcome, "report", ""))),
        }
        return harness, kernel, failure, state_digests
    finally:
        monkeypatch.undo()


def test_observer_matches_exact_ordinary_product_boundary(
    tmp_path: Path,
) -> None:
    direct, _direct_kernel, direct_failure, direct_state = _run(
        tmp_path / "direct",
        observed=False,
    )
    observed, kernel, observed_failure, observed_state = _run(
        tmp_path / "observed",
        observed=True,
    )
    assert direct_failure is None
    assert observed_failure is None
    assert direct.safe_direct_call == observed.safe_direct_call
    assert direct_state == observed_state

    observation = observed.observer.finalize(run_kernel=kernel)
    prompt = observation.prompt_identity
    shape = observation.ask_model_argument_shape
    assert prompt is not None
    assert shape is not None
    assert asdict(prompt) == {
        "semantic_input_digest": direct.safe_direct_call["semantic_input_digest"],
        "semantic_input_length": direct.safe_direct_call["semantic_input_length"],
        "system_prompt_digest": direct.safe_direct_call["system_prompt_digest"],
        "system_prompt_length": direct.safe_direct_call["system_prompt_length"],
        "instruction_digest": direct.safe_direct_call["instruction_digest"],
        "instruction_length": direct.safe_direct_call["instruction_length"],
        "full_prompt_digest": direct.safe_direct_call["full_prompt_digest"],
        "full_prompt_length": direct.safe_direct_call["full_prompt_length"],
        "extraction_posture": "PASS",
    }
    assert shape.keyword_names == direct.safe_direct_call["keyword_names"]
    assert shape.keyword_types == direct.safe_direct_call["keyword_types"]
    assert observation.output_digest == direct.safe_direct_call["output_digest"]
    assert observation.output_length == direct.safe_direct_call["output_length"]
    assert observation.proposal_digest == observed_state["proposal"]
    assert observation.boundary_ref == CANONICAL_PRODUCT_BOUNDARY_REF
    assert observation.parser_posture == "PASS"
    assert observation.validator_posture == "PASS"
    assert observation.runtime_projection_posture == "PASS"
    assert observation.initial_acceptance_posture == "PASS"
    assert observation.search_work_plan_posture == "PASS"


def test_observer_preserves_product_fail_closed_posture(
    tmp_path: Path,
) -> None:
    direct, _direct_kernel, direct_failure, _direct_state = _run(
        tmp_path / "direct-failure",
        observed=False,
        invalid=True,
    )
    observed, kernel, observed_failure, _observed_state = _run(
        tmp_path / "observed-failure",
        observed=True,
        invalid=True,
    )
    assert direct_failure is not None
    assert observed_failure is not None
    assert type(direct_failure) is type(observed_failure)
    assert str(direct_failure) == str(observed_failure)
    assert direct.safe_direct_call == observed.safe_direct_call

    observation = observed.observer.finalize(
        run_kernel=kernel,
        failure=observed_failure,
    )
    assert observation.boundary_status == "FAIL"
    assert observation.parser_posture == "FAIL"
    assert observation.validator_posture == "NOT_REACHED"
    assert observation.runtime_projection_posture == "NOT_REACHED"
    assert observation.initial_acceptance_posture == "NOT_REACHED"


def test_observer_retains_only_safe_digest_and_shape_facts(
    tmp_path: Path,
) -> None:
    harness, kernel, failure, _state = _run(
        tmp_path / "privacy",
        observed=True,
    )
    assert failure is None
    observation = harness.observer.finalize(run_kernel=kernel)
    packet = observation.to_packet()
    serialized = json.dumps(packet, sort_keys=True).casefold()
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_response_retained"] is False
    assert packet["raw_provider_payload_retained"] is False
    assert packet["observer_parsed_model_output"] is False
    assert SCENARIO.root_query.casefold() not in serialized
    assert "synthetic-prefix" not in serialized


def test_observer_delegates_nonplanner_model_roles_without_claiming_them() -> None:
    calls: list[str] = []

    def dependency(
        prompt: str,
        system_prompt: str,
        **_kwargs: Any,
    ) -> str:
        calls.append(f"{system_prompt}:{prompt}")
        return "delegated"

    observer = CanonicalProductSearchPlannerBoundaryObserver(dependency)
    assert observer("payload", "another-role", marker=True) == "delegated"
    assert calls == ["another-role:payload"]
    result = observer.finalize(run_kernel=None)
    assert result.product_boundary_reached is False
    assert result.boundary_status == "NOT_REACHED"


def test_observer_rejects_raw_material_disguised_as_safe_refs() -> None:
    observer = CanonicalProductSearchPlannerBoundaryObserver(lambda _prompt, _system, **_kwargs: "{}")
    prompt = f'Instruction.\n{_PROMPT_MARKER}{{"planner_input":{{"safe":"value"}}}}'
    observer(
        prompt,
        SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
        provider="synthetic",
        model="synthetic",
        effort="fixed",
        require_json=True,
        cost_accumulator=object(),
        cost_phase="search_planner",
    )
    with pytest.raises(ValueError, match="forbidden key: raw_prompt"):
        observer.finalize(
            run_kernel=None,
            safe_execution_refs=({"raw_prompt": "must never enter an observation"},),
        )


def test_observer_failure_reason_retains_only_type_and_digest() -> None:
    raw_exception_material = "synthetic-private-response-material"

    def failing_dependency(
        _prompt: str,
        _system_prompt: str,
        **_kwargs: Any,
    ) -> str:
        raise RuntimeError(raw_exception_material)

    observer = CanonicalProductSearchPlannerBoundaryObserver(
        failing_dependency
    )
    prompt = (
        f'Instruction.\n{_PROMPT_MARKER}'
        '{"planner_input":{"safe":"value"}}'
    )
    with pytest.raises(RuntimeError) as captured:
        observer(
            prompt,
            SEARCH_PLANNER_MODEL_SYSTEM_PROMPT,
            provider="synthetic",
            model="synthetic",
            effort="fixed",
            require_json=True,
            cost_accumulator=object(),
            cost_phase="search_planner",
        )
    observation = observer.finalize(
        run_kernel=None,
        failure=captured.value,
    )
    assert raw_exception_material not in str(
        observation.bounded_failure_reason
    )
    assert observation.bounded_failure_reason == (
        f"RuntimeError:message_sha256={_digest(raw_exception_material)}"
    )
