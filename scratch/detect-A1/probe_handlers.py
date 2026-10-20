"""Probe C: remove_handlers(module, handler) does not undo add_handler(module, handler)."""
import asyncio

import zendriver as zd
from zendriver.core.connection import Connection


async def main() -> None:
    conn = Connection("ws://127.0.0.1:1/devtools/browser/x")

    def h(ev):
        pass

    conn.add_handler(zd.cdp.network, h)
    n = sum(1 for v in conn.handlers.values() if h in v)
    print("event types with h after add_handler(cdp.network, h):", n)
    conn.remove_handlers(zd.cdp.network, h)
    n = sum(1 for v in conn.handlers.values() if h in v)
    print("event types with h after remove_handlers(cdp.network, h):", n)
    conn.remove_handlers(zd.cdp.network)
    n = sum(1 for v in conn.handlers.values() if h in v)
    print("event types with h after remove_handlers(cdp.network):", n)
    print("bogus key created:", zd.cdp.network in conn.handlers)


asyncio.run(main())
