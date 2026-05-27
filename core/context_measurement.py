"""Diagnostics-only prompt/context measurement helpers.

This module intentionally stores only token estimates, counts, and hashes. It
must not persist prompt text or evidence text.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any

HASH_HEX_LENGTH = 16


def estimate_context_tokens(value: Any) -> int:
    """Return a deterministic, non-negative token estimate for diagnostics."""
    if value is None:
        return 0
    text = str(value)
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def stable_context_hash(value: Any, *, length: int = HASH_HEX_LENGTH) -> str:
    """Return a stable truncated SHA-256 hex digest without exposing raw text."""
    text = "" if value is None else str(value)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[: max(1, int(length or HASH_HEX_LENGTH))]


def _ordered_unique(values: Iterable[Any] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        if value is None or isinstance(value, bool):
            continue
        text = str(value).strip()
        if not text or text == "?":
            continue
        if text not in seen:
            out.append(text)
            seen.add(text)
    return out


def repeated_value_count(values: Iterable[Any] | None, prior_values: Iterable[Any] | None) -> int:
    """Count unique values from ``values`` already present in ``prior_values``."""
    current = set(_ordered_unique(values))
    prior = set(_ordered_unique(prior_values))
    return len(current & prior)


def source_ids_from_passages(passages: Iterable[dict[str, Any]] | None) -> list[str]:
    return _ordered_unique(
        passage.get("source_id")
        for passage in (passages or [])
        if isinstance(passage, dict)
    )


def evidence_texts_from_passages(
    passages: Iterable[dict[str, Any]] | None,
    *,
    max_chars: int = 1200,
) -> list[str]:
    texts: list[str] = []
    for passage in passages or []:
        if not isinstance(passage, dict):
            continue
        text = str(passage.get("text") or "")
        if text:
            texts.append(text[:max_chars])
    return texts


class ContextMeasurementCollector:
    """Collect additive prompt/context measurements for one pipeline run."""

    def __init__(self) -> None:
        self._stages: dict[str, dict[str, Any]] = {}
        self._seen_source_ids: set[str] = set()
        self._seen_evidence_hashes: set[str] = set()
        self._all_context_hashes: set[str] = set()

    def add_stage(
        self,
        name: str,
        *,
        prompt: Any,
        stable_prefix: Any | None = None,
        evidence_text: Any | None = None,
        evidence_texts: Iterable[Any] | None = None,
        source_ids: Iterable[Any] | None = None,
        context_hashes: Iterable[Any] | None = None,
    ) -> None:
        stage_name = str(name or "").strip()
        if not stage_name:
            return
        if stage_name in self._stages:
            suffix = 2
            candidate = f"{stage_name}_{suffix}"
            while candidate in self._stages:
                suffix += 1
                candidate = f"{stage_name}_{suffix}"
            stage_name = candidate

        prompt_text = "" if prompt is None else str(prompt)
        prompt_hash = stable_context_hash(prompt_text)
        stable_prefix_tokens = (
            estimate_context_tokens(stable_prefix)
            if stable_prefix is not None
            else None
        )

        evidence_items: list[str] = []
        if evidence_text is not None:
            evidence_items.append(str(evidence_text))
        evidence_items.extend(str(item) for item in (evidence_texts or []) if item is not None)
        evidence_hashes = _ordered_unique(stable_context_hash(item) for item in evidence_items)
        provided_hashes = _ordered_unique(context_hashes)
        all_stage_hashes = _ordered_unique([prompt_hash, *evidence_hashes, *provided_hashes])

        stage_source_ids = _ordered_unique(source_ids)
        repeated_sources = len(set(stage_source_ids) & self._seen_source_ids)
        repeated_evidence_hashes = len(set(evidence_hashes) & self._seen_evidence_hashes)

        self._stages[stage_name] = {
            "prompt_token_estimate": estimate_context_tokens(prompt_text),
            "prompt_hash": prompt_hash,
            "stable_prefix_token_estimate": stable_prefix_tokens,
            "evidence_token_estimate": sum(
                estimate_context_tokens(item) for item in evidence_items
            ),
            "source_id_count": len(stage_source_ids),
            "repeated_source_id_count": repeated_sources,
            "evidence_hash_count": len(evidence_hashes),
            "repeated_evidence_hash_count": repeated_evidence_hashes,
            "context_hash_count": len(all_stage_hashes),
        }
        self._seen_source_ids.update(stage_source_ids)
        self._seen_evidence_hashes.update(evidence_hashes)
        self._all_context_hashes.update(all_stage_hashes)

    def payload(self) -> dict[str, Any]:
        prompt_total = sum(
            int(stage.get("prompt_token_estimate") or 0)
            for stage in self._stages.values()
        )
        evidence_total = sum(
            int(stage.get("evidence_token_estimate") or 0)
            for stage in self._stages.values()
        )
        repeated_source_total = sum(
            int(stage.get("repeated_source_id_count") or 0)
            for stage in self._stages.values()
        )
        repeated_evidence_total = sum(
            int(stage.get("repeated_evidence_hash_count") or 0)
            for stage in self._stages.values()
        )
        return {
            "available": True,
            "stage_count": len(self._stages),
            "stages": dict(self._stages),
            "aggregate": {
                "prompt_token_estimate_total": prompt_total,
                "evidence_token_estimate_total": evidence_total,
                "repeated_source_id_count_total": repeated_source_total,
                "repeated_evidence_hash_count_total": repeated_evidence_total,
                "unique_context_hash_count": len(self._all_context_hashes),
                "raw_prompt_logged": False,
                "raw_evidence_logged": False,
            },
        }
