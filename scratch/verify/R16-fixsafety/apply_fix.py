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

# SEED-C3: a cancelled (or failed) send must not leave its transaction behind
sub('''        await self._send_transaction(tx)
        try:
            return await tx
        except ProtocolException as e:
            e.message = e.message or ""
            e.message += f"\\ncommand:{tx.method}\\nparams:{tx.params}"
            raise e
''', '''        await self._send_transaction(tx)
        try:
            return await tx
        except ProtocolException as e:
            e.message = e.message or ""
            e.message += f"\\ncommand:{tx.method}\\nparams:{tx.params}"
            raise e
        finally:
            # the listener pops answered transactions; one whose caller was
            # cancelled (e.g. by asyncio.wait_for) must not stay behind
            self.mapper.pop(tx.id, None)
''')

# B14.5: a listener that stops (cancelled, or the websocket closed) reports idle,
# so Connection.wait() does not wait forever on it
sub('''    def run(self) -> None:
        self.task = asyncio.create_task(self.listener_loop())
''', '''    def run(self) -> None:
        self.task = asyncio.create_task(self.listener_loop())
        # a stopped listener receives nothing anymore, so it is idle. without this,
        # Connection.wait() would wait forever on a listener that was cancelled
        # (session detached) or whose websocket closed while it was busy
        self.task.add_done_callback(lambda _: self.idle.set())
''')

# SEED-C1: forget a websocket the peer closed, like aclose() does
sub('''                for session in list(self.connection._sessions.values()):
                    session._detach_session()
                self.connection._fail_pending_transactions(e)
                break
''', '''                for session in list(self.connection._sessions.values()):
                    session._detach_session()
                # forget the dead websocket, so that `closed` is true and the
                # next aopen() reconnects instead of reusing it
                self.connection.websocket = None
                self.connection.enabled_domains.clear()
                self.connection.manually_enabled_domains.clear()
                self.connection._fail_pending_transactions(e)
                break
''')
p.write_text(s)
print("patched", p)
