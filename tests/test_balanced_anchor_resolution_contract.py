"""Balanced Anchor Resolution v1 synthetic fixture contract.

These tests intentionally validate static, abstract fixture data. They do not
import or exercise runtime anchor, router, retrieval, provider, Analyst,
Economist, or Author code.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

CORE_FORBIDDEN_BEHAVIOR_CHANGES = frozenset(
    {
        "no provider-routing change",
        "no search-depth change",
        "no query-generation change",
        "no source filtering/ranking change",
        "no Analyst skip",
        "no Economist shortcut",
        "no weak-corpus behavior change",
        "no Author-facing raw anchor dump",
        "retrieve-to-anchor remains recommendation-only",
        "no active probe",
        "no raw quantitative_packet / Economist framework / economist_v1 JSON reaches Author",
        "Fast unchanged",
        "Deep unchanged",
    }
)

SAFETY_HANDOFF_INVARIANTS = frozenset(
    {
        "no Analyst skip",
        "no Economist shortcut",
        "no Author-facing raw anchor dump",
        "no raw quantitative_packet / Economist framework / economist_v1 JSON reaches Author",
    }
)

REQUIRED_FIXTURE_CLASSES = frozenset(
    {
        "ambiguous referent",
        "wrong-domain frame",
        "recent mutable rule",
        "metric ambiguity",
        "likely non-public evidence",
        "simple evergreen negative control",
        "proxy-only evidence risk",
        "causal claim with hidden evidence risk",
        "official/recent source-class expectation",
        "bounded comparison with constraints",
    }
)

NEXT_ACTIONS = frozenset(
    {
        "proceed_single_frame",
        "preserve_multiple_frames",
        "retrieve_to_anchor",
        "ask_clarification",
    }
)


@dataclass(frozen=True)
class AnchorFixture:
    id: str
    fixture_class: str
    positive_request_shape: str
    expected_anchor_observation: str
    negative_control_request_shape: str
    forbidden_behavior_changes: frozenset[str]
    expected_next_action: str


def _fixture(
    *,
    id: str,
    fixture_class: str,
    positive_request_shape: str,
    expected_anchor_observation: str,
    negative_control_request_shape: str,
    expected_next_action: str,
) -> AnchorFixture:
    return AnchorFixture(
        id=id,
        fixture_class=fixture_class,
        positive_request_shape=positive_request_shape,
        expected_anchor_observation=expected_anchor_observation,
        negative_control_request_shape=negative_control_request_shape,
        forbidden_behavior_changes=CORE_FORBIDDEN_BEHAVIOR_CHANGES,
        expected_next_action=expected_next_action,
    )


ANCHOR_FIXTURES = (
    _fixture(
        id="ambiguous_referent",
        fixture_class="ambiguous referent",
        positive_request_shape=(
            "compare the latest rule for the service after it changed ownership"
        ),
        expected_anchor_observation=(
            "multiple plausible referents should be preserved or clarified before "
            "decomposition"
        ),
        negative_control_request_shape=(
            "compare the latest rule for the named service version and named owner"
        ),
        expected_next_action="preserve_multiple_frames",
    ),
    _fixture(
        id="wrong_domain_frame",
        fixture_class="wrong-domain frame",
        positive_request_shape=(
            "explain the current margin requirement for the product class"
        ),
        expected_anchor_observation=(
            "nearby off-domain meanings should be flagged as traps while preserving "
            "the intended domain boundary"
        ),
        negative_control_request_shape=(
            "explain the current margin requirement for the product class in the "
            "specified domain"
        ),
        expected_next_action="preserve_multiple_frames",
    ),
    _fixture(
        id="recent_mutable_rule",
        fixture_class="recent mutable rule",
        positive_request_shape=(
            "what is the current eligibility rule for this filing pathway"
        ),
        expected_anchor_observation=(
            "high freshness and official-current source expectations should be "
            "visible"
        ),
        negative_control_request_shape=(
            "define the eligibility concept for this filing pathway in general"
        ),
        expected_next_action="retrieve_to_anchor",
    ),
    _fixture(
        id="metric_ambiguity",
        fixture_class="metric ambiguity",
        positive_request_shape=(
            "rank these two groups by retention for the last reporting period"
        ),
        expected_anchor_observation=(
            "metric denominator, time basis, and unit ambiguity should be surfaced"
        ),
        negative_control_request_shape=(
            "rank these two groups by monthly retention rate using the stated "
            "denominator for the stated reporting period"
        ),
        expected_next_action="preserve_multiple_frames",
    ),
    _fixture(
        id="likely_non_public_evidence",
        fixture_class="likely non-public evidence",
        positive_request_shape=(
            "which internal review memo changed the approval outcome"
        ),
        expected_anchor_observation=(
            "likely non-public evidence and answerability risk should be forecast"
        ),
        negative_control_request_shape=(
            "which public notice changed the approval outcome"
        ),
        expected_next_action="retrieve_to_anchor",
    ),
    _fixture(
        id="simple_evergreen_negative_control",
        fixture_class="simple evergreen negative control",
        positive_request_shape=(
            "define the standard term used for this general process"
        ),
        expected_anchor_observation=(
            "low ambiguity, low freshness, and a single evergreen frame should be "
            "recognized"
        ),
        negative_control_request_shape=(
            "define the standard term used for it after the recent change"
        ),
        expected_next_action="proceed_single_frame",
    ),
    _fixture(
        id="proxy_only_evidence_risk",
        fixture_class="proxy-only evidence risk",
        positive_request_shape=(
            "give the exact target metric for the private category"
        ),
        expected_anchor_observation=(
            "target metric availability risk and tempting proxy-only evidence should "
            "be identified"
        ),
        negative_control_request_shape=(
            "give a proxy or qualitative framing for the private category"
        ),
        expected_next_action="retrieve_to_anchor",
    ),
    _fixture(
        id="causal_claim_hidden_evidence_risk",
        fixture_class="causal claim with hidden evidence risk",
        positive_request_shape=(
            "did the policy change cause the observed performance shift"
        ),
        expected_anchor_observation=(
            "causal mechanism and hidden evidence risk should be distinguished from "
            "descriptive correlation"
        ),
        negative_control_request_shape=(
            "describe whether the policy change and performance shift occurred in "
            "the same period"
        ),
        expected_next_action="preserve_multiple_frames",
    ),
    _fixture(
        id="official_recent_source_class_expectation",
        fixture_class="official/recent source-class expectation",
        positive_request_shape=(
            "summarize the current official requirement for this compliance action"
        ),
        expected_anchor_observation=(
            "official or primary recent source-class expectation should be explicit"
        ),
        negative_control_request_shape=(
            "summarize the historical background of this compliance action"
        ),
        expected_next_action="retrieve_to_anchor",
    ),
    _fixture(
        id="bounded_comparison_with_constraints",
        fixture_class="bounded comparison with constraints",
        positive_request_shape=(
            "compare these options only for the specified region and time window"
        ),
        expected_anchor_observation=(
            "comparison scope, constraint boundaries, and frame preservation should "
            "be maintained"
        ),
        negative_control_request_shape=(
            "compare these options without any region or time-window constraint"
        ),
        expected_next_action="proceed_single_frame",
    ),
)


@pytest.mark.parametrize("fixture", ANCHOR_FIXTURES, ids=lambda item: item.id)
def test_balanced_anchor_fixture_has_required_contract_fields(
    fixture: AnchorFixture,
) -> None:
    assert fixture.id
    assert fixture.fixture_class
    assert fixture.positive_request_shape
    assert fixture.expected_anchor_observation
    assert fixture.negative_control_request_shape
    assert fixture.forbidden_behavior_changes
    assert fixture.expected_next_action in NEXT_ACTIONS


def test_required_fixture_classes_are_present_exactly_once() -> None:
    fixture_classes = [fixture.fixture_class for fixture in ANCHOR_FIXTURES]

    assert set(fixture_classes) == REQUIRED_FIXTURE_CLASSES
    assert len(fixture_classes) == len(set(fixture_classes))


@pytest.mark.parametrize("fixture", ANCHOR_FIXTURES, ids=lambda item: item.id)
def test_every_fixture_defines_a_nearby_negative_control(
    fixture: AnchorFixture,
) -> None:
    assert fixture.negative_control_request_shape
    assert fixture.negative_control_request_shape != fixture.positive_request_shape


@pytest.mark.parametrize("fixture", ANCHOR_FIXTURES, ids=lambda item: item.id)
def test_forbidden_behavior_changes_pin_core_non_change_invariants(
    fixture: AnchorFixture,
) -> None:
    assert CORE_FORBIDDEN_BEHAVIOR_CHANGES <= fixture.forbidden_behavior_changes


@pytest.mark.parametrize("fixture", ANCHOR_FIXTURES, ids=lambda item: item.id)
def test_fixture_shapes_remain_abstract_and_not_production_specific(
    fixture: AnchorFixture,
) -> None:
    fixture_text = " ".join(
        (
            fixture.positive_request_shape,
            fixture.expected_anchor_observation,
            fixture.negative_control_request_shape,
        )
    )

    assert fixture_text == fixture_text.lower()
    assert "://" not in fixture_text
    assert ".com" not in fixture_text
    assert "project source" not in fixture_text
    assert "failed query" not in fixture_text


def test_retrieve_to_anchor_fixtures_are_recommendation_only() -> None:
    retrieve_fixtures = [
        fixture for fixture in ANCHOR_FIXTURES if fixture.expected_next_action == "retrieve_to_anchor"
    ]

    assert retrieve_fixtures
    for fixture in retrieve_fixtures:
        assert "retrieve-to-anchor remains recommendation-only" in (
            fixture.forbidden_behavior_changes
        )
        assert "no active probe" in fixture.forbidden_behavior_changes
        assert "no query-generation change" in fixture.forbidden_behavior_changes


def test_safety_invariants_include_economist_analyst_author_boundaries() -> None:
    assert SAFETY_HANDOFF_INVARIANTS <= CORE_FORBIDDEN_BEHAVIOR_CHANGES
    assert "no weak-corpus behavior change" in CORE_FORBIDDEN_BEHAVIOR_CHANGES
    assert "Fast unchanged" in CORE_FORBIDDEN_BEHAVIOR_CHANGES
    assert "Deep unchanged" in CORE_FORBIDDEN_BEHAVIOR_CHANGES
