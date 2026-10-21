import asyncio, sys, traceback, collections
sys.path.insert(0, sys.argv[1])
import probe_safety_lib as ps
from zendriver.core import connection as zc

created = []
orig_run = zc.Listener.run
def run(self):
    orig_run(self)
    stack = "".join(traceback.format_stack(limit=8)[:-1])
    def done(task, stack=stack):
        if not task.cancelled() and task.exception() is not None:
            created.append((type(task.exception()).__name__, stack))
    self.task.add_done_callback(done)
zc.Listener.run = run

async def main(n):
    for _ in range(n):
        await asyncio.wait_for(getattr(ps, sys.argv[3])(), 40)

import contextlib, io
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    asyncio.run(main(int(sys.argv[2])))
print("listener tasks that died with an exception:", collections.Counter(c[0] for c in created))
if created:
    print("creation stack of the first one:\n", created[0][1])
