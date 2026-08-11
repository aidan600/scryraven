#!/usr/bin/env python3
"""Repository-owned post-merge local phase cleanup.

Operator command that inspects actual Git/filesystem state and safely removes
one explicitly identified, already-merged ScryRaven phase. Uses only the Python
standard library and the installed ``git`` CLI (never ``shell=True``).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_MERGE_GATE = 2
EXIT_GIT_STATE = 3
EXIT_UNSAFE_FS = 4
EXIT_GIT_OP = 5
EXIT_PATH_BOUNDARY = 6
EXIT_REVIEW_IDENTITY = 7
EXIT_INVARIANT = 8
EXIT_WORKTREE_IDENTITY = 9

SHA40_RE = re.compile(r"^[0-9a-fA-F]{40}$")

WORKTREE_DISPOSABLE_TOPS = frozenset(
    {".pytest_cache", ".ruff_cache", "tmp", "cache", "evidence", "final"}
)
PHASE_ROOT_DISPOSABLE_CHILDREN = frozenset({"cache", "tmp", "evidence", "final"})

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_READONLY = 0x1


class CleanupBlocked(Exception):
    """Safe failure with a nonzero exit code and operator message."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class GitResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def out(self) -> str:
        return self.stdout.strip()


@dataclass
class CleanupReport:
    repo: str = ""
    reviewed_head: str = ""
    phase_branch: str = ""
    phase_root: str = ""
    phase_parent: str = ""
    phase_worktree: str = ""
    remote: str = "origin"
    main_branch: str = "main"
    initial_ordinary_posture: str = ""
    initial_head: str = ""
    origin_main: str = ""
    merge_gate: str = ""
    review_identity: str = ""
    worktree_identity: str = ""
    actions: list[str] = field(default_factory=list)
    final_branch: str = ""
    final_status: str = ""
    final_head: str = ""
    final_origin_main: str = ""
    local_branches: list[str] = field(default_factory=list)
    worktrees: list[str] = field(default_factory=list)
    phase_branch_exists: str = ""
    phase_worktree_exists: str = ""
    phase_root_exists: str = ""
    result: str = ""
    blockers: list[str] = field(default_factory=list)
    exit_code: int = EXIT_OK

    def add_action(self, text: str) -> None:
        self.actions.append(text)

    def add_blocker(self, text: str) -> None:
        self.blockers.append(text)

    def render(self) -> str:
        lines = [
            "=== ScryRaven merged-phase cleanup ===",
            f"Repo: {self.repo}",
            f"Reviewed head: {self.reviewed_head}",
            f"Phase branch: {self.phase_branch}",
            f"Phase root: {self.phase_root}",
            f"Phase parent: {self.phase_parent}",
            f"Phase worktree: {self.phase_worktree}",
            f"Remote: {self.remote}",
            f"Main branch: {self.main_branch}",
            f"Initial ordinary branch / detached posture: {self.initial_ordinary_posture}",
            f"Initial HEAD: {self.initial_head}",
            f"origin/main: {self.origin_main}",
            f"Merge gate result: {self.merge_gate}",
            f"Review identity result: {self.review_identity}",
            f"Worktree identity result: {self.worktree_identity}",
            "Actions performed:",
        ]
        if self.actions:
            lines.extend(f"  - {a}" for a in self.actions)
        else:
            lines.append("  - (none)")
        lines.extend(
            [
                f"Final branch/status: {self.final_branch} / {self.final_status}",
                f"Final HEAD: {self.final_head}",
                f"Final origin/main: {self.final_origin_main}",
                "Local branches:",
            ]
        )
        if self.local_branches:
            lines.extend(f"  - {b}" for b in self.local_branches)
        else:
            lines.append("  - (none)")
        lines.append("Worktrees:")
        if self.worktrees:
            lines.extend(f"  - {w}" for w in self.worktrees)
        else:
            lines.append("  - (none)")
        lines.extend(
            [
                f"Phase branch exists: {self.phase_branch_exists}",
                f"Phase worktree exists: {self.phase_worktree_exists}",
                f"Phase root exists: {self.phase_root_exists}",
                f"Result: {self.result}",
                "Safe errors/blockers:",
            ]
        )
        if self.blockers:
            lines.extend(f"  - {b}" for b in self.blockers)
        else:
            lines.append("  - (none)")
        lines.append(f"Exit code: {self.exit_code}")
        return "\n".join(lines)


def lexical_normalize(path: Path) -> Path:
    """Absolute lexical normalization without following links."""
    if not path.is_absolute():
        raise CleanupBlocked(
            EXIT_PATH_BOUNDARY,
            f"path must be absolute: {path}",
        )
    return Path(os.path.normpath(str(path)))


def compare_key(path: Path) -> str:
    text = os.path.normpath(str(path))
    if os.name == "nt":
        return os.path.normcase(text)
    return text


def paths_equal(a: Path, b: Path) -> bool:
    return compare_key(a) == compare_key(b)


def is_direct_child(parent: Path, child: Path) -> bool:
    parent_n = lexical_normalize(parent)
    child_n = lexical_normalize(child)
    try:
        rel = Path(compare_key(child_n)).relative_to(Path(compare_key(parent_n)))
    except ValueError:
        return False
    return len(rel.parts) == 1 and rel.parts[0] not in (".", "..", "")


