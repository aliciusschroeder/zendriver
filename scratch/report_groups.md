### Q1 listener-robustness
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/connection.py:Transaction.__call__:126; members SEED-L1, A1.1, A2.3, B15.1, B15.4, A2.4
- patch: Keep the listener alive and fail commands instead of hanging them (zendriver/core/connection.py); commit 258db4cf8 on fix/listener-robustness, merged as 4495b70
- tests added (8): test_unparsable_response_fails_only_its_command[generated-parser], test_unparsable_response_fails_only_its_command[custom-raises], test_unparsable_response_fails_only_its_command[custom-does-not-stop], test_handler_that_fails_when_called_does_not_stop_the_listener, test_unexpected_receive_error_fails_pending_commands[not-json], test_unexpected_receive_error_fails_pending_commands[recv-raises], test_flat_session_send_restarts_the_browser_listener, test_detaching_a_session_stops_its_listener_quietly

### Q2 timeout-bounds
- status: **fixed** (verify CCC; review approved in round 2)
- evidence: zendriver/core/tab.py:Tab.select (also Tab.find, Tab.find_all, Tab.select_all):351; members B13.1, A5.1, B13.2, A6.5, B13.3, A11.4, A5.7
- patch: Bound the polling methods by their timeout when CDP does not answer (zendriver/core/tab.py, zendriver/core/cloudflare.py); commit c37681300 on fix/timeout-bounds, merged as b5f083e
- tests added (12): test_xpath_returns_empty_list_when_cdp_reply_never_arrives[0], test_xpath_returns_empty_list_when_cdp_reply_never_arrives[-1], test_xpath_returns_empty_list_when_cdp_reply_never_arrives[1], test_polling_methods_time_out_when_cdp_reply_never_arrives[select|select_include_frames|find|find_all|select_all|wait_for_selector|wait_for_text|call], test_xpath_with_zero_timeout_makes_one_attempt, test_xpath_sleeps_between_attempts, test_polling_methods_with_zero_timeout_make_one_attempt[select|find|wait_for], test_polling_methods_make_their_last_attempt_at_the_deadline[select|find|wait_for], test_cf_is_interactive_challenge_present_is_false_when_cdp_reply_never_arrives, test_verify_cf_raises_when_cdp_reply_never_arrives, test_verify_cf_raises_when_cdp_reply_never_arrives_during_clicks, test_verify_cf_click_delay_does_not_overrun_timeout

### Q3 stop-cleanup
- status: **fixed** (verify CCC; review approved in round 2)
- evidence: zendriver/core/browser.py:Browser._stop:879; members B13.5, A3.4, B15.3, B16.2, A1.2, A3.11, A3.1, B16.3
- patch: Make Browser.stop() always terminate the process and remove the profile (zendriver/core/browser.py); commit f783e5884 on fix/stop-cleanup, merged as e4846f7
- tests added (10): test_cancelled_browser_stop_leaves_no_unretrieved_exception, test_browser_stop_closes_proxy_forwarders_once_the_browser_is_gone[once_the_browser_is_gone], test_browser_stop_closes_proxy_forwarders_once_the_browser_is_gone[never], test_browser_stop_keeps_a_process_started_while_it_ran, test_browser_stop_terminates_a_browser_which_stopped_responding[Target.detachFromTarget] (round 1), test_browser_stop_terminates_a_browser_which_stopped_responding[Browser.close] (round 1), test_browser_stop_cleans_up_when_the_connection_drops_while_detaching (round 1), test_concurrent_browser_stop_calls_do_not_raise (round 1), test_atexit_cleanup_stops_the_browser_under_asyncio_run[stop_never_called] (round 1), test_atexit_cleanup_stops_the_browser_under_asyncio_run[stop_cancelled] (round 1)

