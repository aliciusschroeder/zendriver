"""Drive BaseRequestExpectation handlers directly: two tasks scheduled before either runs
(what Listener.listener_loop does on 3.12+ for a buffered burst)."""
import asyncio, sys, collections
import zendriver
from zendriver import cdp
from zendriver.core.expect import RequestExpectation

class StubTab:
    def __init__(self): self.handlers = collections.defaultdict(list)
    def add_handler(self, t, h): self.handlers[t].append(h)
    def remove_handlers(self, t, h):
        if h in self.handlers[t]: self.handlers[t].remove(h)

def rwbs(rid, url):
    return cdp.network.RequestWillBeSent.from_json({"requestId": rid, "loaderId": "L", "documentURL": "u",
        "request": {"url": url, "method": "GET", "headers": {}, "initialPriority": "High", "referrerPolicy": "x"},
        "timestamp": 1, "wallTime": 1, "initiator": {"type": "other"}, "redirectHasExtraInfo": False})

async def main():
    print("python", sys.version.split()[0], zendriver.__file__)
    errs = []
    asyncio.get_running_loop().set_exception_handler(lambda l, c: errs.append(repr(c.get("exception"))))
    exp = RequestExpectation(StubTab(), r".*\.json")
    await exp._setup()
    t1 = asyncio.create_task(exp._request_handler(rwbs("R1", "http://x/a.json")))
    t2 = asyncio.create_task(exp._request_handler(rwbs("R2", "http://x/b.json")))
    await asyncio.wait([t1, t2])
    print("request_future ->", (await exp.request_future).request_id, " exp.request_id ->", exp.request_id)
    print("t2 exception:", repr(t2.exception()))
asyncio.run(main())
