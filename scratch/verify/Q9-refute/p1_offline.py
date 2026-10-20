import asyncio, json, sys, traceback
import websockets.exceptions
import zendriver
from zendriver.core.browser import Browser
from zendriver.core.config import Config
from zendriver.core.connection import Connection, ProtocolException

print("zendriver from", zendriver.__file__, "py", sys.version.split()[0])

async def tg_fail():
    async with asyncio.TaskGroup() as tg:
        async def boom():
            raise ValueError("inner")
        tg.create_task(boom())

def mk_cases():
    return {
        "json": lambda: json.loads("{bad"),
        "proto": lambda: (_ for _ in ()).throw(ProtocolException({"code": -32000, "message": "No node"})),
        "cc": lambda: (_ for _ in ()).throw(websockets.exceptions.ConnectionClosedError(None, None)),
        "unicode": lambda: b"\xff".decode("utf-8"),
        "keyerror": lambda: {}["k"],
        "value": lambda: (_ for _ in ()).throw(ValueError("plain")),
        "oserror": lambda: open("/nonexistent/x"),
    }

async def run_case(cm, name, fn):
    original = None
    try:
        async with cm:
            try:
                if name == "group":
                    await tg_fail()
                else:
                    fn()
            except BaseException as e:
                original = e
                raise
    except BaseException as caught:
        same = caught is original
        extra = ""
        if isinstance(caught, ProtocolException):
            extra = f" code={caught.code!r}"
        if isinstance(caught, KeyError):
            extra = f" args={caught.args!r}"
        if isinstance(caught, OSError):
            extra = f" errno={caught.errno!r} filename={caught.filename!r}"
        print(f"  {name:9s}: raised {type(original).__name__:22s} -> caught {type(caught).__name__}: {str(caught)[:70]!r} same_obj={same} context_is_orig={caught.__context__ is original}{extra}")
        return caught, original
    print(f"  {name}: nothing raised")

async def main():
    b = Browser(Config(headless=True))
    c = Connection("ws://127.0.0.1:1/devtools/browser/x")
    for label, cm in (("Browser", b), ("Connection", c)):
        print(f"[{label}]")
        for name, fn in list(mk_cases().items()) + [("group", None)]:
            await run_case(cm, name, fn)
    # cancellation still works through async with tab?
    async def body():
        async with c:
            await asyncio.sleep(10)
    t0 = asyncio.get_running_loop().time()
    try:
        async with asyncio.timeout(0.2):
            await body()
    except TimeoutError as e:
        print("[Connection] asyncio.timeout around async-with: TimeoutError OK after", round(asyncio.get_running_loop().time()-t0, 2))
    try:
        async with asyncio.timeout(0.2):
            async with b:
                await asyncio.sleep(10)
    except TimeoutError:
        print("[Browser] asyncio.timeout around async-with: TimeoutError OK")
    # print one full traceback to show chaining
    print("---- full traceback of json case through Browser ----")
    caught, orig = await run_case(b, "json", mk_cases()["json"])
    traceback.print_exception(caught, file=sys.stdout)

asyncio.run(asyncio.wait_for(main(), 60))
