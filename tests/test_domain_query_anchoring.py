"""Synthetic tests for generic domain anchoring of retrieval queries (no web/API calls)."""

from __future__ import annotations

from core.retrieval_quality import (
    anchored_query_variants,
    approved_entity_aliases,
    finalize_retrieval_queries,
    query_has_domain_anchor,
    wants_official_source_bias,
)


def test_gaming_poe2_keeps_primary_with_class_and_patch_terms() -> None:
    out = finalize_retrieval_queries(
        ["Druid upcoming patch", "Shaman balance changes", "Oracle skills"],
        primary_entity="Path of Exile 2",
        entities_list=["Path of Exile 2", "POE 2"],
        core_topic="Path of Exile 2",
        user_query="poe 2 druid upcoming patch",
        intent="general",
        clean=lambda s: " ".join((s or "").strip().split()),
    )
    blob = " ".join(out).lower()
    assert "path of exile 2" in blob
    assert "druid" in blob and "shaman" in blob and "oracle" in blob
    assert "official" in blob and "patch" in blob


def test_tech_codex_anchors_agent_sandbox_terms() -> None:
    out = finalize_retrieval_queries(
        ["agent sandbox changes"],
        primary_entity="OpenAI Codex",
        entities_list=["OpenAI Codex", "Codex"],
        core_topic="OpenAI Codex",
        user_query="codex agent sandbox changes",
        intent="general",
        clean=lambda s: " ".join((s or "").strip().split()),
    )
    joined = " ".join(out).lower()
    assert "codex" in joined
    assert "sandbox" in joined and "agent" in joined


def test_finance_tesla_robotaxi_pricing() -> None:
    out = finalize_retrieval_queries(
        ["robotaxi pricing update"],
        primary_entity="Tesla",
        entities_list=["Tesla"],
        core_topic="Tesla robotaxi",
        user_query="Tesla robotaxi pricing update",
        intent="general",
        clean=lambda s: " ".join((s or "").strip().split()),
    )
    blob = " ".join(out).lower()
    assert "tesla" in blob
    assert "robotaxi" in blob
    assert "official" in blob and "pric" in blob


def test_official_bias_triggered_for_patch_notes_intent_phrases() -> None:
    assert wants_official_source_bias("When is the next balance patch?", "general") is False
    assert wants_official_source_bias("game upcoming patch notes", "general") is True
    assert wants_official_source_bias("changelog for the May release", "general") is True


def test_anchored_query_variants_helper() -> None:
    v = anchored_query_variants(
        "league patch currency",
        primary_entity="Example Game",
        entities_list=["Example Game"],
        core_topic="Example Game",
    )
    assert len(v) == 1
    assert "Example Game" in v[0]
    assert "league" in v[0].lower()


def test_query_has_domain_anchor_requires_multiword_overlap() -> None:
    aliases = ["Path of Exile 2"]
    assert query_has_domain_anchor("nothing here druid patch", aliases) is False
    assert query_has_domain_anchor("path of exile 2 druid", aliases) is True
    assert query_has_domain_anchor("exile balance manifest", aliases) is False
    assert query_has_domain_anchor("path exile balance manifest", aliases) is True


def test_generic_multiword_weak_token_not_anchored_finance() -> None:
    """One substantive token from a multi-word entity must not imply an anchor."""
    primary = "Contoso Metro Financial Journal"
    aliases = [primary]
    assert query_has_domain_anchor("metro earnings report", aliases) is False
    assert query_has_domain_anchor("contoso metro earnings report", aliases) is True


def test_generic_multiword_weak_token_not_anchored_tech() -> None:
    primary = "Acme Aurora Spectacle Headset"
    aliases = [primary]
    assert query_has_domain_anchor("spectacle pricing update", aliases) is False
    assert query_has_domain_anchor("acme aurora spectacle headset pricing", aliases) is True


def test_generic_explicit_alias_single_token_anchors() -> None:
    primary = "Northbridge Expedition Sequel"
    aliases = approved_entity_aliases(
        primary,
        [primary, "NES"],
        primary,
    )
    assert query_has_domain_anchor("sequel balance manifest", aliases) is False
    assert query_has_domain_anchor("nes balance manifest", aliases) is True


def test_generic_secondary_only_query_gets_primary_prefix() -> None:
    primary = "Fabrikam Delta Quartet Service"
    out = finalize_retrieval_queries(
        ["quartet sandbox changes"],
        primary_entity=primary,
        entities_list=[primary, "FDQS"],
        core_topic=primary,
        user_query="fdqs quartet sandbox",
        intent="general",
        clean=lambda s: " ".join((s or "").strip().split()),
    )
    joined = " ".join(out).lower()
    assert "fabrikam" in joined and "quartet" in joined and "sandbox" in joined
