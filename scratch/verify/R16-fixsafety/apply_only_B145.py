import sys, pathlib
p = pathlib.Path(sys.argv[1])
s = p.read_text()

def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old)
    s = s.replace(old, new)

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

p.write_text(s)
print('patched', p)
