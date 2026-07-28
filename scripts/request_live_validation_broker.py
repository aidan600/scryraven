"""Retired job/profile validation-broker entrypoint.

The active broker accepts only the versioned generic provider-execution
envelope.  This compatibility tombstone performs no HTTP request, provider
dispatch, child execution, job lookup, or profile lookup.
"""

from __future__ import annotations

import sys

RETIREMENT_MESSAGE = (
    "retired_validation_broker_path: use "
    "scripts/request_provider_proxy_broker.py with an explicit provider, "
    "operation, and model when required"
)


class RetiredValidationBrokerPathError(RuntimeError):
    """Raised when code attempts to reuse the retired authorization doctrine."""


def main(argv: list[str] | None = None) -> int:
    del argv
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "RETIREMENT_MESSAGE",
    "RetiredValidationBrokerPathError",
    "main",
]
