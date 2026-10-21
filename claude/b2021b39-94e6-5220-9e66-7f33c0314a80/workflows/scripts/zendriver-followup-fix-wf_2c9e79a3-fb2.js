export const meta = {
  name: 'zendriver-followup-fix',
  description: 'Stage 5 follow-up: fix the cross-fix problems the final review confirmed (connection send/rollback/session failure, lost cancellation in timeout bounds, concurrent stop with proxies + a timing-dependent test); fixer + adversarial reviewer per unit, at most 2 rounds',
  phases: [
    { title: 'Fix', detail: 'fixer per unit in its own worktree' },
    { title: 'Review', detail: 'adversarial reviewer per fix' },
    { title: 'Round 2', detail: 'fix + review again when changes were requested' },
  ],
}

const SCR = '/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad'
const BASE = 'ccr-9a8a26e1-b0l7bh'
const BASE_SHA = '8ae752b'
const FINDINGS = `${SCR}/final-review/FINDINGS.md`

const UNITS = [
  { id: 'U1', slug: 'followup-connection', tests: 'tests/core/test_connection.py', notes: `Fix these findings from ${FINDINGS} (sections cancellation-1, connection-1, connection-2, connection-3, and lifecycle-3), all in zendriver/core/connection.py:
(1) cancellation-1 (Q2+Q12 interaction, HANG): in Connection._register_handlers' \`except asyncio.CancelledError\` branch, keep the domain marked as enabled when its enable command was already written to the websocket and only roll it back when it never left (a written-but-unanswered tx stays in self.mapper; _send_transaction pops a tx whose write failed or was cancelled). Otherwise every later send re-sends the enable first, and on a page blocked by a dialog even Page.handleJavaScriptDialog can never be sent. The reviewer's prototype is in ${SCR}/final-review/cancellation/proto/pkg and a browser-free repro in ${SCR}/final-review/cancellation/probe_fake_dialog_wedge.py; keep test_cancelled_domain_enable_is_sent_again (enable never left the socket -> rolled back) passing.
(2) connection-2 + lifecycle-3 + connection-3 (Connection.send ordering): send() registers the tx in self.mapper before awaiting its own _register_handlers. (a) If the tx fails meanwhile (Q1's receive-error path fails pending txs), send() must not transmit the command afterwards: raise the failure instead (reviewer's validated fix: after the _register_handlers block, if tx.done(): pop it and return await tx). (b) If send() leaves before transmitting (exception or cancellation in _register_handlers, or the 'target session was detached' websocket check), pop its never-sent tx from self.mapper so a later aclose() does not set an exception nobody retrieves ('Transaction exception was never retrieved', seen with concurrent Browser.stop()). (c) If such a never-sent command was a manual X.enable(), undo the manually_enabled_domains entry this call added (connection-3), so X's handlers can still be auto-enabled later. Keep it one coherent, minimal change.
(3) connection-1 (Q1, Python >= 3.12, wrong error): the browser listener's new receive-error branch fails flat-session transactions whose replies are already queued in the session inbox. Fail them after those replies instead: e.g. put a sentinel carrying the error and the ids pending at that moment into each attached session's _inbox (fall back to failing directly when the session has no inbox); the session's listener_loop, on reaching the sentinel, fails only those ids that are still in its mapper. Repro: ${SCR}/final-review/connection/probes/probe_routed_then_fail.py.
Prototypes/probes from the reviewers are under ${SCR}/final-review/connection/ (fixpkg = the send() fix) and ${SCR}/final-review/cancellation/. Each sub-fix needs a regression test that fails on ${BASE_SHA} and passes on your fix (browser-free; reuse FakeWebSocket / StalledEnableWebSocket in tests/core/test_connection.py). Run the new tests on Python 3.10 (your worktree .venv) AND 3.13.` },
  { id: 'U2', slug: 'followup-timeouts', tests: 'tests/core/test_tab.py and tests/core/test_cloudflare.py', notes: `Fix finding cancellation-2 from ${FINDINGS}: on Python 3.10/3.11, the asyncio.wait_for that Q2 put around the polling loops (zendriver/core/tab.py _poll_with_timeout used by find/select/find_all/select_all/wait_for/tab(), the asyncio.wait_for in Tab.xpath, and the two bounds in zendriver/core/cloudflare.py cf_wait_for_interactive_challenge and verify_cf) loses a task cancellation that arrives in the same loop iteration as the poll's result (CPython gh-86296): wait_for returns the result (or raises the poll's exception) instead of CancelledError, so a cancelled scraping loop keeps running. Replace those bounds with a small helper that never loses the caller's cancellation (e.g. run the poll as a task, asyncio.wait({task}, timeout=...), cancel and await the task on timeout or when the caller is cancelled, re-raise CancelledError, and retrieve the task's outcome so nothing logs 'exception was never retrieved'), keeping every documented outcome of Q2 exactly as it is (TimeoutError messages, [] for xpath, False for cf_is_interactive_challenge_present, the timeout<=0 one-shot behaviour, the 0.5 s grace). The reviewer's prototype is ${SCR}/final-review/cancellation/proto2/pkg and the repros are probe_cancel_swallow.py / probe_cancel_swallow_loop.py in ${SCR}/final-review/cancellation/. Leave Browser._stop's wait_for alone. Add a regression test that fails on ${BASE_SHA} under Python 3.10 (your worktree .venv) and passes on the fix, and run the Q2 tests in tests/core/test_tab.py and tests/core/test_cloudflare.py on Python 3.10 AND 3.13.` },
  { id: 'U3', slug: 'followup-stop', tests: 'tests/core/test_browser.py', notes: `Fix findings lifecycle-1 and lifecycle-2 from ${FINDINGS}: (1) Two concurrent Browser.stop() calls still raise AttributeError ('NoneType' object has no attribute 'wait_closed') when a proxy context has a live tunnel, because both stop() calls close the same ProxyForwarder and ProxyForwarder.close() is not safe to run twice at once. Make each forwarder closed by exactly one stop() (e.g. pop forwarders off self._proxy_forwarders before closing them in Browser._stop) and/or make ProxyForwarder.close() idempotent; keep the Q3 behaviour (forwarders closed after the process is gone, bounded by STOP_COMMAND_TIMEOUT). Repro with real Chromium: ${SCR}/final-review/lifecycle/probes/concurrent_stop_proxy_real.py; add a browser-free regression test if possible. (2) The new test tests/core/test_browser.py::test_browser_stop_keeps_a_process_started_while_it_ran depends on timing on Python < 3.12 (asyncio.sleep(0.1) before swapping browser._process; a 0.1 s event-loop stall makes it fail; repro ${SCR}/final-review/lifecycle/probes/stall_started_while.py): make it synchronize on the actual event instead of sleeping, without weakening what it checks. Run test_browser.py on Python 3.10 (your worktree .venv) AND 3.13.` },
]

