"""Public module entrypoint for the ScryRaven CLI."""

from __future__ import annotations

import sys

from proplex.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
