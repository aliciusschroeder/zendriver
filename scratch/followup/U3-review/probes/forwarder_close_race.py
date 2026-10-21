"""ProxyForwarder.close() run concurrently, with live CONNECT tunnels through an
upstream that holds them open; also a first close() cut off by a timeout, then a
second close(). reports results, leftover tasks and loop errors."""
import sys

sys.path.insert(0, "/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-6")
import asyncio, gc

from zendriver.core.proxy import ProxyForwarder, UpstreamProxy

errors = []


async def upstream_handler(reader, writer):
    await reader.readuntil(b"\r\n\r\n")
    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await writer.drain()
    try:
        while await reader.read(65536):
            pass
        await asyncio.sleep(3600)
    except BaseException:
        pass


async def scenario(mode):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(lambda l, c: errors.append(c["message"]))
    up = await asyncio.start_server(upstream_handler, "127.0.0.1", 0)
    upport = up.sockets[0].getsockname()[1]
    fw = ProxyForwarder(UpstreamProxy("http", "127.0.0.1", upport, "u", "p"))
    await fw.start()
    port = int(fw.proxy_server.rsplit(":", 1)[1])
    clients = []
    for _ in range(3):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        w.write(b"CONNECT example.test:443 HTTP/1.1\r\nHost: example.test:443\r\n\r\n")
        await r.readuntil(b"\r\n\r\n")
        clients.append((r, w))
    n = len(fw._client_tasks)
    if mode == "gather":
        res = await asyncio.wait_for(
            asyncio.gather(fw.close(), fw.close(), fw.close(), return_exceptions=True), 10
        )
    else:
        # first close() cut off right away, as by stop()'s bound, then a retry
        try:
            await asyncio.wait_for(fw.close(), 0.001)
            first = "done"
        except asyncio.TimeoutError:
            first = "timeout"
        res = [first, await asyncio.wait_for(fw.close(), 10)]
    eofs = [await asyncio.wait_for(r.read(), 10) for r, _ in clients]
    for _, w in clients:
        w.close()
    up.close()
    await asyncio.sleep(0.1)
    left = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    print(
        f"{mode}: clients={n} results={[repr(x) for x in res]} eofs={eofs} "
        f"client_tasks_left={len(fw._client_tasks)} other_tasks={len(left)}"
    )
    for t in left:
        t.cancel()
    await asyncio.gather(*left, return_exceptions=True)


print(sys.version.split()[0])
for mode in ("gather", "timeout_then_retry"):
    asyncio.run(scenario(mode))
gc.collect()
print("loop errors:", errors)
