import sys, pathlib
p = pathlib.Path(sys.argv[1])
s = p.read_text()

def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old)
    s = s.replace(old, new)

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
print('patched', p)
