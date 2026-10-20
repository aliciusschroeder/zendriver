"""
Q12 / SEED-X3: does `except BaseException as e` in UpstreamProxy.open_tunnel swallow CancelledError?
Loads proxy.py straight from the file so it runs on any python without zendriver's deps.
usage: python x3_proxy.py /path/to/zendriver/core/proxy.py
"""
import asyncio
import importlib.util
import sys
import time

spec = importlib.util.spec_from_file_location("zd_proxy", sys.argv[1])
proxy = importlib.util.module_from_spec(spec)
sys.modules["zd_proxy"] = proxy
spec.loader.exec_module(proxy)
print("python", sys.version.split()[0], "proxy module from", proxy.__file__)

EVENTS = []


async def silent_upstream(reader, writer):
    """accepts, reads, never answers; records when the client closes"""
    t0 = time.monotonic()
    try:
        while await reader.read(1024):
            pass
        EVENTS.append(f"upstream saw EOF from client after {time.monotonic() - t0:.2f}s")
    except Exception as e:
        EVENTS.append(f"upstream read error {e!r}")
    finally:
        writer.close()


def chain(task):
    out = []
    c = task.get_coro()
    while c is not None:
        f = getattr(c, "cr_frame", None) or getattr(c, "gi_frame", None)
        if f is None:
            break
        out.append(f"{f.f_code.co_filename.rsplit('/', 1)[-1]}:{f.f_lineno} in {f.f_code.co_name}")
        c = getattr(c, "cr_await", None) or getattr(c, "gi_yieldfrom", None)
    return out


async def run(label, coro_factory, how, after=0.5):
    EVENTS.clear()
    t0 = time.monotonic()
    task = asyncio.create_task(coro_factory())
    await asyncio.sleep(after)
    where = chain(task)
    if how == "cancel":
        task.cancel()
    done, _ = await asyncio.wait({task}, timeout=5)
    await asyncio.sleep(0.2)
    el = time.monotonic() - t0
    if not done:
        res = "STILL RUNNING (cancel swallowed)"
        task.cancel()
    elif task.cancelled():
        res = "cancelled (CancelledError propagated)"
    elif task.exception() is not None:
        res = f"raised {task.exception()!r}"
    else:
        res = f"returned {task.result()!r}"
    print(f"=== {label}\n  suspended at: {where[-3:]}\n  {el:.2f}s: {res}\n  {EVENTS}")


async def main():
    server = await asyncio.start_server(silent_upstream, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        for scheme in ("http", "socks5"):
            up = proxy.UpstreamProxy(scheme, "127.0.0.1", port, "u", "p")
            await run(f"{scheme}: task.cancel() during handshake", lambda: up.open_tunnel("example.com", 443), "cancel")
            await run(f"{scheme}: outer wait_for(0.5) during handshake",
                      lambda: asyncio.wait_for(up.open_tunnel("example.com", 443), 0.5), "wait", after=0.0)

        # through the forwarder: a CONNECT is in open_tunnel when the forwarder is closed
        up = proxy.UpstreamProxy("http", "127.0.0.1", port, "u", "p")
        fwd = proxy.ProxyForwarder(up)
        await fwd.start()
        host, fport = fwd._server.sockets[0].getsockname()[:2]
        r, w = await asyncio.open_connection(host, fport)
        w.write(b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n")
        await w.drain()
        await asyncio.sleep(0.5)
        tasks = list(fwd._client_tasks)
        print("=== forwarder.close() while a client task is in open_tunnel")
        print("  client task at:", chain(tasks[0])[-3:] if tasks else None)
        t0 = time.monotonic()
        await asyncio.wait_for(fwd.close(), 5)
        print(f"  close() returned after {time.monotonic() - t0:.2f}s; client task cancelled={tasks[0].cancelled()}")
        await asyncio.sleep(0.2)
        print(" ", EVENTS)
        w.close()

        # incidental: the inner TIMEOUT path (not a cancellation issue)
        proxy.TIMEOUT = 0.3
        up = proxy.UpstreamProxy("http", "127.0.0.1", port, "u", "p")
        await run("inner TIMEOUT=0.3 expires (incidental message check)", lambda: up.open_tunnel("example.com", 443), "wait")
    finally:
        server.close()


asyncio.run(asyncio.wait_for(main(), 60))
