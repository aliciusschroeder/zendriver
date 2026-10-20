import os, sys, tempfile, glob, pathlib
import zendriver as zd
from zendriver.core import util

# B: Config for connecting to an existing browser still requires a local executable
os.environ["PATH"] = "/nonexistent"
try:
    c = zd.Config(host="127.0.0.1", port=9222)
    print("B: Config ok", c.browser_executable_path)
except Exception as e:
    print("B: Config(host,port) raised", type(e).__name__, str(e)[:80])

# C: repr side effect
before = set(glob.glob(os.path.join(tempfile.gettempdir(), "uc_*")))
c = zd.Config(browser_executable_path="/path/to/browser")
print("C: _user_data_dir before repr:", c._user_data_dir)
r = repr(c)
after = set(glob.glob(os.path.join(tempfile.gettempdir(), "uc_*")))
print("C: _user_data_dir after repr:", c._user_data_dir, "new temp dirs:", after - before)

# E: circle with y=0
pts = list(util.circle(100, 0, radius=10, num=4))
print("E: circle(100, 0) points:", pts)
pts = list(util.circle(100, 50, radius=10, num=4))
print("E: circle(100, 50) points:", pts)

# I: add_extension picks nested manifest
d = pathlib.Path(tempfile.mkdtemp(dir="."))
(d / "manifest.json").write_text('{"manifest_version":3,"name":"x","version":"1"}')
(d / "web").mkdir()
(d / "web" / "manifest.webmanifest").write_text('{}')
c = zd.Config(browser_executable_path="/path/to/browser")
c.add_extension(d)
print("I: extension root", d, "-> loaded path", c._extensions)