### Q4 start-cleanup
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/browser.py:Browser.start / Browser.create:572; members A3.3, B15.2, B16.4
- patch: Stop the launched browser when Browser.start fails or is cancelled (zendriver/core/browser.py); commit f1e18489f on fix/start-cleanup, merged as 4767cf3
- tests added (3): test_cancelled_start_stops_the_launched_browser, test_failed_start_stops_the_launched_browser, test_failed_start_does_not_close_an_attached_browser

### Q5 stderr-pipe
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/util.py:_start_process:352; members B13.4, A3.5, A9.1, B16.1, B13.8
- patch: Drain the browser's stderr so a full pipe cannot stall Chrome (zendriver/core/util.py); commit 5b41bf1b8 on fix/stderr-pipe, merged as f092fe8
- tests added (5): test_start_process_does_not_block_a_process_that_writes_a_lot, test_read_process_stderr_returns_output_of_a_running_process, test_read_process_stderr_returns_output_of_an_exited_process, test_read_process_stderr_replaces_bytes_that_are_not_utf8, test_start_failure_logs_stderr_of_a_browser_that_is_still_running

### Q6 expect-pairing
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/expect.py:BaseRequestExpectation._request_handler:43; members B14.3, A2.8, A10.1, B15.9, B16.8
- patch: Keep expect_request/expect_response on the first matching request (zendriver/core/expect.py); commit 03610e826 on fix/expect-pairing, merged as 522a256
- tests added (4): test_expectation_burst_keeps_first_matching_request[RequestExpectation], test_expectation_burst_keeps_first_matching_request[ResponseExpectation], test_events_after_timed_out_waits_are_tracked_without_errors, test_download_expectation_burst_keeps_first_download

### Q7 register-handlers-snapshot
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/connection.py:Connection._register_handlers:720; members A2.1, B14.1
- patch: Skip already removed domains when pruning in _register_handlers (zendriver/core/connection.py); commit 40e8420ab on fix/register-handlers-snapshot, merged as d22627e
- tests added (1): test_send_drops_stale_domain_while_enabling_a_new_one

### Q8 contradict-shadowing
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/_contradict.py:ContraDict.__getattribute__:53; members A11.1, B16.15
- patch: Keep ContraDict keys from shadowing the dict methods (zendriver/core/_contradict.py); commit b5b3c318c on fix/contradict-shadowing, merged as c852ec8
- tests added (5): test_keys_named_like_dict_methods_do_not_shadow_them, test_other_keys_are_still_available_as_attributes, test_element_with_clear_attribute_can_update, test_element_with_items_attribute_can_be_printed, test_element_with_get_attribute_can_get_attributes

### Q9 aexit-reraise
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/connection.py:Connection.__aexit__:599; members A2.7, A3.8, B15.5, B16.11
- patch: Let exceptions propagate unchanged from Browser and Connection __aexit__ (zendriver/core/browser.py, zendriver/core/connection.py); commit 56e759351 on fix/aexit-reraise, merged as ff60a2a
- tests added (10): test_aexit_propagates_the_original_exception[json], test_aexit_propagates_the_original_exception[connection-closed], test_aexit_propagates_the_original_exception[protocol], test_aexit_propagates_the_original_exception[system-exit], test_aexit_propagates_the_original_exception[exception-group], test_aexit_propagates_the_original_exception[json], test_aexit_propagates_the_original_exception[connection-closed], test_aexit_propagates_the_original_exception[protocol], test_aexit_propagates_the_original_exception[system-exit], test_aexit_propagates_the_original_exception[exception-group]

### Q10 tab-call-args
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/tab.py:Tab.__call__:1966; members A7.1, A6.8, A12.1, B15.11
- patch: Pass text and selector to wait_for by keyword in Tab.__call__ (zendriver/core/tab.py); commit 9531d1c01 on fix/tab-call-args, merged as 7fa5cf9
- tests added (2): test_call_with_text_searches_by_text, test_call_with_selector_queries_css

