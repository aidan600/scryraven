"""Offline regression suite for scripts/cleanup_merged_phase.py.

Builds isolated temporary Git repositories/remotes only. Does not mutate the
developer's real ScryRaven checkout and makes no network/provider calls.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "scripts" / "cleanup_merged_phase.py"
WRAPPER = Path(__file__).resolve().parents[1] / "scripts" / "cleanup_merged_phase.ps1"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed: {completed.stderr or completed.stdout}"
        )
    return completed


def _git_init_identity(repo: Path) -> None:
    _git(repo, "config", "user.email", "cleanup-test@example.com")
    _git(repo, "config", "user.name", "Cleanup Test")
    _git(repo, "config", "core.autocrlf", "false")


@dataclass
class PhaseFixture:
    bare: Path
    repo: Path
    phase_parent: Path
    phase_root: Path
    phase_worktree: Path
    phase_branch: str
    reviewed_head: str


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_merged_phase_fixture(
    tmp_path: Path,
    *,
    phase_name: str = "phase-a",
    phase_branch: str = "cursor/phase-a",
    with_worktree: bool = True,
    merge_to_origin_main: bool = True,
    layout: str = "canonical",
) -> PhaseFixture:
    """Create bare origin + ordinary clone + optional merged phase worktree."""
    if layout not in {"canonical", "legacy_flat"}:
        raise ValueError(f"unknown fixture layout: {layout}")
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", str(bare)],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )

    # Seed from a local init (do not clone an empty bare); push main explicitly.
    seed = tmp_path / "seed"
    subprocess.run(
        ["git", "init", "-b", "main", str(seed)],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    _git_init_identity(seed)
    _write(seed / "README.md", "main\n")
    _write(
        seed / ".gitignore",
        ".pytest_cache/\n.ruff_cache/\n__pycache__/\ntmp/\ncache/\nevidence/\nfinal/\n",
    )
    _git(seed, "add", "README.md", ".gitignore")
    _git(seed, "commit", "-m", "initial main")
    _git(seed, "remote", "add", "origin", str(bare))
    _git(seed, "push", "-u", "origin", "main")
    # Ensure bare HEAD advertises main so clones check out a real branch.
    subprocess.run(
        ["git", "-C", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )

    repo = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", str(bare), str(repo)],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    _git_init_identity(repo)
    # Guarantee ordinary checkout is on main before creating the phase branch.
    _git(repo, "switch", "main")

    phase_parent = tmp_path / "sr-phases"
    phase_root = phase_parent / phase_name
    canonical_worktree = phase_root / "worktree"
    phase_parent.mkdir(parents=True, exist_ok=True)

    _git(repo, "switch", "-c", phase_branch)
    _write(repo / "phase.txt", "phase work\n")
    _git(repo, "add", "phase.txt")
    _git(repo, "commit", "-m", "phase commit")
    reviewed_head = _git(repo, "rev-parse", "HEAD").stdout.strip().lower()

    phase_worktree = (
        phase_root if layout == "legacy_flat" else canonical_worktree
    )
    if with_worktree:
        _git(repo, "switch", "main")
        if layout == "legacy_flat":
            _git(repo, "worktree", "add", str(phase_root), phase_branch)
        else:
            phase_root.mkdir(parents=True, exist_ok=True)
            _git(repo, "worktree", "add", str(canonical_worktree), phase_branch)
    else:
        _git(repo, "switch", "main")
        phase_root.mkdir(parents=True, exist_ok=True)

    if merge_to_origin_main:
        # Fast-forward origin/main to the reviewed phase head without moving local main.
        _git(repo, "push", "origin", f"{reviewed_head}:refs/heads/main")
        _git(repo, "fetch", "origin", "--prune")

    return PhaseFixture(
        bare=bare,
        repo=repo,
        phase_parent=phase_parent,
        phase_root=phase_root,
        phase_worktree=phase_worktree,
        phase_branch=phase_branch,
        reviewed_head=reviewed_head,
    )


def run_cleanup(
    fx: PhaseFixture,
    *,
    reviewed_head: str | None = None,
    phase_root: Path | None = None,
    phase_branch: str | None = None,
    phase_parent: Path | None = None,
    phase_worktree: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(ENGINE),
        "--reviewed-head",
        reviewed_head or fx.reviewed_head,
        "--phase-branch",
        phase_branch or fx.phase_branch,
        "--phase-root",
        str(phase_root or fx.phase_root),
        "--repo",
        str(fx.repo),
        "--phase-parent",
        str(phase_parent or fx.phase_parent),
    ]
    if phase_worktree is not None:
        args.extend(["--phase-worktree", str(phase_worktree)])
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def test_forbidden_git_tokens_absent_from_engine_source() -> None:
    source = ENGINE.read_text(encoding="utf-8")
    # Behavioral authority lives in argument-array guards; also assert production
    # call sites never request these destructive forms.
    assert "shell=False" in source
    assert re.search(r"subprocess\.run\([^\)]*shell\s*=\s*True", source, re.DOTALL) is None
    # No production argv that starts a destructive clean/reset/rebase/force delete.
    assert not re.search(r'run_git\([^\)]*\[["\']clean["\']', source)
    assert not re.search(r'run_git\([^\)]*\[["\']reset["\']', source)
    assert not re.search(r'run_git\([^\)]*\[["\']rebase["\']', source)
    assert 'args[0] in {"reset", "rebase", "clean"}' in source
    assert 'args[:2] == ["branch", "-D"]' in source
    assert '"--force" in args' in source
    # Ensure we never construct a force worktree-remove call site.
    assert "worktree remove --force" not in source or "forbidden" in source
    assert '["worktree", "remove", "--force"' not in source.split("if ")[0]
    # Python 3.11 compatibility: no pathlib follow_symlinks keyword forms.
    assert re.search(r"\.(?:exists|is_dir|is_file)\(\s*follow_symlinks\s*=", source) is None
    assert "lexists_no_follow" in source
    assert "is_dir_no_follow" in source


def test_case_a_ordinary_merged_phase(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    # Sync local main first so cleanup's ff-only has a clean path; fixture leaves
    # local main possibly behind until cleanup fetch+ff.
    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "cleanup complete" in result.stdout
    assert "Worktree topology: canonical" in result.stdout
    assert not fx.phase_worktree.exists()
    assert not fx.phase_root.exists()
    branches = _git(fx.repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/").stdout.splitlines()
    assert branches == ["main"]
    head = _git(fx.repo, "rev-parse", "HEAD").stdout.strip().lower()
    origin = _git(fx.repo, "rev-parse", "origin/main").stdout.strip().lower()
    assert head == origin
    wt = _git(fx.repo, "worktree", "list", "--porcelain").stdout
    assert wt.count("worktree ") == 1


def test_case_b_detached_ordinary_checkout(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    head = _git(fx.repo, "rev-parse", "HEAD").stdout.strip()
    _git(fx.repo, "checkout", "--detach", head)
    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "switched detached" in result.stdout
    branch = _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip()
    assert branch == "main"
    assert not fx.phase_root.exists()


def test_exact_reviewed_merged_phase_branch_recovers_to_main(tmp_path: Path) -> None:
    """A clean ordinary checkout on the exact reviewed phase branch is recoverable."""
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    _git(fx.repo, "switch", fx.phase_branch)

    result = run_cleanup(fx)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "switched exact reviewed merged phase branch ordinary checkout to main" in result.stdout
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == "main"
    assert not fx.phase_root.exists()
    assert _git(
        fx.repo,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{fx.phase_branch}",
        check=False,
    ).returncode != 0


def test_dirty_exact_phase_branch_does_not_auto_switch(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    _git(fx.repo, "switch", fx.phase_branch)
    _write(fx.repo / "keep-local.txt", "preserve\n")

    result = run_cleanup(fx)

    assert result.returncode != 0
    assert "ordinary checkout is dirty" in result.stdout.lower()
    assert "switched exact reviewed merged phase branch" not in result.stdout
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == fx.phase_branch
    assert (fx.repo / "keep-local.txt").exists()
    assert fx.phase_root.exists()


def test_unrelated_ordinary_branch_does_not_auto_switch(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    _git(fx.repo, "branch", "unrelated-branch", "main")
    _git(fx.repo, "switch", "unrelated-branch")

    result = run_cleanup(fx)

    assert result.returncode != 0
    assert "unexpected branch" in result.stdout.lower()
    assert "switched exact reviewed merged phase branch" not in result.stdout
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == "unrelated-branch"
    assert fx.phase_root.exists()


def test_exact_phase_branch_head_mismatch_blocks_before_switch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The recovery check requires the ordinary HEAD, not just the branch name."""
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    _git(fx.repo, "switch", fx.phase_branch)
    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    real_ordinary_head_state = mod.ordinary_head_state

    def mismatched_ordinary_head_state(repo: Path) -> tuple[str, str, bool]:
        posture, _head, detached = real_ordinary_head_state(repo)
        if repo == fx.repo and posture == fx.phase_branch:
            return posture, "0" * 40, detached
        return posture, _head, detached

    monkeypatch.setattr(mod, "ordinary_head_state", mismatched_ordinary_head_state)
    code = mod.run_cleanup(
        [
            "--reviewed-head",
            fx.reviewed_head,
            "--phase-branch",
            fx.phase_branch,
            "--phase-root",
            str(fx.phase_root),
            "--repo",
            str(fx.repo),
            "--phase-parent",
            str(fx.phase_parent),
        ]
    )
    captured = capsys.readouterr().out

    assert code == mod.EXIT_GIT_STATE
    assert "ordinary checkout is on unexpected branch" in captured.lower()
    assert "switched exact reviewed merged phase branch" not in captured
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == fx.phase_branch
    assert fx.phase_root.exists()


