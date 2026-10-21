| group | status | evidence (file:function:line) | patch / commit | tests |
|---|---|---|---|---|
| Q1 listener-robustness | fixed | connection.py:Transaction.__call__:126 | Keep the listener alive and fail commands instead of hanging them — 258db4c (merge 4495b70) | 8 |
| Q2 timeout-bounds | fixed | tab.py:Tab.select (also Tab.find, Tab.find_all, Tab.select_all):351 | Bound the polling methods by their timeout when CDP does not answer — c376813 (merge b5f083e) | 12 |
| Q3 stop-cleanup | fixed | browser.py:Browser._stop:879 | Make Browser.stop() always terminate the process and remove the profile — f783e58 (merge e4846f7) | 10 |
| Q4 start-cleanup | fixed | browser.py:Browser.start / Browser.create:572 | Stop the launched browser when Browser.start fails or is cancelled — f1e1848 (merge 4767cf3) | 3 |
| Q5 stderr-pipe | fixed | util.py:_start_process:352 | Drain the browser's stderr so a full pipe cannot stall Chrome — 5b41bf1 (merge f092fe8) | 5 |
| Q6 expect-pairing | fixed | expect.py:BaseRequestExpectation._request_handler:43 | Keep expect_request/expect_response on the first matching request — 03610e8 (merge 522a256) | 4 |
| Q7 register-handlers-snapshot | fixed | connection.py:Connection._register_handlers:720 | Skip already removed domains when pruning in _register_handlers — 40e8420 (merge d22627e) | 1 |
| Q8 contradict-shadowing | fixed | _contradict.py:ContraDict.__getattribute__:53 | Keep ContraDict keys from shadowing the dict methods — b5b3c31 (merge c852ec8) | 5 |
| Q9 aexit-reraise | fixed | connection.py:Connection.__aexit__:599 | Let exceptions propagate unchanged from Browser and Connection __aexit__ — 56e7593 (merge ff60a2a) | 10 |
| Q10 tab-call-args | fixed | tab.py:Tab.__call__:1966 | Pass text and selector to wait_for by keyword in Tab.__call__ — 9531d1c (merge 7fa5cf9) | 2 |
| Q11 ready-state-order | fixed | tab.py:Tab.wait_for_ready_state (_poll):1343 | Accept a later readyState in Tab.wait_for_ready_state — ecceb40 (merge 9fb97eb) | 5 |
| Q12 swallowed-cancellation | fixed | seeded: connection.py | Let cancellation through domain enables and mouse_click's flash — 0cb04ef (merge 56c4bb9) | 3 |
| R13 hidden-click | report-only | element.py:click / get_position:432 | — | — |
| R14 temp-profile-lifecycle | report-only | browser.py:Browser.__init__ (deepcopy) / Browser._cleanup_temporary_profile:927 | — | — |
| R15 config-args | report-only | seeded: config.py | — | — |
| R16 connection-close-state | report-only | connection.py:Connection.wait:579 | — | — |
| R17 get-new-tab-orphan | report-only (design) | browser.py:Browser.get (get_handler / wait_for_navigation):422 | — | — |
| R18 prep-flags-race | report-only | connection.py:Connection._prepare_expert:790 | — | — |
| R19 sync-callback-thread | report-only | connection.py:Listener.listener_loop (callback dispatch) / Connection.feed_cdp:1002 | — | — |
| R20 send-keys-newline | report-only | keys.py:KeyEvents.conv_to_str (via _get_key_and_text, CHAR path):167 | — | — |
| R21 http-env-proxy | report-only | browser.py:HTTPApi._request:1133 | — | — |
| R22 session-attach-races | report-only | connection.py:Connection._detach_session (called from _receive_message):489 | — | — |
| R23 restart-state | report-only | browser.py:Browser.start:531 | — | — |
| R24 remote-needs-local-chrome | report-only | config.py:Config.__init__ (via util.start / Browser.create / create_from_undetected_chromedriver):89 | — | — |
| R25 autodiscover-off | report-only (design) | browser.py:Browser.get (wait_for_navigation) / Tab.close:431 | — | — |
| R26 domain-lifecycle | report-only (design) | connection.py:Connection.send / Connection._update_manual_domain / Connection._register_handlers:655 | — | — |
| R27 cdp-module-multiword | report-only | util.py:cdp_get_module:300 | — | — |
| R28 iframe-tree-recursion | report-only | util.py:filter_recurse:173 | — | — |
| R29 dom-misc-crashes | report-only | tab.py:Tab.find_elements_by_text (iframe branch):765 | — | — |
| R30 expect-futures | report-only | expect.py:ResponseExpectation.value / RequestExpectation.value / BaseRequestExpectation.request, response, response_body; BaseFetchInterception.request, response_body, continue_request, fulfill_request, fail_request, continue_response:189 | — | — |
| R31 download-state | report-only (design) | tab.py:Tab.set_download_path:1595 | — | — |
| R32 element-screenshot | report-only | element.py:Position.__init__ (used by screenshot_b64):1171 | — | — |
| R33 element-apply-input | report-only | element.py:apply:512 | — | — |
| R34 element-attrs | report-only | element.py:get / _make_attrs:239 | — | — |
| R35 headless-ua-lazy | report-only (design) | connection.py:Connection.send / Connection._prepare_headless:641 | — | — |
| R36 find-text-semantics | report-only | tab.py:Tab.find_elements_by_text:714 | — | — |
| R37 concurrent-dom-queries | report-only (design) | tab.py:Tab.query_selector / Tab.query_selector_all (stale retry branches):645 | — | — |
| R38 keys-events | report-only | keys.py:KeyEvents.from_text / to_cdp_events (CHAR path for emoji/unknown graphemes):306 | — | — |
| R39 tab-misc | report-only | tab.py:Tab.get_all_urls:1635 | — | — |
| R40 window-state | report-only | tab.py:Tab.set_window_state:1201 | — | — |
| R41 browser-misc | report-only | browser.py:Browser.__iter__ / Browser.__next__ / Browser.__reversed__:853 | — | — |
| R42 connection-misc | report-only | connection.py:Connection._fail_pending_transactions / Connection.send:664 | — | — |
| R43 cf-proxy-misc | report-only | cloudflare.py:verify_cf.check_input:239 | — | — |
| R44 contradict-semantics | report-only | _contradict.py:ContraDict (no update/setdefault/__ior__ override):46 | — | — |
| R45 util-config-misc | report-only | util.py:circle:219 | — | — |
| R46 element-design | report-only (design) | element.py:save_to_dom / __repr__:276 | — | — |
| R47 generator | report-only | scripts/generate_cdp.py:main / dl_file:998 | — | — |
| U1 followup-connection | fixed | final-review follow-up: connection (send/rollback/session failure) | Keep Connection.send and domain enables consistent when a command never leaves — e7d5a85 (merge 822610d) | 7 |
| U2 followup-timeouts | fixed | final-review follow-up: cancellation-safe timeout bounds | Keep a cancellation that arrives with a polling attempt's answer — 530989e (merge 4d988bc) | 3 |
| U3 followup-stop | fixed | final-review follow-up: concurrent stop with proxies + test sync | Let concurrent Browser.stop() calls close a proxy forwarder once — 02868a8 (merge 24b0c4a) | 2 |
