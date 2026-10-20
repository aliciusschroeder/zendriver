export const meta = {
  name: 'zendriver-detect',
  description: 'Stage 1: two blind sweeps (file-scoped + bug-class) of read-only bug finders over zendriver/core, with a second round for thin areas',
  phases: [
    { title: 'Sweep A', detail: 'file-scoped finders' },
    { title: 'Sweep B', detail: 'bug-class finders across zendriver/core' },
    { title: 'Round 2', detail: 'fresh finders for areas with 0-1 findings or that ran out of time' },
  ],
}

const SCR = '/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad'

const PREAMBLE = `You are a read-only bug finder in a systematic bug hunt of zendriver, an async Chrome DevTools Protocol (CDP) browser automation library for Python >= 3.10. The repo is checked out at /home/user/zendriver (branch ccr-9a8a26e1-b0l7bh). Find REAL, PROVABLE bugs in your assigned scope.

Calibration — a recent targeted pass found three bugs like these that no test caught:
- Config.__call__ appended a flag that was already in the defaults.
- Connection.aopen had a check-then-await race: N concurrent sends opened N websockets, N-1 sends hung, and the extra sockets leaked.
- Tab.get/Browser.get timeouts bounded only one of several awaits; separately a bare \`except:\` swallowed CancelledError so wait_for timeouts and task.cancel() silently did nothing.
The tests were either missing or never reached the code path (e.g. timeout=0). Assume more bugs like these exist.

HARD RULES
- NEVER modify anything under /home/user/zendriver (no edits, no git commands that change state, no uv sync). Reading and running read-only commands (git log -S, git blame, grep) is fine.
- Scratch probes go ONLY under ${SCR}/<your-scratch-dir>/ (given below). Create it with mkdir -p.
- Out of scope: zendriver/cdp/ (generated code), docs/, examples/, CI config. You may read zendriver/cdp/ to understand types but do not report bugs in it.
- No style nits, no "could be cleaner", no speculation without a traced path from a public API call. Each finding must describe a concrete failure: inputs -> wrong result / hang / leak / crash.
- Skip the KNOWN ISSUES below entirely (do not report them, or trivial restatements of them).

KNOWN ISSUES — do NOT report:
Already fixed:
- the duplicate --disable-session-crashed-bubble flag
- the Connection.aopen websocket race (now guarded by _open_lock)
Owned by another PR:
- Tab.get / Browser.get timeouts that cover only part of the method
Already-known leads (will be verified separately):
- Connection._register_handlers has a bare \`except:\` that swallows CancelledError; the broad excepts in element.py and proxy.py with the same pattern. (A DIFFERENT site elsewhere that swallows CancelledError IS new and reportable.)
- Config.browser_args property neither merges --disable-features nor removes duplicates, so it differs from what Config() returns.
- User browser_args that repeat flags Config adds itself (headless, no-sandbox, lang, webgl, webrtc) are not deduplicated.
- Browser.start adds --load-extension again on every start when a Config is reused.
- Config keeps a reference to the caller's browser_args list, so add_argument mutates that list.
- Config.add_argument rejects any arg containing "lang" or "headless" anywhere (e.g. --disable-features=LanguageDetectionAPI).
- Listener.listener_loop catches only TimeoutError, CancelledError and ConnectionClosed; any other exception (e.g. websockets ConcurrencyError) kills the listener silently.
- On ConnectionClosed the listener does not reset connection.websocket, so aopen never reconnects.
- aclose() during a connect that is still in progress does nothing, and the connection opens after the "close".
- A send() cancelled by wait_for leaves its Transaction in conn.mapper until a reply arrives or the connection closes.
- Browser.get(new_tab=True) timing out after Target.createTarget leaves an orphaned tab.

ENVIRONMENT FOR PROBES (optional but encouraged when cheap and it changes your confidence)
- Python: /home/user/zendriver/.venv/bin/python (zendriver is installed from the repo). Run probes from your scratch dir.
- Real headless Chromium: export PATH=${SCR}/bin:$PATH (a symlink "chromium" lives there). e.g. \`browser = await zendriver.start(headless=True)\`. The container runs as root, so is_root() disables the sandbox automatically.
- Fake CDP peer: an in-process \`websockets.serve\` server on 127.0.0.1:0 that answers/drops/delays replies by method name is a good way to probe Connection/Listener/Tab behaviour without Chrome. websockets version is 14.1.
- Always wrap probes in an outer safety net (e.g. \`timeout 60 python probe.py\` and/or asyncio.wait_for with a POSITIVE timeout). Never use timeout=0 to test a hang path: asyncio.wait_for(x, 0) cancels x before its first step.
- Connection uses the CantTouchThis metaclass, so its class attributes can't be monkeypatched; patch instances, Listener, or websockets.connect, or use a fake server.
- To print where a hung task is stuck: task.print_stack() or task.get_stack().
- Line numbers drift; always cite the function name with the line.

OUTPUT
Return findings via the schema. For each finding: title, bug_class, file (repo-relative), function, line, scenario (concrete, starting from a public API call), why_tests_miss (look at tests/ to justify), repro_idea, severity (crash|hang|leak|wrong-result|cosmetic), confidence (high|medium|low), and evidence (what you traced or what your probe printed). Also fill coverage: what you read in depth, what you did NOT cover, and whether you ran out of time/context. An empty findings list is fine if you genuinely found nothing that meets the bar — but look hard first.`

