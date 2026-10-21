export const meta = {
  name: 'zendriver-final-review',
  description: 'Stage 5: three adversarial reviewers look for interactions between the 12 integrated fixes (locks, timeouts, cancellation, listener and browser lifecycle) that single-fix reviews could not see',
  phases: [
    { title: 'Review', detail: '3 cross-fix reviewers, different lenses' },
  ],
}

const SCR = '/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad'

const COMMON = `You are a final adversarial reviewer of an integrated set of 12 bug fixes in zendriver (async Chrome DevTools Protocol automation library, Python >= 3.10). Each fix was reviewed on its own; your job is to find problems that only appear when the fixes are COMBINED, plus anything the single-fix reviews missed.

Repo: /home/user/zendriver, branch ccr-9a8a26e1-b0l7bh, tip 8ae752b. Base before the fixes: 064148f. Read the combined diff: \`git -C /home/user/zendriver diff 064148f..8ae752b -- zendriver/\` (and the tests). The 12 fix commits (one per group) are listed by \`git -C /home/user/zendriver log --oneline --no-merges 064148f..8ae752b\`; their commit messages explain intent. Group definitions: ${SCR}/triage/groups/Q1.md .. Q12.md; Stage 3 verification reports: ${SCR}/triage/verified/Q*.md; Stage 4 fixer/reviewer reports: ${SCR}/stage4.json (non-blocking reviewer notes there are known; only re-raise them if the combination makes them worse or you can show a concrete failure).

The 12 fixes: Q1 listener robustness (Transaction parse errors -> set_exception; handler errors logged not re-raised; unexpected receive errors fail pending + break; flat-session aopen revives parent listener) | Q2 timeout bounds for find/select/find_all/select_all/xpath/wait_for/tab()/cloudflare (asyncio.wait_for around polling loops, +0.5 s grace, timeout<=0 one-shot) | Q3 Browser.stop cleanup (bounded detach/close, local process ref, polling instead of to_thread, atexit unregister after stop, forwarders after process) | Q4 Browser.start cleanup on BaseException (close connection then stop) | Q5 stderr drain thread / stdout DEVNULL | Q6 expect handlers ignore events once tracked | Q7 _register_handlers guarded remove | Q8 ContraDict class attributes win over keys | Q9 __aexit__ returns None | Q10 Tab.__call__ keyword args | Q11 wait_for_ready_state accepts later states | Q12 _register_handlers re-raises CancelledError (undoing bookkeeping), Element.mouse_click except Exception.

RULES
- NEVER modify /home/user/zendriver (no edits, no commits, no checkouts there). Scratch work only under ${SCR}/final-review/<your-lens>/ ; to test a modified copy: mkdir -p <dir>/pkg && cp -r /home/user/zendriver/zendriver <dir>/pkg/ ; PYTHONPATH=<dir>/pkg ; run from a cwd outside the repo with --rootdir <dir> -p no:cacheprovider -o asyncio_mode=auto and print zendriver.__file__.
- Python: /home/user/zendriver/.venv/bin/python is 3.13. A Python 3.10 environment with the integrated code installed exists at ${SCR}/flaky-check (a detached worktree at 8ae752b; use \`cd ${SCR}/flaky-check && uv run python ...\`) — asyncio cancellation/wait_for semantics differ before 3.12, so check version-dependent claims on BOTH.
- Real headless Chromium: export PATH=${SCR}/bin:$PATH. Fake CDP peer: in-process websockets server on 127.0.0.1:0, or the FakeWebSocket in tests/core/test_connection.py. Connection uses the CantTouchThis metaclass (patch instances, not the class). Never use timeout=0 to test a hang; use positive timeouts plus an outer safety net (\`timeout 120 ...\`). Print task stacks for hangs. Stop every browser you start and kill only pids you started.
- Every finding needs a concrete scenario starting from a public API call and EVIDENCE from a run (command + key output). Unproven suspicions go in "suspicions", not findings. No style nits.`

