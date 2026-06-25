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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a ScryRaven validation bucket.")
    parser.add_argument("bucket", help="Bucket name, such as fast_pr, author_lane, or full.")
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Collect selected tests without running them.",
    )
    args = parser.parse_args()

    command = [sys.executable, "-m", "pytest", "-q"]
    if args.collect_only:
        command.append("--collect-only")

    basetemp = os.environ.get("SCRYRAVEN_PYTEST_BASETEMP")
    if not basetemp:
        cache_tmp_root = ROOT / ".pytest_cache" / "basetemp"
        try:
            cache_tmp_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            cache_tmp_root = None
        if cache_tmp_root is not None:
            basetemp = str(cache_tmp_root / args.bucket)
    if basetemp:
        command.append(f"--basetemp={basetemp}")

    if args.bucket == "full":
        print("Selected validation bucket: full")
    else:
        selected = _read_bucket(args.bucket)
        print(f"Selected validation bucket: {args.bucket}")
        for item in selected:
            print(f"  {item}")
        command.extend(selected)

    env = os.environ.copy()
    # Offline validation must not read local .env secrets during collection.
    env.setdefault("PYTHON_DOTENV_DISABLED", "1")

    return subprocess.call(command, cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
