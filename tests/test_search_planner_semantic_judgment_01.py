"""Phase-focus proof for provider-neutral SearchPlanner semantic judgment.

Proof class: CONTRACT-INVARIANT with sanitized semantic counterexamples.
Surface guarded: teacher-free two-pass MET/NOT_MET/REVIEW_REQUIRED contract.
Closed surface: provider/model selection and live calls remain absent.
Expected cost: tiny deterministic fake-adapter proof. Promotion posture:
phase_focus until a semantic-evaluation lane is explicitly installed.
"""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from scripts.evaluation.search_planner_semantic_judgment import (
    EssentialRequirement,
    RequirementMapping,
    ScriptedSemanticJudgeAdapter,
    SemanticAmbiguity,
    SemanticIssue,
    SemanticJudgmentContractError,
    SemanticPassJudgment,
    build_semantic_judgment_request,
)

COUNTEREXAMPLES = (
    (
        "CE01",
        "same meaning with different component IDs",
        "MET",
        "Equivalent components use unrelated local IDs while preserving facts and edges.",
    ),
    (
        "CE02",
        "same meaning with different labels and wording",
        "MET",
        "Paraphrased labels preserve facts, support posture, and answer capability.",
    ),
    (
        "CE03",
        "same graph with harmless order changes",
        "MET",
        "Permuted arrays preserve normalized topology and primary bindings.",
    ),
    (
        "CE04",
        "plausible alternative query decomposition",
        "REVIEW_REQUIRED",
        "A separate entity-record lookup may be useful or redundant.",
    ),
    (
        "CE05",
        "plausible combined premise decomposition",
        "REVIEW_REQUIRED",
        "Combined acquisition may preserve meaning or hide independent lineage.",
    ),
    (
        "CE06",
        "flattened graph skipping required intermediate",
        "NOT_MET",
        "The required reconstructed class is omitted from the answer path.",
    ),
    (
        "CE07",
        "missing premise",
        "NOT_MET",
        "The material regional flag is absent.",
    ),
    (
        "CE08",
        "missing dependency",
        "NOT_MET",
        "The regional fact exists but its necessary target edge is absent.",
    ),
    (
        "CE09",
        "invented premise",
        "NOT_MET",
        "An unrequested ownership premise changes the answer path.",
    ),
    (
        "CE10",
        "valid structure with incorrect semantic meaning",
        "NOT_MET",
        "A lawful graph answers a tax category instead of the filing route.",
    ),
    (
        "CE11",
        "correct concepts with unsupported authority upgrade",
        "NOT_MET",
        "The plan upgrades inferred material into verified canonical fact.",
    ),
    (
        "CE12",
        "overly fragmented but still potentially usable",
        "REVIEW_REQUIRED",
        "Fragmentation may be redundant or may preserve independently auditable support.",
    ),
    (
        "CE13",
        "superficially similar plan that cannot answer",
        "NOT_MET",
        "Vocabulary overlaps, but contact details cannot answer the requested route.",
    ),
)


