import asyncio, collections, pathlib, tempfile, shutil, sys
import zendriver as zd
from zendriver.core import config as cfgmod
print("zendriver from", zd.__file__, "py", sys.version.split()[0])
FAKE = "/path/to/browser"

def dups(a):
    return {k: v for k, v in collections.Counter(a).items() if v > 1}

# K1
c = zd.Config(browser_executable_path=FAKE, browser_args=["--disable-features=Foo", "--mute-audio", "--mute-audio"])
print("K1 property:", [a for a in c.browser_args if "disable-features" in a or "mute" in a])
print("K1 call    :", [a for a in c() if "disable-features" in a or "mute" in a])

# K2
c = zd.Config(browser_executable_path=FAKE, headless=True, lang="de-DE", disable_webgl=True,
              browser_args=["--headless=new", "--no-sandbox", "--lang=de-DE", "--disable-webgl",
                            "--force-webrtc-ip-handling-policy"])
print("K2 is_root", cfgmod.is_root(), "sandbox", c.sandbox, "dups:", dups(c()))

# K4
lst = ["--mute-audio"]
c = zd.Config(browser_executable_path=FAKE, browser_args=lst)
c.add_argument("--window-size=800,600")
print("K4 caller list after add_argument:", lst)

# K5
for a in ["--disable-features=LanguageDetectionAPI", "--accept-lang=de-DE", "--enable-features=HeadlessModeFoo", "--load-extension=/opt/language-tools"]:
    try:
        zd.Config(browser_executable_path=FAKE).add_argument(a); print("K5 accepted", a)
    except ValueError as e:
        print("K5 REJECTED", a)

# K3 + K5-in-start: drive Browser.start without launching chrome
async def k3():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="r15probe_"))
    try:
        ext = tmp / "ext"; ext.mkdir(); (ext / "manifest.json").write_text("{}")
        c = zd.Config(browser_executable_path="/bin/true", browser_args=["--mute-audio"])
        c.add_extension(ext)
        b = zd.Browser(c)
        calls = []
        from zendriver.core import util
        orig = util._start_process
        class Boom(Exception): pass
        def fake_start(exe, params, is_posix, env=None):
            calls.append(list(params)); raise Boom()
        util._start_process = fake_start
        try:
            for i in range(2):
                b.config.host = b.config.port = None  # make start launch again
                try: await b.start()
                except Boom: pass
        finally:
            util._start_process = orig
        print("K3 --load-extension count per start:", [sum(p.startswith("--load-extension=") for p in ps) for ps in calls])
        # K5 via start: extension dir whose path contains 'headless'
        ext2 = tmp / "headless-helper"; ext2.mkdir(); (ext2 / "manifest.json").write_text("{}")
        c2 = zd.Config(browser_executable_path="/bin/true"); c2.add_extension(ext2)
        b2 = zd.Browser(c2)
        try:
            await b2.start(); print("K5-start: no error")
        except ValueError as e:
            print("K5-start: ValueError from Browser.start:", str(e)[:90])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
asyncio.run(asyncio.wait_for(k3(), 30))
