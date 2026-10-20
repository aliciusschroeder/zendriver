import collections
import zendriver
import zendriver.core.config as cfgmod
from zendriver import Config

print("zendriver from", zendriver.__file__)
print("is_root:", cfgmod.is_root())
FAKE = "/path/to/browser"

def dups(lst):
    c = collections.Counter(lst)
    return {k: v for k, v in c.items() if v > 1}

print("\n=== K1: browser_args property vs __call__ ===")
c = Config(browser_executable_path=FAKE, browser_args=["--disable-features=Foo", "--mute-audio", "--mute-audio"])
prop = c.browser_args
call = c()
print("property disable-features:", [a for a in prop if a.startswith("--disable-features")])
print("__call__ disable-features:", [a for a in call if a.startswith("--disable-features")])
print("property dups:", dups(prop))
print("__call__ dups:", dups(call))
print("in __call__ but not property:", sorted(set(call) - set(prop)))
print("internal reads of .browser_args property: see grep")
print("repr:\n", repr(c))

print("\n=== K2: user args repeating Config-owned flags ===")
c = Config(browser_executable_path=FAKE, headless=True, lang="de-DE", disable_webgl=True,
           browser_args=["--headless=new", "--no-sandbox", "--lang=fr-FR", "--disable-webgl",
                         "--force-webrtc-ip-handling-policy", "--user-agent=X", "--remote-debugging-port=1"],
           user_agent="Y", port=2, host="127.0.0.1")
call = c()
print("dups:", dups(call))
print("lang args in order:", [a for a in call if a.startswith("--lang")])
print("ua args in order:", [a for a in call if a.startswith("--user-agent")])
print("port args in order:", [a for a in call if a.startswith("--remote-debugging-port")])
c = Config(browser_executable_path=FAKE, browser_args=["--no-sandbox"])
print("only --no-sandbox in user args, root:", dups(c()))

print("\n=== K4: aliasing of caller's list ===")
mine = ["--mute-audio"]
c = Config(browser_executable_path=FAKE, browser_args=mine)
print("c._browser_args is mine:", c._browser_args is mine)
c.add_argument("--window-size=800,600")
print("caller list after add_argument:", mine)
c2 = Config(browser_executable_path=FAKE, browser_args=mine)
print("second Config built from same list sees:", c2._browser_args)
empty = []
c3 = Config(browser_executable_path=FAKE, browser_args=empty)
c3.add_argument("--x")
print("empty list passed -> caller list after add_argument:", empty)

print("\n=== K5: add_argument substring rejection ===")
for a in ["--disable-features=LanguageDetectionAPI", "--accept-lang=fr-FR",
          "--load-extension=/home/me/golang/ext", "--load-extension=C:\\Users\\Lang\\ext",
          "--load-extension=/srv/headless-scraper/ext", "--disk-cache-dir=/x/data_dir",
          "--enable-features=HeadlessModeX", "--lang=de", "--headless=new", "--no-sandbox",
          "--user-data-dir=/x", "--disable-setuid-sandbox", "--mute-audio"]:
    c = Config(browser_executable_path=FAKE)
    try:
        c.add_argument(a)
        print("ACCEPTED", a)
    except ValueError as e:
        print("REJECTED", a)