def is_strict_descendant(parent: Path, child: Path) -> bool:
    parent_n = lexical_normalize(parent)
    child_n = lexical_normalize(child)
    if paths_equal(parent_n, child_n):
        return False
    try:
        Path(compare_key(child_n)).relative_to(Path(compare_key(parent_n)))
        return True
    except ValueError:
        return False


def _lstat_no_follow(path: Path) -> os.stat_result | None:
    """lstat without following links.

    Returns None only when the path is genuinely absent.
    Any other OSError is indeterminate and must fail closed.
    """
    try:
        return os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as exc:
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"indeterminate filesystem state for {path}: {exc}",
        ) from exc


def lexists_no_follow(path: Path) -> bool:
    """True if path exists as a directory entry without following links."""
    return _lstat_no_follow(path) is not None


def is_dir_no_follow(path: Path) -> bool:
    """True if path is a real directory, not a symlink/reparse, without following."""
    st = _lstat_no_follow(path)
    if st is None:
        return False
    if stat.S_ISLNK(st.st_mode):
        return False
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    return stat.S_ISDIR(st.st_mode)


def is_reparse_or_symlink(path: Path) -> bool:
    st = _lstat_no_follow(path)
    if st is None:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return False


def reject_reparse(path: Path, label: str) -> None:
    if lexists_no_follow(path) and is_reparse_or_symlink(path):
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"{label} is a symlink/junction/reparse point: {path}",
        )


def default_repo_path() -> Path:
    return Path(__file__).resolve().parents[1]


def default_phase_parent(repo: Path) -> Path:
    return lexical_normalize(repo.parent / "sr-phases")


