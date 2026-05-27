"""Environment variable compatibility helpers for public ScryRaven aliases."""

from __future__ import annotations

import os
from collections.abc import MutableMapping

EnvMapping = MutableMapping[str, str]


def get_env_alias(
    public_name: str,
    legacy_name: str,
    default: str = "",
    *,
    environ: EnvMapping | None = None,
) -> str:
    """Return the public env value, falling back to the legacy compatibility name."""
    env = os.environ if environ is None else environ
    public_value = env.get(public_name)
    if public_value is not None:
        return public_value
    return env.get(legacy_name, default)


def pop_env_alias(
    public_name: str,
    legacy_name: str,
    default: str = "",
    *,
    environ: EnvMapping | None = None,
) -> str:
    """Pop public and legacy aliases, preferring the public value when both exist."""
    env = os.environ if environ is None else environ
    public_value = env.pop(public_name, None)
    legacy_value = env.pop(legacy_name, None)
    if public_value is not None:
        return public_value
    if legacy_value is not None:
        return legacy_value
    return default
