export const meta = {
  name: 'zendriver-fix',
  description: 'Stage 4: one fixer per confirmed fix-queue group (worktree, branch fix/<slug>) followed by an adversarial reviewer; at most 2 fix-and-review rounds, then BLOCKED',
  phases: [
    { title: 'Fix', detail: 'fixer per group in its own worktree' },
    { title: 'Review', detail: 'adversarial reviewer per fix' },
    { title: 'Round 2', detail: 'fix + review again when changes were requested' },
  ],
}

const SCR = '/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad'
const BASE = 'ccr-9a8a26e1-b0l7bh'

const GROUPS = [
  { id: 'Q1', slug: 'listener-robustness', tests: 'tests/core/test_connection.py', notes: `Verifiers found four sub-defects, all in connection.py: (1) Transaction.__call__ lets any non-StopIteration exception from the parser/custom generator escape (and its trailing \`raise ProtocolException('could not parse...')\`) -> make it set_exception on the future instead (chain the cause). (2) listener_loop's per-callback dispatch logs a handler that raises when called (e.g. wrong arity) and then re-raises, killing the listener -> log and skip. (3) listener_loop's receive try catches only TimeoutError/CancelledError/ConnectionClosed -> on any other Exception log it, fail the pending transactions of the connection and of its flat sessions, then BREAK (a continue-based handler freezes the whole event loop on Python >= 3.12 when the error is persistent and synchronous); the next send() starts a new listener. (4) A flat-session Tab never revives a dead parent browser-connection listener (aopen/_attach_session return early) -> when the parent's websocket is open and its listener is not running, start one (no await between the check and creating the Listener, so concurrent sends cannot start two readers). Out of scope: Connection.wait() blocking on a dead listener's idle event and ConnectionClosed not resetting websocket (reported separately as R16).` },
  { id: 'Q2', slug: 'timeout-bounds', tests: 'tests/core/test_tab.py and tests/core/test_cloudflare.py', notes: `Bound Tab.find/select/find_all/select_all/xpath/wait_for (and therefore tab(...)) and cloudflare cf_wait_for_interactive_challenge / cf_is_interactive_challenge_present / verify_cf so they return or raise within about their timeout when a CDP reply never comes (open alert()). The fix-safety verifier showed a strict asyncio.wait_for(loop, timeout) wrap is UNSAFE as written: (a) timeout<=0 must still make exactly one attempt (one-shot semantics; xpath internally calls find_all(xpath, timeout=0)); (b) it must not cut the last attempt (clamp the between-attempt sleep to the remaining time and allow a small grace so an attempt started before the deadline can finish); (c) it must not discard an element that was already found (no sleep after a hit). Keep each method's documented outcome on timeout (TimeoutError for find/select/wait_for/verify_cf, [] for xpath and the *_all methods as they behave today, False for cf_is_interactive_challenge_present). xpath: make at least one attempt even with timeout<=0 and do not busy-spin. verify_cf: the click_delay sleep must not overrun the deadline. Do NOT touch Connection._register_handlers (its bare except swallowing cancellation is group Q12, merged separately) and do NOT touch Tab.get/Browser.get (owned by another PR). Your tests must not depend on Q12 (e.g. do not register an event handler for a not-yet-enabled domain while the renderer is blocked). Prefer browser-free tests (fake CDP peer or instance-patched send that never answers DOM.getDocument); a single real-Chromium alert() test is acceptable if it is fast and reliable.` },
  { id: 'Q3', slug: 'stop-cleanup', tests: 'tests/core/test_browser.py', notes: `Browser.stop()/_stop()/_atexit_cleanup in browser.py: bound the per-target aclose() phase (Target.detachFromTarget) and the Browser.close send with a short timeout and make exceptions from them (e.g. ConnectionClosedError escaping Connection.aclose, which only catches ProtocolException) not abort the rest, so terminate/kill, proxy-forwarder close and temp-profile cleanup always run; snapshot self._process into a local so a concurrent stop() setting it to None cannot crash the other call; replace \`await asyncio.to_thread(self._process.wait)\` (raises 'Executor shutdown has been called' on the asyncio.run atexit path, so the temp profile leaks for every script that never calls stop()) with polling. Consider whether stop() should unregister the atexit callback only after _stop finished, so a cancelled/failed stop() keeps the atexit fallback. Keep the timeout small but safe (the verifier used 5 s). Do NOT change Browser.start (group Q4 fixes start separately). Browser-free tests preferred (fake connection/peer that never answers, fake Popen); the atexit case can run a subprocess with asyncio.run and real Chromium if needed.` },
  { id: 'Q4', slug: 'start-cleanup', tests: 'tests/core/test_browser.py', notes: `Browser.start in browser.py: when start() fails or is cancelled after Chrome was spawned (CancelledError from asyncio.wait_for(zd.start(), t), exceptions from set_discover_targets/update_targets/_read_headless_user_agent), stop the spawned process, remove the temp profile and unregister the instance, then re-raise. In attach mode (host and port given, connect_existing) do NOT send Browser.close to the user's existing browser: only close the connection. Keep the diff to start() (group Q3 changes _stop/stop separately; do not modify them beyond what Q4 strictly needs). The existing 'Failed to connect to browser' path already calls stop(); keep it working.` },
  { id: 'Q5', slug: 'stderr-pipe', tests: 'tests/core/test_browser.py (or a new tests/core/test_util.py)', notes: `util._start_process opens Chrome with stdout=PIPE and stderr=PIPE that nothing reads during the session; once the pipe fills Chrome blocks and CDP hangs. util._read_process_stderr's blocking read(65536) also cannot finish within its 0.25 s while Chrome is alive, so the failure log says 'No output from browser'. Fix minimally: stdout to DEVNULL; stderr drained (a daemon thread keeping a bounded tail, or a temporary file) and _read_process_stderr returns that content even while Chrome is alive (decode with errors='replace'). Do not change the Browser.start failure flow beyond what is needed.` },
  { id: 'Q6', slug: 'expect-pairing', tests: 'a new tests/core/test_expect.py (no expect tests exist yet) or tests/core/test_tab.py', notes: `expect.py BaseRequestExpectation handlers: ignore events once the corresponding future is done, checking BEFORE mutating request_id, so request, response and response_body all belong to the first matching request and no InvalidStateError is raised in handler tasks. Through the real Listener this only reproduces on Python >= 3.12, so make the regression test drive the handlers directly (two matching events dispatched back-to-back) so it fails on every supported Python version. Leave intercept.py and DownloadExpectation unchanged unless the identical guard is a one-liner with its own failing test (mention similar sites in notes instead).` },
  { id: 'Q7', slug: 'register-handlers-snapshot', tests: 'tests/core/test_connection.py', notes: `Connection._register_handlers final loop: \`self.enabled_domains.remove(ed)\` raises ValueError when a nested send (the domain.enable() it awaits re-runs _register_handlers through aopen) already removed it. Guard it (only remove domains still present). Group Q12 changes the except clauses of the same function in a separate branch: keep your diff to the final loop to avoid conflicts.` },
  { id: 'Q8', slug: 'contradict-shadowing', tests: 'a new tests/core/test_contradict.py', notes: `ContraDict.__getattribute__ in _contradict.py returns self[attribute] whenever the name is a key, so keys like clear/get/items/values/update shadow the dict methods (crashing Element.update(), repr(), get(), Tab.get_all_urls on real HTML such as <br clear="all">). Make real class attributes/methods win (e.g. \`attribute in self and not hasattr(type(self), attribute)\`), as the docstring promises; non-colliding keys must still work as attributes. Add a test that an Element built from a fake node with a 'clear'/'items'/'get' attribute can update()/repr()/get() if that is cheap and browser-free.` },
  { id: 'Q9', slug: 'aexit-reraise', tests: 'tests/core/test_connection.py and tests/core/test_browser.py', notes: `Browser.__aexit__ (browser.py) and Connection.__aexit__ (connection.py, inherited by Tab) do \`raise exc_type(exc_val)\`, which turns multi-argument exceptions (json.JSONDecodeError, websockets ConnectionClosed, ExceptionGroup) into TypeError and drops attributes such as ProtocolException.code. Return None so the original exception propagates unchanged; Connection.__aexit__ keeps awaiting aclose(). Do NOT add stop() to Browser.__aexit__ (separate API decision, reported). Tests that need ExceptionGroup must be skipped on Python < 3.11.` },
  { id: 'Q10', slug: 'tab-call-args', tests: 'tests/core/test_tab.py', notes: `Tab.__call__ calls self.wait_for(text, selector, timeout) positionally but the signature is wait_for(selector, text, timeout). Pass by keyword. A browser-free test can set an instance attribute wait_for on a Tab (class attributes cannot be patched because of the CantTouchThis metaclass, instance attributes can) or use the real browser fixture: tab(text='...') must find text.` },
  { id: 'Q11', slug: 'ready-state-order', tests: 'tests/core/test_tab.py', notes: `Tab.wait_for_ready_state compares readyState with ==, so until='interactive' (the default) times out on a page that is already 'complete', and until='loading' fails on any page past loading. Treat a later state as satisfying an earlier target (loading < interactive < complete). Keep the timeout behaviour added in #291 (the timeout must still cover the evaluate call).` },
  { id: 'Q12', slug: 'swallowed-cancellation', tests: 'tests/core/test_connection.py (and an element test if cheap)', notes: `(1) connection.py Connection._register_handlers: the bare \`except:\` around \`await self.send(domain_mod.enable(), _is_update=True)\` swallows CancelledError, so wait_for timeouts/task.cancel() hitting a pending Domain.enable are ignored and the outer send re-sends the enable and can hang forever. Split it: \`except asyncio.CancelledError:\` undoes the enabled_domains bookkeeping for that domain and re-raises; \`except Exception:\` keeps the existing log-and-remove. (2) element.py: the swallowing site is Element.mouse_click (\`try: await self.flash() except: pass\`), not Element.click -> \`except Exception:\`. (3) proxy.py open_tunnel's \`except BaseException\` re-raises; it was refuted by all three verifiers: do not change it. Group Q7 changes the final loop of _register_handlers in a separate branch: keep your diff to the except clauses.` },
]