def run_git(
    repo: Path,
    args: Sequence[str],
    *,
    check: bool = False,
) -> GitResult:
    cmd = ["git", "-C", str(repo), *args]
    # Guardrails: never invoke forbidden operations (argument-array checks only).
    if args and args[0] in {"reset", "rebase", "clean"}:
        raise CleanupBlocked(EXIT_GIT_OP, f"forbidden git operation refused: {args[0]}")
    if args[:2] == ["branch", "-D"] or args[:3] == ["branch", "--delete", "--force"]:
        raise CleanupBlocked(EXIT_GIT_OP, "forbidden git branch -D refused")
    if "worktree" in args and "remove" in args and "--force" in args:
        raise CleanupBlocked(EXIT_GIT_OP, "forbidden git worktree remove --force refused")
    if args and args[0] == "push" and ("--force" in args or "-f" in args):
        raise CleanupBlocked(EXIT_GIT_OP, "forbidden force push refused")

    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    result = GitResult(
        args=list(args),
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
    if check and not result.ok:
        detail = (result.stderr or result.stdout or "").strip()
        raise CleanupBlocked(
            EXIT_GIT_OP,
            f"git {' '.join(args)} failed ({result.returncode}): {detail}",
        )
    return result


def run_git_in(
    worktree: Path,
    args: Sequence[str],
    *,
    check: bool = False,
) -> GitResult:
    return run_git(worktree, args, check=check)


def require_git_worktree(repo: Path) -> None:
    if not repo.is_dir():
        raise CleanupBlocked(EXIT_PATH_BOUNDARY, f"repo does not exist: {repo}")
    reject_reparse(repo, "repo")
    probe = run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    if not probe.ok or probe.out != "true":
        raise CleanupBlocked(EXIT_PATH_BOUNDARY, f"repo is not a Git working tree: {repo}")


def validate_phase_branch_name(repo: Path, branch: str, main_branch: str) -> None:
    if not branch or branch.startswith("-"):
        raise CleanupBlocked(EXIT_USAGE, f"invalid phase branch name: {branch!r}")
    if branch == main_branch:
        raise CleanupBlocked(EXIT_USAGE, "phase branch must not equal main branch")
    check = run_git(repo, ["check-ref-format", "--branch", branch])
    if not check.ok:
        raise CleanupBlocked(
            EXIT_USAGE,
            f"invalid phase branch name (git check-ref-format): {branch!r}",
        )


def validate_reviewed_head(value: str) -> str:
    text = value.strip().lower()
    if not SHA40_RE.fullmatch(text):
        raise CleanupBlocked(
            EXIT_USAGE,
            "reviewed-head must be an exact 40-character commit SHA",
        )
    return text


def prove_phase_path_boundaries(
    *,
    repo: Path,
    phase_parent: Path,
    phase_root: Path,
    phase_worktree: Path,
) -> tuple[Path, Path, Path, Path]:
    repo_n = lexical_normalize(repo)
    parent_n = lexical_normalize(phase_parent)
    root_n = lexical_normalize(phase_root)
    wt_n = lexical_normalize(phase_worktree)

    if paths_equal(root_n, repo_n):
        raise CleanupBlocked(EXIT_PATH_BOUNDARY, "phase root must not equal repo")
    if paths_equal(root_n, lexical_normalize(repo_n.parent)):
        raise CleanupBlocked(EXIT_PATH_BOUNDARY, "phase root must not equal repo parent")
    if is_strict_descendant(root_n, repo_n):
        raise CleanupBlocked(
            EXIT_PATH_BOUNDARY,
            "phase root must not be an ancestor of repo",
        )
    if is_strict_descendant(repo_n, root_n):
        raise CleanupBlocked(
            EXIT_PATH_BOUNDARY,
            "phase root must not be inside the ordinary repo",
        )
    if paths_equal(root_n, parent_n):
        raise CleanupBlocked(
            EXIT_PATH_BOUNDARY,
            "phase root must not equal the trusted phase parent",
        )
    if not is_direct_child(parent_n, root_n):
        raise CleanupBlocked(
            EXIT_PATH_BOUNDARY,
            "phase root must be a direct child of the trusted phase parent",
        )
    expected_wt = lexical_normalize(root_n / "worktree")
    if not paths_equal(wt_n, expected_wt):
        raise CleanupBlocked(
            EXIT_PATH_BOUNDARY,
            "phase worktree must be exactly <phase-root>/worktree",
        )
    # Reject any reparse on existing path components used for deletion authority.
    for label, path in (
        ("phase parent", parent_n),
        ("phase root", root_n),
        ("phase worktree", wt_n),
    ):
        if lexists_no_follow(path):
            reject_reparse(path, label)
            # Also reject reparse on each existing ancestor component under parent.
            _reject_reparse_components(path, stop_at=parent_n.parent)

    return repo_n, parent_n, root_n, wt_n


def _reject_reparse_components(path: Path, *, stop_at: Path) -> None:
    current = lexical_normalize(path)
    stop = lexical_normalize(stop_at)
    while True:
        if lexists_no_follow(current):
            reject_reparse(current, f"path component {current}")
        if paths_equal(current, stop) or current.parent == current:
            break
        current = current.parent


def parse_worktree_porcelain(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        if " " in line:
            key, value = line.split(" ", 1)
        else:
            key, value = line, ""
        current[key] = value
    if current:
        entries.append(current)
    return entries


def find_worktree_entry(
    repo: Path, target: Path
) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
    listed = run_git(repo, ["worktree", "list", "--porcelain"], check=True)
    entries = parse_worktree_porcelain(listed.stdout)
    match = None
    for entry in entries:
        path_text = entry.get("worktree")
        if not path_text:
            continue
        if paths_equal(lexical_normalize(Path(path_text)), target):
            match = entry
            break
    return match, entries


def ordinary_head_state(repo: Path) -> tuple[str, str, bool]:
    """Return (posture_label, head_sha, detached)."""
    head_sha = run_git(repo, ["rev-parse", "HEAD"], check=True).out.lower()
    symbolic = run_git(repo, ["symbolic-ref", "-q", "HEAD"])
    if symbolic.ok:
        ref = symbolic.out
        if ref.startswith("refs/heads/"):
            branch = ref[len("refs/heads/") :]
            return branch, head_sha, False
        return ref, head_sha, False
    return "detached", head_sha, True


def working_tree_dirty(repo: Path) -> bool:
    status = run_git(repo, ["status", "--porcelain"], check=True)
    return bool(status.stdout.strip())


def ensure_ordinary_on_main(
    repo: Path,
    main_branch: str,
    phase_branch: str,
    reviewed_head: str,
    report: CleanupReport,
) -> None:
    posture, head, detached = ordinary_head_state(repo)
    report.initial_ordinary_posture = posture
    report.initial_head = head
    if working_tree_dirty(repo):
        raise CleanupBlocked(
            EXIT_GIT_STATE,
            "ordinary checkout is dirty; refuse stash/reset/clean",
        )
    if detached:
        # Safe recovery for the recurring clean detached ordinary checkout.
        switch = run_git(repo, ["switch", main_branch])
        if not switch.ok:
            detail = (switch.stderr or switch.stdout).strip()
            raise CleanupBlocked(
                EXIT_GIT_STATE,
                f"detached ordinary checkout could not switch to {main_branch}: {detail}",
            )
        report.add_action(f"switched detached ordinary checkout to {main_branch}")
        return
    if (
        posture == phase_branch
        and head == reviewed_head
        and report.merge_gate == "passed"
        and report.review_identity == "passed"
    ):
        # This recovery is deliberately available only after the caller has
        # proven both the reviewed commit's merge and the phase branch's exact
        # review identity. Branch-name equality alone is never authorization.
        switch = run_git(repo, ["switch", main_branch])
        if not switch.ok:
            detail = (switch.stderr or switch.stdout).strip()
            raise CleanupBlocked(
                EXIT_GIT_STATE,
                "exact reviewed merged phase branch ordinary checkout could not "
                f"switch to {main_branch}: {detail}",
            )
        report.add_action(
            "switched exact reviewed merged phase branch ordinary checkout to "
            f"{main_branch}"
        )
        return
    if posture != main_branch:
        raise CleanupBlocked(
            EXIT_GIT_STATE,
            f"ordinary checkout is on unexpected branch {posture!r}; refuse silent switch",
        )


def merge_gate(
    repo: Path, remote: str, main_branch: str, reviewed_head: str, report: CleanupReport
) -> str:
    fetch = run_git(repo, ["fetch", remote, "--prune"], check=True)
    report.add_action(f"git fetch {remote} --prune")
    _ = fetch
    origin_ref = f"{remote}/{main_branch}"
    origin_sha = run_git(repo, ["rev-parse", origin_ref], check=True).out.lower()
    report.origin_main = origin_sha
    # Prove exact reviewed head exists.
    exists = run_git(repo, ["cat-file", "-e", f"{reviewed_head}^{{commit}}"])
    if not exists.ok:
        report.merge_gate = "failed (reviewed head unknown)"
        raise CleanupBlocked(
            EXIT_MERGE_GATE,
            f"reviewed head is not a known commit: {reviewed_head}",
        )
    anc = run_git(
        repo, ["merge-base", "--is-ancestor", reviewed_head, origin_ref]
    )
    if not anc.ok:
        report.merge_gate = "failed (reviewed head not in origin/main)"
        raise CleanupBlocked(
            EXIT_MERGE_GATE,
            "merge gate failed: reviewed head is not an ancestor of "
            f"{origin_ref}; no worktree/branch/phase-root deletion authorized",
        )
    report.merge_gate = "passed"
    report.add_action(
        f"merge gate passed: {reviewed_head} is ancestor of {origin_ref}"
    )
    return origin_sha


def review_identity_gate(
    repo: Path, phase_branch: str, reviewed_head: str, report: CleanupReport
) -> None:
    tip = run_git(repo, ["rev-parse", "--verify", f"refs/heads/{phase_branch}^{{commit}}"])
    if not tip.ok:
        report.review_identity = "satisfied (phase branch absent)"
        report.add_action("review identity: phase branch absent (no-op)")
        return
    tip_sha = tip.out.lower()
    if tip_sha != reviewed_head.lower():
        report.review_identity = "failed (identity mismatch)"
        raise CleanupBlocked(
            EXIT_REVIEW_IDENTITY,
            "phase-branch review-identity gate failed: "
            f"reviewed head={reviewed_head} current tip={tip_sha}",
        )
    report.review_identity = "passed"
    report.add_action(
        f"review identity passed: refs/heads/{phase_branch} == {reviewed_head}"
    )


def sync_main_ff_only(
    repo: Path, remote: str, main_branch: str, report: CleanupReport
) -> None:
    origin_ref = f"{remote}/{main_branch}"
    before = run_git(repo, ["rev-parse", "HEAD"], check=True).out.lower()
    merge = run_git(repo, ["merge", "--ff-only", origin_ref])
    if not merge.ok:
        detail = (merge.stderr or merge.stdout).strip()
        raise CleanupBlocked(
            EXIT_GIT_OP,
            f"fast-forward sync of {main_branch} failed: {detail}",
        )
    after = run_git(repo, ["rev-parse", "HEAD"], check=True).out.lower()
    origin_sha = run_git(repo, ["rev-parse", origin_ref], check=True).out.lower()
    if after != origin_sha:
        raise CleanupBlocked(
            EXIT_GIT_STATE,
            f"HEAD ({after}) != {origin_ref} ({origin_sha}) after ff-only sync",
        )
    if before == after:
        report.add_action(f"{main_branch} already synchronized with {origin_ref}")
    else:
        report.add_action(f"fast-forwarded {main_branch} to {origin_ref} ({after})")


def _path_under_allowlisted_root(rel: Path) -> bool:
    if not rel.parts:
        return False
    top = rel.parts[0]
    if top in WORKTREE_DISPOSABLE_TOPS:
        return True
    if "__pycache__" in rel.parts:
        return True
    return False


def classify_ignored_path(rel_text: str) -> bool:
    """Return True when an ignored path is allowlisted for deletion."""
    rel = Path(rel_text.replace("\\", "/"))
    return _path_under_allowlisted_root(rel)


def list_ignored_paths(worktree: Path) -> list[str]:
    # --ignored shows ignored entries as '!! path'
    status = run_git_in(
        worktree,
        ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"],
        check=True,
    )
    ignored: list[str] = []
    for line in status.stdout.splitlines():
        if line.startswith("!! "):
            ignored.append(line[3:])
    return ignored


def list_dirty_and_untracked(worktree: Path) -> tuple[list[str], list[str]]:
    status = run_git_in(
        worktree, ["status", "--porcelain=v1", "--untracked-files=all"], check=True
    )
    dirty: list[str] = []
    untracked: list[str] = []
    for line in status.stdout.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[3:] if len(line) > 3 else ""
        if code == "??":
            untracked.append(path)
        else:
            dirty.append(f"{code} {path}".strip())
    return dirty, untracked


def _rmtree_no_follow(path: Path) -> None:
    """Recursively delete worktree ignored artifacts without following links.

    Any nested symlink/junction/reparse under an ignored worktree path fails closed.
    """
    if not lexists_no_follow(path):
        return
    reject_reparse(path, "delete target")
    if is_dir_no_follow(path) and not path.is_symlink():
        # Walk top-down; reject any reparse/symlink entry before descending.
        for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
            root_path = Path(root)
            reject_reparse(root_path, "walked directory")
            keep_dirs: list[str] = []
            for name in dirs:
                child = root_path / name
                if is_reparse_or_symlink(child):
                    raise CleanupBlocked(
                        EXIT_UNSAFE_FS,
                        f"symlink/junction/reparse under disposable path: {child}",
                    )
                keep_dirs.append(name)
            dirs[:] = keep_dirs
            for name in files:
                child = root_path / name
                if is_reparse_or_symlink(child):
                    raise CleanupBlocked(
                        EXIT_UNSAFE_FS,
                        f"symlink/junction/reparse file under disposable path: {child}",
                    )
        shutil.rmtree(path)
    else:
        path.unlink()


def _remove_link_object_no_follow(path: Path) -> None:
    """Remove a symlink/junction/reparse leaf object without traversing its target."""
    if not is_reparse_or_symlink(path):
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"expected symlink/junction/reparse leaf at {path}",
        )
    # Symlinks usually unlink; Windows directory junctions typically need rmdir.
    try:
        os.unlink(path)
        return
    except OSError:
        pass
    try:
        os.rmdir(path)
        return
    except OSError as exc:
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"unable to remove nested link/reparse object without traversal: {path}: {exc}",
        ) from exc


