"""Provider-neutral representations for mechanical source acquisition."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FetchedMaterial:
    """Readable source material mechanically associated with its requested URL."""

    requested_url: str
    readable_text: str
