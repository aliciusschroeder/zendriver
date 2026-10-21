import asyncio, sys, pickle, os, tempfile
import zendriver as zd
from zendriver import cdp
from zendriver.core.browser import Browser, CookieJar
print("zendriver from", zd.__file__, sys.version.split()[0])
def mk(name, value, domain="example.com"):
    return cdp.network.Cookie(name=name, value=value, domain=domain, path="/", size=2, http_only=False, secure=False,
        session=True, priority=cdp.network.CookiePriority.MEDIUM, source_scheme=cdp.network.CookieSourceScheme.NON_SECURE,
        source_port=80, expires=-1)
cookies = [mk("a", "x"), mk("b", "y"), mk("session_id", "z")]
print(str(cookies[0].__dict__))
async def main():
    jar = CookieJar.__new__(CookieJar)
    async def get_all(requests_cookie_format=False): return cookies
    jar.get_all = get_all
    d = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
    f = os.path.join(d, "c.dat")
    for pat in ["session", "secure", "path", "name", "Medium", "Secure", "True", "domain", "^a$", "x", "session_id", "example"]:
        await jar.save(f, pattern=pat)
        with open(f, "rb") as fh: saved = pickle.load(fh)
        print(f"save(pattern={pat!r}) -> {[c.name for c in saved]}")
    os.remove(f); os.rmdir(d)
asyncio.run(main())