const SCOPES = [
  { id: 'A1', area: 'connection.py: Transaction, opening and closing, session attach', scope: `zendriver/core/connection.py from the top of the file through Connection.aclose: ProtocolException, Transaction (__init__, message, has_exception, __call__), EventTransaction, CantTouchThis, Connection.__init__, the target/property accessors, closed, _browser_connection, add_handler, remove_handlers, aopen, _attach_session, _detach_session, _fail_pending_transactions, aclose. Read the callers you need (browser.py start/stop/_handle_target_update, tab.py close, Listener in connection.py) to trace scenarios. Think about: Transaction result/error parsing edge cases, ProtocolException formatting, session attach/detach ordering, what state is left after detach/close, handler add/remove semantics with modules, reuse of a Connection after aclose.` },
  { id: 'A2', area: 'connection.py: send, wait, handlers, Listener', scope: `zendriver/core/connection.py from Connection.sleep through the end of the file: sleep, feed_cdp, wait, __aenter__/__aexit__, __await__, update_target, send, _register_handlers, _update_manual_domain, _prepare_headless, _prepare_expert, _next_message_id, _send_transaction, _receive_message, _send_oneshot, _accepts_connection_argument, Listener (run, idle, cancel, running, listener_loop, callback dispatch). Read callers in tab.py/browser.py as needed. Think about: idle detection correctness in wait(), __aexit__ re-raising, handlers mutated while iterating, sync callbacks dispatched via to_thread, events for flat sessions, message routing for sessions, domain enable/disable bookkeeping, _send_oneshot swallowing errors, oneshot vs send ordering.` },
  { id: 'A3', area: 'browser.py: create, start, stop, process and connection lifecycle', scope: `zendriver/core/browser.py: module-level helpers (_user_agent_platform, _host_platform, _windows_platform_version, _host_platform_version, _host_architecture, _headless_user_agent), Browser.create, _atexit_cleanup, __init__, websocket_url, stopped, start, _wait_for_initial_tab, _read_headless_user_agent, test_connection, __aenter__/__aexit__, stop, _stop, _cleanup_temporary_profile, __del__. Also read zendriver/core/util.py start()/deconstruct_browser/registered instances as callers. Think about: process spawn/kill paths, connection retries in start, partial cleanup when start fails midway, temp profile removal, restart of a stopped Browser, atexit behaviour, multiple browsers, headless UA parsing for odd UA strings.` },
  { id: 'A4', area: 'browser.py: targets, get, tabs, cookies, HTTP helper', scope: `zendriver/core/browser.py: main_tab, tabs, get_tab, cookies, wait, _handle_target_update, get (but NOT the known partial-timeout issue), create_context, grant_all_permissions, tile_windows, _get_targets, _get_tab, headless_user_agent, _create_tab, update_targets, __iter__/__reversed__/__next__, CookieJar (get_all, set_all, save, load, clear), HTTPApi (get, post, _request), _to_cookiejar_cookie. Think about: targets list consistency when targets are created/destroyed/changed concurrently, tab identity, iterator protocol correctness, cookie pattern filtering, cookie file round-trip, HTTPApi blocking the event loop or mishandling errors, create_context proxy handling.` },
  { id: 'A5', area: 'tab.py, first third', scope: `zendriver/core/tab.py from the top of the file through Tab.query_selector (inclusive): Tab.__init__, inspector_url, inspector_open, disable_dom_agent, open_external_inspector, get_frames, _search_frames, find, select, find_all, select_all, _query_selector_all_with_frames, xpath, get (but NOT the known partial-timeout issue), query_selector_all, query_selector. Read element.py helpers they call. Think about: timeouts in find/select loops, retry logic on stale nodes, frame search, error handling for 'could not find node', xpath result handling, return types (None vs [] vs exception) matching docstrings.` },
  { id: 'A6', area: 'tab.py, middle third', scope: `zendriver/core/tab.py from Tab.find_elements_by_text through Tab.wait_for_ready_state (inclusive): find_elements_by_text, find_element_by_text, back, forward, reload, evaluate, js_dumps, close, get_window, get_content, maximize, minimize, fullscreen, medimize, set_window_size, activate, bring_to_front, set_window_state, scroll_down, scroll_up, is_scrolled_to_bottom, bypass_insecure_connection_warning, wait_for, wait_for_ready_state. Think about: evaluate's exception/await_promise handling and return values, close() state cleanup, window state transitions, wait_for timeouts, search cleanup (discardSearchResults), text matching.` },
  { id: 'A7', area: 'tab.py, last third', scope: `zendriver/core/tab.py from Tab.expect_request to the end of the file: expect_request, expect_response, expect_download, intercept, download_file, save_snapshot, screenshot_b64, save_screenshot, print_to_pdf, set_download_path, get_all_linked_sources, get_all_urls, verify_cf, _dispatch_mouse_event, mouse_move, mouse_down, mouse_up, mouse_click, mouse_drag, flash_point, get_local_storage, set_local_storage, set_user_agent, __call__, __eq__, __repr__. Think about: file path handling, download behaviour state, mouse event parameters (buttons/click count), url resolution in get_all_urls, set_user_agent interplay with the headless override, __eq__/__hash__ consistency.` },
  { id: 'A8', area: 'element.py', scope: `zendriver/core/element.py, all of it (Element, Position, create, resolve, update, attrs, click/mouse helpers, send_keys/clear_input, apply, get_js_attributes, query helpers, screenshot, is_recording, record_video, flash, highlight, set_value, select_option, etc.). Prioritise methods that await the browser, compute coordinates, or mutate node state. Remember the broad excepts in element.py that swallow CancelledError are already a known lead — skip that specific pattern, but other bugs at the same sites are fair game.` },
  { id: 'A9', area: 'config.py + util.py', scope: `zendriver/core/config.py and zendriver/core/util.py, all of both. Config: __init__, browser_args property, user_data_dir handling/temp dirs, __call__, add_argument, add_extension, extension handling, executable lookup (find_executable / find_chrome_executable), is_root, platform detection, __repr__. util: start(), deconstruct_browser, registered instances, filter_recurse, html_from_tree, circle/geometry helpers, compare_target_info, cdp_get_module, loop helpers, free_port. Remember: the Config issues in the KNOWN ISSUES list are already known; find different ones.` },
  { id: 'A10', area: 'keys.py + expect.py + intercept.py', scope: `zendriver/core/keys.py, zendriver/core/expect.py and zendriver/core/intercept.py, all of them, plus how tab.py/element.py call them. keys: key event generation for characters/special keys/modifiers, unicode, shift handling, KeyEvents.from_text / from_mixed_input etc. expect: Request/Response/Download expectations (handler registration and removal, context manager enter/exit, futures resolved twice, timeouts, value/body retrieval). intercept: Fetch interception setup/teardown, request pattern handling, continue/fulfill/fail, cleanup on exceptions.` },
  { id: 'A11', area: 'cloudflare.py + proxy.py + _contradict.py', scope: `zendriver/core/cloudflare.py, zendriver/core/proxy.py and zendriver/core/_contradict.py, all of them. cloudflare: challenge detection and clicking loops, timeouts, shadow root traversal. proxy: the local proxy server/forwarder, auth handling, connection lifecycle, task cleanup, port selection (the broad excepts that swallow CancelledError are a known lead — find other bugs). _contradict: ContraDict attribute/item semantics, nested conversion, copy/deepcopy, default handling.` },
  { id: 'A12', area: 'tests/: test-gap audit', scope: `tests/ (all of tests/core, tests/bot_detection, tests/docs, conftest.py). This is a TEST-GAP AUDIT. Look for: tests whose parameters or mocks skip the path they claim to cover (e.g. timeout=0 that never reaches the hang path, mocks that replace the logic under test); assertions that can never fail (asserting on a value the test itself set, try/except that swallows AssertionError, asserting truthiness of a non-empty object); important public behaviour with no test at all. Report a test gap only when you can name the concrete behaviour/bug it would let through, ideally a real bug in zendriver/core you then confirm by reading the code (report that bug with bug_class "test-gap" if it is the gap that hides it, otherwise its real class). Use bug_class "test-gap" and the severity of the bug it hides (cosmetic if it hides nothing concrete — but prefer not to report those).` },
  { id: 'A13', area: 'scripts/generate_cdp.py', scope: `scripts/generate_cdp.py (the CDP code generator; the generated output in zendriver/cdp/ is out of scope for reporting, but you may read it to confirm what the generator emits). Look for generator bugs that produce wrong runtime behaviour in the generated code: wrong from_json/to_json for optional fields, arrays, enums, nested types, falsy values (0, "", False) being dropped, event parsing, name mangling collisions, wrong return types for commands with multiple returns. Report the generator site as file/function/line, and cite one concrete generated function in zendriver/cdp/ that exhibits the bug and a public zendriver API that is affected.` },
  { id: 'B13', area: 'bug class: unbounded awaits', scope: `BUG CLASS across ALL of zendriver/core/*.py: UNBOUNDED AWAITS. Enumerate every CDP send (connection.send / tab.send / _send_oneshot), every Future/Transaction await, every asyncio.Event.wait / Queue.get / Condition wait that is reachable from a public method that takes or implies a timeout (timeout=, wait_for, find/select with timeout, wait_for_ready_state, expect_*, download, cloudflare verify, Browser.start connection retries, stop()). Report each place where the public timeout does not actually bound the wait, and each public method that can wait on the browser forever when the browser stops responding to one method (e.g. Chrome never answers a command, or an event never arrives). Exclude the known Tab.get/Browser.get partial-timeout issue. Tip: grep for 'await ', '.wait()', 'wait_for(' and trace upward to the public API.` },
  { id: 'B14', area: 'bug class: concurrency', scope: `BUG CLASS across ALL of zendriver/core/*.py: CONCURRENCY. Check-then-await races (state checked, then an await, then the state is used as if unchanged), shared mutable state touched from several tasks (mapper, handlers dict/lists mutated while the listener iterates, targets list, _sessions), lock scope and lock ordering (_attach_lock, _open_lock, any others), re-entrancy (asyncio.Lock is not reentrant — any path where a lock holder awaits something that tries to take the same lock), fire-and-forget tasks (asyncio.create_task / ensure_future without keeping a reference or observing the exception: their exceptions are lost and they can be garbage-collected mid-flight), sync callbacks run in threads touching asyncio objects. Exclude the already-fixed aopen race and the known issues.` },
  { id: 'B15', area: 'bug class: exception and cancellation handling', scope: `BUG CLASS across ALL of zendriver/core/*.py: EXCEPTION AND CANCELLATION HANDLING. Bare \`except:\` or \`except BaseException\` around awaits, swallowed asyncio.CancelledError (also via \`except Exception\` on Python 3.7-era assumptions, or catching CancelledError and continuing), loops that die on unexpected exceptions, errors logged at debug level and dropped where the caller needs them, wrong exception types raised (e.g. ValueError where callers catch ProtocolException, TimeoutError vs asyncio.TimeoutError on 3.10), finally blocks that raise and mask the original error, __aexit__ that changes the exception. The _register_handlers bare except and the element.py/proxy.py broad excepts are already-known leads — skip those exact sites but report OTHER sites with the same or different problems.` },
  { id: 'B16', area: 'bug class: resource lifecycle and state consistency', scope: `BUG CLASS across ALL of zendriver/core/*.py: RESOURCE LIFECYCLE AND STATE CONSISTENCY. (a) Leaks on close, cancel and error paths: sockets, subprocesses, temporary profile directories, handlers left registered, tabs/targets, threads, files; partial cleanup when an exception happens mid-cleanup. (b) State that is duplicated or disagrees with itself (e.g. a property that doesn't match real behaviour, a cached list that is never refreshed, flags set before an action that then fails). (c) Aliasing of mutable objects the caller passed in (lists/dicts stored without copying then mutated, mutable default arguments). (d) Validation that rejects valid input. (e) Docstrings that contradict the behaviour in a way that misleads callers into a bug. Skip the known Config issues.` },
]

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          bug_class: { type: 'string' },
          file: { type: 'string' },
          function: { type: 'string' },
          line: { type: 'integer' },
          scenario: { type: 'string' },
          why_tests_miss: { type: 'string' },
          repro_idea: { type: 'string' },
          severity: { type: 'string', enum: ['crash', 'hang', 'leak', 'wrong-result', 'cosmetic'] },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          evidence: { type: 'string' },
        },
        required: ['title', 'bug_class', 'file', 'function', 'line', 'scenario', 'why_tests_miss', 'repro_idea', 'severity', 'confidence', 'evidence'],
      },
    },
    coverage: {
      type: 'object',
      properties: {
        read_in_depth: { type: 'string' },
        not_covered: { type: 'string' },
        ran_out_of_time: { type: 'boolean' },
      },
      required: ['read_in_depth', 'not_covered', 'ran_out_of_time'],
    },
  },
  required: ['findings', 'coverage'],
}