def _rmtree_phase_root_disposable_child(path: Path) -> None:
    """Delete a real phase-root disposable child.

    The immediate path must be a normal directory (not a reparse). Nested
    symlink/junction/reparse entries are removed as leaf link objects only —
    never enumerated or followed into their targets.
    """
    if not lexists_no_follow(path):
        return
    if is_reparse_or_symlink(path):
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"phase-root disposable child is symlink/reparse: {path}",
        )
    if not is_dir_no_follow(path):
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"phase-root disposable child is not a directory: {path}",
        )

    def _delete_entry(entry: Path) -> None:
        st = _lstat_no_follow(entry)
        if st is None:
            return
        # Identify links before any directory enumeration to avoid target traversal.
        if is_reparse_or_symlink(entry):
            _remove_link_object_no_follow(entry)
            return
        if stat.S_ISDIR(st.st_mode):
            try:
                children = list(entry.iterdir())
            except OSError as exc:
                raise CleanupBlocked(
                    EXIT_UNSAFE_FS,
                    f"unable to enumerate disposable path {entry}: {exc}",
                ) from exc
            for child in children:
                _delete_entry(child)
            try:
                entry.rmdir()
            except OSError as exc:
                raise CleanupBlocked(
                    EXIT_UNSAFE_FS,
                    f"unable to remove disposable directory {entry}: {exc}",
                ) from exc
            return
        _unlink_phase_root_regular_file(entry, st)

    _delete_entry(path)