const COMMON = `You are working on zendriver, an async Chrome DevTools Protocol browser automation library for Python >= 3.10. Main checkout: /home/user/zendriver, designated branch ${BASE} at ${BASE_SHA} (12 bug fixes already integrated). A final cross-fix review found the problems you are asked to fix; read ${FINDINGS} for the scenarios, evidence and suggested fixes.

HARD RULES
- NEVER push anywhere, never open PRs/issues/comments, never touch cdpdriver/zendriver. A background sync pushes fix branches.
- NEVER modify the main checkout /home/user/zendriver or its branch ${BASE}. Work only in YOUR git worktree (your cwd; run \`pwd\` and \`git worktree list\` first). Scratch files under ${SCR}/followup/<unit-id>/.
- Do not edit CHANGELOG.md. Out of scope: zendriver/cdp/, docs/, examples/, CI config.
- Commits: descriptive message, imperative subject, no Co-authored-by or other trailers, no session links, no model names.

ENVIRONMENT
- In your worktree run \`uv sync --all-groups\` first (its .venv is Python 3.10), and confirm \`uv run python -c "import sys, zendriver; print(sys.version, zendriver.__file__)"\` imports YOUR worktree. For Python 3.13 make a second env, e.g. \`UV_PROJECT_ENVIRONMENT=${SCR}/followup/<unit-id>/venv313 uv sync --all-groups -p 3.13\` and run tests with the same UV_PROJECT_ENVIRONMENT.
- Lint: \`bash scripts/lint.sh\`; format: \`bash scripts/format.sh\`. Browser tests: \`export PATH=${SCR}/bin:$PATH\` and \`ZENDRIVER_TEST_BROWSERS=headless uv run pytest <files> -p no:cacheprovider -q\`; full suite with \`-n 4\`. The container runs as root.
- Gotchas: Connection uses the CantTouchThis metaclass (patch instances, Listener or websockets.connect, or use FakeWebSocket in tests/core/test_connection.py). Never use timeout=0 to test a hang path; positive timeouts plus an outer safety net. On Python >= 3.12 asyncio.wait_for no longer creates a task; several of these bugs are version dependent, so check the versions the finding names. Pre-existing flaky browser tests (evaluate() right after browser.get() races the page load): test_get_position_abs_includes_scroll_offset, test_handler_raising_type_error_is_called_once, test_element_get_returns_empty_attribute_value, test_shadow_children_includes_closed_shadow_root, test_is_scrolled_to_bottom, test_infinite_scrolling_tutorial_1 — do not chase those.`

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    unit_id: { type: 'string' }, status: { type: 'string', enum: ['done', 'blocked'] }, branch: { type: 'string' }, commit: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' }, tests_added: { type: 'array', items: { type: 'string' } },
    fail_before: { type: 'string' }, pass_after: { type: 'string' }, lint_ok: { type: 'boolean' }, affected_tests: { type: 'string' }, notes: { type: 'string' },
  },
  required: ['unit_id', 'status', 'branch', 'commit', 'files_changed', 'summary', 'tests_added', 'fail_before', 'pass_after', 'lint_ok', 'affected_tests', 'notes'],
}
const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    unit_id: { type: 'string' }, verdict: { type: 'string', enum: ['approve', 'request-changes'] }, reviewed_commit: { type: 'string' },
    items: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocking', 'non-blocking'] }, description: { type: 'string' } }, required: ['severity', 'description'] } },
    test_fails_on_base: { type: 'string', enum: ['yes', 'no', 'not-run'] }, test_passes_on_fix: { type: 'string', enum: ['yes', 'no', 'not-run'] }, lint_ok: { type: 'string', enum: ['yes', 'no', 'not-run'] }, summary: { type: 'string' },
  },
  required: ['unit_id', 'verdict', 'reviewed_commit', 'items', 'test_fails_on_base', 'test_passes_on_fix', 'lint_ok', 'summary'],
}

