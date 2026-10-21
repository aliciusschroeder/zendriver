import asyncio, base64, io, sys, zlib, struct
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)
D = sys.argv[1]

def png_center(b64):
    data = base64.b64decode(b64)
    # parse PNG minimal (8-bit RGB/RGBA, no interlace)
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8; idat = b''; w=h=ct=None
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos+4])[0]; typ = data[pos+4:pos+8]; body = data[pos+8:pos+8+ln]
        if typ == b'IHDR': w,h,bd,ct = struct.unpack('>IIBB', body[:10])
        elif typ == b'IDAT': idat += body
        pos += 12+ln
    raw = zlib.decompress(idat); bpp = 4 if ct==6 else 3; stride = w*bpp
    rows=[]; prev=bytearray(stride); i=0
    for y in range(h):
        f = raw[i]; i+=1; line = bytearray(raw[i:i+stride]); i+=stride
        for x in range(stride):
            a = line[x-bpp] if x>=bpp else 0; b = prev[x]; c = prev[x-bpp] if x>=bpp else 0
            if f==1: line[x]=(line[x]+a)&255
            elif f==2: line[x]=(line[x]+b)&255
            elif f==3: line[x]=(line[x]+(a+b)//2)&255
            elif f==4:
                p=a+b-c; pa=abs(p-a); pb=abs(p-b); pc=abs(p-c)
                pr = a if pa<=pb and pa<=pc else (b if pb<=pc else c)
                line[x]=(line[x]+pr)&255
        rows.append(line); prev=line
    cy, cx = h//2, w//2
    return (w,h,tuple(rows[cy][cx*bpp:cx*bpp+3]))

async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(f"file://{D}/page_r32.html")
        await tab.sleep(0.5)
        blue = await tab.select('#blue')
        print("unscrolled blue pos", await blue.get_position())
        print("unscrolled blue center", png_center(await blue.screenshot_b64(format='png')))
        await tab.evaluate("window.scrollTo(0,1100)")
        await tab.sleep(0.3)
        print("scrollY", await tab.evaluate("window.scrollY"))
        print("scrolled blue pos", await blue.get_position())
        print("scrolled blue center", png_center(await blue.screenshot_b64(format='png')))
        await tab.evaluate("window.scrollTo(0,0)")
        # jpg
        try:
            p = await blue.save_screenshot(f"{D}/out_x.jpg", format='jpg')
            print("jpg ok", p)
        except Exception as e:
            print("jpg EXC", type(e).__name__, str(e)[:200])
        for sel in ('#mir', '#rot'):
            el = await tab.select(sel)
            print(sel, "pos", await el.get_position())
            t = asyncio.ensure_future(el.screenshot_b64(format='png'))
            done, pend = await asyncio.wait([t], timeout=20)
            if pend:
                print(sel, "STILL PENDING after 20s; stack:")
                t.print_stack(file=sys.stdout)
                t.cancel()
                try: await t
                except BaseException as e: print(" cancelled:", type(e).__name__)
            else:
                try: print(sel, "result", png_center(t.result()))
                except Exception as e: print(sel, "EXC", type(e).__name__, str(e)[:200])
    finally:
        await browser.stop()
asyncio.run(main())