def _unlink_phase_root_regular_file(path: Path, st: os.stat_result) -> None:
    """Unlink an authorized phase-root disposable regular file.

    On Windows, if the first unlink fails and the file mechanically carries
    FILE_ATTRIBUTE_READONLY, clear only that bit and retry unlink once.
    Generic PermissionError without a proven read-only attribute fails closed.
    """
    if is_reparse_or_symlink(path):
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"refusing unlink of reparse/symlink as regular file: {path}",
        )
    if not stat.S_ISREG(st.st_mode):
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"refusing non-regular disposable entry as file: {path}",
        )
    try:
        path.unlink()
        return
    except OSError as first_exc:
        # Re-inspect without following links; unknown state remains fail-closed.
        st2 = _lstat_no_follow(path)
        if st2 is None:
            return
        if is_reparse_or_symlink(path) or not stat.S_ISREG(st2.st_mode):
            raise CleanupBlocked(
                EXIT_UNSAFE_FS,
                f"unable to remove disposable file {path}: {first_exc}",
            ) from first_exc
        attrs = getattr(st2, "st_file_attributes", 0)
        if os.name != "nt" or not (attrs & FILE_ATTRIBUTE_READONLY):
            raise CleanupBlocked(
                EXIT_UNSAFE_FS,
                f"unable to remove disposable file {path}: {first_exc}",
            ) from first_exc
        try:
            # Clear only the Windows read-only posture; do not alter ACLs/ownership.
            os.chmod(path, stat.S_IWRITE)
        except OSError as chmod_exc:
            raise CleanupBlocked(
                EXIT_UNSAFE_FS,
                f"unable to clear read-only attribute on disposable file {path}: {chmod_exc}",
            ) from chmod_exc
        try:
            path.unlink()
        except OSError as retry_exc:
            raise CleanupBlocked(
                EXIT_UNSAFE_FS,
                f"unable to remove disposable file after clearing read-only {path}: {retry_exc}",
            ) from retry_exc


def remove_allowlisted_ignored(worktree: Path, ignored: Iterable[str], report: CleanupReport) -> None:
    # Delete deepest paths first so parents can be removed after children.
    rel_paths = sorted({p.replace("\\", "/") for p in ignored}, key=lambda s: s.count("/"), reverse=True)
    unknown = [p for p in rel_paths if not classify_ignored_path(p)]
    if unknown:
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            "unknown ignored artifact(s) outside allowlist: " + ", ".join(unknown),
        )
    # Prefer deleting top-level allowlisted disposable roots/directories once.
    tops: set[str] = set()
    for rel in rel_paths:
        parts = Path(rel).parts
        if not parts:
            continue
        if parts[0] in WORKTREE_DISPOSABLE_TOPS:
            tops.add(parts[0])
        elif "__pycache__" in parts:
            # Delete the __pycache__ directory itself.
            idx = parts.index("__pycache__")
            tops.add(str(Path(*parts[: idx + 1])))
    for top in sorted(tops, key=lambda s: s.count("/"), reverse=True):
        target = worktree / top
        if lexists_no_follow(target):
            _rmtree_no_follow(target)
            report.add_action(f"removed allowlisted ignored path: {top}")


