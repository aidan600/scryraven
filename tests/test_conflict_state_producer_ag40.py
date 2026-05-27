from __future__ import annotations

import ast
import json
from pathlib import Path

from core.answer_contract_runtime_handoff import (
    RuntimeAnswerContractFacts,
    build_runtime_answer_contract_handoff,
)
from core.conflict_state_producer import (
    ConflictClaim,
    ConflictState,
    ConflictStateProducerInput,
    build_conflict_state,
    project_conflict_state_to_runtime_facts,
)

_ROOT = Path(__file__).resolve().parents[1]
_PRODUCER_PATH = _ROOT / "core" / "conflict_state_producer.py"


def _central_input(**overrides):
    values = {
        "query": "What are the current eligibility requirements and official rules for the Care Program?",
        "core_topic": "Care Program current eligibility requirements",
        "primary_entity": "Care Program",
        "current_date": "2026-05-18",
        "final_top_evidence": (
            {
                "source_id": 1,
                "title": "Care Program official rule",
                "url": "https://official.gov/care-rule",
                "text": "The Care Program current rule effective date is May 1, 2026.",
                "source_tier": "official",
            },
            {
                "source_id": 2,
                "title": "Care Program reputable secondary update",
                "url": "https://analysis.example/care-rule",
                "text": "The Care Program current rule effective date is June 1, 2026.",
                "source_tier": "secondary",
            },
        ),
        "source_tier_counts": {"official": 1, "secondary": 1},
        "source_class_observability": {},
        "ordinary_next_queries": (),
    }
    values.update(overrides)
    return ConflictStateProducerInput(**values)


def test_conflict_state_sanitizes_deduplicates_and_is_json_safe() -> None:
    state = ConflictState(
        conflicts_present=True,
        conflict_notes=(" official date conflicts ", "official date conflicts"),
        claims_in_tension=(
            ConflictClaim(
                claim_id=" claim:1 ",
                normalized_claim=" Care Program effective_date May 1, 2026 ",
                value=" May 1, 2026 ",
                attribute=" effective_date ",
                subject=" Care Program ",
                source_refs=(" source:1 ", "source:1"),
                source_classes=(" official ", "official"),
            ),
            ConflictClaim(
                claim_id="claim:2",
                normalized_claim="Care Program effective_date June 1, 2026",
                value="June 1, 2026",
                attribute="effective_date",
                subject="Care Program",
                source_refs=("source:2",),
                source_classes=("secondary",),
            ),
        ),
        evidence_refs=("source:1", "source:2", "source:2"),
        centrality_to_contract="central",
        resolving_query_candidates=("Care Program official current effective date",) * 3,
        resolving_query_source="deterministic_claim_pair",
        confidence="medium",
        metadata={"raw_trace": "blocked", "safe": {"value": True}},
    )

    payload = state.to_dict()
    json.dumps(payload)
    assert payload["conflict_notes"] == ["official date conflicts"]
    assert payload["evidence_refs"] == ["source:1", "source:2"]
    assert payload["resolving_query_candidates"] == [
        "Care Program official current effective date"
    ]
    assert "raw_trace" not in payload["metadata"]
    assert state.safe_to_dispatch_resolve_conflict is True


def test_central_current_rule_conflict_projects_to_runtime_facts() -> None:
    state = build_conflict_state(_central_input())
    projection = project_conflict_state_to_runtime_facts(state)

    assert state.conflicts_present is True
    assert state.safe_to_dispatch_resolve_conflict is True
    assert state.resolving_query_source == "deterministic_claim_pair"
    assert projection["conflicts_present"] is True
    assert projection["conflict_notes"]
    assert projection["resolving_queries"] == state.resolving_query_candidates


def test_ordinary_next_queries_never_become_resolving_queries() -> None:
    state = build_conflict_state(
        _central_input(
            final_top_evidence=(),
            ordinary_next_queries=("Care Program ordinary background query",),
        )
    )
    projection = project_conflict_state_to_runtime_facts(state)

    assert state.ordinary_next_queries == ("Care Program ordinary background query",)
    assert state.resolving_query_candidates == ()
    assert projection["resolving_queries"] == ()