### Q11 ready-state-order
- status: **fixed** (verify CCC; review approved in round 1)
- evidence: zendriver/core/tab.py:Tab.wait_for_ready_state (_poll):1343; members A6.1
- patch: Accept a later readyState in Tab.wait_for_ready_state (zendriver/core/tab.py); commit ecceb40af on fix/ready-state-order, merged as 9fb97eb
- tests added (5): test_wait_for_ready_state_accepts_later_state[interactive-complete], test_wait_for_ready_state_accepts_later_state[loading-interactive], test_wait_for_ready_state_accepts_later_state[loading-complete], test_wait_for_ready_state_default_on_complete_page, test_wait_for_ready_state_waits_for_earlier_state

### Q12 swallowed-cancellation
- status: **fixed** (verify PPP; members not confirmed 3/3: SEED-X3 0/3; review approved in round 1)
- evidence: (seeded lead); members SEED-X1, SEED-X2, SEED-X3
- patch: Let cancellation through domain enables and mouse_click's flash (zendriver/core/connection.py, zendriver/core/element.py); commit 0cb04efc1 on fix/swallowed-cancellation, merged as 56c4bb9
- tests added (3): test_send_timeout_during_domain_enable_is_not_swallowed, test_cancelled_domain_enable_is_sent_again, test_element_mouse_click_does_not_swallow_cancellation

### R13 hidden-click
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/element.py:click / get_position:432; members A8.3, B15.6, A8.4
- finding: Element.get_position raises instead of returning None (empty quads / no tree), so click() raises before its JS click on hidden (display:none) elements and the documented 'not visible' fallbacks in mouse_* are dead code

### R14 temp-profile-lifecycle
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/browser.py:Browser.__init__ (deepcopy) / Browser._cleanup_temporary_profile:927; members A3.6, A9.3, B16.5, A3.7, B16.6
- finding: Config.__repr__ (and Browser.__init__'s eager debug formatting) materialises the lazy temp user_data_dir on the template, so browsers started from one Config share a profile (the second fails and its stop() deletes the first one's live profile); failed starts leak temp profiles

### R15 config-args
- status: **report-only (below the fix cap)** (verify CPC; members not confirmed 3/3: SEED-K3 2/3)
- evidence: (seeded lead); members SEED-K1, SEED-K2, SEED-K3, SEED-K4, SEED-K5
- finding: Config argument assembly/validation (seeded leads): browser_args property differs from Config(); Config-owned flags in user args are not deduplicated; --load-extension appended again on every start; caller's browser_args list is aliased; add_argument rejects valid args by substring

### R16 connection-close-state
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/connection.py:Connection.wait:579; members SEED-C1, SEED-C2, SEED-C3, B14.5
- finding: Connection state after close (seeded leads + wait()): ConnectionClosed does not reset websocket so aopen never reconnects; aclose() during an in-progress connect is a no-op and the socket opens afterwards; a cancelled send() leaves its Transaction in mapper; Connection.wait() hangs forever on a listener that was cancelled/stopped while busy

### R17 get-new-tab-orphan
- status: **report-only (design/API change)** (verify CCC)
- evidence: zendriver/core/browser.py:Browser.get (get_handler / wait_for_navigation):422; members SEED-G1, A4.5
- finding: Browser.get wait semantics (Browser.get is owned by the get-timeout PR, so report-only): new_tab=True timing out after Target.createTarget leaves an orphaned tab (seeded lead); get() raises TimeoutError for navigations that never commit (204 No Content, downloads) while Tab.get returns normally

### R18 prep-flags-race
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/connection.py:Connection._prepare_expert:790; members B14.2, B14.6
- finding: _prepare_expert/_prepare_headless check-then-await their done flags: concurrent first sends inject the expert attachShadow override twice (shadow DOM recursion -> stack overflow); a session detached during prepare leaves _prep_headless_done set so the HeadlessChrome UA leaks after reattach

