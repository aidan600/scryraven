"""VALIDATION-REGRESSION: quantitative parser diagnostics.

Proof class: offline_product_path_proof.
Validation bucket: phase_focus.
Surface guarded: the retained quantitative prose evaluator and proof that its
observations have no accepted-prose PRODUCT authority.
High-custody surface: evaluator diagnostics and the pre-Author FAP boundary;
follow-up wiring, acquisition, proposal contracts, QMR, Economist,
provider/model, and retry behavior remain closed this phase.
Runtime/product path guarded: AuthorExecutor, deterministic AuthorProse, and
the AF5B compatibility surface, using bounded offline fixtures only.
Expected cost: a focused offline matrix under two minutes.
Promotion posture: remain phase_focus; the detailed parser/caller matrix is not
ordinary fast_pr tax.
Demotion/retirement condition: replace only if the evaluator or all three
boundary sentinels are retired behind an equivalent smaller proof.
Why not fast_pr: this is exhaustive high-custody evaluator and boundary detail.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import core.pipeline_orchestrator as orchestrator
from core.author_execution_runtime import execute_author_action
from core.cost_accounting import CostAccumulator
from core.final_answer_packet import FinalAnswerAuthorInputPayload
from core.protocols import NullStatusWriter
from core.quantitative_finalization_authority import (
    build_quantitative_finalization_authority_manifest,
    evaluate_author_output_quantitative_authority,
    extract_quantitative_literals,
    semantic_claim_fingerprint,
    validate_author_output_quantitative_authority,
)
from core.run_kernel import (
    AUTHOR_EXECUTION_STAGE,
    ActionType,
    AuthorizedAction,
    ObservationType,
)
from core.sufficiency_readiness_runtime import reduce_sufficiency_readiness
from tests.helpers.offline_ordinary_pipeline import (
    HANDOFF_AUTHOR,
    HANDOFF_PACKET,
    OfflineOrdinaryPipelineHarness,
    install_handoff_capture,
    offline_balanced_run_config,
    scrub_offline_runtime,
)
from tests.test_ag96i3af5b_author_response_finalization import (
    _consume_af5a_with_text,
    _kernel_through_af4d,
)
from tests.test_hardened_quantitative_authority_parity_01 import (
    _assert_fap_blocks_before_author,
    _numeric_chain,
    _reduce_hardened_route,
    _source_authority_material,
)
from tests.test_s1_quantitative_finalization_containment_01 import (
    _accept,
    _reject,
    _source_bundle,
)

REPRESENTATIVE_REJECTIONS = (
    (
        "source_section_assertion",
        "Sources:\n- The unsupported difference is 200 km.",
    ),
    ("compact_currency", "The unsupported fee is USD100."),
    ("bracketed_value", "The unsupported difference is [200] km."),
    ("hyphenated_cardinal", "The unsupported count is twenty-one."),
    ("unicode_fraction", "The unsupported share is ½."),
    ("fullwidth_digits", "The unsupported span is ２００ km."),
    ("digest_shaped_decimal", "The unsupported total is (12345678)."),
    ("numbered_looking_value", "200) km is the unsupported difference."),
    ("accounting_parentheses", "Net income was ($100)."),
    ("compact_currency_rate", "The unsupported rate is USD100/kg."),
    ("superscript_surface", "The unsupported area is 10 m²."),
    (
        "ambiguous_reference_row",
        "Sources:\n- NASA report distance 200 km.",
    ),
    ("reference_row_usd", "Sources:\n- Report USD100."),
    ("reference_row_eur", "Sources:\n- Memo EUR25.50."),
    ("reference_row_gbp", "Citations:\n- Publication GBP40."),
    ("word_ordinal", "The unsupported rank is first."),
)


def _empty_bundle() -> dict[str, Any]:
    return {
        "manifest": build_quantitative_finalization_authority_manifest(
            source_fap_ref={"packet_id": "parser-fail-closed-empty"}
        )
    }


@pytest.mark.parametrize(
    ("candidate", "expected_kind", "expected_value", "expected_unit"),
    (
        (
            "Sources:\n- The unsupported difference is 200 km.",
            "exact",
            "200",
            "km",
        ),
        ("The unsupported fee is USD100.", "exact", "100", "USD"),
        ("The unsupported fee is EUR25.50.", "exact", "25.5", "EUR"),
        ("The unsupported rate is USD100/kg.", "exact", "100", "USD_per_kg"),
        ("The unsupported rate is EUR25.50/day.", "exact", "25.5", "EUR_per_day"),
        ("The unsupported rate is GBP40/hour.", "exact", "40", "GBP_per_hour"),
        ("Sources:\n- Report USD100.", "exact", "100", "USD"),
        ("Sources:\n- Memo EUR25.50.", "exact", "25.5", "EUR"),
        ("Citations:\n- Publication GBP40.", "exact", "40", "GBP"),
        ("The unsupported difference is [200] km.", "exact", "200", "km"),
        ("The unsupported count is twenty-one.", "exact", "21", "dimensionless"),
        ("The unsupported rank is 21st.", "unsupported", None, None),
        ("The unsupported share is ½.", "unsupported", None, None),
        ("The unsupported span is ２００ km.", "unsupported", None, None),
        ("The unsupported rank is first.", "unsupported", None, None),
        ("The unsupported rank is tenth.", "unsupported", None, None),
        ("The unsupported rank is eleventh.", "unsupported", None, None),
        ("The unsupported total is (12345678).", "exact", "12345678", "dimensionless"),
        ("200) km is the unsupported difference.", "exact", "200", "dimensionless"),
        (
            "Net income was ($100).",
            "exact",
            "-100",
            "currency_symbol:$",
        ),
    ),
)
def test_direct_parser_classifies_every_reproduced_surface(
    candidate: str,
    expected_kind: str,
    expected_value: str | None,
    expected_unit: str | None,
) -> None:
    literals = extract_quantitative_literals(candidate)

    assert len(literals) == 1
    literal = literals[0]
    if expected_kind == "unsupported":
        assert literal["unsupported_quantitative_surface"] in {
            "digit_ordinal",
            "unicode_fraction",
            "fullwidth_digits",
            "word_ordinal",
        }
        assert "normalized_numeric_value_text" not in literal
    else:
        assert literal["normalized_numeric_value_text"] == expected_value
        assert literal["canonical_unit"] == expected_unit


@pytest.mark.parametrize(
    ("candidate", "surface_kind", "exact_value", "exact_unit"),
    (
        ("The area is 10 m².", "superscript_digits", "10", "m"),
        ("The volume is 10 m³.", "superscript_digits", "10", "m"),
        ("The unsupported value is 10².", "superscript_digits", "10", "dimensionless"),
        ("The unsupported coordinate is x₂.", "subscript_digits", None, None),
    ),
)
def test_superscript_and_subscript_surfaces_are_explicitly_unsupported(
    candidate: str,
    surface_kind: str,
    exact_value: str | None,
    exact_unit: str | None,
) -> None:
    literals = extract_quantitative_literals(candidate)
    unsupported = [
        item for item in literals if item.get("unsupported_quantitative_surface")
    ]

    assert [item["unsupported_quantitative_surface"] for item in unsupported] == [
        surface_kind
    ]
    exact = [item for item in literals if item.get("normalized_numeric_value_text")]
    if exact_value is None:
        assert exact == []
    else:
        assert len(exact) == 1
        assert exact[0]["normalized_numeric_value_text"] == exact_value
        assert exact[0]["canonical_unit"] == exact_unit


@pytest.mark.parametrize(
    ("candidate", "expected_value", "expected_unit"),
    (
        ("Sources:\n- NASA report distance 200 km.", "200", "km"),
        ("Sources:\n- Report revenue USD100.", "100", "USD"),
        ("Sources: Agency publication total 25 percent.", "25", "percent"),
        ("Sources:\n- Report USD100.", "100", "USD"),
        ("Sources:\n- Memo EUR25.50.", "25.5", "EUR"),
        ("Citations:\n- Publication GBP40.", "40", "GBP"),
    ),
)
def test_ambiguous_reference_noun_rows_remain_inspectable(
    candidate: str,
    expected_value: str,
    expected_unit: str,
) -> None:
    literals = extract_quantitative_literals(candidate)
    diagnostic = _reject(candidate, _empty_bundle())

    assert len(literals) == 1
    assert literals[0]["normalized_numeric_value_text"] == expected_value
    assert literals[0]["canonical_unit"] == expected_unit
    assert diagnostic["candidate_quantitative_literal_count"] == 1
    assert diagnostic["rejection_count"] == 1


def _literal_signature_projection(text: str) -> tuple[tuple[str, ...], ...]:
    fields = (
        "unsupported_quantitative_surface",
        "normalized_numeric_value_text",
        "canonical_unit",
        "precision_posture",
        "scale_posture",
        "sign_posture",
        "percent_convention",
        "notation_posture",
    )
    return tuple(
        sorted(
            tuple(str(item.get(field) or "") for field in fields)
            for item in extract_quantitative_literals(text)
        )
    )


def test_superscript_authority_and_plain_unit_do_not_collapse() -> None:
    superscript = "The area is 10 m²."
    plain = "The area is 10 m."

    _reject(plain, _source_bundle(superscript))
    _reject(superscript, _source_bundle(plain))
    assert semantic_claim_fingerprint(superscript) != semantic_claim_fingerprint(plain)
    assert _literal_signature_projection(superscript) != _literal_signature_projection(plain)


@pytest.mark.parametrize(("label", "candidate"), REPRESENTATIVE_REJECTIONS)
def test_every_reproduced_surface_fails_closed_instead_of_accepting_zero_candidates(
    label: str,
    candidate: str,
) -> None:
    diagnostic = _reject(candidate, _empty_bundle())

    assert diagnostic["candidate_quantitative_literal_count"] >= 1, label
    assert diagnostic["rejection_count"] >= 1


def test_source_section_nonreference_numeric_row_without_copula_fails_closed() -> None:
    diagnostic = _reject("Sources:\n- Revenue USD100.", _empty_bundle())

    assert diagnostic["candidate_quantitative_literal_count"] == 1
    assert diagnostic["rejection_count"] == 1


@pytest.mark.parametrize(
    ("source_claim", "candidate"),
    (
        ("The direct count is 17.", "The direct count is 17."),
        ("The measured mass is 3.50 kg.", "The measured mass is 3.50 kg."),
        ("The supported share is 25 percent.", "The supported share is 25 percent."),
        ("The date is 2026-07-14.", "The date is 2026-07-14."),
        ("The service uses port 443.", "The service uses port 443."),
        ("The schema version is 2.3.", "The schema version is 2.3."),
        ("The diameter is 1,000 km.", "The diameter is 1000 km."),
        ("The supported fee is USD100.", "The supported fee is USD100."),
        ("The supported fee is EUR25.50.", "The supported fee is EUR25.50."),
        ("The supported rate is USD100/kg.", "The supported rate is USD100/kg."),
        ("The supported rate is EUR25.50/day.", "The supported rate is EUR25.50/day."),
        ("The supported rate is GBP40/hour.", "The supported rate is GBP40/hour."),
        ("The supported count is twenty-one.", "The supported count is twenty-one."),
        ("The supported difference is [200] km.", "The supported difference is [200] km."),
        ("200 km is the supported difference.", "200 km is the supported difference."),
    ),
)
def test_exact_supported_numeric_controls_remain_accepted(
    source_claim: str,
    candidate: str,
) -> None:
    accepted = _accept(candidate, _source_bundle(source_claim))

    assert accepted["status"] == "accepted"
    assert accepted["candidate_quantitative_literal_count"] >= 1


@pytest.mark.parametrize(
    "candidate",
    (
        "See https://example.test/2026/v1.2/1000.",
        "The qualitative conclusion is supported [1].",
        "The qualitative conclusion follows from evidence of [1].",
        (
            "Support refs:\n- https://example.test/2026/v1.2/1000\n"
            "- AF5B-ref-77\n- sha256:0123456789abcdef"
        ),
        "Digest (deadbeef) identifies the packet.",
        "Digest (12345678) identifies the packet.",
        "The nonfactual identifier is AF5B-ref-77.",
        "Sources:\n- Official report 2026\n- Example Program reference 17",
        "1. Qualitative evidence supports the claim.\n2) Additional context agrees.",
        "First, consider the qualitative evidence.",
    ),
)
def test_transport_and_structural_list_controls_remain_nonquantitative(
    candidate: str,
) -> None:
    accepted = validate_author_output_quantitative_authority(
        candidate,
        manifest=_empty_bundle()["manifest"],
    )

    assert accepted["status"] == "accepted"
    assert accepted["candidate_quantitative_literal_count"] == 0


def test_accounting_parentheses_preserve_negative_sign_posture() -> None:
    positive = _source_bundle("Net income was $100.")
    accounting_negative = _source_bundle("Net income was ($100).")
    accounting_code_negative = _source_bundle("Net income was (USD 100).")
    explicit_negative = _source_bundle("Net income was -$100.")

    _reject("Net income was ($100).", positive)
    assert _accept("Net income was ($100).", accounting_negative)["status"] == (
        "accepted"
    )
    _reject("Net income was $100.", accounting_negative)
    _reject("Net income was ($100).", _empty_bundle())
    assert _accept("Net income was (USD 100).", accounting_code_negative)[
        "status"
    ] == "accepted"
    assert _accept("Net income was −$100.", explicit_negative)["status"] == (
        "accepted"
    )
    _reject("Net income was ($100).", explicit_negative)

    explanatory = _source_bundle("The span was (100 km) as reported.")
    literal = extract_quantitative_literals("The span was (100 km) as reported.")[0]
    assert literal["sign_posture"] == "implicit_positive"
    assert _accept("The span was (100 km) as reported.", explanatory)["status"] == (
        "accepted"
    )


def test_ordinary_author_executor_keeps_accounting_sign_diagnostic_non_authoritative() -> None:
    manifest = _source_bundle("Net income was $100.")["manifest"]
    payload = FinalAnswerAuthorInputPayload(
        packet_id="accounting-substitution-packet",
        prompt="Draft the answer.\nFINAL ANSWER PACKET AUTHORITY",
        author_system_prompt_key="author",
        author_effort="low",
        quantitative_finalization_authority_manifest=manifest,
    )
    action = AuthorizedAction(
        action_id="accounting-substitution-action",
        run_id="accounting-substitution-run",
        stage=AUTHOR_EXECUTION_STAGE,
        action_type=ActionType.AUTHOR_EXECUTE,
        reason="test accounting substitution",
        inputs={
            "packet_id": payload.packet_id,
            "author_system_prompt_key": payload.author_system_prompt_key,
            "author_effort": payload.author_effort,
        },
        expected_observation_type=ObservationType.AUTHOR_OUTPUT_OBSERVED,
        sequence=1,
    )
    calls = 0
    displayed: list[str] = []

    def ask_model(*_args: Any, **_kwargs: Any) -> list[str]:
        nonlocal calls
        calls += 1
        return ["Net income was ($100)."]

    result = execute_author_action(
        action,
        author_payload=payload,
        ask_model=ask_model,
        system_prompt_registry={"author": "Render only supported claims."},
        base_url=None,
        api_key=None,
        query="What was net income?",
        stream_display=lambda chunks: displayed.extend(chunks),
    )

    assert calls == 1
    assert displayed == ["Net income was ($100)."]
    assert result.report == "Net income was ($100)."
    assert result.observation.payload["post_author_quantitative_semantic_gate_active"] is False
    diagnostic = evaluate_author_output_quantitative_authority(
        result.report,
        manifest=manifest,
    )
    assert diagnostic["status"] == "rejected"
    assert result.report == "Net income was ($100)."


class _RejectedOrdinaryAuthorHarness(OfflineOrdinaryPipelineHarness):
    def __init__(self, *, tmp_path: Path, candidate: str) -> None:
        super().__init__(
            tmp_path=tmp_path,
            query="What qualitative conclusion does the official evidence support?",
            core_topic="Example Program qualitative conclusion",
            primary_entity="Example Program",
            raw_author_response=candidate,
            analyst_response="The official evidence supports a qualitative conclusion.",
            logger_name="test_quantitative_finalization_parser_fail_closed_01",
        )

    def build_search_passages(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": "official-a",
                "title": "Example Program official rule",
                "url": "https://official.example/rule",
                "text": "The official rule supports the qualitative conclusion.",
                "score": 0.99,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "_provider": "offline_fake_search",
            },
            {
                "source_id": "official-b",
                "title": "Example Program official memo",
                "url": "https://official.example/memo",
                "text": "The official memo confirms the qualitative conclusion.",
                "score": 0.97,
                "credibility": 4,
                "source_tier": "official",
                "source_class": "official_current_rules",
                "_provider": "offline_fake_search",
            },
        ]


def test_pre_author_fap_block_does_not_depend_on_evaluator_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label, candidate = REPRESENTATIVE_REJECTIONS[0]
    scrub_offline_runtime(monkeypatch)
    harness = _RejectedOrdinaryAuthorHarness(tmp_path=tmp_path, candidate=candidate)
    captured = install_handoff_capture(
        monkeypatch,
        capture_stages=(HANDOFF_PACKET, HANDOFF_AUTHOR),
    )
    displayed: list[str] = []
    config = replace(
        offline_balanced_run_config(
            query=harness.query,
            current_date="2026-07-15",
            session_id=f"parser-fail-closed-{label}",
            run_id=f"parser-fail-closed-{label}",
        ),
        author_stream_display=lambda chunks: displayed.extend(chunks),
    )

    outcome = orchestrator.run_pipeline(
        config,
        harness.deps(),
        NullStatusWriter(),
        CostAccumulator(),
    )

    kernel = captured["run_kernel"]
    outcome_before_evaluation = dict(kernel.state.final_answer_outcome)
    diagnostic = evaluate_author_output_quantitative_authority(
        candidate,
        manifest=_empty_bundle()["manifest"],
    )
    assert diagnostic["status"] == "rejected"
    assert diagnostic["candidate_quantitative_literal_count"] >= 1, label
    assert displayed == []
    assert kernel.state.final_answer_outcome == outcome_before_evaluation
    assert outcome.report.startswith("ScryRaven could not produce a supported answer.")
    assert captured["author_handoff_called"] is False
    assert len(harness.author_prompts) == 0
    assert candidate not in repr(diagnostic)


@pytest.mark.parametrize(
    ("label", "candidate"),
    tuple(
        item
        for item in REPRESENTATIVE_REJECTIONS
        if any(character.isdigit() for character in item[1])
    ),
)
def test_deterministic_author_prose_is_blocked_at_fap_before_state_or_projection_creation(
    label: str,
    candidate: str,
) -> None:
    chain = _numeric_chain(
        bounded_source_text="The source supports only a qualitative conclusion.",
        safe_claim=candidate,
    )
    reduce_sufficiency_readiness(run_kernel=chain["kernel"])
    _assert_fap_blocks_before_author(chain)
    assert chain["kernel"].state.final_answer_outcome == {}, label


@pytest.mark.parametrize(
    ("label", "candidate"),
    (
        ("hyphenated_cardinal", "The unsupported count is twenty-one."),
        ("unicode_fraction", "The unsupported share is ½."),
        ("word_ordinal", "The unsupported rank is first."),
    ),
)
def test_fap_does_not_block_admitted_word_only_quantifiers_as_a_prose_gate(
    label: str,
    candidate: str,
) -> None:
    chain = _numeric_chain(
        bounded_source_text="The source supports only a qualitative conclusion.",
        safe_claim=candidate,
    )
    _, fap, author = _reduce_hardened_route(chain)
    assert author["answer_text"]
    diagnostic = evaluate_author_output_quantitative_authority(
        candidate,
        manifest=fap["quantitative_finalization_authority_manifest"],
    )
    assert diagnostic["status"] == "rejected", label


def test_author_prose_blocks_accounting_sign_substitution_before_authority_projection() -> (
    None
):
    source_claim = "Net income was $100."
    chain = _numeric_chain(
        bounded_source_text=source_claim,
        safe_claim="Net income was ($100).",
    )
    source_material = _source_authority_material(
        chain,
        source_proposition=source_claim,
    )
    reduce_sufficiency_readiness(
        run_kernel=chain["kernel"],
        quantitative_source_authority_materials=(source_material,),
    )
    _assert_fap_blocks_before_author(chain)


def test_author_prose_accepts_accounting_parentheses_with_valid_negative_authority() -> (
    None
):
    source_claim = "Net income was ($100)."
    chain = _numeric_chain(
        bounded_source_text=source_claim,
        safe_claim=source_claim,
    )
    source_material = _source_authority_material(
        chain,
        source_proposition=source_claim,
    )

    _, fap, author = _reduce_hardened_route(
        chain,
        source_materials=(source_material,),
    )

    rows = fap["quantitative_finalization_authority_manifest"][
        "authorized_numeric_claims"
    ]
    assert "direct_source_numeric" not in {row["authority_kind"] for row in rows}
    assert author["post_author_quantitative_semantic_gate_active"] is False
    diagnostic = evaluate_author_output_quantitative_authority(
        author["answer_text"],
        manifest=fap["quantitative_finalization_authority_manifest"],
    )
    assert diagnostic["status"] == "rejected"
    assert source_claim in author["answer_text"]


@pytest.mark.parametrize(("label", "candidate"), REPRESENTATIVE_REJECTIONS)
def test_af5b_keeps_evaluator_rejections_out_of_final_answer_authority(
    label: str,
    candidate: str,
) -> None:
    kernel = _kernel_through_af4d()
    _consume_af5a_with_text(kernel, candidate)

    action = kernel.authorize_followup_author_response_finalization()
    from tests.test_ag96i3af5b_author_response_finalization import _execute_af5b

    result = _execute_af5b(kernel, action=action)
    kernel.reduce(result.observation)

    answer_before_evaluation = dict(kernel.state.final_answer_outcome)
    diagnostic = evaluate_author_output_quantitative_authority(
        candidate,
        manifest=_empty_bundle()["manifest"],
    )
    assert diagnostic["status"] == "rejected", label
    assert kernel.state.followup_author_response_finalization_state
    normalized_candidate = " ".join(candidate.split())
    assert kernel.state.author_observation["final_answer_text"] == normalized_candidate
    assert kernel.state.final_answer_outcome["final_answer_text"] == normalized_candidate
    assert kernel.state.final_answer_outcome == answer_before_evaluation


@pytest.mark.parametrize(
    "private_candidate",
    (
        "PRIVATE-FRACTION-SENTINEL share is ½.",
        "PRIVATE-RATE-SENTINEL rate is USD100/kg.",
        "PRIVATE-SUPERSCRIPT-SENTINEL area is 10 m².",
        "Sources:\n- PRIVATE-REFERENCE-SENTINEL report distance 200 km.",
        "Sources:\n- Report USD100.\n- PRIVATE-SOURCE-ROW-SENTINEL qualitative context.",
        "PRIVATE-ORDINAL-SENTINEL rank is first.",
    ),
)
def test_rejection_diagnostics_retain_only_bounded_markers_and_digests(
    private_candidate: str,
) -> None:
    private_marker = next(
        token for token in private_candidate.split() if token.startswith("PRIVATE-")
    )

    diagnostic = _reject(private_candidate, _empty_bundle())
    retained = repr(diagnostic)

    assert private_marker not in retained
    assert private_candidate not in retained
    assert diagnostic["answer_rewritten"] is False
    assert diagnostic["answer_fragment_deleted"] is False
    assert diagnostic["author_retry_requested"] is False
    assert diagnostic["final_text_included"] is False
