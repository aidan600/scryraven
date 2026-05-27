"""Text-cleaning helpers shared by UI and headless pipeline code."""

from __future__ import annotations


def clean_json_response(text: str) -> str:
    text = text.strip()

    # Safe bracket-counting parser to extract raw JSON.
    start_idx = -1
    end_idx = -1

    for i, char in enumerate(text):
        if char in "{[" and start_idx == -1:
            start_idx = i
            break

    for i in range(len(text) - 1, -1, -1):
        if text[i] in "}]" and end_idx == -1:
            end_idx = i
            break

    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        return text[start_idx : end_idx + 1]

    return text