def prove_registered_worktree_identity(
    entry: dict[str, str],
    *,
    phase_worktree: Path,
    phase_branch: str,
    reviewed_head: str,
    report: CleanupReport,
) -> None:
    """Bind registered worktree path/branch/HEAD to the exact reviewed phase."""
    expected_branch = f"refs/heads/{phase_branch}"
    expected_head = reviewed_head.lower()
    registered_path = entry.get("worktree", "")
    registered_branch = entry.get("branch", "")
    registered_head = (entry.get("HEAD") or "").strip().lower()
    detached = "detached" in entry and not registered_branch

    def _fail(reason: str) -> None:
        report.worktree_identity = "failed"
        raise CleanupBlocked(
            EXIT_WORKTREE_IDENTITY,
            "worktree identity gate = failed: "
            f"{reason}; "
            f"expected phase branch={expected_branch}; "
            f"registered worktree branch={registered_branch or ('detached' if detached else '(missing)')}; "
            f"expected reviewed head={expected_head}; "
            f"registered worktree HEAD={registered_head or '(missing)'}",
        )

    if not registered_path:
        _fail("registered worktree path missing")
    if not paths_equal(lexical_normalize(Path(registered_path)), phase_worktree):
        _fail("registered worktree path does not match expected phase worktree")
    if detached or not registered_branch:
        _fail("registered worktree is detached or missing branch field")
    if registered_branch != expected_branch:
        _fail("registered worktree branch does not equal expected phase branch")
    if not registered_head:
        _fail("registered worktree HEAD missing")
    if registered_head != expected_head:
        _fail("registered worktree HEAD does not equal reviewed head")

    report.worktree_identity = "passed"
    report.add_action(
        "worktree identity passed: "
        f"path={phase_worktree}; branch={expected_branch}; HEAD={expected_head}"
    )


def cleanup_phase_worktree(
    repo: Path,
    phase_worktree: Path,
    *,
    phase_branch: str,
    reviewed_head: str,
    report: CleanupReport,
) -> None:
    entry, _entries = find_worktree_entry(repo, phase_worktree)
    path_exists = lexists_no_follow(phase_worktree)

    if entry is None and not path_exists:
        report.worktree_identity = "satisfied (phase worktree absent)"
        report.add_action("phase worktree already absent (satisfied)")
        return

    if entry is None and path_exists:
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            "phase worktree path exists but is not registered in git worktree list; "
            "refuse blind recursive deletion",
        )

    assert entry is not None
    if not path_exists:
        prune = run_git(repo, ["worktree", "prune"], check=True)
        _ = prune
        report.add_action("pruned stale worktree metadata (path absent)")
        entry2, _ = find_worktree_entry(repo, phase_worktree)
        if entry2 is None and not lexists_no_follow(phase_worktree):
            report.worktree_identity = "satisfied (phase worktree absent)"
            report.add_action("phase worktree absent after prune (satisfied)")
            return
        raise CleanupBlocked(
            EXIT_GIT_STATE,
            "stale worktree metadata remained after prune",
        )

    reject_reparse(phase_worktree, "phase worktree")
    # Identity gate must pass before any ignored-artifact deletion or removal.
    prove_registered_worktree_identity(
        entry,
        phase_worktree=phase_worktree,
        phase_branch=phase_branch,
        reviewed_head=reviewed_head,
        report=report,
    )

    dirty, untracked = list_dirty_and_untracked(phase_worktree)
    if dirty:
        raise CleanupBlocked(
            EXIT_GIT_STATE,
            "phase worktree has tracked modifications: " + "; ".join(dirty),
        )
    if untracked:
        raise CleanupBlocked(
            EXIT_GIT_STATE,
            "phase worktree has untracked nonignored files: " + "; ".join(untracked),
        )

    ignored = list_ignored_paths(phase_worktree)
    if ignored:
        remove_allowlisted_ignored(phase_worktree, ignored, report)

    # Re-check ignored leftovers after allowlisted deletion.
    ignored_after = list_ignored_paths(phase_worktree)
    if ignored_after:
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            "ignored leftovers remain after allowlisted cleanup: "
            + ", ".join(ignored_after),
        )

    remove = run_git(repo, ["worktree", "remove", str(phase_worktree)])
    if not remove.ok:
        detail = (remove.stderr or remove.stdout).strip()
        raise CleanupBlocked(
            EXIT_GIT_OP,
            f"git worktree remove failed (no --force fallback): {detail}",
        )
    report.add_action(f"removed phase worktree: {phase_worktree}")


def delete_phase_branch(repo: Path, phase_branch: str, report: CleanupReport) -> None:
    exists = run_git(repo, ["show-ref", "--verify", "--quiet", f"refs/heads/{phase_branch}"])
    if not exists.ok:
        report.add_action(f"phase branch already absent: {phase_branch} (satisfied)")
        return
    deleted = run_git(repo, ["branch", "-d", "--", phase_branch])
    if not deleted.ok:
        detail = (deleted.stderr or deleted.stdout).strip()
        raise CleanupBlocked(
            EXIT_GIT_OP,
            f"git branch -d refused for {phase_branch}: {detail}",
        )
    report.add_action(f"deleted phase branch with -d: {phase_branch}")


