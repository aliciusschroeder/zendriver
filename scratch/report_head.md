# zendriver bug hunt — final report

Branch `ccr-9a8a26e1-b0l7bh` on aliciusschroeder/zendriver, tip `822610d` (base before the hunt: `064148f` = main `5fa91ac` + `claude/serene-dijkstra-2awdy9`).
State, transcripts, workflows and every probe: branch `ccr-9a8a26e1-b0l7bh-state` (README.md, STAGES.md, STATUS.md).

**Pipeline:** 17 finders (2 blind sweeps) → 172 findings + 13 seeded leads → 47 root-cause groups (2 findings dropped) →
3 independent verifiers per group (87 agents): **47/47 survived**, 1 seeded member refuted →
12 groups fixed (fixer + adversarial reviewer, 12/12 approved, 2 needed a second round, 0 blocked) →
integrated → 3 cross-fix reviewers found 8 interaction problems (+1 flaky test) → 3 follow-up fixes, all approved → re-tested.

**Tests:** baseline 118 passed, 1 skipped (and the base is flaky: 2 of 4 full runs failed on page-load races in existing
tests). Final: 224 passed, 1 skipped in 3/3 runs on Python 3.13; 222 passed, 3 skipped in 2/2 runs on Python 3.10
(the 2 extra skips are ExceptionGroup cases that need 3.11+). 106 new tests, each run 5x in a loop: 106 passed every time.
Lint (ruff check, ruff format --check, mypy) clean after every merge.

## One entry per group
Status legend: fixed = merged with regression tests; report-only = verified (>= 2/3 verifiers) but below the fix cap;
report-only (design) = verified, needs a design/API decision. Evidence = first member's file:function:line at base 064148f
(full member lists, verifier reports, prototypes and repro tests: `scratch/triage/groups/<id>.md`, `scratch/triage/verified/<id>.md`).
