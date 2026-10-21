import asyncio
import zendriver as zd
from zendriver import cdp
print("ZENDRIVER IMPORTED FROM", zd.__file__)
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = browser.main_tab
        await tab.get("about:blank")
        sent = []
        orig = tab.websocket.send
        async def spy(m, *a, **k):
            sent.append(m)
            return await orig(m, *a, **k)
        tab.websocket.send = spy
        await tab.send(cdp.web_authn.enable(enable_ui=False))
        aid = await tab.send(cdp.web_authn.add_virtual_authenticator(cdp.web_authn.VirtualAuthenticatorOptions(protocol=cdp.web_authn.AuthenticatorProtocol.CTAP2, transport=cdp.web_authn.AuthenticatorTransport.USB)))
        print("manual domains:", [m.__name__ for m in tab.manually_enabled_domains])
        tab.add_handler(cdp.web_authn.CredentialAdded, lambda e: None)
        mark = len(sent)
        try:
            creds = await asyncio.wait_for(tab.send(cdp.web_authn.get_credentials(aid)), 5)
            print("get_credentials after handler added OK:", creds)
        except Exception as e:
            print("get_credentials raised:", type(e).__name__, str(e).splitlines()[0])
        print("frames sent:", [s[:60] for s in sent[mark:]])
    finally:
        await browser.stop()
asyncio.run(main())
