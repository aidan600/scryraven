"""Public module entrypoint for the ScryRaven CLI."""

from __future__ import annotations

import sys

from proplex.__main__ import main as _compatibility_main


def main(argv: list[str] | None = None) -> int:
    """Run the shared CLI while retaining the public ScryRaven identity."""

    return _compatibility_main(argv, entrypoint="scryraven")


if __name__ == "__main__":
    sys.exit(main())