function finderPrompt(s, round, prior) {
  const dir = round === 1 ? `detect-${s.id}` : `detect-r2-${s.id}`
  let p = `${PREAMBLE}\n\nYOUR SCRATCH DIR: ${SCR}/${dir}/\n\nYOUR SCOPE (${s.id} — ${s.area}):\n${s.scope}\n\nRead your scope in depth (at most ~700 lines in depth plus the callers you need). Trace each suspicious path from a public API call to the failure.`
  if (round === 2) {
    p += `\n\nROUND 2: a previous finder covered this same scope and returned few findings or ran out of time. You are a fresh pair of eyes. Do NOT re-report these already-found items:\n${prior.titles.length ? prior.titles.map(t => '- ' + t).join('\n') : '- (none)'}\nThe previous finder reported it did NOT cover: ${prior.not_covered || '(nothing stated)'}\nPrioritise what it did not cover, then dig deeper into the subtle paths (error/cancel/close paths, concurrency, edge-case inputs) rather than the obvious happy path.`
  }
  return p
}

const sweepA = SCOPES.filter(s => s.id.startsWith('A'))
const sweepB = SCOPES.filter(s => s.id.startsWith('B'))

const runFinder = (s, round, prior) => agent(finderPrompt(s, round, prior), {
  label: `${round === 1 ? '' : 'r2:'}${s.id} ${s.area}`.slice(0, 70),
  phase: round === 1 ? (s.id.startsWith('A') ? 'Sweep A' : 'Sweep B') : 'Round 2',
  schema: FINDINGS_SCHEMA,
}).then(r => ({ id: s.id, area: s.area, round, result: r }))

