import asyncio, os, shutil, socket
import zendriver as zd
from zendriver.core import util
from zendriver.core.browser import Browser
print("zendriver from", zd.__file__)
insts = []
_oi = Browser.__init__
def _ni(self, *a, **k):
    _oi(self, *a, **k); insts.append(self)
Browser.__init__ = _ni
async def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    try:
        await asyncio.wait_for(zd.start(browser_executable_path=os.path.abspath("fake-chrome"), host="127.0.0.1", port=port), 0.3)
    except asyncio.TimeoutError:
        print("timed out")
    b = insts[-1]
    d = b.config._user_data_dir
    print("registered", len(util.get_registered_instances()), "temp dir", d, "exists", bool(d) and os.path.exists(d))
    if d: shutil.rmtree(d, ignore_errors=True)
asyncio.run(main())
