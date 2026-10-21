import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import zendriver as zd
from zendriver import cdp
from common import start_server
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

async def main():
    srv, base = start_server()
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get(base + "/a")
        log = []
        orig = tab._send_transaction
        async def wrapped(tx):
            log.append((tx.method, tx.params)); return await orig(tx)
        tab._send_transaction = wrapped
        await tab.send(cdp.web_authn.enable(enable_ui=True))
        print("manual:", [m.__name__ for m in tab.manually_enabled_domains], "enabled:", [m.__name__ for m in tab.enabled_domains])
        opts = cdp.web_authn.VirtualAuthenticatorOptions(protocol=cdp.web_authn.AuthenticatorProtocol.CTAP2, transport=cdp.web_authn.AuthenticatorTransport.INTERNAL, has_resident_key=True, has_user_verification=True, is_user_verified=True)
        aid = await tab.send(cdp.web_authn.add_virtual_authenticator(opts))
        print("authenticator", aid)
        tab.add_handler(cdp.web_authn.CredentialAdded, lambda ev: print("credential added", ev))
        log.clear()
        try:
            creds = await asyncio.wait_for(tab.send(cdp.web_authn.get_credentials(aid)), 10)
            print("get_credentials ok:", creds)
        except Exception as e:
            print("get_credentials raised", type(e).__name__, str(e)[:200])
        print("frames:", log)
        tab._send_transaction = orig
    finally:
        await browser.stop()
        srv.shutdown()
asyncio.run(asyncio.wait_for(main(), 60))
