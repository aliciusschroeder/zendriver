import asyncio
import sys

import zendriver as zd
from zendriver import cdp

print("zendriver from", zd.__file__, sys.version.split()[0])


def spy(tab, log):
    orig = tab._send_transaction

    async def wrapped(tx):
        log.append((tx.method, tx.params))
        return await orig(tx)

    tab._send_transaction = wrapped


async def run(order):
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        sent = []
        spy(tab, sent)

        async def h(ev):
            print("CredentialAdded", ev)

        if order == "handler-first":
            tab.add_handler(cdp.web_authn.CredentialAdded, h)
        await tab.send(cdp.web_authn.enable(enable_ui=True))
        await tab.send(cdp.fed_cm.enable(disable_rejection_delay=True))
        print(order, "manual:", [m.__name__ for m in tab.manually_enabled_domains],
              "auto:", [m.__name__ for m in tab.enabled_domains])
        auth = await tab.send(
            cdp.web_authn.add_virtual_authenticator(
                cdp.web_authn.VirtualAuthenticatorOptions(
                    protocol=cdp.web_authn.AuthenticatorProtocol.CTAP2,
                    transport=cdp.web_authn.AuthenticatorTransport.INTERNAL,
                )
            )
        )
        if order == "enable-first":
            tab.add_handler(cdp.web_authn.CredentialAdded, h)
            tab.add_handler(cdp.fed_cm.DialogShown, h)
        sent.clear()
        creds = await asyncio.wait_for(tab.send(cdp.web_authn.get_credentials(auth)), 10)
        print(order, "sent for one getCredentials call:", sent)
        print(order, "getCredentials ok ->", creds)
        sent.clear()
        await asyncio.wait_for(tab.evaluate("1"), 10)
        print(order, "sent for next call:", [m for m, _ in sent])
    finally:
        await browser.stop()


async def main():
    await run("enable-first")
    await run("handler-first")


asyncio.run(main())
