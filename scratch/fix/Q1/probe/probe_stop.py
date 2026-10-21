import asyncio
import logging
import sys
import traceback

import zendriver as zd
from zendriver.core import connection as conn_mod

print("zendriver from", zd.__file__, sys.version.split()[0])
by_task: dict = {}
orig_init = conn_mod.Listener.__init__


def init(self, connection):
    self._created = "".join(traceback.format_stack(limit=14)[:-1])
    self._conn_desc = f"{connection.websocket_url} session={connection.session_id}"
    orig_init(self, connection)
    by_task[self.task] = self


conn_mod.Listener.__init__ = init

orig_loop = conn_mod.Listener.listener_loop


async def loop(self):
    try:
        await orig_loop(self)
    except BaseException as e:
        print("LISTENER DIED", type(e).__name__, e, self._conn_desc)
        if "-v" in sys.argv:
            print("created at:\n", self._created)
        raise


conn_mod.Listener.listener_loop = loop


class H(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            print("WARNING LOGGED:", record.getMessage())
            lst = by_task.get(asyncio.current_task())
            if lst is not None:
                c = lst.connection
                print("  listener conn:", lst._conn_desc, "| now ws:", c.websocket, "inbox:", c._inbox, "session:", c.session_id)
                print("  created at:\n" + lst._created)


logging.getLogger("uc.connection").addHandler(H())


async def main(url: str) -> None:
    browser = await zd.start(headless=True, sandbox=False)
    page = await browser.get(url)
    el = await page.select("body")
    print("children", len(el.children))
    await browser.stop()
    await asyncio.sleep(0.5)


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "about:blank"))
