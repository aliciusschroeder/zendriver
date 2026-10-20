import asyncio, sys, types
fake = types.ModuleType("mss")
opened = []
class FakeMSS:
    monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
    def __init__(self): opened.append(self); self.closed = False
    def close(self): self.closed = True
fake.mss = FakeMSS
sys.modules["mss"] = fake

from zendriver import cdp
from zendriver.core.browser import Browser
from zendriver.core.config import Config

def ti(tid):
    return cdp.target.TargetInfo(target_id=cdp.target.TargetID(tid), type_="page", title="t", url="about:blank", attached=False, can_access_opener=False)

async def main():
    b = Browser(Config(browser_executable_path="/bin/true"))
    async def no_update(): pass
    b.update_targets = no_update
    try:
        print("0 windows:", await b.tile_windows())
    except Exception as e:
        print("0 windows:", type(e).__name__, e)
    for n in (1, 2, 4):
        tabs = [b._create_tab(ti(f"T{i}")) for i in range(n)]
        for i, t in enumerate(tabs):
            async def gw(i=i): return (i, None)
            async def sws(*a): pass
            t.get_window = gw; t.set_window_size = sws
        grid = await b.tile_windows(tabs)
        covered = sum(w for _, _, w, _ in grid if True) if grid else 0
        print(f"{n} windows -> grid {grid}  (total width used {sum(g[2] for g in grid)} of 1920)")
    print("mss instances opened:", len(opened), "closed:", sum(o.closed for o in opened))
asyncio.run(main())
