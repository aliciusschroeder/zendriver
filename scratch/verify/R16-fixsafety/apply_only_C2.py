import sys, pathlib
p = pathlib.Path(sys.argv[1])
s = p.read_text()

def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old)
    s = s.replace(old, new)

# SEED-C2: aclose must not race an aopen that is still connecting
sub('''            return
        if self.websocket is not None:
            for session in list(self._sessions.values()):
                session._detach_session()
            if self.listener and self.listener.running:
                self.listener.cancel()
                self.enabled_domains.clear()
                self.manually_enabled_domains.clear()
            await self.websocket.close()
            self.websocket = None
            self._fail_pending_transactions(ProtocolException("connection was closed"))
            logger.debug("\\n❌ closed websocket connection to %s", self.websocket_url)
''', '''            return
        # wait for an aopen that is still connecting, so its websocket is closed
        # here instead of being opened after this "close"
        async with self._open_lock:
            if self.websocket is None:
                return
            for session in list(self._sessions.values()):
                session._detach_session()
            if self.listener and self.listener.running:
                self.listener.cancel()
                self.enabled_domains.clear()
                self.manually_enabled_domains.clear()
            await self.websocket.close()
            self.websocket = None
            self._fail_pending_transactions(ProtocolException("connection was closed"))
            logger.debug("\\n❌ closed websocket connection to %s", self.websocket_url)
''')

p.write_text(s)
print('patched', p)
