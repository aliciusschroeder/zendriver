import asyncio, sys, os, re, pkgutil, importlib, inspect
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from zendriver.core import util
from zendriver.core.connection import Connection
from fakepeer import FakePeer
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

# 1. enumerate domains whose Domain.lower() does not resolve to their own module
bad = []
for mi in pkgutil.iter_modules(cdp.__path__):
    if mi.name in ("util",):
        continue
    mod = importlib.import_module(f"zendriver.cdp.{mi.name}")
    src = inspect.getsource(mod)
    m = re.search(r'"method": "([A-Za-z]+)\.', src)
    if not m:
        continue
    dom = m.group(1)
    try:
        got = util.cdp_get_module(dom.lower())
        ok = got is mod
    except ModuleNotFoundError:
        got = None; ok = False
    if not ok:
        has_enable = hasattr(mod, "enable")
        sig = str(inspect.signature(mod.enable)) if has_enable else "-"
        bad.append((dom, mi.name, getattr(got, "__name__", None), sig))
print("domains whose Domain.lower() does not map to their module:")
for b in bad:
    print("   ", b)

async def run(enable_cmd, handler_event, label):
    async with FakePeer() as peer:
        conn = Connection(peer.url)
        try:
            await conn.send(enable_cmd)
            print(f"[{label}] after manual enable: manual={[m.__name__ for m in conn.manually_enabled_domains]} enabled={[m.__name__ for m in conn.enabled_domains]}")
            conn.add_handler(handler_event, lambda ev: None)
            peer.received.clear()
            await conn.send(cdp.runtime.run_if_waiting_for_debugger())
            print(f"[{label}] frames sent for the next unrelated send: {peer.received}")
        finally:
            await conn.aclose()

async def main():
    await run(cdp.web_authn.enable(enable_ui=True), cdp.web_authn.CredentialAdded, "WebAuthn")
    await run(cdp.fed_cm.enable(disable_rejection_delay=True), cdp.fed_cm.DialogShown, "FedCm")
    await run(cdp.network.enable(max_post_data_size=123), cdp.network.RequestWillBeSent, "Network control")

asyncio.run(asyncio.wait_for(main(), 30))