def _request(
    *,
    proposal: dict[str, object] | None = None,
    mechanical: str = "PASS",
    diagnostic: bool = False,
):
    proposed_plan = proposal or {
        "material": {
            "answer_capability": (
                "certificate + registry -> class; class + region -> route"
            )
        }
    }
    proposal_digest = sha256(
        json.dumps(
            proposed_plan,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    return build_semantic_judgment_request(
        normalized_user_request=(
            "Reconstruct the compliance class from certificate and registry "
            "facts, then combine it with the regional flag."
        ),
        planner_input={
            "explicit_requirements": [
                "certificate fact",
                "registry fact",
                "class intermediate",
                "regional flag",
                "filing route target",
            ]
        },
        essential_requirements=(
            EssentialRequirement(
                requirement_id="answer_capability",
                requirement_kind="ANSWER_CAPABILITY",
                normalized_requirement=(
                    "The proposal must preserve all material facts and the two-stage route derivation."
                ),
            ),
        ),
        proposed_plan=proposed_plan,
        mechanical_validation_summary={
            "result_id": f"mechanical-result:{'1' * 64}",
            "owner": "CanonicalSearchPlannerMechanicalAuthority",
            "product_proposal_digest": proposal_digest,
            "overall_posture": mechanical,
            "blocking_failure_rule_ids": ([] if mechanical == "PASS" else ["M04"]),
        },
        evaluation_budget_identity="offline-scripted-contract-proof",
        essential_architecture_constraints=(
            "RunKernel remains canonical.",
            "Planner output remains proposal-only.",
        ),
        prohibited_upgrades_or_shortcuts=(
            "Do not treat inferred support as direct evidence.",
            "Do not omit a required intermediate.",
        ),
        diagnostic_mode=diagnostic,
    )


def _judgment(status: str, explanation: str) -> SemanticPassJudgment:
    if status == "MET":
        return SemanticPassJudgment(
            status="MET",
            requirement_mappings=(
                RequirementMapping(
                    requirement_id="answer_capability",
                    proposal_paths=("/material/answer_capability",),
                    bounded_explanation=explanation,
                ),
            ),
        )
    if status == "NOT_MET":
        return SemanticPassJudgment(
            status="NOT_MET",
            issues=(
                SemanticIssue(
                    requirement_id="answer_capability",
                    issue_kind="MISINTERPRETED",
                    proposal_paths=("/material/answer_capability",),
                    answer_blocking=True,
                    bounded_explanation=explanation,
                ),
            ),
        )
    return SemanticPassJudgment(
        status="REVIEW_REQUIRED",
        ambiguities=(
            SemanticAmbiguity(
                requirement_id="answer_capability",
                precise_ambiguity=explanation,
                competing_interpretations=(
                    "The alternative preserves independently auditable meaning.",
                    "The alternative hides or duplicates a material requirement.",
                ),
                proposal_paths=("/material/answer_capability",),
                smallest_review_action=(
                    "Obtain one independent decision on whether the "
                    "alternative preserves the required relationship."
                ),
            ),
        ),
    )


@pytest.mark.parametrize(
    ("case_id", "candidate_class", "expected_status", "outline"),
    COUNTEREXAMPLES,
    ids=[item[0] for item in COUNTEREXAMPLES],
)
def test_approved_semantic_counterexample_contract_posture(
    case_id: str,
    candidate_class: str,
    expected_status: str,
    outline: str,
) -> None:
    request = _request(
        proposal={
            "material": {"answer_capability": outline},
            "counterexample_ref": case_id,
            "candidate_class": candidate_class,
        }
    )
    precommitted = _judgment(expected_status, outline)
    adapter = ScriptedSemanticJudgeAdapter(
        primary=precommitted,
        adversarial=precommitted,
    )
    result = adapter.judge(request)
    assert result.final_status == expected_status
    assert result.input_packet_digest == request.input_packet_digest
    assert result.proposal_digest == request.proposal_digest
    assert result.deterministic_result_ref == request.deterministic_result_ref
    assert result.answer_capability.status == expected_status
    assert result.requirement_findings
    assert result.bounded_evidence
    assert result.live_call_count == 0
    assert result.provider_selected is False
    assert result.model_selected is False
    assert adapter.invocation_count == 1


def test_met_requires_exact_mapping_for_every_essential_requirement() -> None:
    adapter = ScriptedSemanticJudgeAdapter(
        primary=SemanticPassJudgment(status="MET"),
        adversarial=SemanticPassJudgment(status="MET"),
    )
    with pytest.raises(
        SemanticJudgmentContractError,
        match="map every essential requirement",
    ):
        adapter.judge(_request())


def test_met_mapping_must_cite_existing_proposal_material() -> None:
    missing_path = SemanticPassJudgment(
        status="MET",
        requirement_mappings=(
            RequirementMapping(
                requirement_id="answer_capability",
                proposal_paths=("/material/missing",),
                bounded_explanation="The missing path cannot establish meaning.",
            ),
        ),
    )
    adapter = ScriptedSemanticJudgeAdapter(
        primary=missing_path,
        adversarial=missing_path,
    )
    with pytest.raises(
        SemanticJudgmentContractError,
        match="existing proposal material",
    ):
        adapter.judge(_request())


def test_not_met_requires_an_exact_known_requirement_issue() -> None:
    invalid = SemanticPassJudgment(
        status="NOT_MET",
        issues=(
            SemanticIssue(
                requirement_id="fixture_local_unknown",
                issue_kind="MISSING",
                proposal_paths=("/material/answer_capability",),
                answer_blocking=True,
                bounded_explanation="Unknown requirement.",
            ),
        ),
    )
    adapter = ScriptedSemanticJudgeAdapter(
        primary=invalid,
        adversarial=invalid,
    )
    with pytest.raises(
        SemanticJudgmentContractError,
        match="unknown requirement",
    ):
        adapter.judge(_request())


def test_review_required_needs_precise_competing_interpretations() -> None:
    invalid = SemanticPassJudgment(
        status="REVIEW_REQUIRED",
        ambiguities=(
            SemanticAmbiguity(
                requirement_id="answer_capability",
                precise_ambiguity="The decomposition may be material.",
                competing_interpretations=("only one interpretation",),
                proposal_paths=("/material/answer_capability",),
                smallest_review_action=(
                    "Obtain one independent decomposition decision."
                ),
            ),
        ),
    )
    adapter = ScriptedSemanticJudgeAdapter(
        primary=invalid,
        adversarial=invalid,
    )
    with pytest.raises(
        SemanticJudgmentContractError,
        match="competing interpretations",
    ):
        adapter.judge(_request())


def test_material_two_pass_disagreement_yields_review_required() -> None:
    adapter = ScriptedSemanticJudgeAdapter(
        primary=_judgment("MET", "All material requirements map."),
        adversarial=_judgment(
            "NOT_MET",
            "The required intermediate may be absent.",
        ),
    )
    result = adapter.judge(_request())
    assert result.final_status == "REVIEW_REQUIRED"
    assert result.requirement_mappings == ()
    assert result.issues == ()
    assert result.ambiguities[0].requirement_id == "two_pass_disagreement"


def test_mechanical_nonpass_requires_explicit_diagnostic_mode() -> None:
    with pytest.raises(
        SemanticJudgmentContractError,
        match="mechanical PASS",
    ):
        _request(mechanical="FAIL")
    request = _request(mechanical="FAIL", diagnostic=True)
    supplied = _judgment("MET", "Diagnostic meaning appears complete.")
    result = ScriptedSemanticJudgeAdapter(
        primary=supplied,
        adversarial=supplied,
    ).judge(request)
    assert result.final_status == "MET"
    assert result.diagnostic_only is True
    assert result.mechanical_posture_seen == "FAIL"


def test_teacher_answer_and_raw_material_keys_are_rejected() -> None:
    for key in (
        "teacher_answer",
        "raw_prompt",
        "full_prompt",
        "provider_payload",
        "secret",
    ):
        with pytest.raises(
            SemanticJudgmentContractError,
            match="forbidden key",
        ):
            _request(proposal={"material": {}, key: "forbidden"})


def test_scripted_adapter_has_no_provider_model_retry_or_budget_policy() -> None:
    supplied = _judgment("MET", "All material requirements map.")
    adapter = ScriptedSemanticJudgeAdapter(
        primary=supplied,
        adversarial=supplied,
    )
    for forbidden in (
        "provider",
        "model",
        "reasoning_effort",
        "token_budget",
        "retry_policy",
        "price",
    ):
        assert not hasattr(adapter, forbidden)


def test_result_packet_uses_the_approved_two_pass_contract_fields() -> None:
    supplied = _judgment("MET", "All material requirements map.")
    result = ScriptedSemanticJudgeAdapter(
        primary=supplied,
        adversarial=supplied,
    ).judge(_request())
    packet = result.to_packet()
    assert packet["judge_contract_version"]
    assert packet["final_status"] == "MET"
    assert packet["primary_judgment"]["status"] == "MET"
    assert packet["adversarial_challenge"]["status"] == "MET"
    assert {
        "contract_version",
        "status",
        "primary_pass",
        "adversarial_pass",
    }.isdisjoint(packet)


def test_same_status_with_different_proposal_evidence_requires_review() -> None:
    request = _request(
        proposal={
            "material": {
                "answer_capability": "primary evidence",
                "alternate": "materially different evidence",
            }
        }
    )
    primary = SemanticPassJudgment(
        status="MET",
        requirement_mappings=(
            RequirementMapping(
                requirement_id="answer_capability",
                proposal_paths=("/material/answer_capability",),
                bounded_explanation="The primary path carries the requirement.",
            ),
        ),
    )
    adversarial = SemanticPassJudgment(
        status="MET",
        requirement_mappings=(
            RequirementMapping(
                requirement_id="answer_capability",
                proposal_paths=("/material/alternate",),
                bounded_explanation="Only the alternate path carries the requirement.",
            ),
        ),
    )
    result = ScriptedSemanticJudgeAdapter(
        primary=primary,
        adversarial=adversarial,
    ).judge(request)
    assert result.final_status == "REVIEW_REQUIRED"
    assert set(result.ambiguities[0].proposal_paths) == {
        "/material/answer_capability",
        "/material/alternate",
    }
    assert len(
        set(result.ambiguities[0].competing_interpretations)
    ) == 2


def test_request_digest_validation_rejects_proposal_substitution() -> None:
    request = _request()
    with pytest.raises(
        SemanticJudgmentContractError,
        match="proposal digest does not cover",
    ):
        replace(request, proposal_digest="2" * 64)


def test_not_met_cannot_smuggle_a_review_ambiguity() -> None:
    issue = _judgment(
        "NOT_MET",
        "The answer path is materially incorrect.",
    ).issues
    ambiguity = _judgment(
        "REVIEW_REQUIRED",
        "Two material interpretations remain.",
    ).ambiguities
    invalid = SemanticPassJudgment(
        status="NOT_MET",
        issues=issue,
        ambiguities=ambiguity,
    )
    with pytest.raises(
        SemanticJudgmentContractError,
        match="NOT_MET requires exact issues",
    ):
        ScriptedSemanticJudgeAdapter(
            primary=invalid,
            adversarial=invalid,
        ).judge(_request())


def test_result_cannot_replace_the_primary_owner_projection() -> None:
    supplied = _judgment("MET", "All material requirements map.")
    result = ScriptedSemanticJudgeAdapter(
        primary=supplied,
        adversarial=supplied,
    ).judge(_request())
    with pytest.raises(
        SemanticJudgmentContractError,
        match="projection differs",
    ):
        replace(
            result,
            requirement_mappings=(),
        )