const COMMON = `You are working on zendriver, an async Chrome DevTools Protocol browser automation library for Python >= 3.10. Main checkout: /home/user/zendriver (designated branch ${BASE}, base commit 064148f). Repo: aliciusschroeder/zendriver.

HARD RULES
- NEVER push anywhere, never open PRs/issues/comments, never touch cdpdriver/zendriver. A background sync pushes fix branches for us.
- NEVER modify the main checkout /home/user/zendriver or its branch ${BASE}. Work only in YOUR git worktree (your current working directory; run \`pwd\` and \`git worktree list\` first). Scratch files go under ${SCR}/fix/<group-id>/.
- Do not edit CHANGELOG.md (the supervisor adds changelog lines at integration). Out of scope: zendriver/cdp/ (generated), docs/, examples/, CI config.
- Commits: descriptive message, imperative subject, no Co-authored-by or other trailers, no session links, no model names.

ENVIRONMENT
- In your worktree run \`uv sync --all-groups\` first (creates the worktree's own .venv from the local uv cache), then confirm with \`uv run python -c "import zendriver; print(zendriver.__file__)"\` that zendriver is imported from YOUR worktree.
- Lint: \`bash scripts/lint.sh\` (ruff check, ruff format --check, mypy over zendriver scripts examples tests). Format: \`bash scripts/format.sh\`.
- Browser tests need Chromium on PATH: \`export PATH=${SCR}/bin:$PATH\`, then e.g. \`ZENDRIVER_TEST_BROWSERS=headless uv run pytest tests/core/test_tab.py -p no:cacheprovider -q\`. The container runs as root (is_root() turns the sandbox off).
- Gotchas: Connection uses the CantTouchThis metaclass, so its class attributes can't be monkeypatched (patch instances, Listener or websockets.connect, or use a fake in-process websockets server on 127.0.0.1:0). Monkeypatch zendriver.core.config.is_root to test sandbox=True. asyncio.wait_for(x, 0) cancels x before its first step: never use timeout=0 to test a hang path; use a positive timeout plus an outer safety net that does not depend on the code under test. Line numbers drift: cite function names. On Python >= 3.12 asyncio.wait_for no longer creates a task, so some ordering races only show there. tests/core/test_connection.py already has a FakeWebSocket you can reuse.
- Look at existing tests in the target test module for fixtures and style (pytest-asyncio, the browser fixture in tests/conftest.py). Prefer browser-free unit tests; add a real-browser test only where the bug shows up only with Chrome.`

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    group_id: { type: 'string' },
    status: { type: 'string', enum: ['done', 'blocked'] },
    branch: { type: 'string' },
    commit: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    tests_added: { type: 'array', items: { type: 'string' } },
    fail_before: { type: 'string' },
    pass_after: { type: 'string' },
    lint_ok: { type: 'boolean' },
    format_ok: { type: 'boolean' },
    affected_tests: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['group_id', 'status', 'branch', 'commit', 'files_changed', 'summary', 'tests_added', 'fail_before', 'pass_after', 'lint_ok', 'format_ok', 'affected_tests', 'notes'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    group_id: { type: 'string' },
    verdict: { type: 'string', enum: ['approve', 'request-changes'] },
    reviewed_commit: { type: 'string' },
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['blocking', 'non-blocking'] },
          description: { type: 'string' },
        },
        required: ['severity', 'description'],
      },
    },
    test_fails_on_base: { type: 'string', enum: ['yes', 'no', 'not-run'] },
    test_passes_on_fix: { type: 'string', enum: ['yes', 'no', 'not-run'] },
    lint_ok: { type: 'string', enum: ['yes', 'no', 'not-run'] },
    summary: { type: 'string' },
  },
  required: ['group_id', 'verdict', 'reviewed_commit', 'items', 'test_fails_on_base', 'test_passes_on_fix', 'lint_ok', 'summary'],
}

