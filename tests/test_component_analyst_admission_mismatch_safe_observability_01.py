"""COMPONENT-ANALYST-ADMISSION-MISMATCH-SAFE-OBSERVABILITY-01.

Test path: tests/test_component_analyst_admission_mismatch_safe_observability_01.py
Proof class: offline_product_path_proof / repair diagnostic.
Validation bucket: phase_focus.
Surface guarded: Component Analyst exact-input admission mismatch and the
bounded PRODUCT runner's allowlisted safe projection.
High-custody or closed-this-phase surface: Component Analyst prompt/semantics,
PR #588 current-authority repair, SearchOS ranking, and live PRODUCT calls.
Runtime/product path guarded: ordinary admission fail-closed path and AG-LIVE
bounded runner sanitized failure packet.
Expected cost: unit tests sub-second; one offline N=1 corridor a few seconds.
Promotion posture: stay phase_focus until the live structural mismatch is
classified; never fast_pr.
Demotion/retirement condition: retire after the product mismatch is repaired
and a durable admission/regression sentinel owns the same fail-closed diagnostic.
Why not fast_pr: phase-detail privacy and classification proofs, not a cheap
broad sentinel.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping
from unittest.mock import patch

import pytest

from core.multicomponent_component_admission import (
    COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH,
    COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION,
    MulticomponentComponentAdmissionError,
    build_component_analyst_input_binding_mismatch_v1,
    component_analyst_input_packet,
    contract_authority_facts_from_run_kernel,
    independent_component_analyst_dispatch_input_digest,
    project_component_analyst_input_binding_mismatch_v1,
    stage_multicomponent_component_admission,
)
from core.multicomponent_role_runtime import ROLE_COMPONENT_ANALYST, safe_packet_digest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUNNER_PATH = ROOT / "scripts" / "ag_live_bound_01_bounded_product_runner.py"
SUPPORT_PATH = ROOT / "scripts" / "ag_live_bound_01_support.py"
PRIMARY_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for rel_tol and abs_tol in math.isclose()?"
)
VALID_ARGS = [
    "--query",
    PRIMARY_QUERY,
    "--mode",
    "Balanced",
    "--include-domains",
    "docs.python.org",
    "--output",
    "output/ag_live_bound_01_packet.json",
]

CANARY_EVIDENCE = "CANARY_COMPONENT_EVIDENCE_TEXT_ZXQ91"
CANARY_CLAIM = "CANARY_CLAIM_TEXT_ZXQ92"
CANARY_CAVEAT = "CANARY_CAVEAT_TEXT_ZXQ93"
CANARY_QUERY = "CANARY_USER_QUERY_LIKE_TEXT_ZXQ94"
CANARY_URL = "https://canary.example/private/source-zxq95"
CANARY_PROVIDER = "CANARY_FAKE_PROVIDER_PAYLOAD_ZXQ96"
CANARY_NUMERIC = "424242424242.125"
CANARIES = (
    CANARY_EVIDENCE,
    CANARY_CLAIM,
    CANARY_CAVEAT,
    CANARY_QUERY,
    CANARY_URL,
    CANARY_PROVIDER,
    CANARY_NUMERIC,
)
KNOWN_SECTIONS = (
    "run_binding",
    "component_ref",
    "component_evidence",
    "quantitative_source_catalog",
    "quantitative_specialist_proposal_contract",
)
_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64
_DIGEST_COMPONENT = "c" * 64
_DIGEST_CURRENT = "d" * 64
_VALID_SHA256_DIGEST = "0123456789abcdef" * 4
_UPPER_SHA256_DIGEST = "ABCDEF0123456789" * 4
_DIGEST_FIELD_CANARIES = (
    "CANARY_PRIVATE_DIGEST_VALUE",
    "CANARY_PRIVATE_SUPPLIED_VALUE",
    "CANARY_PRIVATE_SECTION_VALUE",
)


def _ensure_scripts_package() -> None:
    if "scripts" not in sys.modules:
        scripts_pkg = ModuleType("scripts")
        scripts_pkg.__path__ = [str(ROOT / "scripts")]  # type: ignore[attr-defined]
        sys.modules["scripts"] = scripts_pkg


def _load_module(path: Path, module_name: str) -> ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    _ensure_scripts_package()
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_runner() -> ModuleType:
    return _load_module(
        RUNNER_PATH,
        "scripts.ag_live_bound_01_bounded_product_runner",
    )


def _load_support() -> ModuleType:
    return _load_module(SUPPORT_PATH, "scripts.ag_live_bound_01_support")


def _stub_live_runner_without_env(
    runner: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_load_live_environment", lambda: None)
    monkeypatch.setattr(runner, "_validate_live_model_keys", lambda: None)
    monkeypatch.setattr(runner, "_build_live_run_deps", lambda: SimpleNamespace())
    import core.quantitative_specialist_product_activation as product_activation

    monkeypatch.setattr(
        product_activation,
        "compose_quantitative_specialist_product_deps",
        lambda deps: deps,
    )
    monkeypatch.setattr(
        runner,
        "_live_runtime_helpers",
        lambda: (SimpleNamespace(), SimpleNamespace()),
    )

    def fake_run_config(context: Any, *, cap_policy: Any) -> Any:
        return SimpleNamespace(
            query=context.query,
            mode=context.mode,
            fast_provider="FixtureFastProvider",
            fast_model="fixture-fast-model",
            smart_provider="FixtureSmartProvider",
            smart_model="fixture-smart-model",
            embed_provider="FixtureEmbedProvider",
            embed_model="fixture-embed-model",
            cap_policy=cap_policy,
        )

    monkeypatch.setattr(runner, "_build_live_run_config", fake_run_config)


def _component_ref() -> dict[str, Any]:
    return {
        "component_id": "component:1",
        "component_revision": "1",
        "component_digest": _DIGEST_COMPONENT,
        "user_facing_label": "Fact 1",
        "user_facing_question": CANARY_QUERY,
        "mandatory_caveats": [CANARY_CAVEAT],
        "prohibited_upgrades": [],
    }


def _accepted_contract(
    *,
    version: str = "0.1-passive",
    digest: str = _DIGEST_B,
    component_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "owner": "RunKernel.InitialAnswerContract",
        "canonical_state": True,
        "run_id": "run:mismatch-obs",
        "request_id": "request:mismatch-obs",
        "accepted_contract_version": version,
        "accepted_contract_digest": digest,
        "parent_question_meaning_record_id": "qmr:1",
        "parent_question_meaning_record_digest": "qmr-digest",
        "question_meaning_metadata": {
            "explicit_factual_component_list": True,
            "requested_synthesis_directive": "Explain the combined result.",
        },
        "accepted_answer_component_refs": [component_ref or _component_ref()],
    }


def _evidence_input() -> dict[str, Any]:
    return {
        "evidence_status": "available",
        "evidence_ref_id": "evidence:1",
        "bounded_text": CANARY_EVIDENCE,
        "source_url": CANARY_URL,
        "provider_payload": CANARY_PROVIDER,
        "numeric_literal": CANARY_NUMERIC,
        "candidate_custody_ref": {"candidate_id": "cand-1"},
    }


def _packet(
    accepted: dict[str, Any] | None = None,
    component_ref: dict[str, Any] | None = None,
    evidence_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = accepted or _accepted_contract()
    ref = component_ref or _component_ref()
    return component_analyst_input_packet(
        run_id=str(contract["run_id"]),
        request_id=str(contract["request_id"]),
        accepted_contract=contract,
        component_ref=ref,
        evidence_input=evidence_input or _evidence_input(),
    )


def _semantic_output(*, supported: bool = False) -> dict[str, Any]:
    if supported:
        return {
            "case_posture": "supported",
            "support_status": "supported",
            "claim_text": CANARY_CLAIM,
            "evidence_analysis": CANARY_EVIDENCE,
            "self_audit": "The case stays inside the supplied component.",
            "caveats": [CANARY_CAVEAT],
            "nonclaims": [],
            "contradictions": [],
            "blockers": [],
        }
    return {
        "case_posture": "unsupported",
        "support_status": "unsupported",
        "claim_text": CANARY_CLAIM,
        "evidence_analysis": CANARY_EVIDENCE,
        "self_audit": "The case stays inside the supplied component.",
        "caveats": [CANARY_CAVEAT],
        "nonclaims": [],
        "contradictions": [],
        "blockers": [],
    }


def _artifact(
    input_packet: Mapping[str, Any],
    *,
    input_packet_digest: str | None = None,
    supported: bool = False,
) -> dict[str, Any]:
    core = {
        "schema_version": "multicomponent_semantic_role_artifact_v1",
        "role": ROLE_COMPONENT_ANALYST,
        "artifact_id": "artifact:component_analyst:mismatch-obs",
        "run_id": "run:mismatch-obs",
        "request_id": "request:mismatch-obs",
        "input_packet_digest": input_packet_digest or safe_packet_digest(input_packet),
        "logical_evaluation_key": "component:1",
        "logical_evaluations": 1,
        "physical_calls": 1,
        "configured_model_route": {
            "provider": "offline",
            "model": "fixture",
            "role": "SmartModel",
        },
        "authorized_action_ref": {
            "action_id": "action:component_analyst",
            "stage": "stage:component_analyst",
            "sequence": 1,
            "observation_type": "component_analyst_completed",
        },
        "semantic_output": _semantic_output(supported=supported),
        "raw_prompt_retained": False,
        "raw_model_response_retained": False,
        "raw_provider_payload_retained": False,
    }
    return {**core, "artifact_digest": safe_packet_digest(core)}


def _stage_kwargs(
    *,
    accepted: dict[str, Any] | None = None,
    analyst_input: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
    independent_dispatch_input_digest: str | None = None,
    contract_authority_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = accepted or _accepted_contract()
    packet = analyst_input if analyst_input is not None else _packet(contract)
    return {
        "action_id": "action:admission",
        "run_id": contract["run_id"],
        "request_id": contract["request_id"],
        "accepted_contract": contract,
        "evidence_ledger_projection": {},
        "semantic_observation_admission_history": [],
        "component_coverage_history": [],
        "component_id": "component:1",
        "analyst_artifact": artifact or _artifact(packet),
        "analyst_input_packet": packet,
        "semantic_observation": None,
        "sanitized_content_references": [],
        "component_coverage_record": None,
        "independent_dispatch_input_digest": independent_dispatch_input_digest,
        "contract_authority_facts": contract_authority_facts,
    }


def _raise_mismatch(**kwargs: Any) -> MulticomponentComponentAdmissionError:
    with pytest.raises(MulticomponentComponentAdmissionError) as caught:
        stage_multicomponent_component_admission(**_stage_kwargs(**kwargs))
    return caught.value


def _diagnostic_from(**kwargs: Any) -> dict[str, Any]:
    exc = _raise_mismatch(**kwargs)
    assert str(exc) == COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH
    diagnostic = exc.component_analyst_input_binding_mismatch_v1
    assert isinstance(diagnostic, dict)
    return diagnostic


def _assert_no_canaries(value: Any) -> None:
    rendered = json.dumps(value, sort_keys=True)
    for canary in CANARIES:
        assert canary not in rendered


def _assert_closed_sha256(value: Any) -> None:
    assert isinstance(value, str)
    assert len(value) == 64
    assert value == value.lower()
    assert all(char in "0123456789abcdef" for char in value)


def _assert_digest_only(diagnostic: Mapping[str, Any]) -> None:
    _assert_no_canaries(diagnostic)
    assert diagnostic["schema_version"] == (
        COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION
    )
    for section in KNOWN_SECTIONS:
        _assert_closed_sha256(diagnostic[f"{section}_supplied_digest"])
        _assert_closed_sha256(diagnostic[f"{section}_reconstructed_digest"])
        assert isinstance(diagnostic[f"{section}_equal"], bool)
    for key in (
        "artifact_input_packet_digest",
        "supplied_packet_digest",
        "reconstructed_packet_digest",
        "initial_contract_digest",
        "current_contract_digest",
        "accepted_component_digest",
        "packet_contract_digest",
        "packet_component_digest",
        "independent_dispatch_input_digest",
    ):
        value = diagnostic.get(key)
        if value is not None:
            _assert_closed_sha256(value)
    rendered = json.dumps(diagnostic, sort_keys=True)
    assert "bounded_text" not in rendered
    assert "claim_text" not in rendered
    assert "user_facing_question" not in rendered
    assert "provider_payload" not in rendered


def _establish_official_current_qualification_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent

    original = multicomponent._qualify_searchos_read_material_after_component_analyst_case

    def qualify(*args: Any, **kwargs: Any) -> Any:
        bindable = kwargs["bindable"]
        facts = {
            "source_tier": "official",
            "source_class": "official_current_rules",
            "currentness_signal": "current",
            "eligible_for_stronger_obligation": True,
        }
        bindable.passage.update(facts)
        bindable.candidate_record.update(facts)
        candidate = kwargs["run_kernel"].state.evidence_ledger.candidates[
            bindable.evidence_ref_id
        ]
        for key, value in facts.items():
            setattr(candidate, key, value)
        lineage = dict(bindable.passage["searchos_qualification_lineage"])
        lineage["source_facts"] = {
            **dict(lineage.get("source_facts") or {}),
            **facts,
        }
        bindable.passage["searchos_qualification_lineage"] = lineage
        return original(*args, **kwargs)

    monkeypatch.setattr(
        multicomponent,
        "_qualify_searchos_read_material_after_component_analyst_case",
        qualify,
    )


def test_successful_exact_input_admission_has_no_mismatch_diagnostic() -> None:
    packet = _packet()
    staged = stage_multicomponent_component_admission(**_stage_kwargs(analyst_input=packet))
    assert staged["component_admission_ref"]["admission_status"] == "unsupported"
    assert "component_analyst_input_binding_mismatch_v1" not in json.dumps(
        staged, sort_keys=True
    )


def test_supplied_catalog_tamper_does_not_change_exact_digest_guard() -> None:
    original = _packet()
    supplied = deepcopy(original)
    supplied["quantitative_source_catalog"] = {
        **deepcopy(original["quantitative_source_catalog"]),
        "catalog_kind": "tampered",
    }
    staged = stage_multicomponent_component_admission(
        **_stage_kwargs(analyst_input=supplied, artifact=_artifact(original))
    )
    assert staged["component_admission_ref"]["admission_status"] == "unsupported"


def test_mismatched_component_analyst_input_still_fails_closed() -> None:
    packet = _packet()
    exc = _raise_mismatch(
        analyst_input=packet,
        artifact=_artifact(packet, input_packet_digest="0" * 64),
    )
    assert str(exc) == COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH
    assert exc.component_analyst_input_binding_mismatch_v1["schema_version"] == (
        COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION
    )


def test_mismatch_carries_closed_versioned_diagnostic() -> None:
    packet = _packet()
    diagnostic = _diagnostic_from(
        analyst_input=packet,
        artifact=_artifact(packet, input_packet_digest="0" * 64),
    )
    assert diagnostic["mismatch_class"] == "OTHER"
    assert diagnostic["first_divergent_section"] == "unknown"
    assert diagnostic["supplied_digest_equals_reconstructed"] is True
    assert diagnostic["artifact_digest_equals_reconstructed"] is False
    _assert_digest_only(diagnostic)


def test_first_divergent_section_from_accepted_run_binding_change() -> None:
    initial = _accepted_contract()
    packet = _packet(initial)
    current = _accepted_contract(version="0.2-current", digest=_DIGEST_CURRENT)
    diagnostic = _diagnostic_from(
        accepted=current,
        analyst_input=packet,
        artifact=_artifact(packet),
    )
    assert diagnostic["first_divergent_section"] == "run_binding"
    assert diagnostic["run_binding_equal"] is False
    _assert_digest_only(diagnostic)


def test_first_divergent_section_from_accepted_component_ref_change() -> None:
    accepted_ref = {**_component_ref(), "user_facing_label": "accepted-only-label"}
    packet_ref = _component_ref()
    accepted = _accepted_contract(component_ref=accepted_ref)
    packet = _packet(accepted, component_ref=packet_ref)
    diagnostic = _diagnostic_from(
        accepted=accepted,
        analyst_input=packet,
        artifact=_artifact(packet),
    )
    assert diagnostic["first_divergent_section"] == "component_ref"
    assert diagnostic["component_ref_equal"] is False
    _assert_digest_only(diagnostic)


def test_first_divergent_section_from_non_mapping_component_evidence() -> None:
    original = _packet()
    supplied = deepcopy(original)
    supplied["component_evidence"] = CANARY_EVIDENCE
    diagnostic = _diagnostic_from(
        analyst_input=supplied,
        artifact=_artifact(original),
    )
    assert diagnostic["first_divergent_section"] == "component_evidence"
    assert diagnostic["component_evidence_equal"] is False
    _assert_digest_only(diagnostic)


@pytest.mark.parametrize(
    ("mutate", "expected_section"),
    [
        (
            lambda packet: packet["quantitative_source_catalog"].__setitem__(
                "catalog_kind", "tampered"
            ),
            "quantitative_source_catalog",
        ),
        (
            lambda packet: packet["quantitative_specialist_proposal_contract"].__setitem__(
                "target_kind", "tampered"
            ),
            "quantitative_specialist_proposal_contract",
        ),
    ],
)
def test_first_divergent_section_for_rebuilt_packet_sections(
    mutate: Any,
    expected_section: str,
) -> None:
    original = _packet()
    supplied = deepcopy(original)
    mutate(supplied)
    diagnostic = _diagnostic_from(
        analyst_input=supplied,
        artifact=_artifact(original, input_packet_digest="0" * 64),
    )
    assert diagnostic["first_divergent_section"] == expected_section
    assert diagnostic[f"{expected_section}_equal"] is False
    _assert_digest_only(diagnostic)


def test_builder_reports_component_evidence_section_without_contents() -> None:
    original = _packet()
    reconstructed = deepcopy(original)
    supplied = deepcopy(original)
    supplied["component_evidence"] = {
        **deepcopy(original["component_evidence"]),
        "bounded_text": CANARY_EVIDENCE + "-mutated",
    }
    diagnostic = build_component_analyst_input_binding_mismatch_v1(
        analyst={"input_packet_digest": safe_packet_digest(supplied)},
        supplied_input=supplied,
        reconstructed_input=reconstructed,
        accepted_contract=_accepted_contract(),
        accepted_component=_component_ref(),
    )
    assert diagnostic["first_divergent_section"] == "component_evidence"
    assert diagnostic["component_evidence_equal"] is False
    _assert_digest_only(diagnostic)


def test_privacy_canaries_are_absent_from_diagnostic_and_product_packet(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    original = _packet()
    exc = _raise_mismatch(
        analyst_input=original,
        artifact=_artifact(original, input_packet_digest="0" * 64, supported=True),
    )
    diagnostic = exc.component_analyst_input_binding_mismatch_v1
    _assert_no_canaries(diagnostic)
    extra = project_component_analyst_input_binding_mismatch_v1(
        {
            **diagnostic,
            "bounded_text": CANARY_EVIDENCE,
            "claim_text": CANARY_CLAIM,
            "user_query": CANARY_QUERY,
            "url": CANARY_URL,
        }
    )
    assert "bounded_text" not in extra
    assert "claim_text" not in extra
    _assert_no_canaries(extra)

    runner = _load_runner()
    support = _load_support()
    output = "output/ca_admission_mismatch_obs_01_canary.json"
    _stub_live_runner_without_env(runner, monkeypatch)

    def fail_run_pipeline(
        _config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        raise exc

    with patch(
        "core.pipeline_orchestrator.run_pipeline",
        side_effect=fail_run_pipeline,
    ):
        result = runner.main(
            [*VALID_ARGS, "--output", output, "--confirm-live-product-run"]
        )

    assert result == 2
    capsys.readouterr()
    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    (ROOT / output).unlink(missing_ok=True)
    observed = packet["failure_observability"][
        "component_analyst_input_binding_mismatch_v1"
    ]
    assert observed == diagnostic
    assert packet["sanitized_projection_summaries"][
        "component_analyst_input_binding_mismatch_v1"
    ] == diagnostic
    assert packet["failure_summary"]["safe_error_type"] == (
        "MulticomponentComponentAdmissionError"
    )
    assert packet["failure_summary"]["safe_error_message"] == (
        COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH
    )
    _assert_no_canaries(packet)
    support.reject_forbidden_packet(packet)


def test_conservative_classification_does_not_guess_supplied_or_artifact_change() -> None:
    original = _packet()
    supplied = deepcopy(original)
    supplied["quantitative_source_catalog"] = {
        **deepcopy(original["quantitative_source_catalog"]),
        "catalog_kind": "tampered",
    }
    diagnostic = _diagnostic_from(
        analyst_input=supplied,
        artifact=_artifact(original, input_packet_digest="0" * 64),
    )
    assert diagnostic["mismatch_class"] == "OTHER"
    assert diagnostic["independent_dispatch_digest_present"] is False
    assert diagnostic["supplied_digest_equals_dispatch"] is None
    assert diagnostic["artifact_digest_equals_dispatch"] is None


def test_independent_dispatch_digest_can_prove_supplied_packet_changed() -> None:
    original = _packet()
    supplied = deepcopy(original)
    supplied["quantitative_source_catalog"] = {
        **deepcopy(original["quantitative_source_catalog"]),
        "catalog_kind": "tampered",
    }
    original_digest = safe_packet_digest(original)
    diagnostic = _diagnostic_from(
        analyst_input=supplied,
        artifact=_artifact(original, input_packet_digest="0" * 64),
        independent_dispatch_input_digest=original_digest,
    )
    assert diagnostic["mismatch_class"] == "SUPPLIED_PACKET_CHANGED"
    assert diagnostic["independent_dispatch_digest_present"] is True
    assert diagnostic["supplied_digest_equals_dispatch"] is False
    assert diagnostic["artifact_digest_equals_dispatch"] is False


def test_independent_dispatch_digest_can_prove_artifact_digest_changed() -> None:
    packet = _packet()
    packet_digest = safe_packet_digest(packet)
    diagnostic = _diagnostic_from(
        analyst_input=packet,
        artifact=_artifact(packet, input_packet_digest="0" * 64),
        independent_dispatch_input_digest=packet_digest,
    )
    assert diagnostic["mismatch_class"] == "ARTIFACT_DIGEST_CHANGED"
    assert diagnostic["first_divergent_section"] == "unknown"
    assert diagnostic["supplied_digest_equals_reconstructed"] is True
    assert diagnostic["supplied_digest_equals_dispatch"] is True
    assert diagnostic["artifact_digest_equals_dispatch"] is False
    _assert_digest_only(diagnostic)


def test_dispatch_digest_precedes_run_binding_authority_claim() -> None:
    accepted = _accepted_contract()
    original = _packet(accepted)
    supplied = deepcopy(original)
    supplied["run_binding"] = {
        **deepcopy(original["run_binding"]),
        "accepted_contract_version": "0.1-claim-a",
        "accepted_contract_digest": _DIGEST_A,
    }
    diagnostic = _diagnostic_from(
        accepted=accepted,
        analyst_input=supplied,
        artifact=_artifact(supplied),
        independent_dispatch_input_digest=safe_packet_digest(original),
    )
    assert diagnostic["mismatch_class"] == "SUPPLIED_PACKET_CHANGED"
    assert diagnostic["first_divergent_section"] == "run_binding"
    assert diagnostic["supplied_digest_equals_dispatch"] is False
    assert diagnostic["run_binding_matches_accepted_contract"] is False
    _assert_digest_only(diagnostic)


def test_component_ref_difference_is_other_not_reconstruction() -> None:
    accepted_ref = _component_ref()
    packet_ref = {**accepted_ref, "user_facing_label": "packet-only-label"}
    accepted = _accepted_contract(component_ref=accepted_ref)
    supplied = _packet(accepted, component_ref=packet_ref)
    diagnostic = _diagnostic_from(
        accepted=accepted,
        analyst_input=supplied,
        artifact=_artifact(supplied),
    )
    assert diagnostic["first_divergent_section"] == "component_ref"
    assert diagnostic["mismatch_class"] == "OTHER"
    assert diagnostic["supplied_digest_equals_artifact"] is True
    assert diagnostic["run_binding_matches_accepted_contract"] is True
    assert diagnostic["component_ref_equal"] is False
    _assert_digest_only(diagnostic)


def test_true_reconstruction_non_idempotent_for_derived_catalog() -> None:
    original = _packet()
    supplied = deepcopy(original)
    supplied["quantitative_source_catalog"] = {
        **deepcopy(original["quantitative_source_catalog"]),
        "catalog_kind": "tampered",
    }
    supplied_digest = safe_packet_digest(supplied)
    diagnostic = _diagnostic_from(
        analyst_input=supplied,
        artifact=_artifact(supplied),
        independent_dispatch_input_digest=supplied_digest,
    )
    assert diagnostic["mismatch_class"] == "PACKET_RECONSTRUCTION_NON_IDEMPOTENT"
    assert diagnostic["first_divergent_section"] == "quantitative_source_catalog"
    assert diagnostic["supplied_digest_equals_artifact"] is True
    assert diagnostic["supplied_digest_equals_dispatch"] is True
    assert diagnostic["run_binding_equal"] is True
    assert diagnostic["component_ref_equal"] is True
    assert diagnostic["component_evidence_equal"] is True
    assert diagnostic["quantitative_source_catalog_equal"] is False
    _assert_digest_only(diagnostic)


def test_contract_authority_changed_is_mechanically_proven() -> None:
    initial = _accepted_contract()
    packet = _packet(initial)
    current = _accepted_contract(version="0.2-current", digest=_DIGEST_CURRENT)
    diagnostic = _diagnostic_from(
        accepted=current,
        analyst_input=packet,
        artifact=_artifact(packet),
        contract_authority_facts={
            "initial_contract_present": True,
            "initial_contract_version": "0.1-passive",
            "initial_contract_digest": _DIGEST_B,
            "current_contract_present": True,
            "current_contract_version": "0.2-current",
            "current_contract_digest": _DIGEST_CURRENT,
            "accepted_authority_source": "current",
        },
    )
    assert diagnostic["mismatch_class"] == "CONTRACT_AUTHORITY_CHANGED"
    assert diagnostic["first_divergent_section"] == "run_binding"
    assert diagnostic["run_binding_matches_accepted_contract"] is False
    assert diagnostic["current_contract_present"] is True
    assert diagnostic["accepted_authority_source"] == "current"
    _assert_digest_only(diagnostic)


def test_initial_and_current_authority_facts_are_truthful_without_policy_change() -> None:
    packet = _packet()
    supplied = deepcopy(packet)
    supplied["quantitative_source_catalog"] = {
        **deepcopy(packet["quantitative_source_catalog"]),
        "catalog_kind": "tampered",
    }
    initial_only = _diagnostic_from(
        analyst_input=supplied,
        artifact=_artifact(packet, input_packet_digest="0" * 64),
        contract_authority_facts={
            "initial_contract_present": True,
            "initial_contract_version": "0.1-passive",
            "initial_contract_digest": _DIGEST_B,
            "current_contract_present": False,
            "accepted_authority_source": "initial_fallback",
        },
    )
    assert initial_only["initial_contract_present"] is True
    assert initial_only["current_contract_present"] is False
    assert initial_only["accepted_authority_source"] == "initial_fallback"
    assert initial_only["initial_contract_version"] == "0.1-passive"
    assert initial_only["initial_contract_digest"] == _DIGEST_B
    assert initial_only["mismatch_class"] == "OTHER"

    current_present = _diagnostic_from(
        analyst_input=supplied,
        artifact=_artifact(packet, input_packet_digest="0" * 64),
        contract_authority_facts={
            "initial_contract_present": True,
            "initial_contract_version": "0.1-passive",
            "initial_contract_digest": _DIGEST_B,
            "current_contract_present": True,
            "current_contract_version": "0.2-current",
            "current_contract_digest": _DIGEST_CURRENT,
            "accepted_authority_source": "current",
        },
    )
    assert current_present["current_contract_present"] is True
    assert current_present["current_contract_version"] == "0.2-current"
    assert current_present["current_contract_digest"] == _DIGEST_CURRENT
    assert current_present["accepted_authority_source"] == "current"
    assert current_present["mismatch_class"] == "OTHER"
    kernel = SimpleNamespace(
        state=SimpleNamespace(
            current_answer_contract={"accepted_contract_version": "0.2-current"},
            initial_answer_contract={"accepted_contract_version": "0.1-passive"},
            projections={},
        )
    )
    facts = contract_authority_facts_from_run_kernel(kernel)
    assert facts["accepted_authority_source"] == "current"
    assert facts["current_contract_present"] is True
    assert independent_component_analyst_dispatch_input_digest(
        kernel, evaluation_key="component:1"
    ) is None


def test_searchos_n1_success_path_keeps_identical_a_g_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import ordinary_multicomponent_synthesis_runtime as multicomponent
    from core.multicomponent_graph_scheduling import MULTICOMPONENT_SCHEDULER_STAGE
    from core.run_kernel import RunKernel
    from tests.helpers.offline_ordinary_pipeline import (
        run_post_retirement_ordinary_pipeline,
    )

    scheduler_packets: list[dict[str, Any]] = []
    original_packet_install = RunKernel.install_multicomponent_graph_reproof_packet_context

    def capture_packet_install(self: Any, **kwargs: Any) -> Any:
        result = original_packet_install(self, **kwargs)
        packets = {
            str(key): dict(value)
            for key, value in kwargs["component_analyst_input_packets"].items()
        }
        scheduler_packets.append(packets)
        return result

    monkeypatch.setattr(
        RunKernel,
        "install_multicomponent_graph_reproof_packet_context",
        capture_packet_install,
    )
    captured: dict[str, Any] = {}
    original_execute = multicomponent.execute_multicomponent_component_admission

    def capture_execute(**kwargs: Any) -> Any:
        captured["analyst_input_packet"] = deepcopy(kwargs["analyst_input_packet"])
        captured["analyst_artifact"] = deepcopy(kwargs["analyst_artifact"])
        captured["mismatch"] = None
        try:
            return original_execute(**kwargs)
        except MulticomponentComponentAdmissionError as exc:
            captured["mismatch"] = getattr(
                exc, "component_analyst_input_binding_mismatch_v1", None
            )
            raise

    monkeypatch.setattr(
        multicomponent,
        "execute_multicomponent_component_admission",
        capture_execute,
    )
    _establish_official_current_qualification_truth(monkeypatch)
    outcome, harness = run_post_retirement_ordinary_pipeline(
        tmp_path,
        monkeypatch,
        mode="Balanced",
        query="What is Alpha's current official operating rule?",
        core_topic="Alpha current official operating rule",
        primary_entity="Alpha",
        researcher_queries=["Alpha current official operating rule"],
        raw_author_response=(
            "Alpha's current official operating rule is supported. "
            "[[1]](https://alpha.example/report-1)"
        ),
    )

    assert captured["mismatch"] is None
    assert len(scheduler_packets) == 1
    [dispatch_packet] = scheduler_packets[0].values()
    supplied = captured["analyst_input_packet"]
    artifact = captured["analyst_artifact"]
    accepted = (
        harness.run_kernel.state.current_answer_contract
        or harness.run_kernel.state.initial_answer_contract
    )
    assert harness.run_kernel.state.current_answer_contract in (None, {})
    reconstructed = component_analyst_input_packet(
        run_id=harness.run_kernel.state.run_id,
        request_id=harness.run_kernel.state.request_id,
        accepted_contract=accepted,
        component_ref=dict(accepted["accepted_answer_component_refs"][0]),
        evidence_input=dict(supplied["component_evidence"]),
    )
    digest = safe_packet_digest(dispatch_packet)
    assert safe_packet_digest(supplied) == digest
    assert safe_packet_digest(reconstructed) == digest
    assert artifact["input_packet_digest"] == digest
    assert MULTICOMPONENT_SCHEDULER_STAGE not in harness.run_kernel.state.projections
    released = harness.run_kernel.state.multicomponent_scheduler_context
    assert released.get("transient_context_released") is True
    assert released.get("component_input_packet_digests")
    rendered = json.dumps(outcome.execution_trace, sort_keys=True, default=str)
    assert "component_analyst_input_binding_mismatch_v1" not in rendered
    from core.searchos_slice_a_product_runtime import (
        build_bounded_searchos_n1_causal_projection,
    )

    projection = build_bounded_searchos_n1_causal_projection(
        searchos_slice_a_projection=dict(outcome.execution_trace["searchos_slice_a"]),
    )
    assert projection is not None
    assert projection["slots"][0]["semantic_admission_status"] == "admitted"
    assert projection["slots"][0]["component_analyst_case_present"] is True


def test_project_rejects_generic_exception_payloads() -> None:
    projected = project_component_analyst_input_binding_mismatch_v1(
        {
            "schema_version": COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION,
            "mismatch_class": "OTHER",
            "first_divergent_section": "unknown",
            "accepted_authority_source": "unknown",
            "bounded_text": CANARY_EVIDENCE,
            "__dict__": {"secret": CANARY_PROVIDER},
        }
    )
    assert projected["mismatch_class"] == "OTHER"
    assert "bounded_text" not in projected
    assert "__dict__" not in projected
    _assert_no_canaries(projected)
    assert project_component_analyst_input_binding_mismatch_v1(
        {"mismatch_class": "SUPPLIED_PACKET_CHANGED"}
    ) == {}


def _schema_valid_mismatch_payload(**digest_overrides: str) -> dict[str, Any]:
    payload = {
        "schema_version": COMPONENT_ANALYST_INPUT_BINDING_MISMATCH_SCHEMA_VERSION,
        "mismatch_class": "OTHER",
        "first_divergent_section": "unknown",
        "accepted_authority_source": "unknown",
        "artifact_input_packet_digest": _VALID_SHA256_DIGEST,
        "supplied_packet_digest": _VALID_SHA256_DIGEST,
        "reconstructed_packet_digest": _VALID_SHA256_DIGEST,
        "run_binding_supplied_digest": _VALID_SHA256_DIGEST,
        "run_binding_reconstructed_digest": _VALID_SHA256_DIGEST,
        "run_binding_equal": True,
    }
    payload.update(digest_overrides)
    return payload


def test_allowlisted_digest_fields_reject_private_and_malformed_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_payload = _schema_valid_mismatch_payload(
        artifact_input_packet_digest="CANARY_PRIVATE_DIGEST_VALUE",
        supplied_packet_digest="CANARY_PRIVATE_SUPPLIED_VALUE",
        run_binding_supplied_digest="CANARY_PRIVATE_SECTION_VALUE",
        reconstructed_packet_digest="not-hex",
        packet_contract_digest="",
        accepted_component_digest="abc",
        independent_dispatch_input_digest="g" * 64,
        quantitative_source_catalog_supplied_digest=_VALID_SHA256_DIGEST + "aa",
    )
    projected = project_component_analyst_input_binding_mismatch_v1(private_payload)
    assert projected["mismatch_class"] == "OTHER"
    assert projected["artifact_input_packet_digest"] is None
    assert projected["supplied_packet_digest"] is None
    assert projected["run_binding_supplied_digest"] is None
    assert projected["reconstructed_packet_digest"] is None
    assert projected["packet_contract_digest"] is None
    assert projected["accepted_component_digest"] is None
    assert projected["independent_dispatch_input_digest"] is None
    assert projected["quantitative_source_catalog_supplied_digest"] is None
    for canary in _DIGEST_FIELD_CANARIES:
        assert canary not in json.dumps(projected, sort_keys=True)

    valid = project_component_analyst_input_binding_mismatch_v1(
        _schema_valid_mismatch_payload(
            artifact_input_packet_digest=_VALID_SHA256_DIGEST,
            supplied_packet_digest=_UPPER_SHA256_DIGEST,
        )
    )
    assert valid["artifact_input_packet_digest"] == _VALID_SHA256_DIGEST
    assert valid["supplied_packet_digest"] == _UPPER_SHA256_DIGEST.lower()

    runner = _load_runner()
    support = _load_support()
    output = "output/ca_admission_mismatch_obs_01_digest_canary.json"
    _stub_live_runner_without_env(runner, monkeypatch)
    exc = MulticomponentComponentAdmissionError(
        COMPONENT_ANALYST_EXACT_INPUT_BINDING_MISMATCH,
        component_analyst_input_binding_mismatch_v1=private_payload,
    )
    assert exc.component_analyst_input_binding_mismatch_v1 is not None
    for canary in _DIGEST_FIELD_CANARIES:
        assert canary not in json.dumps(
            exc.component_analyst_input_binding_mismatch_v1, sort_keys=True
        )

    def fail_run_pipeline(
        _config: Any,
        _deps: Any,
        _status: Any,
        _accumulator: Any,
    ) -> Any:
        raise exc

    with patch(
        "core.pipeline_orchestrator.run_pipeline",
        side_effect=fail_run_pipeline,
    ):
        result = runner.main(
            [*VALID_ARGS, "--output", output, "--confirm-live-product-run"]
        )

    assert result == 2
    capsys.readouterr()
    packet = json.loads((ROOT / output).read_text(encoding="utf-8"))
    (ROOT / output).unlink(missing_ok=True)
    rendered = json.dumps(packet, sort_keys=True)
    for canary in _DIGEST_FIELD_CANARIES:
        assert canary not in rendered
    support.reject_forbidden_packet(packet)
