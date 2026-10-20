import asyncio, sys, logging
import zendriver as zd
from zendriver import cdp

async def main(with_handler):
    browser = await zd.start(headless=True)
    tab = browser.main_tab
    await tab.get("data:text/html,<p>x</p>")
    sent = []
    orig = tab.connection.websocket.send if hasattr(tab, "connection") else None
    # record outgoing methods
    ws_send = tab.websocket.send
    async def rec(msg, *a, **k):
        import json
        sent.append(json.loads(msg)["method"])
        return await ws_send(msg, *a, **k)
    tab.websocket.send = rec
    await tab.send(cdp.network.enable())
    await tab.send(cdp.web_authn.enable(enable_ui=False))
    print("manually_enabled_domains:", [m.__name__.rsplit('.',1)[-1] for m in tab.manually_enabled_domains])
    opts = cdp.web_authn.VirtualAuthenticatorOptions(protocol=cdp.web_authn.AuthenticatorProtocol.CTAP2, transport=cdp.web_authn.AuthenticatorTransport.USB)
    auth_id = await tab.send(cdp.web_authn.add_virtual_authenticator(opts))
    print("authenticator", auth_id)
    if with_handler:
        tab.add_handler(cdp.web_authn.CredentialAdded, lambda e: None)
        tab.add_handler(cdp.network.RequestWillBeSent, lambda e: None)
    sent.clear()
    try:
        creds = await asyncio.wait_for(tab.send(cdp.web_authn.get_credentials(auth_id)), 10)
        print("get_credentials ok:", creds)
    except Exception as e:
        print("get_credentials failed:", type(e).__name__, " ".join(str(e).split())[:150])
    print("methods sent for that one call:", sent)
    await browser.stop()

asyncio.run(main(sys.argv[1:] == ["handler"]))
