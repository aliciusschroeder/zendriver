import asyncio, sys, types, re, pickle, tempfile, os
import zendriver as zd
from zendriver import cdp
from zendriver.core.browser import Browser, CookieJar
print("zendriver from", zd.__file__, sys.version.split()[0])

def ti(tid, typ="page", url="about:blank"):
    return cdp.target.TargetInfo(target_id=cdp.target.TargetID(tid), type_=typ, title="", url=url, attached=False, can_access_opener=False)

def tryit(label, fn):
    try:
        print(f"{label}: -> {fn()!r}"[:200])
    except BaseException as e:
        print(f"{label}: {type(e).__name__} {e}"[:200])

async def main():
    b = Browser(zd.Config(browser_executable_path="/bin/true", headless=True))
    b.config.host = "127.0.0.1"; b.config.port = 1
    # (a) no targets
    b.targets = []
    tryit("list(empty)", lambda: list(b))
    tryit("next(iter(empty), None)", lambda: next(iter(b), None))
    # (b) only service worker
    b.targets = [b._create_tab(ti("sw1", "service_worker"))]
    tryit("list(only sw)", lambda: list(b))
    # two tabs
    A = b._create_tab(ti("A")); Bt = b._create_tab(ti("B"))
    b.targets = [A, Bt]
    tryit("list(two)", lambda: [t.target_id for t in b])
    tryit("nested", lambda: [(x.target_id, y.target_id) for x in b for y in b])
    tryit("zip(b,b)", lambda: [(x.target_id, y.target_id) for x, y in zip(b, b)])
    def exhaust():
        it = iter(b); list(it); return next(it, "sentinel")
    tryit("next after exhaustion", exhaust)
    def exhaust2():
        it = iter(b); list(it); return list(it)
    tryit("list after exhaustion", exhaust2)
    tryit("next(reversed(b))", lambda: next(reversed(b)))
    tryit("list(reversed(b))", lambda: [t.target_id for t in reversed(b)])
    tryit("for-loop break then list", lambda: ([t for t in b][:0], next(iter(b)).target_id, [t.target_id for t in b]))
    def brk():
        for t in b:
            break
        return [t.target_id for t in b]
    tryit("list after break", brk)
    # tile_windows with fake mss
    inst = []
    class FakeMSS:
        def __init__(self): self.monitors = [{"width": 1920, "height": 1080}]; self.closed = False; inst.append(self)
        def close(self): self.closed = True
    sys.modules["mss"] = types.SimpleNamespace(mss=FakeMSS)
    async def noop(): pass
    b.update_targets = noop
    class FT:
        def __init__(s, i): s.i = i; s.size = None
        async def get_window(s): return (s.i, None)
        async def set_window_size(s, *pos): s.size = pos
    for n in (1, 2, 4, 6):
        tabs = [FT(i) for i in range(n)]
        grid = await b.tile_windows(tabs)
        print(f"tile {n} windows -> {grid}; total width {sum(g[2] for g in grid if g[1]==0)}")
    b.targets = []
    try:
        print("tile 0 windows ->", await b.tile_windows())
    except BaseException as e:
        print("tile 0 windows:", type(e).__name__, e)
    print("mss instances", len(inst), "closed", sum(i.closed for i in inst))
    # CookieJar pattern
    c1 = cdp.network.Cookie(name="a", value="x", domain="example.com", path="/", size=2, http_only=False, secure=False, session=True, priority=cdp.network.CookiePriority.MEDIUM, same_party=False, source_scheme=cdp.network.CookieSourceScheme.NON_SECURE, source_port=80, expires=-1) if 'same_party' in cdp.network.Cookie.__dataclass_fields__ else None
    import inspect
    print("Cookie fields:", list(cdp.network.Cookie.__dataclass_fields__)[:20])
asyncio.run(main())
