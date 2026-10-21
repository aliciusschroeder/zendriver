import sys, pathlib
p = pathlib.Path(sys.argv[1])
s = p.read_text()
old = '''        if self._session_parent is not None:
            browser_connection = self._session_parent
            session_id = self.session_id
            self._detach_session()
            if session_id is not None and not browser_connection.closed:
                try:
                    await browser_connection.send(
                        cdp.target.detach_from_target(
                            session_id=cdp.target.SessionID(session_id)
                        ),
                        _is_update=True,
                    )
                except ProtocolException:
                    logger.debug("could not detach session %s", session_id)
            logger.debug("\\n❌ detached from target %s", self.target_id)
            return
'''
new = '''        # wait for an attach that is still in progress, so its session is detached
        # here instead of being attached after this "close"
        async with self._attach_lock:
            if self._session_parent is not None:
                browser_connection = self._session_parent
                session_id = self.session_id
                self._detach_session()
                if session_id is not None and not browser_connection.closed:
                    try:
                        await browser_connection.send(
                            cdp.target.detach_from_target(
                                session_id=cdp.target.SessionID(session_id)
                            ),
                            _is_update=True,
                        )
                    except ProtocolException:
                        logger.debug("could not detach session %s", session_id)
                logger.debug("\\n❌ detached from target %s", self.target_id)
                return
'''
assert s.count(old) == 1
s = s.replace(old, new)
p.write_text(s)
print("patched", p)