def test_phase_branch_review_identity_mismatch_blocks_before_switch(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    _git(fx.repo, "switch", fx.phase_branch)
    _write(fx.repo / "unreviewed.txt", "unreviewed\n")
    _git(fx.repo, "add", "unreviewed.txt")
    _git(fx.repo, "commit", "-m", "unreviewed local advance")

    result = run_cleanup(fx)

    assert result.returncode == 7
    assert "review-identity" in result.stdout.lower() or "identity" in result.stdout.lower()
    assert "switched exact reviewed merged phase branch" not in result.stdout
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == fx.phase_branch
    assert fx.phase_root.exists()


def test_unmerged_exact_phase_branch_does_not_auto_switch(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(
        tmp_path,
        with_worktree=False,
        merge_to_origin_main=False,
    )
    _git(fx.repo, "switch", fx.phase_branch)

    result = run_cleanup(fx)

    assert result.returncode == 2
    assert "merge gate" in result.stdout.lower()
    assert "switched exact reviewed merged phase branch" not in result.stdout
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == fx.phase_branch
    assert fx.phase_root.exists()


def test_exact_phase_branch_main_switch_failure_blocks_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    _git(fx.repo, "switch", fx.phase_branch)
    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    real_run_git = mod.run_git

    def fail_main_switch(
        repo: Path, args: list[str], *, check: bool = False
    ) -> mod.GitResult:
        if repo == fx.repo and args == ["switch", "main"]:
            return mod.GitResult(
                args=args,
                returncode=1,
                stdout="",
                stderr="simulated switch failure",
            )
        return real_run_git(repo, args, check=check)

    monkeypatch.setattr(mod, "run_git", fail_main_switch)
    code = mod.run_cleanup(
        [
            "--reviewed-head",
            fx.reviewed_head,
            "--phase-branch",
            fx.phase_branch,
            "--phase-root",
            str(fx.phase_root),
            "--repo",
            str(fx.repo),
            "--phase-parent",
            str(fx.phase_parent),
        ]
    )
    captured = capsys.readouterr().out

    assert code == mod.EXIT_GIT_STATE
    assert "could not switch to main" in captured.lower()
    assert "switched exact reviewed merged phase branch" not in captured
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == fx.phase_branch
    assert fx.phase_root.exists()


def test_exact_phase_branch_ff_only_failure_blocks_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    _git(fx.repo, "switch", fx.phase_branch)
    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    real_run_git = mod.run_git

    def fail_ff_only(
        repo: Path, args: list[str], *, check: bool = False
    ) -> mod.GitResult:
        if repo == fx.repo and args == ["merge", "--ff-only", "origin/main"]:
            return mod.GitResult(
                args=args,
                returncode=1,
                stdout="",
                stderr="simulated ff-only failure",
            )
        return real_run_git(repo, args, check=check)

    monkeypatch.setattr(mod, "run_git", fail_ff_only)
    code = mod.run_cleanup(
        [
            "--reviewed-head",
            fx.reviewed_head,
            "--phase-branch",
            fx.phase_branch,
            "--phase-root",
            str(fx.phase_root),
            "--repo",
            str(fx.repo),
            "--phase-parent",
            str(fx.phase_parent),
        ]
    )
    captured = capsys.readouterr().out

    assert code == mod.EXIT_GIT_OP
    assert "fast-forward sync of main failed" in captured.lower()
    assert "switched exact reviewed merged phase branch ordinary checkout to main" in captured
    assert _git(fx.repo, "symbolic-ref", "--short", "HEAD").stdout.strip() == "main"
    assert fx.phase_root.exists()


def test_case_c_main_behind_origin(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    # Local main intentionally behind origin/main after merge push.
    local = _git(fx.repo, "rev-parse", "main").stdout.strip().lower()
    origin = _git(fx.repo, "rev-parse", "origin/main").stdout.strip().lower()
    assert local != origin
    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "fast-forwarded" in result.stdout
    assert "rebase" not in result.stdout.lower() or "forbidden" in result.stdout.lower()
    head = _git(fx.repo, "rev-parse", "HEAD").stdout.strip().lower()
    assert head == _git(fx.repo, "rev-parse", "origin/main").stdout.strip().lower()


def test_case_d_ignored_generated_artifacts(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    wt = fx.phase_worktree
    for rel in (
        ".pytest_cache/v/cache",
        ".ruff_cache/0.1",
        "package/__pycache__",
        "tmp",
    ):
        (wt / rel).mkdir(parents=True, exist_ok=True)
    marker = wt / "tmp" / "execution.jsonl"
    marker_payload = "CLASSIFICATION_MUST_NOT_OPEN_THIS_PAYLOAD"
    marker.write_text(marker_payload + "\n", encoding="utf-8")
    (wt / "tmp" / "kb.jsonl").write_text("kb\n", encoding="utf-8")
    (wt / "tmp" / "policy_journal.jsonl").write_text("policy\n", encoding="utf-8")
    (wt / ".pytest_cache" / "v" / "cache" / "node").write_text("x\n", encoding="utf-8")
    (wt / "package" / "__pycache__" / "mod.cpython-313.pyc").write_bytes(b"\0\0")

    # Monkeypatch proof: classification must not require reading marker contents.
    # We assert post-condition and that cleanup succeeded without opening for logic
    # by ensuring the file is gone and engine source never reads these names for content.
    source = ENGINE.read_text(encoding="utf-8")
    assert "execution.jsonl" not in source or "open(" not in source.split("execution.jsonl")[0][-200:]
    assert "read_text" not in source
    assert "Path.open" not in source

    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not fx.phase_worktree.exists()
    assert "removed allowlisted ignored path" in result.stdout


def test_case_e_unknown_ignored_artifact(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    mystery = fx.phase_worktree / ".mystery_cache"
    mystery.mkdir()
    (mystery / "x.bin").write_bytes(b"abc")
    # Ensure ignored via gitignore append in worktree (local ignore file).
    gitignore = fx.phase_worktree / ".gitignore"
    gitignore.write_text(gitignore.read_text(encoding="utf-8") + ".mystery_cache/\n", encoding="utf-8")
    # The .gitignore modification is tracked dirty unless we don't stage — that
    # would fail Case G. Use info/exclude instead.
    gitignore.write_text(
        "\n".join(
            [
                ".pytest_cache/",
                ".ruff_cache/",
                "__pycache__/",
                "tmp/",
                "cache/",
                "evidence/",
                "final/",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _git(fx.phase_worktree, "checkout", "--", ".gitignore")
    # In a linked worktree, .git is a file; exclusions live in common git dir.
    common = _git(fx.phase_worktree, "rev-parse", "--git-common-dir").stdout.strip()
    exclude_path = Path(common) / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    exclude_path.write_text(existing + "\n.mystery_cache/\n", encoding="utf-8")

    result = run_cleanup(fx)
    assert result.returncode != 0
    assert "unknown ignored" in result.stdout.lower() or "outside allowlist" in result.stdout.lower()
    assert fx.phase_worktree.exists()
    assert mystery.exists()
    # Branch not force-deleted.
    assert _git(fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False).returncode == 0


def test_case_f_untracked_nonignored_file(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    keep = fx.phase_worktree / "keep_me.txt"
    keep.write_text("preserve\n", encoding="utf-8")
    result = run_cleanup(fx)
    assert result.returncode != 0
    assert keep.exists()
    assert "untracked" in result.stdout.lower()


def test_case_g_dirty_tracked_worktree(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    target = fx.phase_worktree / "phase.txt"
    original = target.read_text(encoding="utf-8")
    target.write_text(original + "dirty\n", encoding="utf-8")
    result = run_cleanup(fx)
    assert result.returncode != 0
    assert "tracked modifications" in result.stdout.lower() or "modifications" in result.stdout.lower()
    assert target.read_text(encoding="utf-8") == original + "dirty\n"


def test_case_h_reviewed_head_not_merged(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, merge_to_origin_main=False)
    result = run_cleanup(fx)
    assert result.returncode == 2
    assert "merge gate" in result.stdout.lower()
    assert fx.phase_worktree.exists()
    assert _git(fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False).returncode == 0
    assert fx.phase_root.exists()


def test_case_i_worktree_already_absent(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    assert not fx.phase_worktree.exists()
    # Leave disposable phase-root children so root cleanup still has work.
    (fx.phase_root / "tmp").mkdir(exist_ok=True)
    (fx.phase_root / "tmp" / "execution.jsonl").write_text("x\n", encoding="utf-8")
    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "worktree already absent" in result.stdout
    assert not fx.phase_root.exists()
    assert _git(fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False).returncode != 0


def test_case_j_branch_already_absent(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "merge", "--ff-only", "origin/main")
    _git(fx.repo, "branch", "-d", "--", fx.phase_branch)
    (fx.phase_root / "cache").mkdir(exist_ok=True)
    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "phase branch already absent" in result.stdout
    assert not fx.phase_root.exists()


def test_case_k_phase_root_already_absent(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "merge", "--ff-only", "origin/main")
    _git(fx.repo, "branch", "-d", "--", fx.phase_branch)
    shutil.rmtree(fx.phase_root)
    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "phase root already absent" in result.stdout
    assert "already satisfied / no-op success" in result.stdout or "cleanup complete" in result.stdout


def test_case_l_unexpected_phase_root_entry(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "merge", "--ff-only", "origin/main")
    _git(fx.repo, "branch", "-d", "--", fx.phase_branch)
    unexpected = fx.phase_root / "something-unexpected"
    unexpected.write_text("nope\n", encoding="utf-8")
    result = run_cleanup(fx)
    assert result.returncode != 0
    assert "unexpected phase-root entry" in result.stdout.lower()
    assert unexpected.exists()


def _try_link_dir(link: Path, target: Path) -> str:
    """Create a directory symlink or Windows junction. Returns kind or raises skip."""
    try:
        link.symlink_to(target, target_is_directory=True)
        return "symlink"
    except OSError:
        pass
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        if completed.returncode == 0 and link.exists():
            return "junction"
        raise pytest.skip(
            f"symlink/junction creation unsupported: {completed.stderr or completed.stdout}"
        )
    raise pytest.skip("symlink creation unsupported on this platform")


def test_case_m_symlink_reparse_protection(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    external = tmp_path / "external-target"
    external.mkdir()
    precious = external / "precious.txt"
    precious.write_text("do-not-delete\n", encoding="utf-8")
    link = fx.phase_worktree / "tmp"
    _try_link_dir(link, external)
    # Ensure tmp/ is ignored.
    common = _git(fx.phase_worktree, "rev-parse", "--git-common-dir").stdout.strip()
    exclude_path = Path(common) / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    if "tmp/" not in existing:
        exclude_path.write_text(existing + "\ntmp/\n", encoding="utf-8")

    result = run_cleanup(fx)
    assert result.returncode != 0
    assert "symlink" in result.stdout.lower() or "reparse" in result.stdout.lower()
    assert precious.exists()
    assert precious.read_text(encoding="utf-8") == "do-not-delete\n"


def test_case_n_idempotent_second_invocation(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    first = run_cleanup(fx)
    assert first.returncode == 0, first.stdout + first.stderr
    second = run_cleanup(fx)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "already satisfied / no-op success" in second.stdout
    assert "removed " not in "\n".join(
        line for line in second.stdout.splitlines() if line.strip().startswith("- removed")
    )


def test_case_o_unrelated_branch_and_worktree(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "branch", "unrelated-branch")
    other_wt = tmp_path / "other-worktree"
    _git(fx.repo, "worktree", "add", str(other_wt), "unrelated-branch")
    result = run_cleanup(fx)
    assert result.returncode != 0
    assert "unrelated" in result.stdout.lower() or "local branches must be main only" in result.stdout.lower() or "worktrees must be exactly one" in result.stdout.lower()
    # Unrelated artifacts preserved.
    assert _git(fx.repo, "show-ref", "--verify", "--quiet", "refs/heads/unrelated-branch", check=False).returncode == 0
    assert other_wt.exists()
    # Target phase should still be cleaned (or invariant failed after target cleanup).
    # Branch/worktree of phase should be gone if cleanup reached that far.
    assert _git(fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False).returncode != 0
    assert not fx.phase_worktree.exists()


def test_case_p_phase_branch_advanced_after_review(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    # Advance local phase branch tip beyond reviewed head while worktree checks out branch.
    _git(fx.phase_worktree, "status", "--porcelain")
    _write(fx.phase_worktree / "extra.txt", "unreviewed\n")
    _git(fx.phase_worktree, "add", "extra.txt")
    _git(fx.phase_worktree, "commit", "-m", "unreviewed local advance")
    tip = _git(fx.repo, "rev-parse", f"refs/heads/{fx.phase_branch}").stdout.strip().lower()
    assert tip != fx.reviewed_head
    # Prove reviewed head is still in origin/main.
    anc = _git(fx.repo, "merge-base", "--is-ancestor", fx.reviewed_head, "origin/main", check=False)
    assert anc.returncode == 0

    result = run_cleanup(fx)
    assert result.returncode == 7
    assert "identity" in result.stdout.lower()
    assert fx.reviewed_head in result.stdout
    assert tip in result.stdout
    assert fx.phase_worktree.exists()
    assert _git(fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False).returncode == 0
    assert fx.phase_root.exists()


def test_case_q_valid_direct_child_phase(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, phase_name="phase-a")
    assert fx.phase_root.parent == fx.phase_parent
    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr


def test_case_r_arbitrary_sibling_directory(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    sibling = tmp_path / "not-sr-phases" / "looks-like-phase"
    for name in ("cache", "tmp", "evidence", "final"):
        (sibling / name).mkdir(parents=True, exist_ok=True)
    (sibling / "tmp" / "execution.jsonl").write_text("x\n", encoding="utf-8")
    result = run_cleanup(fx, phase_root=sibling, phase_parent=fx.phase_parent)
    assert result.returncode == 6
    assert (sibling / "tmp" / "execution.jsonl").exists()


def test_case_s_nested_phase_path(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    nested = fx.phase_parent / "phase-a" / "nested-phase"
    nested.mkdir(parents=True, exist_ok=True)
    result = run_cleanup(fx, phase_root=nested)
    assert result.returncode == 6
    assert "direct child" in result.stdout.lower()


def test_case_t_phase_parent_itself(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    result = run_cleanup(fx, phase_root=fx.phase_parent)
    assert result.returncode == 6
    assert "phase parent" in result.stdout.lower() or "direct child" in result.stdout.lower()


def test_case_u_lexical_escape(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    escape = fx.phase_parent / "phase-a" / ".." / ".." / "escaped"
    escape.mkdir(parents=True, exist_ok=True)
    (escape / "cache").mkdir()
    result = run_cleanup(fx, phase_root=escape)
    assert result.returncode == 6


def test_case_v_symlink_phase_root_indirection(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    external = tmp_path / "outside-namespace" / "phase-x"
    external.mkdir(parents=True)
    for name in ("cache", "tmp", "evidence", "final"):
        (external / name).mkdir()
    link_root = fx.phase_parent / "linked-phase"
    _try_link_dir(link_root, external)
    result = run_cleanup(fx, phase_root=link_root)
    assert result.returncode != 0
    assert (external / "tmp").exists()
    # External disposable dirs untouched (still present).
    assert (external / "cache").exists()


def test_cli_is_product_path(tmp_path: Path) -> None:
    """Product-path proof: real CLI drives the state machine (Case A shape)."""
    fx = build_merged_phase_fixture(tmp_path)
    assert ENGINE.is_file()
    assert WRAPPER.is_file()
    result = run_cleanup(fx)
    assert result.returncode == 0
    assert "=== ScryRaven merged-phase cleanup ===" in result.stdout
    assert "Result: cleanup complete" in result.stdout


def test_runtime_guards_refuse_force_branch_delete(tmp_path: Path) -> None:
    # Import engine guards directly.
    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    fx = build_merged_phase_fixture(tmp_path)
    with pytest.raises(mod.CleanupBlocked):
        mod.run_git(fx.repo, ["branch", "-D", "--", "main"])
    with pytest.raises(mod.CleanupBlocked):
        mod.run_git(fx.repo, ["worktree", "remove", "--force", str(fx.phase_worktree)])
    with pytest.raises(mod.CleanupBlocked):
        mod.run_git(fx.repo, ["clean", "-fd"])
    with pytest.raises(mod.CleanupBlocked):
        mod.run_git(fx.repo, ["reset", "--hard"])
    with pytest.raises(mod.CleanupBlocked):
        mod.run_git(fx.repo, ["rebase", "origin/main"])


def test_case_w_unrelated_registered_worktree_at_expected_path(tmp_path: Path) -> None:
    """Expected path occupied by clean unrelated registered worktree must fail closed."""
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "branch", "unrelated-branch", "main")
    _git(fx.repo, "worktree", "add", str(fx.phase_worktree), "unrelated-branch")
    # Ignored artifact inside the unrelated worktree must not be deleted.
    cache = fx.phase_worktree / ".pytest_cache"
    cache.mkdir()
    marker = cache / "keep.bin"
    marker.write_bytes(b"keep")

    tip = _git(fx.repo, "rev-parse", f"refs/heads/{fx.phase_branch}").stdout.strip().lower()
    assert tip == fx.reviewed_head

    result = run_cleanup(fx)
    assert result.returncode == 9, result.stdout + result.stderr
    assert "worktree identity gate = failed" in result.stdout
    assert f"refs/heads/{fx.phase_branch}" in result.stdout
    assert "refs/heads/unrelated-branch" in result.stdout
    assert fx.reviewed_head in result.stdout
    assert fx.phase_worktree.exists()
    assert marker.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0
    assert fx.phase_root.exists()
    assert "removed phase worktree" not in result.stdout
    assert "deleted phase branch" not in result.stdout


def test_case_x_detached_or_wrong_worktree_head(tmp_path: Path) -> None:
    """Detached expected-path worktree, and matching-branch/wrong-HEAD entries, fail closed."""
    fx = build_merged_phase_fixture(tmp_path)
    old_main = _git(fx.repo, "rev-parse", "main").stdout.strip().lower()
    assert old_main != fx.reviewed_head
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "worktree", "add", "--detach", str(fx.phase_worktree), old_main)

    result = run_cleanup(fx)
    assert result.returncode == 9, result.stdout + result.stderr
    assert "worktree identity gate = failed" in result.stdout
    assert fx.phase_worktree.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0
    assert fx.phase_root.exists()

    # Direct gate proof: correct branch field with wrong HEAD still fails closed.
    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    report = mod.CleanupReport()
    with pytest.raises(mod.CleanupBlocked) as raised:
        mod.prove_registered_worktree_identity(
            {
                "worktree": str(fx.phase_worktree),
                "branch": f"refs/heads/{fx.phase_branch}",
                "HEAD": "0" * 40,
            },
            phase_worktree=fx.phase_worktree,
            phase_branch=fx.phase_branch,
            reviewed_head=fx.reviewed_head,
            report=report,
        )
    assert raised.value.code == mod.EXIT_WORKTREE_IDENTITY
    assert "worktree identity gate = failed" in raised.value.message
    assert report.worktree_identity == "failed"


def test_case_y_invalid_cli_invocation_exit_matches_summary() -> None:
    """Invalid CLI invocation must print Exit code matching the process return code."""
    result = subprocess.run(
        [sys.executable, str(ENGINE)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert result.returncode != 0
    assert "Result: safely blocked" in result.stdout
    assert f"Exit code: {result.returncode}" in result.stdout
    assert "invalid arguments" in result.stdout.lower()
    assert result.returncode == 1


def test_case_z_indeterminate_lstat_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unexpected os.lstat errors must fail closed, never look like absence."""
    fx = build_merged_phase_fixture(tmp_path)
    cache = fx.phase_worktree / ".pytest_cache"
    cache.mkdir()
    marker = cache / "keep.bin"
    marker.write_bytes(b"keep")

    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    real_lstat = os.lstat
    target_key = os.path.normcase(os.path.normpath(str(fx.phase_worktree)))

    def flaky_lstat(path: str | bytes | os.PathLike[str], *args: object, **kwargs: object):
        key = os.path.normcase(os.path.normpath(os.fsdecode(path)))
        if key == target_key or key.startswith(target_key + os.sep):
            raise PermissionError("simulated access denied")
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", flaky_lstat)
    # In-process CLI path so the lstat monkeypatch is visible to the engine.
    code = mod.run_cleanup(
        [
            "--reviewed-head",
            fx.reviewed_head,
            "--phase-branch",
            fx.phase_branch,
            "--phase-root",
            str(fx.phase_root),
            "--repo",
            str(fx.repo),
            "--phase-parent",
            str(fx.phase_parent),
        ]
    )
    captured = capsys.readouterr().out
    assert code != 0
    assert "Result: safely blocked" in captured
    assert "indeterminate filesystem state" in captured.lower()
    assert f"Exit code: {code}" in captured
    assert fx.phase_worktree.exists()
    assert marker.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0
    assert fx.phase_root.exists()
    assert "removed allowlisted ignored path" not in captured
    assert "removed phase worktree" not in captured
    assert "deleted phase branch" not in captured


def test_case_aa_nested_phase_root_reparse_leaf_removal(tmp_path: Path) -> None:
    """Nested junction under real phase-root\\tmp is removed without traversing target."""
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "merge", "--ff-only", "origin/main")
    _git(fx.repo, "branch", "-d", "--", fx.phase_branch)

    external = tmp_path / "external-target"
    external.mkdir()
    precious = external / "precious.txt"
    precious.write_text("do-not-delete\n", encoding="utf-8")

    nested = fx.phase_root / "tmp" / "pytest-output" / "fixture" / "worktree"
    nested.mkdir(parents=True, exist_ok=True)
    _try_link_dir(nested / "tmp", external)

    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not fx.phase_root.exists()
    assert external.exists()
    assert precious.exists()
    assert precious.read_text(encoding="utf-8") == "do-not-delete\n"
    assert "safely blocked" not in result.stdout


def test_case_ab_immediate_phase_root_tmp_reparse_fails_closed(tmp_path: Path) -> None:
    """phase-root\\tmp as an immediate junction/symlink must still fail closed."""
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "merge", "--ff-only", "origin/main")
    _git(fx.repo, "branch", "-d", "--", fx.phase_branch)

    external = tmp_path / "external-target"
    external.mkdir()
    precious = external / "precious.txt"
    precious.write_text("do-not-delete\n", encoding="utf-8")

    link = fx.phase_root / "tmp"
    _try_link_dir(link, external)

    result = run_cleanup(fx)
    assert result.returncode != 0
    assert "Result: safely blocked" in result.stdout
    assert "symlink/reparse" in result.stdout.lower()
    assert link.exists()
    assert external.exists()
    assert precious.exists()
    assert precious.read_text(encoding="utf-8") == "do-not-delete\n"


def test_case_ac_windows_readonly_file_under_phase_tmp(tmp_path: Path) -> None:
    """Windows read-only regular file under trusted phase-root\\tmp is removed."""
    if os.name != "nt":
        pytest.skip("Windows read-only attribute semantics required")
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "merge", "--ff-only", "origin/main")
    _git(fx.repo, "branch", "-d", "--", fx.phase_branch)

    obj_dir = fx.phase_root / "tmp" / "pytest-output" / "origin.git" / "objects" / "ab"
    obj_dir.mkdir(parents=True, exist_ok=True)
    obj = obj_dir / "cdef0123456789"
    obj.write_bytes(b"git-object-bytes")
    # Mechanically mark the regular file read-only (Windows FILE_ATTRIBUTE_READONLY).
    os.chmod(obj, stat.S_IREAD)
    st = os.lstat(obj)
    attrs = getattr(st, "st_file_attributes", 0)
    assert attrs & 0x1, "test setup failed to set FILE_ATTRIBUTE_READONLY"

    result = run_cleanup(fx)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not obj.exists()
    assert not fx.phase_root.exists()


def test_case_ad_generic_permission_error_does_not_chmod(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Generic PermissionError without proven read-only attribute fails closed."""
    fx = build_merged_phase_fixture(tmp_path)
    _git(fx.repo, "worktree", "remove", str(fx.phase_worktree))
    _git(fx.repo, "merge", "--ff-only", "origin/main")
    _git(fx.repo, "branch", "-d", "--", fx.phase_branch)

    target = fx.phase_root / "tmp" / "pytest-output" / "blocked.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"keep-me")

    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    real_unlink = Path.unlink
    chmod_calls: list[Path] = []

    def flaky_unlink(self: Path, *args: object, **kwargs: object) -> None:
        key = os.path.normcase(os.path.normpath(str(self)))
        target_key = os.path.normcase(os.path.normpath(str(target)))
        if key == target_key:
            raise PermissionError(5, "simulated access denied", str(self))
        return real_unlink(self, *args, **kwargs)

    def tracking_chmod(path: str | bytes | os.PathLike[str], mode: int) -> None:
        chmod_calls.append(Path(os.fsdecode(path)))
        raise AssertionError("chmod must not run for non-readonly PermissionError")

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    monkeypatch.setattr(os, "chmod", tracking_chmod)

    code = mod.run_cleanup(
        [
            "--reviewed-head",
            fx.reviewed_head,
            "--phase-branch",
            fx.phase_branch,
            "--phase-root",
            str(fx.phase_root),
            "--repo",
            str(fx.repo),
            "--phase-parent",
            str(fx.phase_parent),
        ]
    )
    captured = capsys.readouterr().out
    assert code != 0
    assert "Result: safely blocked" in captured
    assert chmod_calls == []
    assert target.exists()
    assert fx.phase_root.exists()


def _assert_cleanup_removed_phase(fx: PhaseFixture, result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "cleanup complete" in result.stdout
    assert not fx.phase_worktree.exists()
    assert not fx.phase_root.exists()
    branches = _git(fx.repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/").stdout.splitlines()
    assert branches == ["main"]
    head = _git(fx.repo, "rev-parse", "HEAD").stdout.strip().lower()
    origin = _git(fx.repo, "rev-parse", "origin/main").stdout.strip().lower()
    assert head == origin
    status = _git(fx.repo, "status", "--porcelain").stdout.strip()
    assert status == ""
    wt = _git(fx.repo, "worktree", "list", "--porcelain").stdout
    assert wt.count("worktree ") == 1


def test_legacy_flat_merged_phase_cleans_successfully(tmp_path: Path) -> None:
    """Registered worktree at phase_root (legacy-flat) cleans through the same gates."""
    fx = build_merged_phase_fixture(tmp_path, layout="legacy_flat")
    assert fx.phase_worktree == fx.phase_root
    porcelain = _git(fx.repo, "worktree", "list", "--porcelain").stdout
    expected = os.path.normcase(os.path.normpath(str(fx.phase_root)))
    assert any(
        os.path.normcase(os.path.normpath(line[len("worktree ") :])) == expected
        for line in porcelain.splitlines()
        if line.startswith("worktree ")
    )
    assert not (fx.phase_root / "worktree").exists()

    result = run_cleanup(fx)
    _assert_cleanup_removed_phase(fx, result)
    assert "Worktree topology: legacy_flat" in result.stdout
    assert "resolved worktree topology: legacy_flat" in result.stdout
    assert "removed phase worktree" in result.stdout
    assert "deleted phase branch with -d" in result.stdout
    assert "worktree remove --force" not in result.stdout
    assert "branch -D" not in result.stdout


def test_legacy_flat_wrong_branch_fails_closed(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, layout="legacy_flat")
    _git(fx.repo, "worktree", "remove", str(fx.phase_root))
    _git(fx.repo, "branch", "unrelated-branch", "main")
    _git(fx.repo, "worktree", "add", str(fx.phase_root), "unrelated-branch")
    cache = fx.phase_root / ".pytest_cache"
    cache.mkdir()
    marker = cache / "keep.bin"
    marker.write_bytes(b"keep")

    result = run_cleanup(fx)
    assert result.returncode == 9, result.stdout + result.stderr
    assert "worktree identity gate = failed" in result.stdout
    assert "refs/heads/unrelated-branch" in result.stdout
    assert fx.phase_root.exists()
    assert marker.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0
    assert "removed phase worktree" not in result.stdout
    assert "deleted phase branch" not in result.stdout


def test_legacy_flat_head_mismatch_fails_closed(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, layout="legacy_flat")
    old_main = _git(fx.repo, "rev-parse", "main").stdout.strip().lower()
    assert old_main != fx.reviewed_head
    _git(fx.repo, "worktree", "remove", str(fx.phase_root))
    _git(fx.repo, "worktree", "add", "--detach", str(fx.phase_root), old_main)

    result = run_cleanup(fx)
    assert result.returncode == 9, result.stdout + result.stderr
    assert "worktree identity gate = failed" in result.stdout
    assert fx.phase_root.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0


def test_legacy_flat_dirty_worktree_fails_closed(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, layout="legacy_flat")
    target = fx.phase_root / "phase.txt"
    original = target.read_text(encoding="utf-8")
    target.write_text(original + "dirty\n", encoding="utf-8")

    result = run_cleanup(fx)
    assert result.returncode != 0
    assert "tracked modifications" in result.stdout.lower() or "modifications" in result.stdout.lower()
    assert target.read_text(encoding="utf-8") == original + "dirty\n"
    assert fx.phase_root.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0


def test_legacy_flat_path_exists_but_not_registered_fails_closed(tmp_path: Path) -> None:
    fx = build_merged_phase_fixture(tmp_path, with_worktree=False)
    keep = fx.phase_root / "tmp"
    keep.mkdir()
    (keep / "execution.jsonl").write_text("x\n", encoding="utf-8")

    result = run_cleanup(fx, phase_worktree=fx.phase_root)
    assert result.returncode == 4, result.stdout + result.stderr
    assert "not registered" in result.stdout.lower()
    assert keep.exists()
    assert fx.phase_root.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0
    assert "removed phase worktree" not in result.stdout
    assert "deleted phase branch" not in result.stdout


def test_ambiguous_canonical_and_flat_topology_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fx = build_merged_phase_fixture(tmp_path)
    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    real_list = mod.list_worktree_entries

    def both_topologies(repo: Path) -> list[dict[str, str]]:
        entries = real_list(repo)
        entries.append(
            {
                "worktree": str(fx.phase_root),
                "HEAD": fx.reviewed_head,
                "branch": f"refs/heads/{fx.phase_branch}",
            }
        )
        return entries

    monkeypatch.setattr(mod, "list_worktree_entries", both_topologies)
    code = mod.run_cleanup(
        [
            "--reviewed-head",
            fx.reviewed_head,
            "--phase-branch",
            fx.phase_branch,
            "--phase-root",
            str(fx.phase_root),
            "--repo",
            str(fx.repo),
            "--phase-parent",
            str(fx.phase_parent),
        ]
    )
    captured = capsys.readouterr().out
    assert code == mod.EXIT_PATH_BOUNDARY
    assert "ambiguous phase worktree topology" in captured
    assert fx.phase_worktree.exists()
    assert fx.phase_root.exists()
    assert _git(
        fx.repo, "show-ref", "--verify", "--quiet", f"refs/heads/{fx.phase_branch}", check=False
    ).returncode == 0
    assert "removed phase worktree" not in captured
    assert "deleted phase branch" not in captured


def test_resolve_topology_uses_git_registration_not_directory_existence(tmp_path: Path) -> None:
    sys.path.insert(0, str(ENGINE.parent))
    import cleanup_merged_phase as mod

    phase_root = tmp_path / "sr-phases" / "phase-a"
    canonical = phase_root / "worktree"
    phase_root.mkdir(parents=True)
    canonical.mkdir()
    # Unregistered directories must not select legacy-flat.
    path, topology = mod.resolve_phase_worktree_topology(
        phase_root=phase_root,
        requested_worktree=None,
        entries=[],
    )
    assert topology == mod.TOPOLOGY_CANONICAL
    assert path == canonical

    with pytest.raises(mod.CleanupBlocked) as raised:
        mod.resolve_phase_worktree_topology(
            phase_root=phase_root,
            requested_worktree=tmp_path / "elsewhere",
            entries=[],
        )
    assert raised.value.code == mod.EXIT_PATH_BOUNDARY