### R19 sync-callback-thread
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/connection.py:Listener.listener_loop (callback dispatch) / Connection.feed_cdp:1002; members A2.6, B14.4, A12.3
- finding: Sync event handlers run in a worker thread (asyncio.to_thread), so the documented feed_cdp() from a sync handler raises 'no current event loop' and the paused request is never continued; lambdas returning coroutines are never awaited

### R20 send-keys-newline
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/keys.py:KeyEvents.conv_to_str (via _get_key_and_text, CHAR path):167; members A10.4
- finding: Element.send_keys drops '\n'/'\r' from str text (sent as char '\n', which Chrome ignores), so multi-line text loses line breaks and 'query\n' does not submit

### R21 http-env-proxy
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/browser.py:HTTPApi._request:1133; members A4.2
- finding: HTTPApi sends the local DevTools /json/version request through http_proxy from the environment, so start() fails behind a proxy without no_proxy

### R22 session-attach-races
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/connection.py:Connection._detach_session (called from _receive_message):489; members A1.5, A1.6, B14.7
- finding: Session attach/detach ordering: a reply arriving in the same burst as Target.detachedFromTarget is discarded; cancelling the first command during attach leaks a Chrome-side session; a detachedFromTarget processed before _attach_session registers the session is dropped and later sends hang

### R23 restart-state
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/browser.py:Browser.start:531; members A3.2, B16.7, A12.4, A3.10, B16.13
- finding: Browser restart/state: start() stores the auto-chosen host/port in config, so start() after stop() or after a crash takes the connect-existing path and never launches Chrome; for host/port-connected browsers `stopped` is always True and a second start() leaks the first connection

### R24 remote-needs-local-chrome
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/config.py:Config.__init__ (via util.start / Browser.create / create_from_undetected_chromedriver):89; members A3.9, A9.2, B16.12
- finding: Connecting to an existing/remote browser (host+port) requires a local Chrome binary because Config.__init__ always runs find_executable

### R25 autodiscover-off
- status: **report-only (design/API change)** (verify CCC)
- evidence: zendriver/core/browser.py:Browser.get (wait_for_navigation) / Tab.close:431; members B13.6, A4.3, A12.5, A4.4
- finding: With Config.autodiscover_targets=False, Browser.get/Tab.get(new_tab) always raise TimeoutError and Tab.close waits 10 s then raises, because the awaited Target events are never emitted; update_targets never prunes destroyed targets

### R26 domain-lifecycle
- status: **report-only (design/API change)** (verify CCC)
- evidence: zendriver/core/connection.py:Connection.send / Connection._update_manual_domain / Connection._register_handlers:655; members A2.2, A12.2
- finding: Auto-enabled domains are never disabled when their handlers are removed (Fetch keeps pausing every request), and a manual X.disable is undone by a param-less X.enable on the next send

### R27 cdp-module-multiword
- status: **report-only (below the fix cap)** (verify CPC)
- evidence: zendriver/core/util.py:cdp_get_module:300; members A9.5
- finding: util.cdp_get_module cannot map multi-word CDP domains (WebAuthn, FedCm, ...), so a manual X.enable(params) is not tracked and zendriver re-sends X.enable() with default params

### R28 iframe-tree-recursion
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/util.py:filter_recurse:173; members A9.4, A5.4, A8.9, A5.5, A5.9, A6.3
- finding: util.filter_recurse/filter_recurse_all never descend into content_document, so elements inside same-origin iframes lose .parent, cannot update()/query/remove_from_dom, and text search returns raw #text nodes plus duplicates

### R29 dom-misc-crashes
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/tab.py:Tab.find_elements_by_text (iframe branch):765; members A6.2, A5.3, A5.8, B15.7, A8.8
- finding: DOM query crashes/error swallowing: filter_recurse_all yields raw cdp Nodes for shadow roots (AttributeError in find on iframe shadow DOM); Tab.query_selector crashes on cross-origin iframes (content_document None); element-scoped query_selector(_all) swallow every ProtocolException except 'could not find node'; element-scoped query results get the container Element as tree/node so .parent is None

