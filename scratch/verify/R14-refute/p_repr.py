"""Browser-free probe: does repr/str/config()/property read materialise a temp dir on the template?
Run with TMPDIR set to an empty dir so mkdtemp lands there."""
import asyncio
import copy
import glob
import logging
import os
import tempfile

import zendriver as zd
from zendriver.core.browser import Browser

print("zendriver from:", zd.__file__)
print("tempdir:", tempfile.gettempdir())
print("root logger level:", logging.getLogger().level, "zendriver eff level:",
      logging.getLogger("zendriver.core.browser").getEffectiveLevel())

T = tempfile.gettempdir()


def uc():
    return sorted(glob.glob(os.path.join(T, "uc_*")))


def fresh():
    return zd.Config(headless=True, browser_executable_path="/nonexistent/chrome")


for label, fn in [
    ("repr", repr),
    ("str", str),
    ("print-style f-string", lambda c: f"{c}"),
    ("logging %s lazy (not emitted at WARNING)", lambda c: logging.getLogger("x").debug("%s", c)),
    ("logging %s emitted", lambda c: logging.getLogger("x").warning("cfg %s", c) if False else logging.getLogger("x").error("cfg %s", c)),
    ("call config()", lambda c: c()),
    ("read .user_data_dir", lambda c: c.user_data_dir),
    ("read .uses_custom_data_dir", lambda c: c.uses_custom_data_dir),
    ("deepcopy only", copy.deepcopy),
]:
    before = uc()
    c = fresh()
    assert c._user_data_dir is None
    fn(c)
    after = uc()
    new = sorted(set(after) - set(before))
    print(f"{label:45s} template._user_data_dir={c._user_data_dir!r:40s} custom={c._custom_data_dir} new_dirs={len(new)}")
    for d in new:
        os.rmdir(d)


async def init_probe():
    # Browser.__init__: does it touch the template, or only its own copy?
    before = uc()
    tmpl = fresh()
    b = Browser(tmpl)
    after = uc()
    new = sorted(set(after) - set(before))
    print("Browser.__init__: template._user_data_dir =", tmpl._user_data_dir,
          "| copy._user_data_dir =", b.config._user_data_dir, "| new dirs:", new)
    for d in new:
        os.rmdir(d)

    # two Browser objects from the same untouched template -> distinct?
    b1, b2 = Browser(tmpl), Browser(tmpl)
    print("two Browsers from untouched template distinct:", b1.config._user_data_dir != b2.config._user_data_dir)
    for d in (b1.config._user_data_dir, b2.config._user_data_dir):
        os.rmdir(d)

    # two Browser objects from a repr'd template -> same?
    repr(tmpl)
    b1, b2 = Browser(tmpl), Browser(tmpl)
    print("after repr(template): b1 dir == b2 dir == template dir:",
          b1.config._user_data_dir == b2.config._user_data_dir == tmpl._user_data_dir,
          "| custom flags:", b1.config.uses_custom_data_dir, b2.config.uses_custom_data_dir)
    os.rmdir(tmpl._user_data_dir)
    print("leftover uc_*:", uc())


asyncio.run(init_probe())