function groupFiles(g) {
  return `Group definition: ${SCR}/triage/groups/${g.id}.md\nStage 3 verification (three independent verifiers, with their prototype diffs, regression tests and risk analysis): ${SCR}/triage/verified/${g.id}.md\nThe verifiers' prototypes are under ${SCR}/verify/${g.id}-fixsafety/ (and -reproduce/-refute). They were verified, but re-validate everything yourself; take what is right, not what is there.`
}

function fixerPrompt(g, round, review) {
  const branch = `fix/${g.slug}`
  let p = `${COMMON}\n\nYOUR TASK: fix group ${g.id} (${g.slug}) — round ${round} of at most 2.\n${groupFiles(g)}\n\nSupervisor notes for this group:\n${g.notes}\n\nSuggested test location: ${g.tests} (append to the existing module that tests the code you change; create a new tests/core/test_<module>.py only if none exists).\n`
  if (round === 1) {
    p += `
STEPS
1. In your worktree: if branch ${branch} already exists (locally or as origin/${branch}, e.g. from an interrupted earlier attempt) or origin/wip/${branch} exists, inspect it and continue from it if it is sound. Otherwise create it from the designated branch: \`git checkout -B ${branch} ${BASE}\` (your worktree may start from origin/main, which lacks the base commits — always branch from ${BASE}). Verify \`git log --oneline -1 ${BASE}\` is 064148f.
2. Write the MINIMAL patch that fixes every member of the group, matching the surrounding style and comment density. Don't change type annotations or public signatures unless the group requires it.
3. Add regression tests that FAIL before the fix and PASS after it. Show both runs: after committing, temporarily restore the base sources with \`git checkout ${BASE} -- zendriver/\`, run the new tests (they must fail, for the right reason), then \`git checkout HEAD -- zendriver/\` and run them again (they must pass). Paste the key pytest summary lines.
4. Run \`bash scripts/format.sh\`, \`bash scripts/lint.sh\` and the affected test files (with the browser on PATH). Everything must pass; if a pre-existing test fails, check whether it also fails on ${BASE} and say so.
5. Make exactly ONE commit on ${branch} on top of ${BASE} (\`git log --oneline ${BASE}..${branch}\` shows one commit). Then run \`git checkout --detach\` so the branch is not held by your worktree (a reviewer and possibly a second-round fixer need it).
If the group cannot be fixed minimally, return status=blocked with the reason.`
  } else {
    p += `
A reviewer requested changes on your branch ${branch}:
${JSON.stringify(review, null, 1)}

STEPS
1. In your worktree: \`git checkout ${branch}\` (it was left detached by the previous fixer; if the branch is checked out elsewhere, \`git checkout --detach ${branch}\` and later \`git branch -f ${branch} HEAD\`).
2. Address every BLOCKING item (and non-blocking ones when they are right and cheap). If you disagree with an item, explain why in notes instead of changing code.
3. Keep the branch at exactly ONE commit on top of ${BASE}: amend (\`git commit --amend\`), never add a second commit.
4. Re-show the regression tests failing on base sources and passing on the fix (same procedure: \`git checkout ${BASE} -- zendriver/\` ... \`git checkout HEAD -- zendriver/\`), run format.sh, lint.sh and the affected test files.
5. \`git checkout --detach\` at the end.`
  }
  p += `\n\nReturn the schema: branch, final commit sha, files changed, summary, tests added (file::test names), fail_before and pass_after (commands + key output lines), lint/format results, affected test results, notes (residual risks, related sites you deliberately left alone).`
  return p
}