def cleanup_phase_root(phase_root: Path, report: CleanupReport) -> None:
    if not lexists_no_follow(phase_root):
        report.add_action("phase root already absent (satisfied)")
        return
    reject_reparse(phase_root, "phase root")
    if not is_dir_no_follow(phase_root):
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            f"phase root exists but is not a directory: {phase_root}",
        )

    # Enumerate immediate children by name only.
    try:
        children = list(phase_root.iterdir())
    except OSError as exc:
        raise CleanupBlocked(
            EXIT_UNSAFE_FS, f"unable to enumerate phase root: {exc}"
        ) from exc

    for child in children:
        name = child.name
        if name not in PHASE_ROOT_DISPOSABLE_CHILDREN:
            raise CleanupBlocked(
                EXIT_UNSAFE_FS,
                f"unexpected phase-root entry (fail closed): {child}",
            )
        if is_reparse_or_symlink(child):
            raise CleanupBlocked(
                EXIT_UNSAFE_FS,
                f"phase-root child is symlink/reparse: {child}",
            )
        # Immediate child is a real directory. Nested link/reparse leaves may be
        # removed as objects without following their targets.
        _rmtree_phase_root_disposable_child(child)
        report.add_action(f"removed phase-root disposable child: {name}")

    # Remove phase root only when empty.
    remaining = list(phase_root.iterdir()) if lexists_no_follow(phase_root) else []
    if remaining:
        raise CleanupBlocked(
            EXIT_UNSAFE_FS,
            "phase root not empty after disposable-child removal: "
            + ", ".join(p.name for p in remaining),
        )
    phase_root.rmdir()
    report.add_action(f"removed empty phase root: {phase_root}")


def list_local_branches(repo: Path) -> list[str]:
    result = run_git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads/"], check=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def verify_final_invariants(
    repo: Path,
    *,
    remote: str,
    main_branch: str,
    phase_branch: str,
    phase_worktree: Path,
    phase_root: Path,
    report: CleanupReport,
) -> None:
    posture, head, detached = ordinary_head_state(repo)
    origin_sha = run_git(repo, ["rev-parse", f"{remote}/{main_branch}"], check=True).out.lower()
    report.final_branch = "detached" if detached else posture
    report.final_head = head
    report.final_origin_main = origin_sha
    report.final_status = (
        "dirty" if working_tree_dirty(repo) else "clean"
    )
    branches = list_local_branches(repo)
    report.local_branches = branches
    _entry, entries = find_worktree_entry(repo, phase_worktree)
    report.worktrees = [
        f"{e.get('worktree', '?')} {e.get('HEAD', '')} {e.get('branch', e.get('detached', ''))}".strip()
        for e in entries
    ]
    branch_exists = run_git(
        repo, ["show-ref", "--verify", "--quiet", f"refs/heads/{phase_branch}"]
    ).ok
    report.phase_branch_exists = "yes" if branch_exists else "no"
    wt_registered, _ = find_worktree_entry(repo, phase_worktree)
    wt_exists = lexists_no_follow(phase_worktree)
    report.phase_worktree_exists = (
        "yes" if (wt_registered is not None or wt_exists) else "no"
    )
    report.phase_root_exists = (
        "yes" if lexists_no_follow(phase_root) else "no"
    )

    blockers: list[str] = []
    if detached or posture != main_branch:
        blockers.append(f"ordinary branch must be {main_branch}, found {report.final_branch}")
    if head != origin_sha:
        blockers.append(f"HEAD ({head}) != {remote}/{main_branch} ({origin_sha})")
    if report.final_status != "clean":
        blockers.append("ordinary working tree is dirty")
    unexpected_branches = [b for b in branches if b != main_branch]
    if unexpected_branches:
        blockers.append(
            "local branches must be main only; unrelated branches remain: "
            + ", ".join(unexpected_branches)
        )
    if len(entries) != 1:
        blockers.append(
            f"registered worktrees must be exactly one; found {len(entries)}"
        )
    if branch_exists:
        blockers.append(f"phase branch still exists: {phase_branch}")
    if wt_registered is not None or wt_exists:
        blockers.append(f"phase worktree still present: {phase_worktree}")
    if lexists_no_follow(phase_root):
        blockers.append(f"phase root still present: {phase_root}")

    if blockers:
        for b in blockers:
            report.add_blocker(b)
        raise CleanupBlocked(
            EXIT_INVARIANT,
            "final invariants failed: " + "; ".join(blockers),
        )


def build_parser() -> argparse.ArgumentParser:
    class _CleanupArgumentParser(argparse.ArgumentParser):
        """Convert argparse usage errors into controlled CleanupBlocked failures."""

        def error(self, message: str) -> None:  # type: ignore[override]
            raise CleanupBlocked(EXIT_USAGE, f"invalid arguments: {message}")

    parser = _CleanupArgumentParser(
        description="Safely clean one explicitly identified merged ScryRaven phase.",
        allow_abbrev=False,
    )
    parser.add_argument("--reviewed-head", required=True, help="Exact 40-char reviewed phase head SHA")
    parser.add_argument("--phase-branch", required=True, help="Local phase branch name")
    parser.add_argument("--phase-root", required=True, help="Absolute phase root path")
    parser.add_argument(
        "--repo",
        default=None,
        help="Ordinary repository path (default: repository containing this script)",
    )
    parser.add_argument("--remote", default="origin", help="Remote name (default: origin)")
    parser.add_argument("--main-branch", default="main", help="Main branch name (default: main)")
    parser.add_argument(
        "--phase-parent",
        default=None,
        help="Trusted phase-parent directory (default: <repo-parent>/sr-phases)",
    )
    parser.add_argument(
        "--phase-worktree",
        default=None,
        help="Optional override; must equal <phase-root>/worktree",
    )
    return parser