const LENSES = [
  { key: 'cancellation', prompt: `YOUR LENS: CANCELLATION AND TIMEOUTS ACROSS FIXES. Examples to probe: Q2's asyncio.wait_for cancelling a send that is inside _register_handlers (now re-raised by Q12) or inside _attach_session/_prepare_headless (_attach_lock released? session bookkeeping consistent? Transaction left in mapper?); Q2 bound firing while Q1's listener revival or a nested Domain.enable is in flight; Q4's BaseException cleanup awaiting Q3's bounded stop() while the task is being cancelled (Python 3.10 wait_for vs 3.12 asyncio.timeout semantics, double cancellation, uncancel counts); Q3's wait_for(gather(...)) when stop() itself is cancelled; whether any path now converts a cancellation into a different exception or a hang, or leaves 'Task exception was never retrieved'/'Future exception was never retrieved' noise; whether a timed-out Q2 call leaves the tab in a state where the NEXT call misbehaves (stale enabled_domains, DOM agent left enabled, half-attached session).` },
  { key: 'connection', prompt: `YOUR LENS: CONNECTION / LISTENER STATE MACHINE. Q1, Q7, Q9 and Q12 all changed zendriver/core/connection.py. Probe their interplay: can Q1's aopen revival start a second Listener reading the same websocket (ConcurrencyError) together with send()'s own 'if not self.listener or not self.listener.running' restart, or with _attach_session? After Q1's receive-error break, what do flat sessions see (their inboxes, their own listeners, Connection.wait())? Q1 fails pending transactions with the raw exception: does that interact with Q12's CancelledError path or Q3's stop (which now gathers aclose() with return_exceptions)? Q9's __aexit__ now returns None: does 'async with tab' still close correctly with Q1's quiet-detach break? Does Q7's guard plus Q12's undo keep enabled_domains consistent when a cancellation and a nested enable interleave? Check for leaked listener tasks or duplicated event dispatch after recovery.` },
  { key: 'lifecycle', prompt: `YOUR LENS: BROWSER LIFECYCLE, PROCESS AND IO, AND TEST QUALITY. Q3, Q4, Q5 and Q9 changed zendriver/core/browser.py and util.py. Probe: the Q5 stderr drain thread across stop()/atexit/restart (thread exits? file descriptor closed? _stderr_tails entries released? any blocking read during stop or interpreter exit?); Q4 cleanup + Q3 stop on failed starts in attach mode and launch mode (process terminated, profile removed, registry cleaned, atexit hook state consistent, no Browser.close sent to an attached browser); asyncio.run(main) that never calls stop() (atexit path) with real Chromium on Python 3.10 and 3.13 (profile removed? no 'Executor shutdown' error? no stray Chrome?); running several browsers concurrently and stopping them concurrently; behaviour of zd.start() twice / multiple browsers (test_multiple_browsers). Also review the 79 NEW tests (ids in ${SCR}/integration/ids-new.txt) for flakiness and false positives: timing assumptions that may fail on a slow CI runner, tests that pass for the wrong reason, global state leaks (monkeypatched module attributes, leftover processes, registry entries) between tests. Run the new tests under load (e.g. pytest -n 4 with the full suite, and a CPU hog in parallel) to look for flakes.` },
]

const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          severity: { type: 'string', enum: ['crash', 'hang', 'leak', 'wrong-result', 'flaky-test', 'cosmetic'] },
          fixes_involved: { type: 'array', items: { type: 'string' } },
          files: { type: 'string' },
          scenario: { type: 'string' },
          evidence: { type: 'string' },
          python_versions: { type: 'string' },
          regression_vs_base: { type: 'string', enum: ['new-regression', 'pre-existing', 'pre-existing-made-worse', 'unclear'] },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          suggested_fix: { type: 'string' },
        },
        required: ['title', 'severity', 'fixes_involved', 'files', 'scenario', 'evidence', 'python_versions', 'regression_vs_base', 'confidence', 'suggested_fix'],
      },
    },
    suspicions: { type: 'array', items: { type: 'string' } },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'suspicions', 'checked_ok'],
}

phase('Review')
const results = await parallel(LENSES.map(l => () =>
  agent(`${COMMON}\n\n${l.prompt}\n\nScratch dir: ${SCR}/final-review/${l.key}/`, { label: `final:${l.key}`, phase: 'Review', schema: SCHEMA })
    .then(r => ({ lens: l.key, result: r }))
))
return { reviews: results.filter(Boolean) }
