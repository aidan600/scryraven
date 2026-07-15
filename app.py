"""Compatibility tombstone for the retired legacy Streamlit shell."""

import sys

RETIREMENT_MESSAGE = (
    "The legacy Streamlit shell is retired. "
    "The ScryRaven CLI is the current supported interface "
    "(`python -m scryraven`; `python -m proplex` remains compatible). "
    "Future UI integration is intentionally undecided."
)


def main() -> int:
    """Explain the retired entrypoint and fail closed."""
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
