"""Explicit provider role/config for source-of-record recovery acquisition.

This module is a narrow product-owned config seam. It does not choose providers
at runtime, create a fallback loop, call providers, or make evidence/source
authority claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SOURCE_OF_RECORD_RECOVERY_PROVIDER_CONFIG_SCHEMA_VERSION = (
    "source_of_record_recovery_provider_config_v1"
)
SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE = (
    "source_of_record_recovery_extraction_provider"
)
SOURCE_OF_RECORD_RECOVERY_SCOUT_PROVIDER_ROLE = "source_of_record_recovery_scout_provider"
SOURCE_OF_RECORD_RECOVERY_PROVIDER_DECISION_SCOPE = (
    "source_of_record_recovery_acquisition_only"
)
DEFAULT_SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER = "tavily"
DEFAULT_SOURCE_OF_RECORD_RECOVERY_PROVIDER_OPERATION = "search"
DEFAULT_SOURCE_OF_RECORD_RECOVERY_MAX_RESULTS = 5


@dataclass(frozen=True, slots=True)
class SourceOfRecordRecoveryProviderConfig:
    schema_version: str = SOURCE_OF_RECORD_RECOVERY_PROVIDER_CONFIG_SCHEMA_VERSION
    provider: str = DEFAULT_SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER
    provider_role: str = SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE
    operation: str = DEFAULT_SOURCE_OF_RECORD_RECOVERY_PROVIDER_OPERATION
    max_results: int = DEFAULT_SOURCE_OF_RECORD_RECOVERY_MAX_RESULTS
    decision_scope: str = SOURCE_OF_RECORD_RECOVERY_PROVIDER_DECISION_SCOPE
    global_default_provider: bool = False
    raw_private_retention: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "provider_role": self.provider_role,
            "operation": self.operation,
            "max_results": self.max_results,
            "decision_scope": self.decision_scope,
            "global_default_provider": self.global_default_provider,
            "raw_private_retention": self.raw_private_retention,
        }


def get_source_of_record_recovery_extraction_provider_config() -> (
    SourceOfRecordRecoveryProviderConfig
):
    """Return the explicit recovery-role provider config."""

    return SourceOfRecordRecoveryProviderConfig()


__all__ = [
    "DEFAULT_SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER",
    "DEFAULT_SOURCE_OF_RECORD_RECOVERY_MAX_RESULTS",
    "DEFAULT_SOURCE_OF_RECORD_RECOVERY_PROVIDER_OPERATION",
    "SOURCE_OF_RECORD_RECOVERY_EXTRACTION_PROVIDER_ROLE",
    "SOURCE_OF_RECORD_RECOVERY_PROVIDER_CONFIG_SCHEMA_VERSION",
    "SOURCE_OF_RECORD_RECOVERY_PROVIDER_DECISION_SCOPE",
    "SOURCE_OF_RECORD_RECOVERY_SCOUT_PROVIDER_ROLE",
    "SourceOfRecordRecoveryProviderConfig",
    "get_source_of_record_recovery_extraction_provider_config",
]