### R30 expect-futures
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/expect.py:ResponseExpectation.value / RequestExpectation.value / BaseRequestExpectation.request, response, response_body; BaseFetchInterception.request, response_body, continue_request, fulfill_request, fail_request, continue_response:189; members A10.3, A10.7, B13.7, A10.8
- finding: expect.py futures: a timed-out wait on exp.value/request/response cancels the shared future (expectation dead); expect_request/expect_response never enable Network on enter (page-initiated requests hang until some unrelated send); Network.loadingFailed is ignored so response/response_body hang forever for failed requests

### R31 download-state
- status: **report-only (design/API change)** (verify CCC)
- evidence: zendriver/core/tab.py:Tab.set_download_path:1595; members A7.2, A7.3, A7.4, A10.6, B16.9
- finding: Download behaviour is browser-context-wide but tracked per Tab and sent without browser_context_id/events_enabled: download_file inside expect_download disables download events (ex.value hangs); context tabs ignore set_download_path; one tab's download_file/expect_download clobbers another tab's path

### R32 element-screenshot
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/element.py:Position.__init__ (used by screenshot_b64):1171; members A8.1, A8.2, A8.11
- finding: Element screenshots: Position uses fixed quad indices so mirrored/rotated elements give negative width and Page.captureScreenshot never answers (hang); scrolled pages capture the wrong region; save_screenshot(format='jpg') sends an invalid format

### R33 element-apply-input
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/element.py:apply:512; members A8.6, B15.8, A8.7, A8.5
- finding: Element.apply swallows JS exceptions (returns None/{}) and ignores return_by_value=False; clear_input/clear_input_by_deleting silently do nothing on <textarea> (regression from b506c8f)

### R34 element-attrs
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/element.py:get / _make_attrs:239; members A8.12, B16.14, A8.14, B16.16, A8.15, A8.16
- finding: Element attribute plumbing: get('class') returns None (stored as 'class_'); __setattr__ checks key[1:] so the tree setter never runs; copy/deepcopy/pickle recurse forever; highlight_overlay goes through the deprecated __getattr__

### R35 headless-ua-lazy
- status: **report-only (design/API change)** (verify CCC)
- evidence: zendriver/core/connection.py:Connection.send / Connection._prepare_headless:641; members A2.5
- finding: The headless UA override (and expert patch) is applied lazily on a Tab's first send, so Browser.get(new_tab=True)/create_context/popups load their first document with 'HeadlessChrome' in the UA

### R36 find-text-semantics
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/tab.py:Tab.find_elements_by_text:714; members A6.4, A6.10, A5.10, A6.11, A5.6
- finding: find_elements_by_text result semantics: duplicates when attribute and text both match; tag_hint ignored; return_enclosing_element ignored; iframe query errors print()ed and dropped by select_all(include_frames=True)

### R37 concurrent-dom-queries
- status: **report-only (design/API change)** (verify CCC)
- evidence: zendriver/core/tab.py:Tab.query_selector / Tab.query_selector_all (stale retry branches):645; members A5.2
- finding: Concurrent DOM queries on one tab silently return None/[]: each DOM.getDocument invalidates the other queries' node ids and the one-shot stale retry gives up quietly

### R38 keys-events
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/keys.py:KeyEvents.from_text / to_cdp_events (CHAR path for emoji/unknown graphemes):306; members A10.5, A10.9, A10.10, A10.11
- finding: keys.py event generation: emoji graphemes of 4+ UTF-16 units raise ProtocolException mid-typing; modifiers released before the main key's keyup; KeyEvents reuse mutates self.key; SpecialKeys.SPACE sends code ' ' instead of 'Space'

