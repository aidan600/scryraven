"""Lossless Research catalog presentation, including absent/null distinctions."""
import json
from copy import deepcopy

import pytest

from scryraven.model import _catalog_tables, _evidence_json, _input_blocks


def decode(catalog):
    return {kind: [dict(zip(group["columns"], row, strict=True))
                   for group in groups for row in group["rows"]]
            for kind, groups in catalog.items()}


@pytest.mark.parametrize("catalog", [
    {"materials": [], "candidates": []},
    {"materials": [
        {"id": "E1", "url": "https://example.test/é", "title": "", "source_id": "E1",
         "acquisition": "provider_highlights", "parent_id": None, "start_char": None,
         "end_char": None, "characters": 20, "exposed": True},
        {"id": "E2", "url": "https://example.test/é", "title": 'Different "标题"',
         "source_id": "E1", "acquisition": "fetched_source", "parent_id": None,
         "start_char": None, "end_char": None, "characters": 90, "exposed": False},
        {"id": "E2@0:4", "url": "https://example.test/é", "title": 'Different "标题"',
         "source_id": "E1", "acquisition": "targeted_view", "parent_id": "E2",
         "start_char": 0, "end_char": 4, "characters": 4, "exposed": True}],
     "candidates": [
         {"id": "C1", "url": "https://example.test/é", "title": "", "material_ids": ["E2", "E1"]},
         {"id": "C2", "url": "https://example.test/nav", "title": "导航", "material_ids": [], "context": ""},
         {"id": "C3", "url": "https://example.test/n", "title": "", "material_ids": [], "context": None},
         {"id": "C4", "url": "https://example.test/m", "title": "", "material_ids": []}]},
    {"materials": [{"id": "E1"}, {"id": "E2", "start_char": None}, {"id": "E3"}],
     "candidates": []},
    {"materials": [
        {"id": "E1", "version": 0, "exposed": False, "future_field": "line 1\nline 2\\quoted\""},
        {"id": "E2", "version": 1, "exposed": True, "future_field": "雪"},
        {"id": "E3", "version": 2, "exposed": False, "future_field": None},
        {"id": "E4", "version": 3, "exposed": False},
        {"id": "E5", "version": 4, "exposed": True, "future_field": ""}],
     "candidates": [{"id": "C1", "material_ids": [], "url": "https://example.test/a?x=1&y=%22q%22"}]},
])
def test_catalog_round_trip(catalog):
    original = deepcopy(catalog)
    encoded = _catalog_tables(catalog)
    assert decode(json.loads(json.dumps(encoded))) == original == catalog
    for kind, groups in encoded.items():
        assert sum(len(group["rows"]) for group in groups) == len(catalog[kind])
        for left, right in zip(groups, groups[1:]):
            assert left["columns"] != right["columns"]


def test_only_research_catalog_changes_and_cache_boundaries_survive():
    packet = {"conversation_context": [{"question": "Before", "answer": "Earlier"}],
              "current_date": "2026-09-29", "phase": "research", "question": "Now",
              "catalog": {"materials": [{"id": "E1", "exposed": True}], "candidates": []},
              "evidence": [{"id": "E1", "content": 'Exact\n"é"'}], "budget": {"remaining": 3}}
    original = deepcopy(packet)
    inputs, labels = _input_blocks("instructions", packet, "research", "research")
    blocks = inputs[1]["content"]
    parsed = json.loads("".join(b["text"] for b in blocks))
    parsed["catalog"] = decode(parsed["catalog"])
    assert parsed == original == packet
    assert labels == ("instructions", "history", "research_context")
    assert all("catalog" not in b["text"] for b in blocks if "prompt_cache_breakpoint" in b)
    assert '"evidence": ' + _evidence_json(packet["evidence"]) in blocks[-1]["text"]
    answer, _ = _input_blocks("instructions", packet, "answer", "answer")
    assert json.loads("".join(b["text"] for b in answer[1]["content"])) == original
