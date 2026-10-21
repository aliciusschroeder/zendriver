"""does asyncio.Server.wait_closed() wait for a client which stopped reading, and
does it return once that client process is killed?"""

import asyncio
import subprocess
import sys
import time


async def main() -> None:
    writers = []

    async def handle(reader, writer):  # type: ignore[no-untyped-def]
        writers.append(writer)
        writer.write(b"x" * 50_000_000)  # far more than the socket buffers hold
        try:
            await reader.read()
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    client = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import socket, time; "
            f"s = socket.create_connection(('127.0.0.1', {port})); "
            "print('ready', flush=True); time.sleep(60)",
        ],
        stdout=subprocess.PIPE,
    )
    assert client.stdout is not None
    assert client.stdout.readline().strip() == b"ready"
    await asyncio.sleep(0.3)
    server.close()
    for w in writers:
        w.close()
    v = sys.version.split()[0]
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(server.wait_closed(), 2)
        print(v, "wait_closed returned while the client is alive", round(time.monotonic() - t0, 2))
    except asyncio.TimeoutError:
        print(v, "wait_closed still waits after 2 s while the client is alive")
        client.kill()
        client.wait()
        t0 = time.monotonic()
        await asyncio.wait_for(server.wait_closed(), 5)
        print(v, "after killing the client wait_closed returned in", round(time.monotonic() - t0, 2))
    if client.poll() is None:
        client.kill()
        client.wait()


asyncio.run(main())
