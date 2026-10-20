"""Browser-free reproducer for Q9: __aexit__ re-raising exc_type(exc_val).

Uses an in-process fake CDP peer (websockets server) for Connection, and an
unstarted zendriver.Browser instance for Browser.__aexit__.
"""

import asyncio
import json
import sys
import traceback

import websockets
import websockets.asyncio.server
import websockets.exceptions

import zendriver
from zendriver import cdp
from zendriver.core.connection import Connection, ProtocolException

print("zendriver from:", zendriver.__file__, "python", sys.version.split()[0])


async def handler(ws):
    async for raw in ws:
        msg = json.loads(raw)
        if msg["method"] == "DOM.resolveNode":
            await ws.send(
                json.dumps(
                    {
                        "id": msg["id"],
                        "error": {
                            "code": -32000,
                            "message": "No node with given id found",
                        },
                    }
                )
            )
        else:
            await ws.send(json.dumps({"id": msg["id"], "result": {}}))


def make_exceptions():
    out = {}
    try:
        json.loads("{bad")
    except json.JSONDecodeError as e:
        out["JSONDecodeError"] = e
    try:
        b"\xff".decode("utf-8")
    except UnicodeDecodeError as e:
        out["UnicodeDecodeError"] = e
    out["ConnectionClosedError"] = websockets.exceptions.ConnectionClosedError(
        None, None
    )
    out["ExceptionGroup"] = ExceptionGroup("grp", [ValueError("v")])
    out["KeyError"] = KeyError("k")
    out["ProtocolException(dict)"] = ProtocolException(
        {"code": -32000, "message": "m"}
    )
    return out


async def body_raise(exc):
    raise exc


async def taskgroup_fail():
    async def boom():
        raise ValueError("inner")

    async with asyncio.TaskGroup() as tg:
        tg.create_task(boom())


def describe(caught, original):
    same = caught is original
    extra = ""
    if isinstance(caught, ProtocolException):
        extra = f" code={caught.code!r} message={caught.message!r}"
    if isinstance(caught, KeyError):
        extra = f" args={caught.args!r}"
    return f"caught {type(caught).__name__}: {caught!s:.90} | same_obj={same}{extra}"


async def run_ctx(label, ctx_factory, exc_factory):
    for name, exc in exc_factory().items():
        ctx = await ctx_factory()
        try:
            async with ctx:
                await body_raise(exc)
        except BaseException as caught:  # noqa
            print(f"[{label}] raised {name:24s} -> {describe(caught, exc)}")
    # TaskGroup failure in body
    ctx = await ctx_factory()
    try:
        async with ctx:
            await taskgroup_fail()
    except* ValueError as eg:
        print(f"[{label}] TaskGroup failure -> except* ValueError matched: {eg!r}")
    except* BaseException as eg:
        print(
            f"[{label}] TaskGroup failure -> except* ValueError MISSED; got {[type(e).__name__ + ': ' + str(e) for e in eg.exceptions]}"
        )


async def main():
    async with websockets.asyncio.server.serve(handler, "127.0.0.1", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/devtools/page/X"

        async def conn_factory():
            return Connection(url)

        # Real ProtocolException from a failing command inside `async with conn:`
        conn = Connection(url)
        orig = None
        try:
            async with conn:
                try:
                    await conn.send(cdp.dom.resolve_node(node_id=cdp.dom.NodeId(999999)))
                except ProtocolException as e:
                    orig = e
                    print(f"[Connection] inside block: code={e.code!r} message={e.message!r}")
                    raise
        except ProtocolException as caught:
            print(f"[Connection] real failing send -> {describe(caught, orig)}")
            tb = traceback.extract_tb(caught.__traceback__)
            print("[Connection]   caught.__traceback__ frames:", [f.name for f in tb])
            print("[Connection]   caught.__context__ is orig:", caught.__context__ is orig)

        await run_ctx("Connection", conn_factory, make_exceptions)

        async def browser_factory():
            return zendriver.Browser(zendriver.Config(headless=True))

        await run_ctx("Browser", browser_factory, make_exceptions)

        # control: what a well-behaved context manager gives
        class Good:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return None

        async def good_factory():
            return Good()

        await run_ctx("control", good_factory, make_exceptions)


asyncio.run(asyncio.wait_for(main(), 60))
