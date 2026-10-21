import importlib
import inspect
import pkgutil
import sys

import zendriver
from zendriver import cdp
from zendriver.core import util

print("zendriver from", zendriver.__file__, sys.version.split()[0])
rows = []
for m in pkgutil.iter_modules(cdp.__path__):
    if m.name in ("util",):
        continue
    mod = importlib.import_module(f"zendriver.cdp.{m.name}")
    enable = getattr(mod, "enable", None)
    if enable is None:
        continue
    gen = enable(**{p: None for p, v in inspect.signature(enable).parameters.items() if v.default is inspect.Parameter.empty}) if False else None
    # get the method name from source instead of calling (required params)
    src = inspect.getsource(enable)
    import re

    meth = re.search(r'"method": "([A-Za-z]+)\.enable"', src).group(1)
    try:
        resolved = util.cdp_get_module(meth.lower())
        ok = resolved is mod
        res_name = getattr(resolved, "__name__", resolved)
    except ModuleNotFoundError:
        ok = False
        res_name = "ModuleNotFoundError"
    sig = inspect.signature(enable)
    req = [p for p, v in sig.parameters.items() if v.default is inspect.Parameter.empty]
    opt = [p for p, v in sig.parameters.items() if v.default is not inspect.Parameter.empty]
    events = len(cdp.util.get_event_classes(mod)) if hasattr(cdp.util, "get_event_classes") else "?"
    if not ok:
        rows.append((meth, m.name, res_name, req, opt, events))
for r in rows:
    print("UNRESOLVED domain=%-22s module=%-22s resolved=%-20s required=%s optional=%s events=%s" % r)
