import json
import re
from typing import Callable, Optional


class _NoopStatusContainer:
    def write(self, text: str) -> None:
        return


_NOOP_STATUS_CONTAINER = _NoopStatusContainer()

QUANT_REPORT_TYPES = {
    "quantitative_comparison",
    "cost_analysis",
    "financial_model",
    "unit_economics",
    "benchmark",
}


def run_scout(
    scout_key: str,
    core_topic: str,
    chunks: list[dict],
    ask_model: Callable[..., str],
    clean_json_response: Callable[[str], str],
    fast_provider: str,
    fast_model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    status_container=_NOOP_STATUS_CONTAINER,
) -> Optional[dict]:
    """
    Runs a domain scout on first-pass evidence chunks.
    Returns parsed JSON dict or None if scout fails.
    Scout failure is non-fatal - pipeline continues without scout context.
    """
    from core.prompts import get_scout_prompt

    prompt = get_scout_prompt(scout_key)
    if not prompt:
        return None

    evidence_lines = []
    for i, chunk in enumerate(chunks[:8], 1):
        text = chunk.get("text", "")[:300]
        source = chunk.get("url", "unknown")
        evidence_lines.append(f"[{i}] {source}\n{text}")
    evidence_block = "\n\n".join(evidence_lines)
    user_message = f"QUERY TOPIC: {core_topic}\n\nEVIDENCE:\n{evidence_block}"

    try:
        response = ask_model(
            user_message,
            prompt,
            provider=fast_provider,
            model=fast_model,
            effort="low",
            base_url=base_url,
            api_key=api_key,
            require_json=True,
            use_reasoning=False,
        )
        cleaned = clean_json_response(response)
        return json.loads(cleaned.strip())
    except Exception as e:
        status_container.write(f"Scout skipped ({scout_key}): {e}")
        return None


def should_skip_quant_scout(report_type: str, chunks: list[dict]) -> bool:
    """
    Skip quant scout when first-pass evidence already appears directly comparable.
    Heuristic: enough credible chunks with numeric evidence likely means retrieval
    can answer directly without scout-driven second-order planning.
    """
    if report_type not in QUANT_REPORT_TYPES:
        return False

    high_cred_chunks = [c for c in chunks[:8] if c.get("credibility", 0) >= 2]
    numeric_chunks = []
    for chunk in high_cred_chunks:
        text = chunk.get("text", "")
        if not isinstance(text, str):
            continue
        if re.search(r"\d", text):
            numeric_chunks.append(chunk)

    return len(high_cred_chunks) >= 4 and len(numeric_chunks) >= 4