function reviewerPrompt(g, fix, round) {
  const branch = `fix/${g.slug}`
  return `${COMMON}\n\nYOUR TASK: ADVERSARIAL REVIEW of the fix for group ${g.id} (${g.slug}), review round ${round}. You did not write it; try to find what is wrong with it.\n${groupFiles(g)}\n\nSupervisor notes for this group (what the fix was asked to do):\n${g.notes}\n\nThe fixer reported:\n${JSON.stringify(fix, null, 1)}\n
STEPS
1. In your own worktree: \`git checkout --detach ${branch}\` and \`uv sync --all-groups\`. Read \`git diff ${BASE}...${branch}\` in full and the surrounding code.
2. Review: correctness (does it fix every member's scenario?), minimality (no unrelated changes, matches style), new failure modes (deadlocks, lock ordering, re-entrancy — asyncio.Lock is not reentrant — swallowed errors or CancelledError, leaked tasks, behaviour changes callers would notice, Python 3.10 compatibility e.g. ExceptionGroup/asyncio.timeout are 3.11+), and whether the tests are meaningful (could they pass for the wrong reason? are they flaky / timing-dependent? do they use timeout=0 on a hang path?).
3. Prove the tests really fail without the fix: \`git checkout ${BASE} -- zendriver/\`, run the new tests (expect failures for the right reason), \`git checkout HEAD -- zendriver/\`, run them again (expect pass). Run each new test 3 times to look for flakiness. Run \`bash scripts/lint.sh\`.
4. Verdict: "approve" only if there is no blocking item. Otherwise "request-changes" with concrete, actionable items (severity blocking/non-blocking). Do not modify the branch yourself.`
}

