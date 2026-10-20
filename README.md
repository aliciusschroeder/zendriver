# zendriver bug hunt — state, docs and recovery

This branch (`ccr-9a8a26e1-b0l7bh-state`, checked out as a git worktree at
`/home/user/bughunt-state`) holds **everything needed to understand and resume** the
repo-wide bug hunt of `aliciusschroeder/zendriver`. It is snapshotted and pushed every
~5 minutes, so no stage or agent loses more than ~5 minutes of work.

The code changes themselves go to the designated branch **`ccr-9a8a26e1-b0l7bh`**.
Nothing here is ever pushed to `cdpdriver/zendriver`, and no PR is opened; the PR
title/body goes to `scratch/PR.md` at the end.

| file | what it is |
|---|---|
| `README.md` | this orientation (hand-written, updated at stage boundaries) |
| `STAGES.md` | stage-by-stage log: what ran, workflow run ids, outcomes, decisions |
| `STATUS.md` | **generated** every sync: workflows and agents in flight, worktrees, pushes |
| `scratch/` | mirror of the supervisor scratchpad: baseline, triage, stage outputs, every finder/verifier probe and test. Prototype package copies (`*/pkg/zendriver`) are stored as `pkg.patch` against base commit `064148f` |
| `scratch/triage/groups/<id>.md` | definition of each root-cause group (members, files, fix strategy, test approach) |
| `claude/` | Claude transcripts: the supervisor session (`<session>.jsonl`), every workflow `journal.jsonl` (completed agent results), every agent transcript (`agent-*.jsonl`), the workflow scripts (`workflows/scripts/*.js`) |
| `tasks/` | background task outputs (the final return value of each workflow) |
| `tools/sync.py` | the snapshot + push script; `tools/sync-loop.sh` runs it every 5 min; `tools/ensure-sync.sh` starts the loop if it is not running |
| `tools/journal_results.py` | extracts completed agent results from a saved journal (for resuming in a new session) |

## Branches

* `ccr-9a8a26e1-b0l7bh` — designated branch: base (main + `claude/serene-dijkstra-2awdy9`) plus the integrated fixes. The sync fast-forward-pushes it.
* `ccr-9a8a26e1-b0l7bh-state` — this branch (snapshots, docs).
* `fix/<group-slug>` — one per Stage 4 fixer (worktree isolation); force-pushed by the sync whenever its head moves.
* `wip/<branch-or-worktree>` — snapshot of **uncommitted** work in any extra worktree, made with a temporary index (the agent's own index and branch are never touched); force-pushed every sync.

## How the snapshotting works

`tools/sync-loop.sh` runs `tools/sync.py` every 300 s under `flock` (no overlapping runs).
Each run copies new/changed files (never deletes from here, so a wiped source cannot
wipe the snapshot), writes prototype patches, snapshots every extra worktree, pushes
agent branches, regenerates `STATUS.md`, commits and pushes this branch.

* Check it: `cat /tmp/bughunt-sync.pid; tail /home/user/bughunt-state/sync.log` (or read `STATUS.md` → "Last sync").
* (Re)start it: `bash /home/user/bughunt-state/tools/ensure-sync.sh` (idempotent).
  A `SessionStart` hook in `~/.claude/settings.json` runs it automatically when the
  session (re)starts, and the supervisor also runs it whenever it wakes up.
* Force a snapshot now: `python3 /home/user/bughunt-state/tools/sync.py`.
* Background processes do not survive a container restart; that is why the hook exists.

## How to resume

### A. Same session after a container restart (most common)
1. `bash /home/user/bughunt-state/tools/ensure-sync.sh`
2. Read `STATUS.md` for workflows whose agents were in flight, and `STAGES.md` for the current stage.
3. Re-launch an interrupted workflow with
   `Workflow({scriptPath: <claude/.../workflows/scripts/<name>.js>, resumeFromRunId: <run id>})`.
   Completed agents replay from `journal.jsonl`; only unfinished ones run again. Their
   partial work is still in `scratch/verify/<unit>-<lens>/` (or `scratch/detect-*`), and
   the restarted agent may reuse it.
4. Stage 4 fixers: their committed work is on `origin/fix/<slug>` and uncommitted work
   on `origin/wip/<name>`; a new fixer can start from either.

### B. New session or new container (local disk gone)
1. `git -C /home/user/zendriver fetch origin ccr-9a8a26e1-b0l7bh ccr-9a8a26e1-b0l7bh-state`
   and `git -C /home/user/zendriver worktree add /home/user/bughunt-state ccr-9a8a26e1-b0l7bh-state`.
2. Read `README.md`, `STAGES.md`, `STATUS.md`, `scratch/TRIAGE.md`.
3. Edit the constants at the top of `tools/sync.py` (`SESSION`, `SCR`, `TASKS`) for the new
   session, then run `tools/ensure-sync.sh`.
4. Copy `scratch/` back into the new scratchpad if the stage needs earlier probes
   (`patch -p1 -d <dir>/pkg/zendriver < pkg.patch` on a fresh `cp -r zendriver` restores a prototype).
5. `resumeFromRunId` only works in the same session. To continue a half-done workflow,
   extract what finished: `python3 tools/journal_results.py claude/<session>/subagents/workflows/<run>/journal.jsonl > done.json`,
   then run the stage's script (copy in `claude/.../workflows/scripts/`) for only the
   units that are missing, passing the finished results in via `args` if the script needs them.
6. Fix branches: `git fetch origin 'refs/heads/fix/*:refs/remotes/origin/fix/*' 'refs/heads/wip/*:refs/remotes/origin/wip/*'`.

## Environment notes for anyone resuming
* `uv sync --all-groups`; lint `scripts/lint.sh`; format `scripts/format.sh`.
* Browser tests need Chromium on PATH as `chromium`: `ln -sf /opt/pw-browsers/chromium-1194/chrome-linux/chrome <scratch>/bin/chromium`, prepend `<scratch>/bin` to PATH, then
  `ZENDRIVER_TEST_BROWSERS=headless uv run pytest -n 4 -p no:cacheprovider`.
* Baseline before any fix: lint clean, **118 passed, 1 skipped** (Widevine) in ~36 s.
* Testing a scratch copy: `PYTHONPATH=<copy>`, cwd outside the repo, `--rootdir <scratch> -p no:cacheprovider -o asyncio_mode=auto`, print `zendriver.__file__`.
* `Connection` uses the `CantTouchThis` metaclass (patch instances, `Listener` or `websockets.connect`).
* The container runs as root (`is_root()` disables the sandbox).
* Never use `asyncio.wait_for(x, 0)` to test a hang path.
