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

## Stage 3 — verify (running since ~21:08)
* Workflow `zendriver-verify`, run `wf_2183e4a7-b84`.
* Units: Q1–Q12 and R13–R16, R18–R24 one pipeline each; the other 24 small groups in 6
  bundles of 4 (BA–BF). Each unit gets 3 independent verifiers: reproduce, refute/realism,
  fix-safety (prototype + regression test that fails on the repo and passes on the prototype).
* A group survives with >= 2 of 3 confirming (confirmed or partially-confirmed).
* Per-verifier scratch: `scratch/verify/<unit>-<lens>/` (prototype `pkg.patch` + tests).

## Stage 4 — fix (pending)
Planned: one fixer per confirmed queue group (worktree isolation, branch `fix/<slug>`),
then an adversarial reviewer; at most 2 rounds, else BLOCKED.

## Stage 5 — integrate (pending)
Planned: merge fix branches one by one (same-file groups sequentially), lint + unit tests
after each, CHANGELOG lines, full headless suite vs baseline, 5x loop of new tests, final
review workflow (2–3 reviewers), push, final report, `scratch/PR.md`.
