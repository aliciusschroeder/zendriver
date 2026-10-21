import asyncio, json, sys, tempfile, pathlib, shutil
import zendriver
from zendriver import KeyEvents, SpecialKeys, KeyModifiers, KeyPressEvent
print("zendriver from", zendriver.__file__)

HTML = """<html><body><textarea id=t></textarea><script>
window.log=[];
for (const ev of ['keydown','keypress','keyup']) document.addEventListener(ev, e => log.push(`${e.type}:${JSON.stringify(e.key)}:${e.code}:shift=${e.shiftKey}:ctrl=${e.ctrlKey}`), true);
</script></body></html>"""

async def main():
    d = tempfile.mkdtemp()
    p = pathlib.Path(d)/"k.html"; p.write_text(HTML)
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(p.as_uri())
        ta = await tab.select("#t")
        for s in ['\U0001F44D', '\U0001F44D\U0001F3FD', '\U0001F1E9\U0001F1EA', '\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466', 'á̂̃']:
            await ta.apply("(e)=>{e.value=''}")
            try:
                await ta.send_keys('x'+s+'y')
                res = "OK"
            except Exception as e:
                res = f"EXC {type(e).__name__} {e}"
            val = await ta.apply("(e)=>e.value")
            print(repr(s), "utf16:", len(s.encode('utf-16-le'))//2, res, "value ok:", val == 'x'+s+'y', repr(val))
        # modifiers
        for label, seq in [("A", ["A"]), ("Ctrl+Enter", [(SpecialKeys.ENTER, KeyModifiers.Ctrl)]), ("Ctrl+Shift+a", [("a", KeyModifiers.Ctrl|KeyModifiers.Shift)]), ("SPACE", [SpecialKeys.SPACE])]:
            await tab.evaluate("window.log=[]")
            await ta.send_keys(KeyEvents.from_mixed_input(seq))
            print(label, await tab.evaluate("JSON.stringify(window.log)"))
        await tab.evaluate("window.log=[]")
        await ta.send_keys(SpecialKeys.SPACE)
        print("send_keys(SPACE)", await tab.evaluate("JSON.stringify(window.log)"))
        ev = KeyEvents('A')
        p1 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP); p2 = ev.to_cdp_events(KeyPressEvent.DOWN_AND_UP)
        print("reuse p1 texts", [x['text'] for x in p1 if x['type_']=='keyDown'], "p2 texts", [x['text'] for x in p2 if x['type_']=='keyDown'], "ev.key now", ev.key)
    finally:
        await browser.stop()
        shutil.rmtree(d, ignore_errors=True)

asyncio.run(asyncio.wait_for(main(), 90))
