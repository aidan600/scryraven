from __future__ import annotations

from pathlib import Path


def test_tmp_path_uses_workspace_local_base(tmp_path: Path) -> None:
    assert ".pytest-tmp" in tmp_path.parts or (
        len(tmp_path.parts) >= 2
        and tmp_path.parts[0].casefold() == "c:\\"
        and tmp_path.parts[1].casefold() == "tmp"
    )


def test_tmp_path_is_isolated_per_test(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    assert not marker.exists()
    marker.write_text("isolated\n", encoding="utf-8")