def run_cleanup(argv: Sequence[str] | None = None) -> int:
    report = CleanupReport()
    try:
        args = build_parser().parse_args(argv)
        reviewed_head = validate_reviewed_head(args.reviewed_head)
        repo = lexical_normalize(Path(args.repo) if args.repo else default_repo_path())
        remote = args.remote
        main_branch = args.main_branch
        phase_branch = args.phase_branch
        phase_parent = lexical_normalize(
            Path(args.phase_parent) if args.phase_parent else default_phase_parent(repo)
        )
        phase_root = lexical_normalize(Path(args.phase_root))
        phase_worktree = lexical_normalize(
            Path(args.phase_worktree) if args.phase_worktree else phase_root / "worktree"
        )

        report.repo = str(repo)
        report.reviewed_head = reviewed_head
        report.phase_branch = phase_branch
        report.phase_root = str(phase_root)
        report.phase_parent = str(phase_parent)
        report.phase_worktree = str(phase_worktree)
        report.remote = remote
        report.main_branch = main_branch

        require_git_worktree(repo)
        validate_phase_branch_name(repo, phase_branch, main_branch)
        repo, phase_parent, phase_root, phase_worktree = prove_phase_path_boundaries(
            repo=repo,
            phase_parent=phase_parent,
            phase_root=phase_root,
            phase_worktree=phase_worktree,
        )
        report.repo = str(repo)
        report.phase_parent = str(phase_parent)
        report.phase_root = str(phase_root)
        report.phase_worktree = str(phase_worktree)

        merge_gate(repo, remote, main_branch, reviewed_head, report)
        review_identity_gate(repo, phase_branch, reviewed_head, report)
        ensure_ordinary_on_main(
            repo,
            main_branch,
            phase_branch,
            reviewed_head,
            report,
        )
        sync_main_ff_only(repo, remote, main_branch, report)

        cleanup_phase_worktree(
            repo,
            phase_worktree,
            phase_branch=phase_branch,
            reviewed_head=reviewed_head,
            report=report,
        )
        delete_phase_branch(repo, phase_branch, report)
        cleanup_phase_root(phase_root, report)

        verify_final_invariants(
            repo,
            remote=remote,
            main_branch=main_branch,
            phase_branch=phase_branch,
            phase_worktree=phase_worktree,
            phase_root=phase_root,
            report=report,
        )

        destructive = any(
            a.startswith(
                (
                    "removed ",
                    "deleted ",
                    "fast-forwarded ",
                    "switched ",
                    "pruned ",
                )
            )
            for a in report.actions
        )
        report.result = (
            "already satisfied / no-op success"
            if not destructive
            else "cleanup complete"
        )
        report.exit_code = EXIT_OK
        return EXIT_OK
    except CleanupBlocked as exc:
        report.result = "safely blocked"
        report.exit_code = exc.code
        report.add_blocker(exc.message)
        # Best-effort final snapshot fields.
        try:
            if report.repo:
                repo_path = Path(report.repo)
                if repo_path.is_dir():
                    posture, head, detached = ordinary_head_state(repo_path)
                    report.final_branch = "detached" if detached else posture
                    report.final_head = head
                    report.final_status = (
                        "dirty" if working_tree_dirty(repo_path) else "clean"
                    )
                    report.local_branches = list_local_branches(repo_path)
                    _e, entries = find_worktree_entry(
                        repo_path, Path(report.phase_worktree or repo_path)
                    )
                    report.worktrees = [
                        e.get("worktree", "?") for e in entries
                    ]
                    if report.phase_branch:
                        report.phase_branch_exists = (
                            "yes"
                            if run_git(
                                repo_path,
                                [
                                    "show-ref",
                                    "--verify",
                                    "--quiet",
                                    f"refs/heads/{report.phase_branch}",
                                ],
                            ).ok
                            else "no"
                        )
                    if report.phase_worktree:
                        pwt = Path(report.phase_worktree)
                        reg, _ = find_worktree_entry(repo_path, pwt)
                        report.phase_worktree_exists = (
                            "yes" if reg is not None or lexists_no_follow(pwt) else "no"
                        )
                    if report.phase_root:
                        report.phase_root_exists = (
                            "yes"
                            if lexists_no_follow(Path(report.phase_root))
                            else "no"
                        )
                    if not report.final_origin_main and report.remote and report.main_branch:
                        om = run_git(
                            repo_path,
                            ["rev-parse", f"{report.remote}/{report.main_branch}"],
                        )
                        if om.ok:
                            report.final_origin_main = om.out.lower()
                            if not report.origin_main:
                                report.origin_main = report.final_origin_main
        except Exception as snap_exc:  # noqa: BLE001 - best-effort snapshot only
            report.add_blocker(f"final snapshot incomplete: {snap_exc}")
        return exc.code
    except Exception as exc:  # noqa: BLE001 - always print a summary
        report.result = "unexpected failure"
        report.exit_code = EXIT_USAGE
        report.add_blocker(f"unexpected error: {exc}")
        return EXIT_USAGE
    finally:
        print(report.render())


def main() -> None:
    raise SystemExit(run_cleanup())


if __name__ == "__main__":
    main()