function fixerPrompt(u, round, review) {
  const branch = `fix/${u.slug}`
  let p = `${COMMON}\n\nYOUR TASK: unit ${u.id} (${u.slug}) — round ${round} of at most 2.\n\n${u.notes}\n\nSuggested test location: ${u.tests}.\n`
  if (round === 1) {
    p += `\nSTEPS\n1. If branch ${branch} (or origin/${branch}, origin/wip/${branch}) already exists from an interrupted attempt, inspect it and continue if sound; else \`git checkout -B ${branch} ${BASE}\` and check \`git log --oneline -1\` is ${BASE_SHA}.\n2. Minimal patch, matching the surrounding style and comment density; no public signature changes.\n3. Regression tests that FAIL before and PASS after: after committing, \`git checkout ${BASE} -- zendriver/\`, run the new tests (must fail for the right reason, on the Python version(s) where the bug exists), \`git checkout HEAD -- zendriver/\`, run again (must pass). Paste the key lines.\n4. \`bash scripts/format.sh\`, \`bash scripts/lint.sh\`, the affected test files, and the full headless suite (-n 4) once on 3.10 and once on 3.13.\n5. Exactly ONE commit on ${branch} on top of ${BASE}; then \`git checkout --detach\`.\nIf it cannot be fixed minimally, return status=blocked with the reason.`
  } else {
    p += `\nA reviewer requested changes on ${branch}:\n${JSON.stringify(review, null, 1)}\n\nSTEPS\n1. \`git checkout ${branch}\` (or detach at it and \`git branch -f ${branch} HEAD\` at the end if it is checked out elsewhere).\n2. Address every BLOCKING item (non-blocking ones when right and cheap); explain disagreements in notes.\n3. Keep exactly ONE commit on top of ${BASE} (amend).\n4. Re-show fail-before/pass-after, format, lint, affected tests on 3.10 and 3.13.\n5. \`git checkout --detach\`.`
  }
  return p + `\n\nReturn the schema (final commit sha, tests added as file::name, fail_before/pass_after with commands and key output, notes with residual risks).`
}

