from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUCKET_DIR = ROOT / "tests" / "buckets"


def _read_bucket(name: str) -> list[str]:
    path = BUCKET_DIR / f"{name}.txt"
    if not path.is_file():
        raise SystemExit(f"Unknown validation bucket: {name}")

    selected: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            selected.append(stripped)
    if not selected:
        raise SystemExit(f"Validation bucket is empty: {name}")
    return selected


def _pytest_command(*, collect_only: bool, basetemp: str | None) -> list[str]:
    command = [sys.executable, "-m", "pytest", "-q"]
    if collect_only:
        command.append("--collect-only")
    if basetemp:
        command.append(f"--basetemp={basetemp}")
    return command


def _default_basetemp(bucket: str) -> str | None:
    configured = os.environ.get("SCRYRAVEN_PYTEST_BASETEMP")
    if configured:
        return configured
    cache_tmp_root = ROOT / ".pytest_cache" / "basetemp"
    try:
        cache_tmp_root.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return str(cache_tmp_root / bucket)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a ScryRaven validation bucket.")
    parser.add_argument("bucket", help="Bucket name, such as fast_pr, author_lane, or full.")
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Collect selected tests without running them.",
    )
    args = parser.parse_args(argv)

    selected: list[str] = []
    if args.bucket == "full":
        print("Selected validation bucket: full")
    else:
        selected = _read_bucket(args.bucket)
        print(f"Selected validation bucket: {args.bucket}")
        for item in selected:
            print(f"  {item}")
    env = os.environ.copy()
    # Offline validation must not read local .env secrets during collection.
    env.setdefault("PYTHON_DOTENV_DISABLED", "1")

    if args.bucket == "fast_pr":
        print("Running full-suite collection guard before fast_pr tests.", flush=True)
        guard_command = _pytest_command(
            collect_only=True,
            basetemp=_default_basetemp("fast_pr-full-collection"),
        )
        guard_return_code = subprocess.call(guard_command, cwd=ROOT, env=env)
        if guard_return_code:
            return guard_return_code

    command = _pytest_command(
        collect_only=args.collect_only,
        basetemp=_default_basetemp(args.bucket),
    )
    command.extend(selected)
    return subprocess.call(command, cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
