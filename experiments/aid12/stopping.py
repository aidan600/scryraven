"""AID-12 treatment for an isolated local experiment process."""

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


def initial_research_prompt(original: str) -> str:
    if original.count(HANDOFF) != 1 or STOPPING_INSTRUCTION in original:
        raise ValueError("Unexpected initial Research prompt")
    return original.replace(HANDOFF, STOPPING_INSTRUCTION + HANDOFF)