// Interleave B finders with A finders so both sweeps progress concurrently; they never see each other's results.
const order = []
const maxLen = Math.max(sweepA.length, sweepB.length)
for (let i = 0; i < maxLen; i++) {
  if (i < sweepA.length) order.push(sweepA[i])
  if (i % 3 === 0 && sweepB[Math.floor(i / 3)]) order.push(sweepB[Math.floor(i / 3)])
}
for (const b of sweepB) if (!order.includes(b)) order.push(b)

const round1 = await parallel(order.map(s => () => runFinder(s, 1)))

const r1 = round1.filter(Boolean)
for (const s of SCOPES) {
  const r = r1.find(x => x.id === s.id)
  const n = r && r.result ? r.result.findings.length : 'FAILED'
  log(`R1 ${s.id}: ${n} findings${r && r.result && r.result.coverage.ran_out_of_time ? ' (ran out of time)' : ''}`)
}

const needR2 = SCOPES.filter(s => {
  const r = r1.find(x => x.id === s.id)
  if (!r || !r.result) return true
  return r.result.findings.length <= 1 || r.result.coverage.ran_out_of_time
})
log(`Round 2 for: ${needR2.map(s => s.id).join(', ') || '(none)'}`)

const round2 = await parallel(needR2.map(s => () => {
  const r = r1.find(x => x.id === s.id)
  const prior = {
    titles: r && r.result ? r.result.findings.map(f => f.title) : [],
    not_covered: r && r.result ? r.result.coverage.not_covered : 'previous finder failed to return',
  }
  return runFinder(s, 2, prior)
}))

return { round1: r1, round2: round2.filter(Boolean), round2_requested: needR2.map(s => s.id) }
