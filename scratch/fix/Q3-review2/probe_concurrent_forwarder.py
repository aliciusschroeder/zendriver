"""
two simultaneous stop() calls with a proxy forwarder which has a live client connection.
no browser: a python process stands in for it.
"""

import asyncio
import shutil
import subprocess
import sys

import zendriver as zd
from zendriver.core.proxy import ProxyForwarder, UpstreamProxy


async def once() -> list:
    browser = zd.Browser(zd.Config(browser_executable_path=sys.executable))
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(60)"],
        stdout=subprocess.PIPE,
    )
    assert process.stdout is not None
    process.stdout.readline()
    browser._process, browser._process_pid = process, process.pid
    forwarder = ProxyForwarder(UpstreamProxy("http", "127.0.0.1", 1, "user", "pass"))
    await forwarder.start()
    browser._proxy_forwarders.append(forwarder)
    host, port = forwarder._server.sockets[0].getsockname()[:2]
    # a client which keeps its connection open, as chrome's network service could
    reader, writer = await asyncio.open_connection(host, port)
    await asyncio.sleep(0.05)
    print("client tasks", len(forwarder._client_tasks))
    try:
        results = await asyncio.wait_for(
            asyncio.gather(browser.stop(), browser.stop(), return_exceptions=True), 30
        )
    finally:
        writer.close()
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        shutil.rmtree(browser.config.user_data_dir, ignore_errors=True)
    return [repr(r) for r in results]


async def main() -> None:
    print(sys.version.split()[0], zd.__file__)
    for _ in range(3):
        print(await once())


asyncio.run(main())
