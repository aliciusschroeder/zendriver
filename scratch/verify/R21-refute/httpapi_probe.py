"""Browser-free: HTTPApi vs a fake DevTools HTTP server, with env proxy set.
usage: httpapi_probe.py <proxy_mode: reject|forward|blackhole|none> <env_style: lower|upper|https_only> <no_proxy value or '-' for unset>
"""
import asyncio, json, os, sys, time
mode, style, np = sys.argv[1], sys.argv[2], sys.argv[3]
for k in list(os.environ):
    if k.lower().endswith("_proxy"):
        del os.environ[k]

import zendriver
from zendriver.core.browser import HTTPApi
print("zendriver from", zendriver.__file__)

proxy_log = []
devtools_hits = []

async def devtools(reader, writer):
    line = await reader.readline()
    devtools_hits.append(line)
    while (await reader.readline()) not in (b"\r\n", b""):
        pass
    body = json.dumps({"Browser": "Fake/1.0", "webSocketDebuggerUrl": "ws://127.0.0.1:1/devtools/browser/x"}).encode()
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % len(body) + body)
    await writer.drain(); writer.close()

async def proxy(reader, writer):
    line = await reader.readline()
    proxy_log.append(line)
    hdrs = []
    while (l := await reader.readline()) not in (b"\r\n", b""):
        hdrs.append(l)
    if mode == "reject":
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await writer.drain(); writer.close()
    elif mode == "blackhole":
        await asyncio.sleep(3600)
    elif mode == "forward":
        # like cntlm/px running on the same host: forwards absolute-form request
        _, url, ver = line.decode().split()
        import urllib.parse
        u = urllib.parse.urlsplit(url)
        r2, w2 = await asyncio.open_connection(u.hostname, u.port)
        w2.write(f"GET {u.path} HTTP/1.0\r\nHost: {u.netloc}\r\n\r\n".encode())
        await w2.drain()
        data = await r2.read()
        writer.write(data); await writer.drain(); writer.close()

async def main():
    dt = await asyncio.start_server(devtools, "127.0.0.1", 0)
    px = await asyncio.start_server(proxy, "127.0.0.1", 0)
    dport = dt.sockets[0].getsockname()[1]
    pport = px.sockets[0].getsockname()[1]
    purl = f"http://127.0.0.1:{pport}"  # stands in for a corporate proxy
    if style == "lower":
        os.environ["http_proxy"] = purl
    elif style == "upper":
        os.environ["HTTP_PROXY"] = purl
    elif style == "https_only":
        os.environ["https_proxy"] = purl
    if np != "-":
        os.environ["no_proxy"] = np
    api = HTTPApi(("127.0.0.1", dport))
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(api.get("version"), 30)
        res = f"OK {r.get('Browser')}"
    except Exception as e:
        res = f"FAIL {type(e).__name__}: {e}"
    print(f"mode={mode} env={style} no_proxy={np!r}: {res} after {time.monotonic()-t0:.1f}s; proxy saw={proxy_log}; devtools saw={devtools_hits}")
    dt.close(); px.close()

asyncio.run(main())
