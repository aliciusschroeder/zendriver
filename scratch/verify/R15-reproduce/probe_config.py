import collections, sys
import zendriver
from zendriver.core import config as cfgmod
from zendriver import Config
print("python", sys.version.split()[0], "zendriver from", zendriver.__file__)
FAKE = "/path/to/browser"

def dups(args):
    return {a: n for a, n in collections.Counter(args).items() if n > 1}

print("\n=== K1: browser_args property vs Config() ===")
c = Config(browser_executable_path=FAKE,
           browser_args=["--disable-features=Foo", "--no-first-run", "--mute-audio", "--mute-audio"])
prop = c.browser_args
call = c()
print("property --disable-features entries:", [a for a in prop if a.startswith("--disable-features=")])
print("call()   --disable-features entries:", [a for a in call if a.startswith("--disable-features=")])
print("property duplicates:", dups(prop))
print("call()   duplicates:", dups(call))
print("in property not in call():", sorted(set(prop) - set(call)))
print("in call() not in property:", sorted(set(call) - set(prop)))
print("repr shows browser_args line:", [l for l in repr(c).splitlines() if "browser_args" in l][:1])
try:
    c.browser_args = ["--x"]
    print("assignment to browser_args OK")
except AttributeError as e:
    print("assignment to browser_args (as docs/quickstart.md shows) ->", type(e).__name__, e)

print("\n=== K2: user args repeating Config-owned flags ===")
cfgmod_is_root = cfgmod.is_root
c = Config(browser_executable_path=FAKE, headless=True, lang="de-DE", disable_webgl=True,
           sandbox=False,
           browser_args=["--headless=new", "--no-sandbox", "--lang=de-DE", "--disable-webgl",
                         "--disable-webgl2", "--webrtc-ip-handling-policy=disable_non_proxied_udp",
                         "--force-webrtc-ip-handling-policy", "--user-agent=UA", "--mute-audio", "--mute-audio"],
           user_agent="UA")
args = c()
print("duplicates in Config():", dups(args))
c2 = Config(browser_executable_path=FAKE, browser_args=["--webrtc-ip-handling-policy=default"])
a2 = c2()
print("user webrtc policy then Config's:", [a for a in a2 if a.startswith("--webrtc-ip-handling-policy")])
c3 = Config(browser_executable_path=FAKE, lang="de-DE", browser_args=["--lang=fr-FR"])
print("conflicting --lang entries:", [a for a in c3() if a.startswith("--lang")])
c4 = Config(browser_executable_path=FAKE, headless=False, browser_args=["--headless=new"])
print("headless attr False but argv has:", [a for a in c4() if "headless" in a], "config.headless =", c4.headless)

print("\n=== K4: aliasing of caller's browser_args list ===")
mine = ["--window-size=800,600"]
c = Config(browser_executable_path=FAKE, browser_args=mine)
print("c._browser_args is mine:", c._browser_args is mine)
c.add_argument("--mute-audio")
print("caller list after c.add_argument:", mine)
other = Config(browser_executable_path=FAKE, browser_args=mine)
print("second Config built from same list contains --mute-audio:", "--mute-audio" in other())
empty = []
c5 = Config(browser_executable_path=FAKE, browser_args=empty)
c5.add_argument("--mute-audio")
print("empty caller list after add_argument (not aliased because `if not browser_args`):", empty)

print("\n=== K5: add_argument substring rejection ===")
cands = ["--disable-features=LanguageDetectionAPI", "--accept-lang=fr-FR",
         "--enable-features=TranslateUI,LanguageSettings",
         "--load-extension=/home/me/headless-scraper/ext",
         "--load-extension=/opt/LanguageTool",
         "--disk-cache-dir=/tmp/user-data-dir-cache",
         "--mute-audio",
         "--lang=de", "--headless=new", "--no-sandbox", "--user-data-dir=/x"]
for a in cands:
    c = Config(browser_executable_path=FAKE)
    try:
        c.add_argument(a)
        print("ACCEPTED", a)
    except ValueError as e:
        print("REJECTED", a, "->", e)
print("\nvia constructor (no validation):", [a for a in Config(browser_executable_path=FAKE, browser_args=["--lang=fr", "--headless=new", "--user-data-dir=/x"])() if a.startswith(("--lang", "--headless", "--user-data-dir"))])
