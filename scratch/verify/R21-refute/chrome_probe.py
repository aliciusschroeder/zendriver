"""Real headless Chromium + env proxy.
usage: chrome_probe.py <reject|forward|blackhole> <lower|upper|https_only> <no_proxy or -> <max_tries>
"""
import asyncio, os, sys, time, json, urllib.parse
mode, style, np, tries = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
for k in list(os.environ):
    if k.lower().endswith("_proxy"):
        del os.environ[k]
import zendriver
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
log = []

async def direct_get(url):
    # what a real forwarding proxy (squid/cntlm/px) sends upstream: origin-form, HTTP/1.1
    u = urllib.parse.urlsplit(url)
    r, w = await asyncio.open_connection(u.hostname, u.port)
    w.write(f"GET {u.path} HTTP/1.1\r\nHost: {u.netloc}\r\nConnection: close\r\n\r\n".encode()); await w.drain()
    head = await r.readuntil(b"\r\n\r\n")
    n = 0
    for l in head.split(b"\r\n"):
        if l.lower().startswith(b"content-length:"):
            n = int(l.split(b":", 1)[1])
    body = await r.readexactly(n)
    w.close()
    return head + body

async def proxy(reader, writer):
    line = await reader.readline()
    while (l := await reader.readline()) not in (b"\r\n", b""):
        pass
    _, url, _ = line.decode().split()
    entry = {"req": line.decode().strip()}
    log.append(entry)
    if mode == "reject":
        if not url.startswith("http://127.0.0.1"):
            writer.close(); return
        try:
            data = await direct_get(url)
            entry["direct_status"] = data.split(b"\r\n", 1)[0].decode()
            entry["direct_has_ws_url"] = b"webSocketDebuggerUrl" in data
        except Exception as e:
            entry["direct_status"] = repr(e)
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await writer.drain(); writer.close()
    elif mode == "forward":
        try:
            data = await direct_get(url)
        except Exception as e:
            entry["fwd_err"] = repr(e)
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        else:
            entry["fwd_status"] = data.split(b"\r\n", 1)[0].decode()
            writer.write(data)
        await writer.drain(); writer.close()
    elif mode == "blackhole":
        await asyncio.sleep(3600)

async def main():
    px = await asyncio.start_server(proxy, "127.0.0.1", 0)
    purl = "http://127.0.0.1:%d" % px.sockets[0].getsockname()[1]
    if style == "lower": os.environ["http_proxy"] = purl
    elif style == "upper": os.environ["HTTP_PROXY"] = purl
    elif style == "https_only": os.environ["https_proxy"] = purl
    if np != "-": os.environ["no_proxy"] = np
    t0 = time.monotonic()
    browser = None
    try:
        browser = await asyncio.wait_for(zendriver.start(headless=True, browser_connection_max_tries=tries), 100)
        tab = await asyncio.wait_for(browser.get("data:text/html,<title>hi</title>"), 30)
        title = await tab.evaluate("document.title")
        res = f"OK started, page title={title!r}, ws={browser.info.webSocketDebuggerUrl[:40]}"
    except Exception as e:
        msg = " ".join(str(e).split())
        res = f"FAIL {type(e).__name__}: {msg[:120]}"
    finally:
        if browser is not None:
            await browser.stop()
    print(f"mode={mode} env={style} no_proxy={np!r} tries={tries}: {res} after {time.monotonic()-t0:.1f}s")
    print("  proxy log:", json.dumps(log)[:600], f"({len(log)} requests)")
    px.close()

asyncio.run(main())
