import zendriver, traceback
print("zendriver from", zendriver.__file__)
from zendriver.core._contradict import ContraDict, cdict

def t(label, fn):
    try:
        r = fn()
        print(f"OK   {label} -> {r!r}")
    except Exception as e:
        print(f"FAIL {label} -> {type(e).__name__}: {e}")

cd = ContraDict({'clear': 'all', 'items': '3', 'get': 'x', 'keys': 1, 'values': 'v', 'update': 'u', 'pop': 'p', 'copy': 'c', 'a': 1}, silent=True)
t("cd.clear()", lambda: cd.copy())
t("cd.items()", lambda: list(cd.items()))
t("cd.get('a')", lambda: cd.get('a'))
t("cd.keys()", lambda: list(cd.keys()))
t("cd.values()", lambda: list(cd.values()))
t("cd.update({})", lambda: cd.update({}))
t("cd.pop('a')", lambda: cd.pop('a'))
t("cd.clear()", lambda: cd.clear())
t("cdict({'keys':1}).keys()", lambda: cdict({'keys': 1}, silent=True).keys())
# key set later via __setitem__ (the Element._make_attrs path)
e = ContraDict(silent=True)
e['clear'] = 'all'
t("setitem-then .clear()", lambda: e.clear())
# control: normal keys
n = ContraDict({'a': 1}, silent=True)
t("control .items()", lambda: list(n.items()))
t("control .a", lambda: n.a)
# does dict's own machinery still work (dict(cd), json)?
import json
t("json.dumps(cd w/ clear)", lambda: json.dumps(ContraDict({'clear': 'all'}, silent=True)))
t("dict.items(cd) direct", lambda: list(dict.items(ContraDict({'items': 'x'}, silent=True))))
