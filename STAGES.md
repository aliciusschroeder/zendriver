# Stage log

Supervisor session: `b2021b39-94e6-5220-9e66-7f33c0314a80`. Times are UTC, 2026-10-20.
Workflow scripts: `claude/b2021b39-…/workflows/scripts/`. Journals: `claude/b2021b39-…/subagents/workflows/<run>/journal.jsonl`.
Note: the machine has 4 CPUs, so each workflow runs at most 2 agents at a time.

## Stage 0 — setup and baseline (done, 18:39–18:41)
* Designated branch `ccr-9a8a26e1-b0l7bh` = `origin/main` (`5fa91ac`) fast-forwarded with
  `claude/serene-dijkstra-2awdy9` (`064148f`: duplicate `--disable-session-crashed-bubble`
  fix, `aopen` websocket race fix, changelog). Pushed.
* `uv sync --all-groups`; Chromium symlinked to `<scratch>/bin/chromium`.
* Baseline: lint clean; headless suite **118 passed, 1 skipped** (`test_drm.py:23` Widevine) in 35.6 s.
  Details: `scratch/BASELINE.md`, `scratch/baseline-*.txt`.

## Stage 1 — detect (done, 18:44–20:59)
* Workflow `zendriver-detect`, run `wf_e08be936-1f7` (interrupted once by a container
  restart at ~20:00 and resumed with `resumeFromRunId`; 11 cached agents replayed).
* 17 read-only finders: 13 file-scoped (A1–A13; A13 = `scripts/generate_cdp.py`) and 4
  bug-class sweeps (B13 unbounded awaits, B14 concurrency, B15 exceptions/cancellation,
  B16 lifecycle/state), blind to each other.
* **172 findings.** Every finder returned >= 4 findings and none ran out of time, so the
  "round 2 for areas with 0–1 findings" rule triggered for no area.
* Outputs: `scratch/stage1.json` (raw), `scratch/findings_flat.json`, `scratch/findings_compact.txt`.

## Stage 2 — group and triage (done, ~21:05)
* 172 findings + 13 seeded leads → **47 root-cause groups**; 2 findings dropped
  (A9.10 intended behaviour, A9.6 unsupported platform). Every finding id is a member of exactly one group.
* Fix queue (ranked): Q1 listener-robustness, Q2 timeout-bounds, Q3 stop-cleanup,
  Q4 start-cleanup, Q5 stderr-pipe, Q6 expect-pairing, Q7 register-handlers-snapshot,
  Q8 contradict-shadowing, Q9 aexit-reraise, Q10 tab-call-args, Q11 ready-state-order,
  Q12 swallowed-cancellation (seeded).
* Below the cap (verified + reported; promotion candidates if queue groups are refuted):
  R13–R24 (incl. seeded R15 config-args, R16 connection-close-state). Design/API, report-only:
  R17, R25, R26, R31, R35, R37, R46. Remaining R groups are small report-only groups.
* Files: `scratch/TRIAGE.md`, `scratch/triage/spec.py` (source of truth), `scratch/triage/groups.json`, `scratch/triage/groups/<id>.md`.

## Stage 3 — verify (done, 21:08 → 03:20 next day; 87 agents, ~6.2 h)
* Workflow `zendriver-verify`, run `wf_2183e4a7-b84`. Units: Q1–Q12 and R13–R16, R18–R24 one pipeline each;
  24 small groups in 6 bundles of 4 (BA–BF). 3 independent verifiers per unit: reproduce, refute/realism, fix-safety.
* Result: **all 47 groups survive** (>= 2 of 3 confirming). Only member refuted: SEED-X3 (proxy.py `open_tunnel`
  `except BaseException` re-raises, so cancellation propagates; 0/3). SEED-K3 (`--load-extension` re-added) 2/3.
* Important refinements carried into Stage 4:
  - Q2: a strict `wait_for(loop, timeout)` wrap regresses timeout=0 one-shots and cuts the last attempt; Q2 also needs
    Q12's `_register_handlers` fix, otherwise a pending Domain.enable swallows the timeout's cancellation.
  - Q1: the receive-error path must `break` (a `continue` freezes the loop on py>=3.12 for a persistent error).
  - Q4: in attach mode (host+port), cleanup must not send Browser.close to a browser zendriver did not launch.
  - Q6: only reproduces on Python >= 3.12 (3.10/3.11 yield between messages).
  - Q12: the swallow site in element.py is `Element.mouse_click`, not `click`; proxy.py needs no change.
* Outputs: `scratch/stage3.json` (raw), `scratch/stage3_digest.txt`, per-group `scratch/triage/verified/<id>.md`
  (all three lens reports with prototype diffs, regression tests and risks), prototypes as `scratch/verify/<unit>-fixsafety/pkg.patch`.
* Decision: fix queue = Q1–Q12 (all confirmed, 12 groups ≈ "top 10 or so"; Q12 is a prerequisite of Q2's fix).
  All R groups are verified and REPORT-ONLY (below the cap or design/API).

## Stage 4 — fix (pending)
Planned: one fixer per confirmed queue group (worktree isolation, branch `fix/<slug>`),
then an adversarial reviewer; at most 2 rounds, else BLOCKED.

## Stage 5 — integrate (pending)
Planned: merge fix branches one by one (same-file groups sequentially), lint + unit tests
after each, CHANGELOG lines, full headless suite vs baseline, 5x loop of new tests, final
review workflow (2–3 reviewers), push, final report, `scratch/PR.md`.

## Persistence (set up 22:30, during Stage 3)
* State worktree `/home/user/bughunt-state` on branch `ccr-9a8a26e1-b0l7bh-state`, synced and pushed every 5 min by
  `tools/sync-loop.sh` (see README). SessionStart hook in `~/.claude/settings.json` restarts the loop after a container restart.
* Self-tested: committed + uncommitted + untracked work in an extra worktree was pushed as `fix/_sync-selftest` and
  `wip/fix/_sync-selftest` without touching the worktree's index. Those two refs could not be deleted afterwards
  (the proxy answers 403 to remote branch deletion) and remain on origin.
* Stage 4+ prompts tell fixers to start from `origin/fix/<slug>` / `origin/wip/...` if an earlier attempt was interrupted.
