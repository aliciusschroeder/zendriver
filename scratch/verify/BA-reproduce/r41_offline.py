import asyncio, sys, types, re
import zendriver as zd
from zendriver import cdp
from zendriver.core.browser import Browser
from zendriver.core.config import Config
print("zendriver from", zd.__file__, "python", sys.version.split()[0])

def ti(tid, type_="page"):
    return cdp.target.TargetInfo(target_id=cdp.target.TargetID(tid), type_=type_, title=tid, url="about:blank", attached=False, can_access_opener=False)

def attempt(label, fn):
    try:
        print(f"{label}: {fn()!r}")
    except BaseException as e:
        print(f"{label}: {type(e).__name__} {e}")

async def iteration():
    b = Browser(Config(browser_executable_path="/bin/true"))
    b.config.host, b.config.port = "127.0.0.1", 1
    # (a) no targets
    b.targets = []
    attempt("list(empty)", lambda: list(b))
    attempt("next(iter(empty), None)", lambda: next(iter(b), None))
    # (b) only a service worker
    b.targets = [b._create_tab(ti("sw1", "service_worker"))]
    attempt("list(only sw)", lambda: list(b))
    # two page tabs
    A, B = b._create_tab(ti("A")), b._create_tab(ti("B"))
    b.targets = [A, B]
    attempt("list(b)", lambda: [t.target_id for t in b])
    attempt("nested", lambda: [(x.target_id, y.target_id) for x in b for y in b])
    attempt("zip(b,b)", lambda: [(x.target_id, y.target_id) for x, y in zip(b, b)])
    def exhausted():
        it = iter(b); list(it); return next(it, "sentinel")
    attempt("next after exhaustion (default)", exhausted)
    def exhausted2():
        it = iter(b); list(it)
        try:
            next(it)
        except StopIteration:
            return "StopIteration"
    attempt("next after exhaustion", exhausted2)
    attempt("next(reversed(b))", lambda: next(reversed(b)))
    attempt("list(reversed(b))", lambda: [t.target_id for t in reversed(b)])
    # Break inside loop then reiterate: shared state
    def broken_then_list():
        for t in b:
            break
        return [t.target_id for t in b]
    attempt("break then list", broken_then_list)

class FakeMSS:
    opened = 0; closed = 0
    def __init__(self, w=1920, h=1080):
        FakeMSS.opened += 1
        self.monitors = [{"left": 0, "top": 0, "width": w, "height": h}]
    def close(self):
        FakeMSS.closed += 1
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

async def tiling():
    fake = types.ModuleType("mss"); fake.mss = FakeMSS
    sys.modules["mss"] = fake
    b = Browser(Config(browser_executable_path="/bin/true"))
    b.config.host, b.config.port = "127.0.0.1", 1
    async def noop_update(): pass
    b.update_targets = noop_update
    def make_tab(i):
        t = b._create_tab(ti(f"T{i}"))
        async def get_window(i=i): return (i, None)
        sizes = []
        async def set_window_size(*pos): sizes.append(pos)
        t.__dict__["get_window"] = get_window
        t.__dict__["set_window_size"] = set_window_size
        return t
    for n in (1, 2, 4, 7):
        tabs = [make_tab(i) for i in range(n)]
        grid = await b.tile_windows(tabs)
        used = sum(g[2] for g in grid if g[1] == 0)
        print(f"{n} windows -> {grid} (row0 width used {used} of 1920; rows={len(set(g[1] for g in grid))})")
    grid = await b.tile_windows(tabs[:4], max_columns=2)
    print("4 windows max_columns=2 ->", grid)
    b.targets = []
    try:
        print("0 windows:", await b.tile_windows())
    except BaseException as e:
        print("0 windows:", type(e).__name__, e)
    try:
        print("windows=[] :", await b.tile_windows([]))
    except BaseException as e:
        print("windows=[]:", type(e).__name__, e)
    print(f"mss instances opened: {FakeMSS.opened} closed: {FakeMSS.closed}")
    del sys.modules["mss"]

def cookies():
    c = cdp.network.Cookie(name="sid", value="abc", domain="example.com", path="/", size=6, http_only=False,
                           secure=False, session=True, priority=cdp.network.CookiePriority.MEDIUM,
                           source_scheme=cdp.network.CookieSourceScheme.NON_SECURE, source_port=80)
    s = str(c.__dict__)
    print("str(__dict__) =", s[:300])
    for pat in ("session", "secure", "path", "name", "Medium", "http_only", "priority", "zzz"):
        print(f"  pattern {pat!r} matches cookie sid/abc/example.com: {bool(re.search(pat, s))}")

async def main():
    await iteration()
    await tiling()
    cookies()
asyncio.run(main())
