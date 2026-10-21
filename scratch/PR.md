# Fix hangs, leaks and wrong results found by a repo-wide bug hunt

## Description

<!-- Please describe your change below this line -->

A systematic bug hunt over `zendriver/core` found 172 problems, which were grouped into 47 root causes. Each group was reproduced or refuted by three independent verifiers. This PR fixes the 12 highest-ranked confirmed groups, plus 3 interaction problems that only showed up once those fixes were combined. Each fix has regression tests that fail on the base and pass with the fix. The remaining confirmed groups are below the fix cap or need a design decision, so they are listed at the end and not changed here.

The branch also contains the two earlier fixes from `claude/serene-dijkstra-2awdy9`: the duplicate `--disable-session-crashed-bubble` flag and the `Connection.aopen` websocket race.

**Connection and listener (`connection.py`)**
- A response the bundled CDP parser rejects (for example a field or enum value from a newer Chrome) now fails only that command with `ProtocolException`. Before, the listener died and `send()` hung forever.
- A handler that raises when it is called is logged and skipped instead of stopping the listener.
- An unexpected receive error fails the pending commands instead of leaving them hanging. A flat-session tab restarts a stopped browser listener.
- `_register_handlers` no longer raises `ValueError` when a nested send already pruned a stale domain.
- A timeout or cancellation during an automatic `Domain.enable` is no longer swallowed by a bare `except:`. `Element.mouse_click` had the same problem around `flash()`.
- A command that never left is removed from the mapper and is not sent after it was already reported as failed. An enable that did reach the browser stays marked as enabled, so a page blocked by a dialog can still be sent `Page.handleJavaScriptDialog`.
- `async with tab:` and `async with browser:` let exceptions propagate unchanged.

**Timeouts (`tab.py`, `cloudflare.py`)**
- `find`, `select`, `find_all`, `select_all`, `xpath`, `wait_for`, `tab(...)`, `verify_cf` and `cf_is_interactive_challenge_present` now return or raise at their timeout when the renderer stops answering (for example an open `alert()`), instead of hanging forever.
- The bound keeps the last attempt at the deadline, with 0.5 s of grace, and keeps the existing one-shot behaviour for `timeout <= 0`.
- A caller's cancellation is not lost on Python 3.10/3.11 (CPython gh-86296).
- Known trade-off: a single lookup that takes longer than timeout + 0.5 s is now cut off.
- `tab(text=...)` and `tab(selector=...)` are no longer swapped.
- `wait_for_ready_state()` accepts a later state, so the default `"interactive"` works on a page that is already `complete`.

**Browser lifecycle (`browser.py`, `util.py`, `proxy.py`)**
- `stop()` always terminates the process and removes the temporary profile:
  - The CDP steps are bounded, so a frozen browser no longer blocks it.
  - A crash just before `stop()` no longer aborts the cleanup.
  - Concurrent `stop()` calls, including with proxy forwarders, no longer raise.
  - The cleanup at exit under `asyncio.run` no longer leaks the profile.
- A failed or cancelled `start()` stops what it launched. An existing browser that `start()` only attached to is left running.
- Chrome's stderr is drained, so the browser no longer stalls once about 64 KiB of logs accumulate. The startup-failure log now shows stderr even while Chrome is still running.

**Other**
- `expect_request`/`expect_response` no longer pair a request with another request's response when several matching requests start at once (Python ≥ 3.12).
- `ContraDict` keys such as `clear`, `items` or `get` no longer shadow the dict methods. For example, `<br clear="all">` used to break `Element.update()`.

**Testing:** 106 new tests, mostly browser-free (fake websocket or patched instances).
- Full headless suite (`ZENDRIVER_TEST_BROWSERS=headless uv run pytest -n 4`): 224 passed and 1 skipped on Python 3.13 (3 of 3 runs). On Python 3.10, 222 passed and 3 skipped (2 of 2 runs); the 2 extra skips are `ExceptionGroup` cases that need 3.11+.
- The 106 new tests were each run 5 times: no failures.
- Pre-existing flakiness, not changed here: a few existing tests call `evaluate()` right after `browser.get()`, which returns once navigation starts, so they race the page load. The base failed 2 of 4 full runs on them.

**Confirmed but not changed in this PR** (report-only, ranked below the cap or needing a design decision):
- hidden-element `click()`
- temporary-profile sharing via `repr(config)`
- `Config` argument assembly and validation
- connection state after close and reconnect
- `Browser.get(new_tab=True)` orphaned tab
- expert and headless preparation races
- `feed_cdp` from sync handlers
- `send_keys` newline
- `http_proxy` used for the local DevTools endpoint
- session attach/detach races
- restart after `stop()`
- remote connections requiring a local Chrome
- `autodiscover_targets=False`
- domain enable/disable lifecycle
- multi-word CDP domains
- iframe tree recursion
- DOM query edge cases
- `expect_*` futures and `loadingFailed`
- download state per browser context
- element screenshots on mirrored or scrolled elements
- `Element.apply` exceptions and `clear_input` on `<textarea>`
- `Element` attribute plumbing
- lazy headless UA override on new tabs
- `find` text semantics
- concurrent DOM queries
- `keys.py` events
- assorted `Tab`, `Browser`, cloudflare, proxy, `ContraDict` and util issues
- the CDP generator

## Pre-merge Checklist

<!--
Check each box by marking it with an x, like this: "- [x]"

Before creating your pull request, please ensure each item is completed.
-->

- [x] I have described my change in the section above.
- [x] I have ran the [`./scripts/format.sh`](https://github.com/cdpdriver/zendriver/blob/main/scripts/format.sh) and [`./scripts/lint.sh`](https://github.com/cdpdriver/zendriver/blob/main/scripts/lint.sh) scripts. My code is properly formatted and has no linting errors.
- [x] I have ran `uv run pytest` and ensured all tests pass.
- [x] I have added my change to [CHANGELOG.md](https://github.com/cdpdriver/zendriver/blob/main/CHANGELOG.md) under the `[Unreleased]` section.
