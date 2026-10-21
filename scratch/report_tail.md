
Notes on verification votes: every group got 3 confirming lenses except Q12 (3x partially-confirmed: member SEED-X3 refuted),
R15 (SEED-K3 `--load-extension` re-add confirmed 2/3), R27 and R44 (one partially-confirmed lens each).

## Follow-ups from the final cross-fix review (all fixed above as U1–U3)
- cancellation-1 (Q2+Q12): a timed-out lookup that cut off a pending auto `Domain.enable` made every later send re-send it; on a dialog-blocked page even `Page.handleJavaScriptDialog` could never be sent → U1 keeps a written enable marked enabled (a stand-in tracks a later rejection).
- cancellation-2 (Q2, Py 3.10/3.11): `asyncio.wait_for` dropped a cancellation that arrived together with a poll's answer (CPython gh-86296) → U2 `_wait_for` helper.
- connection-1 (Q1, Py ≥ 3.12): the receive-error break failed session commands whose replies were already queued → U1 sentinel in the session inbox.
- connection-2/-3, lifecycle-3: `send()` transmitted a command it had already failed, left never-sent transactions behind ("exception never retrieved"), and kept a cancelled manual enable recorded → U1.
- lifecycle-1: concurrent `stop()` still raised with a live proxy tunnel (pre-existing, but the changelog claimed it) → U3 idempotent `ProxyForwarder.close()`.
- lifecycle-2: a new Q3 test was timing-dependent on Py < 3.12 → U3 synchronises on the actual event.

## Dropped findings
- A9.10 `find_binary` picks the shortest path — intended behaviour (code comment "assuming the shortest path wins").
- A9.6 `is_posix` false on BSD — unsupported platform, only simulated.
- SEED-X3 (proxy.py `open_tunnel` `except BaseException`) — refuted 3/3 by verification: it re-raises, cancellation propagates.
- Duplicates: every other finding was merged into exactly one group (members listed per group).

## Residual risks and notes (non-blocking reviewer notes, not fixed)
- Q2: a single lookup slower than timeout + 0.5 s (very large pages with short timeouts) is now cut off; `timeout=None` raises TypeError. Documented in the commit and changelog.
- U1: with handlers in two lazily enabled domains, recovery from a dialog wedge takes one bounded attempt per domain (nested enables).
- Pre-existing `asyncio.wait_for` bounds outside the Q2 methods (wait_for_ready_state, Tab.get, Connection.wait, Browser.get, Browser._stop) still have the Py 3.10/3.11 lost-cancellation window.
- Q1: a handler with the wrong arity logs a traceback per event; the receive-error path stops the reader until the next send (events-only waits stay pending until then).
- Q3: worst-case `stop()` of a frozen browser is ~23 s (5 s detach + 5 s close + websockets close timeout + 3 s terminate); a second concurrent `close()` of a proxy forwarder returns before the first finished.
- Q4: cleanup of a launched browser on a failed/cancelled start uses terminate() (connection closed first so an attached browser is never sent Browser.close).
- Windows CI: new stub tests relying on SIGTERM semantics were not run on Windows.
- Test suite: existing tests that `evaluate()` right after `browser.get()` race the page load (Browser.get returns when navigation starts): test_get_position_abs_includes_scroll_offset, test_handler_raising_type_error_is_called_once, test_element_get_returns_empty_attribute_value, test_shadow_children_includes_closed_shadow_root, test_is_scrolled_to_bottom, test_infinite_scrolling_tutorial_1. Pre-existing (base fails 2/4 runs); not fixed.

## Areas not covered
- zendriver/cdp/ (generated; out of scope) — generator bugs that need regeneration are report-only (R47).
- Not run: Windows/macOS-only paths (`_windows_platform_version`, `is_root` via ctypes, msedge/brave lookup), real BSD, headful window-manager behaviour (only Xvfb without WM), real Cloudflare pages (Turnstile simulated), record_video/is_recording, send_file/select_option probing, free_port TOCTOU between concurrent starts, IPv6 hosts in HTTPApi.
- Read but not probed: get_frames while targets change, find()/select() during navigation, js_dumps fallback (`recurse` undefined in variant B), local-storage edge origins, flash_point page globals, intercept at RequestStage.RESPONSE against a live server, DownloadExpectation across tabs, non-ASCII digits in keys.py.
- No second detection round was triggered: every finder returned >= 4 findings and none ran out of time.
