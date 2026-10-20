import asyncio, zendriver as zd
from zendriver.core import cloudflare as cf

HTML = """data:text/html,<html><body>
<div id=host><div id=chal style="width:300px;height:65px;background:gray">box</div></div>
<input type=hidden name=cf-turnstile-response value="">
<script>
document.addEventListener('mousedown', () => { document.open(); document.write('<p>solved, real site</p>'); document.close(); });
</script></body></html>"""

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(HTML)
        await tab.wait_for_ready_state("complete")
        host = await tab.select("#host")
        iframe = await tab.select("#chal")
        async def fake_wait(_tab, _timeout):
            return host, object(), iframe
        cf.cf_wait_for_interactive_challenge = fake_wait
        try:
            await cf.verify_cf(tab, click_delay=1, timeout=10)
            print("verify_cf returned normally (success detected)")
        except Exception as e:
            print("verify_cf raised", type(e).__name__, ":", str(e)[:160])
        print("page now:", await tab.evaluate("document.body.innerText"))
    finally:
        await browser.stop()

asyncio.run(asyncio.wait_for(main(), 60))