async function fixGroup(g) {
  const fix1 = await agent(fixerPrompt(g, 1), { label: `fix:${g.id}`, phase: 'Fix', schema: FIX_SCHEMA, isolation: 'worktree' })
  if (!fix1 || fix1.status === 'blocked') {
    log(`${g.id}: fixer round 1 blocked or failed`)
    return { group: g.id, slug: g.slug, status: 'BLOCKED', reason: fix1 ? fix1.notes : 'fixer returned nothing', rounds: [{ fix: fix1 }] }
  }
  const rev1 = await agent(reviewerPrompt(g, fix1, 1), { label: `review:${g.id}`, phase: 'Review', schema: REVIEW_SCHEMA, isolation: 'worktree' })
  if (rev1 && rev1.verdict === 'approve') {
    log(`${g.id}: approved in round 1 (${fix1.commit.slice(0, 9)})`)
    return { group: g.id, slug: g.slug, status: 'APPROVED', commit: fix1.commit, rounds: [{ fix: fix1, review: rev1 }] }
  }
  const fix2 = await agent(fixerPrompt(g, 2, rev1), { label: `fix2:${g.id}`, phase: 'Round 2', schema: FIX_SCHEMA, isolation: 'worktree' })
  if (!fix2 || fix2.status === 'blocked') {
    log(`${g.id}: fixer round 2 blocked or failed`)
    return { group: g.id, slug: g.slug, status: 'BLOCKED', reason: 'round 2 fixer blocked: ' + (fix2 ? fix2.notes : 'returned nothing'), rounds: [{ fix: fix1, review: rev1 }, { fix: fix2 }] }
  }
  const rev2 = await agent(reviewerPrompt(g, fix2, 2), { label: `review2:${g.id}`, phase: 'Round 2', schema: REVIEW_SCHEMA, isolation: 'worktree' })
  const ok = rev2 && rev2.verdict === 'approve'
  log(`${g.id}: ${ok ? 'approved in round 2' : 'BLOCKED after 2 rounds'}`)
  return { group: g.id, slug: g.slug, status: ok ? 'APPROVED' : 'BLOCKED', commit: fix2.commit, reason: ok ? '' : 'reviewer still requests changes after round 2', rounds: [{ fix: fix1, review: rev1 }, { fix: fix2, review: rev2 }] }
}

const results = await pipeline(GROUPS, g => fixGroup(g))
return { results: results.filter(Boolean) }