def test_metadata_only_source_class_mismatch_fails_closed() -> None:
    state = build_conflict_state(
        _central_input(
            final_top_evidence=(),
            source_class_observability={
                "missing_expected_source_classes": ["official_current_rules"],
                "source_class_satisfaction_status": {
                    "official_current_rules": "expected_but_only_secondary"
                },
            },
        )
    )

    assert state.conflicts_present is False
    assert state.safe_to_dispatch_resolve_conflict is False
    assert state.blockers == ("metadata_only_signal",)


def test_centrality_confidence_and_blockers_gate_dispatch() -> None:
    noncentral = build_conflict_state(
        _central_input(
            query="Explain the background history of the Care Program.",
            core_topic="Care Program background history",
        )
    )
    low_confidence = build_conflict_state(
        _central_input(
            final_top_evidence=(
                {
                    "source_id": 1,
                    "text": "The rule effective date is May 1, 2026.",
                    "source_tier": "secondary",
                },
                {
                    "source_id": 2,
                    "text": "The rule effective date is June 1, 2026.",
                    "source_tier": "secondary",
                },
            )
        )
    )
    no_query = build_conflict_state(
        _central_input(allow_resolving_query_candidates=False)
    )

    assert noncentral.safe_to_dispatch_resolve_conflict is False
    assert "not_central_to_contract" in noncentral.blockers
    assert low_confidence.safe_to_dispatch_resolve_conflict is False
    assert "low_confidence" in low_confidence.blockers
    assert no_query.safe_to_dispatch_resolve_conflict is False
    assert "no_resolving_query_candidates" in no_query.blockers


def test_noncentral_conflict_and_query_candidate_do_not_project_resolving_queries() -> None:
    state = build_conflict_state(
        _central_input(
            query="Explain the background history of the Care Program.",
            core_topic="Care Program background history",
        )
    )
    projection = project_conflict_state_to_runtime_facts(state)

    assert state.resolving_query_candidates
    assert projection["conflicts_present"] is False
    assert projection["resolving_queries"] == ()


def test_same_date_different_context_control_has_no_claim_pair() -> None:
    state = build_conflict_state(
        _central_input(
            final_top_evidence=(
                {
                    "source_id": 1,
                    "text": "The Care Program announcement date was April 1, 2026.",
                    "source_tier": "official",
                },
                {
                    "source_id": 2,
                    "text": "The Care Program current rule effective date is May 1, 2026.",
                    "source_tier": "secondary",
                },
            )
        )
    )

    assert state.conflicts_present is False
    assert state.blockers == ("no_claim_pair",)


def test_stale_secondary_vs_current_official_blocks_dispatch() -> None:
    state = build_conflict_state(
        _central_input(
            final_top_evidence=(
                {
                    "source_id": 1,
                    "text": "The current official rule effective date is May 1, 2026.",
                    "source_tier": "official",
                },
                {
                    "source_id": 2,
                    "text": "Archived older summary: the rule effective date is June 1, 2026.",
                    "source_tier": "secondary",
                },
            )
        )
    )
    projection = project_conflict_state_to_runtime_facts(state)

    assert state.conflicts_present is True
    assert state.safe_to_dispatch_resolve_conflict is False
    assert "stale_secondary_superseded_by_current_official" in state.blockers
    assert projection["resolving_queries"] == ()


def test_conflict_without_safe_resolving_query_surfaces_notes_only_in_runtime() -> None:
    state = build_conflict_state(
        _central_input(allow_resolving_query_candidates=False)
    )
    projection = project_conflict_state_to_runtime_facts(state)
    result = build_runtime_answer_contract_handoff(
        RuntimeAnswerContractFacts(
            query="Care Program current rules",
            evidence_available=True,
            evidence_sufficient=False,
            conflicts_present=projection["conflicts_present"],
            conflict_notes=projection["conflict_notes"],
            resolving_queries=projection["resolving_queries"],
        )
    )

    evidence_state = result.state.evidence_state_summary
    assert evidence_state.conflicts_present is True
    assert evidence_state.conflict_notes
    assert evidence_state.resolving_queries == ()


def test_conflict_state_producer_static_import_guard() -> None:
    tree = ast.parse(_PRODUCER_PATH.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    forbidden_prefixes = (
        "core.answer_contract_runtime_handoff",
        "core.db",
        "core.pipeline_orchestrator",
        "core.prompts",
        "core.routing",
        "core.search_providers",
        "core.provider",
        "core.providers",
        "core.storage",
        "core.persistence",
        "core.final",
    )
    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imports
        for prefix in forbidden_prefixes
    )
