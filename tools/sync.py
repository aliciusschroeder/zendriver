#!/usr/bin/env python3
"""Snapshot all bug-hunt work into the state worktree and push it.

Run every ~5 minutes by tools/sync-loop.sh. Safe to run by hand at any time:
  python3 /home/user/bughunt-state/tools/sync.py

What it saves (see README.md for the layout):
  * the supervisor scratchpad (probes, tests, triage, stage outputs); prototype
    package copies (`pkg/zendriver`) are stored as patches against the base commit
  * Claude transcripts: the supervisor session, every workflow journal, every
    agent transcript, the workflow scripts, background task outputs
  * every extra git worktree: named branches are force-pushed as-is, and any
    uncommitted work is snapshotted (without touching the agent's index or
    branch) and force-pushed to refs/heads/wip/<name>
  * STATUS.md: a generated overview of workflows, agents, worktrees and pushes
It never deletes anything from the state dir, so a wiped source cannot wipe the
snapshot.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path("/home/user/zendriver")
STATE = Path("/home/user/bughunt-state")
DESIGNATED = "ccr-9a8a26e1-b0l7bh"
STATE_BRANCH = "ccr-9a8a26e1-b0l7bh-state"
BASE_COMMIT = "064148f"  # designated branch before any bug-hunt fix
SESSION = "b2021b39-94e6-5220-9e66-7f33c0314a80"
SCR = Path(f"/tmp/claude-0/-home-user-zendriver/{SESSION}/scratchpad")
TASKS = Path(f"/tmp/claude-0/-home-user-zendriver/{SESSION}/tasks")
CLAUDE_PROJ = Path("/root/.claude/projects/-home-user-zendriver")
BASE_TREE = Path("/home/user/.bughunt-base")  # pristine export of BASE_COMMIT (not tracked)
PUSHED = STATE / ".sync-pushed.json"  # last pushed sha per ref (not tracked)
LOG = STATE / "sync.log"

SKIP_DIRS = {"pkg", "__pycache__", ".venv", "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SCRATCH_MAX = 1 * 1024 * 1024  # bigger scratch files are stored gzipped (up to 20 MiB)
TRANSCRIPT_MAX = 45 * 1024 * 1024


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    with LOG.open("a") as fh:
        fh.write(line + "\n")


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=check)


CHROME_PROFILE_MARKERS = ("Local State", "SingletonLock", "SingletonCookie")


def skip_dir(name: str, path: Path | None = None) -> bool:
    if name in SKIP_DIRS or name.startswith(("venv", "uc_", ".org.chromium")):
        return True
    # generated cdp copies (e.g. a regenerated protocol) are not worth keeping
    if name == "cdp" and path is not None and (path / "page.py").exists():
        return True
    if path is None:
        return False
    # git checkouts/worktrees (agent worktrees are snapshotted through git instead)
    if (path / ".git").exists():
        return True
    # chrome user data dirs created by probes
    return any((path / m).exists() for m in CHROME_PROFILE_MARKERS)


def mirror(src: Path, dst: Path, max_size: int, skipped: list[str]) -> int:
    """copy new/changed files from src to dst; never deletes in dst"""
    copied = 0
    if not src.exists():
        return 0
    for root, dirs, files in os.walk(src, followlinks=False):
        dirs[:] = [d for d in dirs if not skip_dir(d, Path(root) / d)]
        rel = Path(root).relative_to(src)
        for name in files:
            s = Path(root) / name
            if s.is_symlink() or not s.is_file() or name == ".git" or name.endswith((".pyc", ".lock")):
                continue
            try:
                st = s.stat()
            except OSError:
                continue
            d = dst / rel / name
            if st.st_size > max_size:
                # big files are kept gzipped; only really huge ones are skipped
                if st.st_size > 20 * max_size:
                    skipped.append(f"{s} ({st.st_size // 1024} KiB)")
                    continue
                gz = d.with_name(name + ".gz")
                if not gz.exists() or gz.stat().st_mtime < st.st_mtime:
                    gz.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run(f"gzip -c {sh(s)} > {sh(gz)}", shell=True)
                    copied += 1
                continue
            if d.exists():
                dstat = d.stat()
                if dstat.st_size == st.st_size and int(dstat.st_mtime) >= int(st.st_mtime):
                    continue
            d.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(s, d)
                copied += 1
            except OSError as e:
                skipped.append(f"{s} (copy failed: {e})")
    return copied


def sh(p: Path | str) -> str:
    return "'" + str(p).replace("'", "'\\''") + "'"


def ensure_base_tree() -> None:
    if (BASE_TREE / "zendriver").is_dir():
        return
    BASE_TREE.mkdir(parents=True, exist_ok=True)
    subprocess.run(f"git -C {sh(REPO)} archive {BASE_COMMIT} zendriver | tar -x -C {sh(BASE_TREE)}", shell=True, check=True)


def save_prototype_patches(dst_root: Path) -> int:
    """prototype copies live in <dir>/pkg/zendriver: store them as patches against BASE_COMMIT"""
    n = 0
    for pkg in SCR.rglob("pkg"):
        if not (pkg / "zendriver").is_dir() or "pkg" in pkg.relative_to(SCR).parts[:-1]:
            continue
        rel = pkg.relative_to(SCR)
        out = dst_root / rel.parent / "pkg.patch"
        p = run(["diff", "-ruN", "-x", "__pycache__", "-x", "*.pyc", "-x", "cdp", str(BASE_TREE / "zendriver"), str(pkg / "zendriver")])
        text = p.stdout.replace(str(BASE_TREE) + "/", "a/").replace(str(pkg) + "/", "b/")
        if out.exists() and out.read_text() == text:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        n += 1
    return n


def load_pushed() -> dict:
    try:
        return json.loads(PUSHED.read_text())
    except (OSError, ValueError):
        return {}


def push(ref_spec: str, key: str, sha: str, pushed: dict, results: list[str]) -> None:
    if pushed.get(key) == sha:
        return
    for delay in (0, 2, 4, 8, 16):
        if delay:
            time.sleep(delay)
        p = run(["git", "-C", str(REPO), "push", "--no-verify", "origin", ref_spec])
        if p.returncode == 0:
            pushed[key] = sha
            results.append(f"pushed {ref_spec.lstrip('+')} @ {sha[:9]}")
            return
        if "rejected" in p.stderr or "denied" in p.stderr or "403" in p.stderr:
            break
    results.append(f"PUSH FAILED {ref_spec}: {p.stderr.strip()[-300:]}")


def worktrees() -> list[dict]:
    p = run(["git", "-C", str(REPO), "worktree", "list", "--porcelain"])
    out, cur = [], {}
    for line in p.stdout.splitlines() + [""]:
        if not line:
            if cur:
                out.append(cur)
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v or True
    return out


def snapshot_worktrees(pushed: dict, results: list[str]) -> list[str]:
    rows = []
    for wt in worktrees():
        path = Path(wt["worktree"])
        if path in (REPO, STATE):
            continue
        branch = wt.get("branch", "")
        branch = branch[len("refs/heads/"):] if isinstance(branch, str) and branch.startswith("refs/heads/") else ""
        head = wt.get("HEAD", "")
        name = branch or path.name
        if not path.exists():
            rows.append(f"| {path} | {branch or '(detached)'} | {head[:9]} | missing on disk |")
            continue
        # push only branches that carry new commits (harness worktrees start on throwaway
        # worktree-* branches at origin/main; remote deletion is refused, so don't litter origin)
        if branch and not any(
            run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", head, ref]).returncode == 0
            for ref in (DESIGNATED, "origin/main")
        ):
            push(f"+refs/heads/{branch}:refs/heads/{branch}", f"branch:{branch}", head, pushed, results)
        dirty = run(["git", "-C", str(path), "status", "--porcelain"]).stdout.strip()
        wip = ""
        if dirty:
            with tempfile.TemporaryDirectory() as td:
                env = dict(os.environ, GIT_INDEX_FILE=str(Path(td) / "index"))
                run(["git", "-C", str(path), "read-tree", "HEAD"], env=env)
                run(["git", "-C", str(path), "add", "-A"], env=env)
                tree = run(["git", "-C", str(path), "write-tree"], env=env).stdout.strip()
                if tree:
                    c = run(["git", "-C", str(path), "commit-tree", tree, "-p", head, "-m", f"WIP snapshot of {path} ({name}) at {now()}"]).stdout.strip()
                    if c:
                        safe = re.sub(r"[^A-Za-z0-9._/-]", "-", name)
                        push(f"+{c}:refs/heads/wip/{safe}", f"wiptree:{safe}", tree, pushed, results)
                        wip = f"wip/{safe} (tree {tree[:9]})"
        rows.append(f"| {path} | {branch or '(detached)'} | {head[:9]} | {('uncommitted -> ' + wip) if dirty else 'clean'} |")
    # the designated branch itself (fast-forward only, never forced)
    sha = run(["git", "-C", str(REPO), "rev-parse", DESIGNATED]).stdout.strip()
    if sha:
        push(f"refs/heads/{DESIGNATED}:refs/heads/{DESIGNATED}", f"branch:{DESIGNATED}", sha, pushed, results)
    return rows


def workflow_rows() -> list[str]:
    rows = []
    sess = CLAUDE_PROJ / SESSION
    scripts = {p.name: p for p in (sess / "workflows" / "scripts").glob("*.js")}
    for wf in sorted((sess / "subagents" / "workflows").glob("wf_*")):
        j = wf / "journal.jsonl"
        started, results, labels = {}, set(), {}
        if j.exists():
            for line in j.read_text().splitlines():
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") == "started":
                    started[d["key"]] = d.get("label", "?")
                elif d.get("type") == "result":
                    results.add(d["key"])
        inflight = [started[k] for k in started if k not in results]
        script = next((n for n in scripts if wf.name in n), "?")
        mtime = dt.datetime.fromtimestamp(j.stat().st_mtime, dt.timezone.utc).strftime("%H:%M UTC") if j.exists() else "-"
        rows.append(f"| {wf.name} | {script} | {len(started)} | {len(results)} | {mtime} | {', '.join(inflight) or '-'} |")
    return rows


def loop_pid() -> str:
    try:
        pid = Path("/tmp/bughunt-sync.pid").read_text().strip()
        return pid if Path(f"/proc/{pid}").exists() else f"{pid} (not running)"
    except OSError:
        return "none"


def git_commit_push(results: list[str]) -> None:
    run(["git", "-C", str(STATE), "add", "-A"])
    if run(["git", "-C", str(STATE), "diff", "--cached", "--quiet"]).returncode == 0:
        return
    run(["git", "-C", str(STATE), "commit", "-q", "-m", f"sync {now()}"])
    for delay in (0, 2, 4, 8, 16):
        if delay:
            time.sleep(delay)
        p = run(["git", "-C", str(STATE), "push", "-q", "origin", f"HEAD:refs/heads/{STATE_BRANCH}"])
        if p.returncode == 0:
            return
    log(f"STATE PUSH FAILED: {p.stderr.strip()[-300:]}")


def main() -> None:
    t0 = time.time()
    skipped: list[str] = []
    results: list[str] = []
    ensure_base_tree()
    n_scr = mirror(SCR, STATE / "scratch", SCRATCH_MAX, skipped)
    n_pat = save_prototype_patches(STATE / "scratch")
    n_cl = mirror(CLAUDE_PROJ / SESSION, STATE / "claude" / SESSION, TRANSCRIPT_MAX, skipped)
    main_tx = CLAUDE_PROJ / f"{SESSION}.jsonl"
    if main_tx.exists():
        (STATE / "claude").mkdir(parents=True, exist_ok=True)
        if main_tx.stat().st_size <= TRANSCRIPT_MAX:
            shutil.copy2(main_tx, STATE / "claude" / main_tx.name)
        else:
            subprocess.run(f"gzip -c {sh(main_tx)} > {sh(STATE / 'claude' / (main_tx.name + '.gz'))}", shell=True)
    n_tk = mirror(TASKS, STATE / "tasks", TRANSCRIPT_MAX, skipped)
    pushed = load_pushed()
    wt_rows = snapshot_worktrees(pushed, results)
    PUSHED.write_text(json.dumps(pushed, indent=1))
    status = [
        "# STATUS (generated by tools/sync.py — do not edit)",
        "",
        f"Last sync: **{now()}** (took {time.time() - t0:.1f}s; next in ~5 min while tools/sync-loop.sh runs; loop pid {loop_pid()}).",
        f"Copied this round: scratch {n_scr}, prototype patches {n_pat}, claude transcripts {n_cl}, task outputs {n_tk}.",
        "",
        "## Workflows (from journal.jsonl)",
        "| run | script | agents started | agents done | journal updated | in flight |",
        "|---|---|---|---|---|---|",
        *workflow_rows(),
        "",
        "## Extra git worktrees",
        "| path | branch | HEAD | state |",
        "|---|---|---|---|",
        *(wt_rows or ["| (none) | | | |"]),
        "",
        "## Pushes this round",
        *([f"- {r}" for r in results] or ["- (nothing new)"]),
        "",
        "## Skipped files (too large)",
        *([f"- {s}" for s in skipped[:50]] or ["- (none)"]),
    ]
    (STATE / "STATUS.md").write_text("\n".join(status) + "\n")
    lines = LOG.read_text().splitlines()[-400:] if LOG.exists() else []
    LOG.write_text("\n".join(lines) + "\n")
    log(f"sync ok: scratch={n_scr} patches={n_pat} claude={n_cl} tasks={n_tk} pushes={len(results)} skipped={len(skipped)}")
    git_commit_push(results)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # keep the loop alive; the error is in the log
        log(f"SYNC ERROR: {e!r}")
        sys.exit(1)
