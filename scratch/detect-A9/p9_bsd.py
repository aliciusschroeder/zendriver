import sys, os, shutil
print("chromium on PATH:", shutil.which("chromium"))
sys.platform = "freebsd14"   # what CPython reports on FreeBSD 14 (os.name == "posix")
import zendriver as zd
from zendriver.core import config as c
print("is_posix:", c.is_posix, "os.name:", os.name)
try:
    print("found:", c.find_executable("auto"))
except Exception as e:
    print("find_executable failed:", type(e).__name__)