function reviewerPrompt(u, fix, round) {
  const branch = `fix/${u.slug}`
  return `${COMMON}\n\nYOUR TASK: ADVERSARIAL REVIEW of unit ${u.id} (${u.slug}), review round ${round}. You did not write it; find what is wrong with it.\n\nWhat the fix was asked to do:\n${u.notes}\n\nThe fixer reported:\n${JSON.stringify(fix, null, 1)}\n\nSTEPS\n1. In your own worktree: \`git checkout --detach ${branch}\`, \`uv sync --all-groups\` (3.10) and a 3.13 env as described. Read \`git diff ${BASE}...${branch}\` in full plus the surrounding code; re-read the relevant findings in ${FINDINGS}.\n2. Review correctness (every listed finding fixed, re-run the reviewers' repro probes against your checkout with PYTHONPATH), minimality, new failure modes (deadlocks, lock ordering, swallowed errors or CancelledError, leaked tasks, 'never retrieved' noise, behaviour changes callers notice, Python 3.10/3.11 vs 3.12+ differences), and that the 12 already-integrated fixes still hold (run tests/core/test_connection.py, test_tab.py, test_browser.py, test_cloudflare.py, test_expect.py on 3.10 and 3.13).\n3. Prove the new tests fail without the fix: \`git checkout ${BASE} -- zendriver/\`, run them on the relevant Python version(s), \`git checkout HEAD -- zendriver/\`, run again; run each new test 3 times for flakiness. Run \`bash scripts/lint.sh\`.\n4. Verdict: "approve" only with no blocking item; otherwise "request-changes" with concrete items. Do not modify the branch.`
}

async function fixUnit(u) {
  const fix1 = await agent(fixerPrompt(u, 1), { label: `fix:${u.id}`, phase: 'Fix', schema: FIX_SCHEMA, isolation: 'worktree' })
  if (!fix1 || fix1.status === 'blocked') return { unit: u.id, slug: u.slug, status: 'BLOCKED', reason: fix1 ? fix1.notes : 'no result', rounds: [{ fix: fix1 }] }
  const rev1 = await agent(reviewerPrompt(u, fix1, 1), { label: `review:${u.id}`, phase: 'Review', schema: REVIEW_SCHEMA, isolation: 'worktree' })
  if (rev1 && rev1.verdict === 'approve') { log(`${u.id}: approved in round 1`); return { unit: u.id, slug: u.slug, status: 'APPROVED', commit: fix1.commit, rounds: [{ fix: fix1, review: rev1 }] } }
  const fix2 = await agent(fixerPrompt(u, 2, rev1), { label: `fix2:${u.id}`, phase: 'Round 2', schema: FIX_SCHEMA, isolation: 'worktree' })
  if (!fix2 || fix2.status === 'blocked') return { unit: u.id, slug: u.slug, status: 'BLOCKED', reason: 'round 2 blocked: ' + (fix2 ? fix2.notes : 'no result'), rounds: [{ fix: fix1, review: rev1 }, { fix: fix2 }] }
  const rev2 = await agent(reviewerPrompt(u, fix2, 2), { label: `review2:${u.id}`, phase: 'Round 2', schema: REVIEW_SCHEMA, isolation: 'worktree' })
  const ok = rev2 && rev2.verdict === 'approve'
  log(`${u.id}: ${ok ? 'approved in round 2' : 'BLOCKED after 2 rounds'}`)
  return { unit: u.id, slug: u.slug, status: ok ? 'APPROVED' : 'BLOCKED', commit: fix2.commit, reason: ok ? '' : 'reviewer still requests changes after round 2', rounds: [{ fix: fix1, review: rev1 }, { fix: fix2, review: rev2 }] }
}

const results = await pipeline(UNITS, u => fixUnit(u))
return { results: results.filter(Boolean) }
