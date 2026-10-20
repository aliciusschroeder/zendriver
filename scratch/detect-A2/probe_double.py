import asyncio
import zendriver as zd
from zendriver import cdp

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("about:blank")
        await tab.send(cdp.runtime.evaluate("0"))
        sent = []
        orig = tab._send_transaction
        async def spy(tx):
            sent.append((tx.method, tx.params))
            return await orig(tx)
        tab._send_transaction = spy
        tab.add_handler(cdp.fetch.RequestPaused, lambda e: None)
        await tab.send(cdp.fetch.enable(patterns=[cdp.fetch.RequestPattern(
            url_pattern="*/only-this.json", request_stage=cdp.fetch.RequestStage.RESPONSE)]))
        for m in sent:
            print(m)
        print("enabled", tab.enabled_domains, "manual", [m.__name__ for m in tab.manually_enabled_domains])
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 50))
