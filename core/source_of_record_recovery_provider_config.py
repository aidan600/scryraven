"""Provider-neutral role labels for source-of-record recovery acquisition.

Provider and operation selection belong exclusively to ``core.routing``.  This
module intentionally exposes no executable provider default or provider config.
"""

from __future__ import annotations

SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE = (
    "source_of_record_recovery_extraction_provider"
)
SOURCE_OF_RECORD_RECOVERY_SCOUT_PROVIDER_ROLE = "source_of_record_recovery_scout_provider"


__all__ = [
    "SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE",
    "SOURCE_OF_RECORD_RECOVERY_SCOUT_PROVIDER_ROLE",
]