### R39 tab-misc
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/tab.py:Tab.get_all_urls:1635; members A7.5, A12.7, A7.6, A7.7, A7.8, A7.9, B16.18, A7.10, A7.12
- finding: Tab misc correctness: get_all_urls resolves against the origin and drops relative links; set_user_agent drops client-hint metadata; download_file injects url/filename into JS without escaping; save_snapshot writes CRLF MHTML in text mode; save_screenshot(format='webp') UnboundLocalError; auto-named screenshots collide within a second; print_to_pdf(ReturnAsStream) writes 0 bytes

### R40 window-state
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/tab.py:Tab.set_window_state:1201; members A6.6, A6.7
- finding: set_window_state: bounds ignored when the window is not normal; minimize/maximize/fullscreen first reset the window to 0,0 1280x720

### R41 browser-misc
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/browser.py:Browser.__iter__ / Browser.__next__ / Browser.__reversed__:853; members A4.1, A4.6, A4.7, A4.8, A12.6
- finding: Browser misc: iteration protocol crashes (no tabs / nested / shared cursor); grant_all_permissions always fails on current Chromium; tile_windows uses a third of the screen, ZeroDivisionError with no tabs and leaks mss; CookieJar.save/load match the pattern against str(cookie.__dict__)

### R42 connection-misc
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/connection.py:Connection._fail_pending_transactions / Connection.send:664; members A1.4, A2.9, B15.10, A1.3, A1.7, A1.8
- finding: Connection misc: one ProtocolException instance shared by all failed pending sends and mutated by each; NaN/Infinity params produce invalid JSON whose id-less error reply leaves send() hanging; remove_handlers(module, handler) is a no-op; ProtocolException drops the CDP error 'data'

### R43 cf-proxy-misc
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/cloudflare.py:verify_cf.check_input:239; members A11.2, A11.3, A11.7, A11.9
- finding: cloudflare/proxy misc: verify_cf raises when the solved challenge navigates away (the normal success path); forwarder leaks TLS-upstream tunnels after the client closes; non-ProxyError failures drop the client without a 502; handshake timeout reported as 'proxy closed the connection'

### R44 contradict-semantics
- status: **report-only (below the fix cap)** (verify CCP)
- evidence: zendriver/core/_contradict.py:ContraDict (no update/setdefault/__ior__ override):46; members A11.5, A11.6, A11.8
- finding: ContraDict semantics: update/setdefault/|= store plain dicts; copy.copy/pickle keep stale attributes after del; assigning an existing ContraDict/list stores a copy

### R45 util-config-misc
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: zendriver/core/util.py:circle:219; members A9.8, A9.9, A9.7, A9.11, B16.17
- finding: util/config misc: circle() treats y=0 as missing; html_from_tree duplicates every subtree; add_extension(dir) picks the last nested manifest.*; add_extension(.crx) leaks its extraction dir

### R46 element-design
- status: **report-only (design/API change)** (verify CCC)
- evidence: zendriver/core/element.py:save_to_dom / __repr__:276; members A8.10, A8.13, A8.17, A7.11, A10.2, A6.9, B16.10
- finding: Element/Tab design-level: save_to_dom serialises via an unescaped __repr__ (corrupts DOM); DOM.resolveNode remote objects never released; Element/Tab define __eq__ without __hash__ (unhashable); intercept() cannot be nested; evaluate returns None for unserializable values (NaN/Infinity/-0/BigInt); `async with await zd.start() as browser` never stops the browser

### R47 generator
- status: **report-only (below the fix cap)** (verify CCC)
- evidence: scripts/generate_cdp.py:main / dl_file:998; members A13.2, A13.1, A13.3, A13.4
- finding: scripts/generate_cdp.py: run from a non-root cwd it downloads the spec to cwd, deletes zendriver/cdp and fails; array alias types with $ref items are not converted (typed TargetFilter unusable); __repr__ override changes str() of int/float aliases; Optional any-typed None cannot express JSON null. The last three need regenerating zendriver/cdp (out of scope) so they are report-only.

