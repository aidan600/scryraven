"""Retired private-copy broker example.

The active implementation is repository-tracked at
``scripts/provider_execution_broker.py`` and is started by
``scripts/run_provider_proxy_broker_once.py``.  This historical import surface
contains no server, provider adapter, request schema, credential handling, or
dispatch behavior.
"""

from __future__ import annotations

RETIREMENT_NOTICE = (
    "private broker copies are retired; use the tracked loopback provider "
    "execution broker"
)


def main() -> int:
    raise RuntimeError(RETIREMENT_NOTICE)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["RETIREMENT_NOTICE", "main"]
