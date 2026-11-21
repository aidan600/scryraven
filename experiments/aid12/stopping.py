"""AID-12 treatment for an isolated local experiment process."""

from hashlib import sha256

# SHA-256 of the tracked control prompt.
CONTROL_PROMPT_SHA256 = "28489e7e73250521e19957c4822ec37f713c6fd6b580929161120d965a73334f"  # pragma: allowlist secret

STOPPING_INSTRUCTION = (
    "\n\nAfter receiving source material for a single factual lookup, return in that decision "
    "if an acquired passage directly establishes the requested fact for the identified entity, "
    "time and scope, with any qualifications that change the answer. Select the actual passage "
    "and update the briefing. A second Search or Read solely to repeat that support adds no value. "
    "This stopping point requires the passage itself to be sufficient. Continue the ordinary "
    "investigation when identity is ambiguous, evidence conflicts, an excerpt leaves material "
    "context out, or a further requested fact, calculation input or citation needs support."
)

HANDOFF = "\n\n# Handoff\n"


def ordinary_research_prompt(original: str) -> str:
    """Apply the treatment only to the exact registered Research prompt."""
    if original.count(HANDOFF) != 1 or sha256(original.encode("utf-8")).hexdigest() != CONTROL_PROMPT_SHA256:
        raise ValueError("Unexpected ordinary Research prompt")
    return original.replace(HANDOFF, STOPPING_INSTRUCTION + HANDOFF)
